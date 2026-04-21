"""Tests for ThermalCamSensor — reading payload and predator.thermal_hit alert."""

from __future__ import annotations

import pytest

from skyherd.sensors.thermal import ThermalCamSensor, _in_cone
from skyherd.world.predators import Predator, PredatorSpecies, PredatorState


@pytest.mark.asyncio
async def test_thermal_reading_published_no_predators(world, mock_bus) -> None:
    """Tick publishes a thermal.reading with zero detected predators."""
    world.predator_spawner.predators = []
    sensor = ThermalCamSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        cam_id="therm_1",
        period_s=15.0,
    )
    await sensor.tick()

    topic = "skyherd/ranch_a/thermal/therm_1"
    msgs = mock_bus.all_payloads(topic)
    assert len(msgs) == 1
    p = msgs[0]
    assert p["kind"] == "thermal.reading"
    assert p["predators_detected"] == 0
    assert p["hits"] == []
    assert "cam_pos" in p
    assert "cam_heading_deg" in p


@pytest.mark.asyncio
async def test_thermal_hit_alert_in_cone(world, mock_bus) -> None:
    """Predator inside camera cone triggers predator.thermal_hit alert."""
    barn_pos = world.terrain.config.barn.pos  # (1850, 1850)
    # Camera heading is 0° (east in math coords = +x direction).
    # Place predator due east of barn — diff=0, well within 30° half-angle.
    pred = Predator(
        id="pred_cone",
        species=PredatorSpecies.MOUNTAIN_LION,
        pos=(barn_pos[0] + 50.0, barn_pos[1]),  # due east, 50m
        heading_deg=0.0,
        state=PredatorState.APPROACHING,
        size_kg=65.0,
        thermal_signature=0.7,
    )
    world.predator_spawner.predators = [pred]

    sensor = ThermalCamSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        cam_id="therm_1",
        period_s=15.0,
    )
    await sensor.tick()

    alert_topic = "skyherd/ranch_a/alert/thermal_hit"
    alerts = mock_bus.all_payloads(alert_topic)
    assert len(alerts) >= 1
    assert alerts[0]["kind"] == "predator.thermal_hit"
    assert alerts[0]["predator_id"] == "pred_cone"


@pytest.mark.asyncio
async def test_thermal_no_hit_outside_range(world, mock_bus) -> None:
    """Predator beyond 300m range is not detected."""
    barn_pos = world.terrain.config.barn.pos
    # Place predator 500m away (beyond _CAM_RANGE_M=300)
    pred = Predator(
        id="pred_far",
        species=PredatorSpecies.COYOTE,
        pos=(barn_pos[0] - 500.0, barn_pos[1]),
        heading_deg=0.0,
        state=PredatorState.ROAMING,
        size_kg=13.0,
        thermal_signature=0.4,
    )
    world.predator_spawner.predators = [pred]

    sensor = ThermalCamSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        cam_id="therm_1",
        period_s=15.0,
    )
    await sensor.tick()

    # Reading is published but no thermal_hit alert
    topic = "skyherd/ranch_a/thermal/therm_1"
    msgs = mock_bus.all_payloads(topic)
    assert len(msgs) == 1
    assert msgs[0]["predators_detected"] == 0

    alert_topic = "skyherd/ranch_a/alert/thermal_hit"
    assert mock_bus.all_payloads(alert_topic) == []


def test_in_cone_within_angle_and_range() -> None:
    """Point directly in front of camera is in cone."""
    assert _in_cone((0.0, 0.0), 0.0, (100.0, 0.0)) is True


def test_in_cone_outside_angle() -> None:
    """Point behind camera is not in cone."""
    assert _in_cone((0.0, 0.0), 0.0, (-100.0, 0.0)) is False


def test_in_cone_exactly_at_origin() -> None:
    """Point at camera position is always in cone."""
    assert _in_cone((100.0, 100.0), 45.0, (100.0, 100.0)) is True


def test_in_cone_beyond_range() -> None:
    """Point more than 300m away is not in cone."""
    assert _in_cone((0.0, 0.0), 0.0, (400.0, 0.0)) is False
