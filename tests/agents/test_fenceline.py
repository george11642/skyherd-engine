"""Tests for FencelineDispatcher — fence.breach event, tool call assertions."""

from __future__ import annotations

from skyherd.agents.fenceline_dispatcher import (
    FENCELINE_DISPATCHER_SPEC,
    _simulate_handler,
    handler,
)
from skyherd.agents.session import Session, SessionManager


def _make_session() -> Session:
    mgr = SessionManager()
    return mgr.create_session(FENCELINE_DISPATCHER_SPEC)


class TestFencelineDispatcherSpec:
    def test_name(self):
        assert FENCELINE_DISPATCHER_SPEC.name == "FenceLineDispatcher"

    def test_wake_topics_include_fence(self):
        assert any("fence" in t for t in FENCELINE_DISPATCHER_SPEC.wake_topics)

    def test_wake_topics_include_thermal(self):
        assert any("thermal" in t for t in FENCELINE_DISPATCHER_SPEC.wake_topics)

    def test_mcp_servers(self):
        assert "sensor_mcp" in FENCELINE_DISPATCHER_SPEC.mcp_servers
        assert "galileo_mcp" in FENCELINE_DISPATCHER_SPEC.mcp_servers

    def test_model(self):
        assert FENCELINE_DISPATCHER_SPEC.model == "claude-opus-4-7"

    def test_skills_non_empty(self):
        assert len(FENCELINE_DISPATCHER_SPEC.skills) > 0


class TestFencelineSimulateHandler:
    def _fence_event(self) -> dict:
        return {
            "topic": "skyherd/ranch_a/fence/seg_1",
            "type": "fence.breach",
            "ranch_id": "ranch_a",
            "segment": "seg_1",
            "lat": 34.123,
            "lon": -106.456,
        }

    def test_returns_list(self):
        session = _make_session()
        calls = _simulate_handler(self._fence_event(), session)
        assert isinstance(calls, list)
        assert len(calls) > 0

    def test_get_thermal_clip_called(self):
        session = _make_session()
        calls = _simulate_handler(self._fence_event(), session)
        tools = [c["tool"] for c in calls]
        assert "get_thermal_clip" in tools

    def test_launch_drone_called(self):
        session = _make_session()
        calls = _simulate_handler(self._fence_event(), session)
        tools = [c["tool"] for c in calls]
        assert "launch_drone" in tools

    def test_page_rancher_called(self):
        session = _make_session()
        calls = _simulate_handler(self._fence_event(), session)
        tools = [c["tool"] for c in calls]
        assert "page_rancher" in tools

    def test_launch_drone_has_coordinates(self):
        session = _make_session()
        calls = _simulate_handler(self._fence_event(), session)
        drone_call = next(c for c in calls if c["tool"] == "launch_drone")
        inp = drone_call["input"]
        has_coords = (
            "lat" in inp or "target_lat" in inp
            or "coordinates" in inp or "segment" in inp
        )
        assert has_coords, f"launch_drone input missing coordinates: {inp}"

    def test_page_rancher_includes_urgency(self):
        session = _make_session()
        calls = _simulate_handler(self._fence_event(), session)
        rancher_call = next(c for c in calls if c["tool"] == "page_rancher")
        assert "urgency" in rancher_call["input"]

    def test_play_deterrent_called(self):
        session = _make_session()
        calls = _simulate_handler(self._fence_event(), session)
        tools = [c["tool"] for c in calls]
        assert "play_deterrent" in tools


class TestFencelineHandlerAsync:
    async def test_handler_no_api_key_uses_simulation(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        session = _make_session()
        event = {
            "topic": "skyherd/ranch_a/fence/seg_1",
            "type": "fence.breach",
            "ranch_id": "ranch_a",
            "segment": "seg_1",
            "lat": 34.123,
            "lon": -106.456,
        }
        calls = await handler(session, event, sdk_client=None)
        assert isinstance(calls, list)
        assert len(calls) > 0

    async def test_handler_returns_launch_drone_and_page_rancher(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        session = _make_session()
        event = {
            "topic": "skyherd/ranch_a/fence/seg_1",
            "type": "fence.breach",
            "ranch_id": "ranch_a",
            "segment": "seg_1",
            "lat": 34.123,
            "lon": -106.456,
        }
        calls = await handler(session, event, sdk_client=None)
        tools = [c["tool"] for c in calls]
        assert "launch_drone" in tools
        assert "page_rancher" in tools
