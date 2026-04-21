"""Tests for CollarSensor — reading payload and low-battery alert."""

from __future__ import annotations

import pytest

from skyherd.sensors.collar import _LOW_BATTERY_THRESHOLD_PCT, CollarSensor


@pytest.mark.asyncio
async def test_collar_reading_published(world, mock_bus) -> None:
    """Tick emits a collar.reading payload with required fields."""
    cow_id = world.herd.cows[0].id  # first cow
    sensor = CollarSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        cow_id=cow_id,
        period_s=60.0,
    )
    await sensor.tick()

    topic = f"skyherd/ranch_a/collar/{cow_id}"
    msgs = mock_bus.all_payloads(topic)
    assert len(msgs) == 1
    p = msgs[0]
    assert p["kind"] == "collar.reading"
    assert p["entity"] == cow_id
    assert "pos" in p
    assert "heading_deg" in p
    assert "activity" in p
    assert p["activity"] in {"walking", "grazing", "resting"}
    assert "battery_pct" in p
    assert 0.0 <= p["battery_pct"] <= 100.0


@pytest.mark.asyncio
async def test_collar_low_battery_alert_fires(world, mock_bus) -> None:
    """collar.low_battery alert fires when battery drops below threshold."""
    cow_id = world.herd.cows[0].id
    sensor = CollarSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        cow_id=cow_id,
        period_s=60.0,
        # Start just above threshold so first tick drops it below
        initial_battery_pct=_LOW_BATTERY_THRESHOLD_PCT + 0.01,
    )

    await sensor.tick()  # battery drain drops it below threshold

    alert_topic = "skyherd/ranch_a/alert/collar_low_battery"
    alerts = mock_bus.all_payloads(alert_topic)
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "collar.low_battery"
    assert alerts[0]["entity"] == cow_id
    assert alerts[0]["battery_pct"] < _LOW_BATTERY_THRESHOLD_PCT


@pytest.mark.asyncio
async def test_collar_low_battery_fires_once(world, mock_bus) -> None:
    """collar.low_battery is debounced — fires only once per episode."""
    cow_id = world.herd.cows[0].id
    sensor = CollarSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        cow_id=cow_id,
        period_s=60.0,
        initial_battery_pct=5.0,  # already low
    )

    await sensor.tick()
    await sensor.tick()
    await sensor.tick()

    alert_topic = "skyherd/ranch_a/alert/collar_low_battery"
    alerts = mock_bus.all_payloads(alert_topic)
    assert len(alerts) == 1, "Low battery alert must fire only once per episode"


@pytest.mark.asyncio
async def test_collar_no_alert_when_battery_ok(world, mock_bus) -> None:
    """No low-battery alert when battery is well above threshold."""
    cow_id = world.herd.cows[0].id
    sensor = CollarSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        cow_id=cow_id,
        period_s=60.0,
        initial_battery_pct=90.0,
    )
    await sensor.tick()

    alert_topic = "skyherd/ranch_a/alert/collar_low_battery"
    assert mock_bus.all_payloads(alert_topic) == []


@pytest.mark.asyncio
async def test_collar_activity_classification(world, mock_bus) -> None:
    """Activity field is one of walking/grazing/resting on multiple ticks."""
    cow_id = world.herd.cows[0].id
    sensor = CollarSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        cow_id=cow_id,
        period_s=60.0,
        initial_battery_pct=90.0,
    )
    valid_activities = {"walking", "grazing", "resting"}
    for _ in range(5):
        await sensor.tick()

    topic = f"skyherd/ranch_a/collar/{cow_id}"
    for msg in mock_bus.all_payloads(topic):
        assert msg["activity"] in valid_activities
