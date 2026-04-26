"""Tests for Session and SessionManager — lifecycle, checkpointing, cost gating."""

from __future__ import annotations

import json
from pathlib import Path

from skyherd.agents.session import Session, SessionManager, _mqtt_topic_matches
from skyherd.agents.spec import AgentSpec


def _make_spec(name: str = "TestAgent", wake_topics: list[str] | None = None) -> AgentSpec:
    return AgentSpec(
        name=name,
        system_prompt_template_path="src/skyherd/agents/prompts/fenceline_dispatcher.md",
        wake_topics=wake_topics or ["skyherd/+/fence/+"],
        mcp_servers=["sensor_mcp"],
        skills=[],
        checkpoint_interval_s=3600,
        max_idle_s_before_checkpoint=600,
        model="claude-opus-4-7",
    )


class TestSessionLifecycle:
    def test_create_session_returns_session(self):
        mgr = SessionManager()
        spec = _make_spec()
        session = mgr.create_session(spec)
        assert isinstance(session, Session)
        assert session.state == "idle"

    def test_session_has_unique_id(self):
        mgr = SessionManager()
        spec = _make_spec()
        s1 = mgr.create_session(spec)
        s2 = mgr.create_session(spec)
        assert s1.id != s2.id

    def test_wake_transitions_to_active(self):
        mgr = SessionManager()
        spec = _make_spec()
        session = mgr.create_session(spec)
        mgr.wake(session.id, {"type": "fence.breach"})
        assert session.state == "active"

    def test_sleep_transitions_to_idle(self):
        mgr = SessionManager()
        spec = _make_spec()
        session = mgr.create_session(spec)
        mgr.wake(session.id, {"type": "fence.breach"})
        mgr.sleep(session.id)
        assert session.state == "idle"

    def test_wake_appends_event(self):
        mgr = SessionManager()
        spec = _make_spec()
        session = mgr.create_session(spec)
        event = {"type": "fence.breach", "ranch_id": "ranch_a"}
        mgr.wake(session.id, event)
        assert event in session.wake_events_consumed

    def test_cost_accrues_only_when_active(self):
        """CostTicker must be idle-state while session is idle."""
        mgr = SessionManager()
        spec = _make_spec()
        session = mgr.create_session(spec)
        assert session._ticker is not None
        assert session._ticker._current_state == "idle"

        mgr.wake(session.id, {"type": "test"})
        assert session._ticker._current_state == "active"

        mgr.sleep(session.id)
        assert session._ticker._current_state == "idle"

    def test_to_dict_serialisable(self):
        mgr = SessionManager()
        spec = _make_spec()
        session = mgr.create_session(spec)
        d = session.to_dict()
        # Must be JSON-serialisable
        json.dumps(d)
        assert "id" in d
        assert "state" in d
        assert "agent_name" in d

    def test_checkpoint_writes_file(self, tmp_path, monkeypatch):
        import skyherd.agents.session as sess_mod

        monkeypatch.setattr(sess_mod, "_RUNTIME_DIR", tmp_path)
        mgr = SessionManager()
        spec = _make_spec()
        session = mgr.create_session(spec)
        mgr.checkpoint(session.id)
        assert session.checkpoint_path is not None
        p = Path(session.checkpoint_path)
        assert p.exists()
        data = json.loads(p.read_text())
        assert data["id"] == session.id

    def test_restore_from_checkpoint(self, tmp_path, monkeypatch):
        import skyherd.agents.session as sess_mod

        monkeypatch.setattr(sess_mod, "_RUNTIME_DIR", tmp_path)
        mgr = SessionManager()
        spec = _make_spec()
        session = mgr.create_session(spec)
        mgr.wake(session.id, {"type": "test"})
        mgr.sleep(session.id)
        mgr.checkpoint(session.id)

        # Restore
        restored = mgr.restore_from_checkpoint(session.id)
        assert restored.id == session.id
        assert restored.state in ("idle", "checkpointed")

    def test_all_tickers_returns_tickers(self):
        mgr = SessionManager()
        spec = _make_spec()
        mgr.create_session(spec)
        mgr.create_session(spec)
        tickers = mgr.all_tickers()
        assert len(tickers) == 2


