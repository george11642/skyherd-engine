"""Tests for run_all() — all 8 scenarios back-to-back."""

from __future__ import annotations

from skyherd.scenarios import SCENARIOS, run_all


class TestRunAll:
    def test_run_all_returns_all_results(self) -> None:
        results = run_all(seed=42)
        assert len(results) == len(SCENARIOS)

    def test_run_all_covers_all_scenario_names(self) -> None:
        results = run_all(seed=42)
        result_names = {r.name for r in results}
        assert result_names == set(SCENARIOS.keys())

    def test_run_all_all_pass(self) -> None:
        results = run_all(seed=42)
        failures = [r for r in results if not r.outcome_passed]
        assert failures == [], "Failing scenarios: " + ", ".join(
            f"{r.name}({r.outcome_error})" for r in failures
        )

    def test_run_all_each_has_event_stream(self) -> None:
        results = run_all(seed=42)
        for result in results:
            assert len(result.event_stream) > 0, f"Scenario {result.name!r} produced no events"

    def test_run_all_each_has_tool_calls(self) -> None:
        results = run_all(seed=42)
        for result in results:
            total_tools = sum(len(v) for v in result.agent_tool_calls.values())
            assert total_tools > 0, f"Scenario {result.name!r} produced no tool calls"

    def test_run_all_each_has_attestation_entries(self) -> None:
        results = run_all(seed=42)
        for result in results:
            assert len(result.attestation_entries) > 0, (
                f"Scenario {result.name!r} produced no attestation entries"
            )

    def test_run_all_each_writes_jsonl(self) -> None:
        results = run_all(seed=42)
        for result in results:
            assert result.jsonl_path is not None, f"Scenario {result.name!r} did not write JSONL"
            assert result.jsonl_path.exists(), (
                f"JSONL file missing for {result.name!r}: {result.jsonl_path}"
            )

    def test_run_all_canonical_order(self) -> None:
        """Results are returned in the canonical SCENARIOS order."""
        results = run_all(seed=42)
        result_names = [r.name for r in results]
        expected_order = list(SCENARIOS.keys())
        assert result_names == expected_order

    def test_every_agent_dispatched_at_least_once_across_suite(self) -> None:
        """ROUT-04: All 5 agents must be dispatched at least once across the 8-scenario suite."""
        results = run_all(seed=42)
        dispatched: set[str] = set()
        for r in results:
            dispatched.update(r.agent_tool_calls.keys())
        required = {
            "FenceLineDispatcher",
            "HerdHealthWatcher",
            "PredatorPatternLearner",
            "GrazingOptimizer",
            "CalvingWatch",
        }
        missing = required - dispatched
        assert not missing, (
            f"Agents never dispatched anywhere in the 8-scenario suite: {missing}. "
            f"Agents dispatched: {dispatched}"
        )
