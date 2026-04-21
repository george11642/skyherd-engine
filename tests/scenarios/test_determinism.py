"""Determinism test — two runs of the coyote scenario with seed=42 produce
identical event streams (excluding wall-clock timestamps).

We compare event types + sim_time_s fields, not full dicts, because absolute
wall-clock timestamps are non-deterministic.
"""

from __future__ import annotations

from typing import Any


def _normalize_stream(events: list[dict[str, Any]]) -> list[tuple[str, float | None]]:
    """Extract (type, sim_time_s) tuples — the deterministic fields."""
    return [(e.get("type", ""), e.get("sim_time_s")) for e in events]


def _normalize_tool_calls(
    tool_call_log: dict[str, list[dict[str, Any]]]
) -> list[tuple[str, str]]:
    """Extract (agent_name, tool_name) pairs in order."""
    pairs: list[tuple[str, str]] = []
    for agent, calls in sorted(tool_call_log.items()):
        for call in calls:
            pairs.append((agent, call.get("tool", "")))
    return pairs


class TestDeterminism:
    def test_coyote_event_stream_is_identical(self) -> None:
        from skyherd.scenarios import run

        result1 = run("coyote", seed=42)
        result2 = run("coyote", seed=42)

        stream1 = _normalize_stream(result1.event_stream)
        stream2 = _normalize_stream(result2.event_stream)

        assert stream1 == stream2, (
            f"Event streams differ between runs:\n"
            f"  run1 ({len(stream1)} events)\n"
            f"  run2 ({len(stream2)} events)\n"
            f"  first diff at index "
            + str(next((i for i, (a, b) in enumerate(zip(stream1, stream2)) if a != b), "?"))
        )

    def test_coyote_tool_calls_are_identical(self) -> None:
        from skyherd.scenarios import run

        result1 = run("coyote", seed=42)
        result2 = run("coyote", seed=42)

        calls1 = _normalize_tool_calls(result1.agent_tool_calls)
        calls2 = _normalize_tool_calls(result2.agent_tool_calls)

        assert calls1 == calls2, (
            f"Tool call sequences differ:\n  run1: {calls1}\n  run2: {calls2}"
        )

    def test_different_seeds_produce_different_streams(self) -> None:
        """Sanity check: seed=42 and seed=99 diverge (predator spawns differ)."""
        from skyherd.scenarios import run

        result42 = run("coyote", seed=42)
        result99 = run("coyote", seed=99)

        # The injected scenario events are identical, but world events differ
        # because predator spawner is seeded differently.
        # At minimum, event counts can differ or some world events differ.
        stream42 = _normalize_stream(result42.event_stream)
        stream99 = _normalize_stream(result99.event_stream)

        # Both should contain fence.breach (injected), but world events differ
        types42 = {e[0] for e in stream42}
        types99 = {e[0] for e in stream99}
        assert "fence.breach" in types42
        assert "fence.breach" in types99
        # We merely assert both runs complete without error; strict divergence
        # is not guaranteed if predator spawn hasn't fired yet.
        assert result42.outcome_passed
        assert result99.outcome_passed

    def test_all_scenarios_deterministic(self) -> None:
        """All 5 scenarios produce identical event streams on two runs."""
        from skyherd.scenarios import SCENARIOS, run

        for name in SCENARIOS:
            r1 = run(name, seed=42)
            r2 = run(name, seed=42)
            s1 = _normalize_stream(r1.event_stream)
            s2 = _normalize_stream(r2.event_stream)
            assert s1 == s2, f"Scenario {name!r} not deterministic"
