"""Live-mode EventBroadcaster integration tests — DASH-02 coverage scaffold.

Uses EventBroadcaster.subscribe() directly per RESEARCH.md Pitfall 2
(httpx.AsyncClient.stream() + ASGITransport hangs with SSE).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from skyherd.server.events import AGENT_NAMES, EventBroadcaster


def _make_ticker_mock(agent_name: str, *, state: str = "active") -> MagicMock:
    ticker = MagicMock()
    ticker.session_id = f"sess_{agent_name.lower()}"
    ticker.agent_name = agent_name
    ticker._current_state = state
    ticker.cumulative_cost_usd = 0.002
    ticker._cumulative_tokens_in = 1000
    ticker._cumulative_tokens_out = 400
    return ticker


def _make_session_mock(agent_name: str) -> MagicMock:
    s = MagicMock()
    s.id = f"sess_{agent_name.lower()}"
    s.agent_name = agent_name
    s.state = "active"
    s.last_active_ts = time.time()
    return s


def _make_mesh_with_public_accessors(state: str = "active") -> MagicMock:
    mesh = MagicMock()
    tickers = [_make_ticker_mock(name, state=state) for name in AGENT_NAMES]
    sessions = {name: _make_session_mock(name) for name in AGENT_NAMES}
    mesh.agent_tickers = MagicMock(return_value=tickers)
    mesh.agent_sessions = MagicMock(return_value=sessions)
    return mesh


def _make_ledger_mock_with_events(count: int = 3) -> MagicMock:
    ledger = MagicMock()
    events = []
    for seq in range(1, count + 1):
        ev = MagicMock()
        ev.seq = seq
        ev.model_dump = MagicMock(return_value={"seq": seq, "kind": "test", "source": "test"})
        events.append(ev)
    ledger.iter_events = MagicMock(return_value=iter(events))
    return ledger


@pytest.mark.asyncio
async def test_live_cost_tick_emits_six_agents() -> None:
    """DASH-02 + CRM-01: live cost.tick carries 6 agent entries via public accessors."""
    mesh = _make_mesh_with_public_accessors(state="active")
    bc = EventBroadcaster(mock=False, mesh=mesh, ledger=None, world=MagicMock())
    bc.start()
    try:
        async def first_cost_tick() -> dict[str, Any]:
            async for etype, payload in bc.subscribe():
                if etype == "cost.tick":
                    return payload
            return {}

        tick = await asyncio.wait_for(first_cost_tick(), timeout=5.0)
        assert "agents" in tick, f"cost.tick missing 'agents' key: {tick}"
        assert len(tick["agents"]) == 6, (
            f"Expected 6 agents from 6-ticker mesh, got {len(tick['agents'])}."
        )
        for a in tick["agents"]:
            assert isinstance(a.get("cumulative_cost_usd"), (int, float))
        assert tick.get("all_idle") is False
    finally:
        bc.stop()


@pytest.mark.asyncio
async def test_live_attest_append_forwards_ledger_iter_events() -> None:
    """DASH-02: live attest.append forwards every Event.model_dump() from ledger."""
    ledger = _make_ledger_mock_with_events(count=3)
    bc = EventBroadcaster(
        mock=False,
        mesh=_make_mesh_with_public_accessors(),
        ledger=ledger,
        world=MagicMock(),
    )
    bc.start()
    try:
        seen_seqs: list[int] = []

        async def collect() -> None:
            async for etype, payload in bc.subscribe():
                if etype == "attest.append":
                    seen_seqs.append(payload["seq"])
                    if len(seen_seqs) >= 3:
                        return

        await asyncio.wait_for(collect(), timeout=5.0)
        assert sorted(seen_seqs) == [1, 2, 3], f"Expected seqs [1,2,3], got {sorted(seen_seqs)}"
    finally:
        bc.stop()
