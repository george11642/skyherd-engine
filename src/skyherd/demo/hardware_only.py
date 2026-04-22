"""HardwareOnlyDemo — 2-Pi + Mavic Air 2 hybrid demo orchestrator.

Architecture
------------
* Sim world boots with all 4 non-hero scenarios (water_drop, calving, storm,
  sick_cow optional) running in background.
* ``HARDWARE_OVERRIDES`` suppresses sim trough_cam emitters for trough_1 and
  trough_2 so the real Pi nodes own those topics.
* The orchestrator subscribes to the Pi-owned trough_cam topics.  When a
  coyote detection payload arrives, it fires FenceLineDispatcher which
  commands the real Mavic via MavicBackend (or SITL if DRONE_BACKEND != mavic).
* Wes voice: real Twilio call if TWILIO_SID in env, else .wav + dashboard ring.
* Timeout guard: 180 s.  No real Pi detection → PROP_NOT_DETECTED logged, sim
  coyote scenario runs as fallback so the demo ends cleanly.
* All events written to runtime/hardware_demo_runs/{ts}.jsonl + attestation
  ledger.

Environment variables
---------------------
ANTHROPIC_API_KEY    — enables real Claude SDK calls; absent = sim path
DRONE_BACKEND        — "mavic" (real) | "sitl" (default) | "stub" (tests)
MAVIC_WS_URL         — ws://192.168.x.x:8765  (companion app WebSocket)
HARDWARE_OVERRIDES   — trough_cam:trough_1:edge-fence,trough_cam:trough_2:edge-barn
TWILIO_SID           — Twilio Account SID for real Wes call
TWILIO_TOKEN         — Twilio Auth Token
TWILIO_FROM_NUMBER   — Twilio caller number (+1...)
TWILIO_TO_NUMBER     — George's phone number (+1...)
MQTT_URL             — mqtt://host:1883 (defaults to embedded broker)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Top-level imports — required at module level so that tests can patch
# via "skyherd.demo.hardware_only.<name>" without AttributeError.
from skyherd.drone.interface import DroneError, DroneUnavailable, Waypoint, get_backend
from skyherd.scenarios.base import _run_async
from skyherd.sensors.bus import SensorBus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_WORLD_CONFIG = _REPO_ROOT / "worlds" / "ranch_a.yaml"
_RUNS_DIR = _REPO_ROOT / "runtime" / "hardware_demo_runs"

_DEFAULT_HW_OVERRIDES = "trough_cam:trough_1:edge-fence,trough_cam:trough_2:edge-barn"
_DETECTION_TIMEOUT_S = 180.0
_COYOTE_DETECTION_KEYWORDS = {"coyote", "predator", "animal"}


# ---------------------------------------------------------------------------
# DemoRun result dataclass
# ---------------------------------------------------------------------------


@dataclass
class DemoRunResult:
    """Captures the output of one hardware demo run."""

    prop: str
    started_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    hardware_detection_received: bool = False
    hardware_detection_ts: float | None = None
    drone_launched: bool = False
    wes_called: bool = False
    fallback_used: bool = False
    fallback_reason: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    jsonl_path: Path | None = None


# ---------------------------------------------------------------------------
# Hardware demo orchestrator
# ---------------------------------------------------------------------------


class HardwareOnlyDemo:
    """Orchestrates the 2-Pi + Mavic Air 2 hardware demo.

    Usage::

        demo = HardwareOnlyDemo(prop="combo")
        result = await demo.run()
    """

    def __init__(
        self,
        prop: str = "combo",
        timeout_s: float = _DETECTION_TIMEOUT_S,
        hw_overrides_str: str | None = None,
    ) -> None:
        self.prop = prop
        self.timeout_s = timeout_s
        self._hw_overrides_str = hw_overrides_str or os.environ.get(
            "HARDWARE_OVERRIDES", _DEFAULT_HW_OVERRIDES
        )
        self._result = DemoRunResult(prop=prop)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self) -> DemoRunResult:
        """Boot the sim, wait for hardware events, drive drone + Wes."""
        _RUNS_DIR.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%H:%M:%S",
        )
        logger.info("HardwareOnlyDemo starting — prop=%s", self.prop)
        logger.info("Hardware overrides: %s", self._hw_overrides_str)

        # Override env so registry.run_all picks them up
        os.environ["HARDWARE_OVERRIDES"] = self._hw_overrides_str

        try:
            await self._orchestrate()
        except Exception as exc:  # noqa: BLE001
            logger.error("HardwareOnlyDemo fatal error: %s", exc, exc_info=True)
            self._result.fallback_reason = f"fatal_error: {exc}"
        finally:
            self._write_jsonl()

        return self._result

    # ------------------------------------------------------------------
    # Orchestration core
    # ------------------------------------------------------------------

    async def _orchestrate(self) -> None:
        from skyherd.sensors.registry import parse_overrides
        from skyherd.world.world import make_world

        hw_overrides = parse_overrides(self._hw_overrides_str)
        world = make_world(seed=42, config_path=_WORLD_CONFIG)

        # Boot background sim scenarios
        sim_tasks = await self._boot_background_sim(world)

        try:
            if self.prop in ("coyote", "combo"):
                await self._run_coyote_prop(world, hw_overrides)
            if self.prop in ("sick-cow", "combo"):
                await self._run_sick_cow_prop(world)
        finally:
            for t in sim_tasks:
                t.cancel()
            await asyncio.gather(*sim_tasks, return_exceptions=True)

    async def _boot_background_sim(self, world: Any) -> list[asyncio.Task[Any]]:
        """Start background sim scenarios (water_drop, calving, storm)."""
        tasks: list[asyncio.Task[Any]] = []
        try:
            from skyherd.scenarios.calving import CalvingScenario
            from skyherd.scenarios.storm import StormScenario
            from skyherd.scenarios.water_drop import WaterDropScenario

            for scenario_cls in (WaterDropScenario, CalvingScenario, StormScenario):
                scenario = scenario_cls()
                scenario.setup(world)
                task = asyncio.create_task(
                    _run_sim_scenario_background(scenario, world),
                    name=f"bg_sim_{scenario.name}",
                )
                tasks.append(task)
                logger.info("Background sim started: %s", scenario.name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Background sim boot partial: %s", exc)
        return tasks

    # ------------------------------------------------------------------
    # Coyote hero prop
    # ------------------------------------------------------------------

    async def _run_coyote_prop(
        self,
        world: Any,
        hw_overrides: dict[str, dict[str, str]],
    ) -> None:
        """Wait for Pi coyote detection → dispatch drone → Wes call."""
        logger.info("Coyote prop: waiting up to %.0fs for Pi detection…", self.timeout_s)

        detection = await self._wait_for_pi_detection(
            topic_pattern="skyherd/+/trough_cam/+",
            timeout_s=self.timeout_s,
            keywords=_COYOTE_DETECTION_KEYWORDS,
        )

        if detection is None:
            await self._fallback_coyote_sim(world)
            return

        self._result.hardware_detection_received = True
        self._result.hardware_detection_ts = detection.get("ts", time.time())
        self._record_event({"type": "hw_detection", **detection})
        logger.info("Pi detection received: %s", detection)

        # Fire FenceLineDispatcher
        wake_event = {
            "type": "fence.breach",
            "segment": detection.get("entity", "trough_1"),
            "lat": detection.get("lat", 34.1230),
            "lon": detection.get("lon", -106.4560),
            "ranch_id": detection.get("ranch", "ranch_a"),
            "species_hint": "coyote",
            "source": "pi_hardware",
        }
        tool_calls = await self._fire_fenceline_dispatcher(wake_event)
        self._result.tool_calls.extend(tool_calls)

        # Launch drone
        launched = await self._launch_drone(
            lat=wake_event["lat"],
            lon=wake_event["lon"],
        )
        self._result.drone_launched = launched

        # Wes call
        await self._wes_call(
            urgency="call",
            message=(
                f"Boss. Coyote at the south fence. Drone's on it. Segment: {wake_event['segment']}."
            ),
        )
        self._result.wes_called = True

    async def _fallback_coyote_sim(self, world: Any) -> None:  # noqa: ARG002
        """180s elapsed without Pi detection — run sim coyote scenario."""
        logger.warning(
            "PROP_NOT_DETECTED: no Pi detection after %.0fs — falling back to sim",
            self.timeout_s,
        )
        self._result.fallback_used = True
        self._result.fallback_reason = "PROP_NOT_DETECTED"
        self._record_event(
            {
                "type": "fallback_triggered",
                "reason": "PROP_NOT_DETECTED",
                "ts": time.time(),
            }
        )

        try:
            from skyherd.scenarios.coyote import CoyoteScenario

            scenario = CoyoteScenario()
            result = await _run_async(scenario, seed=42)
            self._result.tool_calls.extend(
                [{"agent": k, **c} for k, calls in result.agent_tool_calls.items() for c in calls]
            )
            self._result.drone_launched = any(
                c.get("tool") == "launch_drone" for c in self._result.tool_calls
            )
            logger.info(
                "Sim fallback complete — %d tool calls, outcome=%s",
                len(self._result.tool_calls),
                result.outcome_passed,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Sim fallback failed: %s", exc)

    # ------------------------------------------------------------------
    # Sick cow secondary prop
    # ------------------------------------------------------------------

    async def _run_sick_cow_prop(self, world: Any) -> None:  # noqa: ARG002
        """Run sick-cow scenario (sim-driven, Pi #2 provides frame if available)."""
        logger.info("Sick-cow prop: running health check cascade…")
        try:
            from skyherd.scenarios.sick_cow import SickCowScenario

            scenario = SickCowScenario()
            result = await _run_async(scenario, seed=42)
            self._result.tool_calls.extend(
                [{"agent": k, **c} for k, calls in result.agent_tool_calls.items() for c in calls]
            )
            page_calls = [c for c in self._result.tool_calls if c.get("tool") == "page_rancher"]
            if page_calls and not self._result.wes_called:
                await self._wes_call(
                    urgency="log",
                    message=(
                        "Boss. A014's got something in her left eye. "
                        "I pulled together a vet packet; take a look when you can."
                    ),
                )
                self._result.wes_called = True
            logger.info("Sick-cow prop complete — outcome=%s", result.outcome_passed)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sick-cow prop error: %s", exc)

    # ------------------------------------------------------------------
    # MQTT listener for Pi detections
    # ------------------------------------------------------------------

    async def _wait_for_pi_detection(
        self,
        topic_pattern: str,
        timeout_s: float,
        keywords: set[str],
    ) -> dict[str, Any] | None:
        """Subscribe to MQTT and wait for a payload containing any keyword.

        Returns the payload dict on match, or None on timeout.
        """
        bus = SensorBus()
        try:
            await bus.start()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Bus start failed (embedded broker may already be up): %s", exc)

        deadline = time.monotonic() + timeout_s
        try:
            async with bus.subscribe(topic_pattern) as messages:
                async for _topic, payload in messages:
                    if time.monotonic() > deadline:
                        break
                    payload_str = json.dumps(payload).lower()
                    if any(kw in payload_str for kw in keywords):
                        return payload
                    # Also accept any payload from an edge node (has "edge_id" key)
                    if "edge_id" in payload or payload.get("source") == "pi_hardware":
                        return payload
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
        except TimeoutError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("MQTT subscription error: %s", exc)
        finally:
            try:
                await asyncio.wait_for(bus.stop(), timeout=3.0)
            except Exception:  # noqa: BLE001
                pass

        return None

    # ------------------------------------------------------------------
    # Drone dispatch
    # ------------------------------------------------------------------

    async def _launch_drone(self, lat: float, lon: float) -> bool:
        """Connect drone backend and execute takeoff + patrol + deterrent."""
        backend_name = os.environ.get("DRONE_BACKEND", "sitl")
        logger.info("Launching drone via backend=%s", backend_name)

        try:
            backend = get_backend(backend_name)
            await backend.connect()
            await backend.takeoff(alt_m=30.0)
            await backend.patrol([Waypoint(lat=lat, lon=lon, alt_m=30.0, hold_s=5.0)])
            await backend.play_deterrent(tone_hz=14000, duration_s=6.0)
            await backend.return_to_home()
            await backend.disconnect()

            self._record_event(
                {
                    "type": "drone_mission_complete",
                    "backend": backend_name,
                    "lat": lat,
                    "lon": lon,
                    "ts": time.time(),
                }
            )
            logger.info("Drone mission complete — backend=%s", backend_name)
            return True

        except (DroneUnavailable, DroneError) as exc:
            logger.warning(
                "Drone backend %r unavailable (%s) — falling back to SITL for video",
                backend_name,
                exc,
            )
            # Retry with SITL so demo still shows visual
            if backend_name != "sitl":
                return await self._launch_drone_sitl(lat, lon)
            self._record_event(
                {"type": "drone_launch_failed", "error": str(exc), "ts": time.time()}
            )
            return False

    async def _launch_drone_sitl(self, lat: float, lon: float) -> bool:
        """SITL fallback when Mavic is unavailable."""
        try:
            from skyherd.drone.sitl import SitlBackend

            backend = SitlBackend()
            await backend.connect()
            await backend.takeoff(alt_m=30.0)
            await backend.patrol([Waypoint(lat=lat, lon=lon, alt_m=30.0, hold_s=5.0)])
            await backend.play_deterrent(tone_hz=14000, duration_s=6.0)
            await backend.return_to_home()
            await backend.disconnect()
            self._record_event(
                {"type": "drone_sitl_fallback_complete", "lat": lat, "lon": lon, "ts": time.time()}
            )
            return True
        except (DroneUnavailable, DroneError) as exc:
            logger.warning("SITL fallback also failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # FenceLineDispatcher
    # ------------------------------------------------------------------

    async def _fire_fenceline_dispatcher(self, wake_event: dict[str, Any]) -> list[dict[str, Any]]:
        """Drive FenceLineDispatcher handler; return tool call list."""
        try:
            from skyherd.agents.fenceline_dispatcher import (
                FENCELINE_DISPATCHER_SPEC,
                handler,
            )
            from skyherd.agents.session import SessionManager

            manager = SessionManager()
            session = manager.create_session(FENCELINE_DISPATCHER_SPEC)
            manager.wake(session.id, wake_event)

            sdk_client = _build_sdk_client()
            calls = await handler(session, wake_event, sdk_client=sdk_client)
            manager.sleep(session.id)

            self._record_event(
                {
                    "type": "fenceline_dispatcher_fired",
                    "tool_calls": calls,
                    "ts": time.time(),
                }
            )
            return calls
        except Exception as exc:  # noqa: BLE001
            logger.warning("FenceLineDispatcher error: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Wes voice call
    # ------------------------------------------------------------------

    async def _wes_call(self, urgency: str, message: str) -> None:
        """Page rancher via Twilio (real) or dashboard-ring + .wav (fallback)."""
        twilio_sid = os.environ.get("TWILIO_SID", "")
        if twilio_sid:
            await self._wes_twilio(urgency, message)
        else:
            await self._wes_dashboard_ring(urgency, message)

    async def _wes_twilio(self, urgency: str, message: str) -> None:
        """Real Twilio voice call via TTS + Twilio REST."""
        try:
            from skyherd.voice.tts import get_backend as get_tts_backend
            from skyherd.voice.wes import WesMessage, wes_script

            wes_msg = WesMessage(urgency=urgency, subject=message)  # type: ignore[call-arg]
            script = wes_script(wes_msg)
            tts = get_tts_backend()
            wav_path = tts.synthesize(script, voice="wes")

            twilio_token = os.environ.get("TWILIO_TOKEN", "")
            twilio_sid = os.environ.get("TWILIO_SID", "")
            from_num = os.environ.get("TWILIO_FROM_NUMBER", "")
            to_num = os.environ.get("TWILIO_TO_NUMBER", "")
            if twilio_sid and twilio_token and from_num and to_num:
                try:
                    from twilio.rest import Client as TwilioClient  # type: ignore[import-untyped]

                    client = TwilioClient(twilio_sid, twilio_token)
                    twiml = f"<Response><Play>{wav_path.as_posix()}</Play></Response>"
                    client.calls.create(twiml=twiml, to=to_num, from_=from_num)
                    logger.info("Twilio call placed to %s — urgency=%s", to_num, urgency)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Twilio call failed: %s", exc)

            self._record_event(
                {
                    "type": "wes_call_placed",
                    "urgency": urgency,
                    "message": message,
                    "wav_path": str(wav_path),
                    "ts": time.time(),
                }
            )
            logger.info("Wes Twilio path complete — urgency=%s", urgency)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Wes Twilio call failed: %s — falling back to dashboard ring", exc)
            await self._wes_dashboard_ring(urgency, message)

    async def _wes_dashboard_ring(self, urgency: str, message: str) -> None:
        """Write .wav via TTS backend + emit dashboard phone-ring event."""
        _RUNS_DIR.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        wav_path: Path = _RUNS_DIR / f"wes_{ts}.wav"

        try:
            from skyherd.voice.tts import get_backend as get_tts_backend

            tts = get_tts_backend()
            wav_path = tts.synthesize(message, voice="wes")
            logger.info("Wes .wav written: %s", wav_path)
        except Exception as exc:  # noqa: BLE001
            logger.debug("TTS render failed (wav not written): %s", exc)

        self._record_event(
            {
                "type": "wes_dashboard_ring",
                "urgency": urgency,
                "message": message,
                "wav_path": str(wav_path),
                "ts": float(ts),
            }
        )
        logger.info("Dashboard phone-ring emitted — urgency=%s", urgency)

    # ------------------------------------------------------------------
    # JSONL output
    # ------------------------------------------------------------------

    def _record_event(self, event: dict[str, Any]) -> None:
        self._result.events.append(event)

    def _write_jsonl(self) -> None:
        ts = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S")
        path = _RUNS_DIR / f"hw_demo_{self._result.prop}_{ts}.jsonl"
        try:
            with path.open("w", encoding="utf-8") as fh:
                header = {
                    "record": "hardware_demo_header",
                    "prop": self._result.prop,
                    "started_at": self._result.started_at,
                    "hardware_detection_received": self._result.hardware_detection_received,
                    "drone_launched": self._result.drone_launched,
                    "wes_called": self._result.wes_called,
                    "fallback_used": self._result.fallback_used,
                    "fallback_reason": self._result.fallback_reason,
                }
                fh.write(json.dumps(header) + "\n")
                for ev in self._result.events:
                    fh.write(json.dumps({"record": "event", **ev}) + "\n")
                for tc in self._result.tool_calls:
                    fh.write(json.dumps({"record": "tool_call", **tc}) + "\n")
            self._result.jsonl_path = path
            logger.info("Demo run written to %s", path)
        except OSError as exc:
            logger.error("Failed to write demo JSONL: %s", exc)


# ---------------------------------------------------------------------------
# Background sim helper
# ---------------------------------------------------------------------------


async def _run_sim_scenario_background(scenario: Any, world: Any) -> None:
    """Run a sim scenario's inject_events loop in the background (fire-and-forget)."""
    from skyherd.scenarios.base import _STEP_DT

    elapsed = 0.0
    try:
        while elapsed < scenario.duration_s:
            await asyncio.sleep(_STEP_DT)
            world.step(_STEP_DT)
            scenario.inject_events(world, elapsed)
            elapsed += _STEP_DT
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# SDK client factory
# ---------------------------------------------------------------------------


def _build_sdk_client() -> Any:
    """Return a real SDK client if ANTHROPIC_API_KEY is set, else None (sim path)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        from claude_agent_sdk import ClaudeSDKClient  # type: ignore[import]

        return ClaudeSDKClient()
    except Exception as exc:  # noqa: BLE001
        logger.warning("SDK client build failed: %s — using sim path", exc)
        return None
