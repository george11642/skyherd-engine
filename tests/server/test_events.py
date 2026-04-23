"""Tests for EventBroadcaster — source merging and backpressure."""

from __future__ import annotations

import asyncio
import random

import pytest

from skyherd.server.events import (
    AGENT_NAMES,
    EventBroadcaster,
    _mock_agent_log,
    _mock_attest_entry,
    _mock_cost_tick,
    _mock_world_snapshot,
)

# ------------------------------------------------------------------
# Mock data generators
# ------------------------------------------------------------------


def test_mock_world_snapshot_shape():
    snap = _mock_world_snapshot()
    assert "cows" in snap
    assert "predators" in snap
    assert "weather" in snap
    assert "drone" in snap
    assert "paddocks" in snap
    assert "water_tanks" in snap
    assert isinstance(snap["cows"], list)
    assert len(snap["cows"]) > 0


def test_mock_world_snapshot_cow_positions():
    snap = _mock_world_snapshot()
    for cow in snap["cows"]:
        x, y = cow["pos"]
        assert 0.0 <= x <= 1.0
        assert 0.0 <= y <= 1.0


def test_mock_cost_tick_shape():
    tick = _mock_cost_tick(1)
    assert "agents" in tick
    assert len(tick["agents"]) == 6
    assert "all_idle" in tick
    assert "rate_per_hr_usd" in tick
    assert "total_cumulative_usd" in tick


def test_mock_cost_tick_agent_names():
    tick = _mock_cost_tick(1)
    names = {a["name"] for a in tick["agents"]}
    assert names == set(AGENT_NAMES)


def test_mock_cost_tick_paused_when_all_idle():
    """When all agents are idle, rate should be 0."""
    # We can't deterministically force all idle in mock, but we can check shape
    for seq in range(1, 20):
        tick = _mock_cost_tick(seq)
        if tick["all_idle"]:
            assert tick["rate_per_hr_usd"] == 0.0
        else:
            assert tick["rate_per_hr_usd"] == 0.08


def test_mock_cost_tick_rate_string():
    """Verify the 0.08 constant is present in tick payload."""
    found = False
    for seq in range(1, 20):
        tick = _mock_cost_tick(seq)
        if not tick["all_idle"]:
            assert tick["rate_per_hr_usd"] == 0.08
            found = True
    # At least one active tick expected over 20 iterations
    assert found, "Expected at least one active cost tick in 20 iterations"


def test_mock_attest_entry_shape():
    entry = _mock_attest_entry()
    assert "seq" in entry
    assert "ts_iso" in entry
    assert "source" in entry
    assert "kind" in entry
    assert "event_hash" in entry
    assert "signature" in entry
    assert "prev_hash" in entry


def test_mock_agent_log_shape():
    rng = random.Random(42)
    log = _mock_agent_log(rng)
    assert "agent" in log
    assert "message" in log
    assert "state" in log
    assert log["agent"] in AGENT_NAMES


# ------------------------------------------------------------------
# EventBroadcaster
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcaster_starts_and_stops():
    bc = EventBroadcaster(mock=True)
    bc.start()
    await asyncio.sleep(0.05)
    bc.stop()
    # No exception = pass


@pytest.mark.asyncio
async def test_broadcaster_emits_events():
    bc = EventBroadcaster(mock=True)
    bc.start()

    received = []

    async def collect():
        async for event_type, payload in bc.subscribe():
            received.append((event_type, payload))
            if len(received) >= 3:
                break

    try:
        await asyncio.wait_for(collect(), timeout=5.0)
    except TimeoutError:
        pytest.fail("Broadcaster did not emit 3 events within 5s")
    finally:
        bc.stop()

    assert len(received) >= 3


@pytest.mark.asyncio
async def test_broadcaster_emits_cost_tick():
    bc = EventBroadcaster(mock=True)
    bc.start()

    cost_events = []

    async def collect():
        async for event_type, payload in bc.subscribe():
            if event_type == "cost.tick":
                cost_events.append(payload)
                if len(cost_events) >= 1:
                    break

    try:
        await asyncio.wait_for(collect(), timeout=5.0)
    except TimeoutError:
        pytest.fail("Broadcaster did not emit a cost.tick within 5s")
    finally:
        bc.stop()

    assert len(cost_events) >= 1
    tick = cost_events[0]
    assert "agents" in tick
    assert "all_idle" in tick


