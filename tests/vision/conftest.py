"""Shared fixtures for vision tests."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from skyherd.vision.renderer import render_trough_frame
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


def _make_terrain() -> Terrain:
    """Minimal 2km×2km ranch terrain with a single trough."""
    config = TerrainConfig(
        name="vision_test",
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
            FenceLineConfig(id="fence_s", segment=[(0.0, 0.0), (2000.0, 0.0)], tag="perimeter")
        ],
        barn=BarnConfig(pos=(1900.0, 1900.0)),
    )
    return Terrain(config)


def _make_cow(
    tag: str = "T001",
    health_score: float = 1.0,
    lameness_score: int = 0,
    ocular_discharge: float = 0.0,
    bcs: float = 5.5,
    disease_flags: set[str] | None = None,
    pregnancy_days_remaining: int | None = None,
    pos: tuple[float, float] = (300.0, 300.0),
) -> Cow:
    return Cow(
        id=f"cow_{tag}",
        tag=tag,
        pos=pos,
        health_score=health_score,
        lameness_score=lameness_score,
        ocular_discharge=ocular_discharge,
        bcs=bcs,
        disease_flags=disease_flags or set(),
        pregnancy_days_remaining=pregnancy_days_remaining,
    )


@pytest.fixture()
def terrain() -> Terrain:
    return _make_terrain()


@pytest.fixture()
def healthy_cow() -> Cow:
    return _make_cow(tag="H001")


@pytest.fixture()
def world_with_sick_cow(terrain: Terrain) -> World:
    """A world containing one sick cow (lameness 4, high ocular discharge)."""
    sick = _make_cow(
        tag="SICK01",
        health_score=0.4,
        lameness_score=4,
        ocular_discharge=0.75,
        disease_flags={"respiratory"},
    )
    rng = random.Random(42)
    herd = Herd(cows=[sick], rng=rng)
    from datetime import UTC, datetime

    clock = Clock(sim_start_utc=datetime(2026, 4, 21, 13, 0, tzinfo=UTC))
    pred_spawner = PredatorSpawner(rng=random.Random(99))
    weather_driver = WeatherDriver()
    return World(
        clock=clock,
        terrain=terrain,
        herd=herd,
        predator_spawner=pred_spawner,
        weather_driver=weather_driver,
    )


@pytest.fixture()
def world_healthy(terrain: Terrain) -> World:
    """A world containing only healthy cows."""
    cows = [_make_cow(tag=f"OK{i:02d}", pos=(float(100 + i * 50), 300.0)) for i in range(3)]
    rng = random.Random(7)
    herd = Herd(cows=cows, rng=rng)
    from datetime import UTC, datetime

    clock = Clock(sim_start_utc=datetime(2026, 4, 21, 13, 0, tzinfo=UTC))
    pred_spawner = PredatorSpawner(rng=random.Random(11))
    weather_driver = WeatherDriver()
    return World(
        clock=clock,
        terrain=terrain,
        herd=herd,
        predator_spawner=pred_spawner,
        weather_driver=weather_driver,
    )


@pytest.fixture()
def sick_pinkeye_world(terrain: Terrain) -> World:
    """A world containing one pinkeye-positive cow — ocular_discharge=0.85 will render a red eye streak."""
    sick = _make_cow(
        tag="SICK01",
        health_score=0.5,
        lameness_score=0,
        ocular_discharge=0.85,
        disease_flags={"pinkeye"},
        pos=(300.0, 300.0),
    )
    rng = random.Random(42)
    herd = Herd(cows=[sick], rng=rng)
    from datetime import UTC, datetime

    clock = Clock(sim_start_utc=datetime(2026, 4, 21, 13, 0, tzinfo=UTC))
    pred_spawner = PredatorSpawner(rng=random.Random(99))
    weather_driver = WeatherDriver()
    return World(
        clock=clock,
        terrain=terrain,
        herd=herd,
        predator_spawner=pred_spawner,
        weather_driver=weather_driver,
    )


@pytest.fixture()
def rendered_positive_frame(
    sick_pinkeye_world: World, tmp_path: Path
) -> tuple[Path, World]:
    """Render trough_a for the pinkeye-positive world. Returns (png_path, world)."""
    raw_path = tmp_path / "raw_positive.png"
    render_trough_frame(sick_pinkeye_world, "trough_a", out_path=raw_path)
    return (raw_path, sick_pinkeye_world)


@pytest.fixture()
def rendered_negative_frame(
    world_healthy: World, tmp_path: Path
) -> tuple[Path, World]:
    """Render trough_a for the all-healthy world. Returns (png_path, world)."""
    raw_path = tmp_path / "raw_negative.png"
    render_trough_frame(world_healthy, "trough_a", out_path=raw_path)
    return (raw_path, world_healthy)
