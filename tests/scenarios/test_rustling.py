"""Tests for the Rustling / Theft Detection scenario."""

from __future__ import annotations

from pathlib import Path

from skyherd.scenarios import run
from skyherd.scenarios.rustling import (
    _DETECTION_AT_S,
    _HUMAN_TEMP_K,
    _VEHICLE_ENGINE_TEMP_C,
    RustlingScenario,
)

_WORLDS = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"


def _make_world():
    from skyherd.world.world import make_world

    return make_world(seed=42, config_path=_WORLDS)


class TestRustlingScenarioUnit:
    def test_name(self) -> None:
        s = RustlingScenario()
        assert s.name == "rustling"

    def test_description_mentions_silent(self) -> None:
        s = RustlingScenario()
        assert "silent" in s.description.lower()

    def test_duration(self) -> None:
        s = RustlingScenario()
        assert s.duration_s == 600.0

    def test_detection_time_is_nighttime(self) -> None:
        # 02:15 ranch time → anomalous nighttime window
        assert 100.0 < _DETECTION_AT_S < 300.0

    def test_human_temp_in_body_range(self) -> None:
        # Human body surface ~310K (37°C) per rustling-indicators.md
        assert 305.0 <= _HUMAN_TEMP_K <= 315.0

    def test_vehicle_engine_temp_in_warm_range(self) -> None:
        # Recently arrived truck engine: 340–380°C per rustling-indicators.md
        assert 300.0 <= _VEHICLE_ENGINE_TEMP_C <= 400.0

    def test_setup_forces_calm_night_weather(self) -> None:
        world = _make_world()
        s = RustlingScenario()
        s.setup(world)
        wx = world.weather_driver.current
        assert wx.conditions == "clear"
        assert wx.wind_kt <= 5.0

    def test_no_events_before_threshold(self) -> None:
        world = _make_world()
        s = RustlingScenario()
        s.setup(world)
        events = s.inject_events(world, 0.0)
        assert events == []

    def test_anomaly_event_injected_at_threshold(self) -> None:
        world = _make_world()
        s = RustlingScenario()
        s.setup(world)
        events = s.inject_events(world, _DETECTION_AT_S + 1.0)
        types = [e["type"] for e in events]
        assert "thermal.anomaly" in types

    def test_anomaly_event_has_human_and_vehicle_shapes(self) -> None:
        world = _make_world()
        s = RustlingScenario()
        s.setup(world)
        events = s.inject_events(world, _DETECTION_AT_S + 1.0)
        anomaly = next((e for e in events if e["type"] == "thermal.anomaly"), None)
        assert anomaly is not None
        shapes = anomaly.get("shapes_detected", [])
        assert "human_shape" in shapes, f"human_shape missing from shapes: {shapes}"
        assert "vehicle_shape" in shapes, f"vehicle_shape missing from shapes: {shapes}"

    def test_anomaly_event_location_is_gate(self) -> None:
        world = _make_world()
        s = RustlingScenario()
        s.setup(world)
        events = s.inject_events(world, _DETECTION_AT_S + 1.0)
        anomaly = next((e for e in events if e["type"] == "thermal.anomaly"), None)
        assert anomaly is not None
        assert anomaly.get("location") == "nw_gate"
        assert anomaly.get("is_scheduled") is False

    def test_fence_breach_injected_with_silent_mode(self) -> None:
        world = _make_world()
        s = RustlingScenario()
        s.setup(world)
        events = s.inject_events(world, _DETECTION_AT_S + 1.0)
        breach = next((e for e in events if e["type"] == "fence.breach"), None)
        assert breach is not None
        assert breach.get("rustling_suspected") is True
        assert breach.get("silent_mode") is True
        assert breach.get("species_hint") == "human"

    def test_silent_alert_injected(self) -> None:
        world = _make_world()
        s = RustlingScenario()
        s.setup(world)
        events = s.inject_events(world, _DETECTION_AT_S + 1.0)
        alert = next((e for e in events if e["type"] == "alert.silent"), None)
        assert alert is not None
        assert alert.get("event_category") == "rustling_suspected"

    def test_anomaly_only_injected_once(self) -> None:
        world = _make_world()
        s = RustlingScenario()
        s.setup(world)
        s.inject_events(world, _DETECTION_AT_S + 1.0)
        events_second = s.inject_events(world, _DETECTION_AT_S + 20.0)
        anomaly_count = sum(1 for e in events_second if e["type"] == "thermal.anomaly")
        assert anomaly_count == 0


class TestRustlingScenarioIntegration:
    def test_full_run_passes(self) -> None:
        result = run("rustling", seed=42)
        assert result.outcome_passed, f"Rustling scenario failed: {result.outcome_error}"

    def test_full_run_has_thermal_anomaly_event(self) -> None:
        result = run("rustling", seed=42)
        anomaly = next((e for e in result.event_stream if e.get("type") == "thermal.anomaly"), None)
        assert anomaly is not None, "Expected thermal.anomaly event in stream"

    def test_full_run_has_silent_alert_event(self) -> None:
        result = run("rustling", seed=42)
        alert = next((e for e in result.event_stream if e.get("type") == "alert.silent"), None)
        assert alert is not None, "Expected alert.silent event in stream"
        assert alert.get("event_category") == "rustling_suspected"

    def test_full_run_has_launch_drone(self) -> None:
        result = run("rustling", seed=42)
        all_tool_calls = [call for calls in result.agent_tool_calls.values() for call in calls]
        tool_names = {c.get("tool") for c in all_tool_calls}
        assert "launch_drone" in tool_names, (
            f"Expected launch_drone (silent observation). Got: {tool_names}"
        )

    def test_full_run_no_play_deterrent(self) -> None:
        result = run("rustling", seed=42)
        all_tool_calls = [call for calls in result.agent_tool_calls.values() for call in calls]
        tool_names = {c.get("tool") for c in all_tool_calls}
        assert "play_deterrent" not in tool_names, (
            "play_deterrent MUST NOT fire in rustling scenario — would alert suspects. "
            f"Tool calls found: {tool_names}"
        )

    def test_full_run_has_rustling_suspected_attestation(self) -> None:
        result = run("rustling", seed=42)
        rustling_events = [
            ev for ev in result.event_stream if ev.get("event_category") == "rustling_suspected"
        ]
        assert len(rustling_events) >= 1, (
            "Expected at least one event with event_category=rustling_suspected"
        )

    def test_full_run_writes_jsonl(self) -> None:
        result = run("rustling", seed=42)
        assert result.jsonl_path is not None
        assert result.jsonl_path.exists()
        lines = result.jsonl_path.read_text().splitlines()
        assert len(lines) > 0