@pytest.mark.asyncio
async def test_broadcaster_emits_world_snapshot():
    bc = EventBroadcaster(mock=True)
    bc.start()

    snapshots = []

    async def collect():
        async for event_type, payload in bc.subscribe():
            if event_type == "world.snapshot":
                snapshots.append(payload)
                if len(snapshots) >= 1:
                    break

    try:
        await asyncio.wait_for(collect(), timeout=5.0)
    except TimeoutError:
        pytest.fail("Broadcaster did not emit a world.snapshot within 5s")
    finally:
        bc.stop()

    assert len(snapshots) >= 1
    assert "cows" in snapshots[0]


@pytest.mark.asyncio
async def test_broadcaster_multiple_subscribers():
    """Multiple subscribers should each receive events independently."""
    bc = EventBroadcaster(mock=True)
    bc.start()

    results_a: list = []
    results_b: list = []

    async def collect_a():
        async for event_type, _payload in bc.subscribe():
            results_a.append(event_type)
            if len(results_a) >= 2:
                break

    async def collect_b():
        async for event_type, _payload in bc.subscribe():
            results_b.append(event_type)
            if len(results_b) >= 2:
                break

    try:
        await asyncio.wait_for(
            asyncio.gather(collect_a(), collect_b()),
            timeout=5.0,
        )
    except TimeoutError:
        pytest.fail("Multiple subscribers timed out")
    finally:
        bc.stop()

    assert len(results_a) >= 2
    assert len(results_b) >= 2


@pytest.mark.asyncio
async def test_broadcaster_backpressure_slow_consumer():
    """A slow consumer should not block the broadcaster."""
    bc = EventBroadcaster(mock=True)
    bc.start()

    # Fast subscriber that collects quickly
    fast_received = []

    async def fast():
        async for event_type, _payload in bc.subscribe():
            fast_received.append(event_type)
            if len(fast_received) >= 5:
                break

    # Slow subscriber that sleeps between reads
    slow_received = []

    async def slow():
        async for event_type, _payload in bc.subscribe():
            await asyncio.sleep(0.5)  # deliberate slow consumer
            slow_received.append(event_type)
            if len(slow_received) >= 2:
                break

    try:
        await asyncio.wait_for(
            asyncio.gather(fast(), slow()),
            timeout=8.0,
        )
    except TimeoutError:
        # Fast subscriber should still have received events even if slow timed out
        pass
    finally:
        bc.stop()

    # Fast subscriber should have received its events regardless
    assert len(fast_received) >= 3


@pytest.mark.asyncio
async def test_broadcaster_no_mock_world_uses_mock_fallback():
    """When world=None and mock=False, snapshot falls back gracefully."""
    bc = EventBroadcaster(mock=False, world=None)
    bc.start()

    snapshots = []

    async def collect():
        async for event_type, payload in bc.subscribe():
            if event_type == "world.snapshot":
                snapshots.append(payload)
                if len(snapshots) >= 1:
                    break

    try:
        await asyncio.wait_for(collect(), timeout=5.0)
    except TimeoutError:
        pytest.fail("Broadcaster (no world) did not emit world.snapshot within 5s")
    finally:
        bc.stop()

    assert len(snapshots) >= 1


# ---------------------------------------------------------------------------
# Phase 02 CRM-05: broadcast_neighbor_alert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_neighbor_alert_fans_out_to_subscribers():
    """broadcast_neighbor_alert must publish 'neighbor.alert' to all SSE subscribers."""
    bc = EventBroadcaster(mock=True)
    bc.start()
    payload = {
        "from_ranch": "ranch_a",
        "to_ranch": "ranch_b",
        "species": "coyote",
        "shared_fence": "fence_west",
        "confidence": 0.91,
        "ts": 1745200000.0,
        "attestation_hash": "sha256:deadbeef",
    }
    received: list = []

    async def collect():
        async for event_type, p in bc.subscribe():
            if event_type == "neighbor.alert":
                received.append(p)
                break

    collector = asyncio.create_task(collect())
    # Let subscriber register before we broadcast.
    await asyncio.sleep(0.1)
    bc.broadcast_neighbor_alert(payload)
    try:
        await asyncio.wait_for(collector, timeout=5.0)
    finally:
        bc.stop()
    assert received == [payload]
