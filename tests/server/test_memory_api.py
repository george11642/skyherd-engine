"""Tests for /api/memory/{agent} endpoint (Plan 01-05)."""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from skyherd.server.app import create_app
from skyherd.server.events import (
    AGENT_NAMES,
    EventBroadcaster,
    _mock_memory_read_entry,
    _mock_memory_written_entry,
)


@pytest.fixture
def mock_app():
    return create_app(mock=True)


@pytest_asyncio.fixture
async def client(mock_app):
    async with AsyncClient(
        transport=ASGITransport(app=mock_app, raise_app_exceptions=True),
        base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_memory_returns_envelope_for_known_agent(client):
    resp = await client.get("/api/memory/FenceLineDispatcher")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("entries"), list)
    assert "ts" in data
    assert data["agent"] == "FenceLineDispatcher"


@pytest.mark.asyncio
async def test_memory_returns_404_for_unknown_agent(client):
    resp = await client.get("/api/memory/UnknownAgent")
    assert resp.status_code == 404
    assert "unknown agent" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_memory_rejects_path_traversal(client):
    """Traversal via encoded slashes must NOT expose /etc/passwd or any memory payload.

    FastAPI decodes %2f and the multi-segment path no longer matches the
    single-segment {agent} route. The response may come from the catch-all
    SPA fallback (HTML) or a 404 — either way, it's never 200 with a JSON
    memory envelope.
    """
    resp = await client.get("/api/memory/..%2fetc%2fpasswd")
    if resp.status_code == 200:
        # If 200, it's the SPA fallback (text/html), NOT a memory JSON envelope.
        content_type = resp.headers.get("content-type", "")
        assert "text/html" in content_type or "application/xhtml" in content_type
        assert "entries" not in resp.text[:500]
    else:
        assert resp.status_code in (400, 404, 405)


@pytest.mark.asyncio
async def test_memory_each_known_agent_responds_200(client):
    for name in AGENT_NAMES:
        resp = await client.get(f"/api/memory/{name}")
        assert resp.status_code == 200, f"{name} returned {resp.status_code}"


