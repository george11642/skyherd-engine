"""Tests for the calving scenario."""

from __future__ import annotations


class TestCalvingScenario:
    def test_name_and_description(self) -> None:
        from skyherd.scenarios.calving import CalvingScenario

        s = CalvingScenario()
        assert s.name == "calving"
        assert "b007" in s.description.lower() or "calv" in s.description.lower()

    def test_setup_sets_b007_pregnancy(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.calving import CalvingScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CalvingScenario()
        s.setup(world)
        b007 = next((c for c in world.herd.cows if c.tag == "B007"), None)
        assert b007 is not None
        assert b007.pregnancy_days_remaining == 2

    def test_prelabor_injected_at_minute_2(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.calving import CalvingScenario, _PRELABOR_AT_S
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CalvingScenario()
        s.setup(world)
        # Before threshold — nothing injected
        early = s.inject_events(world, _PRELABOR_AT_S - 1.0)
        assert early == []
        # At threshold
        events = s.inject_events(world, _PRELABOR_AT_S + 1.0)
        types = [e["type"] for e in events]
        assert "collar.activity_spike" in types
        assert "calving.prelabor" in types

    def test_prelabor_event_has_correct_tag(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.calving import CalvingScenario, _PRELABOR_AT_S
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CalvingScenario()
        s.setup(world)
        events = s.inject_events(world, _PRELABOR_AT_S + 1.0)
        spike = next(e for e in events if e["type"] == "collar.activity_spike")
        assert spike["tag"] == "B007"
        assert spike.get("pregnancy_days_remaining") == 2

    def test_full_run_passes(self) -> None:
        from skyherd.scenarios import run

        result = run("calving", seed=42)
        assert result.outcome_passed, f"calving scenario failed: {result.outcome_error}"

    def test_full_run_has_prelabor_event(self) -> None:
        from skyherd.scenarios import run

        result = run("calving", seed=42)
        prelabor = next(
            (e for e in result.event_stream if e.get("type") == "calving.prelabor"), None
        )
        assert prelabor is not None
        assert prelabor.get("cow_tag") == "B007"

    def test_full_run_has_page_rancher(self) -> None:
        from skyherd.scenarios import run

        result = run("calving", seed=42)
        all_tools: list[dict] = []
        for calls in result.agent_tool_calls.values():
            all_tools.extend(calls)
        page_calls = [c for c in all_tools if c.get("tool") == "page_rancher"]
        assert len(page_calls) > 0
