"""
MavicBackend — DJI Mavic Air 2 via Android companion app.

Communication path
------------------
  MAVSDK agent tool call
    → MavicBackend (this module)
      → WebSocket / MQTT JSON commands
        → SkyHerdCompanion Android app (android/SkyHerdCompanion/)
          → DJI Mobile SDK V5

Protocol
--------
Outbound command (Python → app)::

    {"cmd": "takeoff", "args": {"alt_m": 5.0}, "seq": 1}

Inbound acknowledgement (app → Python)::

    {"ack": "takeoff", "result": "ok", "seq": 1}
    {"ack": "takeoff", "result": "error", "message": "...", "seq": 1}

Connection is configured via environment variables:

  ``MAVIC_WS_URL``   — WebSocket URL of the companion app bridge, e.g.
                       ``ws://192.168.1.10:8765``.
                       Default: ``ws://localhost:8765``

  ``MAVIC_MQTT_URL`` — MQTT broker URL for the companion app to consume.
                       Used when the Android app is configured for MQTT mode.
                       Default: ``mqtt://localhost:1883``

Safety guards (shared via safety.py)
--------------------------------------
  - GeofenceChecker  — validated on every patrol() call.
  - BatteryGuard     — checked before takeoff.
  - WindGuard        — ceiling 21 kt for Mavic Air 2.

Thermal note
-------------
Mavic Air 2 has no thermal camera.  ``get_thermal_clip`` returns a synthetic
visible-light frame via the same PIL compositor used by SitlBackend so that
agent tool calls resolve consistently regardless of hardware.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from skyherd.drone.interface import DroneBackend, DroneError, DroneState, DroneUnavailable, Waypoint
from skyherd.drone.safety import (
    WIND_CEILING_MAVIC_KT,
    BatteryGuard,
    GeofenceChecker,
    WindGuard,
)

logger = logging.getLogger(__name__)

_DEFAULT_WS_URL = "ws://localhost:8765"
_CMD_TIMEOUT_S = 30.0
_CONNECT_TIMEOUT_S = 15.0

_EVENTS_PATH = Path("runtime/drone_events_mavic.jsonl")
_THERMAL_DIR = Path("runtime/thermal")


def _ensure_runtime_dirs() -> None:
    _EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _THERMAL_DIR.mkdir(parents=True, exist_ok=True)


def _append_event(event: dict) -> None:
    _ensure_runtime_dirs()
    with _EVENTS_PATH.open("a") as fh:
        fh.write(json.dumps(event) + "\n")


class _WSTransport:
    """
    Thin asyncio WebSocket transport wrapper.

    Factored out so tests can inject a mock transport without touching the
    backend's business logic.
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._ws: Any = None

    async def connect(self, timeout_s: float = _CONNECT_TIMEOUT_S) -> None:
        try:
            import websockets  # noqa: PLC0415
        except ImportError as exc:
            raise DroneUnavailable(
                "websockets package not installed — run `uv add websockets`"
            ) from exc

        try:
            self._ws = await asyncio.wait_for(
                websockets.connect(self._url),
                timeout=timeout_s,
            )
        except TimeoutError as exc:
            raise DroneUnavailable(
                f"Companion app not reachable at {self._url} within {timeout_s:.0f} s. "
                "Check that SkyHerdCompanion is running and MAVIC_WS_URL is correct."
            ) from exc
        except Exception as exc:
            raise DroneUnavailable(
                f"Cannot connect to companion app at {self._url}: {exc}"
            ) from exc

    async def send_command(self, cmd: str, args: dict, seq: int) -> dict:
        """Send a JSON command and await the matching ACK."""
        if self._ws is None:
            raise DroneUnavailable("WebSocket not connected")

        payload = json.dumps({"cmd": cmd, "args": args, "seq": seq})
        await self._ws.send(payload)

        # Wait for the matching ACK
        deadline = time.monotonic() + _CMD_TIMEOUT_S
        while True:
            try:
                raw = await asyncio.wait_for(
                    self._ws.recv(),
                    timeout=max(0.1, deadline - time.monotonic()),
                )
            except TimeoutError as exc:
                raise DroneError(
                    f"Companion app did not ACK command '{cmd}' within {_CMD_TIMEOUT_S:.0f} s"
                ) from exc

            msg = json.loads(raw)
            if msg.get("seq") == seq and msg.get("ack") == cmd:
                return msg
            # Discard telemetry / out-of-order messages and keep waiting

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None


