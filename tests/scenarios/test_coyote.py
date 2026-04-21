"""Tests for the coyote scenario."""

from __future__ import annotations

from skyherd.scenarios import run
from skyherd.scenarios.coyote import CoyoteScenario, _BREACH_AT_S


class TestCoyoteScenario:
    def test_name_and_description(self) -> None:
        s = CoyoteScenario()
        assert s.name == "coyote"
        assert "coyote" in s.description.lower()

    def test_duration(self) -> None:
        s = CoyoteScenario()
        assert s.duration_s == 600.0

    def test_breach_at_constant(self) -> None:
        # ~7:42 pm offset — should be between 400s and 500s from start
        assert 400.0 < _BREACH_AT_S < 500.0

    def test_setup_sets_southerly_wind(self) -> None:
        from pathlib import Path

        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CoyoteScenario()
        s.setup(world)
        assert world.weather_driver.current.wind_dir_deg == 180.0

    def test_breach_not_injected_before_threshold(self) -> None:
        from pathlib import Path

        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CoyoteScenario()
        s.setup(world)
        early_events = s.inject_events(world, 0.0)
        assert early_events == []

    def test_breach_injected_at_threshold(self) -> None:
        from pathlib import Path

        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CoyoteScenario()
        s.setup(world)
        events = s.inject_events(world, _BREACH_AT_S + 1.0)
        types = [e["type"] for e in events]
        assert "fence.breach" in types

    def test_coyote_added_to_world(self) -> None:
        from pathlib import Path

        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CoyoteScenario()
        s.setup(world)
        s.inject_events(world, _BREACH_AT_S + 1.0)
        pred_ids = [p.id for p in world.predator_spawner.predators]
        assert "coyote_scenario_001" in pred_ids

    def test_full_run_passes(self) -> None:
        result = run("coyote", seed=42)
        assert result.outcome_passed, f"Coyote scenario failed: {result.outcome_error}"
        assert len(result.event_stream) > 0

    def test_full_run_has_fence_breach(self) -> None:
        result = run("coyote", seed=42)
        breach = next(
            (e for e in result.event_stream if e.get("type") == "fence.breach"), None
        )
        assert breach is not None

    def test_full_run_has_predator_fleeing(self) -> None:
        result = run("coyote", seed=42)
        fleeing = next(
            (e for e in result.event_stream if e.get("type") == "predator.fleeing"), None
        )
        assert fleeing is not None

    def test_full_run_writes_jsonl(self) -> None:
        result = run("coyote", seed=42)
        assert result.jsonl_path is not None
        assert result.jsonl_path.exists()
        lines = result.jsonl_path.read_text().splitlines()
        assert len(lines) > 0
