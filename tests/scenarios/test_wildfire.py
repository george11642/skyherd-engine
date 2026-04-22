"""Tests for the Wildfire Thermal Early-Warning scenario."""

from __future__ import annotations

from pathlib import Path

import pytest

from skyherd.scenarios import run
from skyherd.scenarios.wildfire import (
    _CONFIDENCE,
    _HOTSPOT_AT_S,
    _HOTSPOT_LAT,
    _HOTSPOT_LON,
    _PEAK_TEMP_C,
    WildfireScenario,
)

_WORLDS = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"


def _make_world():
    from skyherd.world.world import make_world

    return make_world(seed=42, config_path=_WORLDS)


class TestWildfireScenarioUnit:
    def test_name(self) -> None:
        s = WildfireScenario()
        assert s.name == "wildfire"

    def test_description_contains_hotspot(self) -> None:
        s = WildfireScenario()
        assert "hotspot" in s.description.lower() or "thermal" in s.description.lower()

    def test_duration(self) -> None:
        s = WildfireScenario()
        assert s.duration_s == 600.0

    def test_hotspot_at_constant_is_dawn_window(self) -> None:
        # Dawn sweep fires within the 600s scenario window
        assert 60.0 < _HOTSPOT_AT_S < 600.0

    def test_peak_temp_in_smouldering_range(self) -> None:
        # Smouldering brush: 320–450°C per wildfire-signatures.md
        assert 300.0 <= _PEAK_TEMP_C <= 500.0

    def test_confidence_above_action_threshold(self) -> None:
        # 0.90+ triggers both rancher page and fire dept draft
        assert _CONFIDENCE >= 0.90

    def test_setup_forces_calm_dawn_weather(self) -> None:
        world = _make_world()
        s = WildfireScenario()
        s.setup(world)
        wx = world.weather_driver.current
        assert wx.conditions == "clear"
        assert wx.wind_kt <= 5.0  # calm dawn

    def test_no_events_before_threshold(self) -> None:
        world = _make_world()
        s = WildfireScenario()
        s.setup(world)
        events = s.inject_events(world, 0.0)
        assert events == []

    def test_no_events_just_before_threshold(self) -> None:
        world = _make_world()
        s = WildfireScenario()
        s.setup(world)
        events = s.inject_events(world, _HOTSPOT_AT_S - 1.0)
        assert events == []

    def test_hotspot_event_injected_at_threshold(self) -> None:
        world = _make_world()
        s = WildfireScenario()
        s.setup(world)
        events = s.inject_events(world, _HOTSPOT_AT_S + 1.0)
        types = [e["type"] for e in events]
        assert "thermal.hotspot" in types

    def test_hotspot_event_has_correct_fields(self) -> None:
        world = _make_world()
        s = WildfireScenario()
        s.setup(world)
        events = s.inject_events(world, _HOTSPOT_AT_S + 1.0)
        hotspot = next((e for e in events if e["type"] == "thermal.hotspot"), None)
        assert hotspot is not None
        assert hotspot["lat"] == pytest.approx(_HOTSPOT_LAT, abs=0.01)
        assert hotspot["lon"] == pytest.approx(_HOTSPOT_LON, abs=0.01)
        assert hotspot["peak_temp_c"] >= 300.0
        assert hotspot["confidence"] >= 0.70
        assert "plume_drift_deg" in hotspot
        assert hotspot["is_scheduled_burn"] is False

    def test_fence_breach_also_injected(self) -> None:
        # FenceLineDispatcher wakes via fence.breach (defend-layer)
        world = _make_world()
        s = WildfireScenario()
        s.setup(world)
        events = s.inject_events(world, _HOTSPOT_AT_S + 1.0)
        types = [e["type"] for e in events]
        assert "fence.breach" in types

    def test_fence_breach_has_thermal_hotspot_flag(self) -> None:
        world = _make_world()
        s = WildfireScenario()
        s.setup(world)
        events = s.inject_events(world, _HOTSPOT_AT_S + 1.0)
        breach = next((e for e in events if e["type"] == "fence.breach"), None)
        assert breach is not None
        assert breach.get("thermal_hotspot") is True
        assert breach.get("species_hint") == "wildfire"

    def test_hotspot_only_injected_once(self) -> None:
        world = _make_world()
        s = WildfireScenario()
        s.setup(world)
        s.inject_events(world, _HOTSPOT_AT_S + 1.0)
        events_second = s.inject_events(world, _HOTSPOT_AT_S + 10.0)
        hotspot_count = sum(1 for e in events_second if e["type"] == "thermal.hotspot")
        assert hotspot_count == 0


class TestWildfireScenarioIntegration:
    def test_full_run_passes(self) -> None:
        result = run("wildfire", seed=42)
        assert result.outcome_passed, f"Wildfire scenario failed: {result.outcome_error}"

    def test_full_run_has_thermal_hotspot_event(self) -> None:
        result = run("wildfire", seed=42)
        hotspot = next((e for e in result.event_stream if e.get("type") == "thermal.hotspot"), None)
        assert hotspot is not None, "Expected thermal.hotspot event in stream"

    def test_full_run_has_launch_drone(self) -> None:
        result = run("wildfire", seed=42)
        all_tool_calls = [call for calls in result.agent_tool_calls.values() for call in calls]
        tool_names = {c.get("tool") for c in all_tool_calls}
        assert "launch_drone" in tool_names, (
            f"Expected launch_drone in tool calls. Got: {tool_names}"
        )

    def test_full_run_has_page_rancher_high(self) -> None:
        result = run("wildfire", seed=42)
        all_tool_calls = [call for calls in result.agent_tool_calls.values() for call in calls]
        rancher_calls = [c for c in all_tool_calls if c.get("tool") == "page_rancher"]
        assert rancher_calls, "Expected page_rancher call in wildfire scenario"
        urgencies = [c.get("input", {}).get("urgency", "") for c in rancher_calls]
        assert any(u in ("high", "emergency", "call") for u in urgencies), (
            f"Expected urgency high/emergency/call, got: {urgencies}"
        )

    def test_full_run_no_regression_on_event_count(self) -> None:
        result = run("wildfire", seed=42)
        # Wildfire scenario should produce at least 3 events
        assert len(result.event_stream) >= 3

    def test_full_run_writes_jsonl(self) -> None:
        result = run("wildfire", seed=42)
        assert result.jsonl_path is not None
        assert result.jsonl_path.exists()
        lines = result.jsonl_path.read_text().splitlines()
        assert len(lines) > 0
