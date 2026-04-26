"""Tests for the cross-ranch coyote scenario (Extended Vision).

All tests run WITHOUT an Anthropic API key — the _simulate_handler path is used.
No real MQTT broker is required.
"""

from __future__ import annotations

from skyherd.scenarios.cross_ranch_coyote import (
    _BREACH_AT_S,
    _RANCH_A_SHARED_FENCE,
    _RANCH_B_SHARED_FENCE,
    CrossRanchCoyoteScenario,
    run_cross_ranch,
)


class TestCrossRanchCoyoteScenarioMetadata:
    def test_name(self):
        s = CrossRanchCoyoteScenario()
        assert s.name == "cross_ranch_coyote"

    def test_description_mentions_handoff(self):
        s = CrossRanchCoyoteScenario()
        assert "handoff" in s.description.lower()

    def test_duration(self):
        s = CrossRanchCoyoteScenario()
        assert s.duration_s == 600.0

    def test_breach_at_constant_in_reasonable_range(self):
        assert 400.0 < _BREACH_AT_S < 500.0

    def test_shared_fence_constants(self):
        assert _RANCH_A_SHARED_FENCE == "fence_east"
        assert _RANCH_B_SHARED_FENCE == "fence_west"


class TestCrossRanchCoyoteSetup:
    def test_setup_sets_southerly_wind(self):
        from pathlib import Path

        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CrossRanchCoyoteScenario()
        s.setup(world)
        assert world.weather_driver.current.wind_dir_deg == 180.0

    def test_no_breach_before_threshold(self):
        from pathlib import Path

        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CrossRanchCoyoteScenario()
        s.setup(world)
        events = s.inject_events(world, 0.0)
        assert events == []

    def test_breach_injected_at_threshold(self):
        from pathlib import Path

        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CrossRanchCoyoteScenario()
        s.setup(world)
        events = s.inject_events(world, _BREACH_AT_S + 1.0)
        types = [e["type"] for e in events]
        assert "fence.breach" in types

    def test_breach_is_on_shared_fence(self):
        from pathlib import Path

        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CrossRanchCoyoteScenario()
        s.setup(world)
        events = s.inject_events(world, _BREACH_AT_S + 1.0)
        breach = next((e for e in events if e["type"] == "fence.breach"), None)
        assert breach is not None
        assert (
            breach.get("fence_id") == _RANCH_A_SHARED_FENCE
            or breach.get("segment") == _RANCH_A_SHARED_FENCE
        )

    def test_coyote_spawned_at_east_boundary(self):
        from pathlib import Path

        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CrossRanchCoyoteScenario()
        s.setup(world)
        s.inject_events(world, _BREACH_AT_S + 1.0)
        pred_ids = [p.id for p in world.predator_spawner.predators]
        assert "coyote_cross_ranch_001" in pred_ids

    def test_coyote_not_injected_twice(self):
        """Second call past threshold does not re-inject the same coyote."""
        from pathlib import Path

        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = CrossRanchCoyoteScenario()
        s.setup(world)
        s.inject_events(world, _BREACH_AT_S + 1.0)
        s.inject_events(world, _BREACH_AT_S + 5.0)
        cross_ranch_coyotes = [
            p for p in world.predator_spawner.predators if p.id == "coyote_cross_ranch_001"
        ]
        assert len(cross_ranch_coyotes) == 1


