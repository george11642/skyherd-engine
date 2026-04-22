"""Tests for the storm scenario."""

from __future__ import annotations


class TestStormScenario:
    def test_name_and_description(self) -> None:
        from skyherd.scenarios.storm import StormScenario

        s = StormScenario()
        assert s.name == "storm"
        assert "storm" in s.description.lower()

    def test_setup_clears_weather(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.storm import StormScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = StormScenario()
        s.setup(world)
        assert world.weather_driver.current.conditions == "clear"

    def test_storm_warning_injected_at_threshold(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.storm import _STORM_WARNING_AT_S, StormScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = StormScenario()
        s.setup(world)
        # Before threshold
        early = s.inject_events(world, _STORM_WARNING_AT_S - 1.0)
        assert early == []
        # At threshold
        events = s.inject_events(world, _STORM_WARNING_AT_S + 1.0)
        types = [e["type"] for e in events]
        assert "storm.warning" in types
        assert "weather.storm" in types

    def test_auto_approval_injected_60s_after_warning(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.storm import _STORM_WARNING_AT_S, StormScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = StormScenario()
        s.setup(world)
        # Fire warning first
        s.inject_events(world, _STORM_WARNING_AT_S + 1.0)
        # Then approval
        events = s.inject_events(world, _STORM_WARNING_AT_S + 61.0)
        types = [e["type"] for e in events]
        assert "rancher.approval" in types
        assert "acoustic.activated" in types

    def test_acoustic_tone_sub_20khz(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.storm import _STORM_WARNING_AT_S, StormScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = StormScenario()
        s.setup(world)
        s.inject_events(world, _STORM_WARNING_AT_S + 1.0)
        events = s.inject_events(world, _STORM_WARNING_AT_S + 61.0)
        acoustic = next(e for e in events if e["type"] == "acoustic.activated")
        assert acoustic["tone_hz"] < 20000

    def test_full_run_passes(self) -> None:
        from skyherd.scenarios import run

        result = run("storm", seed=42)
        assert result.outcome_passed, f"storm scenario failed: {result.outcome_error}"

    def test_full_run_has_storm_warning(self) -> None:
        from skyherd.scenarios import run

        result = run("storm", seed=42)
        warning = next((e for e in result.event_stream if e.get("type") == "storm.warning"), None)
        assert warning is not None

    def test_full_run_has_acoustic_activation(self) -> None:
        from skyherd.scenarios import run

        result = run("storm", seed=42)
        acoustic = next(
            (e for e in result.event_stream if e.get("type") == "acoustic.activated"), None
        )
        assert acoustic is not None
        assert acoustic.get("tone_hz", 99999) < 20000
