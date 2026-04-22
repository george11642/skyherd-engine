"""Tests for two-Pi-4 fleet topology.

Simulates edge-house and edge-barn publishing to distinct MQTT topic subtrees.
Verifies:
- No cross-talk between nodes (distinct topics, distinct edge_ids).
- Both nodes visible under the wildcard subscription pattern.
- Heartbeat payloads carry the correct edge_id for each node.
"""

from __future__ import annotations

import asyncio

import pytest

from skyherd.edge.camera import MockCamera
from skyherd.edge.detector import RuleDetector
from skyherd.edge.watcher import EdgeWatcher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_edge(edge_id: str, **kwargs) -> EdgeWatcher:
    defaults = {
        "camera": MockCamera(),
        "detector": RuleDetector(),
        "ranch_id": "ranch_a",
        "mqtt_url": "mqtt://localhost:19999",  # unreachable — publish best-effort
        "capture_interval_s": 1.0,
        "heartbeat_interval_s": 0.05,
        "healthz_port": 0,
    }
    defaults.update(kwargs)
    return EdgeWatcher(edge_id=edge_id, **defaults)


# ---------------------------------------------------------------------------
# Topic isolation
# ---------------------------------------------------------------------------


class TestTopicIsolation:
    """Each node publishes to its own topic subtree — no cross-talk."""

    def test_house_and_barn_have_distinct_topics(self) -> None:
        house = _make_edge("edge-house")
        barn = _make_edge("edge-barn")
        assert house._topic != barn._topic

    def test_house_topic_contains_edge_id(self) -> None:
        house = _make_edge("edge-house")
        assert "edge-house" in house._topic

    def test_barn_topic_contains_edge_id(self) -> None:
        barn = _make_edge("edge-barn")
        assert "edge-barn" in barn._topic

    def test_status_topics_are_distinct(self) -> None:
        house = _make_edge("edge-house")
        barn = _make_edge("edge-barn")
        assert house._status_topic != barn._status_topic

    def test_both_topics_under_ranch_wildcard(self) -> None:
        """Both topic paths are rooted at skyherd/{ranch}/ so one
        wildcard subscription captures both nodes."""
        house = _make_edge("edge-house")
        barn = _make_edge("edge-barn")
        prefix = "skyherd/ranch_a/"
        assert house._topic.startswith(prefix)
        assert barn._topic.startswith(prefix)
        assert house._status_topic.startswith(prefix)
        assert barn._status_topic.startswith(prefix)

    def test_edge_status_wildcard_matches_both(self) -> None:
        """Topics match skyherd/+/edge_status/# subscription pattern."""
        house = _make_edge("edge-house")
        barn = _make_edge("edge-barn")
        # Verify the pattern manually: skyherd/{ranch}/edge_status/{edge_id}
        for watcher in (house, barn):
            parts = watcher._status_topic.split("/")
            assert parts[0] == "skyherd"
            assert parts[2] == "edge_status"
            assert len(parts) == 4


# ---------------------------------------------------------------------------
# Payload identity
# ---------------------------------------------------------------------------


class TestPayloadIdentity:
    """Published payloads carry the correct edge_id — no cross-contamination."""

    @pytest.mark.asyncio
    async def test_house_payload_has_house_edge_id(self) -> None:
        house = _make_edge("edge-house")
        payload = await house.run_once()
        assert payload["entity"] == "edge-house"

    @pytest.mark.asyncio
    async def test_barn_payload_has_barn_edge_id(self) -> None:
        barn = _make_edge("edge-barn")
        payload = await barn.run_once()
        assert payload["entity"] == "edge-barn"

    @pytest.mark.asyncio
    async def test_two_nodes_publish_independently(self) -> None:
        """Running both nodes concurrently produces distinct published records."""
        house = _make_edge("edge-house")
        barn = _make_edge("edge-barn")

        house_payload, barn_payload = await asyncio.gather(
            house.run_once(),
            barn.run_once(),
        )

        assert house_payload["entity"] == "edge-house"
        assert barn_payload["entity"] == "edge-barn"
        assert house_payload["entity"] != barn_payload["entity"]

    @pytest.mark.asyncio
    async def test_published_lists_do_not_cross_contaminate(self) -> None:
        """Each watcher's _published list contains only its own messages."""
        house = _make_edge("edge-house")
        barn = _make_edge("edge-barn")

        for _ in range(2):
            await house.run_once()
            await barn.run_once()

        assert all(p["entity"] == "edge-house" for p in house._published)
        assert all(p["entity"] == "edge-barn" for p in barn._published)
        assert len(house._published) == 2
        assert len(barn._published) == 2


