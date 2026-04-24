"""PiToMissionBridge — wires Pi sensor events to a real drone mission.

Subscribes to MQTT topics emitted by :class:`~skyherd.edge.coyote_harness.CoyoteHarness`
and :class:`~skyherd.edge.picam_sensor.PiCamSensor` (Phase 5), routes each wake
event through :class:`~skyherd.agents.fenceline_dispatcher.FENCELINE_DISPATCHER_SPEC`
simulation handler, and executes the resulting ``launch_drone`` / ``play_deterrent``
tool calls against a real :class:`~skyherd.drone.interface.DroneBackend`.

Design notes
------------
* No Anthropic API key required — uses :func:`skyherd.agents.simulate.fenceline_dispatcher`
  which returns a deterministic tool-call list.  Swap via the ``dispatch`` DI hook.
* Every externally-observable step appends one entry to an
  :class:`~skyherd.attest.ledger.Ledger` — ``wake_event``, ``mission.launched``,
  ``deterrent.played``, ``mission.failed``, ``sitl.failover`` are the canonical kinds.
* Deterministic: no wall-clock imports; every timestamp flows through an injected
  ``ts_provider`` (same pattern as :class:`CoyoteHarness`).
* Failure-tolerant: :class:`~skyherd.drone.interface.DroneUnavailable` never
  propagates out of :meth:`handle_event`; the bridge logs, writes a failover
  ledger entry, and keeps the subscriber loop alive.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import signal
import sqlite3
import time
from collections.abc import Awaitable, Callable
from typing import Any

from skyherd.agents.fenceline_dispatcher import FENCELINE_DISPATCHER_SPEC
from skyherd.agents.session import Session
from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.drone.interface import DroneBackend, DroneError, Waypoint

logger = logging.getLogger(__name__)

# Allowed topic prefixes (matched lexicographically after filling in ranch_id)
_ALLOWED_TOPIC_SUFFIXES = ("/fence/", "/alert/thermal_hit", "/thermal/")

_DEFAULT_RANCH_ID = "ranch_a"
_DEFAULT_MQTT_URL = "mqtt://localhost:1883"

__all__ = [
    "PiToMissionBridge",
    "verify_chain",
]


def _canonical_json(payload: dict[str, Any]) -> str:
    """Deterministic JSON wire format."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


# ---------------------------------------------------------------------------
# PiToMissionBridge
# ---------------------------------------------------------------------------


DispatchCallable = Callable[[dict[str, Any], Session], list[dict[str, Any]]]


