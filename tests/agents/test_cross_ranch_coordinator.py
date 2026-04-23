"""Unit tests for CrossRanchCoordinator (Phase 02 CRM-01).

All tests run WITHOUT an Anthropic API key — simulate path is used throughout.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from skyherd.agents.cross_ranch_coordinator import (
    CROSS_RANCH_COORDINATOR_SPEC,
    _simulate_handler,
    handler,
)
from skyherd.agents.session import SessionManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def session():
    sm = SessionManager()
    return sm.create_session(CROSS_RANCH_COORDINATOR_SPEC)


@pytest.fixture()
def wake_event() -> dict[str, Any]:
    return {
        "type": "neighbor_alert",
        "topic": "skyherd/neighbor/ranch_a/ranch_b/predator_confirmed",
        "ranch_id": "ranch_b",
        "from_ranch": "ranch_a",
        "shared_fence": "fence_west",
        "species": "coyote",
        "confidence": 0.91,
        "ts": 1745200000.0,
        "attestation_hash": "sha256:abcdef1234567890",
    }


# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------


class TestSpec:
    def test_spec_name(self):
        assert CROSS_RANCH_COORDINATOR_SPEC.name == "CrossRanchCoordinator"

    def test_spec_wake_topics_matches_neighbor_pattern(self):
        topics = CROSS_RANCH_COORDINATOR_SPEC.wake_topics
        assert len(topics) == 1
        assert topics[0] == "skyherd/neighbor/+/+/predator_confirmed"

    def test_spec_mcp_servers(self):
        servers = set(CROSS_RANCH_COORDINATOR_SPEC.mcp_servers)
        assert {"drone_mcp", "sensor_mcp", "galileo_mcp"} == servers

    def test_spec_skills_five_entries(self):
        assert len(CROSS_RANCH_COORDINATOR_SPEC.skills) == 5

    def test_spec_skills_cover_three_domains(self):
        paths = CROSS_RANCH_COORDINATOR_SPEC.skills
        assert any("predator-ids" in p for p in paths)
        assert any("nm-ecology" in p for p in paths)
        assert any("voice-persona" in p for p in paths)

    def test_spec_model(self):
        assert CROSS_RANCH_COORDINATOR_SPEC.model == "claude-opus-4-7"

    def test_spec_checkpoint_interval(self):
        assert CROSS_RANCH_COORDINATOR_SPEC.checkpoint_interval_s == 1800

    def test_spec_system_prompt_file_exists(self):
        from pathlib import Path

        p = Path(CROSS_RANCH_COORDINATOR_SPEC.system_prompt_template_path)
        assert p.exists(), f"system prompt file missing: {p}"


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


class TestSimulation:
    def test_returns_three_tool_calls(self, session, wake_event):
        calls = _simulate_handler(wake_event, session)
        assert len(calls) == 3

    def test_no_page_rancher(self, session, wake_event):
        calls = _simulate_handler(wake_event, session)
        tools = {c["tool"] for c in calls}
        assert "page_rancher" not in tools

    def test_mission_is_neighbor_pre_position_patrol(self, session, wake_event):
        calls = _simulate_handler(wake_event, session)
        launches = [c for c in calls if c["tool"] == "launch_drone"]
        assert len(launches) == 1
        assert launches[0]["input"]["mission"] == "neighbor_pre_position_patrol"

    def test_deterministic(self, session, wake_event):
        a = _simulate_handler(wake_event, session)
        b = _simulate_handler(wake_event, session)
        assert a == b

    def test_log_agent_event_has_neighbor_handoff(self, session, wake_event):
        calls = _simulate_handler(wake_event, session)
        log_calls = [c for c in calls if c["tool"] == "log_agent_event"]
        assert len(log_calls) == 1
        assert log_calls[0]["input"]["event_type"] == "neighbor_handoff"
        assert log_calls[0]["input"]["response_mode"] == "pre_position"

    def test_species_and_confidence_propagate(self, session):
        event = {
            "ranch_id": "ranch_b",
            "from_ranch": "ranch_c",
            "shared_fence": "fence_south",
            "species": "mountain_lion",
            "confidence": 0.77,
        }
        calls = _simulate_handler(event, _session_for(event))
        log_call = next(c for c in calls if c["tool"] == "log_agent_event")
        assert log_call["input"]["species"] == "mountain_lion"
        assert log_call["input"]["confidence"] == pytest.approx(0.77)
        launch_call = next(c for c in calls if c["tool"] == "launch_drone")
        assert "mountain_lion" in launch_call["input"]["note"]

    def test_thermal_clip_scoped_to_shared_fence(self, session, wake_event):
        calls = _simulate_handler(wake_event, session)
        thermal = next(c for c in calls if c["tool"] == "get_thermal_clip")
        assert thermal["input"]["segment"] == wake_event["shared_fence"]

    def test_registered_in_handlers_dict(self):
        from skyherd.agents.simulate import HANDLERS

        assert "CrossRanchCoordinator" in HANDLERS


# ---------------------------------------------------------------------------
# Handler entry point
# ---------------------------------------------------------------------------


class TestHandler:
    async def test_handler_simulate_path_without_api_key(
        self, session, wake_event, monkeypatch
    ):
        """No API key → simulate path returns 3 tool calls."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        calls = await handler(session, wake_event, sdk_client=None)
        assert len(calls) == 3
        assert any(c["tool"] == "launch_drone" for c in calls)

    async def test_handler_loads_skills_without_crashing(
        self, session, wake_event, monkeypatch
    ):
        """Handler must not explode on missing skill files — build_cached_messages
        gracefully treats missing files as empty strings via _load_text."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        calls = await handler(session, wake_event, sdk_client=None)
        assert isinstance(calls, list)

    async def test_handler_with_sdk_client_and_api_key_delegates_to_run_handler_cycle(
        self, session, wake_event, monkeypatch
    ):
        """With API key + sdk_client, handler calls run_handler_cycle."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-stub")

        import skyherd.agents.cross_ranch_coordinator as mod

        mock_cycle = AsyncMock(return_value=[{"tool": "mocked", "input": {}}])
        monkeypatch.setattr(mod, "run_handler_cycle", mock_cycle)

        dummy_client = object()
        calls = await handler(session, wake_event, sdk_client=dummy_client)
        assert calls == [{"tool": "mocked", "input": {}}]
        mock_cycle.assert_awaited_once()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session_for(_event: dict[str, Any]):
    sm = SessionManager()
    return sm.create_session(CROSS_RANCH_COORDINATOR_SPEC)
