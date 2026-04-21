"""Tests for AcousticEmitterSensor — state publishing and command handling."""

from __future__ import annotations

import asyncio

import pytest

from skyherd.sensors.acoustic import AcousticEmitterSensor


@pytest.mark.asyncio
async def test_acoustic_reading_published(world, mock_bus) -> None:
    """Tick publishes acoustic.reading with default state."""
    sensor = AcousticEmitterSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        emitter_id="emit_1",
        period_s=30.0,
    )
    await sensor.tick()

    topic = "skyherd/ranch_a/acoustic/emit_1"
    msgs = mock_bus.all_payloads(topic)
    assert len(msgs) == 1
    p = msgs[0]
    assert p["kind"] == "acoustic.reading"
    assert p["entity"] == "emit_1"
    assert p["active"] is False
    assert "frequency_hz" in p
    assert "pattern" in p
    assert "target_conditioning_phase" in p


@pytest.mark.asyncio
async def test_acoustic_apply_command_activates(world, mock_bus) -> None:
    """_apply_command updates active state."""
    sensor = AcousticEmitterSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        emitter_id="emit_1",
        period_s=30.0,
    )
    assert sensor._active is False
    sensor._apply_command({"active": True, "frequency_hz": 20000.0, "pattern": "sweep"})
    assert sensor._active is True
    assert sensor._frequency_hz == 20000.0
    assert sensor._pattern == "sweep"


@pytest.mark.asyncio
async def test_acoustic_apply_command_partial_update(world, mock_bus) -> None:
    """_apply_command with partial keys only updates provided fields."""
    sensor = AcousticEmitterSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        emitter_id="emit_1",
        period_s=30.0,
    )
    original_freq = sensor._frequency_hz
    sensor._apply_command({"conditioning_phase": "aversion"})
    assert sensor._conditioning_phase == "aversion"
    assert sensor._frequency_hz == original_freq  # unchanged


@pytest.mark.asyncio
async def test_acoustic_tick_reflects_activated_state(world, mock_bus) -> None:
    """After activation, tick payload shows active=True."""
    sensor = AcousticEmitterSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        emitter_id="emit_1",
        period_s=30.0,
    )
    sensor._apply_command({"active": True})
    await sensor.tick()

    topic = "skyherd/ranch_a/acoustic/emit_1"
    msgs = mock_bus.all_payloads(topic)
    assert msgs[-1]["active"] is True


@pytest.mark.asyncio
async def test_acoustic_run_cancels_cleanly(world, mock_bus) -> None:
    """run() task (which spawns cmd listener) cancels without error."""
    sensor = AcousticEmitterSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        emitter_id="emit_1",
        period_s=0.01,
    )

    # MockBus.subscribe is not implemented — patch the listener to be a no-op
    from unittest.mock import patch

    async def fake_listen():
        await asyncio.sleep(9999)

    with patch.object(sensor, "_listen_commands", new=fake_listen):
        task = asyncio.create_task(sensor.run())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass  # expected
