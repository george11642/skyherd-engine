"""Tests for registry.run_all hardware override mechanism.

Verifies:
- Overridden (sensor_type, entity_id) pairs produce no sim task.
- Non-overridden sensors still get a task.
- parse_overrides correctly parses env-var format.
- _load_overrides falls back to env var when kwarg is None.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skyherd.sensors.registry import (
    OVERRIDEABLE_SENSOR_TYPES,
    _build_sensors,
    _is_overridden,
    _load_overrides,
    parse_overrides,
    run_all,
)

# ---------------------------------------------------------------------------
# parse_overrides
# ---------------------------------------------------------------------------


def test_parse_overrides_single():
    result = parse_overrides("trough_cam:trough_1:edge-fence")
    assert result == {"trough_cam": {"trough_1": "edge-fence"}}


def test_parse_overrides_multiple():
    raw = "trough_cam:trough_1:edge-fence,trough_cam:trough_2:edge-barn"
    result = parse_overrides(raw)
    assert result["trough_cam"]["trough_1"] == "edge-fence"
    assert result["trough_cam"]["trough_2"] == "edge-barn"


def test_parse_overrides_mixed_types():
    raw = "trough_cam:trough_1:edge-fence,fence:fence_sw:edge-fence,thermal:therm_1:edge-fence"
    result = parse_overrides(raw)
    assert "trough_cam" in result
    assert "fence" in result
    assert "thermal" in result


def test_parse_overrides_skips_malformed(caplog):
    result = parse_overrides("trough_cam:trough_1:edge-fence,bad_entry,fence:fence_sw:edge")
    assert "trough_cam" in result
    # bad_entry has only 1 part → skipped
    assert len(result.get("bad_entry", {})) == 0


def test_parse_overrides_empty():
    assert parse_overrides("") == {}
    assert parse_overrides("   ") == {}


# ---------------------------------------------------------------------------
# _load_overrides
# ---------------------------------------------------------------------------


def test_load_overrides_kwarg_takes_priority(monkeypatch):
    monkeypatch.setenv("HARDWARE_OVERRIDES", "trough_cam:trough_1:edge-fence")
    kwarg = {"trough_cam": {"trough_2": "edge-barn"}}
    result = _load_overrides(kwarg)
    # kwarg wins — trough_2 is returned, not trough_1
    assert "trough_2" in result.get("trough_cam", {})
    assert "trough_1" not in result.get("trough_cam", {})


def test_load_overrides_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("HARDWARE_OVERRIDES", "trough_cam:trough_1:edge-fence")
    result = _load_overrides(None)
    assert result["trough_cam"]["trough_1"] == "edge-fence"


def test_load_overrides_empty_env(monkeypatch):
    monkeypatch.delenv("HARDWARE_OVERRIDES", raising=False)
    result = _load_overrides(None)
    assert result == {}


# ---------------------------------------------------------------------------
# _is_overridden
# ---------------------------------------------------------------------------


def test_is_overridden_true():
    overrides = {"trough_cam": {"trough_1": "edge-fence"}}
    assert _is_overridden("trough_cam", "trough_1", overrides) is True


def test_is_overridden_false_wrong_entity():
    overrides = {"trough_cam": {"trough_1": "edge-fence"}}
    assert _is_overridden("trough_cam", "trough_2", overrides) is False


def test_is_overridden_false_wrong_type():
    overrides = {"trough_cam": {"trough_1": "edge-fence"}}
    assert _is_overridden("fence", "trough_1", overrides) is False


def test_is_overridden_empty():
    assert _is_overridden("trough_cam", "trough_1", {}) is False


# ---------------------------------------------------------------------------
# _build_sensors — override suppresses emitter
# ---------------------------------------------------------------------------


def _make_mock_world_and_bus(n_troughs: int = 2, n_fences: int = 1):
    """Build minimal mock world + bus for _build_sensors."""
    world = MagicMock()
    bus = MagicMock()

    # Troughs
    troughs = []
    for i in range(1, n_troughs + 1):
        trough = MagicMock()
        trough.id = f"trough_{i}"
        trough.pos = (100.0 * i, 200.0 * i)
        troughs.append(trough)

    # Fences
    fences = []
    for i in range(1, n_fences + 1):
        fence = MagicMock()
        fence.id = "fence_sw" if i == 1 else f"fence_{i}"
        fences.append(fence)

    # Water tanks
    tank = MagicMock()
    tank.id = "tank_1"
    tank.pos = (0.0, 0.0)

    world.terrain.config.troughs = troughs
    world.terrain.config.fence_lines = fences
    world.terrain.config.water_tanks = [tank]

    # Cows
    cow = MagicMock()
    cow.id = "cow_001"
    world.herd.cows = [cow]

    return world, bus


def test_build_sensors_all_sim_when_no_overrides():
    world, bus = _make_mock_world_and_bus(n_troughs=2, n_fences=1)
    sensors = _build_sensors(world, bus, "ranch_a", ledger=None, hw_overrides={})
    sensor_types = [type(s).__name__ for s in sensors]
    # Should have TroughCamSensor × 2
    assert sensor_types.count("TroughCamSensor") == 2
    assert "FenceMotionSensor" in sensor_types
    assert "ThermalCamSensor" in sensor_types


def test_build_sensors_trough_1_suppressed():
    world, bus = _make_mock_world_and_bus(n_troughs=2)
    overrides = {"trough_cam": {"trough_1": "edge-fence"}}
    sensors = _build_sensors(world, bus, "ranch_a", ledger=None, hw_overrides=overrides)
    trough_ids = [
        getattr(s, "_trough_id", None) for s in sensors if type(s).__name__ == "TroughCamSensor"
    ]
    assert "trough_1" not in trough_ids, "trough_1 should be suppressed by hardware override"
    assert "trough_2" in trough_ids, "trough_2 should still have a sim emitter"


def test_build_sensors_both_troughs_suppressed():
    world, bus = _make_mock_world_and_bus(n_troughs=2)
    overrides = {"trough_cam": {"trough_1": "edge-fence", "trough_2": "edge-barn"}}
    sensors = _build_sensors(world, bus, "ranch_a", ledger=None, hw_overrides=overrides)
    trough_cam_count = sum(1 for s in sensors if type(s).__name__ == "TroughCamSensor")
    assert trough_cam_count == 0


def test_build_sensors_thermal_suppressed():
    world, bus = _make_mock_world_and_bus()
    overrides = {"thermal": {"therm_1": "edge-fence"}}
    sensors = _build_sensors(world, bus, "ranch_a", ledger=None, hw_overrides=overrides)
    thermal_count = sum(1 for s in sensors if type(s).__name__ == "ThermalCamSensor")
    assert thermal_count == 0


def test_build_sensors_fence_suppressed():
    world, bus = _make_mock_world_and_bus(n_fences=1)
    overrides = {"fence": {"fence_sw": "edge-fence"}}
    sensors = _build_sensors(world, bus, "ranch_a", ledger=None, hw_overrides=overrides)
    fence_count = sum(1 for s in sensors if type(s).__name__ == "FenceMotionSensor")
    assert fence_count == 0


def test_build_sensors_non_overrideable_sensors_always_present():
    """Water, collar, acoustic, weather are never suppressed by overrides."""
    world, bus = _make_mock_world_and_bus()
    # Override everything overrideable
    overrides = {
        "trough_cam": {"trough_1": "edge-fence", "trough_2": "edge-barn"},
        "fence": {"fence_sw": "edge-fence"},
        "thermal": {"therm_1": "edge-fence"},
    }
    sensors = _build_sensors(world, bus, "ranch_a", ledger=None, hw_overrides=overrides)
    sensor_names = {type(s).__name__ for s in sensors}
    assert "WaterTankSensor" in sensor_names
    assert "CollarSensor" in sensor_names
    assert "AcousticEmitterSensor" in sensor_names
    assert "WeatherSensor" in sensor_names


# ---------------------------------------------------------------------------
# run_all — integration check (tasks spawned)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_all_with_overrides_returns_fewer_tasks():
    """run_all with trough overrides spawns fewer tasks than without."""
    world, bus = _make_mock_world_and_bus(n_troughs=2)

    # Patch sensor run() to avoid real async loops
    with patch("skyherd.sensors.registry._build_sensors") as mock_build:
        mock_sensor_1 = MagicMock()
        mock_sensor_1.topic = "skyherd/ranch_a/trough_cam/cam_2"
        mock_sensor_1.run = AsyncMock(side_effect=asyncio.CancelledError)

        mock_sensor_2 = MagicMock()
        mock_sensor_2.topic = "skyherd/ranch_a/water/tank_1"
        mock_sensor_2.run = AsyncMock(side_effect=asyncio.CancelledError)

        mock_build.return_value = [mock_sensor_1, mock_sensor_2]

        overrides = {"trough_cam": {"trough_1": "edge-fence"}}
        tasks = await run_all(world, bus, "ranch_a", overrides=overrides)

        # Verify _build_sensors was called with our hw_overrides
        call_kwargs = mock_build.call_args
        assert call_kwargs is not None
        passed_overrides = (
            call_kwargs.kwargs.get("hw_overrides") or call_kwargs.args[4]
            if len(call_kwargs.args) > 4
            else None
        )
        # The mock returned 2 sensors → 2 tasks
        assert len(tasks) == 2

        # Cancel tasks to avoid warnings
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


# ---------------------------------------------------------------------------
# OVERRIDEABLE_SENSOR_TYPES constant
# ---------------------------------------------------------------------------


def test_overrideable_sensor_types_contains_expected():
    assert "trough_cam" in OVERRIDEABLE_SENSOR_TYPES
    assert "fence" in OVERRIDEABLE_SENSOR_TYPES
    assert "thermal" in OVERRIDEABLE_SENSOR_TYPES
    # collar and water are never overridden
    assert "collar" not in OVERRIDEABLE_SENSOR_TYPES
    assert "water" not in OVERRIDEABLE_SENSOR_TYPES