class MavicBackend(DroneBackend):
    """
    Drone backend for DJI Mavic Air 2 via SkyHerdCompanion Android app.

    All public methods are coroutines; call ``await backend.connect()``
    before any other method.

    Parameters
    ----------
    ws_url:
        WebSocket URL of the companion app.  Defaults to the value of the
        ``MAVIC_WS_URL`` env var, or ``ws://localhost:8765``.
    world_name:
        Ranch world YAML name for geofence loading (default ``"ranch_a"``).
    wind_speed_kt:
        Pre-flight wind speed for WindGuard.  Set to 0.0 (default) to skip
        wind check in CI / tests.
    transport:
        Injectable transport for unit tests.  If None, a real :class:`_WSTransport`
        is created from ``ws_url``.
    """

    def __init__(
        self,
        ws_url: str | None = None,
        world_name: str = "ranch_a",
        wind_speed_kt: float = 0.0,
        transport: Any = None,
    ) -> None:
        self._ws_url = ws_url or os.environ.get("MAVIC_WS_URL", _DEFAULT_WS_URL)
        self._transport = transport or _WSTransport(self._ws_url)
        self._connected = False
        self._seq = 0
        self._wind_speed_kt = wind_speed_kt

        # Cached state from telemetry ACKs
        self._state = DroneState()

        # Safety guards
        self._geofence = GeofenceChecker(world_name=world_name)
        self._battery = BatteryGuard()
        self._wind = WindGuard(ceiling_kt=WIND_CEILING_MAVIC_KT)

    # ------------------------------------------------------------------
    # DroneBackend implementation
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        Open WebSocket connection to SkyHerdCompanion.

        Raises :class:`~skyherd.drone.interface.DroneUnavailable` if the
        companion app is not reachable.
        """
        try:
            await self._transport.connect()
        except DroneUnavailable:
            raise
        except Exception as exc:
            raise DroneUnavailable(
                f"Cannot connect to Mavic companion app at {self._ws_url}: {exc}\n"
                "Check that SkyHerdCompanion is running on the Android device."
            ) from exc

        self._connected = True
        self._state.mode = "STANDBY"
        logger.info("MavicBackend connected to companion app at %s", self._ws_url)
        _append_event({"ts": time.time(), "event": "connected", "url": self._ws_url})

        # Fetch initial state from companion app
        try:
            await self._sync_state()
        except Exception as exc:
            logger.warning("MavicBackend: initial state sync failed: %s", exc)

    async def takeoff(self, alt_m: float = 30.0) -> None:
        """
        Take off to *alt_m* metres AGL via DJI SDK FlightController.startTakeoff.

        Safety checks: WindGuard → BatteryGuard → alt cap.
        """
        self._assert_connected()

        # Safety gate 1: wind
        if self._wind_speed_kt > 0.0:
            self._wind.check(self._wind_speed_kt)

        # Safety gate 2: battery (refresh from companion app)
        await self._sync_state()
        self._battery.check_takeoff(self._state.battery_pct)

        # Safety gate 3: altitude cap (DJI hard limit is 120 m; we cap at 60 m)
        if alt_m > 60.0:
            logger.warning(
                "MavicBackend: requested altitude %.1f m clamped to 60 m",
                alt_m,
            )
            alt_m = 60.0

        ack = await self._send("takeoff", {"alt_m": alt_m})
        if ack.get("result") != "ok":
            raise DroneError(
                f"Companion app rejected takeoff: {ack.get('message', 'unknown error')}"
            )

        self._state.armed = True
        self._state.in_air = True
        self._state.altitude_m = alt_m
        self._state.mode = "GUIDED"
        logger.info("MavicBackend takeoff to %.1f m AGL", alt_m)
        _append_event({"ts": time.time(), "event": "takeoff", "alt_m": alt_m})

    async def patrol(self, waypoints: list[Waypoint]) -> None:
        """Upload and fly a waypoint mission via the companion app."""
        self._assert_connected()

        if not waypoints:
            logger.warning("MavicBackend patrol called with no waypoints — skipping")
            return

        # Safety: geofence check
        self._geofence.check_waypoints(waypoints)

        serialised = [
            {"lat": wp.lat, "lon": wp.lon, "alt_m": wp.alt_m, "hold_s": wp.hold_s}
            for wp in waypoints
        ]

        ack = await self._send("patrol", {"waypoints": serialised})
        if ack.get("result") != "ok":
            raise DroneError(
                f"Companion app rejected patrol: {ack.get('message', 'unknown error')}"
            )

        # Update cached state to last waypoint
        last = waypoints[-1]
        self._state.lat = last.lat
        self._state.lon = last.lon
        self._state.altitude_m = last.alt_m
        self._state.mode = "AUTO"

        _append_event(
            {
                "ts": time.time(),
                "event": "patrol_complete",
                "waypoints": serialised,
            }
        )

    async def return_to_home(self) -> None:
        """Command RTH via the companion app and wait for landing."""
        self._assert_connected()

        ack = await self._send("return_to_home", {})
        if ack.get("result") != "ok":
            raise DroneError(f"Companion app rejected RTH: {ack.get('message', 'unknown error')}")

        self._state.in_air = False
        self._state.armed = False
        self._state.mode = "LAND"
        logger.info("MavicBackend returned to home")
        _append_event({"ts": time.time(), "event": "return_to_home"})

    async def play_deterrent(self, tone_hz: int = 12000, duration_s: float = 6.0) -> None:
        """
        Activate acoustic deterrent via the companion app.

        The companion app calls DJI SDK ``playTone`` if an accessory speaker
        is paired; otherwise it logs the event on the device.
        """
        self._assert_connected()

        ack = await self._send("play_deterrent", {"tone_hz": tone_hz, "duration_s": duration_s})
        if ack.get("result") != "ok":
            logger.warning(
                "MavicBackend: deterrent not confirmed by companion app: %s",
                ack.get("message", "unknown"),
            )

        logger.info(
            "MavicBackend deterrent: %.0f Hz for %.1f s",
            tone_hz,
            duration_s,
        )
        _append_event(
            {
                "ts": time.time(),
                "event": "deterrent",
                "tone_hz": tone_hz,
                "duration_s": duration_s,
            }
        )

    async def get_thermal_clip(self, duration_s: float = 10.0) -> Path:
        """
        Capture a visual clip and return a synthetic frame path.

        Mavic Air 2 has no thermal camera.  This method requests a
        visible-light clip from the companion app (``captureVisualClip``)
        and also writes a synthetic greyscale frame locally so that the
        agent's tool call always resolves to a valid Path — identical
        behaviour to SitlBackend.
        """
        self._assert_connected()
        _ensure_runtime_dirs()

        # Best-effort request to companion app for real visual clip
        try:
            ack = await self._send("capture_visual_clip", {"duration_s": duration_s})
            logger.info(
                "MavicBackend visual clip: %s",
                ack.get("result", "unknown"),
            )
        except DroneError as exc:
            logger.warning("MavicBackend: visual clip request failed: %s", exc)

        # Always write a synthetic frame for consistent agent resolution
        ts = int(time.time())
        out_path = _THERMAL_DIR / f"mavic_{ts}.png"
        try:
            _generate_synthetic_frame(out_path)
        except Exception as exc:
            logger.error("MavicBackend: synthetic frame generation failed: %s", exc)
            raise

        _append_event(
            {
                "ts": time.time(),
                "event": "thermal_clip",
                "path": str(out_path),
                "ir_payload": False,
                "note": "Mavic Air 2 has no thermal camera — synthetic frame",
            }
        )
        return out_path

    async def state(self) -> DroneState:
        """Return a fresh DroneState snapshot (synced from companion app)."""
        self._assert_connected()
        await self._sync_state()
        return DroneState(
            armed=self._state.armed,
            in_air=self._state.in_air,
            altitude_m=self._state.altitude_m,
            battery_pct=self._state.battery_pct,
            mode=self._state.mode,
            lat=self._state.lat,
            lon=self._state.lon,
        )

    async def disconnect(self) -> None:
        """Close the WebSocket connection to the companion app."""
        await self._transport.close()
        self._connected = False
        self._state.mode = "UNKNOWN"
        logger.info("MavicBackend disconnected")
        _append_event({"ts": time.time(), "event": "disconnected"})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assert_connected(self) -> None:
        if not self._connected:
            raise DroneUnavailable(
                "MavicBackend not connected — call connect() first.\n"
                "Check that SkyHerdCompanion is running on the Android device."
            )

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def _send(self, cmd: str, args: dict) -> dict:
        """Send a command to the companion app and return the ACK dict."""
        return await self._transport.send_command(cmd, args, self._next_seq())

    async def _sync_state(self) -> None:
        """Request a state snapshot from the companion app and update cache."""
        try:
            ack = await self._send("get_state", {})
            data = ack.get("data", {})
            self._state.armed = bool(data.get("armed", self._state.armed))
            self._state.in_air = bool(data.get("in_air", self._state.in_air))
            self._state.altitude_m = float(data.get("altitude_m", self._state.altitude_m))
            self._state.battery_pct = float(data.get("battery_pct", self._state.battery_pct))
            self._state.mode = str(data.get("mode", self._state.mode))
            self._state.lat = float(data.get("lat", self._state.lat))
            self._state.lon = float(data.get("lon", self._state.lon))
        except Exception as exc:
            logger.debug("MavicBackend: state sync failed (using cached): %s", exc)


# ---------------------------------------------------------------------------
# Synthetic visible-light frame generator (no thermal on Mavic Air 2)
# ---------------------------------------------------------------------------


def _generate_synthetic_frame(path: Path, width: int = 480, height: int = 360) -> None:
    """Write a 480×360 greyscale PNG as a visible-light fallback frame."""
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
