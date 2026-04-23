"""make_world(seed=42) must work with no config_path argument (BLD-01)."""
from __future__ import annotations

from pathlib import Path

from skyherd.world.world import make_world


def test_make_world_no_config_path() -> None:
    """The canonical judge quickstart invocation — no config_path arg."""
    world = make_world(seed=42)
    assert world is not None
    assert len(world.herd.cows) == 50  # ranch_a.yaml has 50 cows
    assert world.clock.sim_time_s == 0.0


def test_make_world_deterministic_without_config() -> None:
    """Same seed + default config → identical cow positions."""
    w1 = make_world(seed=7)
    w2 = make_world(seed=7)
    assert [c.pos for c in w1.herd.cows] == [c.pos for c in w2.herd.cows]


def test_make_world_explicit_config_still_works() -> None:
    """Backward-compat: existing callers passing config_path= keep working."""
    config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
    world = make_world(seed=42, config_path=config)
    assert len(world.herd.cows) == 50
