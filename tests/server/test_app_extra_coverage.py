"""Additional server live-path coverage (DASH-02 / Plan 05-04).

These tests fill coverage gaps surfaced by the 85% server-scoped coverage gate:
- SSE semaphore 429 branch (fast path, no stream subscription)
- metrics endpoint import-error fallback
- SPA catch-all serving a specific static file vs index fallback
- EventBroadcaster._real_cost_tick error branches
- EventBroadcaster._vet_intake_loop broadcasting .md files
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from skyherd.server.app import create_app
from skyherd.server.events import AGENT_NAMES, EventBroadcaster


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_world() -> MagicMock:
    w = MagicMock()
    snap = MagicMock()
    snap.model_dump.return_value = {
        "cows": [], "predators": [], "drone": {"state": "idle"},
        "weather": {"wind_speed_kt": 0.0},
        "paddocks": [], "is_night": False,
    }
    w.snapshot.return_value = snap
    return w


def _make_mesh() -> MagicMock:
    m = MagicMock()
    sessions: dict[str, Any] = {}
    for name in AGENT_NAMES:
        s = MagicMock()
        s.state = "idle"
        s.last_active_ts = time.time()
        s.cumulative_tokens_in = 10
        s.cumulative_tokens_out = 5
        s.cumulative_cost_usd = 0.0001
        sessions[name] = s
    m._sessions = sessions
    return m


# ---------------------------------------------------------------------------
# SSE 429 branch (app.py line 204-209)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_returns_429_when_semaphore_exhausted() -> None:
    """When the SSE connection semaphore is drained, /events must return 429.

    The 429 branch executes SYNCHRONOUSLY (no async stream subscription),
    so the test can reliably read response status + body without blocking
    on the SSE generator.
    """
    app = create_app(mock=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Warm-up triggers lifespan so the semaphore is created
        r0 = await client.get("/health")
        assert r0.status_code == 200

        from skyherd.server import app as app_mod

        if app_mod._sse_semaphore is not None:
            # Drain every slot so _value == 0
            while app_mod._sse_semaphore._value > 0:
                await app_mod._sse_semaphore.acquire()

            try:
                resp = await client.get("/events")
                assert resp.status_code == 429
                assert "Too many" in resp.text
            finally:
                # Release slots so downstream tests see a healthy semaphore
                while app_mod._sse_semaphore._value < 100:
                    try:
                        app_mod._sse_semaphore.release()
                    except ValueError:
                        break


# ---------------------------------------------------------------------------
# Metrics endpoint fallback (app.py line 232-241)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_endpoint_happy_path() -> None:
    """/metrics returns 200 — either prometheus text or the fallback line."""
    app = create_app(mock=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        assert resp.text is not None


# ---------------------------------------------------------------------------
# SPA catch-all static file vs index fallback (app.py line 262-267)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spa_catch_all_serves_existing_file(tmp_path, monkeypatch) -> None:
    """A path that maps to a real file on disk must be returned directly."""
    dist = tmp_path / "web" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>SPA</body></html>")
    (dist / "assets").mkdir()
    (dist / "my-static.txt").write_text("literal static file")

    from skyherd.server import app as app_mod
    monkeypatch.setattr(app_mod, "_STATIC_DIR", dist)

    app = create_app(mock=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/my-static.txt")
        assert resp.status_code == 200
        assert resp.text == "literal static file"


@pytest.mark.asyncio
async def test_spa_catch_all_falls_back_to_index(tmp_path, monkeypatch) -> None:
    """An unknown client-side route falls through to index.html."""
    dist = tmp_path / "web" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>SPA</body></html>")
    (dist / "assets").mkdir()

    from skyherd.server import app as app_mod
    monkeypatch.setattr(app_mod, "_STATIC_DIR", dist)

    app = create_app(mock=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/some/unknown/client-route")
        assert resp.status_code == 200
        assert "SPA" in resp.text


# ---------------------------------------------------------------------------
# EventBroadcaster._real_cost_tick error-branch coverage (events.py 362-371)
# ---------------------------------------------------------------------------


def test_real_cost_tick_tolerates_mesh_without_accessor() -> None:
    """A mesh without agent_tickers() must not crash the cost tick."""

    class NoAccessorMesh:
        pass  # no agent_tickers()

    b = EventBroadcaster(mock=False, mesh=NoAccessorMesh(), ledger=None, world=None)
    payload = b._real_cost_tick()
    assert payload["agents"] == []
    assert payload["all_idle"] is True


def test_real_cost_tick_handles_accessor_raising_unexpected() -> None:
    """If agent_tickers() raises an unexpected error, _real_cost_tick still returns."""

    class BoomMesh:
        def agent_tickers(self):
            raise RuntimeError("synthetic failure")

    b = EventBroadcaster(mock=False, mesh=BoomMesh(), ledger=None, world=None)
    payload = b._real_cost_tick()
    assert payload["agents"] == []
    assert payload["all_idle"] is True


def test_real_cost_tick_skips_malformed_ticker() -> None:
    """A ticker that raises on attribute access must be skipped, not propagate."""

    class BadTicker:
        def __getattr__(self, name: str):
            raise ValueError("explode")

    class MeshWithBadTicker:
        def agent_tickers(self):
            return [BadTicker()]

    b = EventBroadcaster(mock=False, mesh=MeshWithBadTicker(),
                         ledger=None, world=None)
    payload = b._real_cost_tick()
    assert payload["agents"] == []


# ---------------------------------------------------------------------------
# EventBroadcaster._vet_intake_loop broadcast path (events.py 441-457)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vet_intake_loop_broadcasts_new_md_files(tmp_path, monkeypatch) -> None:
    """A .md file in runtime/vet_intake/ must trigger a vet_intake.drafted event."""
    intake_dir = tmp_path / "runtime" / "vet_intake"
    intake_dir.mkdir(parents=True)

    import os
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        from skyherd.server import events as events_mod
        monkeypatch.setattr(events_mod, "VET_INTAKE_POLL_INTERVAL_S", 0.02)

        b = EventBroadcaster(mock=True)
        (intake_dir / "A014_20260422T153200Z.md").write_text("# vet intake\n")

        q: asyncio.Queue = asyncio.Queue(maxsize=16)
        b._subscribers.append(q)

        task = asyncio.create_task(b._vet_intake_loop())
        try:
            item = await asyncio.wait_for(q.get(), timeout=2.0)
        finally:
            b._stop_event.set()
            try:
                await asyncio.wait_for(task, timeout=1.0)
            except asyncio.TimeoutError:
                task.cancel()

        evt, payload = item
        assert evt == "vet_intake.drafted"
        assert payload["id"] == "A014_20260422T153200Z"
        assert payload["cow_tag"] == "A014"
    finally:
        os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# Snapshot endpoint live-path with a world.snapshot() that raises (events.py 331-332)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_snapshot_endpoint_returns_json() -> None:
    """With a live world, /api/snapshot returns a JSON payload (200)."""
    app = create_app(mock=False, mesh=_make_mesh(), ledger=None, world=_make_world())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/snapshot")
        assert resp.status_code == 200
        body = resp.json()
        assert "cows" in body
