"""
Round-trip tests for StubBackend.

All tests are pure in-memory — no Docker, no network.  They validate that
the full takeoff → patrol → return_to_home → disconnect flow updates
DroneState correctly, and that guard conditions (not connected, empty
waypoints, deterrent, thermal clip) behave as specified.
"""

from __future__ import annotations

import pytest

from skyherd.drone.interface import DroneUnavailable, Waypoint
from skyherd.drone.stub import StubBackend

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def connected_stub() -> StubBackend:
    """Return a StubBackend that has already been connected."""
    backend = StubBackend()
    await backend.connect()
    return backend


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


async def test_connect_sets_mode() -> None:
    backend = StubBackend()
    initial_state = await backend.state() if False else None  # can't call before connect
    await backend.connect()
    s = await backend.state()
    assert s.mode == "STABILIZE"
    assert not s.armed
    assert not s.in_air


async def test_disconnect_clears_connected(connected_stub: StubBackend) -> None:
    await connected_stub.disconnect()
    s = await connected_stub.state()
    assert s.mode == "UNKNOWN"


async def test_operations_raise_when_not_connected() -> None:
    backend = StubBackend()
    with pytest.raises(DroneUnavailable):
        await backend.takeoff()


# ---------------------------------------------------------------------------
# Takeoff
# ---------------------------------------------------------------------------


async def test_takeoff_marks_in_air(connected_stub: StubBackend) -> None:
    await connected_stub.takeoff(alt_m=25.0)
    s = await connected_stub.state()
    assert s.in_air
    assert s.armed
    assert s.altitude_m == pytest.approx(25.0)
    assert s.mode == "GUIDED"


async def test_takeoff_default_altitude(connected_stub: StubBackend) -> None:
    await connected_stub.takeoff()
    s = await connected_stub.state()
    assert s.altitude_m == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# Patrol
# ---------------------------------------------------------------------------


async def test_patrol_updates_position(connected_stub: StubBackend) -> None:
    await connected_stub.takeoff()
    waypoints = [
        Waypoint(lat=34.1, lon=-106.1, alt_m=30.0),
        Waypoint(lat=34.2, lon=-106.2, alt_m=35.0, hold_s=2.0),
        Waypoint(lat=34.3, lon=-106.3, alt_m=30.0),
    ]
    await connected_stub.patrol(waypoints)

    s = await connected_stub.state()
    # After patrol completes, position should be at the last waypoint.
    assert s.lat == pytest.approx(34.3)
    assert s.lon == pytest.approx(-106.3)
    assert s.altitude_m == pytest.approx(30.0)
    assert s.mode == "AUTO"


async def test_patrol_empty_waypoints_is_noop(connected_stub: StubBackend) -> None:
    await connected_stub.takeoff()
    initial = await connected_stub.state()
    await connected_stub.patrol([])
    after = await connected_stub.state()
    # Mode should not change to AUTO for empty patrol.
    assert after.mode == initial.mode


# ---------------------------------------------------------------------------
# Return to home
# ---------------------------------------------------------------------------


async def test_return_to_home_lands_and_disarms(connected_stub: StubBackend) -> None:
    await connected_stub.takeoff()
    await connected_stub.patrol([Waypoint(lat=34.5, lon=-106.5, alt_m=30.0)])
    await connected_stub.return_to_home()

    s = await connected_stub.state()
    assert not s.in_air
    assert not s.armed
    assert s.mode == "LAND"
    # Landed at stub home coords.
    assert s.lat == pytest.approx(34.0)
    assert s.lon == pytest.approx(-106.0)
    assert s.altitude_m == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Full round-trip
# ---------------------------------------------------------------------------


async def test_full_round_trip(connected_stub: StubBackend) -> None:
    """takeoff → patrol (3 waypoints) → RTH → disconnect without errors."""
    waypoints = [
        Waypoint(lat=34.11, lon=-106.11, alt_m=30.0),
        Waypoint(lat=34.12, lon=-106.12, alt_m=40.0),
        Waypoint(lat=34.13, lon=-106.13, alt_m=30.0),
    ]

    await connected_stub.takeoff(alt_m=30.0)
    await connected_stub.patrol(waypoints)
    await connected_stub.return_to_home()

    s = await connected_stub.state()
    assert not s.in_air
    assert not s.armed

    await connected_stub.disconnect()
    s_after = await connected_stub.state()
    assert s_after.mode == "UNKNOWN"


# ---------------------------------------------------------------------------
# Deterrent
# ---------------------------------------------------------------------------


async def test_play_deterrent_does_not_raise(connected_stub: StubBackend) -> None:
    await connected_stub.takeoff()
    # Should complete without raising.
    await connected_stub.play_deterrent(tone_hz=8000, duration_s=3.0)


async def test_play_deterrent_default_params(connected_stub: StubBackend) -> None:
    await connected_stub.takeoff()
    await connected_stub.play_deterrent()  # defaults: 12000 Hz, 6 s


# ---------------------------------------------------------------------------
# Thermal clip
# ---------------------------------------------------------------------------


async def test_get_thermal_clip_returns_path(connected_stub: StubBackend) -> None:
    from pathlib import Path

    await connected_stub.takeoff()
    path = await connected_stub.get_thermal_clip()
    assert isinstance(path, Path)
    assert str(path).endswith(".png")


# ---------------------------------------------------------------------------
# State isolation — state() returns a copy
# ---------------------------------------------------------------------------


async def test_state_returns_copy(connected_stub: StubBackend) -> None:
    s1 = await connected_stub.state()
    s1.armed = True  # mutate the copy
    s2 = await connected_stub.state()
    assert not s2.armed  # internal state unchanged