class TestMqttTopicMatching:
    """Unit tests for MQTT wildcard matching logic."""

    def test_exact_match(self):
        assert _mqtt_topic_matches("skyherd/ranch_a/fence/seg_1", "skyherd/ranch_a/fence/seg_1")

    def test_single_level_wildcard(self):
        assert _mqtt_topic_matches("skyherd/ranch_a/fence/seg_1", "skyherd/+/fence/+")

    def test_single_level_wildcard_no_match_extra_level(self):
        assert not _mqtt_topic_matches("skyherd/ranch_a/fence/seg_1/extra", "skyherd/+/fence/+")

    def test_hash_wildcard_matches_suffix(self):
        assert _mqtt_topic_matches("skyherd/ranch_a/fence/seg_1/sub", "skyherd/ranch_a/#")

    def test_hash_wildcard_matches_single_level(self):
        assert _mqtt_topic_matches("skyherd/ranch_a", "skyherd/#")

    def test_no_match(self):
        assert not _mqtt_topic_matches("skyherd/ranch_a/collar/tag_007", "skyherd/+/fence/+")

    def test_plus_does_not_cross_slashes(self):
        assert not _mqtt_topic_matches("a/b/c", "a/+")


class TestOnWebhook:
    def test_on_webhook_wakes_matching_session(self):
        mgr = SessionManager()
        spec = _make_spec(name="FenceAgent", wake_topics=["skyherd/+/fence/+"])
        session = mgr.create_session(spec)
        event = {"topic": "skyherd/ranch_a/fence/seg_1", "type": "fence.breach"}
        woken = mgr.on_webhook(event)
        assert session in woken
        assert session.state == "active"

    def test_on_webhook_does_not_wake_non_matching(self):
        mgr = SessionManager()
        spec = _make_spec(name="CollarAgent", wake_topics=["skyherd/+/collar/+"])
        session = mgr.create_session(spec)
        event = {"topic": "skyherd/ranch_a/fence/seg_1", "type": "fence.breach"}
        woken = mgr.on_webhook(event)
        assert session not in woken
        assert session.state == "idle"

    def test_on_webhook_no_topic_returns_empty(self):
        mgr = SessionManager()
        spec = _make_spec()
        mgr.create_session(spec)
        woken = mgr.on_webhook({"type": "no_topic_event"})
        assert woken == []


# ---------------------------------------------------------------------------
# MA-05: Checkpoint persistence — PredatorPatternLearner across sim-day boundary
# ---------------------------------------------------------------------------


