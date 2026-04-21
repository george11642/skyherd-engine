"""Tests for determinism — two worlds with same seed produce identical event streams."""

from __future__ import annotations

from pathlib import Path

from skyherd.world.world import make_world

_CONFIG_PATH = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"


def _run_world(seed: int, n_steps: int, dt: float) -> list[dict]:
    """Create a world with *seed* and run *n_steps*; return the full event log."""
    world = make_world(seed=seed, config_path=_CONFIG_PATH)
    for _ in range(n_steps):
        world.step(dt)
    return world.events


class TestDeterminism:
    def test_same_seed_same_events(self) -> None:
        """Two worlds with the same seed must produce identical event streams."""
        events_a = _run_world(seed=42, n_steps=500, dt=10.0)
        events_b = _run_world(seed=42, n_steps=500, dt=10.0)

        assert len(events_a) == len(events_b), (
            f"Event count mismatch: {len(events_a)} vs {len(events_b)}"
        )
        for i, (ea, eb) in enumerate(zip(events_a, events_b)):
            assert ea == eb, f"Event {i} differs:\n  A: {ea}\n  B: {eb}"

    def test_different_seeds_different_events(self) -> None:
        """Two worlds with different seeds should (almost certainly) diverge."""
        events_42 = _run_world(seed=42, n_steps=500, dt=10.0)
        events_99 = _run_world(seed=99, n_steps=500, dt=10.0)

        # Not guaranteed they differ in count, but event content should differ
        # (at minimum, predator spawn positions will differ)
        combined_42 = str(events_42)
        combined_99 = str(events_99)
        assert combined_42 != combined_99, "Different seeds should produce different simulations"

    def test_determinism_1000_steps(self) -> None:
        """Larger run — 1000 steps × 10s — must still be deterministic."""
        events_a = _run_world(seed=42, n_steps=1000, dt=10.0)
        events_b = _run_world(seed=42, n_steps=1000, dt=10.0)

        assert events_a == events_b, "1000-step run must be fully deterministic"

    def test_snapshot_determinism(self) -> None:
        """Snapshots at the same step count must be identical."""
        from skyherd.world.world import make_world

        w1 = make_world(seed=7, config_path=_CONFIG_PATH)
        w2 = make_world(seed=7, config_path=_CONFIG_PATH)

        for _ in range(200):
            w1.step(5.0)
            w2.step(5.0)

        snap1 = w1.snapshot()
        snap2 = w2.snapshot()

        assert snap1.sim_time_s == snap2.sim_time_s
        assert snap1.is_night == snap2.is_night
        assert snap1.event_count == snap2.event_count
        assert snap1.cows == snap2.cows
        assert snap1.predators == snap2.predators

    def test_world_loads_from_config(self) -> None:
        """make_world should successfully load ranch_a.yaml and produce a World."""
        world = make_world(seed=0, config_path=_CONFIG_PATH)
        assert len(world.herd.cows) == 50
        assert world.clock.sim_time_s == 0.0

    def test_step_returns_events_list(self) -> None:
        world = make_world(seed=1, config_path=_CONFIG_PATH)
        events = world.step(1.0)
        assert isinstance(events, list)
