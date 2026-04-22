"""
Tests for shared drone safety guards: GeofenceChecker, BatteryGuard, WindGuard.

All tests are pure in-memory — no network, no hardware, no filesystem writes
for the geofence tests (polygon injected directly).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skyherd.drone.interface import Waypoint
from skyherd.drone.safety import (
    WIND_CEILING_F3_KT,
    WIND_CEILING_MAVIC_KT,
    BatteryGuard,
    BatteryTooLow,
    GeofenceChecker,
    GeofenceViolation,
    WindGuard,
    WindTooHigh,
    _point_in_polygon,
)

# ---------------------------------------------------------------------------
# _point_in_polygon helper
# ---------------------------------------------------------------------------


def test_point_inside_square() -> None:
    square = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    assert _point_in_polygon(0.5, 0.5, square) is True


def test_point_outside_square() -> None:
    square = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    assert _point_in_polygon(2.0, 2.0, square) is False


def test_point_on_edge() -> None:
    # Ray-casting edge-on behaviour is implementation-defined; we just check
    # it does not raise.
    square = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    _point_in_polygon(0.0, 0.5, square)  # should not raise


# ---------------------------------------------------------------------------
# GeofenceChecker — polygon injected via YAML-less path
# ---------------------------------------------------------------------------


def _make_checker_with_polygon(polygon: list[tuple[float, float]]) -> GeofenceChecker:
    """Build a GeofenceChecker with a pre-loaded polygon (bypasses file I/O)."""
    checker = GeofenceChecker.__new__(GeofenceChecker)
    checker._world_name = "test"
    checker._polygon = polygon
    checker._loaded = True
    checker._worlds_dir = Path("/nonexistent")
    return checker


_NM_BOX = [
    (34.00, -106.10),
    (34.10, -106.10),
    (34.10, -106.00),
    (34.00, -106.00),
]


def test_geofence_inside_passes() -> None:
    checker = _make_checker_with_polygon(_NM_BOX)
    wp = Waypoint(lat=34.05, lon=-106.05, alt_m=30.0)
    checker.check_waypoint(wp)  # should not raise


def test_geofence_outside_raises() -> None:
    checker = _make_checker_with_polygon(_NM_BOX)
    wp = Waypoint(lat=35.0, lon=-107.0, alt_m=30.0)
    with pytest.raises(GeofenceViolation):
        checker.check_waypoint(wp)


def test_geofence_check_waypoints_first_violation_raises() -> None:
    checker = _make_checker_with_polygon(_NM_BOX)
    waypoints = [
        Waypoint(lat=34.05, lon=-106.05, alt_m=30.0),  # inside
        Waypoint(lat=35.0, lon=-107.0, alt_m=30.0),  # outside
        Waypoint(lat=34.06, lon=-106.06, alt_m=30.0),  # inside (never reached)
    ]
    with pytest.raises(GeofenceViolation):
        checker.check_waypoints(waypoints)


def test_geofence_all_inside_passes() -> None:
    checker = _make_checker_with_polygon(_NM_BOX)
    waypoints = [
        Waypoint(lat=34.02, lon=-106.08, alt_m=30.0),
        Waypoint(lat=34.05, lon=-106.05, alt_m=40.0),
        Waypoint(lat=34.09, lon=-106.02, alt_m=30.0),
    ]
    checker.check_waypoints(waypoints)  # should not raise


def test_geofence_no_polygon_is_noop() -> None:
    """When no geofence polygon is configured, all waypoints pass."""
    checker = GeofenceChecker.__new__(GeofenceChecker)
    checker._world_name = "test"
    checker._polygon = None
    checker._loaded = True
    checker._worlds_dir = Path("/nonexistent")

    wp = Waypoint(lat=99.0, lon=199.0, alt_m=30.0)  # clearly invalid coords
    checker.check_waypoint(wp)  # should not raise


def test_geofence_missing_world_file_is_noop(tmp_path: Path) -> None:
    """If the world YAML file doesn't exist, geofence is disabled (no error)."""
    checker = GeofenceChecker(world_name="nonexistent_ranch", worlds_dir=tmp_path)
    wp = Waypoint(lat=99.0, lon=199.0, alt_m=30.0)
    checker.check_waypoint(wp)  # should not raise


