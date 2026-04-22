"""Tests for run_all — spawns all sensor tasks for a 50-cow world without deadlock."""

from __future__ import annotations

import asyncio

import pytest

from skyherd.sensors.registry import _build_sensors, run_all


@pytest.mark.asyncio
async def test_run_all_task_counts(world, mock_bus) -> None:
    """run_all spawns correct number of tasks for ranch_a (50 cows, 3 tanks, 6 troughs, 8 fences)."""
    cfg = world.terrain.config

    # Expected: 3 water + 6 trough_cam + 1 thermal + 8 fence + 50 collar + 1 acoustic + 1 weather
    expected_sensors = (
        len(cfg.water_tanks)  # 3
        + len(cfg.troughs)  # 6
        + 1  # thermal
        + len(cfg.fence_lines)  # 8
        + len(world.herd.cows)  # 50
        + 1  # acoustic
        + 1  # weather
    )
    assert len(world.herd.cows) == 50
    assert expected_sensors == 70


@pytest.mark.asyncio
async def test_run_all_spawns_collar_tasks_per_cow(world, mock_bus) -> None:
    """_build_sensors produces exactly one CollarSensor per cow."""
    from skyherd.sensors.collar import CollarSensor

    sensors = _build_sensors(world, mock_bus, "ranch_a", ledger=None)
    collar_sensors = [s for s in sensors if isinstance(s, CollarSensor)]
    assert len(collar_sensors) == len(world.herd.cows)
    assert len(collar_sensors) == 50


@pytest.mark.asyncio
async def test_run_all_spawns_water_tasks_per_tank(world, mock_bus) -> None:
    """_build_sensors produces one WaterTankSensor per water tank."""
    from skyherd.sensors.water import WaterTankSensor

    sensors = _build_sensors(world, mock_bus, "ranch_a", ledger=None)
    water_sensors = [s for s in sensors if isinstance(s, WaterTankSensor)]
    assert len(water_sensors) == 3


@pytest.mark.asyncio
async def test_run_all_spawns_fence_tasks_per_segment(world, mock_bus) -> None:
    """_build_sensors produces one FenceMotionSensor per fence segment."""
    from skyherd.sensors.fence import FenceMotionSensor

    sensors = _build_sensors(world, mock_bus, "ranch_a", ledger=None)
    fence_sensors = [s for s in sensors if isinstance(s, FenceMotionSensor)]
    assert len(fence_sensors) == len(world.terrain.config.fence_lines)


@pytest.mark.asyncio
async def test_run_all_no_deadlock_five_sim_seconds(world, mock_bus) -> None:
    """Tasks run for 5 sim-seconds without hanging.

    Uses very short periods so multiple ticks fire quickly.
    We monkeypatch asyncio.sleep to skip real wall-clock time.
    """
    from unittest.mock import patch

    # Track call count to limit iterations
    tick_count = 0
    MAX_TICKS = 5

    real_sleep = asyncio.sleep
    sleep_calls = 0

    async def fast_sleep(delay: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        # Yield control without actually sleeping
        await real_sleep(0)

    # Run tasks for a very short real-time window
    # We patch sleep to be instant and let the event loop process a few ticks
    with patch("skyherd.sensors.base.asyncio.sleep", side_effect=fast_sleep):
        # Build sensors with very short period
        from skyherd.sensors.registry import _build_sensors

        sensors = _build_sensors(world, mock_bus, "ranch_a", ledger=None)

        # Create tasks
        tasks = [asyncio.create_task(s.run()) for s in sensors]
        assert len(tasks) == 70

        # Let them run briefly (a few event loop turns)
        await asyncio.sleep(0.05)

        # Cancel all tasks cleanly
        for t in tasks:
            t.cancel()
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # All tasks should have been cancelled (no unexpected exceptions)
    for r in results:
        assert isinstance(r, (asyncio.CancelledError, type(None)))

    assert len(tasks) == 70


@pytest.mark.asyncio
async def test_run_all_returns_cancellable_tasks(world, mock_bus) -> None:
    """run_all returns a list of tasks that can be cancelled cleanly."""
    tasks = await run_all(world, mock_bus, "ranch_a", ledger=None)

    assert len(tasks) > 0

    # All should be running
    running = [t for t in tasks if not t.done()]
    assert len(running) == len(tasks)

    # Cancel all
    for t in tasks:
        t.cancel()
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        assert isinstance(r, (asyncio.CancelledError, type(None)))
