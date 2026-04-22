"""Tests for render_trough_frame and render_thermal_frame."""

from __future__ import annotations

import hashlib
import random
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image

from skyherd.vision.renderer import render_thermal_frame, render_trough_frame
from skyherd.world.cattle import Cow, Herd
from skyherd.world.clock import Clock
from skyherd.world.predators import PredatorSpawner
from skyherd.world.weather import WeatherDriver
from skyherd.world.world import World


def test_render_trough_frame_returns_png(world_with_sick_cow: World, tmp_path: Path) -> None:
    """render_trough_frame produces a PNG at the specified path."""
    out = tmp_path / "trough.png"
    result = render_trough_frame(world_with_sick_cow, "trough_a", out_path=out)
    assert result == out
    assert out.exists()
    img = Image.open(str(out))
    assert img.format == "PNG"


def test_render_trough_frame_dimensions(world_with_sick_cow: World, tmp_path: Path) -> None:
    """Output frame is exactly 640×480."""
    out = tmp_path / "trough.png"
    render_trough_frame(world_with_sick_cow, "trough_a", out_path=out)
    img = Image.open(str(out))
    assert img.size == (640, 480)


def test_render_trough_frame_deterministic(world_with_sick_cow: World, tmp_path: Path) -> None:
    """Same world state produces identical frames (byte-for-byte)."""
    out_a = tmp_path / "a.png"
    out_b = tmp_path / "b.png"
    render_trough_frame(world_with_sick_cow, "trough_a", out_path=out_a)
    render_trough_frame(world_with_sick_cow, "trough_a", out_path=out_b)
    assert out_a.read_bytes() == out_b.read_bytes()


def test_render_trough_frame_zero_cows(terrain, tmp_path: Path) -> None:
    """render_trough_frame tolerates a world with zero cows — produces blank frame."""
    import random
    from datetime import UTC, datetime

    from skyherd.world.cattle import Herd
    from skyherd.world.clock import Clock
    from skyherd.world.predators import PredatorSpawner
    from skyherd.world.weather import WeatherDriver
    from skyherd.world.world import World

    clock = Clock(sim_start_utc=datetime(2026, 4, 21, 13, 0, tzinfo=UTC))
    herd = Herd(cows=[], rng=random.Random(0))
    world = World(
        clock=clock,
        terrain=terrain,
        herd=herd,
        predator_spawner=PredatorSpawner(rng=random.Random(0)),
        weather_driver=WeatherDriver(),
    )
    out = tmp_path / "empty.png"
    render_trough_frame(world, "trough_a", out_path=out)
    img = Image.open(str(out))
    assert img.size == (640, 480)


def test_render_trough_frame_default_out_path(world_healthy: World) -> None:
    """render_trough_frame creates a file even when out_path is not provided."""
    result = render_trough_frame(world_healthy, "trough_a")
    assert result.exists()
    assert result.suffix == ".png"
    result.unlink(missing_ok=True)


def test_render_thermal_frame_dimensions(world_with_sick_cow: World, tmp_path: Path) -> None:
    """Thermal frame is exactly 320×240."""
    out = tmp_path / "thermal.png"
    render_thermal_frame(world_with_sick_cow, center_pos=(500.0, 500.0), out_path=out)
    img = Image.open(str(out))
    assert img.size == (320, 240)


def test_render_thermal_frame_grayscale(world_with_sick_cow: World, tmp_path: Path) -> None:
    """Thermal frame is grayscale (mode L)."""
    out = tmp_path / "thermal.png"
    render_thermal_frame(world_with_sick_cow, center_pos=(500.0, 500.0), out_path=out)
    img = Image.open(str(out))
    assert img.mode == "L"


def test_render_thermal_frame_zero_cows(terrain, tmp_path: Path) -> None:
    """Thermal frame with no cows in FOV — blank image, no crash."""
    clock = Clock(sim_start_utc=datetime(2026, 4, 21, 13, 0, tzinfo=UTC))
    herd = Herd(cows=[], rng=random.Random(0))
    world = World(
        clock=clock,
        terrain=terrain,
        herd=herd,
        predator_spawner=PredatorSpawner(rng=random.Random(0)),
        weather_driver=WeatherDriver(),
    )
    out = tmp_path / "thermal_empty.png"
    render_thermal_frame(world, center_pos=(0.0, 0.0), out_path=out)
    img = Image.open(str(out))
    assert img.size == (320, 240)