@pytest.mark.asyncio
async def test_memory_versions_endpoint(client):
    resp = await client.get("/api/memory/FenceLineDispatcher/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("entries"), list)


@pytest.mark.asyncio
async def test_mock_mode_returns_deterministic_sample(client):
    resp1 = await client.get("/api/memory/FenceLineDispatcher")
    resp2 = await client.get("/api/memory/FenceLineDispatcher")
    # Entry contents (excluding ts) are identical across sequential mock calls.
    e1 = resp1.json()["entries"]
    e2 = resp2.json()["entries"]
    assert e1 == e2


# ---------------------------------------------------------------------------
# SSE event types registered
# ---------------------------------------------------------------------------


def test_memory_written_event_type_registered():
    """_broadcast accepts 'memory.written' without error; mock generator exists."""
    broadcaster = EventBroadcaster(mock=True)
    payload = _mock_memory_written_entry()
    # No exception on unknown event type (no whitelist; all strings accepted).
    broadcaster._broadcast("memory.written", payload)
    # Mock generator keys.
    assert "memory_version_id" in payload
    assert "agent" in payload


def test_memory_read_event_type_registered():
    broadcaster = EventBroadcaster(mock=True)
    payload = _mock_memory_read_entry()
    broadcaster._broadcast("memory.read", payload)
    assert "memory_version_id" in payload


@pytest.mark.asyncio
async def test_emit_memory_written_delivers_to_subscriber():
    """emit_memory_written routes payload through _broadcast to the subscriber queue.

    We poke the subscriber queue directly (after calling _broadcast) to avoid the
    async generator dance of subscribe(), which only registers the queue on first
    __anext__() call.
    """
    broadcaster = EventBroadcaster(mock=True)
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    broadcaster._subscribers.append(q)
    try:
        await broadcaster.emit_memory_written(
            {"agent": "FLD", "memory_version_id": "memver_x"}
        )
        event_type, payload = q.get_nowait()
        assert event_type == "memory.written"
        assert payload["memory_version_id"] == "memver_x"
    finally:
        broadcaster._subscribers.remove(q)


@pytest.mark.asyncio
async def test_emit_memory_read_delivers_to_subscriber():
    broadcaster = EventBroadcaster(mock=True)
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    broadcaster._subscribers.append(q)
    try:
        await broadcaster.emit_memory_read(
            {"agent": "FLD", "memory_version_id": "memver_y"}
        )
        event_type, payload = q.get_nowait()
        assert event_type == "memory.read"
    finally:
        broadcaster._subscribers.remove(q)


# ---------------------------------------------------------------------------
# Live mode (non-mock) paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_mode_with_store_id_map_calls_list_memories(client):
    """When use_mock=False and manager is provided, router delegates to list_memories.

    Uses the mock_app client fixture and temporarily flips the module-level
    ``_state`` dict — avoids spinning up a full second create_app which can
    deadlock in test harness teardown.
    """
    from unittest.mock import AsyncMock
    from skyherd.agents.memory import ListEnvelope
    from skyherd.server import memory_api

    fake_mgr = AsyncMock()
    fake_mgr.list_memories = AsyncMock(
        return_value=ListEnvelope(
            data=[{"memory_id": "mem_live"}],
            prefixes=["patterns/"],
        )
    )
    saved = (
        memory_api._state["memory_store_manager"],
        memory_api._state["store_id_map"],
        memory_api._state["use_mock"],
    )
    try:
        memory_api._state["memory_store_manager"] = fake_mgr
        memory_api._state["store_id_map"] = {"FenceLineDispatcher": "memstore_live"}
        memory_api._state["use_mock"] = False
        resp = await client.get("/api/memory/FenceLineDispatcher")
        assert resp.status_code == 200
        assert resp.json()["entries"] == [{"memory_id": "mem_live"}]
        fake_mgr.list_memories.assert_awaited_once_with("memstore_live", path_prefix=None)
    finally:
        memory_api._state["memory_store_manager"] = saved[0]
        memory_api._state["store_id_map"] = saved[1]
        memory_api._state["use_mock"] = saved[2]


@pytest.mark.asyncio
async def test_live_mode_no_store_id_returns_503(client):
    """Live mode, agent known but no store_id registered — 503."""
    from unittest.mock import AsyncMock
    from skyherd.server import memory_api

    saved = (
        memory_api._state["memory_store_manager"],
        memory_api._state["store_id_map"],
        memory_api._state["use_mock"],
    )
    try:
        memory_api._state["memory_store_manager"] = AsyncMock()
        memory_api._state["store_id_map"] = {}
        memory_api._state["use_mock"] = False
        resp = await client.get("/api/memory/FenceLineDispatcher")
        assert resp.status_code == 503
    finally:
        memory_api._state["memory_store_manager"] = saved[0]
        memory_api._state["store_id_map"] = saved[1]
        memory_api._state["use_mock"] = saved[2]


@pytest.mark.asyncio
async def test_live_mode_upstream_failure_returns_502(client):
    from unittest.mock import AsyncMock
    from skyherd.server import memory_api

    fake_mgr = AsyncMock()
    fake_mgr.list_memories = AsyncMock(side_effect=RuntimeError("upstream dead"))
    saved = (
        memory_api._state["memory_store_manager"],
        memory_api._state["store_id_map"],
        memory_api._state["use_mock"],
    )
    try:
        memory_api._state["memory_store_manager"] = fake_mgr
        memory_api._state["store_id_map"] = {"FenceLineDispatcher": "memstore_live"}
        memory_api._state["use_mock"] = False
        resp = await client.get("/api/memory/FenceLineDispatcher")
        assert resp.status_code == 502
    finally:
        memory_api._state["memory_store_manager"] = saved[0]
        memory_api._state["store_id_map"] = saved[1]
        memory_api._state["use_mock"] = saved[2]


@pytest.mark.asyncio
async def test_live_mode_versions_delegates(client):
    from unittest.mock import AsyncMock
    from skyherd.agents.memory import MemoryVersion
    from skyherd.server import memory_api

    fake_mgr = AsyncMock()
    fake_mgr.list_versions = AsyncMock(return_value=[
        MemoryVersion(
            id="memver_live",
            operation="created",
            created_by={"type": "api_actor", "api_key_id": "apikey_live"},
            path="/patterns/x.md",
        )
    ])
    saved = (
        memory_api._state["memory_store_manager"],
        memory_api._state["store_id_map"],
        memory_api._state["use_mock"],
    )
    try:
        memory_api._state["memory_store_manager"] = fake_mgr
        memory_api._state["store_id_map"] = {"FenceLineDispatcher": "memstore_live"}
        memory_api._state["use_mock"] = False
        resp = await client.get("/api/memory/FenceLineDispatcher/versions")
        assert resp.status_code == 200
        assert len(resp.json()["entries"]) == 1
        assert resp.json()["entries"][0]["id"] == "memver_live"
    finally:
        memory_api._state["memory_store_manager"] = saved[0]
        memory_api._state["store_id_map"] = saved[1]
        memory_api._state["use_mock"] = saved[2]
