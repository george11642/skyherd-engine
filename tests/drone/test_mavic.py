"""
Tests for MavicBackend.

All tests inject a mock WebSocket transport — no real network connection,
no Android device, no DJI SDK.

The mock transport implements the same interface as _WSTransport:
  - connect(timeout_s)
  - send_command(cmd, args, seq) → dict
  - close()
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from skyherd.drone.interface import DroneError, DroneUnavailable, Waypoint
from skyherd.drone.mavic import MavicBackend
from skyherd.drone.safety import BatteryTooLow, GeofenceViolation, WindTooHigh

# ---------------------------------------------------------------------------
# Mock transport factory
# ---------------------------------------------------------------------------


def _make_transport(
    battery_pct: float = 80.0,
    in_air: bool = False,
    armed: bool = False,
    lat: float = 34.05,
    lon: float = -106.05,
    alt_m: float = 0.0,
    mode: str = "STANDBY",
    takeoff_ok: bool = True,
    patrol_ok: bool = True,
    rth_ok: bool = True,
    deterrent_ok: bool = True,
    clip_ok: bool = True,
) -> MagicMock:
    """
    Build a mock _WSTransport that returns sensible ACK dicts for each command.
    """

    state_data = {
        "armed": armed,
        "in_air": in_air,
        "altitude_m": alt_m,
        "battery_pct": battery_pct,
        "mode": mode,
        "lat": lat,
        "lon": lon,
    }

    def _ack(cmd: str, ok: bool, extra: dict | None = None) -> dict:
        d: dict = {"ack": cmd, "result": "ok" if ok else "error", "seq": 0}
        if extra:
            d.update(extra)
        if not ok:
            d["message"] = "mock error"
        return d

    async def send_command(cmd: str, args: dict, seq: int) -> dict:
        d = dict(_ack(cmd, True))
        d["seq"] = seq
        if cmd == "get_state":
            d["data"] = state_data
        elif cmd == "takeoff":
            d["result"] = "ok" if takeoff_ok else "error"
            if not takeoff_ok:
                d["message"] = "mock takeoff error"
        elif cmd == "patrol":
            d["result"] = "ok" if patrol_ok else "error"
        elif cmd == "return_to_home":
            d["result"] = "ok" if rth_ok else "error"
        elif cmd == "play_deterrent":
            d["result"] = "ok" if deterrent_ok else "error"
        elif cmd == "capture_visual_clip":
            d["result"] = "ok" if clip_ok else "error"
        return d

    transport = MagicMock()
    transport.connect = AsyncMock()
    transport.send_command = send_command
    transport.close = AsyncMock()
    return transport


async def _connected_backend(
    battery_pct: float = 80.0,
    in_air: bool = False,
    armed: bool = False,
    world_name: str = "ranch_a",
    wind_speed_kt: float = 0.0,
    takeoff_ok: bool = True,
    patrol_ok: bool = True,
    rth_ok: bool = True,
) -> MavicBackend:
    """Return a connected MavicBackend with a mock transport."""
    transport = _make_transport(
        battery_pct=battery_pct,
        in_air=in_air,
        armed=armed,
        takeoff_ok=takeoff_ok,
        patrol_ok=patrol_ok,
        rth_ok=rth_ok,
    )
    backend = MavicBackend(
        world_name=world_name,
        wind_speed_kt=wind_speed_kt,
        transport=transport,
    )
    await backend.connect()
    return backend


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


async def test_connect_sets_connected_flag() -> None:
    backend = await _connected_backend()
    assert backend._connected is True


async def test_connect_transport_failure_raises_unavailable() -> None:
    transport = MagicMock()
    transport.connect = AsyncMock(side_effect=DroneUnavailable("mock WS failure"))
    transport.close = AsyncMock()

    backend = MavicBackend(transport=transport)
    with pytest.raises(DroneUnavailable):
        await backend.connect()


async def test_operations_without_connect_raise_unavailable() -> None:
    transport = _make_transport()
    backend = MavicBackend(transport=transport)
    with pytest.raises(DroneUnavailable):
        await backend.takeoff()


# ---------------------------------------------------------------------------
# Full round-trip: takeoff → patrol → return_to_home
# ---------------------------------------------------------------------------


async def test_full_round_trip() -> None:
    """takeoff → patrol (3 waypoints) → RTH flow completes without errors.

    MavicBackend updates _state eagerly after each command, then state() syncs
    from the companion app.  We verify the cached state (not re-synced) is
    updated correctly after takeoff so the test does not depend on the mock
    transport reflecting in-flight telemetry.
    """
    backend = await _connected_backend(battery_pct=80.0)

    # Disable geofence for the round-trip test
    backend._geofence._polygon = None
    backend._geofence._loaded = True

    await backend.takeoff(alt_m=25.0)
    # Check internal cached state (eagerly set after takeoff command ACK)
    assert backend._state.in_air is True
    assert backend._state.armed is True
    assert backend._state.altitude_m == pytest.approx(25.0)

    waypoints = [
        Waypoint(lat=34.02, lon=-106.08, alt_m=30.0),
        Waypoint(lat=34.05, lon=-106.05, alt_m=35.0),
        Waypoint(lat=34.09, lon=-106.02, alt_m=30.0),
    ]
    await backend.patrol(waypoints)
    # After patrol the last waypoint position is eagerly cached
    assert backend._state.lat == pytest.approx(34.09)
    assert backend._state.lon == pytest.approx(-106.02)

    await backend.return_to_home()
    assert backend._state.in_air is False
    assert backend._state.armed is False
    assert backend._state.mode == "LAND"


# ---------------------------------------------------------------------------
# Takeoff safety guards
# ---------------------------------------------------------------------------


async def test_takeoff_battery_too_low_raises() -> None:
    backend = await _connected_backend(battery_pct=20.0)
    with pytest.raises(BatteryTooLow):
        await backend.takeoff()


async def test_takeoff_wind_too_high_raises() -> None:
    backend = await _connected_backend(battery_pct=80.0, wind_speed_kt=25.0)
    with pytest.raises(WindTooHigh):
        await backend.takeoff()


async def test_takeoff_altitude_clamped_to_60m() -> None:
    backend = await _connected_backend(battery_pct=80.0)
    await backend.takeoff(alt_m=120.0)
    # After clamp, cached altitude should be 60 m
    assert backend._state.altitude_m == pytest.approx(60.0)


async def test_takeoff_companion_app_error_raises_drone_error() -> None:
    backend = await _connected_backend(battery_pct=80.0, takeoff_ok=False)
    with pytest.raises(DroneError):
        await backend.takeoff()


# ---------------------------------------------------------------------------
# Patrol geofence guard
# ---------------------------------------------------------------------------


async def test_patrol_outside_geofence_raises() -> None:
    backend = await _connected_backend(battery_pct=80.0)
    backend._geofence._polygon = [
        (34.00, -106.10),
        (34.10, -106.10),
        (34.10, -106.00),
        (34.00, -106.00),
    ]
    backend._geofence._loaded = True

    with pytest.raises(GeofenceViolation):
        await backend.patrol([Waypoint(lat=35.0, lon=-107.0, alt_m=30.0)])


async def test_patrol_empty_waypoints_is_noop() -> None:
    backend = await _connected_backend()
    await backend.patrol([])  # should not raise; transport never called for patrol


async def test_patrol_companion_app_error_raises_drone_error() -> None:
    backend = await _connected_backend(patrol_ok=False)
    backend._geofence._polygon = None
    backend._geofence._loaded = True

    with pytest.raises(DroneError):
        await backend.patrol([Waypoint(lat=34.05, lon=-106.05, alt_m=30.0)])


# ---------------------------------------------------------------------------
# Return to home
# ---------------------------------------------------------------------------


async def test_return_to_home_updates_state() -> None:
    backend = await _connected_backend()
    await backend.return_to_home()
    assert backend._state.in_air is False
    assert backend._state.armed is False
    assert backend._state.mode == "LAND"


async def test_rth_companion_app_error_raises_drone_error() -> None:
    backend = await _connected_backend(rth_ok=False)
    with pytest.raises(DroneError):
        await backend.return_to_home()


# ---------------------------------------------------------------------------
# Deterrent
# ---------------------------------------------------------------------------


async def test_play_deterrent_does_not_raise() -> None:
    backend = await _connected_backend()
    await backend.play_deterrent(tone_hz=8000, duration_s=3.0)


# ---------------------------------------------------------------------------
# Thermal clip (synthetic frame — no IR on Mavic Air 2)
# ---------------------------------------------------------------------------


async def test_get_thermal_clip_returns_png_path(tmp_path: Path) -> None:
    backend = await _connected_backend()

    import skyherd.drone.mavic as mavic_module

    orig = mavic_module._THERMAL_DIR
    mavic_module._THERMAL_DIR = tmp_path

    try:
        path = await backend.get_thermal_clip(duration_s=0.0)
        assert isinstance(path, Path)
        assert str(path).endswith(".png")
    finally:
        mavic_module._THERMAL_DIR = orig


# ---------------------------------------------------------------------------
# Disconnect
# ---------------------------------------------------------------------------


async def test_disconnect_clears_connected() -> None:
    backend = await _connected_backend()
    await backend.disconnect()
    assert backend._connected is False
    assert backend._state.mode == "UNKNOWN"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


async def test_get_backend_factory_returns_mavic_adapter() -> None:
    """Phase 7: "mavic" now returns the two-legged MavicAdapter."""
    from skyherd.drone.interface import get_backend
    from skyherd.drone.mavic_adapter import MavicAdapter

    backend = get_backend("mavic")
    assert isinstance(backend, MavicAdapter)


async def test_get_backend_factory_mavic_direct_returns_bare_backend() -> None:
    """Phase 7 regression: "mavic_direct" still returns bare MavicBackend."""
    from skyherd.drone.interface import get_backend

    backend = get_backend("mavic_direct")
    assert isinstance(backend, MavicBackend)
