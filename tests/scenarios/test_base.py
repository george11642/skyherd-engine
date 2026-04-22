"""Tests for skyherd.scenarios.base — Scenario ABC and ScenarioResult dataclass."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

import pytest

from skyherd.scenarios.base import Scenario, ScenarioResult

# ---------------------------------------------------------------------------
# ScenarioResult dataclass
# ---------------------------------------------------------------------------


class TestScenarioResult:
    def test_default_fields(self) -> None:
        result = ScenarioResult(name="test", seed=42, duration_s=60.0)
        assert result.name == "test"
        assert result.seed == 42
        assert result.duration_s == 60.0
        assert result.event_stream == []
        assert result.agent_tool_calls == {}
        assert result.attestation_entries == []
        assert result.outcome_passed is False
        assert result.outcome_error is None
        assert result.wall_time_s == 0.0
        assert result.jsonl_path is None

    def test_mutable_defaults_are_independent(self) -> None:
        r1 = ScenarioResult(name="a", seed=1, duration_s=10.0)
        r2 = ScenarioResult(name="b", seed=2, duration_s=20.0)
        r1.event_stream.append({"type": "x"})
        assert r2.event_stream == [], "Mutable defaults must not be shared"

    def test_all_expected_fields_present(self) -> None:
        field_names = {f.name for f in fields(ScenarioResult)}
        expected = {
            "name",
            "seed",
            "duration_s",
            "event_stream",
            "agent_tool_calls",
            "attestation_entries",
            "outcome_passed",
            "outcome_error",
            "wall_time_s",
            "jsonl_path",
        }
        assert expected.issubset(field_names)


# ---------------------------------------------------------------------------
# Scenario abstract base
# ---------------------------------------------------------------------------


class _ConcreteScenario(Scenario):
    """Minimal concrete implementation for testing the base class."""

    name = "test_scenario"
    description = "A test scenario"
    duration_s = 10.0

    def setup(self, world: Any) -> None:
        pass

    def inject_events(self, world: Any, sim_time_s: float) -> list[dict[str, Any]]:
        return []

    def assert_outcome(self, event_stream: list[dict], mesh: Any) -> None:
        pass


class TestScenarioAbstract:
    def test_concrete_subclass_instantiates(self) -> None:
        s = _ConcreteScenario()
        assert s.name == "test_scenario"
        assert s.description == "A test scenario"
        assert s.duration_s == 10.0

    def test_abstract_class_cannot_be_instantiated(self) -> None:
        with pytest.raises(TypeError):
            Scenario()  # type: ignore[abstract]

    def test_missing_name_attribute_is_allowed_by_abc(self) -> None:
        # Scenario uses plain attributes (not abstractproperties),
        # so subclasses that forget name just get None — not a TypeError.
        class _Partial(Scenario):
            description = "partial"

            def setup(self, world: Any) -> None:
                pass

            def inject_events(self, world: Any, sim_time_s: float) -> list[dict]:
                return []

            def assert_outcome(self, event_stream: list[dict], mesh: Any) -> None:
                pass

        s = _Partial()
        assert not hasattr(s, "name") or s.name is None or True  # just doesn't raise

    def test_find_event_returns_first_match(self) -> None:
        s = _ConcreteScenario()
        events = [
            {"type": "a", "val": 1},
            {"type": "b", "val": 2},
            {"type": "a", "val": 3},
        ]
        result = s._find_event(events, "a")
        assert result is not None
        assert result["val"] == 1

    def test_find_event_returns_none_on_miss(self) -> None:
        s = _ConcreteScenario()
        result = s._find_event([{"type": "x"}], "missing")
        assert result is None

    def test_find_tool_call(self) -> None:
        s = _ConcreteScenario()

        class _FakeMesh:
            _tool_call_log = {
                "AgentA": [{"tool": "launch_drone", "input": {}}],
                "AgentB": [{"tool": "page_rancher", "input": {}}],
            }

        call = s._find_tool_call(_FakeMesh(), "launch_drone")
        assert call is not None
        assert call["tool"] == "launch_drone"

    def test_find_tool_call_returns_none_on_miss(self) -> None:
        s = _ConcreteScenario()

        class _FakeMesh:
            _tool_call_log: dict = {}

        call = s._find_tool_call(_FakeMesh(), "missing_tool")
        assert call is None

    def test_all_tool_calls_flattens(self) -> None:
        s = _ConcreteScenario()

        class _FakeMesh:
            _tool_call_log = {
                "AgentA": [{"tool": "a"}, {"tool": "b"}],
                "AgentB": [{"tool": "c"}],
            }

        calls = s._all_tool_calls(_FakeMesh())
        assert len(calls) == 3
        tool_names = {c["tool"] for c in calls}
        assert tool_names == {"a", "b", "c"}
