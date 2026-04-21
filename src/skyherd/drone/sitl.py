"""
SitlBackend — ArduPilot SITL via MAVSDK-Python.

Connects to a local SITL instance on UDP port 14540 (standard ArduPilot
default).  Start the simulator with ``make sitl-up`` before using this backend.

Event log rows are written to ``runtime/drone_events.jsonl``.
Synthetic thermal frames are written to ``runtime/thermal/{ts}.png``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from skyherd.drone.interface import DroneBackend, DroneState, DroneUnavailable, Waypoint

logger = logging.getLogger(__name__)

_SITL_ADDRESS = "udpin://0.0.0.0:14540"
_CONNECT_TIMEOUT_S = 30.0
_EVENTS_PATH = Path("runtime/drone_events.jsonl")
_THERMAL_DIR = Path("runtime/thermal")


def _ensure_runtime_dirs() -> None:
    _EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _THERMAL_DIR.mkdir(parents=True, exist_ok=True)


def _append_event(event: dict) -> None:
    _ensure_runtime_dirs()
    with _EVENTS_PATH.open("a") as fh:
        fh.write(json.dumps(event) + "\n")


class SitlBackend(DroneBackend):
    """
    Drone backend that talks to ArduPilot SITL via MAVSDK.

    All public methods are coroutines; call ``await backend.connect()``
    before any other method.

    Raises :class:`~skyherd.drone.interface.DroneUnavailable` if the SITL
    process is not reachable within :py:data:`_CONNECT_TIMEOUT_S` seconds.
    """

    def __init__(self) -> None:
        self._drone: mavsdk.System | None = None  # type: ignore[name-defined]
        self._connected = False

    # ------------------------------------------------------------------
    # DroneBackend implementation
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        try:
            import mavsdk  # noqa: PLC0415
        except ImportError as exc:
            raise DroneUnavailable("mavsdk package not installed — run `uv add mavsdk`") from exc

        drone = mavsdk.System()
        try:
            await drone.connect(system_address=_SITL_ADDRESS)
        except Exception as exc:
            raise DroneUnavailable(
                f"Cannot connect to SITL at {_SITL_ADDRESS}: {exc}\n"
                "Hint: run `make sitl-up` to start the ArduPilot SITL container."
            ) from exc

        # Wait for physical connection acknowledgement.
        deadline = time.monotonic() + _CONNECT_TIMEOUT_S
        try:
            async for state in drone.core.connection_state():
                if state.is_connected:
                    break
                if time.monotonic() > deadline:
                    raise DroneUnavailable(
                        f"SITL did not connect within {_CONNECT_TIMEOUT_S:.0f} s. "
                        "Hint: run `make sitl-up`."
                    )
        except Exception as exc:
            if isinstance(exc, DroneUnavailable):
                raise
            raise DroneUnavailable(f"Error while waiting for SITL connection: {exc}") from exc

        # Wait for GPS fix before declaring ready.
        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                break

        self._drone = drone
        self._connected = True
        logger.info("SitlBackend connected to %s", _SITL_ADDRESS)
        _append_event({"ts": time.time(), "event": "connected", "address": _SITL_ADDRESS})

    async def takeoff(self, alt_m: float = 30.0) -> None:
        drone = self._assert_connected()
        await drone.action.set_takeoff_altitude(alt_m)
        await drone.action.arm()
        await drone.action.takeoff()

        # Wait until airborne.
        async for in_air in drone.telemetry.in_air():
            if in_air:
                break

        logger.info("SitlBackend airborne at %.1f m AGL", alt_m)
        _append_event({"ts": time.time(), "event": "takeoff", "alt_m": alt_m})

    async def patrol(self, waypoints: list[Waypoint]) -> None:
        drone = self._assert_connected()

        if not waypoints:
            logger.warning("SitlBackend patrol called with no waypoints — skipping")
            return

        try:
            from mavsdk.mission import MissionItem, MissionPlan  # noqa: PLC0415
        except ImportError as exc:
            raise DroneUnavailable("mavsdk.mission not available") from exc

        mission_items = [
            MissionItem(
                latitude_deg=wp.lat,
                longitude_deg=wp.lon,
                relative_altitude_m=wp.alt_m,
                speed_m_s=10.0,
                is_fly_through=wp.hold_s == 0.0,
                gimbal_pitch_deg=float("nan"),
                gimbal_yaw_deg=float("nan"),
                camera_action=MissionItem.CameraAction.NONE,
                loiter_time_s=wp.hold_s if wp.hold_s > 0 else float("nan"),
                camera_photo_interval_s=float("nan"),
                acceptance_radius_m=float("nan"),
                yaw_deg=float("nan"),
                camera_photo_distance_m=float("nan"),
                vehicle_action=MissionItem.VehicleAction.NONE,
            )
            for wp in waypoints
        ]

        plan = MissionPlan(mission_items)
        await drone.mission.set_return_to_launch_after_mission(False)
        await drone.mission.upload_mission(plan)
        await drone.mission.start_mission()

        # Wait for mission completion.
        async for progress in drone.mission.mission_progress():
            logger.debug("Mission progress: %d/%d", progress.current, progress.total)
            if progress.current == progress.total and progress.total > 0:
                break

        _append_event(
            {
                "ts": time.time(),
                "event": "patrol_complete",
                "waypoints": [wp.model_dump() for wp in waypoints],
            }
        )

    async def return_to_home(self) -> None:
        drone = self._assert_connected()
        await drone.action.return_to_launch()

        # Wait until on the ground.
        async for in_air in drone.telemetry.in_air():
            if not in_air:
                break

        await drone.action.disarm()
        logger.info("SitlBackend returned to home and disarmed")
        _append_event({"ts": time.time(), "event": "return_to_home"})

    async def play_deterrent(self, tone_hz: int = 12000, duration_s: float = 6.0) -> None:
        self._assert_connected()
        current = await self.state()

        event: dict = {
            "ts": time.time(),
            "event": "deterrent",
            "tone_hz": tone_hz,
            "duration_s": duration_s,
            "in_air": current.in_air,
            "lat": current.lat,
            "lon": current.lon,
            "alt_m": current.altitude_m,
        }

        if current.in_air:
            # In the air: log + simulate an 8-s hold at current position.
            logger.info(
                "SitlBackend deterrent (airborne) %.0f Hz for %.1f s — 8s hold",
                tone_hz,
                duration_s,
            )
            await asyncio.sleep(8.0)
        else:
            # On the ground: play audio (stubbed — logs intent).
            logger.info(
                "SitlBackend deterrent (ground) %.0f Hz for %.1f s",
                tone_hz,
                duration_s,
            )
            await asyncio.sleep(duration_s)

        _append_event(event)

    async def get_thermal_clip(self, duration_s: float = 10.0) -> Path:
        self._assert_connected()
        _ensure_runtime_dirs()

        ts = int(time.time())
        out_path = _THERMAL_DIR / f"{ts}.png"

        try:
            _generate_synthetic_thermal(out_path)
        except Exception as exc:
            logger.error("Failed to generate synthetic thermal frame: %s", exc)
            raise

        _append_event({"ts": time.time(), "event": "thermal_clip", "path": str(out_path)})
        logger.info("SitlBackend synthetic thermal frame saved to %s", out_path)
        return out_path

    async def state(self) -> DroneState:
        drone = self._assert_connected()

        armed = False
        in_air = False
        alt_m = 0.0
        battery_pct = 100.0
        mode = "UNKNOWN"
        lat = 0.0
        lon = 0.0

        try:
            async for is_armed in drone.telemetry.armed():
                armed = is_armed
                break
        except Exception:
            pass

        try:
            async for is_in_air in drone.telemetry.in_air():
                in_air = is_in_air
                break
        except Exception:
            pass

        try:
            async for pos in drone.telemetry.position():
                lat = pos.latitude_deg
                lon = pos.longitude_deg
                alt_m = pos.relative_altitude_m
                break
        except Exception:
            pass

        try:
            async for bat in drone.telemetry.battery():
                battery_pct = bat.remaining_percent * 100.0
                break
        except Exception:
            pass

        try:
            async for fm in drone.telemetry.flight_mode():
                mode = str(fm)
                break
        except Exception:
            pass

        return DroneState(
            armed=armed,
            in_air=in_air,
            altitude_m=alt_m,
            battery_pct=battery_pct,
            mode=mode,
            lat=lat,
            lon=lon,
        )

    async def disconnect(self) -> None:
        self._drone = None
        self._connected = False
        logger.info("SitlBackend disconnected")
        _append_event({"ts": time.time(), "event": "disconnected"})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assert_connected(self) -> mavsdk.System:  # type: ignore[name-defined]
        if not self._connected or self._drone is None:
            raise DroneUnavailable(
                "SitlBackend not connected — call connect() first.\n"
                "Hint: run `make sitl-up` to start the ArduPilot SITL container."
            )
        return self._drone


# ---------------------------------------------------------------------------
# Synthetic thermal frame generator
# ---------------------------------------------------------------------------


def _generate_synthetic_thermal(path: Path, width: int = 480, height: int = 360) -> None:
    """
    Write a 480x360 greyscale PNG simulating an IR thermal frame.

    A Gaussian blob at the image centre represents a warm target (animal /
    predator).  Cool background is ~40 DN; blob peak is ~220 DN.
    """
    try:
        import numpy as np  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError("Pillow and numpy are required for thermal frame synthesis") from exc

    # Background — cool scene noise.
    rng = np.random.default_rng(seed=int(time.time()) % 2**32)
    frame = rng.normal(loc=40, scale=3, size=(height, width)).astype(np.float32)

    # Gaussian blob — warm target near centre with slight random offset.
    cx = width // 2 + int(rng.integers(-40, 40))
    cy = height // 2 + int(rng.integers(-30, 30))
    sigma = 35.0

    yy, xx = np.mgrid[0:height, 0:width]
    blob = 180.0 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma**2))
    frame = np.clip(frame + blob, 0, 255).astype(np.uint8)

    img = Image.fromarray(frame, mode="L")
    img.save(path)
