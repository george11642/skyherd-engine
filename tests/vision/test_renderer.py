"""Tests for render_trough_frame and render_thermal_frame."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from skyherd.vision.renderer import render_thermal_frame, render_trough_frame
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
    out = tmp_path / "thermal_empty.png"
    render_thermal_frame(world, center_pos=(0.0, 0.0), out_path=out)
    img = Image.open(str(out))
    assert img.size == (320, 240)
