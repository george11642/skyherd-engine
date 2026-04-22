"""Regression tests for C5: every MAVSDK await must have a DroneTimeoutError on timeout.

These tests mock MAVSDK async generators that hang forever and assert
DroneTimeoutError is raised within the configured SLO.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skyherd.drone.interface import DroneTimeoutError, DroneUnavailable
from skyherd.drone.sitl import SitlBackend


def _make_connected_backend() -> SitlBackend:
    """Return a SitlBackend with a mock mavsdk.System already wired in."""
    backend = SitlBackend()
    backend._connected = True
    drone = MagicMock()
    backend._drone = drone
    return backend, drone


async def _hanging_async_gen():
    """An async generator that yields nothing and waits forever."""
    await asyncio.sleep(9999)
    yield  # pragma: no cover


# ---------------------------------------------------------------------------
# connect() — GPS health timeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_health_timeout_raises_drone_timeout_error() -> None:
    """If health() never publishes GPS-ok, DroneTimeoutError must fire."""
    backend = SitlBackend()
    backend._connected = False

    mock_drone = MagicMock()
    # drone.connect() must be awaitable
    mock_drone.connect = AsyncMock()
    # connection_state immediately yields is_connected=True
    connected_state = MagicMock()
    connected_state.is_connected = True

    async def _connected_gen():
        yield connected_state

    mock_drone.core.connection_state = _connected_gen
    # health() hangs forever — simulates stuck GPS
    mock_drone.telemetry.health = _hanging_async_gen

    mock_mavsdk_system = MagicMock()
    mock_mavsdk_system.return_value = mock_drone
    mock_mavsdk_module = MagicMock()
    mock_mavsdk_module.System = mock_mavsdk_system

    with patch.dict("sys.modules", {"mavsdk": mock_mavsdk_module}):
        # Override timeout to 0.05 s for test speed
        with patch("skyherd.drone.sitl._TIMEOUT_HEALTH_S", 0.05):
            with pytest.raises(DroneTimeoutError, match="GPS health check"):
                await backend.connect()


# ---------------------------------------------------------------------------
# takeoff() — in_air timeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_takeoff_in_air_timeout_raises_drone_timeout_error() -> None:
    """If in_air() never becomes True, DroneTimeoutError must fire."""
    backend, drone = _make_connected_backend()

    # arm / set_takeoff_altitude / takeoff succeed instantly
    drone.action.set_takeoff_altitude = AsyncMock()
    drone.action.arm = AsyncMock()
    drone.action.takeoff = AsyncMock()

    # in_air() hangs forever
    drone.telemetry.in_air = _hanging_async_gen

    with patch("skyherd.drone.sitl._TIMEOUT_IN_AIR_S", 0.05):
        with pytest.raises(DroneTimeoutError, match="airborne"):
            await backend.takeoff()


# ---------------------------------------------------------------------------
# return_to_home() — landing timeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_return_to_home_land_timeout_raises_drone_timeout_error() -> None:
    """If the drone never lands after RTL, DroneTimeoutError must fire."""
    backend, drone = _make_connected_backend()

    drone.action.return_to_launch = AsyncMock()

    # in_air() yields True forever (never lands)
    async def _always_in_air():
        while True:
            yield True
            await asyncio.sleep(0)

    drone.telemetry.in_air = _always_in_air

    with patch("skyherd.drone.sitl._TIMEOUT_RTL_S", 0.05):
        with pytest.raises(DroneTimeoutError, match="land"):
            await backend.return_to_home()


# ---------------------------------------------------------------------------
# DroneTimeoutError inherits DroneUnavailable
# ---------------------------------------------------------------------------


def test_drone_timeout_error_is_drone_unavailable() -> None:
    """DroneTimeoutError must be catchable as DroneUnavailable."""
    err = DroneTimeoutError("test")
    assert isinstance(err, DroneUnavailable)
    assert isinstance(err, DroneTimeoutError)
