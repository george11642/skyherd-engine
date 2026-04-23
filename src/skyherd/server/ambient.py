"""In-process ambient scenario driver for the live dashboard.

Problem
-------
``skyherd.server.live`` boots a real ``world`` / ``ledger`` / ``_DemoMesh`` and
then sits idle - ``skyherd-demo play`` runs in a *separate* process with its
own in-memory deps, so nothing reaches the dashboard's SSE broadcaster. The
user lands on an empty dashboard.

Fix
---
Run scenarios *inside* the server process against the same mesh/world/ledger
the broadcaster already watches. The broadcaster's existing ``_snapshot_loop``,
``_cost_loop``, ``_attest_loop``, and ``_vet_intake_loop`` observers fire
naturally - no broadcaster changes required.

:class:`AmbientDriver` rotates through the 8 demo scenarios in the video
narrative order (coyote -> sick_cow -> water_drop -> storm -> calving ->
wildfire -> rustling -> cross_ranch_coyote) and calls
:func:`skyherd.scenarios.base._run_async_shared` with the caller-owned
deps. Speed is a sim-to-wall ratio; the default 15.0 pushes each 600 s
scenario through in ~40 s wall-time so all 8 cycle in ~6 minutes.

Optional ``broadcaster`` argument lets the driver announce scenario
transitions on SSE via ``scenario.active`` / ``scenario.ended`` events
(Part B's RanchMap breadcrumb subscribes to these).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from skyherd.scenarios import SCENARIOS
from skyherd.scenarios.base import _DemoMesh, _run_async_shared

logger = logging.getLogger(__name__)


# Demo-video rotation order (locked in docs/ARCHITECTURE.md:121 hero loop).
_ROTATION: tuple[str, ...] = (
    "coyote",
    "sick_cow",
    "water_drop",
    "storm",
    "calving",
    "wildfire",
    "rustling",
    "cross_ranch_coyote",
)


def _iso_utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _try_emit(broadcaster: Any, event_type: str, payload: dict[str, Any]) -> None:
    """Best-effort SSE emit: try ``emit`` -> ``publish`` -> ``_broadcast``.

    The dashboard's ``EventBroadcaster`` exposes ``_broadcast(event_type,
    payload)`` today; the public wrapper is ``emit`` / ``publish`` per the
    plan. Duck-typed so the driver works with future broadcaster refactors
    without changes.
    """
    if broadcaster is None:
        return
    for attr in ("emit", "publish", "_broadcast"):
        fn = getattr(broadcaster, attr, None)
        if callable(fn):
            try:
                fn(event_type, payload)
            except Exception as exc:  # noqa: BLE001
                logger.debug("broadcaster.%s(%s) raised: %s", attr, event_type, exc)
            return
    logger.debug("broadcaster has no emit/publish/_broadcast - skipping %s", event_type)


class AmbientDriver:
    """Background task that rotates through demo scenarios forever.

    Drives :func:`_run_async_shared` against caller-owned mesh/world/ledger
    so all side-effects land on the broadcaster the live dashboard reads.
    Speed and skip are runtime-settable so ``/api/ambient/speed`` and
    ``/api/ambient/next`` can steer the loop without a server restart.
    """

    def __init__(
        self,
        mesh: _DemoMesh,
        world: Any,
        ledger: Any,
        broadcaster: Any | None = None,
        speed: float = 15.0,
    ) -> None:
        self._mesh = mesh
        self._world = world
        self._ledger = ledger
        self._broadcaster = broadcaster
        self._speed = float(speed)
        self._stopped = False
        self._task: asyncio.Task[None] | None = None
        self._active: str | None = None
        self._skip_event = asyncio.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def active_scenario(self) -> str | None:
        """Name of the currently-playing scenario, or ``None`` when idle."""
        return self._active

    @property
    def speed(self) -> float:
        return self._speed

    def set_speed(self, speed: float) -> None:
        """Change sim-to-wall ratio at runtime.

        Takes effect on the next step of the current scenario (and on all
        subsequent scenarios).
        """
        self._speed = float(speed)

    def skip(self) -> None:
        """Bail out of the current scenario at the next step boundary."""
        self._skip_event.set()

    async def start(self) -> None:
        """Spawn the background rotation task. Idempotent."""
        if self._task is not None and not self._task.done():
            return
        self._stopped = False
        self._skip_event.clear()
        self._task = asyncio.create_task(self._run_forever(), name="ambient-driver")

    async def stop(self) -> None:
        """Cancel the task and wait for it to exit cleanly."""
        self._stopped = True
        task = self._task
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("AmbientDriver background task raised: %s", exc)
        finally:
            self._task = None
            self._active = None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _run_forever(self) -> None:
        pass_idx = 0
        try:
            while not self._stopped:
                for name in _ROTATION:
                    if self._stopped:
                        break
                    await self._play_one(name, pass_idx)
                    if self._stopped:
                        break
                    # Cooldown scales inversely with speed so 15x feels idle
                    # but 30x video mode doesn't pad the timelapse.
                    cooldown = max(1.0, 3.0 / max(self._speed, 0.1))
                    try:
                        await asyncio.sleep(cooldown)
                    except asyncio.CancelledError:
                        raise
                pass_idx += 1
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("AmbientDriver crashed: %s", exc)

    async def _play_one(self, name: str, pass_idx: int) -> None:
        scenario_cls = SCENARIOS.get(name)
        if scenario_cls is None:
            logger.warning("AmbientDriver: unknown scenario %r - skipping", name)
            return
        scenario = scenario_cls()
        self._active = name
        self._skip_event.clear()
        started_at = _iso_utc_now()
        _try_emit(
            self._broadcaster,
            "scenario.active",
            {
                "name": name,
                "pass_idx": pass_idx,
                "speed": self._speed,
                "started_at": started_at,
            },
        )
        outcome = "ok"
        try:
            await self._race_with_skip(scenario, pass_idx)
        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("AmbientDriver: scenario %s raised %s", name, exc)
            outcome = f"error:{type(exc).__name__}"
        finally:
            ended_at = _iso_utc_now()
            _try_emit(
                self._broadcaster,
                "scenario.ended",
                {
                    "name": name,
                    "pass_idx": pass_idx,
                    "outcome": outcome,
                    "started_at": started_at,
                    "ended_at": ended_at,
                },
            )
            self._active = None

    async def _race_with_skip(self, scenario: Any, pass_idx: int) -> None:
        """Run the scenario; bail early if :meth:`skip` is called."""
        play_task: asyncio.Task[Any] = asyncio.create_task(
            _run_async_shared(
                scenario,
                world=self._world,
                ledger=self._ledger,
                mesh=self._mesh,
                seed=42 + pass_idx,
                speed=self._speed,
                assert_outcome=False,
            ),
            name=f"ambient-play-{scenario.name}",
        )
        skip_wait: asyncio.Task[Any] = asyncio.create_task(
            self._skip_event.wait(), name="ambient-skip-wait"
        )
        try:
            done, _pending = await asyncio.wait(
                {play_task, skip_wait}, return_when=asyncio.FIRST_COMPLETED
            )
            if skip_wait in done and not play_task.done():
                play_task.cancel()
                try:
                    await play_task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
        finally:
            if not skip_wait.done():
                skip_wait.cancel()
                try:
                    await skip_wait
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
            if not play_task.done():
                play_task.cancel()
                try:
                    await play_task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
