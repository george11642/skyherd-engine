"""Tests for /api/neighbors endpoint (Phase 02 CRM-04).

Mock mode returns synthetic entries. Live mode consumes any mesh with
``.recent_events()`` callable; mesh without the attribute returns [].
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from skyherd.server.app import create_app


# ---------------------------------------------------------------------------
# Mock-mode fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_app():
    return create_app(mock=True)


@pytest_asyncio.fixture
async def mock_client(mock_app):
    async with AsyncClient(
        transport=ASGITransport(app=mock_app, raise_app_exceptions=True),
        base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Live-mode fixture with a stub mesh
# ---------------------------------------------------------------------------


def _make_stub_mesh_with_recent_events(events: list[dict[str, Any]]) -> Any:
    mesh = MagicMock()
    mesh.recent_events = MagicMock(return_value=events)
    # Provide agent accessors so other endpoints don't trip
    mesh.agent_sessions = MagicMock(return_value={})
    mesh.agent_tickers = MagicMock(return_value=[])
    return mesh


def _make_bare_mesh_no_recent_events() -> Any:
    mesh = MagicMock(spec=[])  # no attrs at all
    return mesh


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_neighbors_endpoint_returns_200_in_mock_mode(mock_client):
    resp = await mock_client.get("/api/neighbors")
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert "ts" in data


@pytest.mark.asyncio
async def test_neighbors_mock_entries_have_required_fields(mock_client):
    resp = await mock_client.get("/api/neighbors")
    data = resp.json()
    required = {
        "direction",
        "from_ranch",
        "to_ranch",
        "species",
        "shared_fence",
        "confidence",
        "ts",
        "attestation_hash",
    }
    for e in data["entries"]:
        missing = required - set(e.keys())
        assert not missing, f"entry missing fields: {missing} in {e}"


@pytest.mark.asyncio
async def test_neighbors_mock_has_both_directions(mock_client):
    resp = await mock_client.get("/api/neighbors")
    data = resp.json()
    dirs = {e["direction"] for e in data["entries"]}
    assert "inbound" in dirs
    assert "outbound" in dirs


@pytest.mark.asyncio
async def test_neighbors_live_mesh_with_recent_events_returns_list():
    sample = [
        {
            "direction": "outbound",
            "from_ranch": "ranch_a",
            "to_ranch": "ranch_b",
            "species": "coyote",
            "shared_fence": "fence_east",
            "confidence": 0.87,
            "ts": 1745200000.0,
            "attestation_hash": "sha256:live00001",
        }
    ]
    mesh = _make_stub_mesh_with_recent_events(sample)
    app = create_app(mock=False, mesh=mesh)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=True),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/neighbors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == sample


@pytest.mark.asyncio
async def test_neighbors_live_mesh_missing_recent_events_returns_empty_list():
    mesh = _make_bare_mesh_no_recent_events()
    app = create_app(mock=False, mesh=mesh)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=True),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/neighbors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == []


@pytest.mark.asyncio
async def test_neighbors_live_mesh_recent_events_raises_returns_empty_list():
    """Mesh.recent_events() raising any exception must not surface as 500."""
    mesh = MagicMock()
    mesh.recent_events = MagicMock(side_effect=RuntimeError("boom"))
    app = create_app(mock=False, mesh=mesh)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=True),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/neighbors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == []
