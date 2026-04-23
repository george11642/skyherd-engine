"""Unit tests for the Cross-Ranch Mesh (NeighborBroadcaster + NeighborListener).

All tests run WITHOUT an Anthropic API key — the _simulate_handler path is used
throughout.  No real MQTT broker is required either; callbacks are injected.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from skyherd.agents.fenceline_dispatcher import FENCELINE_DISPATCHER_SPEC
from skyherd.agents.mesh import AgentMesh
from skyherd.agents.mesh_neighbor import (
    CrossRanchMesh,
    NeighborBroadcaster,
    NeighborListener,
    _attestation_hash,
)
from skyherd.agents.session import SessionManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_manager() -> tuple[SessionManager, str]:
    """Return a SessionManager with one FenceLineDispatcher session."""
    sm = SessionManager()
    session = sm.create_session(FENCELINE_DISPATCHER_SPEC)
    return sm, session.id


# ---------------------------------------------------------------------------
# NeighborBroadcaster unit tests
# ---------------------------------------------------------------------------


class TestNeighborBroadcaster:
    async def test_broadcast_fires_on_shared_fence(self, monkeypatch):
        """Broadcaster fires when fence_id is in shared_fence_ids."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        published: list[tuple[str, dict[str, Any]]] = []

        async def fake_publish(topic: str, payload: dict[str, Any]) -> None:
            published.append((topic, payload))

        broadcaster = NeighborBroadcaster(
            from_ranch="ranch_a",
            shared_fence_ids={"fence_east"},
            neighbor_map={"fence_east": "ranch_b"},
            publish_callback=fake_publish,
        )

        decision = {"fence_id": "fence_east", "species": "coyote", "confidence": 0.91}
        fired = await broadcaster.on_fenceline_decision(decision)

        assert fired is True
        assert len(published) == 1
        topic, payload = published[0]
        assert "ranch_a" in topic
        assert "ranch_b" in topic
        assert "predator_confirmed" in topic

    async def test_broadcast_skips_non_shared_fence(self, monkeypatch):
        """Broadcaster is silent for fences not in shared_fence_ids."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        published: list = []

        async def fake_publish(topic: str, payload: dict) -> None:
            published.append((topic, payload))

        broadcaster = NeighborBroadcaster(
            from_ranch="ranch_a",
            shared_fence_ids={"fence_east"},
            neighbor_map={"fence_east": "ranch_b"},
            publish_callback=fake_publish,
        )

        # Internal fence — should NOT broadcast
        decision = {"fence_id": "fence_internal_v", "species": "coyote", "confidence": 0.85}
        fired = await broadcaster.on_fenceline_decision(decision)

        assert fired is False
        assert len(published) == 0

    async def test_broadcast_uses_segment_fallback(self, monkeypatch):
        """Broadcaster falls back to 'segment' key if 'fence_id' is absent."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        published: list = []

        async def fake_publish(topic: str, payload: dict) -> None:
            published.append((topic, payload))

        broadcaster = NeighborBroadcaster(
            from_ranch="ranch_a",
            shared_fence_ids={"fence_east"},
            neighbor_map={"fence_east": "ranch_b"},
            publish_callback=fake_publish,
        )

        decision = {"segment": "fence_east", "species": "coyote", "confidence": 0.91}
        fired = await broadcaster.on_fenceline_decision(decision)

        assert fired is True

    async def test_payload_contains_attestation_hash(self, monkeypatch):
        """Published payload includes an attestation_hash field."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        published: list = []

        async def fake_publish(topic: str, payload: dict) -> None:
            published.append(payload)

        broadcaster = NeighborBroadcaster(
            from_ranch="ranch_a",
            shared_fence_ids={"fence_east"},
            neighbor_map={"fence_east": "ranch_b"},
            publish_callback=fake_publish,
        )

        decision = {"fence_id": "fence_east", "species": "coyote", "confidence": 0.91}
        await broadcaster.on_fenceline_decision(decision)

        assert len(published) == 1
        payload = published[0]
        assert "attestation_hash" in payload
        assert payload["attestation_hash"].startswith("sha256:")

    async def test_no_publish_callback_does_not_raise(self, monkeypatch):
        """Broadcaster with no publish_callback logs and returns True."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        broadcaster = NeighborBroadcaster(
            from_ranch="ranch_a",
            shared_fence_ids={"fence_east"},
            neighbor_map={"fence_east": "ranch_b"},
            publish_callback=None,
        )
        decision = {"fence_id": "fence_east", "species": "coyote", "confidence": 0.91}
        fired = await broadcaster.on_fenceline_decision(decision)
        assert fired is True

    async def test_published_count_increments(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        published_count = 0

        async def fake_publish(topic: str, payload: dict) -> None:
            nonlocal published_count
            published_count += 1

        broadcaster = NeighborBroadcaster(
            from_ranch="ranch_a",
            shared_fence_ids={"fence_east"},
            neighbor_map={"fence_east": "ranch_b"},
            publish_callback=fake_publish,
        )

        decision = {"fence_id": "fence_east", "species": "coyote", "confidence": 0.91}
        await broadcaster.on_fenceline_decision(decision)
        await broadcaster.on_fenceline_decision(decision)

        assert broadcaster._published_count == 2


# ---------------------------------------------------------------------------
# NeighborListener unit tests
# ---------------------------------------------------------------------------


class TestNeighborListener:
    def _make_listener(self) -> tuple[NeighborListener, SessionManager, str]:
        sm, fid = _make_session_manager()
        wake_bus: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        listener = NeighborListener(
            this_ranch="ranch_b",
            session_manager=sm,
            fenceline_session_id=fid,
            wake_bus=wake_bus,
        )
        return listener, sm, fid

    async def test_forwards_valid_alert(self, monkeypatch):
        """Listener forwards a well-formed neighbor alert onto the wake bus."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        listener, _sm, _fid = self._make_listener()

        payload = {
            "from_ranch": "ranch_a",
            "to_ranch": "ranch_b",
            "event_kind": "predator_confirmed",
            "species": "coyote",
            "confidence": 0.91,
            "shared_fence": "fence_east",
            "ts": time.time(),
            "attestation_hash": "sha256:abc123",
        }
        forwarded = await listener.on_neighbor_event(
            "skyherd/neighbor/ranch_a/ranch_b/predator_confirmed", payload
        )

        assert forwarded is True
        assert listener._wake_bus is not None
        assert not listener._wake_bus.empty()

        wake_event = listener._wake_bus.get_nowait()
        assert wake_event["type"] == "neighbor_alert"
        assert wake_event["response_mode"] == "pre_position"
        assert wake_event["from_ranch"] == "ranch_a"

    async def test_deduplicates_repeat_alert(self, monkeypatch):
        """Listener suppresses duplicate (from_ranch, shared_fence) within TTL."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        listener, _sm, _fid = self._make_listener()

        payload = {
            "from_ranch": "ranch_a",
            "to_ranch": "ranch_b",
            "event_kind": "predator_confirmed",
            "species": "coyote",
            "confidence": 0.91,
            "shared_fence": "fence_east",
            "ts": time.time(),
            "attestation_hash": "sha256:abc123",
        }
        topic = "skyherd/neighbor/ranch_a/ranch_b/predator_confirmed"

        first = await listener.on_neighbor_event(topic, payload)
        second = await listener.on_neighbor_event(topic, payload)

        assert first is True
        assert second is False  # deduped
        assert listener._deduped_count == 1

    async def test_dedup_expires_after_ttl(self, monkeypatch):
        """After TTL expires, the same alert is forwarded again."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        listener, _sm, _fid = self._make_listener()

        payload = {
            "from_ranch": "ranch_a",
            "to_ranch": "ranch_b",
            "species": "coyote",
            "shared_fence": "fence_east",
            "ts": time.time(),
            "attestation_hash": "sha256:abc",
        }
        topic = "skyherd/neighbor/ranch_a/ranch_b/predator_confirmed"

        await listener.on_neighbor_event(topic, payload)

        # Manually expire the dedup entry
        listener._dedup.clear()

        second = await listener.on_neighbor_event(topic, payload)
        assert second is True

    async def test_ignores_alert_addressed_to_other_ranch(self, monkeypatch):
        """Listener ignores alerts not addressed to its ranch."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        listener, _sm, _fid = self._make_listener()

        payload = {
            "from_ranch": "ranch_a",
            "to_ranch": "ranch_c",  # not ranch_b
            "species": "coyote",
            "shared_fence": "fence_east",
            "ts": time.time(),
            "attestation_hash": "sha256:xyz",
        }
        forwarded = await listener.on_neighbor_event(
            "skyherd/neighbor/ranch_a/ranch_c/predator_confirmed", payload
        )
        assert forwarded is False

    async def test_received_count_increments(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        listener, _sm, _fid = self._make_listener()

        payload = {
            "from_ranch": "ranch_a",
            "to_ranch": "ranch_b",
            "species": "coyote",
            "shared_fence": "fence_east",
            "ts": time.time(),
            "attestation_hash": "sha256:abc",
        }
        topic = "skyherd/neighbor/ranch_a/ranch_b/predator_confirmed"
        await listener.on_neighbor_event(topic, payload)
        await listener.on_neighbor_event(topic, payload)  # will be deduped

        assert listener._received_count == 2


# ---------------------------------------------------------------------------
# CrossRanchMesh integration tests
# ---------------------------------------------------------------------------


class TestCrossRanchMesh:
    async def test_start_creates_broadcasters_and_listeners(self, monkeypatch):
        """CrossRanchMesh start() wires a broadcaster and listener per ranch."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh_a = AgentMesh()
        mesh_b = AgentMesh()
        cross = CrossRanchMesh(
            meshes={"ranch_a": mesh_a, "ranch_b": mesh_b},
            neighbor_config={
                "ranch_a": {"fence_east": "ranch_b"},
                "ranch_b": {"fence_west": "ranch_a"},
            },
        )
        await cross.start()
        try:
            assert "ranch_a" in cross._broadcasters
            assert "ranch_b" in cross._broadcasters
            assert "ranch_a" in cross._listeners
            assert "ranch_b" in cross._listeners
        finally:
            await cross.stop()

    async def test_simulate_coyote_broadcasts_and_wakes_ranch_b(self, monkeypatch):
        """simulate_coyote_at_shared_fence drives the full cross-ranch cascade."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh_a = AgentMesh()
        mesh_b = AgentMesh()
        cross = CrossRanchMesh(
            meshes={"ranch_a": mesh_a, "ranch_b": mesh_b},
            neighbor_config={
                "ranch_a": {"fence_east": "ranch_b"},
                "ranch_b": {"fence_west": "ranch_a"},
            },
        )
        await cross.start()
        try:
            result = await cross.simulate_coyote_at_shared_fence(
                from_ranch="ranch_a",
                shared_fence_id="fence_east",
                species="coyote",
                confidence=0.91,
            )
            assert result["neighbor_broadcast"] is True
            assert result["ranch_b_woken"] is True
            assert result["ranch_b_pre_positioned"] is True
            assert len(result["ranch_a_tool_calls"]) > 0
            assert len(result["ranch_b_tool_calls"]) > 0
            assert len(result["attestation_hashes"]) >= 2
        finally:
            await cross.stop()

    async def test_ranch_b_does_not_page_rancher(self, monkeypatch):
        """Ranch_b pre-position response must NOT call page_rancher (silent handoff)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh_a = AgentMesh()
        mesh_b = AgentMesh()
        cross = CrossRanchMesh(
            meshes={"ranch_a": mesh_a, "ranch_b": mesh_b},
            neighbor_config={
                "ranch_a": {"fence_east": "ranch_b"},
                "ranch_b": {"fence_west": "ranch_a"},
            },
        )
        await cross.start()
        try:
            result = await cross.simulate_coyote_at_shared_fence(
                from_ranch="ranch_a",
                shared_fence_id="fence_east",
            )
            ranch_b_calls = result["ranch_b_tool_calls"]
            rancher_pages = [c for c in ranch_b_calls if c.get("tool") == "page_rancher"]
            assert len(rancher_pages) == 0, (
                f"Ranch_b should NOT page rancher on neighbor alert. Got: {rancher_pages}"
            )
        finally:
            await cross.stop()

    async def test_ranch_b_launches_drone(self, monkeypatch):
        """Ranch_b pre-position response must call launch_drone."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh_a = AgentMesh()
        mesh_b = AgentMesh()
        cross = CrossRanchMesh(
            meshes={"ranch_a": mesh_a, "ranch_b": mesh_b},
            neighbor_config={
                "ranch_a": {"fence_east": "ranch_b"},
                "ranch_b": {"fence_west": "ranch_a"},
            },
        )
        await cross.start()
        try:
            result = await cross.simulate_coyote_at_shared_fence(
                from_ranch="ranch_a",
                shared_fence_id="fence_east",
            )
            ranch_b_tools = {c.get("tool") for c in result["ranch_b_tool_calls"]}
            assert "launch_drone" in ranch_b_tools, (
                f"Ranch_b expected launch_drone for pre-position. Got: {ranch_b_tools}"
            )
        finally:
            await cross.stop()

    async def test_non_shared_fence_does_not_trigger_ranch_b(self, monkeypatch):
        """A breach on an internal fence must NOT trigger ranch_b."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh_a = AgentMesh()
        mesh_b = AgentMesh()
        cross = CrossRanchMesh(
            meshes={"ranch_a": mesh_a, "ranch_b": mesh_b},
            neighbor_config={
                "ranch_a": {"fence_east": "ranch_b"},
                "ranch_b": {"fence_west": "ranch_a"},
            },
        )
        await cross.start()
        try:
            # Use an internal fence — NOT in the shared set
            result = await cross.simulate_coyote_at_shared_fence(
                from_ranch="ranch_a",
                shared_fence_id="fence_internal_v",  # not shared
            )
            assert result["neighbor_broadcast"] is False
            assert result["ranch_b_woken"] is False
        finally:
            await cross.stop()


# ---------------------------------------------------------------------------
# Attestation hash helper
# ---------------------------------------------------------------------------


class TestAttestationHash:
    def test_deterministic(self):
        payload = {"a": 1, "b": "foo"}
        assert _attestation_hash(payload) == _attestation_hash(payload)

    def test_different_payloads_give_different_hashes(self):
        assert _attestation_hash({"a": 1}) != _attestation_hash({"a": 2})

    def test_hash_starts_with_sha256(self):
        h = _attestation_hash({"x": "y"})
        assert h.startswith("sha256:")


# ---------------------------------------------------------------------------
# Phase 02 CRM-04: recent_events ring buffer on broadcaster + listener
# ---------------------------------------------------------------------------


class TestRecentEventsRingBuffer:
    async def test_broadcaster_records_recent_outbound_event(self, monkeypatch):
        """After on_fenceline_decision fires, broadcaster.recent_events has 1 outbound entry."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        async def fake_publish(topic: str, payload: dict) -> None:
            return None

        broadcaster = NeighborBroadcaster(
            from_ranch="ranch_a",
            shared_fence_ids={"fence_east"},
            neighbor_map={"fence_east": "ranch_b"},
            publish_callback=fake_publish,
        )
        await broadcaster.on_fenceline_decision(
            {"fence_id": "fence_east", "species": "coyote", "confidence": 0.91}
        )
        assert len(broadcaster.recent_events) == 1
        entry = broadcaster.recent_events[0]
        assert entry["direction"] == "outbound"
        assert entry["from_ranch"] == "ranch_a"
        assert entry["to_ranch"] == "ranch_b"
        assert entry["shared_fence"] == "fence_east"
        assert entry["species"] == "coyote"

    async def test_broadcaster_skips_non_shared_does_not_record(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        broadcaster = NeighborBroadcaster(
            from_ranch="ranch_a",
            shared_fence_ids={"fence_east"},
            neighbor_map={"fence_east": "ranch_b"},
            publish_callback=None,
        )
        await broadcaster.on_fenceline_decision(
            {"fence_id": "fence_internal_v", "species": "coyote", "confidence": 0.91}
        )
        assert broadcaster.recent_events == []

    async def test_listener_records_recent_inbound_event(self, monkeypatch):
        """After on_neighbor_event fires, listener.recent_events has 1 inbound entry."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        sm, fid = _make_session_manager()
        listener = NeighborListener(
            this_ranch="ranch_b",
            session_manager=sm,
            fenceline_session_id=fid,
        )
        topic = "skyherd/neighbor/ranch_a/ranch_b/predator_confirmed"
        payload = {
            "from_ranch": "ranch_a",
            "to_ranch": "ranch_b",
            "species": "coyote",
            "confidence": 0.91,
            "shared_fence": "fence_west",
            "ts": 1745200000.0,
            "attestation_hash": "sha256:deadbeef",
        }
        forwarded = await listener.on_neighbor_event(topic, payload)
        assert forwarded is True
        assert len(listener.recent_events) == 1
        entry = listener.recent_events[0]
        assert entry["direction"] == "inbound"
        assert entry["from_ranch"] == "ranch_a"
        assert entry["to_ranch"] == "ranch_b"
        assert entry["shared_fence"] == "fence_west"

    async def test_listener_deduped_events_not_recorded_twice(self, monkeypatch):
        """Deduped inbound events (same from_ranch + shared_fence within TTL)
        should only record ONCE in recent_events."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        sm, fid = _make_session_manager()
        listener = NeighborListener(
            this_ranch="ranch_b",
            session_manager=sm,
            fenceline_session_id=fid,
        )
        topic = "skyherd/neighbor/ranch_a/ranch_b/predator_confirmed"
        payload = {
            "from_ranch": "ranch_a",
            "to_ranch": "ranch_b",
            "species": "coyote",
            "confidence": 0.91,
            "shared_fence": "fence_west",
            "ts": time.time(),
            "attestation_hash": "sha256:deadbeef",
        }
        await listener.on_neighbor_event(topic, payload)
        await listener.on_neighbor_event(topic, payload)  # dedup
        assert len(listener.recent_events) == 1

    async def test_cross_ranch_mesh_recent_events_combines_in_out(self, monkeypatch):
        """CrossRanchMesh.recent_events() returns union (inbound + outbound) sorted by ts desc."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mesh_a = AgentMesh()
        mesh_b = AgentMesh()
        cross = CrossRanchMesh(
            meshes={"ranch_a": mesh_a, "ranch_b": mesh_b},
            neighbor_config={
                "ranch_a": {"fence_east": "ranch_b"},
                "ranch_b": {"fence_west": "ranch_a"},
            },
        )
        await cross.start()
        try:
            await cross.simulate_coyote_at_shared_fence(
                from_ranch="ranch_a",
                shared_fence_id="fence_east",
            )
            events = cross.recent_events()
            directions = {e["direction"] for e in events}
            assert "outbound" in directions
            assert "inbound" in directions
            # Should be sorted by ts desc — verify non-increasing
            ts_list = [float(e["ts"]) for e in events]
            assert ts_list == sorted(ts_list, reverse=True)
        finally:
            await cross.stop()