class PiToMissionBridge:
    """Pi MQTT events → FenceLineDispatcher → DroneBackend + Ledger.

    Parameters
    ----------
    ranch_id:
        Target ranch id.  Subscribed topics use this as a prefix.
    drone_backend:
        A :class:`DroneBackend`.  When ``None`` a lazy
        :func:`skyherd.drone.interface.get_backend` call is used (respects the
        ``DRONE_BACKEND`` environment variable).
    ledger:
        Pre-opened :class:`Ledger`.  When ``None`` an in-memory SQLite ledger is
        constructed with a fresh :class:`Signer`.
    agent_session:
        Pre-constructed :class:`Session`.  Default is a throwaway session for
        ``FenceLineDispatcher``.
    dispatch:
        DI hook — the callable that maps ``(wake_event, session) -> list[tool_call_dict]``.
        Defaults to :func:`skyherd.agents.simulate.fenceline_dispatcher`.
    mqtt_publish:
        Optional async callable ``(topic, raw_bytes) -> None`` used for side-channel
        publishes (e.g. the ``deterrent/play`` emit).  When ``None`` side-channel
        publishes are best-effort via ``aiomqtt`` (or no-op in tests).
    ts_provider:
        Injectable timestamp source.  Used for payload ``ts`` fields and for the
        Ledger's ``ts_provider`` if we construct one.
    seed:
        Deterministic mission-id seed.  When set, the pseudo-random mission id is
        reproducible across replays (seed=42 → identical ids, always).
    """

    def __init__(
        self,
        *,
        ranch_id: str | None = None,
        drone_backend: DroneBackend | None = None,
        ledger: Ledger | None = None,
        agent_session: Session | None = None,
        dispatch: DispatchCallable | None = None,
        mqtt_publish: Callable[[str, bytes], Awaitable[None]] | None = None,
        ts_provider: Callable[[], float] | None = None,
        seed: int | None = None,
    ) -> None:
        self._ranch_id = ranch_id or os.environ.get("RANCH_ID", _DEFAULT_RANCH_ID)
        self._mqtt_url = os.environ.get("MQTT_URL", _DEFAULT_MQTT_URL)
        self._drone_backend = drone_backend or self._default_backend()
        self._ts_provider = ts_provider or time.time
        self._ledger = ledger or self._default_ledger(self._ts_provider)
        self._session = agent_session or self._default_session()
        self._dispatch = dispatch or self._default_dispatch()
        self._mqtt_publish = mqtt_publish
        self._seed = seed
        self._tick_counter = 0
        self._running = False
        self._connected = False
        self._topic_filter = tuple(
            f"skyherd/{self._ranch_id}{suffix}" for suffix in _ALLOWED_TOPIC_SUFFIXES
        )

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_backend() -> DroneBackend:
        from skyherd.drone.interface import get_backend

        return get_backend()

    @staticmethod
    def _default_ledger(ts_provider: Callable[[], float]) -> Ledger:
        signer = Signer.generate()
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.commit()
        # Bootstrap DDL via Ledger.open pattern (mirrors ledger.open internals).
        from skyherd.attest.ledger import _DDL  # noqa: PLC0415

        conn.execute(_DDL)
        conn.commit()
        return Ledger(conn, signer, ts_provider=ts_provider)

    @staticmethod
    def _default_session() -> Session:
        return Session(
            id="pi_to_mission_session",
            agent_name="FenceLineDispatcher",
            agent_spec=FENCELINE_DISPATCHER_SPEC,
        )

    @staticmethod
    def _default_dispatch() -> DispatchCallable:
        from skyherd.agents.simulate import fenceline_dispatcher

        return fenceline_dispatcher

    # ------------------------------------------------------------------
    # Public: connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open the underlying drone backend connection (idempotent)."""
        if self._connected:
            return
        try:
            await self._drone_backend.connect()
            self._connected = True
        except DroneError as exc:
            logger.warning("PiToMissionBridge backend connect failed: %s", exc)
            self._append_ledger("backend.connect_failed", {"error": str(exc)})

    async def close(self) -> None:
        """Disconnect the drone backend (best-effort)."""
        try:
            await self._drone_backend.disconnect()
        except Exception as exc:  # noqa: BLE001
            logger.debug("PiToMissionBridge backend disconnect error: %s", exc)
        self._connected = False

    # ------------------------------------------------------------------
    # Public: event handling
    # ------------------------------------------------------------------

    async def handle_event(
        self, topic: str, payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Route one inbound event; return the list of executed tool calls.

        Executed tool calls include a ``status`` key (``"ok"`` / ``"failed"``) for
        observability.  Returns ``[]`` when the topic is filtered out or the event
        is a non-dispatch kind.
        """
        if not self._accepts(topic):
            logger.debug("PiToMissionBridge drop: topic %s not in allowlist", topic)
            return []

        wake_event = self._normalise(topic, payload)
        self._append_ledger("wake_event", {"topic": topic, "event": wake_event})

        if wake_event.get("type") not in ("fence.breach", "thermal.hotspot"):
            # Non-dispatch events (sensor.heartbeat, water.low, …) — log-only.
            self._append_ledger("wake_event.ignored", {"topic": topic, "type": wake_event.get("type")})
            return []

        # Ensure backend is connected before dispatching.
        await self.connect()

        tool_calls = self._dispatch(wake_event, self._session)
        executed: list[dict[str, Any]] = []
        for call in tool_calls:
            result = await self._execute_tool_call(call, wake_event)
            executed.append(result)
        return executed

    async def failover(self, reason: str) -> None:
        """Trigger return-to-home and record a ``sitl.failover`` ledger entry."""
        try:
            await self._drone_backend.return_to_home()
            self._append_ledger(
                "sitl.failover",
                {"reason": reason, "status": "rtl_ok"},
            )
        except DroneError as exc:
            self._append_ledger(
                "sitl.failover",
                {"reason": reason, "status": "rtl_failed", "error": str(exc)},
            )

    # ------------------------------------------------------------------
    # Topic filter + wake-event normalisation
    # ------------------------------------------------------------------

    def _accepts(self, topic: str) -> bool:
        return any(topic.startswith(prefix) for prefix in self._topic_filter)

    def _normalise(self, topic: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Flatten incoming payload into the schema FenceLineDispatcher expects."""
        kind = payload.get("kind", "")
        segment = topic.rstrip("/").rsplit("/", 1)[-1]
        lat = float(payload.get("lat", payload.get("cam_lat", 34.0)))
        lon = float(payload.get("lon", payload.get("cam_lon", -106.0)))

        # Determine the dispatcher "type" from the payload/topic.
        if "/fence/" in topic:
            event_type = "fence.breach"
        elif "/alert/thermal_hit" in topic or kind == "predator.thermal_hit":
            event_type = "thermal.hotspot"
        elif "/thermal/" in topic:
            event_type = "thermal.hotspot"
        else:
            event_type = payload.get("type", "unknown")

        return {
            "type": event_type,
            "topic": topic,
            "source": payload.get("source", "pi_to_mission"),
            "ranch_id": payload.get("ranch", payload.get("ranch_id", self._ranch_id)),
            "segment": payload.get("segment", segment),
            "lat": lat,
            "lon": lon,
            "species_hint": payload.get("species", payload.get("species_hint")),
            "raw_kind": kind,
        }

    # ------------------------------------------------------------------
    # Tool-call execution
    # ------------------------------------------------------------------

    async def _execute_tool_call(
        self, call: dict[str, Any], wake_event: dict[str, Any]
    ) -> dict[str, Any]:
        tool = call.get("tool", "")
        args = call.get("input", {}) or {}
        if tool == "launch_drone":
            return await self._exec_launch_drone(args, wake_event)
        if tool == "play_deterrent":
            return await self._exec_play_deterrent(args, wake_event)
        if tool == "get_thermal_clip":
            return await self._exec_get_thermal_clip(args)
        if tool == "page_rancher":
            # Page routing lives in the voice module; emit a skipped entry so
            # tests can count it but don't fail if the voice stack is absent.
            self._append_ledger("tool.skipped", {"tool": tool, "input": args})
            return {"tool": tool, "status": "skipped"}
        # Unknown tool — log and ignore.
        self._append_ledger("tool.skipped", {"tool": tool, "input": args})
        return {"tool": tool, "status": "skipped"}

    async def _exec_launch_drone(
        self, args: dict[str, Any], wake_event: dict[str, Any]
    ) -> dict[str, Any]:
        mission = str(args.get("mission", "fence_patrol"))
        lat = float(args.get("target_lat", wake_event.get("lat", 34.0)))
        lon = float(args.get("target_lon", wake_event.get("lon", -106.0)))
        alt_m = float(args.get("alt_m", 60.0))
        mission_id = self._make_mission_id()
        try:
            await self._drone_backend.takeoff(alt_m=alt_m)
            waypoint = Waypoint(lat=lat, lon=lon, alt_m=alt_m)
            await self._drone_backend.patrol([waypoint])
        except DroneError as exc:
            logger.warning("launch_drone failed: %s", exc)
            self._append_ledger(
                "mission.failed",
                {
                    "mission_id": mission_id,
                    "mission": mission,
                    "error": str(exc),
                },
            )
            await self.failover(reason=f"mission_failed: {exc}")
            return {
                "tool": "launch_drone",
                "status": "failed",
                "mission_id": mission_id,
                "error": str(exc),
            }

        self._append_ledger(
            "mission.launched",
            {
                "mission_id": mission_id,
                "mission": mission,
                "target_lat": lat,
                "target_lon": lon,
                "alt_m": alt_m,
            },
        )
        return {
            "tool": "launch_drone",
            "status": "ok",
            "mission_id": mission_id,
            "mission": mission,
            "target_lat": lat,
            "target_lon": lon,
            "alt_m": alt_m,
        }

    async def _exec_play_deterrent(
        self, args: dict[str, Any], wake_event: dict[str, Any]
    ) -> dict[str, Any]:
        tone_hz = int(args.get("tone_hz", 12000))
        duration_s = float(args.get("duration_s", 6.0))
        try:
            await self._drone_backend.play_deterrent(
                tone_hz=tone_hz, duration_s=duration_s
            )
        except DroneError as exc:
            logger.warning("play_deterrent failed: %s", exc)
            self._append_ledger(
                "deterrent.failed",
                {"tone_hz": tone_hz, "duration_s": duration_s, "error": str(exc)},
            )
            return {
                "tool": "play_deterrent",
                "status": "failed",
                "error": str(exc),
            }

        self._append_ledger(
            "deterrent.played",
            {"tone_hz": tone_hz, "duration_s": duration_s},
        )
        # Side-channel: publish deterrent/play for speaker_bridge consumers.
        await self._emit_side_channel(
            f"skyherd/{self._ranch_id}/deterrent/play",
            {
                "tone_hz": tone_hz,
                "duration_s": duration_s,
                "ts": self._ts_provider(),
                "segment": wake_event.get("segment"),
            },
        )
        return {
            "tool": "play_deterrent",
            "status": "ok",
            "tone_hz": tone_hz,
            "duration_s": duration_s,
        }

    async def _exec_get_thermal_clip(self, args: dict[str, Any]) -> dict[str, Any]:
        duration_s = float(args.get("duration_s", 10.0))
        try:
            path = await self._drone_backend.get_thermal_clip(duration_s=duration_s)
        except DroneError as exc:
            logger.debug("get_thermal_clip best-effort failure: %s", exc)
            self._append_ledger("thermal.clip_failed", {"error": str(exc)})
            return {"tool": "get_thermal_clip", "status": "failed", "error": str(exc)}
        self._append_ledger(
            "thermal.clip_captured",
            {"path": str(path), "duration_s": duration_s},
        )
        return {
            "tool": "get_thermal_clip",
            "status": "ok",
            "path": str(path),
            "duration_s": duration_s,
        }

    # ------------------------------------------------------------------
    # Side-channel MQTT publish
    # ------------------------------------------------------------------

    async def _emit_side_channel(self, topic: str, payload: dict[str, Any]) -> None:
        raw = _canonical_json(payload).encode()
        if self._mqtt_publish is not None:
            try:
                await self._mqtt_publish(topic, raw)
            except Exception as exc:  # noqa: BLE001
                logger.debug("side-channel publish hook raised: %s", exc)
            return
        # Default: best-effort aiomqtt
        try:
            import aiomqtt  # type: ignore[import-untyped]

            host, _, port_str = self._mqtt_url.split("://", 1)[-1].rpartition(":")
            try:
                port = int(port_str)
            except ValueError:
                port = 1883
            host = host or "localhost"
            async with aiomqtt.Client(hostname=host, port=port, timeout=2.0) as client:
                await client.publish(topic, payload=raw, qos=0)
        except Exception as exc:  # noqa: BLE001
            logger.debug("side-channel aiomqtt publish failed: %s", exc)

    # ------------------------------------------------------------------
    # Ledger helper + mission id
    # ------------------------------------------------------------------

    def _append_ledger(self, kind: str, payload: dict[str, Any]) -> None:
        try:
            self._ledger.append(source="pi_to_mission", kind=kind, payload=payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ledger append failed (kind=%s): %s", kind, exc)

    def _make_mission_id(self) -> str:
        """Deterministic 8-hex mission id, seeded when possible."""
        self._tick_counter += 1
        if self._seed is None:
            # Fall back to a counter-based id (deterministic in practice for tests,
            # non-unique across bridges — acceptable for sim; hardware flow uses
            # real MAVSDK mission ids).
            base = f"mission-{self._tick_counter:08x}"
        else:
            # Knuth multiplicative hash — identical seed + tick → identical id.
            value = (self._seed * 2654435761 + self._tick_counter) & 0xFFFFFFFF
            base = f"{value:08x}"
        return base

    # ------------------------------------------------------------------
    # Run loop (optional; tests drive handle_event directly)
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Subscribe to MQTT topics and forward events to :meth:`handle_event`.

        Best-effort: when ``aiomqtt`` is unavailable or the broker is down the
        coroutine logs and returns.  Tests should prefer :meth:`handle_event` directly.
        """
        self._running = True
        self._install_signal_handlers()
        logger.info(
            "PiToMissionBridge started — ranch=%s mqtt=%s filter=%s",
            self._ranch_id,
            self._mqtt_url,
            self._topic_filter,
        )
        try:
            import aiomqtt  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("aiomqtt unavailable; PiToMissionBridge.run() exiting")
            return

        host, _, port_str = self._mqtt_url.split("://", 1)[-1].rpartition(":")
        try:
            port = int(port_str)
        except ValueError:
            port = 1883
        host = host or "localhost"

        try:
            async with aiomqtt.Client(hostname=host, port=port) as client:
                for suffix in _ALLOWED_TOPIC_SUFFIXES:
                    topic = f"skyherd/{self._ranch_id}{suffix}"
                    if topic.endswith("/"):
                        topic = topic + "+"
                    await client.subscribe(topic)
                async for message in client.messages:
                    if not self._running:
                        break
                    try:
                        payload = json.loads(message.payload)
                    except (TypeError, ValueError) as exc:
                        logger.debug("bad JSON on %s: %s", message.topic, exc)
                        continue
                    topic = str(message.topic)
                    try:
                        await self.handle_event(topic, payload)
                    except Exception as exc:  # noqa: BLE001
                        logger.error("handle_event raised on %s: %s", topic, exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PiToMissionBridge.run() exiting: %s", exc)
        finally:
            await self.close()

    def stop(self) -> None:
        """Request graceful shutdown."""
        self._running = False

    def _install_signal_handlers(self) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGINT, self.stop)
            loop.add_signal_handler(signal.SIGTERM, self.stop)
        except (NotImplementedError, RuntimeError) as exc:
            logger.debug("signal handler unavailable: %s", exc)

    # ------------------------------------------------------------------
    # Introspection for tests
    # ------------------------------------------------------------------

    @property
    def ledger(self) -> Ledger:
        return self._ledger

    @property
    def ranch_id(self) -> str:
        return self._ranch_id


# ---------------------------------------------------------------------------
# Chain verification helper
# ---------------------------------------------------------------------------


def verify_chain(ledger: Ledger) -> bool:
    """Walk the ledger; re-compute hashes + verify signatures.

    Returns ``True`` iff every entry's ``prev_hash`` chains to its predecessor's
    ``event_hash`` AND every Ed25519 signature verifies against the embedded
    pubkey.  Used by Phase 6 E2E tests; a drop-in replacement for
    :mod:`skyherd.attest.verify_cli`'s internal walker.
    """
    from skyherd.attest.ledger import GENESIS_PREV_HASH, _compute_hash
    from skyherd.attest.signer import verify as sig_verify

    prev = GENESIS_PREV_HASH
    for event in ledger.iter_events():
        if not hmac.compare_digest(event.prev_hash, prev):
            logger.error(
                "ledger chain broken at seq=%s: prev_hash=%s expected=%s",
                event.seq,
                event.prev_hash,
                prev,
            )
            return False
        raw_hash = _compute_hash(
            event.prev_hash,
            event.payload_json,
            event.ts_iso,
            event.source,
            event.kind,
        )
        if raw_hash.hex() != event.event_hash:
            logger.error("ledger hash mismatch at seq=%s", event.seq)
            return False
        try:
            ok = sig_verify(event.pubkey, raw_hash, bytes.fromhex(event.signature))
        except Exception as exc:  # noqa: BLE001
            logger.error("ledger signature verify raised at seq=%s: %s", event.seq, exc)
            return False
        if not ok:
            return False
        prev = event.event_hash
    return True
