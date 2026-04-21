"""Tests for HerdHealthWatcher — trough_cam.motion, ClassifyPipeline stub, escalation."""

from __future__ import annotations

from skyherd.agents.herd_health_watcher import (
    HERD_HEALTH_WATCHER_SPEC,
    _simulate_handler,
    handler,
)
from skyherd.agents.session import Session, SessionManager


def _make_session() -> Session:
    mgr = SessionManager()
    return mgr.create_session(HERD_HEALTH_WATCHER_SPEC)


class TestHerdHealthWatcherSpec:
    def test_name(self):
        assert HERD_HEALTH_WATCHER_SPEC.name == "HerdHealthWatcher"

    def test_wake_topics_include_trough_cam(self):
        assert any("trough_cam" in t for t in HERD_HEALTH_WATCHER_SPEC.wake_topics)

    def test_mcp_servers(self):
        assert "sensor_mcp" in HERD_HEALTH_WATCHER_SPEC.mcp_servers
        assert "rancher_mcp" in HERD_HEALTH_WATCHER_SPEC.mcp_servers

    def test_skills_non_empty(self):
        assert len(HERD_HEALTH_WATCHER_SPEC.skills) > 0

    def test_model(self):
        assert HERD_HEALTH_WATCHER_SPEC.model == "claude-opus-4-7"


class TestHerdHealthSimulateHandler:
    def _motion_event(self, anomaly: bool = True) -> dict:
        return {
            "topic": "skyherd/ranch_a/trough_cam/trough_a",
            "type": "camera.motion",
            "ranch_id": "ranch_a",
            "trough_id": "trough_a",
            "anomaly": anomaly,
        }

    def test_returns_list(self):
        session = _make_session()
        calls = _simulate_handler(self._motion_event(), session)
        assert isinstance(calls, list)
        assert len(calls) > 0

    def test_classify_pipeline_called(self):
        session = _make_session()
        calls = _simulate_handler(self._motion_event(), session)
        tools = [c["tool"] for c in calls]
        assert "classify_pipeline" in tools

    def test_anomaly_triggers_page_rancher(self):
        session = _make_session()
        calls = _simulate_handler(self._motion_event(anomaly=True), session)
        tools = [c["tool"] for c in calls]
        assert "page_rancher" in tools

    def test_classify_pipeline_has_trough_id(self):
        session = _make_session()
        calls = _simulate_handler(self._motion_event(), session)
        pipeline_call = next(c for c in calls if c["tool"] == "classify_pipeline")
        assert pipeline_call["input"].get("trough_id") == "trough_a"

    def test_page_rancher_urgency_is_text_for_anomaly(self):
        session = _make_session()
        calls = _simulate_handler(self._motion_event(anomaly=True), session)
        rancher_call = next(c for c in calls if c["tool"] == "page_rancher")
        assert rancher_call["input"]["urgency"] == "text"


class TestHerdHealthHandlerAsync:
    async def test_handler_no_api_key_uses_simulation(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        session = _make_session()
        event = {
            "topic": "skyherd/ranch_a/trough_cam/trough_a",
            "type": "camera.motion",
            "ranch_id": "ranch_a",
            "trough_id": "trough_a",
            "anomaly": True,
        }
        calls = await handler(session, event, sdk_client=None)
        assert isinstance(calls, list)
        assert len(calls) > 0

    async def test_handler_classify_pipeline_in_calls(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        session = _make_session()
        event = {
            "topic": "skyherd/ranch_a/trough_cam/trough_a",
            "type": "camera.motion",
            "ranch_id": "ranch_a",
            "trough_id": "trough_a",
            "anomaly": True,
        }
        calls = await handler(session, event, sdk_client=None)
        tools = [c["tool"] for c in calls]
        assert "classify_pipeline" in tools
