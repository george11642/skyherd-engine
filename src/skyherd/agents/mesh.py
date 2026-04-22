"""AgentMesh — orchestrates all 5 SkyHerd managed-agent sessions.

Usage::

    mesh = AgentMesh()
    await mesh.start()
    # ... demo runs ...
    await mesh.stop()

Or via CLI::

    skyherd-mesh mesh start
    skyherd-mesh mesh smoke
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from skyherd.agents.calving_watch import CALVING_WATCH_SPEC
from skyherd.agents.calving_watch import handler as calving_handler
from skyherd.agents.cost import run_tick_loop
from skyherd.agents.fenceline_dispatcher import (
    FENCELINE_DISPATCHER_SPEC,
)
from skyherd.agents.fenceline_dispatcher import (
    handler as fenceline_handler,
)
from skyherd.agents.grazing_optimizer import (
    GRAZING_OPTIMIZER_SPEC,
)
from skyherd.agents.grazing_optimizer import (
    handler as grazing_handler,
)
from skyherd.agents.herd_health_watcher import (
    HERD_HEALTH_WATCHER_SPEC,
)
from skyherd.agents.herd_health_watcher import (
    handler as herd_handler,
)
from skyherd.agents.predator_pattern_learner import (
    PREDATOR_PATTERN_LEARNER_SPEC,
)
from skyherd.agents.predator_pattern_learner import (
    handler as predator_handler,
)
from skyherd.agents.session import Session, SessionManager
from skyherd.agents.spec import AgentSpec

logger = logging.getLogger(__name__)

# Map agent name → (spec, handler)
_AGENT_REGISTRY: list[tuple[AgentSpec, Any]] = [
    (FENCELINE_DISPATCHER_SPEC, fenceline_handler),
    (HERD_HEALTH_WATCHER_SPEC, herd_handler),
    (PREDATOR_PATTERN_LEARNER_SPEC, predator_handler),
    (GRAZING_OPTIMIZER_SPEC, grazing_handler),
    (CALVING_WATCH_SPEC, calving_handler),
]

# Synthetic smoke-test wake events (one per agent)
_SMOKE_WAKE_EVENTS: list[dict[str, Any]] = [
    {
        "topic": "skyherd/ranch_a/fence/seg_1",
        "type": "fence.breach",
        "ranch_id": "ranch_a",
        "segment": "seg_1",
        "lat": 34.123,
        "lon": -106.456,
    },
    {
        "topic": "skyherd/ranch_a/trough_cam/trough_a",
        "type": "camera.motion",
        "ranch_id": "ranch_a",
        "trough_id": "trough_a",
        "anomaly": True,
    },
    {
        "topic": "skyherd/ranch_a/thermal/cam_1",
        "type": "nightly.analysis",
        "ranch_id": "ranch_a",
    },
    {
        "topic": "skyherd/ranch_a/cron/weekly_monday",
        "type": "weekly.schedule",
        "ranch_id": "ranch_a",
    },
    {
        "topic": "skyherd/ranch_a/collar/tag_007",
        "type": "collar.activity_spike",
        "ranch_id": "ranch_a",
        "tag": "tag_007",
    },
]


class AgentMesh:
    """Orchestrates the 5 SkyHerd agent sessions.

    Manages session lifecycle, MQTT routing, cost ticking, and the smoke test.
    """

    def __init__(
        self,
        mqtt_publish_callback: Any | None = None,
        ledger_callback: Any | None = None,
    ) -> None:
        self._session_manager = SessionManager(
            mqtt_publish_callback=mqtt_publish_callback,
            ledger_callback=ledger_callback,
        )
        self._sessions: dict[str, Session] = {}  # name → session
        self._handlers: dict[str, Any] = {}  # name → handler fn
        self._stop_event = asyncio.Event()
        self._tick_task: asyncio.Task[None] | None = None
        self._mqtt_task: asyncio.Task[None] | None = None
        self._inflight_handlers: set[asyncio.Task] = set()  # prevent GC of fire-and-forget tasks

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Create all 5 sessions and start the cost-tick loop + MQTT subscriber."""
        for spec, handler_fn in _AGENT_REGISTRY:
            session = self._session_manager.create_session(spec)
            self._sessions[spec.name] = session
            self._handlers[spec.name] = handler_fn
            logger.info("AgentMesh: registered %s (session %s)", spec.name, session.id[:8])

        tickers = self._session_manager.all_tickers()
        self._tick_task = asyncio.create_task(
            run_tick_loop(tickers, self._stop_event),
            name="cost-tick-loop",
        )

        # Start MQTT subscriber if bus is available
        self._mqtt_task = asyncio.create_task(
            self._mqtt_loop(),
            name="mqtt-event-loop",
        )

        logger.info("AgentMesh started — 5 sessions idle, cost ticker running.")

    async def stop(self) -> None:
        """Gracefully shut down: flush all checkpoints, cancel tasks."""
        self._stop_event.set()

        for session in self._sessions.values():
            try:
                self._session_manager.checkpoint(session.id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("checkpoint failed for %s: %s", session.agent_name, exc)

        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass

        if self._mqtt_task:
            self._mqtt_task.cancel()
            try:
                await self._mqtt_task
            except asyncio.CancelledError:
                pass

        logger.info("AgentMesh stopped — all sessions checkpointed.")

    # ------------------------------------------------------------------
    # Smoke test
    # ------------------------------------------------------------------

    async def smoke_test(self, sdk_client: Any | None = None) -> dict[str, Any]:
        """Synchronous coroutine: fire one synthetic wake event per agent.

        Does NOT require ANTHROPIC_API_KEY — all agents fall back to
        ``_simulate_handler()`` when the key is absent.

        Returns a dict mapping agent_name → list-of-tool-calls.
        """
        results: dict[str, Any] = {}

        # If no API key, use None for sdk_client to force simulation path
        if sdk_client is None and not os.environ.get("ANTHROPIC_API_KEY"):
            sdk_client = None

        for (spec, handler_fn), wake_event in zip(_AGENT_REGISTRY, _SMOKE_WAKE_EVENTS, strict=True):
            session = self._session_manager.create_session(spec)
            self._session_manager.wake(session.id, wake_event)

            try:
                tool_calls = await handler_fn(session, wake_event, sdk_client)
            except Exception as exc:  # noqa: BLE001
                logger.error("smoke_test handler error for %s: %s", spec.name, exc)
                tool_calls = []

            self._session_manager.sleep(session.id)
            results[spec.name] = tool_calls

            logger.info(
                "smoke_test: %s → %d tool calls",
                spec.name,
                len(tool_calls),
            )

        return results

    # ------------------------------------------------------------------
    # Internal MQTT loop
    # ------------------------------------------------------------------

    async def _mqtt_loop(self) -> None:
        """Subscribe to MQTT and route events to sessions via on_webhook."""
        try:
            from skyherd.sensors.bus import SensorBus

            bus = SensorBus()
            async with bus.subscribe("#") as messages:
                async for topic, payload in messages:
                    if self._stop_event.is_set():
                        break
                    event = {"topic": topic, **payload}
                    woken = self._session_manager.on_webhook(event)
                    for session in woken:
                        handler_fn = self._handlers.get(session.agent_name)
                        if handler_fn:
                            _task = asyncio.create_task(
                                self._run_handler(session, event, handler_fn),
                                name=f"handler-{session.agent_name}",
                            )
                            self._inflight_handlers.add(_task)
                            _task.add_done_callback(self._inflight_handlers.discard)
        except Exception as exc:  # noqa: BLE001
            logger.debug("MQTT loop unavailable (%s) — running without live sensor bus.", exc)

    async def _run_handler(
        self,
        session: Session,
        wake_event: dict[str, Any],
        handler_fn: Any,
    ) -> None:
        """Run one handler wake cycle and sleep the session on completion."""
        try:
            await handler_fn(session, wake_event, sdk_client=None)
        except Exception as exc:  # noqa: BLE001
            logger.error("handler error for %s: %s", session.agent_name, exc)
        finally:
            self._session_manager.sleep(session.id)
