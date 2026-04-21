"""Tests for WeatherSensor — reading payload and storm alert."""

from __future__ import annotations

import pytest

from skyherd.sensors.weather import WeatherSensor


@pytest.mark.asyncio
async def test_weather_reading_published(world, mock_bus) -> None:
    """Tick emits a weather.reading payload with all required fields."""
    sensor = WeatherSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        station_id="station_1",
        period_s=30.0,
    )
    await sensor.tick()

    topic = "skyherd/ranch_a/weather/station_1"
    msgs = mock_bus.all_payloads(topic)
    assert len(msgs) == 1
    p = msgs[0]
    assert p["kind"] == "weather.reading"
    assert "wind_kt" in p
    assert "wind_dir_deg" in p
    assert "temp_f" in p
    assert "conditions" in p
    assert p["ranch"] == "ranch_a"
    assert p["entity"] == "station_1"


@pytest.mark.asyncio
async def test_weather_storm_alert_fires(world, mock_bus) -> None:
    """weather.storm alert published when conditions == 'storm'."""
    # Schedule a storm at t=0 so it fires immediately
    world.weather_driver.schedule_storm(at_s=0.0, duration_s=300.0, severity=1.0)
    world.step(dt=1.0)  # advance world so storm activates

    sensor = WeatherSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        station_id="station_1",
        period_s=30.0,
    )

    # Verify world is in storm
    assert str(world.weather_driver.current.conditions) == "storm"

    await sensor.tick()

    alert_topic = "skyherd/ranch_a/alert/weather_storm"
    alerts = mock_bus.all_payloads(alert_topic)
    assert len(alerts) >= 1
    assert alerts[0]["kind"] == "weather.storm"
    assert alerts[0]["ranch"] == "ranch_a"


@pytest.mark.asyncio
async def test_weather_no_storm_alert_when_clear(world, mock_bus) -> None:
    """No storm alert published under clear conditions."""
    # Default world starts clear
    assert str(world.weather_driver.current.conditions) != "storm"

    sensor = WeatherSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        station_id="station_1",
        period_s=30.0,
    )
    await sensor.tick()

    alert_topic = "skyherd/ranch_a/alert/weather_storm"
    assert mock_bus.all_payloads(alert_topic) == []


@pytest.mark.asyncio
async def test_weather_storm_multiple_ticks_single_log_transition(world, mock_bus) -> None:
    """Storm alert fires on each tick while storm is active (stateless alert)."""
    world.weather_driver.schedule_storm(at_s=0.0, duration_s=3600.0, severity=1.0)
    world.step(dt=1.0)

    sensor = WeatherSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        station_id="station_1",
        period_s=30.0,
    )

    await sensor.tick()
    await sensor.tick()

    alert_topic = "skyherd/ranch_a/alert/weather_storm"
    alerts = mock_bus.all_payloads(alert_topic)
    # Each tick during a storm fires an alert
    assert len(alerts) >= 2
