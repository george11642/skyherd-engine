"""Tests for the sick_cow scenario."""

from __future__ import annotations


class TestSickCowScenario:
    def test_name_and_description(self) -> None:
        from skyherd.scenarios.sick_cow import SickCowScenario

        s = SickCowScenario()
        assert s.name == "sick_cow"
        assert "pinkeye" in s.description.lower() or "a014" in s.description.lower()

    def test_setup_stamps_a014(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.sick_cow import SickCowScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = SickCowScenario()
        s.setup(world)
        a014 = next((c for c in world.herd.cows if c.tag == "A014"), None)
        assert a014 is not None
        assert a014.ocular_discharge >= 0.7
        assert "pinkeye" in a014.disease_flags

    def test_setup_does_not_affect_other_cows(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.sick_cow import SickCowScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = SickCowScenario()
        s.setup(world)
        # A001 should be unaffected
        a001 = next((c for c in world.herd.cows if c.tag == "A001"), None)
        assert a001 is not None
        assert a001.ocular_discharge == 0.0

    def test_health_check_injected_at_threshold(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.sick_cow import _HEALTH_CHECK_AT_S, SickCowScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = SickCowScenario()
        s.setup(world)
        events = s.inject_events(world, _HEALTH_CHECK_AT_S + 1.0)
        types = [e["type"] for e in events]
        assert "camera.motion" in types
        assert "health.check" in types

    def test_health_check_has_correct_cow_tag(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.sick_cow import _HEALTH_CHECK_AT_S, SickCowScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = SickCowScenario()
        s.setup(world)
        events = s.inject_events(world, _HEALTH_CHECK_AT_S + 1.0)
        health_ev = next((e for e in events if e["type"] == "health.check"), None)
        assert health_ev is not None
        assert health_ev["cow_tag"] == "A014"
        assert "pinkeye" in health_ev["disease_flags"]

    def test_full_run_passes(self) -> None:
        from skyherd.scenarios import run

        result = run("sick_cow", seed=42)
        assert result.outcome_passed, f"sick_cow scenario failed: {result.outcome_error}"

    def test_full_run_has_health_check_event(self) -> None:
        from skyherd.scenarios import run

        result = run("sick_cow", seed=42)
        hc = next((e for e in result.event_stream if e.get("type") == "health.check"), None)
        assert hc is not None
        assert hc.get("cow_tag") == "A014"