def test_geofence_world_file_without_key_is_noop(tmp_path: Path) -> None:
    """A world YAML without a 'geofence' key disables the check."""
    yaml_file = tmp_path / "my_ranch.yaml"
    yaml_file.write_text("name: my_ranch\nbounds_m: [2000.0, 2000.0]\n")

    checker = GeofenceChecker(world_name="my_ranch", worlds_dir=tmp_path)
    wp = Waypoint(lat=99.0, lon=199.0, alt_m=30.0)
    checker.check_waypoint(wp)  # should not raise


def test_geofence_world_file_with_polygon(tmp_path: Path) -> None:
    """A world YAML with a 'geofence' key enforces the polygon."""
    yaml_file = tmp_path / "fenced_ranch.yaml"
    yaml_file.write_text(
        "name: fenced_ranch\n"
        "geofence:\n"
        "  - [34.00, -106.10]\n"
        "  - [34.10, -106.10]\n"
        "  - [34.10, -106.00]\n"
        "  - [34.00, -106.00]\n"
    )

    checker = GeofenceChecker(world_name="fenced_ranch", worlds_dir=tmp_path)

    inside = Waypoint(lat=34.05, lon=-106.05, alt_m=30.0)
    checker.check_waypoint(inside)  # passes

    outside = Waypoint(lat=35.0, lon=-105.0, alt_m=30.0)
    with pytest.raises(GeofenceViolation):
        checker.check_waypoint(outside)


# ---------------------------------------------------------------------------
# BatteryGuard
# ---------------------------------------------------------------------------


def test_battery_guard_takeoff_ok() -> None:
    guard = BatteryGuard()
    guard.check_takeoff(80.0)  # well above 30% — should not raise


def test_battery_guard_takeoff_exactly_at_minimum() -> None:
    guard = BatteryGuard(min_takeoff_pct=30.0)
    guard.check_takeoff(30.0)  # at threshold — passes (not below)


def test_battery_guard_takeoff_too_low() -> None:
    guard = BatteryGuard()
    with pytest.raises(BatteryTooLow):
        guard.check_takeoff(25.0)


def test_battery_guard_should_rth_below_threshold() -> None:
    guard = BatteryGuard(rth_threshold_pct=25.0)
    assert guard.should_rth(20.0) is True
    assert guard.should_rth(25.0) is True  # at threshold triggers RTH


def test_battery_guard_should_rth_above_threshold() -> None:
    guard = BatteryGuard(rth_threshold_pct=25.0)
    assert guard.should_rth(26.0) is False
    assert guard.should_rth(100.0) is False


def test_battery_guard_in_flight_rth_raises() -> None:
    guard = BatteryGuard()
    with pytest.raises(BatteryTooLow):
        guard.check_in_flight(20.0)


def test_battery_guard_in_flight_ok() -> None:
    guard = BatteryGuard()
    guard.check_in_flight(50.0)  # should not raise


def test_battery_guard_custom_thresholds() -> None:
    guard = BatteryGuard(rth_threshold_pct=35.0, min_takeoff_pct=40.0)
    with pytest.raises(BatteryTooLow):
        guard.check_takeoff(39.0)
    assert guard.should_rth(35.0) is True
    assert guard.should_rth(36.0) is False


# ---------------------------------------------------------------------------
# WindGuard
# ---------------------------------------------------------------------------


def test_wind_guard_default_mavic_ceiling() -> None:
    guard = WindGuard()
    assert guard.ceiling_kt == WIND_CEILING_MAVIC_KT


def test_wind_guard_below_ceiling_passes() -> None:
    guard = WindGuard(ceiling_kt=WIND_CEILING_MAVIC_KT)
    guard.check(10.0)  # should not raise


def test_wind_guard_at_ceiling_passes() -> None:
    guard = WindGuard(ceiling_kt=21.0)
    guard.check(21.0)  # exactly at ceiling — not exceeded


def test_wind_guard_above_ceiling_raises() -> None:
    guard = WindGuard(ceiling_kt=21.0)
    with pytest.raises(WindTooHigh):
        guard.check(22.0)


def test_wind_guard_f3_ceiling() -> None:
    guard = WindGuard(ceiling_kt=WIND_CEILING_F3_KT)
    assert guard.ceiling_kt == 18.0
    guard.check(17.9)  # passes
    with pytest.raises(WindTooHigh):
        guard.check(18.1)


def test_wind_guard_error_message_contains_speeds() -> None:
    guard = WindGuard(ceiling_kt=21.0)
    try:
        guard.check(25.0)
    except WindTooHigh as exc:
        assert "25.0" in str(exc)
        assert "21" in str(exc)
