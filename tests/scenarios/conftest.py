"""Shared fixtures for scenario tests.

Provides:
- ``scenarios_snapshot``: autouse fixture that snapshots SCENARIOS dict before
  each test and restores it afterward, preventing cross-test pollution from
  any test that registers extra scenarios or mutates the dict.
- ``sick_pinkeye_world``: a minimal 2km×2km world with one pinkeye-positive cow
  (discharge=0.85) for use in pixel-path bbox pipeline assertions (Plan 05 Branch B).
"""

from __future__ import annotations

import random

import pytest


@pytest.fixture()
def sick_pinkeye_world():  # type: ignore[no-untyped-def]
    """A minimal world containing one pinkeye-positive cow (discharge=0.85).

    Duplicated from tests/vision/conftest.py for cross-directory fixture access
    (Option 1 per Plan 05 Task 3 spec — tests/conftest.py does not exist).
    """
    from datetime import UTC, datetime

    from skyherd.world.cattle import Cow, Herd
    from skyherd.world.clock import Clock
    from skyherd.world.predators import PredatorSpawner
    from skyherd.world.terrain import (
        BarnConfig,
        FenceLineConfig,
        PaddockConfig,
        Terrain,
        TerrainConfig,
        TroughConfig,
        WaterTankConfig,
    )
    from skyherd.world.weather import WeatherDriver
    from skyherd.world.world import World

    config = TerrainConfig(
        name="scenario_pinkeye_test",
        bounds_m=(2000.0, 2000.0),
        paddocks=[
            PaddockConfig(
                id="p_main",
                polygon=[(0.0, 0.0), (2000.0, 0.0), (2000.0, 2000.0), (0.0, 2000.0)],
            )
        ],
        water_tanks=[WaterTankConfig(id="wt1", pos=(200.0, 200.0), capacity_l=5000.0)],
        troughs=[TroughConfig(id="trough_a", pos=(200.0, 200.0), paddock="p_main")],
        fence_lines=[
            FenceLineConfig(
                id="fence_s", segment=[(0.0, 0.0), (2000.0, 0.0)], tag="perimeter"
            )
        ],
        barn=BarnConfig(pos=(1900.0, 1900.0)),
    )
    terrain = Terrain(config)
    sick = Cow(
        id="cow_SICK01",
        tag="SICK01",
        pos=(300.0, 300.0),
        health_score=0.5,
        lameness_score=0,
        ocular_discharge=0.85,
        disease_flags={"pinkeye"},
    )
    herd = Herd(cows=[sick], rng=random.Random(42))
    clock = Clock(sim_start_utc=datetime(2026, 4, 21, 13, 0, tzinfo=UTC))
    return World(
        clock=clock,
        terrain=terrain,
        herd=herd,
        predator_spawner=PredatorSpawner(rng=random.Random(99)),
        weather_driver=WeatherDriver(),
    )


@pytest.fixture(autouse=True)
def scenarios_snapshot():
    """Snapshot the SCENARIOS dict before each test; restore after.

    This prevents test_run_all.py from contaminating wildfire/rustling/
    cross_ranch tests when they share a single pytest session.
    """
    from skyherd.scenarios import SCENARIOS

    # Take a shallow copy of the dict and its reference
    original_keys = list(SCENARIOS.keys())
    original_values = dict(SCENARIOS)

    yield

    # Restore: remove any keys added during the test, restore any removed
    keys_to_remove = [k for k in SCENARIOS if k not in original_values]
    for k in keys_to_remove:
        del SCENARIOS[k]

    for k, v in original_values.items():
        SCENARIOS[k] = v

    # Restore original insertion order
    for k in list(SCENARIOS.keys()):
        if k not in original_keys:
            del SCENARIOS[k]
