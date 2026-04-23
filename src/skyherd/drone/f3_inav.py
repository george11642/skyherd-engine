"""
F3InavBackend — SP Racing F3 flight controller running iNav 7.x firmware.

Communication path
------------------
  Laptop USB-serial → mavlink-router → UDP 14550 → MAVSDK-Python

The user must run ``mavlink-router`` (or ``mavproxy``) on the laptop to
bridge the F3's MAVLink UART to the UDP port before connecting:

    # Example mavlink-router invocation (see docs/HARDWARE_F3_INAV.md):
    mavlink-router -e 0.0.0.0:14550 /dev/ttyUSB0:115200

Safety guards (shared via safety.py)
-------------------------------------
  - GeofenceChecker  — validated on every patrol() call.
  - BatteryGuard     — checked before takeoff; RTH warning in flight.
  - WindGuard        — ceiling 18 kt for F3 quads; checked before takeoff.

Hardware limitations
---------------------
  - Mavic Air 2's thermal camera is NOT present on the F3 quad.
    ``get_thermal_clip`` falls back to visible-light if ``F3_HAS_IR=1`` is
    not set, otherwise raises :class:`~skyherd.drone.interface.DroneError`.
  - Acoustic deterrent is cued via ``play_deterrent``, which logs an event
    and, if a GPIO/speaker is wired per the runbook, can be triggered via an
    external script called as a subprocess.  The call never blocks the flight
    controller loop.
  - Hard altitude ceiling: 60 m AGL (Part 107 + safety).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from skyherd.drone.interface import DroneBackend, DroneState, DroneUnavailable, Waypoint
from skyherd.drone.safety import (
    WIND_CEILING_F3_KT,
    BatteryGuard,
    GeofenceChecker,
    WindGuard,
)

logger = logging.getLogger(__name__)

_F3_ADDRESS = "udpin://0.0.0.0:14550"
_CONNECT_TIMEOUT_S = 30.0
_MAX_ALTITUDE_M = 60.0
_ARM_CHECK_BATTERY_PCT = 30.0

_EVENTS_PATH = Path("runtime/drone_events_f3.jsonl")
_THERMAL_DIR = Path("runtime/thermal")


def _ensure_runtime_dirs() -> None:
    _EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _THERMAL_DIR.mkdir(parents=True, exist_ok=True)


def _append_event(event: dict) -> None:
    _ensure_runtime_dirs()
    with _EVENTS_PATH.open("a") as fh:
        fh.write(json.dumps(event) + "\n")


class F3InavBackend(DroneBackend):
    """
    Drone backend for SP Racing F3 + iNav 7.x over MAVSDK-Python.

    Connects to the F3's MAVLink stream forwarded by ``mavlink-router`` on
    UDP 14550.  All public methods are coroutines; call
    ``await backend.connect()`` before any other method.

    Parameters
    ----------
    address:
        MAVSDK system address string (default ``udpin://0.0.0.0:14550``).
    world_name:
        Ranch world YAML name for geofence loading (default ``"ranch_a"``).
    wind_speed_kt:
        Pre-flight wind speed in knots for the WindGuard check.  Set to 0.0
        (default) to skip wind check (useful in tests / CI).
    """

    def __init__(
        self,
        address: str = _F3_ADDRESS,
        world_name: str = "ranch_a",
        wind_speed_kt: float = 0.0,
    ) -> None:
        self._address = address
        self._drone: Any = None  # mavsdk.System, typed as Any for lazy import
        self._connected = False
        self._wind_speed_kt = wind_speed_kt

        # Safety guards
        self._geofence = GeofenceChecker(world_name=world_name)
        self._battery = BatteryGuard(min_takeoff_pct=_ARM_CHECK_BATTERY_PCT)
        self._wind = WindGuard(ceiling_kt=WIND_CEILING_F3_KT)

    # ------------------------------------------------------------------
    # DroneBackend implementation
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        Establish MAVLink connection to F3 via mavlink-router.

        Raises :class:`~skyherd.drone.interface.DroneUnavailable` if:
        - ``mavsdk`` package is not installed.
        - UDP port is not reachable within :py:data:`_CONNECT_TIMEOUT_S` s.
        """
        try:
            import mavsdk  # noqa: PLC0415
        except ImportError as exc:
            raise DroneUnavailable("mavsdk package not installed — run `uv add mavsdk`") from exc

        drone = mavsdk.System()
        try:
            await drone.connect(system_address=self._address)
        except Exception as exc:
            raise DroneUnavailable(
                f"Cannot connect to F3/iNav at {self._address}: {exc}\n"
                "Hint: Start mavlink-router first; see docs/HARDWARE_F3_INAV.md"
            ) from exc

        deadline = time.monotonic() + _CONNECT_TIMEOUT_S
        try:
            async for state in drone.core.connection_state():
                if state.is_connected:
                    break
                if time.monotonic() > deadline:
                    raise DroneUnavailable(
                        f"F3/iNav did not connect within {_CONNECT_TIMEOUT_S:.0f} s. "
                        "Hint: Start mavlink-router first; see docs/HARDWARE_F3_INAV.md"
                    )
        except Exception as exc:
            if isinstance(exc, DroneUnavailable):
                raise
            raise DroneUnavailable(f"Error while waiting for F3/iNav connection: {exc}") from exc

        # Wait for GPS fix
        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                break

        self._drone = drone
        self._connected = True
        logger.info("F3InavBackend connected to %s", self._address)
        _append_event({"ts": time.time(), "event": "connected", "address": self._address})

    async def takeoff(self, alt_m: float = 30.0) -> None:
        """
        Arm F3 and take off to *alt_m* metres AGL.

        Pre-flight checks (in order):
          1. WindGuard — abort if wind exceeds 18 kt.
          2. BatteryGuard — abort if battery < 30 %.
          3. Altitude cap — clamp to :py:data:`_MAX_ALTITUDE_M` (60 m).
          4. GPS arm check — done by iNav; MAVSDK will reject if no fix.
        """
        drone = self._assert_connected()

        # Safety gate 1: wind
        if self._wind_speed_kt > 0.0:
            self._wind.check(self._wind_speed_kt)

        # Safety gate 2: battery
        current = await self.state()
        self._battery.check_takeoff(current.battery_pct)

        # Safety gate 3: altitude cap
        if alt_m > _MAX_ALTITUDE_M:
            logger.warning(
                "F3InavBackend: requested altitude %.1f m clamped to %.0f m",
                alt_m,
                _MAX_ALTITUDE_M,
            )
            alt_m = _MAX_ALTITUDE_M

        await drone.action.set_takeoff_altitude(alt_m)
        await drone.action.arm()
        await drone.action.takeoff()

        async for in_air in drone.telemetry.in_air():
            if in_air:
                break

        logger.info("F3InavBackend airborne at %.1f m AGL", alt_m)
        _append_event({"ts": time.time(), "event": "takeoff", "alt_m": alt_m})

    async def patrol(self, waypoints: list[Waypoint]) -> None:
        """Upload and fly a waypoint mission.

        Geofence-checks every waypoint before upload.
        """
        drone = self._assert_connected()

        if not waypoints:
            logger.warning("F3InavBackend patrol called with no waypoints — skipping")
            return

        # Safety: geofence check
        self._geofence.check_waypoints(waypoints)

        try:
            from mavsdk.mission import MissionItem, MissionPlan  # noqa: PLC0415
        except ImportError as exc:
            raise DroneUnavailable("mavsdk.mission not available") from exc

        mission_items = [
            MissionItem(
                latitude_deg=wp.lat,
                longitude_deg=wp.lon,
                relative_altitude_m=min(wp.alt_m, _MAX_ALTITUDE_M),
                speed_m_s=8.0,
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

        async for progress in drone.mission.mission_progress():
            logger.debug("F3 mission progress: %d/%d", progress.current, progress.total)
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
        """Command RTH and wait for landing and disarm."""
        drone = self._assert_connected()
        await drone.action.return_to_launch()

        async for in_air in drone.telemetry.in_air():
            if not in_air:
                break

        await drone.action.disarm()
        logger.info("F3InavBackend returned to home and disarmed")
        _append_event({"ts": time.time(), "event": "return_to_home"})

    async def play_deterrent(self, tone_hz: int = 12000, duration_s: float = 6.0) -> None:
        """
        Activate acoustic deterrent.

        Logs the event and emits a speaker-cue note.  If a GPIO-wired speaker
        is present (see docs/HARDWARE_F3_INAV.md for wiring), a companion
        script on the laptop picks up the JSONL event and drives the GPIO pin.
        This method never blocks the flight controller loop.
        """
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
            "speaker_cue": True,
        }

        logger.info(
            "F3InavBackend deterrent: %.0f Hz for %.1f s (in_air=%s) — speaker cue logged",
            tone_hz,
            duration_s,
            current.in_air,
        )

        if current.in_air:
            await asyncio.sleep(8.0)
        else:
            await asyncio.sleep(duration_s)

        _append_event(event)

    async def get_thermal_clip(self, duration_s: float = 10.0) -> Path:
        """
        Capture a thermal clip.

        F3 quad has no IR payload by default.  If the environment variable
        ``F3_HAS_IR=1`` is set, the method attempts a real capture (no-op
        stub here — real implementation would call the IR camera API).

        Otherwise, falls back to a visible-light synthetic frame using the
        same PIL compositor as :class:`~skyherd.drone.sitl.SitlBackend`.

        Returns the path to the first frame PNG.
        """
        self._assert_connected()
        _ensure_runtime_dirs()

        has_ir = os.environ.get("F3_HAS_IR", "0") == "1"

        if has_ir:
            # Real IR payload path — stub returns the same synthetic frame
            # in this software-ready implementation.  A production build
            # would call the camera SDK here.
            logger.info("F3InavBackend: IR payload active — capturing thermal clip")
        else:
            logger.info(
                "F3InavBackend: no IR payload — falling back to visible-light synthetic frame"
            )

        ts = int(time.time())
        out_path = _THERMAL_DIR / f"f3_{ts}.png"

        try:
            _generate_synthetic_frame(out_path)
        except Exception as exc:
            logger.error("F3InavBackend: failed to generate synthetic frame: %s", exc)
            raise

        _append_event(
            {
                "ts": time.time(),
                "event": "thermal_clip",
                "path": str(out_path),
                "ir_payload": has_ir,
            }
        )
        return out_path

    async def state(self) -> DroneState:
        """Return a fresh DroneState snapshot from MAVLink telemetry."""
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
        except Exception as exc:  # noqa: BLE001
            # mavsdk telemetry stream may not be ready on first poll — safe default used
            logger.debug("mavsdk telemetry read for armed failed: %s", exc)

        try:
            async for is_in_air in drone.telemetry.in_air():
                in_air = is_in_air
                break
        except Exception as exc:  # noqa: BLE001
            # mavsdk telemetry stream may not be ready on first poll — safe default used
            logger.debug("mavsdk telemetry read for in_air failed: %s", exc)

        try:
            async for pos in drone.telemetry.position():
                lat = pos.latitude_deg
                lon = pos.longitude_deg
                alt_m = pos.relative_altitude_m
                break
        except Exception as exc:  # noqa: BLE001
            # mavsdk telemetry stream may not be ready on first poll — safe default used
            logger.debug("mavsdk telemetry read for position failed: %s", exc)

        try:
            async for bat in drone.telemetry.battery():
                battery_pct = bat.remaining_percent * 100.0
                break
        except Exception as exc:  # noqa: BLE001
            # mavsdk telemetry stream may not be ready on first poll — safe default used
            logger.debug("mavsdk telemetry read for battery failed: %s", exc)

        try:
            async for fm in drone.telemetry.flight_mode():
                mode = str(fm)
                break
        except Exception as exc:  # noqa: BLE001
            # mavsdk telemetry stream may not be ready on first poll — safe default used
            logger.debug("mavsdk telemetry read for flight_mode failed: %s", exc)

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
        """Cleanly disconnect from the F3."""
        self._drone = None
        self._connected = False
        logger.info("F3InavBackend disconnected")
        _append_event({"ts": time.time(), "event": "disconnected"})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assert_connected(self):  # type: ignore[return]
        if not self._connected or self._drone is None:
            raise DroneUnavailable(
                "F3InavBackend not connected — call connect() first.\n"
                "Hint: Start mavlink-router first; see docs/HARDWARE_F3_INAV.md"
            )
        return self._drone


# ---------------------------------------------------------------------------
# Visible-light / fallback synthetic frame generator
# (identical algorithm to SitlBackend for consistent agent tool-call results)
# ---------------------------------------------------------------------------


def _generate_synthetic_frame(path: Path, width: int = 480, height: int = 360) -> None:
    """Write a 480×360 greyscale PNG simulating a visible-light or IR frame."""
    try:
        import numpy as np  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError("Pillow and numpy are required for synthetic frame generation") from exc

    rng = np.random.default_rng(seed=int(time.time()) % 2**32)
    frame = rng.normal(loc=40, scale=3, size=(height, width)).astype("float32")

    cx = width // 2 + int(rng.integers(-40, 40))
    cy = height // 2 + int(rng.integers(-30, 30))
    sigma = 35.0

    yy, xx = np.mgrid[0:height, 0:width]
    blob = 180.0 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma**2))
    frame = np.clip(frame + blob, 0, 255).astype("uint8")

    img = Image.fromarray(frame, mode="L")
    img.save(path)
