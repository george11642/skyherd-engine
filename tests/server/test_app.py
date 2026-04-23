"""Tests for the SkyHerd FastAPI server.

Uses httpx AsyncClient with the app in mock mode so no live mesh/bus is needed.
"""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from skyherd.server.app import create_app
from skyherd.server.events import EventBroadcaster


@pytest.fixture
def mock_app():
    return create_app(mock=True)


@pytest_asyncio.fixture
async def client(mock_app):
    # Use lifespan=True so the broadcaster starts up properly
    async with AsyncClient(
        transport=ASGITransport(app=mock_app, raise_app_exceptions=True),
        base_url="http://test",
    ) as c:
        yield c


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "ts" in data


# ------------------------------------------------------------------
# /api/snapshot
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_snapshot_returns_valid_json(client):
    resp = await client.get("/api/snapshot")
    assert resp.status_code == 200
    data = resp.json()
    # Must have top-level keys from WorldSnapshot
    assert "cows" in data
    assert "predators" in data
    assert "weather" in data
    assert isinstance(data["cows"], list)


@pytest.mark.asyncio
async def test_snapshot_cows_have_positions(client):
    resp = await client.get("/api/snapshot")
    data = resp.json()
    assert len(data["cows"]) > 0
    for cow in data["cows"]:
        assert "pos" in cow
        assert len(cow["pos"]) == 2


@pytest.mark.asyncio
async def test_snapshot_has_drone(client):
    resp = await client.get("/api/snapshot")
    data = resp.json()
    assert "drone" in data


# ------------------------------------------------------------------
# /api/agents
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agents_returns_six_agents(client):
    """Phase 02 adds CrossRanchCoordinator → 6 agents total."""
    resp = await client.get("/api/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
    assert len(data["agents"]) == 6


@pytest.mark.asyncio
async def test_agents_have_expected_names(client):
    resp = await client.get("/api/agents")
    data = resp.json()
    names = {a["name"] for a in data["agents"]}
    assert "FenceLineDispatcher" in names
    assert "HerdHealthWatcher" in names
    assert "PredatorPatternLearner" in names
    assert "GrazingOptimizer" in names
    assert "CalvingWatch" in names


@pytest.mark.asyncio
async def test_agents_have_state(client):
    resp = await client.get("/api/agents")
    data = resp.json()
    for agent in data["agents"]:
        assert agent["state"] in ("active", "idle", "checkpointed")


# ------------------------------------------------------------------
# /api/attest
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attest_returns_entries(client):
    resp = await client.get("/api/attest")
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert isinstance(data["entries"], list)


@pytest.mark.asyncio
async def test_attest_since_seq_param(client):
    resp = await client.get("/api/attest?since_seq=5")
    assert resp.status_code == 200


# ------------------------------------------------------------------
# /events SSE — tested via broadcaster directly (avoids lifespan/transport gap)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_events_sse_broadcaster_emits_within_3s():
    """The EventBroadcaster (which backs /events) emits events within 3s."""
    bc = EventBroadcaster(mock=True)
    bc.start()
    received = []
    try:

        async def collect():
            async for event_type, payload in bc.subscribe():
                received.append((event_type, payload))
                return

        await asyncio.wait_for(collect(), timeout=3.0)
    except TimeoutError:
        pytest.fail("EventBroadcaster did not emit any event within 3 seconds")
    finally:
        bc.stop()

    assert len(received) >= 1


@pytest.mark.asyncio
async def test_events_sse_broadcaster_emits_known_event_types():
    """Broadcaster emits only the known SkyHerd event types."""
    known_types = {"world.snapshot", "cost.tick", "attest.append", "agent.log"}
    bc = EventBroadcaster(mock=True)
    bc.start()
    seen_types: set[str] = set()
    try:

        async def collect():
            async for event_type, _payload in bc.subscribe():
                seen_types.add(event_type)
                if len(seen_types) >= 2:
                    return

        await asyncio.wait_for(collect(), timeout=5.0)
    except TimeoutError:
        pass
    finally:
        bc.stop()

    assert seen_types.issubset(known_types), f"Unexpected event types: {seen_types - known_types}"
    assert len(seen_types) >= 1
