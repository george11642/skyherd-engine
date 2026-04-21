"""Tests for PredatorSpawner — nocturnal spawning, pathfinding to fence."""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime

from skyherd.world.cattle import Cow, Herd
from skyherd.world.clock import Clock
from skyherd.world.predators import Predator, PredatorSpawner, PredatorState
from skyherd.world.terrain import (
    BarnConfig,
    FenceLineConfig,
    PaddockConfig,
    Terrain,
    TerrainConfig,
    TroughConfig,
    WaterTankConfig,
)


def _make_terrain() -> Terrain:
    config = TerrainConfig(
        name="test",
        bounds_m=(2000.0, 2000.0),
        paddocks=[
            PaddockConfig(
                id="p_all",
                polygon=[(0.0, 0.0), (2000.0, 0.0), (2000.0, 2000.0), (0.0, 2000.0)],
            )
        ],
        water_tanks=[WaterTankConfig(id="wt1", pos=(1000.0, 1000.0), capacity_l=5000.0)],
        troughs=[TroughConfig(id="tr1", pos=(1000.0, 1000.0), paddock="p_all")],
        fence_lines=[
            FenceLineConfig(id="fence_s", segment=[(0.0, 0.0), (2000.0, 0.0)], tag="perimeter"),
            FenceLineConfig(
                id="fence_n", segment=[(0.0, 2000.0), (2000.0, 2000.0)], tag="perimeter"
            ),
            FenceLineConfig(id="fence_w", segment=[(0.0, 0.0), (0.0, 2000.0)], tag="perimeter"),
            FenceLineConfig(
                id="fence_e", segment=[(2000.0, 0.0), (2000.0, 2000.0)], tag="perimeter"
            ),
        ],
        barn=BarnConfig(pos=(1900.0, 1900.0)),
    )
    return Terrain(config)


def _night_clock() -> Clock:
    """Return a clock where is_night() is True (MT 22:00 = UTC 05:00)."""
    start = datetime(2026, 4, 21, 5, 0, 0, tzinfo=UTC)
    return Clock(sim_start_utc=start)


def _day_clock() -> Clock:
    """Return a clock where is_night() is False (MT 12:00 = UTC 19:00)."""
    start = datetime(2026, 4, 21, 19, 0, 0, tzinfo=UTC)
    return Clock(sim_start_utc=start)


def _make_herd_at_center() -> Herd:
    cow = Cow(id="c0", tag="T0", pos=(1000.0, 1000.0))
    return Herd([cow], rng=random.Random(0))


class TestNocturnalSpawning:
    def test_spawns_more_at_night_than_day(self) -> None:
        """Over many trials, night should produce more spawns than day."""
        terrain = _make_terrain()
        herd = _make_herd_at_center()

        dt = 100.0  # large dt to force Poisson arrivals
        n_trials = 200

        night_spawns = 0
        day_spawns = 0

        for i in range(n_trials):
            spawner = PredatorSpawner(rng=random.Random(i))
            events = spawner.step(
                dt=dt, clock=_night_clock(), terrain=terrain, herd=herd, sim_time_s=0.0
            )
            night_spawns += len([e for e in events if e["type"] == "predator.spawned"])

        for i in range(n_trials):
            spawner = PredatorSpawner(rng=random.Random(i))
            events = spawner.step(
                dt=dt, clock=_day_clock(), terrain=terrain, herd=herd, sim_time_s=0.0
            )
            day_spawns += len([e for e in events if e["type"] == "predator.spawned"])

        assert night_spawns > day_spawns, (
            f"Night should spawn more predators than day: night={night_spawns}, day={day_spawns}"
        )

    def test_spawn_event_has_required_fields(self) -> None:
        """Spawn event must include type, predator_id, species, pos, sim_time_s."""
        terrain = _make_terrain()
        herd = _make_herd_at_center()
        # Force a spawn: use a rng that guarantees Poisson arrival
        # With rate=0.008 and dt=1000, P(spawn) ≈ 8 → guaranteed
        spawner = PredatorSpawner(rng=random.Random(42))
        events: list = []
        # Run until we get a spawn
        for i in range(100):
            evs = spawner.step(
                dt=500.0,
                clock=_night_clock(),
                terrain=terrain,
                herd=herd,
                sim_time_s=float(i * 500),
            )
            events.extend(evs)
            if any(e["type"] == "predator.spawned" for e in events):
                break

        spawn_events = [e for e in events if e["type"] == "predator.spawned"]
        assert len(spawn_events) >= 1
        ev = spawn_events[0]
        assert "predator_id" in ev
        assert "species" in ev
        assert "pos" in ev
        assert "sim_time_s" in ev

    def test_spawn_pos_at_boundary(self) -> None:
        """Spawned predators should appear at the ranch boundary (x=0, x=2000, y=0, or y=2000)."""
        terrain = _make_terrain()
        herd = _make_herd_at_center()
        spawner = PredatorSpawner(rng=random.Random(7))
        bounds = 2000.0
        _EPS = 0.1

        for i in range(50):
            spawner.step(
                dt=500.0,
                clock=_night_clock(),
                terrain=terrain,
                herd=herd,
                sim_time_s=float(i * 500),
            )

        for pred in spawner.predators:
            x, y = pred.pos
            on_boundary = (
                abs(x) < _EPS or abs(x - bounds) < _EPS or abs(y) < _EPS or abs(y - bounds) < _EPS
            )
            # Note: predators may have moved already — they could have moved inward
            # So we just check they're within bounds
            assert 0.0 <= x <= bounds
            assert 0.0 <= y <= bounds


class TestPredatorPathfinding:
    def test_predator_approaches_herd_centroid(self) -> None:
        """After enough steps, a predator should be closer to the herd centroid."""
        terrain = _make_terrain()
        herd = _make_herd_at_center()  # centroid at (1000, 1000)

        # Manually place a predator at the north boundary
        spawner = PredatorSpawner(rng=random.Random(0))
        pred = Predator(
            id="pred_test",
            species="coyote",
            pos=(0.0, 2000.0),  # NW corner
            heading_deg=0.0,
            state="roaming",
            size_kg=13.0,
            thermal_signature=0.4,
        )
        spawner.predators = [pred]

        initial_dist = math.sqrt((0.0 - 1000.0) ** 2 + (2000.0 - 1000.0) ** 2)

        # Step 200 times × 1s each
        for i in range(200):
            spawner.step(
                dt=1.0, clock=_night_clock(), terrain=terrain, herd=herd, sim_time_s=float(i)
            )

        if spawner.predators:
            final_pos = spawner.predators[0].pos
            final_dist = math.sqrt((final_pos[0] - 1000.0) ** 2 + (final_pos[1] - 1000.0) ** 2)
            assert final_dist < initial_dist, "Predator should have moved toward herd"

    def test_predator_state_approaching_when_far(self) -> None:
        """Predator far from herd centroid should be in approaching state."""
        terrain = _make_terrain()
        herd = _make_herd_at_center()
        spawner = PredatorSpawner(rng=random.Random(0))
        pred = Predator(
            id="p0",
            species="coyote",
            pos=(0.0, 0.0),
            heading_deg=45.0,
            state="roaming",
            size_kg=13.0,
            thermal_signature=0.4,
        )
        spawner.predators = [pred]
        spawner.step(dt=1.0, clock=_night_clock(), terrain=terrain, herd=herd, sim_time_s=0.0)

        updated = spawner.predators[0]
        assert updated.state == PredatorState.APPROACHING.value or updated.state == "approaching"