class TestCheckpointPersistence:
    """Verify Managed Agents checkpoint persistence (MA-05).

    PredatorPatternLearner runs nightly and must retain context across sim-day
    boundaries within a scenario run. The local shim models the real MA platform
    checkpoint semantics: serialize session state to runtime/sessions/{id}.json,
    then rehydrate on the other side of the boundary.
    """

    def test_predator_pattern_learner_checkpoint_round_trip(self, tmp_path, monkeypatch) -> None:
        """MA-05: learner session state survives checkpoint → restore cycle.

        Simulates a sim-day boundary: two wake events (thermal clip + nightly
        analysis), separated by sleep calls, then checkpoint + restore into a
        fresh SessionManager. wake_events_consumed must be preserved.
        """
        import skyherd.agents.session as sess_mod

        monkeypatch.setattr(sess_mod, "_RUNTIME_DIR", tmp_path)

        from skyherd.agents.predator_pattern_learner import (
            PREDATOR_PATTERN_LEARNER_SPEC,
        )
        from skyherd.agents.session import SessionManager

        mgr = SessionManager()
        session = mgr.create_session(PREDATOR_PATTERN_LEARNER_SPEC)
        session_id = session.id

        # Sim-day 1: thermal clip arrives, handler processes, sleeps.
        thermal_event = {
            "topic": "skyherd/ranch_a/thermal/cam_1",
            "type": "thermal.clip",
            "ranch_id": "ranch_a",
        }
        mgr.wake(session_id, thermal_event)
        mgr.sleep(session_id)

        # Sim-day 2: nightly analysis cron fires, handler runs, sleeps.
        nightly_event = {
            "topic": "skyherd/ranch_a/cron/nightly",
            "type": "nightly.analysis",
            "ranch_id": "ranch_a",
        }
        mgr.wake(session_id, nightly_event)
        mgr.sleep(session_id)

        # Pre-checkpoint invariant: both events recorded.
        assert len(session.wake_events_consumed) == 2, (
            f"Pre-checkpoint wake_events_consumed count wrong: {len(session.wake_events_consumed)}"
        )

        # Serialize state.
        checkpoint_path = mgr.checkpoint(session_id)
        assert checkpoint_path.exists(), f"Checkpoint file not written: {checkpoint_path}"

        # Simulate sim-day boundary: fresh SessionManager, restore from disk.
        mgr2 = SessionManager()
        # The restore path needs the session pre-registered to resolve its
        # AgentSpec (per session.py line 284). Pre-register by copying the
        # reference — mimics a scenario runner that carried the session object
        # across the boundary.
        mgr2._sessions[session_id] = session

        restored = mgr2.restore_from_checkpoint(session_id)

        # MA-05 assertions.
        assert restored.id == session_id
        assert restored.agent_name == "PredatorPatternLearner", (
            f"Agent name lost in round-trip: {restored.agent_name}"
        )
        assert len(restored.wake_events_consumed) == 2, (
            f"wake_events_consumed count lost in round-trip: {len(restored.wake_events_consumed)}"
        )
        # Event payloads preserved
        restored_types = [e.get("type") for e in restored.wake_events_consumed]
        assert "thermal.clip" in restored_types
        assert "nightly.analysis" in restored_types
        # State always restores to idle per session.py:304
        assert restored.state == "idle"

    def test_checkpoint_preserves_agent_name(self, tmp_path, monkeypatch) -> None:
        """Simple regression: agent_name survives serialization."""
        import skyherd.agents.session as sess_mod

        monkeypatch.setattr(sess_mod, "_RUNTIME_DIR", tmp_path)

        from skyherd.agents.predator_pattern_learner import (
            PREDATOR_PATTERN_LEARNER_SPEC,
        )
        from skyherd.agents.session import SessionManager

        mgr = SessionManager()
        session = mgr.create_session(PREDATOR_PATTERN_LEARNER_SPEC)
        mgr.checkpoint(session.id)

        mgr2 = SessionManager()
        mgr2._sessions[session.id] = session
        restored = mgr2.restore_from_checkpoint(session.id)
        assert restored.agent_name == "PredatorPatternLearner"

    def test_checkpoint_file_written_to_runtime_dir(self, tmp_path, monkeypatch) -> None:
        """Checkpoint writes a JSON file named {session_id}.json in _RUNTIME_DIR."""
        import skyherd.agents.session as sess_mod

        monkeypatch.setattr(sess_mod, "_RUNTIME_DIR", tmp_path)

        from skyherd.agents.predator_pattern_learner import (
            PREDATOR_PATTERN_LEARNER_SPEC,
        )
        from skyherd.agents.session import SessionManager

        mgr = SessionManager()
        session = mgr.create_session(PREDATOR_PATTERN_LEARNER_SPEC)
        path = mgr.checkpoint(session.id)

        expected_path = tmp_path / f"{session.id}.json"
        assert path == expected_path
        assert path.exists()
        assert path.suffix == ".json"
