"""
StubBackend — pure in-memory drone backend for unit tests.

Zero network I/O.  All commands update the internal DroneState and return
immediately.  Tests that need drone behaviour but not Docker/SITL use this.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from skyherd.drone.interface import DroneBackend, DroneState, DroneUnavailable, Waypoint

logger = logging.getLogger(__name__)

# Sentinel: set to True in tests to simulate a connection failure.
STUB_FORCE_UNAVAILABLE = False


class StubBackend(DroneBackend):
    """
    In-memory drone backend.

    Maintains a :class:`~skyherd.drone.interface.DroneState` that callers
    can inspect after each command.  Appropriate for unit/integration tests
    that must not touch Docker or a network.
    """

    def __init__(self) -> None:
        self._state = DroneState()
        self._connected = False
        self._home_lat: float = 34.0  # dummy NM ranch coords
        self._home_lon: float = -106.0
        self._home_alt: float = 0.0

    # ------------------------------------------------------------------
    # DroneBackend implementation
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        if STUB_FORCE_UNAVAILABLE:
            raise DroneUnavailable("StubBackend forced unavailable (STUB_FORCE_UNAVAILABLE=True)")
        self._connected = True
        self._state.mode = "STABILIZE"
        logger.debug("StubBackend connected")

    async def takeoff(self, alt_m: float = 30.0) -> None:
        self._assert_connected()
        self._state.armed = True
        self._state.in_air = True
        self._state.altitude_m = alt_m
        self._state.mode = "GUIDED"
        logger.debug("StubBackend takeoff to %.1f m", alt_m)
        await asyncio.sleep(0)  # yield so awaited callers behave correctly

    async def patrol(self, waypoints: list[Waypoint]) -> None:
        self._assert_connected()
        if not waypoints:
            logger.debug("StubBackend patrol called with empty waypoint list — noop")
            return

        self._state.mode = "AUTO"
        for wp in waypoints:
            self._state.lat = wp.lat
            self._state.lon = wp.lon
            self._state.altitude_m = wp.alt_m
            logger.debug(
                "StubBackend at waypoint lat=%.4f lon=%.4f alt=%.1f",
                wp.lat,
                wp.lon,
                wp.alt_m,
            )
            await asyncio.sleep(0)

    async def return_to_home(self) -> None:
        self._assert_connected()
        self._state.lat = self._home_lat
        self._state.lon = self._home_lon
        self._state.altitude_m = self._home_alt
        self._state.in_air = False
        self._state.armed = False
        self._state.mode = "LAND"
        logger.debug("StubBackend returned to home")
        await asyncio.sleep(0)

    async def play_deterrent(self, tone_hz: int = 12000, duration_s: float = 6.0) -> None:
        self._assert_connected()
        logger.info("StubBackend deterrent: %.0f Hz for %.1f s", tone_hz, duration_s)
        await asyncio.sleep(0)

    async def get_thermal_clip(self, duration_s: float = 10.0) -> Path:
        self._assert_connected()
        # Return a sentinel path; tests that need an actual file should mock this.
        path = Path("runtime/thermal/stub_frame.png")
        logger.debug("StubBackend thermal clip at %s", path)
        await asyncio.sleep(0)
        return path

    async def state(self) -> DroneState:
        # Return a copy so callers can't mutate internal state.
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
        self._connected = False
        self._state.mode = "UNKNOWN"
        logger.debug("StubBackend disconnected")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assert_connected(self) -> None:
        if not self._connected:
            raise DroneUnavailable("StubBackend not connected — call connect() first")
