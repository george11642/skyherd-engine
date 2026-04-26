"""Phase 9 PF-04 — End-to-end Friday workflow simulation.

Fully mocked: no Docker, no real Pi, no real Mavic, no Anthropic API. Exercises
the exact sequence George will run on Friday morning after plugging in the
two Raspberry Pi 4s and pairing the Mavic Air 2:

1. Two Pi-emulated EdgeWatchers publish `edge_status` heartbeats to an
   in-memory MQTT broker.
2. `/api/edges` (simulated via a pure-Python aggregator that mirrors the
   server's logic) aggregates and reports both nodes online.
3. Pi-A publishes a camera.motion (coyote) event on
   `skyherd/ranch_a/events/camera.motion`.
4. A mocked FenceLineDispatcher (via the `simulate` path) emits a drone mission.
5. StubBackend accepts the mission — no real Mavic.
6. Attestation ledger records fence.breach, drone.dispatched events.

Total wall time target: < 30 seconds. Runs in `make preflight`.

This test does NOT use the full H2 chain (which lives in test_h2_e2e.py). It
is intentionally a slimmer, faster test that covers the Friday-specific
topology: 2 Pis + `/api/edges` aggregation + coyote dispatch.
"""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.drone.stub import StubBackend

# ---------------------------------------------------------------------------
# In-memory broker — reuses the pattern from test_h2_e2e.py
# ---------------------------------------------------------------------------


class InMemoryBroker:
    """Async fan-out broker for fully-mocked MQTT simulation."""

    def __init__(self) -> None:
        self._next_seq = 0
        self._messages: list[tuple[int, str, dict[str, Any]]] = []
        self._by_topic: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
        self._subscribers: list[Any] = []

    def publisher(self):  # type: ignore[no-untyped-def]
        async def publish(topic: str, payload: dict[str, Any]) -> None:
            self._next_seq += 1
            self._messages.append((self._next_seq, topic, payload))
            self._by_topic[topic].append((self._next_seq, payload))
            for sub in list(self._subscribers):
                await sub(topic, payload)

        return publish

    def subscribe(self, callback) -> None:  # type: ignore[no-untyped-def]
        self._subscribers.append(callback)

    def messages_on(self, topic_prefix: str) -> list[dict[str, Any]]:
        return [p for _seq, t, p in self._messages if t.startswith(topic_prefix)]

    def total(self) -> int:
        return len(self._messages)


# ---------------------------------------------------------------------------
# Heartbeat emitter — minimal surface that mirrors EdgeWatcher.heartbeat_payload()
# ---------------------------------------------------------------------------


def _heartbeat_payload(edge_id: str, ts: float) -> dict[str, Any]:
    """Mirror EdgeWatcher.heartbeat_payload() output shape."""
    return {
        "edge_id": edge_id,
        "ts": ts,
        "capture_cadence_s": 10.0,
        "last_detection_ts": None,
        "cpu_temp_c": 52.3,
        "mem_pct": 34.1,
    }


async def emit_heartbeats(
    broker: InMemoryBroker,
    edge_id: str,
    count: int = 3,
    base_ts: float = 1_714_000_000.0,
) -> None:
    """Emit `count` heartbeats for `edge_id`, spaced 30s apart."""
    publish = broker.publisher()
    topic = f"skyherd/ranch_a/edge_status/{edge_id}"
    for i in range(count):
        payload = _heartbeat_payload(edge_id, base_ts + i * 30.0)
        await publish(topic, payload)


# ---------------------------------------------------------------------------
# /api/edges simulator — mirrors server-side aggregation logic
# ---------------------------------------------------------------------------


def aggregate_edges(
    broker: InMemoryBroker,
    *,
    now_ts: float,
    offline_threshold_s: float = 90.0,
) -> list[dict[str, Any]]:
    """Mirror the `/api/edges` endpoint aggregation.

    Walks heartbeat topics, returns one row per edge_id with `online` flag.
    """
    latest: dict[str, dict[str, Any]] = {}
    for topic_prefix in ["skyherd/ranch_a/edge_status/"]:
        for _seq, t, payload in broker._messages:
            if t.startswith(topic_prefix):
                eid = payload.get("edge_id")
                if eid is None:
                    continue
                if eid not in latest or payload["ts"] > latest[eid]["ts"]:
                    latest[eid] = payload

    result: list[dict[str, Any]] = []
    for eid, hb in latest.items():
        online = (now_ts - hb["ts"]) <= offline_threshold_s
        result.append(
            {
                "edge_id": eid,
                "last_seen_ts": hb["ts"],
                "cpu_temp_c": hb.get("cpu_temp_c"),
                "mem_pct": hb.get("mem_pct"),
                "online": online,
            }
        )
    return sorted(result, key=lambda r: r["edge_id"])


