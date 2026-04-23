"""Tests for AgentMesh — smoke test, session creation, task lifecycle."""

from __future__ import annotations

from skyherd.agents.mesh import _AGENT_REGISTRY, _SMOKE_WAKE_EVENTS, AgentMesh


class TestAgentRegistryConsistency:
    def test_registry_has_six_agents(self):
        """Phase 02 CRM-01: CrossRanchCoordinator added as 6th agent."""
        assert len(_AGENT_REGISTRY) == 6

    def test_smoke_wake_events_count_matches_registry(self):
        assert len(_SMOKE_WAKE_EVENTS) == len(_AGENT_REGISTRY)

    def test_all_specs_have_names(self):
        for spec, _ in _AGENT_REGISTRY:
            assert spec.name, f"Spec missing name: {spec}"

    def test_all_handlers_are_callable(self):
        for _, handler_fn in _AGENT_REGISTRY:
            assert callable(handler_fn)

    def test_six_distinct_agent_names(self):
        names = [spec.name for spec, _ in _AGENT_REGISTRY]
        assert len(set(names)) == 6


class TestAgentMeshSmokeTest:
    async def test_smoke_test_returns_dict(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh = AgentMesh()
        results = await mesh.smoke_test(sdk_client=None)
        assert isinstance(results, dict)

    async def test_smoke_test_has_six_agents(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh = AgentMesh()
        results = await mesh.smoke_test(sdk_client=None)
        assert len(results) == 6

    async def test_smoke_test_all_agents_produce_tool_calls(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh = AgentMesh()
        results = await mesh.smoke_test(sdk_client=None)
        for agent_name, calls in results.items():
            assert isinstance(calls, list), f"{agent_name} returned non-list"
            assert len(calls) > 0, f"{agent_name} produced 0 tool calls"

    async def test_smoke_test_fenceline_launches_drone(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh = AgentMesh()
        results = await mesh.smoke_test(sdk_client=None)
        fenceline_calls = results.get("FenceLineDispatcher", [])
        tools = [c["tool"] for c in fenceline_calls]
        assert "launch_drone" in tools

    async def test_smoke_test_calving_watch_pages_rancher(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh = AgentMesh()
        results = await mesh.smoke_test(sdk_client=None)
        calving_calls = results.get("CalvingWatch", [])
        tools = [c["tool"] for c in calving_calls]
        assert "page_rancher" in tools

    async def test_smoke_test_grazing_optimizer_pages_rancher(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh = AgentMesh()
        results = await mesh.smoke_test(sdk_client=None)
        grazing_calls = results.get("GrazingOptimizer", [])
        tools = [c["tool"] for c in grazing_calls]
        assert "page_rancher" in tools


class TestAgentMeshLifecycle:
    async def test_start_and_stop(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh = AgentMesh()
        await mesh.start()
        assert len(mesh._sessions) == 6
        await mesh.stop()

    async def test_start_creates_six_sessions(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh = AgentMesh()
        await mesh.start()
        try:
            assert len(mesh._sessions) == 6
        finally:
            await mesh.stop()

    async def test_stop_is_idempotent(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh = AgentMesh()
        await mesh.start()
        await mesh.stop()
        # Second stop should not raise
        await mesh.stop()
