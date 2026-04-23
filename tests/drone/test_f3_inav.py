"""
Tests for F3InavBackend.

All tests use a mocked MAVSDK System() — no real MAVLink connection is
made.  The mock is injected by patching ``mavsdk`` in the module namespace
before ``connect()`` is called.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skyherd.drone.f3_inav import F3InavBackend
from skyherd.drone.interface import DroneUnavailable, Waypoint
from skyherd.drone.safety import BatteryTooLow, GeofenceViolation, WindTooHigh

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_mavsdk(
    battery_pct: float = 80.0,
    in_air: bool = False,
    armed: bool = False,
    lat: float = 34.05,
    lon: float = -106.05,
    alt_m: float = 0.0,
    mode: str = "STABILIZE",
) -> MagicMock:
    """
    Build a mock of the ``mavsdk`` module with a System() that returns
    sensible telemetry values.
    """

    async def _connection_states():
        mock_state = MagicMock()
        mock_state.is_connected = True
        yield mock_state

    async def _health_ok():
        h = MagicMock()
        h.is_global_position_ok = True
        h.is_home_position_ok = True
        yield h

    async def _in_air_gen():
        yield in_air

    async def _armed_gen():
        yield armed

    async def _position_gen():
        p = MagicMock()
        p.latitude_deg = lat
        p.longitude_deg = lon
        p.relative_altitude_m = alt_m
        yield p

    async def _battery_gen():
        b = MagicMock()
        b.remaining_percent = battery_pct / 100.0
        yield b

    async def _flight_mode_gen():
        yield mode

    async def _mission_progress_gen():
        p = MagicMock()
        p.current = 1
        p.total = 1
        yield p

    system = MagicMock()
    system.connect = AsyncMock()
    system.core.connection_state = _connection_states
    system.telemetry.health = _health_ok
    system.telemetry.in_air = _in_air_gen
    system.telemetry.armed = _armed_gen
    system.telemetry.position = _position_gen
    system.telemetry.battery = _battery_gen
    system.telemetry.flight_mode = _flight_mode_gen
    system.action.set_takeoff_altitude = AsyncMock()
    system.action.arm = AsyncMock()
    system.action.takeoff = AsyncMock()
    system.action.return_to_launch = AsyncMock()
    system.action.disarm = AsyncMock()
    system.mission.set_return_to_launch_after_mission = AsyncMock()
    system.mission.upload_mission = AsyncMock()
    system.mission.start_mission = AsyncMock()
    system.mission.mission_progress = _mission_progress_gen

    mock_mavsdk = MagicMock()
    mock_mavsdk.System.return_value = system

    # MissionItem / MissionPlan mocks
    mission_item = MagicMock()
    mission_item.CameraAction.NONE = "NONE"
    mission_item.VehicleAction.NONE = "NONE"
    mock_mavsdk.mission = MagicMock()
    mock_mavsdk.mission.MissionItem = mission_item
    mock_mavsdk.mission.MissionPlan = MagicMock(return_value=MagicMock())

    return mock_mavsdk


async def _connected_backend(
    battery_pct: float = 80.0,
    in_air: bool = False,
    world_name: str = "ranch_a",
    wind_speed_kt: float = 0.0,
) -> tuple[F3InavBackend, MagicMock]:
    """Connect a backend with a mock MAVSDK system and return both."""
    mock_mavsdk = _make_mock_mavsdk(battery_pct=battery_pct, in_air=in_air)
    backend = F3InavBackend(world_name=world_name, wind_speed_kt=wind_speed_kt)

    with patch.dict("sys.modules", {"mavsdk": mock_mavsdk}):
        await backend.connect()

    backend._drone = mock_mavsdk.System.return_value
    return backend, mock_mavsdk


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


async def test_connect_sets_connected_flag() -> None:
    mock_mavsdk = _make_mock_mavsdk()
    backend = F3InavBackend()

    with patch.dict("sys.modules", {"mavsdk": mock_mavsdk}):
        await backend.connect()

    assert backend._connected is True


async def test_connect_mavsdk_missing_raises_unavailable() -> None:
    backend = F3InavBackend()
    with patch.dict("sys.modules", {"mavsdk": None}):
        with pytest.raises((DroneUnavailable, ImportError)):
            await backend.connect()


async def test_operations_without_connect_raise_unavailable() -> None:
    backend = F3InavBackend()
    with pytest.raises(DroneUnavailable):
        await backend.takeoff()


# ---------------------------------------------------------------------------
# Full round-trip: takeoff → patrol → return_to_home
# ---------------------------------------------------------------------------


async def test_full_round_trip(tmp_path: Path) -> None:
    """takeoff → patrol (3 waypoints) → RTH completes without errors."""
    backend, mock_sdk = await _connected_backend(battery_pct=80.0)

    # Inject geofence-disabled checker so waypoints always pass
    backend._geofence._polygon = None
    backend._geofence._loaded = True

    waypoints = [
        Waypoint(lat=34.02, lon=-106.08, alt_m=30.0),
        Waypoint(lat=34.05, lon=-106.05, alt_m=35.0),
        Waypoint(lat=34.09, lon=-106.02, alt_m=30.0),
    ]

    await backend.takeoff(alt_m=30.0)
    mock_sdk.System.return_value.action.arm.assert_awaited_once()
    mock_sdk.System.return_value.action.takeoff.assert_awaited_once()

    await backend.patrol(waypoints)
    mock_sdk.System.return_value.mission.upload_mission.assert_awaited_once()
    mock_sdk.System.return_value.mission.start_mission.assert_awaited_once()

    await backend.return_to_home()
    mock_sdk.System.return_value.action.return_to_launch.assert_awaited_once()
    mock_sdk.System.return_value.action.disarm.assert_awaited_once()


# ---------------------------------------------------------------------------
# Takeoff safety guards
# ---------------------------------------------------------------------------


async def test_takeoff_battery_too_low_raises() -> None:
    backend, _ = await _connected_backend(battery_pct=20.0)

    with pytest.raises(BatteryTooLow):
        await backend.takeoff()


async def test_takeoff_wind_too_high_raises() -> None:
    backend, _ = await _connected_backend(battery_pct=80.0, wind_speed_kt=25.0)

    with pytest.raises(WindTooHigh):
        await backend.takeoff()


async def test_takeoff_altitude_clamped_to_60m() -> None:
    backend, mock_sdk = await _connected_backend(battery_pct=80.0)

    await backend.takeoff(alt_m=100.0)

    # set_takeoff_altitude should be called with 60 m (the cap), not 100 m
    call_args = mock_sdk.System.return_value.action.set_takeoff_altitude.call_args
    assert call_args[0][0] == pytest.approx(60.0)


# ---------------------------------------------------------------------------
# Patrol geofence guard
# ---------------------------------------------------------------------------


async def test_patrol_outside_geofence_raises() -> None:
    backend, _ = await _connected_backend(battery_pct=80.0)

    # Set a tight NM geofence
    backend._geofence._polygon = [
        (34.00, -106.10),
        (34.10, -106.10),
        (34.10, -106.00),
        (34.00, -106.00),
    ]
    backend._geofence._loaded = True

    outside_waypoints = [
        Waypoint(lat=35.0, lon=-107.0, alt_m=30.0),  # clearly outside
    ]

    with pytest.raises(GeofenceViolation):
        await backend.patrol(outside_waypoints)


async def test_patrol_empty_waypoints_is_noop() -> None:
    backend, mock_sdk = await _connected_backend(battery_pct=80.0)
    await backend.patrol([])
    mock_sdk.System.return_value.mission.upload_mission.assert_not_awaited()


# ---------------------------------------------------------------------------
# Deterrent
# ---------------------------------------------------------------------------


async def test_play_deterrent_logs_event(tmp_path: Path) -> None:
    backend, _ = await _connected_backend()
    # Should not raise
    await backend.play_deterrent(tone_hz=8000, duration_s=0.0)


# ---------------------------------------------------------------------------
# Thermal clip
# ---------------------------------------------------------------------------


async def test_get_thermal_clip_returns_png_path(tmp_path: Path) -> None:
    backend, _ = await _connected_backend()
    # Redirect runtime dir to tmp_path
    import skyherd.drone.f3_inav as f3_module

    orig = f3_module._THERMAL_DIR
    f3_module._THERMAL_DIR = tmp_path

    try:
        path = await backend.get_thermal_clip(duration_s=0.0)
        assert isinstance(path, Path)
        assert str(path).endswith(".png")
    finally:
        f3_module._THERMAL_DIR = orig


# ---------------------------------------------------------------------------
# Disconnect
# ---------------------------------------------------------------------------


async def test_disconnect_clears_connected() -> None:
    backend, _ = await _connected_backend()
    assert backend._connected is True
    await backend.disconnect()
    assert backend._connected is False


async def test_get_backend_factory_returns_f3_inav() -> None:
    from skyherd.drone.interface import get_backend

    backend = get_backend("f3_inav")
    assert isinstance(backend, F3InavBackend)


# ---------------------------------------------------------------------------
# Telemetry DEBUG log on transient failure (HYG-01)
# ---------------------------------------------------------------------------


async def test_telemetry_debug_log_on_transient_failure(caplog) -> None:  # type: ignore[no-untyped-def]
    """Transient mavsdk telemetry read failure logs at DEBUG with field name."""
    import logging

    async def _armed_raise():
        raise RuntimeError("stream not ready")
        yield  # make it an async generator  # noqa: unreachable

    backend, mock_sdk = await _connected_backend(battery_pct=80.0)
    # Replace the armed() stream with one that raises immediately
    mock_sdk.System.return_value.telemetry.armed = _armed_raise

    with caplog.at_level(logging.DEBUG, logger="skyherd.drone.f3_inav"):
        await backend.state()

    assert "mavsdk telemetry read for armed" in caplog.text