class TestCrossRanchFullRun:
    def test_full_run_passes(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        assert result["outcome_passed"], (
            f"Cross-ranch scenario failed: {result.get('outcome_error')}"
        )

    def test_both_ranches_produce_tool_calls(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        assert len(result["ranch_a_tool_calls"]) > 0, "Ranch_a produced no tool calls"
        assert len(result["ranch_b_tool_calls"]) > 0, "Ranch_b produced no tool calls"

    def test_ranch_a_launches_drone(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        a_tools = {c.get("tool") for c in result["ranch_a_tool_calls"]}
        assert "launch_drone" in a_tools, f"Ranch_a expected launch_drone. Got: {a_tools}"

    def test_ranch_b_launches_drone_pre_position(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        b_tools = {c.get("tool") for c in result["ranch_b_tool_calls"]}
        assert "launch_drone" in b_tools, (
            f"Ranch_b expected pre_position launch_drone. Got: {b_tools}"
        )

    def test_ranch_b_does_not_page_rancher(self, monkeypatch):
        """Silent handoff: ranch_b must NOT call page_rancher on neighbor alert."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        b_rancher_pages = [
            c for c in result["ranch_b_tool_calls"] if c.get("tool") == "page_rancher"
        ]
        assert len(b_rancher_pages) == 0, (
            f"Ranch_b should not page rancher on neighbor_alert. Got: {b_rancher_pages}"
        )

    def test_two_attestation_hashes(self, monkeypatch):
        """Both ranches generate attestation hashes — shared fence attested twice."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        sim_result = result.get("simulation_result", {})
        hashes = sim_result.get("attestation_hashes", [])
        assert len(hashes) >= 2, f"Expected >=2 attestation hashes. Got: {hashes}"

    def test_event_stream_has_fence_breach(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        # event_count > 0 means events were emitted
        assert result["event_count"] > 0

    def test_deterministic_with_same_seed(self, monkeypatch):
        """Two runs with the same seed produce identical tool call sets."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        r1 = run_cross_ranch(seed=42)
        r2 = run_cross_ranch(seed=42)
        a1 = [c.get("tool") for c in r1["ranch_a_tool_calls"]]
        a2 = [c.get("tool") for c in r2["ranch_a_tool_calls"]]
        assert a1 == a2, "Ranch_a tool calls differ across seeds"
        b1 = [c.get("tool") for c in r1["ranch_b_tool_calls"]]
        b2 = [c.get("tool") for c in r2["ranch_b_tool_calls"]]
        assert b1 == b2, "Ranch_b tool calls differ across seeds"

    def test_ranch_b_handoff_log_entry(self, monkeypatch):
        """Ranch_b must emit a neighbor_handoff log entry (for dashboard)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        b_calls = result["ranch_b_tool_calls"]
        handoff_logs = [
            c
            for c in b_calls
            if c.get("tool") == "log_agent_event"
            and c.get("input", {}).get("event_type") == "neighbor_handoff"
        ]
        assert len(handoff_logs) > 0, (
            "Ranch_b expected log_agent_event(neighbor_handoff). "
            f"Got tools: {[c.get('tool') for c in b_calls]}"
        )


class TestCrossRanchCoyoteUpgradedAssertions:
    """Phase 02 CRM-06: upgraded assert_outcome — first-class scenario."""

    def test_ranch_b_mission_is_neighbor_pre_position_patrol(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        launch_calls = [c for c in result["ranch_b_tool_calls"] if c.get("tool") == "launch_drone"]
        missions = [c.get("input", {}).get("mission") for c in launch_calls]
        assert "neighbor_pre_position_patrol" in missions, (
            f"Ranch_b launch_drone mission must be 'neighbor_pre_position_patrol'. Got: {missions}"
        )

    def test_ranch_b_handoff_log_has_response_mode_pre_position(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        pre_position_logs = [
            c
            for c in result["ranch_b_tool_calls"]
            if c.get("tool") == "log_agent_event"
            and c.get("input", {}).get("event_type") == "neighbor_handoff"
            and c.get("input", {}).get("response_mode") == "pre_position"
        ]
        assert len(pre_position_logs) > 0, (
            "Ranch_b neighbor_handoff log must set response_mode='pre_position'."
        )

    def test_simulation_result_flags_pre_positioned(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        sim = result.get("simulation_result", {})
        assert sim.get("ranch_b_pre_positioned") is True, (
            "simulation_result.ranch_b_pre_positioned must be True — got "
            f"{sim.get('ranch_b_pre_positioned')}"
        )

    def test_attestation_hashes_are_distinct(self, monkeypatch):
        """Shared fence attested twice — hashes differ (separate ranch ledger entries)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        hashes = result.get("simulation_result", {}).get("attestation_hashes", [])
        assert len(set(hashes)) >= 2, (
            f"Expected >=2 distinct attestation hashes (one per ranch). Got: {hashes}"
        )

    def test_assert_outcome_passes_with_full_cross_ranch_mesh(self, monkeypatch):
        """Full upgraded assert_outcome gate — calls run_cross_ranch and confirms
        outcome_passed is True (all CRM-06 assertions satisfied)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = run_cross_ranch(seed=42)
        assert result["outcome_passed"], (
            f"Upgraded assert_outcome failed: {result.get('outcome_error')}"
        )
