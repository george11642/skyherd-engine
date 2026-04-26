"""Tests for ManagedSessionManager and _handler_base run_handler_cycle.

All external Anthropic API calls are mocked — no real API key required.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skyherd.agents.fenceline_dispatcher import (
    FENCELINE_DISPATCHER_SPEC,
)
from skyherd.agents.fenceline_dispatcher import (
    handler as fenceline_handler,
)
from skyherd.agents.herd_health_watcher import (
    HERD_HEALTH_WATCHER_SPEC,
)
from skyherd.agents.herd_health_watcher import (
    handler as herd_handler,
)
from skyherd.agents.managed import ManagedAgentsUnavailable, ManagedSession, ManagedSessionManager
from skyherd.agents.session import LocalSessionManager, SessionManager, get_session_manager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fence_event() -> dict[str, Any]:
    return {
        "topic": "skyherd/ranch_a/fence/seg_1",
        "type": "fence.breach",
        "ranch_id": "ranch_a",
        "segment": "seg_1",
        "lat": 34.123,
        "lon": -106.456,
    }


def _make_trough_event() -> dict[str, Any]:
    return {
        "topic": "skyherd/ranch_a/trough_cam/trough_a",
        "type": "camera.motion",
        "ranch_id": "ranch_a",
        "trough_id": "trough_a",
        "anomaly": True,
    }


# ---------------------------------------------------------------------------
# ManagedAgentsUnavailable
# ---------------------------------------------------------------------------


class TestManagedAgentsUnavailable:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ManagedAgentsUnavailable, match="ANTHROPIC_API_KEY"):
            ManagedSessionManager(api_key="")

    def test_is_runtime_error(self):
        assert issubclass(ManagedAgentsUnavailable, RuntimeError)


# ---------------------------------------------------------------------------
# get_session_manager factory
# ---------------------------------------------------------------------------


class TestGetSessionManagerFactory:
    def test_local_runtime_returns_local(self):
        mgr = get_session_manager(runtime="local")
        assert isinstance(mgr, LocalSessionManager)

    def test_auto_without_env_returns_local(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("SKYHERD_AGENTS", raising=False)
        mgr = get_session_manager(runtime="auto")
        assert isinstance(mgr, LocalSessionManager)

    def test_auto_with_local_env_set_returns_local(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        monkeypatch.setenv("SKYHERD_AGENTS", "local")  # not "managed"
        mgr = get_session_manager(runtime="auto")
        assert isinstance(mgr, LocalSessionManager)

    def test_managed_runtime_raises_without_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises((ManagedAgentsUnavailable, Exception)):
            get_session_manager(runtime="managed")


# ---------------------------------------------------------------------------
# ManagedSession dataclass
# ---------------------------------------------------------------------------


class TestManagedSession:
    def _make(self) -> ManagedSession:
        return ManagedSession(
            id="local-uuid",
            agent_name="FenceLineDispatcher",
            platform_session_id="sess_abc123",
            platform_agent_id="agent_xyz",
            platform_env_id="env_001",
        )

    def test_to_dict_has_platform_ids(self):
        sess = self._make()
        d = sess.to_dict()
        assert d["platform_session_id"] == "sess_abc123"
        assert d["platform_agent_id"] == "agent_xyz"
        assert d["platform_env_id"] == "env_001"

    def test_default_state_is_idle(self):
        sess = self._make()
        assert sess.state == "idle"

    def test_to_dict_has_token_fields(self):
        sess = self._make()
        d = sess.to_dict()
        assert "cumulative_tokens_in" in d
        assert "cumulative_tokens_out" in d


# ---------------------------------------------------------------------------
# _handler_base.run_handler_cycle — no API key → returns []
# ---------------------------------------------------------------------------


class TestRunHandlerCycleNoKey:
    @pytest.mark.asyncio
    async def test_returns_empty_without_api_key(self, monkeypatch):
        from skyherd.agents._handler_base import run_handler_cycle

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mgr = SessionManager()
        session = mgr.create_session(FENCELINE_DISPATCHER_SPEC)
        cached_payload = {"system": [], "messages": []}

        # With sdk_client=None, should return []
        result = await run_handler_cycle(session, {}, None, cached_payload)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_with_stub_client_no_key(self, monkeypatch):
        from skyherd.agents._handler_base import run_handler_cycle

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mgr = SessionManager()
        session = mgr.create_session(FENCELINE_DISPATCHER_SPEC)
        cached_payload = {"system": [], "messages": []}
        stub = MagicMock()

        result = await run_handler_cycle(session, {}, stub, cached_payload)
        assert result == []


# ---------------------------------------------------------------------------
# _handler_base.run_handler_cycle — local runtime with mocked API response
# ---------------------------------------------------------------------------


class TestRunHandlerCycleLocalMock:
    def _make_mock_client(self, tool_name: str = "launch_drone") -> MagicMock:
        """Return a mock AsyncAnthropic client whose messages.create returns a tool_use block."""
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.name = tool_name
        mock_block.input = {"segment": "seg_1"}

        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50
        mock_usage.cache_read_input_tokens = 80
        mock_usage.cache_creation_input_tokens = 0

        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        return mock_client

    @pytest.mark.asyncio
    async def test_extracts_tool_use_blocks(self, monkeypatch):
        from skyherd.agents._handler_base import run_handler_cycle

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        monkeypatch.delenv("SKYHERD_AGENTS", raising=False)

        mgr = SessionManager()
        session = mgr.create_session(FENCELINE_DISPATCHER_SPEC)
        cached_payload = {
            "system": [{"type": "text", "text": "You are FenceLineDispatcher."}],
            "messages": [{"role": "user", "content": [{"type": "text", "text": "WAKE EVENT"}]}],
        }
        mock_client = self._make_mock_client("launch_drone")

        result = await run_handler_cycle(session, {}, mock_client, cached_payload)
        assert len(result) == 1
        assert result[0]["tool"] == "launch_drone"
        assert result[0]["input"] == {"segment": "seg_1"}

    @pytest.mark.asyncio
    async def test_token_counts_updated(self, monkeypatch):
        from skyherd.agents._handler_base import run_handler_cycle

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        monkeypatch.delenv("SKYHERD_AGENTS", raising=False)

        mgr = SessionManager()
        session = mgr.create_session(HERD_HEALTH_WATCHER_SPEC)
        cached_payload = {
            "system": [{"type": "text", "text": "You are HerdHealthWatcher."}],
            "messages": [{"role": "user", "content": [{"type": "text", "text": "WAKE"}]}],
        }
        mock_client = self._make_mock_client("log_observation")

        await run_handler_cycle(session, {}, mock_client, cached_payload)
        # input_tokens + cache_read + cache_write = 100 + 80 + 0 = 180
        assert session.cumulative_tokens_in == 180
        assert session.cumulative_tokens_out == 50

    @pytest.mark.asyncio
    async def test_passes_system_blocks_to_messages_create(self, monkeypatch):
        """C1 fix: system blocks with cache_control must reach messages.create."""
        from skyherd.agents._handler_base import run_handler_cycle

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        monkeypatch.delenv("SKYHERD_AGENTS", raising=False)

        mgr = SessionManager()
        session = mgr.create_session(FENCELINE_DISPATCHER_SPEC)

        system_blocks = [
            {"type": "text", "text": "System prompt.", "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": "Skill text.", "cache_control": {"type": "ephemeral"}},
        ]
        messages = [{"role": "user", "content": [{"type": "text", "text": "wake"}]}]
        cached_payload = {"system": system_blocks, "messages": messages}
        mock_client = self._make_mock_client("page_rancher")

        await run_handler_cycle(session, {}, mock_client, cached_payload)

        # Verify messages.create was called with the full system blocks (C1 fix)
        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs is not None
        passed_system = call_kwargs.kwargs.get(
            "system", call_kwargs.args[0] if call_kwargs.args else None
        )
        if passed_system is None and call_kwargs.kwargs:
            passed_system = call_kwargs.kwargs.get("system")
        # The system arg must be the list with cache_control blocks
        assert passed_system == system_blocks, (
            f"C1 fix: expected system blocks with cache_control to be passed, got: {passed_system}"
        )


# ---------------------------------------------------------------------------
# Handler simulation paths — no API key
# ---------------------------------------------------------------------------


class TestHandlerSimulationPaths:
    @pytest.mark.asyncio
    async def test_fenceline_handler_sim_returns_tool_calls(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mgr = LocalSessionManager()
        session = mgr.create_session(FENCELINE_DISPATCHER_SPEC)
        calls = await fenceline_handler(session, _make_fence_event(), sdk_client=None)
        assert isinstance(calls, list)
        assert len(calls) > 0
        tools = [c["tool"] for c in calls]
        assert "launch_drone" in tools or "get_thermal_clip" in tools

    @pytest.mark.asyncio
    async def test_herd_health_handler_sim_returns_tool_calls(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mgr = LocalSessionManager()
        session = mgr.create_session(HERD_HEALTH_WATCHER_SPEC)
        calls = await herd_handler(session, _make_trough_event(), sdk_client=None)
        assert isinstance(calls, list)
        assert len(calls) > 0


# ---------------------------------------------------------------------------
# ManagedSessionManager — mocked platform calls
# ---------------------------------------------------------------------------


class TestManagedSessionManagerMocked:
    def _make_manager(self, monkeypatch, tmp_path) -> ManagedSessionManager:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        mgr = ManagedSessionManager(
            api_key="sk-test-fake",
            agent_ids_path=str(tmp_path / "agent_ids.json"),
        )
        return mgr

    @pytest.mark.asyncio
    async def test_ensure_agent_creates_and_caches(self, monkeypatch, tmp_path):
        mgr = self._make_manager(monkeypatch, tmp_path)

        mock_agent = MagicMock()
        mock_agent.id = "agent_test_001"
        mgr._client.beta = MagicMock()
        mgr._client.beta.agents = MagicMock()
        mgr._client.beta.agents.create = AsyncMock(return_value=mock_agent)

        agent_id = await mgr.ensure_agent(FENCELINE_DISPATCHER_SPEC)
        assert agent_id == "agent_test_001"
        assert FENCELINE_DISPATCHER_SPEC.name in mgr._agent_ids
        assert (tmp_path / "agent_ids.json").exists()

    @pytest.mark.asyncio
    async def test_ensure_agent_uses_cached_id(self, monkeypatch, tmp_path):
        mgr = self._make_manager(monkeypatch, tmp_path)
        mgr._agent_ids[FENCELINE_DISPATCHER_SPEC.name] = "agent_cached"
        mgr._client.beta = MagicMock()
        mgr._client.beta.agents = MagicMock()
        mgr._client.beta.agents.create = AsyncMock()

        agent_id = await mgr.ensure_agent(FENCELINE_DISPATCHER_SPEC)
        assert agent_id == "agent_cached"
        mgr._client.beta.agents.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_environment_creates_and_caches(self, monkeypatch, tmp_path):
        mgr = self._make_manager(monkeypatch, tmp_path)

        mock_env = MagicMock()
        mock_env.id = "env_test_001"
        mgr._client.beta = MagicMock()
        mgr._client.beta.environments = MagicMock()
        mgr._client.beta.environments.create = AsyncMock(return_value=mock_env)

        # Override cache path to tmp_path
        with patch("skyherd.agents.managed.Path") as mock_path_cls:
            # Don't patch Path entirely — just stub the env cache check
            env_cache = MagicMock()
            env_cache.exists.return_value = False
            env_cache.parent = MagicMock()
            env_cache.write_text = MagicMock()
            # Restore normal Path for other uses
            mock_path_cls.side_effect = lambda p: (
                env_cache if "ma_environment_id" in str(p) else Path(p)
            )

            # Reset cached env ID
            mgr._environment_id = None
            env_id = await mgr._ensure_environment()
            assert env_id == "env_test_001"

    @pytest.mark.asyncio
    async def test_create_session_async_returns_managed_session(self, monkeypatch, tmp_path):
        mgr = self._make_manager(monkeypatch, tmp_path)

        # Pre-seed agent + env IDs so no network calls for those
        mgr._agent_ids[FENCELINE_DISPATCHER_SPEC.name] = "agent_xyz"
        mgr._environment_id = "env_abc"

        mock_platform_session = MagicMock()
        mock_platform_session.id = "sess_platform_001"
        mgr._client.beta = MagicMock()
        mgr._client.beta.sessions = MagicMock()
        mgr._client.beta.sessions.create = AsyncMock(return_value=mock_platform_session)

        sess = await mgr.create_session_async(FENCELINE_DISPATCHER_SPEC)
        assert isinstance(sess, ManagedSession)
        assert sess.platform_session_id == "sess_platform_001"
        assert sess.platform_agent_id == "agent_xyz"
        assert sess.platform_env_id == "env_abc"
        assert sess.agent_name == "FenceLineDispatcher"
        assert sess.state == "idle"


# ---------------------------------------------------------------------------
# _run_managed — mocked SSE stream
# ---------------------------------------------------------------------------


class TestRunManaged:
    """Cover the _run_managed SSE path in _handler_base."""

    def _make_stream_event(self, event_type: str, **attrs):
        ev = MagicMock()
        ev.type = event_type
        for k, v in attrs.items():
            setattr(ev, k, v)
        return ev

    def _make_managed_client(self, events: list) -> MagicMock:
        """Return a mock sdk_client whose beta.sessions.events.stream yields *events*.

        The real SDK's AsyncEvents.stream() is ``async def`` — it returns a coroutine
        that resolves to an AsyncStream (which is itself an async context manager).
        The mock must match: stream() is an awaitable coroutine, and the awaited result
        supports ``async with`` + ``async for``.  The fix under test is the
        ``async with await ...stream(...)`` pattern; without the inner ``await`` the
        code would try to enter the coroutine object as a context manager, raising
        TypeError.
        """
        from contextlib import asynccontextmanager

        # Inner async CM that the awaited coroutine returns.
        @asynccontextmanager
        async def _stream_cm():
            async def _gen():
                for ev in events:
                    yield ev

            stream = MagicMock()
            stream.__aiter__ = lambda s: _gen()
            yield stream

        # Outer coroutine — mirrors ``async def stream(session_id) -> AsyncStream``.
        async def _fake_stream(_session_id):
            return _stream_cm()

        mock_client = MagicMock()
        mock_client.beta = MagicMock()
        mock_client.beta.sessions = MagicMock()
        mock_client.beta.sessions.events = MagicMock()
        mock_client.beta.sessions.events.send = AsyncMock()
        mock_client.beta.sessions.events.stream = _fake_stream
        return mock_client

    @pytest.mark.asyncio
    async def test_run_managed_extracts_tool_use(self, monkeypatch):
        from skyherd.agents._handler_base import _run_managed

        mgr = SessionManager()
        session = mgr.create_session(FENCELINE_DISPATCHER_SPEC)

        tool_ev = self._make_stream_event(
            "agent.custom_tool_use",
            name="launch_drone",
            input={"segment": "seg_1"},
            id="tool_use_001",
        )
        idle_ev = self._make_stream_event("session.status_terminated")

        mock_client = self._make_managed_client([tool_ev, idle_ev])
        cached_payload = {
            "system": [],
            "messages": [{"role": "user", "content": [{"type": "text", "text": "wake"}]}],
        }

        calls = await _run_managed(
            session=session,
            sdk_client=mock_client,
            cached_payload=cached_payload,
            platform_session_id="sess_abc",
            tool_dispatcher=None,
        )
        assert len(calls) == 1
        assert calls[0]["tool"] == "launch_drone"

    @pytest.mark.asyncio
    async def test_run_managed_calls_tool_dispatcher(self, monkeypatch):
        from skyherd.agents._handler_base import _run_managed

        mgr = SessionManager()
        session = mgr.create_session(FENCELINE_DISPATCHER_SPEC)

        tool_ev = self._make_stream_event(
            "agent.custom_tool_use",
            name="get_thermal_clip",
            input={"segment": "seg_1"},
            id="tool_use_002",
        )
        idle_ev = self._make_stream_event("session.status_terminated")

        mock_client = self._make_managed_client([tool_ev, idle_ev])
        dispatch_results = []

        async def _dispatcher(name, inp):
            dispatch_results.append(name)
            return "ok"

        cached_payload = {
            "system": [],
            "messages": [{"role": "user", "content": [{"type": "text", "text": "wake"}]}],
        }

        await _run_managed(
            session=session,
            sdk_client=mock_client,
            cached_payload=cached_payload,
            platform_session_id="sess_abc",
            tool_dispatcher=_dispatcher,
        )
        assert "get_thermal_clip" in dispatch_results

    @pytest.mark.asyncio
    async def test_run_managed_usage_tokens_counted(self, monkeypatch):
        from skyherd.agents._handler_base import _run_managed

        mgr = SessionManager()
        session = mgr.create_session(FENCELINE_DISPATCHER_SPEC)

        usage = MagicMock()
        usage.input_tokens = 200
        usage.output_tokens = 75
        span_ev = self._make_stream_event("span.model_request_end", model_usage=usage)
        idle_ev = self._make_stream_event("session.status_terminated")

        mock_client = self._make_managed_client([span_ev, idle_ev])
        cached_payload = {
            "system": [],
            "messages": [{"role": "user", "content": [{"type": "text", "text": "wake"}]}],
        }

        await _run_managed(
            session=session,
            sdk_client=mock_client,
            cached_payload=cached_payload,
            platform_session_id="sess_abc",
            tool_dispatcher=None,
        )
        assert session.cumulative_tokens_in == 200
        assert session.cumulative_tokens_out == 75

    @pytest.mark.asyncio
    async def test_run_managed_idle_requires_action_does_not_break(self, monkeypatch):
        """session.status_idle with stop_reason.type=requires_action must NOT break the loop."""
        from skyherd.agents._handler_base import _run_managed

        mgr = SessionManager()
        session = mgr.create_session(FENCELINE_DISPATCHER_SPEC)

        # requires_action idle — loop continues
        stop_reason = MagicMock()
        stop_reason.type = "requires_action"
        transient_idle = self._make_stream_event("session.status_idle", stop_reason=stop_reason)

        # Then a tool_use event after the transient idle
        tool_ev = self._make_stream_event(
            "agent.custom_tool_use",
            name="page_rancher",
            input={"urgency": "high"},
            id="tool_003",
        )
        terminal = self._make_stream_event("session.status_terminated")

        mock_client = self._make_managed_client([transient_idle, tool_ev, terminal])
        cached_payload = {
            "system": [],
            "messages": [{"role": "user", "content": [{"type": "text", "text": "wake"}]}],
        }

        calls = await _run_managed(
            session=session,
            sdk_client=mock_client,
            cached_payload=cached_payload,
            platform_session_id="sess_abc",
            tool_dispatcher=None,
        )
        # page_rancher must be in the calls list (loop didn't break early)
        assert any(c["tool"] == "page_rancher" for c in calls)

    @pytest.mark.asyncio
    async def test_stream_is_awaited_before_async_with(self):
        """Regression: stream() coroutine must be awaited before async-with.

        The real SDK's AsyncEvents.stream() is ``async def`` — it returns a
        coroutine, NOT an AsyncStream directly.  Using ``async with stream(...)``
        without ``await`` would pass the unawaited coroutine object to
        ``__aenter__``, which raises TypeError at runtime.  This test guards
        against that regression by using a mock that returns an awaitable
        coroutine (matching the real SDK shape): if the code omits ``await``,
        Python raises ``TypeError: object coroutine can't be used in 'async with'``
        and the test fails.
        """
        from skyherd.agents._handler_base import _run_managed

        mgr = SessionManager()
        session = mgr.create_session(FENCELINE_DISPATCHER_SPEC)

        terminal = self._make_stream_event("session.status_terminated")
        mock_client = self._make_managed_client([terminal])
        cached_payload = {
            "system": [],
            "messages": [{"role": "user", "content": [{"type": "text", "text": "wake"}]}],
        }

        # Must not raise TypeError — if await is missing this blows up.
        calls = await _run_managed(
            session=session,
            sdk_client=mock_client,
            cached_payload=cached_payload,
            platform_session_id="sess_regression",
            tool_dispatcher=None,
        )
        assert calls == []

    @pytest.mark.asyncio
    async def test_managed_stream_session_events_awaits_coroutine(self):
        """Regression: ManagedSessionManager.stream_session_events must await stream().

        Guards the same ``async with await ...stream(...)`` fix in managed.py.
        A mock whose .stream() is an async def coroutine (not a context manager
        directly) will raise TypeError if the await is missing.
        """
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock, patch

        terminal = self._make_stream_event("session.status_terminated")

        @asynccontextmanager
        async def _stream_cm():
            async def _gen():
                yield terminal

            s = MagicMock()
            s.__aiter__ = lambda self: _gen()
            yield s

        async def _fake_stream(_session_id):
            return _stream_cm()

        mock_client = MagicMock()
        mock_client.beta.sessions.events.stream = _fake_stream

        with patch("anthropic.AsyncAnthropic", return_value=mock_client):
            mgr = ManagedSessionManager.__new__(ManagedSessionManager)
            mgr._client = mock_client

        ms = ManagedSession(
            id="local-1",
            agent_name="FenceLineDispatcher",
            platform_session_id="sess_reg2",
            platform_agent_id="agent_reg2",
            platform_env_id="env_reg2",
        )

        # Collect events — must not raise TypeError.
        collected = []
        async for ev in mgr.stream_session_events(ms):
            collected.append(ev)

        assert len(collected) == 1
        assert collected[0].type == "session.status_terminated"


# ---------------------------------------------------------------------------
# Webhook router
# ---------------------------------------------------------------------------


class TestWebhookRouter:
    """Cover skyherd.agents.webhook via httpx TestClient."""

    def _make_app(self):
        from fastapi import FastAPI

        from skyherd.agents.webhook import webhook_router

        app = FastAPI()
        app.include_router(webhook_router)
        return app

    @pytest.mark.asyncio
    async def test_post_returns_204_no_secret(self):
        from httpx import ASGITransport, AsyncClient

        import skyherd.agents.webhook as wh

        original_secret = wh._WEBHOOK_SECRET
        wh._WEBHOOK_SECRET = ""  # dev mode — skip sig check
        try:
            app = self._make_app()
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/webhooks/managed-agents",
                    json={"type": "agent.custom_tool_use", "session_id": "sess_1"},
                )
            assert resp.status_code == 204
        finally:
            wh._WEBHOOK_SECRET = original_secret

    @pytest.mark.asyncio
    async def test_post_routes_to_mesh(self):
        from httpx import ASGITransport, AsyncClient

        import skyherd.agents.webhook as wh

        original_secret = wh._WEBHOOK_SECRET
        original_mesh = wh._mesh_ref
        wh._WEBHOOK_SECRET = ""

        received = []
        mock_mesh = MagicMock()
        mock_mesh.on_webhook = lambda ev: received.append(ev)
        wh._mesh_ref = mock_mesh

        try:
            app = self._make_app()
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post(
                    "/webhooks/managed-agents",
                    json={"type": "fence.breach", "session_id": "sess_2", "ranch_id": "ranch_a"},
                )
            assert len(received) == 1
            assert received[0]["type"] == "fence.breach"
            assert received[0]["ranch_id"] == "ranch_a"
        finally:
            wh._WEBHOOK_SECRET = original_secret
            wh._mesh_ref = original_mesh

    @pytest.mark.asyncio
    async def test_post_invalid_signature_returns_401(self):
        from httpx import ASGITransport, AsyncClient

        import skyherd.agents.webhook as wh

        original_secret = wh._WEBHOOK_SECRET
        wh._WEBHOOK_SECRET = "real-secret"
        try:
            app = self._make_app()
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/webhooks/managed-agents",
                    json={"type": "agent.custom_tool_use", "session_id": "sess_3"},
                    headers={"X-SkyHerd-Signature": "sha256=badsig"},
                )
            assert resp.status_code == 401
        finally:
            wh._WEBHOOK_SECRET = original_secret

    @pytest.mark.asyncio
    async def test_post_valid_signature_accepted(self):
        import hashlib
        import hmac
        import json

        from httpx import ASGITransport, AsyncClient

        import skyherd.agents.webhook as wh

        secret = "test-secret-xyz"
        original_secret = wh._WEBHOOK_SECRET
        wh._WEBHOOK_SECRET = secret
        try:
            body = json.dumps({"type": "fence.breach", "session_id": "sess_4"}).encode()
            sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            app = self._make_app()
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/webhooks/managed-agents",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-SkyHerd-Signature": sig,
                    },
                )
            assert resp.status_code == 204
        finally:
            wh._WEBHOOK_SECRET = original_secret

    def test_verify_signature_no_secret_always_true(self):
        import skyherd.agents.webhook as wh

        original = wh._WEBHOOK_SECRET
        wh._WEBHOOK_SECRET = ""
        try:
            assert wh._verify_signature(b"anything", None) is True
            assert wh._verify_signature(b"anything", "wrong") is True
        finally:
            wh._WEBHOOK_SECRET = original

    def test_verify_signature_missing_header_returns_false(self):
        import skyherd.agents.webhook as wh

        original = wh._WEBHOOK_SECRET
        wh._WEBHOOK_SECRET = "real-secret"
        try:
            assert wh._verify_signature(b"body", None) is False
        finally:
            wh._WEBHOOK_SECRET = original


# ---------------------------------------------------------------------------
# ManagedSessionManager lifecycle methods
# ---------------------------------------------------------------------------


class TestManagedSessionManagerLifecycle:
    """Cover sleep/wake/checkpoint/on_webhook and platform event helpers."""

    def _make_manager_with_session(self, monkeypatch, tmp_path) -> tuple:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        mgr = ManagedSessionManager(
            api_key="sk-test-fake",
            agent_ids_path=str(tmp_path / "agent_ids.json"),
        )
        sess = ManagedSession(
            id="local-sess-001",
            agent_name="FenceLineDispatcher",
            platform_session_id="platform-sess-001",
            platform_agent_id="agent-xyz",
            platform_env_id="env-abc",
            agent_spec=FENCELINE_DISPATCHER_SPEC,
        )
        mgr._sessions["local-sess-001"] = sess
        return mgr, sess

    def test_sleep_sets_idle(self, monkeypatch, tmp_path):
        mgr, sess = self._make_manager_with_session(monkeypatch, tmp_path)
        sess.state = "active"
        result = mgr.sleep("local-sess-001")
        assert result.state == "idle"

    def test_wake_sets_active_and_records_event(self, monkeypatch, tmp_path):
        mgr, sess = self._make_manager_with_session(monkeypatch, tmp_path)
        event = {"topic": "skyherd/ranch_a/fence/seg_1", "type": "fence.breach"}
        result = mgr.wake("local-sess-001", event)
        assert result.state == "active"
        assert event in result.wake_events_consumed

    def test_checkpoint_writes_file(self, monkeypatch, tmp_path):
        mgr, sess = self._make_manager_with_session(monkeypatch, tmp_path)
        # Override runtime/sessions to tmp_path

        import skyherd.agents.managed as ma_mod

        original_path = ma_mod.Path
        try:
            path = mgr.checkpoint("local-sess-001")
            assert path.exists()
            assert sess.state == "checkpointed"
        finally:
            pass  # no patch needed — uses real Path

    def test_get_raises_on_unknown_session(self, monkeypatch, tmp_path):
        mgr, _ = self._make_manager_with_session(monkeypatch, tmp_path)
        with pytest.raises(KeyError, match="Unknown MA session"):
            mgr._get("nonexistent-id")

    def test_get_session_returns_session(self, monkeypatch, tmp_path):
        mgr, sess = self._make_manager_with_session(monkeypatch, tmp_path)
        assert mgr.get_session("local-sess-001") is sess

    def test_all_sessions_returns_list(self, monkeypatch, tmp_path):
        mgr, sess = self._make_manager_with_session(monkeypatch, tmp_path)
        sessions = mgr.all_sessions()
        assert isinstance(sessions, list)
        assert sess in sessions

    def test_all_tickers_returns_empty(self, monkeypatch, tmp_path):
        mgr, _ = self._make_manager_with_session(monkeypatch, tmp_path)
        assert mgr.all_tickers() == []

    def test_on_webhook_wakes_matching_session(self, monkeypatch, tmp_path):
        mgr, sess = self._make_manager_with_session(monkeypatch, tmp_path)
        event = {"topic": "skyherd/ranch_a/fence/seg_1", "type": "fence.breach"}
        woken = mgr.on_webhook(event)
        assert sess in woken
        assert sess.state == "active"

    def test_on_webhook_no_match_returns_empty(self, monkeypatch, tmp_path):
        mgr, sess = self._make_manager_with_session(monkeypatch, tmp_path)
        event = {"topic": "skyherd/ranch_a/trough_cam/trough_a", "type": "camera.motion"}
        # FenceLineDispatcher only matches fence/+  and thermal/+ — trough_cam won't match
        woken = mgr.on_webhook(event)
        # trough_cam doesn't match FENCELINE topics, so no wakes
        assert sess not in woken

    def test_restore_from_checkpoint_round_trips(self, monkeypatch, tmp_path):
        mgr, sess = self._make_manager_with_session(monkeypatch, tmp_path)
        # Write checkpoint then delete from memory and restore
        mgr.checkpoint("local-sess-001")
        del mgr._sessions["local-sess-001"]
        restored = mgr.restore_from_checkpoint("local-sess-001")
        assert restored.platform_session_id == "platform-sess-001"
        assert restored.agent_name == "FenceLineDispatcher"

    def test_restore_from_checkpoint_missing_raises(self, monkeypatch, tmp_path):
        mgr, _ = self._make_manager_with_session(monkeypatch, tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.restore_from_checkpoint("no-such-id")

    def test_load_text_missing_returns_empty(self, monkeypatch, tmp_path):
        mgr, _ = self._make_manager_with_session(monkeypatch, tmp_path)
        result = ManagedSessionManager._load_text("/no/such/file.txt")
        assert result == ""

    @pytest.mark.asyncio
    async def test_send_wake_event_calls_platform(self, monkeypatch, tmp_path):
        mgr, sess = self._make_manager_with_session(monkeypatch, tmp_path)
        mgr._client.beta = MagicMock()
        mgr._client.beta.sessions = MagicMock()
        mgr._client.beta.sessions.events = MagicMock()
        mgr._client.beta.sessions.events.send = AsyncMock()

        await mgr.send_wake_event(sess, "hello ranch")

        mgr._client.beta.sessions.events.send.assert_called_once()
        call_args = mgr._client.beta.sessions.events.send.call_args
        assert call_args.args[0] == "platform-sess-001"
        events = call_args.kwargs.get(
            "events", call_args.args[1] if len(call_args.args) > 1 else []
        )
        assert events[0]["type"] == "user.message"

    @pytest.mark.asyncio
    async def test_send_tool_result_calls_platform(self, monkeypatch, tmp_path):
        mgr, sess = self._make_manager_with_session(monkeypatch, tmp_path)
        mgr._client.beta = MagicMock()
        mgr._client.beta.sessions = MagicMock()
        mgr._client.beta.sessions.events = MagicMock()
        mgr._client.beta.sessions.events.send = AsyncMock()

        await mgr.send_tool_result(sess, "tool_use_123", "result payload")

        mgr._client.beta.sessions.events.send.assert_called_once()
        call_args = mgr._client.beta.sessions.events.send.call_args
        events = call_args.kwargs.get(
            "events", call_args.args[1] if len(call_args.args) > 1 else []
        )
        assert events[0]["type"] == "user.custom_tool_result"
        assert events[0]["custom_tool_use_id"] == "tool_use_123"

    @pytest.mark.asyncio
    async def test_smoke_test_session_returns_platform_id(self, monkeypatch, tmp_path):
        mgr, _ = self._make_manager_with_session(monkeypatch, tmp_path)

        # Pre-seed agent + env IDs
        mgr._agent_ids[FENCELINE_DISPATCHER_SPEC.name] = "agent_xyz"
        mgr._environment_id = "env_abc"

        mock_platform_session = MagicMock()
        mock_platform_session.id = "sess_smoke_001"
        mgr._client.beta = MagicMock()
        mgr._client.beta.sessions = MagicMock()
        mgr._client.beta.sessions.create = AsyncMock(return_value=mock_platform_session)
        mgr._client.beta.sessions.events = MagicMock()
        mgr._client.beta.sessions.events.send = AsyncMock()

        wake_event = {
            "type": "fence.breach",
            "ranch_id": "ranch_a",
            "topic": "skyherd/ranch_a/fence/seg_1",
        }
        result = await mgr.smoke_test_session(FENCELINE_DISPATCHER_SPEC, wake_event)
        assert result == "sess_smoke_001"


# ---------------------------------------------------------------------------
# Plan 01-03: _build_tools_config + memory_store_ids extra_body attach (MEM-02, MEM-11)
# ---------------------------------------------------------------------------


class TestBuildToolsConfig:
    def test_build_tools_config_no_disable_returns_default_config(self):
        from skyherd.agents.managed import _build_tools_config
        from skyherd.agents.spec import AgentSpec

        spec = AgentSpec(name="X", system_prompt_template_path="/tmp/x.md")
        cfg = _build_tools_config(spec)
        assert cfg["type"] == "agent_toolset_20260401"
        assert cfg["default_config"] == {"enabled": True}
        assert "configs" not in cfg

    def test_build_tools_config_with_disable_emits_configs(self):
        from skyherd.agents.managed import _build_tools_config
        from skyherd.agents.spec import AgentSpec

        spec = AgentSpec(
            name="X",
            system_prompt_template_path="/tmp/x.md",
            disable_tools=["web_search", "web_fetch"],
        )
        cfg = _build_tools_config(spec)
        assert cfg["configs"] == [
            {"name": "web_search", "enabled": False},
            {"name": "web_fetch", "enabled": False},
        ]

    def test_build_tools_config_handles_spec_without_attr(self):
        from skyherd.agents.managed import _build_tools_config

        class BareSpec:
            pass

        cfg = _build_tools_config(BareSpec())
        assert cfg["type"] == "agent_toolset_20260401"
        assert "configs" not in cfg


class TestEnsureAgentToolsConfig:
    @pytest.mark.asyncio
    async def test_ensure_agent_passes_tools_config_from_spec(self, monkeypatch, tmp_path):
        from skyherd.agents.managed import _build_tools_config
        from skyherd.agents.spec import AgentSpec

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        monkeypatch.chdir(tmp_path)

        mgr = ManagedSessionManager(
            api_key="sk-test-fake",
            agent_ids_path=str(tmp_path / "agent_ids.json"),
        )
        # Mock the beta.agents.create call to capture tools kwarg.
        mock_agent_response = MagicMock()
        mock_agent_response.id = "agent_xyz"
        mgr._client = MagicMock()
        mgr._client.beta = MagicMock()
        mgr._client.beta.agents = MagicMock()
        mgr._client.beta.agents.create = AsyncMock(return_value=mock_agent_response)

        spec_path = tmp_path / "sys.md"
        spec_path.write_text("System prompt.")
        spec = AgentSpec(
            name="CalvingWatch",
            system_prompt_template_path=str(spec_path),
            disable_tools=["web_search"],
        )

        await mgr.ensure_agent(spec)
        create_kwargs = mgr._client.beta.agents.create.await_args.kwargs
        assert create_kwargs["tools"] == [_build_tools_config(spec)]


class TestSessionCreateMemoryAttach:
    @pytest.fixture
    def _mocked_mgr(self, monkeypatch, tmp_path):
        """Build a MSM with create_session_async primed but dependencies mocked."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        monkeypatch.chdir(tmp_path)

        def _factory(memory_store_ids: dict[str, str] | None = None):
            mgr = ManagedSessionManager(
                api_key="sk-test-fake",
                environment_id="env_test",
                agent_ids_path=str(tmp_path / "agent_ids.json"),
                memory_store_ids=memory_store_ids,
            )
            mgr._client = MagicMock()
            mgr._client.beta = MagicMock()
            mgr._client.beta.sessions = MagicMock()
            mock_session = MagicMock()
            mock_session.id = "sess_fake"
            mgr._client.beta.sessions.create = AsyncMock(return_value=mock_session)
            # Skip real agent creation — patch ensure_agent + _ensure_environment.
            mgr.ensure_agent = AsyncMock(return_value="agent_X")  # type: ignore
            mgr._ensure_environment = AsyncMock(return_value="env_test")  # type: ignore
            return mgr

        return _factory

    @pytest.mark.asyncio
    async def test_session_create_attaches_memory_resources_via_extra_body(self, _mocked_mgr):
        from skyherd.agents.fenceline_dispatcher import FENCELINE_DISPATCHER_SPEC

        mgr = _mocked_mgr(
            memory_store_ids={
                "FenceLineDispatcher": "memstore_perA",
                "_shared": "memstore_shared",
            }
        )
        await mgr.create_session_async(FENCELINE_DISPATCHER_SPEC)
        kwargs = mgr._client.beta.sessions.create.await_args.kwargs
        assert kwargs["extra_body"] == {
            "resources": [
                {
                    "type": "memory_store",
                    "memory_store_id": "memstore_perA",
                    "access": "read_write",
                },
                {
                    "type": "memory_store",
                    "memory_store_id": "memstore_shared",
                    "access": "read_only",
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_session_create_no_extra_body_when_no_memory_store_ids(self, _mocked_mgr):
        from skyherd.agents.fenceline_dispatcher import FENCELINE_DISPATCHER_SPEC

        mgr = _mocked_mgr(memory_store_ids=None)
        await mgr.create_session_async(FENCELINE_DISPATCHER_SPEC)
        kwargs = mgr._client.beta.sessions.create.await_args.kwargs
        assert "extra_body" not in kwargs

    @pytest.mark.asyncio
    async def test_session_create_only_shared_when_no_per_agent_entry(self, _mocked_mgr):
        from skyherd.agents.fenceline_dispatcher import FENCELINE_DISPATCHER_SPEC

        # PredatorPatternLearner not in the map, only _shared entry
        mgr = _mocked_mgr(memory_store_ids={"_shared": "memstore_shared"})
        await mgr.create_session_async(FENCELINE_DISPATCHER_SPEC)
        kwargs = mgr._client.beta.sessions.create.await_args.kwargs
        assert kwargs["extra_body"] == {
            "resources": [
                {
                    "type": "memory_store",
                    "memory_store_id": "memstore_shared",
                    "access": "read_only",
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_session_create_only_per_agent_when_no_shared(self, _mocked_mgr):
        from skyherd.agents.fenceline_dispatcher import FENCELINE_DISPATCHER_SPEC

        mgr = _mocked_mgr(memory_store_ids={"FenceLineDispatcher": "memstore_fld"})
        await mgr.create_session_async(FENCELINE_DISPATCHER_SPEC)
        kwargs = mgr._client.beta.sessions.create.await_args.kwargs
        assert kwargs["extra_body"] == {
            "resources": [
                {"type": "memory_store", "memory_store_id": "memstore_fld", "access": "read_write"},
            ]
        }
