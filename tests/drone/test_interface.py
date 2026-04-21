"""
Contract tests for the DroneBackend abstract interface.

Verifies that:
- All required abstract methods are declared on DroneBackend.
- DroneBackend cannot be instantiated directly.
- Waypoint and DroneState have the expected fields and defaults.
- get_backend() factory dispatches to StubBackend when name="stub".
- get_backend() raises DroneError for unknown backend names.
"""

from __future__ import annotations

import inspect

import pytest

from skyherd.drone.interface import (
    DroneBackend,
    DroneError,
    DroneState,
    DroneUnavailable,
    Waypoint,
    get_backend,
)

# ---------------------------------------------------------------------------
# Abstract method contract
# ---------------------------------------------------------------------------

REQUIRED_METHODS = {
    "connect",
    "takeoff",
    "patrol",
    "return_to_home",
    "play_deterrent",
    "get_thermal_clip",
    "state",
    "disconnect",
}


def test_all_abstract_methods_declared() -> None:
    """Every required method must be declared as abstract on DroneBackend."""
    abstract_methods = getattr(DroneBackend, "__abstractmethods__", set())
    missing = REQUIRED_METHODS - abstract_methods
    assert not missing, f"Methods not abstract: {missing}"


def test_drone_backend_not_instantiable() -> None:
    """DroneBackend is abstract — direct instantiation must fail."""
    with pytest.raises(TypeError):
        DroneBackend()  # type: ignore[abstract]


def test_all_required_methods_are_coroutines() -> None:
    """Each abstract method must be declared as a coroutine function."""
    for name in REQUIRED_METHODS:
        method = getattr(DroneBackend, name)
        assert inspect.iscoroutinefunction(method), f"DroneBackend.{name} must be an async method"


# ---------------------------------------------------------------------------
# Waypoint model
# ---------------------------------------------------------------------------


def test_waypoint_required_fields() -> None:
    wp = Waypoint(lat=34.0, lon=-106.0, alt_m=30.0)
    assert wp.lat == pytest.approx(34.0)
    assert wp.lon == pytest.approx(-106.0)
    assert wp.alt_m == pytest.approx(30.0)
    assert wp.hold_s == pytest.approx(0.0)  # default


def test_waypoint_hold_s_optional() -> None:
    wp = Waypoint(lat=0.0, lon=0.0, alt_m=10.0, hold_s=5.0)
    assert wp.hold_s == pytest.approx(5.0)


def test_waypoint_is_pydantic_model() -> None:
    from pydantic import BaseModel

    assert issubclass(Waypoint, BaseModel)


def test_waypoint_rejects_missing_required_fields() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Waypoint(lat=34.0)  # type: ignore[call-arg]  # missing lon + alt_m


# ---------------------------------------------------------------------------
# DroneState dataclass
# ---------------------------------------------------------------------------


def test_drone_state_defaults() -> None:
    s = DroneState()
    assert s.armed is False
    assert s.in_air is False
    assert s.altitude_m == pytest.approx(0.0)
    assert s.battery_pct == pytest.approx(100.0)
    assert s.mode == "UNKNOWN"
    assert s.lat == pytest.approx(0.0)
    assert s.lon == pytest.approx(0.0)


def test_drone_state_mutable() -> None:
    s = DroneState()
    s.armed = True
    assert s.armed is True


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


def test_drone_unavailable_is_drone_error() -> None:
    assert issubclass(DroneUnavailable, DroneError)


def test_drone_error_is_exception() -> None:
    assert issubclass(DroneError, Exception)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_get_backend_stub_returns_stub_instance() -> None:
    from skyherd.drone.stub import StubBackend

    backend = get_backend("stub")
    assert isinstance(backend, StubBackend)


def test_get_backend_unknown_raises_drone_error() -> None:
    with pytest.raises(DroneError):
        get_backend("nonexistent_backend_xyz")


def test_get_backend_returns_drone_backend_subclass() -> None:
    backend = get_backend("stub")
    assert isinstance(backend, DroneBackend)