# ---------------------------------------------------------------------------
# Heartbeat identity
# ---------------------------------------------------------------------------


class TestHeartbeatIdentity:
    """Heartbeat payloads carry the correct edge_id for each node."""

    def test_house_heartbeat_has_house_id(self) -> None:
        house = _make_edge("edge-house")
        hb = house.heartbeat_payload()
        assert hb["edge_id"] == "edge-house"

    def test_barn_heartbeat_has_barn_id(self) -> None:
        barn = _make_edge("edge-barn")
        hb = barn.heartbeat_payload()
        assert hb["edge_id"] == "edge-barn"

    @pytest.mark.asyncio
    async def test_concurrent_heartbeat_loops_are_independent(self) -> None:
        """Two nodes running heartbeat loops simultaneously produce
        correctly-labelled payloads with no cross-contamination."""
        house = _make_edge("edge-house", heartbeat_interval_s=0.04)
        barn = _make_edge("edge-barn", heartbeat_interval_s=0.04)
        house._running = True
        barn._running = True

        async def _stop(watcher: EdgeWatcher, delay: float) -> None:
            await asyncio.sleep(delay)
            watcher._running = False

        await asyncio.gather(
            house._heartbeat_loop(),
            barn._heartbeat_loop(),
            _stop(house, 0.15),
            _stop(barn, 0.15),
        )

        assert len(house._heartbeats) >= 1
        assert len(barn._heartbeats) >= 1
        assert all(hb["edge_id"] == "edge-house" for hb in house._heartbeats)
        assert all(hb["edge_id"] == "edge-barn" for hb in barn._heartbeats)


# ---------------------------------------------------------------------------
# MQTT subscription pattern coverage
# ---------------------------------------------------------------------------


class TestMqttSubscriptionCoverage:
    """Verify that both trough_cam and edge_status topics are reachable
    under the wildcard patterns documented in HARDWARE_PI_FLEET.md."""

    def _matches_wildcard(self, topic: str, pattern: str) -> bool:
        """Minimal MQTT single-level (+) and multi-level (#) wildcard match."""
        t_parts = topic.split("/")
        p_parts = pattern.split("/")
        if p_parts[-1] == "#":
            p_parts = p_parts[:-1]
            if len(t_parts) < len(p_parts):
                return False
            t_parts = t_parts[: len(p_parts)]
        if len(t_parts) != len(p_parts):
            return False
        return all(p == "+" or p == t for p, t in zip(p_parts, t_parts))

    def test_trough_cam_topic_matches_ranch_wildcard(self) -> None:
        for edge_id in ("edge-house", "edge-barn"):
            watcher = _make_edge(edge_id)
            assert self._matches_wildcard(watcher._topic, "skyherd/ranch_a/#")

    def test_edge_status_topic_matches_ranch_wildcard(self) -> None:
        for edge_id in ("edge-house", "edge-barn"):
            watcher = _make_edge(edge_id)
            assert self._matches_wildcard(watcher._status_topic, "skyherd/ranch_a/#")

    def test_edge_status_matches_plus_wildcard(self) -> None:
        """skyherd/+/edge_status/# matches both nodes."""
        for edge_id in ("edge-house", "edge-barn"):
            watcher = _make_edge(edge_id)
            assert self._matches_wildcard(watcher._status_topic, "skyherd/+/edge_status/#")
