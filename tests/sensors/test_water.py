"""Tests for WaterTankSensor — level reading and water.low debounce."""

from __future__ import annotations

import pytest

from skyherd.sensors.water import WaterTankSensor


@pytest.mark.asyncio
async def test_water_reading_published(world, mock_bus) -> None:
    """Tick publishes a water.reading payload."""
    tank_cfg = world.terrain.config.water_tanks[0]  # wt_sw, level=82%
    sensor = WaterTankSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        tank_cfg=tank_cfg,
        period_s=5.0,
    )
    await sensor.tick()

    expected_topic = "skyherd/ranch_a/water/wt_sw"
    msgs = mock_bus.all_payloads(expected_topic)
    assert len(msgs) == 1
    payload = msgs[0]
    assert payload["kind"] == "water.reading"
    assert payload["entity"] == "wt_sw"
    assert payload["level_pct"] == pytest.approx(82.0, abs=0.1)
    assert "pressure_psi" in payload
    assert "flow_lpm" in payload
    assert "temp_f" in payload


@pytest.mark.asyncio
async def test_water_low_fires_once_below_threshold(world, mock_bus) -> None:
    """water.low alert fires exactly once when tank at 15% (wt_n)."""
    # wt_n has level_pct=15.0 in ranch_a.yaml — below the 20% threshold
    tank_cfg = next(t for t in world.terrain.config.water_tanks if t.id == "wt_n")
    assert tank_cfg.level_pct < 20.0  # guard

    sensor = WaterTankSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        tank_cfg=tank_cfg,
        period_s=5.0,
    )

    # Tick three times — alert should fire only once
    await sensor.tick()
    await sensor.tick()
    await sensor.tick()

    alert_topic = "skyherd/ranch_a/alert/water_low"
    alerts = mock_bus.all_payloads(alert_topic)
    assert len(alerts) == 1, "water.low must fire exactly once (debounced)"
    assert alerts[0]["kind"] == "water.low"
    assert alerts[0]["entity"] == "wt_n"


@pytest.mark.asyncio
async def test_water_low_does_not_fire_above_threshold(world, mock_bus) -> None:
    """No water.low alert when tank level is above 20%."""
    tank_cfg = next(t for t in world.terrain.config.water_tanks if t.id == "wt_sw")
    assert tank_cfg.level_pct >= 20.0  # guard — wt_sw is at 82%

    sensor = WaterTankSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        tank_cfg=tank_cfg,
        period_s=5.0,
    )
    await sensor.tick()
    await sensor.tick()

    alert_topic = "skyherd/ranch_a/alert/water_low"
    assert mock_bus.all_payloads(alert_topic) == []


@pytest.mark.asyncio
async def test_water_low_debounce_resets_after_recovery(world, mock_bus) -> None:
    """After debounce fires, modifying level above threshold resets it."""
    tank_cfg = next(t for t in world.terrain.config.water_tanks if t.id == "wt_n")
    sensor = WaterTankSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        tank_cfg=tank_cfg,
        period_s=5.0,
    )

    await sensor.tick()  # fires alert (15%)

    # Simulate recovery by patching the tank level
    tank_cfg.__dict__["level_pct"] = 85.0  # above threshold
    await sensor.tick()  # debounce resets

    # Drop back below — should fire again
    tank_cfg.__dict__["level_pct"] = 10.0
    await sensor.tick()

    alert_topic = "skyherd/ranch_a/alert/water_low"
    alerts = mock_bus.all_payloads(alert_topic)
    assert len(alerts) == 2