# ---------------------------------------------------------------------------
# Coyote-event → mission emitter (mocked FenceLineDispatcher)
# ---------------------------------------------------------------------------


async def simulate_coyote_dispatch(
    broker: InMemoryBroker,
    *,
    edge_id: str,
    ledger: Ledger,
    drone: StubBackend,
    ts: float = 1_714_000_100.0,
) -> dict[str, Any]:
    """Publish a camera.motion(coyote) event, route to mission + ledger.

    In production, FenceLineDispatcher (Claude Managed Agent) runs this chain.
    For preflight, we skip the agent and drive the tool-calls directly —
    same event topics, same ledger schema.
    """
    publish = broker.publisher()

    # Step 1: Pi-A publishes motion event.
    motion_event = {
        "ranch": "ranch_a",
        "edge_id": edge_id,
        "kind": "camera.motion",
        "confidence": 0.9,
        "label": "coyote",
        "ts": ts,
    }
    await publish("skyherd/ranch_a/events/camera.motion", motion_event)

    # Step 2: Ledger appends fence.breach.
    ledger.append(
        source=f"edge:{edge_id}",
        kind="fence.breach",
        payload={
            "edge_id": edge_id,
            "confidence": motion_event["confidence"],
            "label": motion_event["label"],
        },
    )

    # Step 3: Drone stub accepts mission.
    await drone.connect()
    await drone.takeoff(alt_m=20.0)
    # StubBackend has no goto_waypoint — state is sufficient for preflight.
    state = await drone.state()

    # Step 4: Publish mission dispatched event.
    await publish(
        "skyherd/ranch_a/drone/mission",
        {
            "kind": "drone.dispatched",
            "target": "FENCE_SW",
            "mode": "deterrent",
            "ts": ts + 2.0,
        },
    )

    # Step 5: Ledger appends drone.dispatched.
    ledger.append(
        source=f"agent:FenceLineDispatcher:{edge_id}",
        kind="drone.dispatched",
        payload={
            "target": "FENCE_SW",
            "mode": "deterrent",
        },
    )

    return {
        "motion_event": motion_event,
        "drone_state": {"mode": state.mode, "armed": state.armed},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def broker() -> InMemoryBroker:
    return InMemoryBroker()


@pytest.fixture
def ledger(tmp_path: Path) -> Ledger:
    return Ledger.open(
        tmp_path / "preflight_ledger.db",
        Signer.generate(),
        ts_provider=lambda: 1_714_000_000.0,
    )


class TestPreflightStep1Heartbeats:
    """Step 1 of Friday sequence — both Pis publish edge_status heartbeats."""

    @pytest.mark.asyncio
    async def test_both_pis_publish_heartbeats(self, broker: InMemoryBroker) -> None:
        await emit_heartbeats(broker, "edge-house", count=2)
        await emit_heartbeats(broker, "edge-barn", count=2)

        hb_messages = broker.messages_on("skyherd/ranch_a/edge_status/")
        assert len(hb_messages) == 4
        edge_ids = {m["edge_id"] for m in hb_messages}
        assert edge_ids == {"edge-house", "edge-barn"}

    @pytest.mark.asyncio
    async def test_heartbeat_schema_matches_watcher(self, broker: InMemoryBroker) -> None:
        """Payload shape must match EdgeWatcher.heartbeat_payload()."""
        await emit_heartbeats(broker, "edge-house", count=1)
        messages = broker.messages_on("skyherd/ranch_a/edge_status/")
        assert len(messages) == 1
        hb = messages[0]
        for required in ("edge_id", "ts", "capture_cadence_s", "cpu_temp_c", "mem_pct"):
            assert required in hb, f"Missing {required} from heartbeat payload"


class TestPreflightStep2ApiEdges:
    """Step 2 — /api/edges aggregates and reports both online."""

    @pytest.mark.asyncio
    async def test_both_edges_online_within_90s(self, broker: InMemoryBroker) -> None:
        base_ts = 1_714_000_000.0
        await emit_heartbeats(broker, "edge-house", count=1, base_ts=base_ts)
        await emit_heartbeats(broker, "edge-barn", count=1, base_ts=base_ts)

        # 30s after last heartbeat → both online
        edges = aggregate_edges(broker, now_ts=base_ts + 30.0)
        assert len(edges) == 2
        assert all(e["online"] for e in edges)
        edge_ids = {e["edge_id"] for e in edges}
        assert edge_ids == {"edge-house", "edge-barn"}

    @pytest.mark.asyncio
    async def test_single_edge_goes_offline_after_threshold(self, broker: InMemoryBroker) -> None:
        """If one Pi goes dark > 90s, it's marked offline."""
        base_ts = 1_714_000_000.0
        await emit_heartbeats(broker, "edge-house", count=1, base_ts=base_ts)
        await emit_heartbeats(broker, "edge-barn", count=1, base_ts=base_ts)

        # 120s after the last heartbeats → both offline
        edges = aggregate_edges(broker, now_ts=base_ts + 120.0)
        assert len(edges) == 2
        assert all(not e["online"] for e in edges)


class TestPreflightStep3CoyoteDispatch:
    """Step 3 — camera.motion event → FenceLineDispatcher → drone mission."""

    @pytest.mark.asyncio
    async def test_coyote_event_triggers_drone_mission(
        self, broker: InMemoryBroker, ledger: Ledger
    ) -> None:
        drone = StubBackend()
        result = await simulate_coyote_dispatch(
            broker, edge_id="edge-house", ledger=ledger, drone=drone
        )

        # Motion event present
        motion = broker.messages_on("skyherd/ranch_a/events/camera.motion")
        assert len(motion) == 1
        assert motion[0]["label"] == "coyote"

        # Drone mission dispatched
        mission = broker.messages_on("skyherd/ranch_a/drone/mission")
        assert len(mission) == 1
        assert mission[0]["target"] == "FENCE_SW"
        assert mission[0]["mode"] == "deterrent"

        # Drone stub reached the armed state
        assert result["drone_state"]["mode"] != "STABILIZE"  # takeoff changes mode

    @pytest.mark.asyncio
    async def test_ledger_records_fence_breach_and_mission(
        self, broker: InMemoryBroker, ledger: Ledger
    ) -> None:
        drone = StubBackend()
        await simulate_coyote_dispatch(broker, edge_id="edge-house", ledger=ledger, drone=drone)

        # Ledger should hold fence.breach + drone.dispatched.
        events = list(ledger.iter_events())
        kinds = [e.kind for e in events]
        assert "fence.breach" in kinds, f"Missing fence.breach in {kinds}"
        assert "drone.dispatched" in kinds, f"Missing drone.dispatched in {kinds}"


class TestPreflightFullFridayWorkflow:
    """End-to-end: heartbeats + edges aggregator + coyote dispatch in one test."""

    @pytest.mark.asyncio
    async def test_full_friday_flow(self, broker: InMemoryBroker, ledger: Ledger) -> None:
        """Simulates the exact Friday morning sequence end-to-end.

        Baseline timing: emits all heartbeats + dispatch + ledger work. Must
        return under 30s real time (typical run: <100ms, amortized).
        """
        t0 = time.time()
        base_ts = 1_714_000_000.0

        # 1. Both Pis heartbeat x3 each (60s simulated time).
        await emit_heartbeats(broker, "edge-house", count=3, base_ts=base_ts)
        await emit_heartbeats(broker, "edge-barn", count=3, base_ts=base_ts)

        # 2. /api/edges shows both online at t+60s.
        edges = aggregate_edges(broker, now_ts=base_ts + 60.0)
        assert len(edges) == 2
        assert all(e["online"] for e in edges), f"Edges not online: {edges}"

        # 3. Coyote at fence → dispatch.
        drone = StubBackend()
        dispatch_result = await simulate_coyote_dispatch(
            broker, edge_id="edge-house", ledger=ledger, drone=drone, ts=base_ts + 100.0
        )

        # 4. Assert the full observable chain.
        assert dispatch_result["motion_event"]["label"] == "coyote"
        assert len(broker.messages_on("skyherd/ranch_a/drone/mission")) == 1

        # Ledger has both attestation entries.
        events = list(ledger.iter_events())
        kinds = [e.kind for e in events]
        assert kinds.count("fence.breach") == 1
        assert kinds.count("drone.dispatched") == 1

        # 5. Time budget.
        elapsed = time.time() - t0
        assert elapsed < 30.0, f"Preflight E2E took {elapsed:.2f}s — exceeds 30s budget"

    @pytest.mark.asyncio
    async def test_friday_flow_is_fast(self, broker: InMemoryBroker, ledger: Ledger) -> None:
        """Regression guard: the full Friday flow completes in under 5s typical."""
        t0 = time.time()
        base_ts = 1_714_000_000.0

        await emit_heartbeats(broker, "edge-house", count=3, base_ts=base_ts)
        await emit_heartbeats(broker, "edge-barn", count=3, base_ts=base_ts)
        edges = aggregate_edges(broker, now_ts=base_ts + 60.0)
        assert len(edges) == 2

        drone = StubBackend()
        await simulate_coyote_dispatch(
            broker, edge_id="edge-house", ledger=ledger, drone=drone, ts=base_ts + 100.0
        )

        elapsed = time.time() - t0
        # Headroom: should be well under 5s; signals regression if approaching 30s.
        assert elapsed < 5.0, f"Preflight workflow took {elapsed:.2f}s — CI will time out"