# ---------------------------------------------------------------------------
# H-10 regression — vectorized numpy renderer produces identical output
# ---------------------------------------------------------------------------


def _make_large_herd_world(terrain, n_healthy: int = 497, sick_tags: list[str] | None = None) -> World:
    """Build a world with n_healthy healthy cows + sick cows from sick_tags."""
    if sick_tags is None:
        sick_tags = ["S001", "S002", "S003"]
    healthy_cows = [
        Cow(
            id=f"cow_H{i:04d}",
            tag=f"H{i:04d}",
            pos=(float(50 + (i % 40) * 48), float(50 + (i // 40) * 48)),
            health_score=1.0,
            lameness_score=0,
            ocular_discharge=0.0,
            bcs=5.5,
            disease_flags=set(),
            pregnancy_days_remaining=None,
        )
        for i in range(n_healthy)
    ]
    sick_cows = [
        Cow(
            id=f"cow_{tag}",
            tag=tag,
            pos=(300.0, 300.0),
            health_score=0.25,
            lameness_score=4,
            ocular_discharge=0.9,
            bcs=2.5,
            disease_flags={"respiratory"},
            pregnancy_days_remaining=None,
        )
        for tag in sick_tags
    ]
    clock = Clock(sim_start_utc=datetime(2026, 4, 21, 13, 0, tzinfo=UTC))
    herd = Herd(cows=healthy_cows + sick_cows, rng=random.Random(99))
    return World(
        clock=clock,
        terrain=terrain,
        herd=herd,
        predator_spawner=PredatorSpawner(rng=random.Random(0)),
        weather_driver=WeatherDriver(),
    )


def test_render_trough_vectorized_deterministic(terrain, tmp_path: Path) -> None:
    """Vectorized gradient background: two renders of same world are byte-identical (H-10)."""
    world = _make_large_herd_world(terrain)
    out_a = tmp_path / "vec_a.png"
    out_b = tmp_path / "vec_b.png"
    render_trough_frame(world, "trough_a", out_path=out_a)
    render_trough_frame(world, "trough_a", out_path=out_b)
    md5_a = hashlib.md5(out_a.read_bytes()).hexdigest()
    md5_b = hashlib.md5(out_b.read_bytes()).hexdigest()
    assert md5_a == md5_b, "Vectorized trough render must be byte-for-byte deterministic"


def test_render_thermal_vectorized_deterministic(terrain, tmp_path: Path) -> None:
    """Vectorized gaussian blob: two renders of same world are byte-identical (H-10)."""
    world = _make_large_herd_world(terrain)
    out_a = tmp_path / "therm_a.png"
    out_b = tmp_path / "therm_b.png"
    render_thermal_frame(world, center_pos=(1000.0, 1000.0), out_path=out_a)
    render_thermal_frame(world, center_pos=(1000.0, 1000.0), out_path=out_b)
    md5_a = hashlib.md5(out_a.read_bytes()).hexdigest()
    md5_b = hashlib.md5(out_b.read_bytes()).hexdigest()
    assert md5_a == md5_b, "Vectorized thermal render must be byte-for-byte deterministic"


def test_render_trough_pixel_gradient_correct(terrain, tmp_path: Path) -> None:
    """Vectorized background: top-left pixel is dark green, bottom-left is lighter (H-10)."""
    world = _make_large_herd_world(terrain, n_healthy=0, sick_tags=[])
    out = tmp_path / "grad.png"
    render_trough_frame(world, "trough_a", out_path=out)
    arr = np.array(Image.open(str(out)))
    top_green = int(arr[0, 0, 1])
    bot_green = int(arr[479, 0, 1])
    assert top_green < bot_green, (
        f"Top green channel ({top_green}) should be darker than bottom ({bot_green})"
    )
