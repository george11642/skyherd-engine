"""Tests for FenceMotionSensor — breach detection and debounce."""

from __future__ import annotations

import pytest

from skyherd.sensors.fence import _DEBOUNCE_S, FenceMotionSensor
from skyherd.world.predators import Predator, PredatorSpecies, PredatorState


def _get_fence_cfg(world, fence_id: str):
    return next(f for f in world.terrain.config.fence_lines if f.id == fence_id)


@pytest.mark.asyncio
async def test_fence_breach_predator(world, mock_bus) -> None:
    """Predator on fence boundary triggers fence.breach with subject_kind=predator."""
    # Place a predator exactly on the south fence line (y=0)
    pred = Predator(
        id="pred_test",
        species=PredatorSpecies.COYOTE,
        pos=(500.0, 0.0),  # on fence_south (y=0)
        heading_deg=0.0,
        state=PredatorState.ROAMING,
        size_kg=13.0,
        thermal_signature=0.4,
    )
    world.predator_spawner.predators = [pred]

    fence_cfg = _get_fence_cfg(world, "fence_south")
    sensor = FenceMotionSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        fence_cfg=fence_cfg,
        period_s=3.0,
    )

    await sensor.tick()

    msgs = mock_bus.all_payloads("skyherd/ranch_a/fence/fence_south")
    assert len(msgs) == 1
    payload = msgs[0]
    assert payload["kind"] == "fence.breach"
    assert payload["subject_kind"] == "predator"
    assert payload["segment_id"] == "fence_south"
    assert payload["thermal_hint"] == pytest.approx(0.4, abs=0.01)


@pytest.mark.asyncio
async def test_fence_breach_debounced(world, mock_bus) -> None:
    """Second breach within debounce window is suppressed."""
    pred = Predator(
        id="pred_debound",
        species=PredatorSpecies.COYOTE,
        pos=(500.0, 0.0),
        heading_deg=0.0,
        state=PredatorState.ROAMING,
        size_kg=13.0,
        thermal_signature=0.4,
    )
    world.predator_spawner.predators = [pred]

    fence_cfg = _get_fence_cfg(world, "fence_south")
    sensor = FenceMotionSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        fence_cfg=fence_cfg,
        period_s=3.0,
    )

    await sensor.tick()  # fires
    await sensor.tick()  # debounced
    await sensor.tick()  # still debounced

    msgs = mock_bus.all_payloads("skyherd/ranch_a/fence/fence_south")
    assert len(msgs) == 1, "Debounce must suppress repeated alerts within cooldown"


@pytest.mark.asyncio
async def test_fence_breach_debounce_expires(world, mock_bus) -> None:
    """After debounce window passes, a new breach fires again."""

    pred = Predator(
        id="pred_expire",
        species=PredatorSpecies.COYOTE,
        pos=(500.0, 0.0),
        heading_deg=0.0,
        state=PredatorState.ROAMING,
        size_kg=13.0,
        thermal_signature=0.4,
    )
    world.predator_spawner.predators = [pred]

    fence_cfg = _get_fence_cfg(world, "fence_south")
    sensor = FenceMotionSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        fence_cfg=fence_cfg,
        period_s=3.0,
    )

    await sensor.tick()  # fires
    # Manually expire the debounce by backdating last_alert_time
    sensor._last_alert_time -= _DEBOUNCE_S + 1.0
    await sensor.tick()  # fires again

    msgs = mock_bus.all_payloads("skyherd/ranch_a/fence/fence_south")
    assert len(msgs) == 2


@pytest.mark.asyncio
async def test_fence_no_breach_no_publish(world, mock_bus) -> None:
    """No predators or cows on fence → nothing published."""
    world.predator_spawner.predators = []
    # All cows in ranch_a are well inside paddocks — far from fence segments
    # (no movement needed)

    fence_cfg = _get_fence_cfg(world, "fence_north")
    sensor = FenceMotionSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        fence_cfg=fence_cfg,
        period_s=3.0,
    )
    await sensor.tick()

    msgs = mock_bus.all_payloads("skyherd/ranch_a/fence/fence_north")
    assert msgs == []
