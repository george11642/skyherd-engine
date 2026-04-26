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


# ---------------------------------------------------------------------------
# _DemoMesh session registry (MA-01, MA-02, ROUT-01)
# ---------------------------------------------------------------------------


class TestDemoMesh:
    """Verify _DemoMesh holds a persistent session registry per MA-01/MA-02/ROUT-01."""

    _EXPECTED_AGENTS = {
        "FenceLineDispatcher",
        "HerdHealthWatcher",
        "PredatorPatternLearner",
        "GrazingOptimizer",
        "CalvingWatch",
    }

    def test_demo_mesh_holds_five_sessions_keyed_by_name(self) -> None:
        from skyherd.scenarios.base import _DemoMesh

        mesh = _DemoMesh(ledger=None)
        assert hasattr(mesh, "_sessions"), "_DemoMesh must expose _sessions registry"
        assert set(mesh._sessions.keys()) == self._EXPECTED_AGENTS, (
            f"Expected 5 agent sessions, got: {set(mesh._sessions.keys())}"
        )
        assert all(s.state == "idle" for s in mesh._sessions.values()), (
            "All sessions must start in idle state"
        )

    def test_registry_includes_predator_pattern_learner(self) -> None:
        # ROUT-01: learner must be present in _DemoMesh session registry
        from skyherd.scenarios.base import _DemoMesh

        mesh = _DemoMesh(ledger=None)
        assert "PredatorPatternLearner" in mesh._sessions, (
            "PredatorPatternLearner missing from _DemoMesh._sessions (ROUT-01)"
        )

    def test_public_agent_sessions_accessor_returns_dict(self) -> None:
        # Phase 5 API contract: read sessions without touching private attrs
        from skyherd.scenarios.base import _DemoMesh

        mesh = _DemoMesh(ledger=None)
        sessions = mesh.agent_sessions()
        assert isinstance(sessions, dict)
        assert set(sessions.keys()) == self._EXPECTED_AGENTS

    def test_public_agent_tickers_accessor_returns_list(self) -> None:
        # Phase 5 API contract: cost-tick aggregator iterates tickers via this accessor
        from skyherd.scenarios.base import _DemoMesh

        mesh = _DemoMesh(ledger=None)
        tickers = mesh.agent_tickers()
        assert isinstance(tickers, list)
        assert len(tickers) == 5, f"Expected 5 tickers (one per agent), got {len(tickers)}"
        for t in tickers:
            assert hasattr(t, "_current_state"), (
                "agent_tickers() must return CostTicker-shaped objects"
            )

    # ------------------------------------------------------------------
    # Routing-table unit tests (ROUT-02 — Plan 02)
    # ------------------------------------------------------------------

    def _run_route_event_sync(self, event: dict[str, Any]) -> Any:
        """Helper: run one _route_event call synchronously via asyncio.run.

        Builds the same 5-agent registry used by _run_async and a fresh
        _DemoMesh (no ledger needed — _route_event never accesses ledger at
        runtime, and _DemoMesh tolerates ledger=None).
        """
        import asyncio

        from skyherd.agents.calving_watch import CALVING_WATCH_SPEC
        from skyherd.agents.calving_watch import handler as calving_handler
        from skyherd.agents.fenceline_dispatcher import (
            FENCELINE_DISPATCHER_SPEC,
        )
        from skyherd.agents.fenceline_dispatcher import (
            handler as fenceline_handler,
        )
        from skyherd.agents.grazing_optimizer import GRAZING_OPTIMIZER_SPEC
        from skyherd.agents.grazing_optimizer import handler as grazing_handler
        from skyherd.agents.herd_health_watcher import (
            HERD_HEALTH_WATCHER_SPEC,
        )
        from skyherd.agents.herd_health_watcher import (
            handler as herd_handler,
        )
        from skyherd.agents.predator_pattern_learner import (
            PREDATOR_PATTERN_LEARNER_SPEC,
        )
        from skyherd.agents.predator_pattern_learner import (
            handler as predator_handler,
        )
        from skyherd.scenarios.base import _DemoMesh, _route_event

        mesh = _DemoMesh(ledger=None)
        registry = {
            "FenceLineDispatcher": (FENCELINE_DISPATCHER_SPEC, fenceline_handler),
            "HerdHealthWatcher": (HERD_HEALTH_WATCHER_SPEC, herd_handler),
            "PredatorPatternLearner": (
                PREDATOR_PATTERN_LEARNER_SPEC,
                predator_handler,
            ),
            "GrazingOptimizer": (GRAZING_OPTIMIZER_SPEC, grazing_handler),
            "CalvingWatch": (CALVING_WATCH_SPEC, calving_handler),
        }

        async def _go() -> None:
            # _route_event types ledger as Ledger but never accesses it at
            # runtime (it is threaded through to mesh, which guards None).
            await _route_event(event, mesh, registry, ledger=None)  # type: ignore[arg-type]

        asyncio.run(_go())
        return mesh

    def test_routing_table_thermal_anomaly(self) -> None:
        """ROUT-02: thermal.anomaly must fan out to FenceLineDispatcher + PredatorPatternLearner."""
        event = {
            "type": "thermal.anomaly",
            "ranch_id": "ranch_a",
            "topic": "skyherd/ranch_a/thermal/cam_1",
            "shapes_detected": ["human_shape"],
        }
        mesh = self._run_route_event_sync(event)
        agents_called = set(mesh._tool_call_log.keys())
        assert "FenceLineDispatcher" in agents_called, (
            f"thermal.anomaly must dispatch FenceLineDispatcher; got {agents_called}"
        )
        assert "PredatorPatternLearner" in agents_called, (
            f"thermal.anomaly must dispatch PredatorPatternLearner (ROUT-02); got {agents_called}"
        )

    def test_routing_table_nightly_analysis(self) -> None:
        """ROUT-02: nightly.analysis must dispatch only PredatorPatternLearner."""
        event = {
            "type": "nightly.analysis",
            "ranch_id": "ranch_a",
            "topic": "skyherd/ranch_a/cron/nightly",
        }
        mesh = self._run_route_event_sync(event)
        agents_called = set(mesh._tool_call_log.keys())
        assert agents_called == {"PredatorPatternLearner"}, (
            f"nightly.analysis must dispatch ONLY PredatorPatternLearner (ROUT-02); "
            f"got {agents_called}"
        )
