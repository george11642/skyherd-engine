"""Additional coverage for skyherd.server.app — live-mode branches and helpers.

The existing test_app.py covers the mock=True (SKYHERD_MOCK=1) path.
This file covers the live-injection path (mock=False with real stubs injected)
and the _live_agent_statuses / _mock_agent_statuses helpers.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from skyherd.server.app import _live_agent_statuses, _mock_agent_statuses, create_app
from skyherd.server.events import AGENT_NAMES

# ---------------------------------------------------------------------------
# Fixtures — injected world / mesh / ledger stubs
# ---------------------------------------------------------------------------


def _make_mock_world() -> MagicMock:
    world = MagicMock()
    snapshot = MagicMock()
    snapshot.model_dump.return_value = {
        "clock_iso": "2026-04-21T00:00:00Z",
        "cows": [{"id": "B001", "pos": [100.0, 200.0], "health": "ok"}],
        "predators": [],
        "drone": {"state": "idle"},
        "weather": {"wind_speed_kt": 5.0},
        "paddocks": [],
        "is_night": False,
    }
    world.snapshot.return_value = snapshot
    return world


def _make_mock_mesh() -> MagicMock:
    mesh = MagicMock()
    sessions: dict[str, Any] = {}
    for name in AGENT_NAMES:
        session = MagicMock()
        session.state = "active"
        session.last_active_ts = time.time()
        session.cumulative_tokens_in = 1000
        session.cumulative_tokens_out = 400
        session.cumulative_cost_usd = 0.002
        sessions[name] = session
    mesh._sessions = sessions
    return mesh


def _make_mock_ledger() -> MagicMock:
    ledger = MagicMock()
    entry = MagicMock()
    entry.model_dump.return_value = {
        "seq": 1,
        "ts": "2026-04-21T00:00:00Z",
        "event_type": "fence.breach",
        "hash": "abc123",
    }
    ledger.iter_events.return_value = [entry]
    return ledger


@pytest.fixture
def live_app():
    """App with injected world/mesh/ledger — exercises live-mode code paths."""
    return create_app(
        mock=False, mesh=_make_mock_mesh(), ledger=_make_mock_ledger(), world=_make_mock_world()
    )


@pytest_asyncio.fixture
async def live_client(live_app):
    async with AsyncClient(
        transport=ASGITransport(app=live_app, raise_app_exceptions=True),
        base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Live-mode snapshot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_snapshot_uses_world(live_client):
    """In live mode with a world injected, /api/snapshot calls world.snapshot()."""
    resp = await live_client.get("/api/snapshot")
    assert resp.status_code == 200
    data = resp.json()
    assert "cows" in data
    # Our injected world returns 1 cow
    assert len(data["cows"]) == 1
    assert data["cows"][0]["id"] == "B001"


# ---------------------------------------------------------------------------
# Live-mode agents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_agents_uses_mesh(live_client):
    """In live mode with a mesh injected, /api/agents calls _live_agent_statuses."""
    resp = await live_client.get("/api/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
    names = {a["name"] for a in data["agents"]}
    assert "FenceLineDispatcher" in names


# ---------------------------------------------------------------------------
# Live-mode attest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_attest_uses_ledger(live_client):
    """In live mode with a ledger injected, /api/attest calls ledger.iter_events."""
    resp = await live_client.get("/api/attest?since_seq=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert len(data["entries"]) >= 1
    assert data["entries"][0]["event_type"] == "fence.breach"


# ---------------------------------------------------------------------------
# _mock_agent_statuses helper
# ---------------------------------------------------------------------------


def test_mock_agent_statuses_returns_five():
    result = _mock_agent_statuses()
    assert len(result) == 5


def test_mock_agent_statuses_have_required_keys():
    result = _mock_agent_statuses()
    for agent in result:
        assert "name" in agent
        assert "state" in agent
        assert "last_wake" in agent
        assert "cumulative_tokens_in" in agent
        assert "cumulative_tokens_out" in agent
        assert "cumulative_cost_usd" in agent


def test_mock_agent_statuses_state_values():
    result = _mock_agent_statuses()
    for agent in result:
        assert agent["state"] in ("active", "idle")


def test_mock_agent_statuses_all_five_agent_names():
    result = _mock_agent_statuses()
    names = {a["name"] for a in result}
    assert names == set(AGENT_NAMES)


# ---------------------------------------------------------------------------
# _live_agent_statuses helper
# ---------------------------------------------------------------------------


def test_live_agent_statuses_extracts_session_fields():
    mesh = _make_mock_mesh()
    result = _live_agent_statuses(mesh)
    assert len(result) == 5
    for agent in result:
        assert "name" in agent
        assert "state" in agent
        assert agent["state"] == "active"
        assert agent["cumulative_tokens_in"] == 1000


def test_live_agent_statuses_uses_all_sessions():
    mesh = _make_mock_mesh()
    result = _live_agent_statuses(mesh)
    names = {a["name"] for a in result}
    assert names == set(AGENT_NAMES)


# ---------------------------------------------------------------------------
# Dev-mode HTML routes (static dir absent)
# ---------------------------------------------------------------------------


@pytest.fixture
def dev_app():
    """App without a static dir present — exercises the dev-mode HTML routes."""
    # Patch _STATIC_DIR to a nonexistent path so the `else` branch runs
    with patch("skyherd.server.app._STATIC_DIR") as mock_dir:
        mock_dir.exists.return_value = False
        return create_app(mock=True)


@pytest_asyncio.fixture
async def dev_client(dev_app):
    async with AsyncClient(
        transport=ASGITransport(app=dev_app, raise_app_exceptions=True),
        base_url="http://test",
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_dev_root_returns_html(dev_client):
    resp = await dev_client.get("/")
    assert resp.status_code == 200
    assert "SkyHerd" in resp.text


@pytest.mark.asyncio
async def test_dev_rancher_returns_html(dev_client):
    resp = await dev_client.get("/rancher")
    assert resp.status_code == 200
    assert "Rancher" in resp.text


# ---------------------------------------------------------------------------
# Phase 5 plan 05-01: public-accessor cost-tick path (DASH-02)
# ---------------------------------------------------------------------------


def _make_mock_mesh_with_public_accessors() -> MagicMock:
    """Mesh mock exposing ONLY Phase 1's public API (no private _sessions/_tickers).

    Shared fixture — Plan 05-03 reuses this for verify-chain + vet-intake tests.
    """
    from skyherd.server.events import AGENT_NAMES

    mesh = MagicMock()
    tickers = []
    for name in AGENT_NAMES:
        t = MagicMock()
        t.session_id = f"sess_{name.lower()}"
        t.agent_name = name
        t._current_state = "active"
        t.cumulative_cost_usd = 0.002
        t._cumulative_tokens_in = 1000
        t._cumulative_tokens_out = 400
        tickers.append(t)
    sessions = {}
    for name in AGENT_NAMES:
        s = MagicMock()
        s.id = f"sess_{name.lower()}"
        s.agent_name = name
        s.state = "active"
        s.last_active_ts = time.time()
        sessions[name] = s
    mesh.agent_tickers = MagicMock(return_value=tickers)
    mesh.agent_sessions = MagicMock(return_value=sessions)
    return mesh


def test_real_cost_tick_via_public_accessors() -> None:
    """DASH-02: _real_cost_tick must use agent_tickers() + agent_sessions(), not private attrs."""
    from skyherd.server.events import EventBroadcaster

    mesh = _make_mock_mesh_with_public_accessors()
    bc = EventBroadcaster(mock=False, mesh=mesh, ledger=None, world=MagicMock())
    tick = bc._real_cost_tick()
    assert "agents" in tick
    assert len(tick["agents"]) == 5, (
        f"Expected 5 agents via public API, got {len(tick['agents'])}. "
        "Fix: _real_cost_tick must call mesh.agent_tickers() not mesh._session_manager._tickers."
    )
    for a in tick["agents"]:
        assert isinstance(a.get("cumulative_cost_usd"), (int, float))
        assert a.get("name") in {
            "FenceLineDispatcher",
            "HerdHealthWatcher",
            "PredatorPatternLearner",
            "GrazingOptimizer",
            "CalvingWatch",
        }
    assert tick["all_idle"] is False


def test_real_cost_tick_falls_back_when_no_accessor() -> None:
    """DASH-02: meshes lacking public API must yield empty agents gracefully, not raise."""
    from skyherd.server.events import EventBroadcaster

    bare_mesh = MagicMock(spec=[])  # no attributes — .agent_tickers / .agent_sessions absent
    bc = EventBroadcaster(mock=False, mesh=bare_mesh, ledger=None, world=MagicMock())
    tick = bc._real_cost_tick()
    assert tick["agents"] == []
    assert tick["all_idle"] is True


# ---------------------------------------------------------------------------
# Phase 5 plan 05-01: DASH-01 acceptance — live /api/snapshot returns real data
# (consumes Phase 4 BLD-03 plumbing; does NOT re-implement it)
# ---------------------------------------------------------------------------


def test_snapshot_live_mode_real_world(tmp_path) -> None:
    """DASH-01: /api/snapshot in live mode returns 50 cows (not 12 mock cows).

    Factory-level proof. Complements tests/server/test_live_cli.py which
    exercises the subprocess CLI path.
    """
    try:
        from skyherd.attest.ledger import Ledger
        from skyherd.attest.signer import Signer
        from skyherd.server.app import create_app
        from skyherd.world.world import make_world
    except ImportError as exc:
        pytest.skip(f"BLD-03 prerequisite — Phase 4 live-mode plumbing required: {exc}")

    try:
        from skyherd.scenarios.base import _DemoMesh
    except ImportError as exc:
        pytest.skip(f"Phase 1 _DemoMesh required: {exc}")

    try:
        world = make_world(seed=42)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"BLD-03 prerequisite — make_world(seed=42) unavailable: {exc}")

    from fastapi.testclient import TestClient

    ledger_path = tmp_path / "dash01_ledger.db"
    signer = Signer.generate()
    ledger = Ledger.open(str(ledger_path), signer)
    mesh = _DemoMesh(ledger=ledger)

    app = create_app(mock=False, mesh=mesh, world=world, ledger=ledger)
    client = TestClient(app)

    r = client.get("/api/snapshot")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "cows" in body, f"/api/snapshot missing 'cows' key: {body.keys()}"
    assert len(body["cows"]) == 50, (
        f"DASH-01: expected 50 cows from ranch_a.yaml live world, got "
        f"{len(body['cows'])} (mock path returns 12 — mock=False not honored)."
    )
    assert body.get("sim_time_s") == 0.0, (
        f"DASH-01: live world boots at sim_time_s=0.0, got {body.get('sim_time_s')}"
    )
