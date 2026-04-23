"""Tests for memory_paths.decide_write_path (Plan 01-01 Task 3).

Covers:
  - Every agent branch returns the expected (path, content) shape.
  - _redact replaces secret-bearing keys.
  - decide_write_path is byte-identical for identical inputs (determinism).
  - Unknown agent raises ValueError.
"""

from __future__ import annotations

import pytest

from skyherd.agents.memory_paths import _redact, decide_write_path


class TestPerAgentBranches:
    def test_predator_pattern_learner_returns_pattern_path(self) -> None:
        path, content = decide_write_path(
            "PredatorPatternLearner",
            {"classification": "coyote.confirmed", "ranch_id": "ranch_a", "type": "predator.detected"},
            [],
        )
        assert path == "patterns/coyote-crossings.md"
        assert "coyote" in content

    def test_herd_health_watcher_returns_notes_path(self) -> None:
        path, content = decide_write_path(
            "HerdHealthWatcher",
            {"tag": "T042", "type": "cow.motion"},
            [],
        )
        assert path == "notes/T042.md"
        assert content != ""

    def test_calving_watch_returns_baselines_path(self) -> None:
        path, content = decide_write_path(
            "CalvingWatch",
            {"tag": "T042", "type": "labor.signal"},
            [],
        )
        assert path == "baselines/T042.md"
        assert content != ""

    def test_fenceline_dispatcher_returns_dispatch_path(self) -> None:
        path, content = decide_write_path(
            "FenceLineDispatcher",
            {"segment": "seg_1", "type": "fence.breach"},
            [],
        )
        assert path == "notes/dispatch-seg_1.md"
        assert content != ""

    def test_grazing_optimizer_returns_rotation_path(self) -> None:
        path, content = decide_write_path(
            "GrazingOptimizer",
            {"ranch_id": "ranch_a", "type": "grazing.weekly"},
            [],
        )
        assert path == "notes/rotation-proposal.md"
        assert content != ""


class TestRedaction:
    def test_redact_replaces_rancher_phone(self) -> None:
        out = _redact({"rancher_phone": "+15551234567", "type": "evt"})
        assert out == {"rancher_phone": "[REDACTED]", "type": "evt"}

    def test_redact_replaces_all_known_secret_keys(self) -> None:
        inp = {
            "rancher_phone": "+15551112222",
            "vet_phone": "+15553334444",
            "auth_token": "bearer_xyz",
            "api_key": "sk-abc",
            "twilio_sid": "AC1234",
            "public_field": "keepme",
        }
        out = _redact(inp)
        for k in ("rancher_phone", "vet_phone", "auth_token", "api_key", "twilio_sid"):
            assert out[k] == "[REDACTED]", f"{k!r} should be redacted"
        assert out["public_field"] == "keepme"

    def test_redact_does_not_mutate_input(self) -> None:
        inp = {"rancher_phone": "+15551234567"}
        original_copy = dict(inp)
        _redact(inp)
        assert inp == original_copy


class TestDeterminism:
    def test_same_inputs_yield_byte_identical_output(self) -> None:
        evt = {"classification": "coyote.confirmed", "ranch_id": "ranch_a", "type": "predator.detected", "ts": 1000}
        a = decide_write_path("PredatorPatternLearner", evt, [])
        b = decide_write_path("PredatorPatternLearner", evt, [])
        assert a == b

    def test_different_classification_changes_path(self) -> None:
        a, _ = decide_write_path(
            "PredatorPatternLearner",
            {"classification": "coyote.confirmed"},
            [],
        )
        b, _ = decide_write_path(
            "PredatorPatternLearner",
            {"classification": "wolf.confirmed"},
            [],
        )
        assert a != b


class TestUnknownAgent:
    def test_raises_value_error_on_unknown_agent(self) -> None:
        with pytest.raises(ValueError, match="unknown agent"):
            decide_write_path("NonexistentAgent", {}, [])


# ---------------------------------------------------------------------------
# Phase 02 CRM-03: CrossRanchCoordinator branch
# ---------------------------------------------------------------------------


class TestCrossRanchCoordinator:
    def _event(self, **overrides) -> dict[str, object]:
        base: dict[str, object] = {
            "from_ranch": "ranch_a",
            "shared_fence": "fence_west",
            "species": "coyote",
            "confidence": 0.91,
            "ts": 1745200000.0,
        }
        base.update(overrides)
        return base

    def test_path_prefix(self) -> None:
        path, _content = decide_write_path(
            "CrossRanchCoordinator", self._event(), []
        )
        assert path.startswith("neighbors/ranch_a/")
        assert path.endswith(".md")

    def test_content_includes_species_and_confidence(self) -> None:
        _path, content = decide_write_path(
            "CrossRanchCoordinator", self._event(), []
        )
        assert "- species: coyote" in content
        assert "- confidence: 0.91" in content
        assert "response_mode: pre_position" in content

    def test_deterministic(self) -> None:
        evt = self._event()
        a = decide_write_path("CrossRanchCoordinator", evt, [])
        b = decide_write_path("CrossRanchCoordinator", evt, [])
        assert a == b

    def test_respects_redaction_for_phone_leak(self) -> None:
        evt = self._event()
        evt["rancher_phone"] = "+15551112222"
        _path, content = decide_write_path("CrossRanchCoordinator", evt, [])
        # Phone number should NOT appear in content (redacted upstream).
        assert "5551112222" not in content
        assert "[REDACTED]" not in content  # not in content body either

    def test_known_agents_includes_cross_ranch_coordinator(self) -> None:
        # If we can call decide_write_path without ValueError, CRC is registered.
        path, content = decide_write_path(
            "CrossRanchCoordinator", self._event(), []
        )
        assert path
        assert content

    def test_different_shared_fence_changes_path(self) -> None:
        a, _ = decide_write_path(
            "CrossRanchCoordinator", self._event(shared_fence="fence_west"), []
        )
        b, _ = decide_write_path(
            "CrossRanchCoordinator", self._event(shared_fence="fence_east"), []
        )
        assert a != b
