"""Tests for MQTT webhook routing — topic matching and session targeting."""

from __future__ import annotations

from skyherd.agents.calving_watch import CALVING_WATCH_SPEC
from skyherd.agents.fenceline_dispatcher import FENCELINE_DISPATCHER_SPEC
from skyherd.agents.grazing_optimizer import GRAZING_OPTIMIZER_SPEC
from skyherd.agents.herd_health_watcher import HERD_HEALTH_WATCHER_SPEC
from skyherd.agents.predator_pattern_learner import PREDATOR_PATTERN_LEARNER_SPEC
from skyherd.agents.session import SessionManager, _mqtt_topic_matches


def _full_manager() -> tuple[SessionManager, dict]:
    """Create a SessionManager with all 5 agents registered. Returns (mgr, sessions_by_name)."""
    mgr = SessionManager()
    sessions = {}
    for spec in [
        FENCELINE_DISPATCHER_SPEC,
        HERD_HEALTH_WATCHER_SPEC,
        PREDATOR_PATTERN_LEARNER_SPEC,
        GRAZING_OPTIMIZER_SPEC,
        CALVING_WATCH_SPEC,
    ]:
        sessions[spec.name] = mgr.create_session(spec)
    return mgr, sessions


class TestTopicMatchingUnit:
    """Isolated unit tests for _mqtt_topic_matches."""

    def test_fence_topic_matches_fenceline_pattern(self):
        assert _mqtt_topic_matches("skyherd/ranch_a/fence/seg_1", "skyherd/+/fence/+")

    def test_fence_topic_does_not_match_collar_pattern(self):
        assert not _mqtt_topic_matches("skyherd/ranch_a/fence/seg_1", "skyherd/+/collar/+")

    def test_trough_cam_matches_herd_health_pattern(self):
        assert _mqtt_topic_matches("skyherd/ranch_a/trough_cam/trough_a", "skyherd/+/trough_cam/+")

    def test_thermal_matches_predator_pattern(self):
        assert _mqtt_topic_matches("skyherd/ranch_a/thermal/cam_1", "skyherd/+/thermal/+")

    def test_collar_matches_calving_watch_pattern(self):
        assert _mqtt_topic_matches("skyherd/ranch_a/collar/tag_007", "skyherd/+/collar/+")

    def test_weekly_cron_matches_grazing_pattern(self):
        assert _mqtt_topic_matches("skyherd/ranch_a/cron/weekly_monday", "skyherd/+/cron/weekly_monday")

    def test_nightly_cron_matches_predator_pattern(self):
        assert _mqtt_topic_matches("skyherd/ranch_a/cron/nightly", "skyherd/+/cron/nightly")

    def test_hash_wildcard_matches_any_suffix(self):
        assert _mqtt_topic_matches("skyherd/ranch_a/fence/seg_1/sub/deep", "skyherd/#")


class TestOnWebhookRouting:
    """Integration tests for on_webhook routing to the correct agent session."""

    def test_fence_breach_routes_only_to_fenceline(self):
        mgr, sessions = _full_manager()
        event = {"topic": "skyherd/ranch_a/fence/seg_1", "type": "fence.breach"}
        woken = mgr.on_webhook(event)
        woken_names = {s.agent_name for s in woken}
        assert "FenceLineDispatcher" in woken_names
        # Should NOT wake unrelated agents
        assert "CalvingWatch" not in woken_names
        assert "GrazingOptimizer" not in woken_names

    def test_collar_activity_routes_only_to_calving_watch(self):
        mgr, sessions = _full_manager()
        event = {"topic": "skyherd/ranch_a/collar/tag_007", "type": "collar.activity_spike"}
        woken = mgr.on_webhook(event)
        woken_names = {s.agent_name for s in woken}
        assert "CalvingWatch" in woken_names
        assert "FenceLineDispatcher" not in woken_names
        assert "GrazingOptimizer" not in woken_names

    def test_trough_cam_wakes_herd_health_and_calving(self):
        """trough_cam topics wake both HerdHealthWatcher and CalvingWatch."""
        mgr, sessions = _full_manager()
        event = {"topic": "skyherd/ranch_a/trough_cam/trough_a", "type": "camera.motion"}
        woken = mgr.on_webhook(event)
        woken_names = {s.agent_name for s in woken}
        assert "HerdHealthWatcher" in woken_names
        assert "CalvingWatch" in woken_names

    def test_thermal_wakes_fenceline_and_predator(self):
        """thermal topics wake both FenceLineDispatcher and PredatorPatternLearner."""
        mgr, sessions = _full_manager()
        event = {"topic": "skyherd/ranch_a/thermal/cam_1", "type": "thermal.clip"}
        woken = mgr.on_webhook(event)
        woken_names = {s.agent_name for s in woken}
        assert "FenceLineDispatcher" in woken_names
        assert "PredatorPatternLearner" in woken_names

    def test_weekly_cron_wakes_only_grazing_optimizer(self):
        mgr, sessions = _full_manager()
        event = {"topic": "skyherd/ranch_a/cron/weekly_monday", "type": "weekly.schedule"}
        woken = mgr.on_webhook(event)
        woken_names = {s.agent_name for s in woken}
        assert "GrazingOptimizer" in woken_names
        assert "FenceLineDispatcher" not in woken_names
        assert "HerdHealthWatcher" not in woken_names
        assert "CalvingWatch" not in woken_names

    def test_no_topic_wakes_nobody(self):
        mgr, sessions = _full_manager()
        event = {"type": "unknown_event"}
        woken = mgr.on_webhook(event)
        assert woken == []

    def test_woken_sessions_transition_to_active(self):
        mgr, sessions = _full_manager()
        event = {"topic": "skyherd/ranch_a/fence/seg_1", "type": "fence.breach"}
        woken = mgr.on_webhook(event)
        for session in woken:
            assert session.state == "active"

    def test_non_matching_sessions_remain_idle(self):
        mgr, sessions = _full_manager()
        event = {"topic": "skyherd/ranch_a/fence/seg_1", "type": "fence.breach"}
        mgr.on_webhook(event)
        # CalvingWatch and GrazingOptimizer should still be idle
        assert sessions["CalvingWatch"].state == "idle"
        assert sessions["GrazingOptimizer"].state == "idle"
