"""Unit tests for :class:`skyherd.edge.pi_to_mission.PiToMissionBridge`.

Covers topic filtering, dispatch through the FenceLineDispatcher simulation
path, tool-call execution against a StubBackend, attestation chain integrity,
side-channel MQTT publishes, and determinism across replays.  All tests are
offline — no Docker, no MAVSDK, no Anthropic API key.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

import pytest

import skyherd.drone.stub as stub_module
from skyherd.drone.stub import StubBackend
from skyherd.edge.coyote_harness import CoyoteHarness
from skyherd.edge.pi_to_mission import PiToMissionBridge, verify_chain

# ---------------------------------------------------------------------------
# In-memory broker fixture (local copy — decoupled from tests/hardware)
# ---------------------------------------------------------------------------


class InMemoryBroker:
    """Minimal pub/sub router for tests (sequence-numbered)."""

    def __init__(self) -> None:
        self._next_seq = 0
        self._messages: list[tuple[int, str, dict[str, Any]]] = []
        self._by_topic: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)

    def publisher(self):  # type: ignore[no-untyped-def]
        async def publish(topic: str, raw: bytes) -> None:
            payload = json.loads(raw.decode())
            self._next_seq += 1
            self._messages.append((self._next_seq, topic, payload))
            self._by_topic[topic].append((self._next_seq, payload))

        return publish

    def messages_on(self, topic_prefix: str) -> list[dict[str, Any]]:
        return [p for _seq, t, p in self._messages if t.startswith(topic_prefix)]

    def all_topics(self) -> set[str]:
        return set(self._by_topic.keys())

    def total(self) -> int:
        return len(self._messages)


def _fixed_ts() -> float:
    return 1_714_000_000.0


# ---------------------------------------------------------------------------
# Canonical payloads
# ---------------------------------------------------------------------------


def _fence_breach_payload() -> dict[str, Any]:
    return {
        "kind": "fence.breach",
        "ranch": "ranch_a",
        "segment": "sw_fence",
        "lat": 34.123,
        "lon": -106.456,
    }


def _thermal_hit_payload() -> dict[str, Any]:
    return {
        "kind": "predator.thermal_hit",
        "ranch": "ranch_a",
        "entity": "coyote_cam",
        "lat": 34.125,
        "lon": -106.458,
        "species": "coyote",
        "thermal_signature": 0.91,
    }


def _thermal_reading_payload() -> dict[str, Any]:
    return {
        "kind": "thermal.reading",
        "ranch": "ranch_a",
        "entity": "coyote_cam",
        "lat": 34.125,
        "lon": -106.458,
        "predators_detected": 1,
    }


def _build_bridge(
    *,
    broker: InMemoryBroker | None = None,
    seed: int | None = 42,
) -> PiToMissionBridge:
    broker = broker or InMemoryBroker()
    backend = StubBackend()
    return PiToMissionBridge(
        ranch_id="ranch_a",
        drone_backend=backend,
        mqtt_publish=broker.publisher(),
        ts_provider=_fixed_ts,
        seed=seed,
    )


# ---------------------------------------------------------------------------
# Topic filter
# ---------------------------------------------------------------------------


class TestTopicFilter:
    def test_drops_foreign_topic_prefix(self) -> None:
        bridge = _build_bridge()
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_z/fence/sw_fence", _fence_breach_payload())
        )
        assert result == []
        # Ledger should NOT have a wake_event entry for a filtered topic.
        kinds = [e.kind for e in bridge.ledger.iter_events()]
        assert "wake_event" not in kinds

    def test_drops_unknown_suffix(self) -> None:
        bridge = _build_bridge()
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/weather/storm_front", {"kind": "weather.alert"})
        )
        assert result == []

    def test_accepts_fence_topic(self) -> None:
        bridge = _build_bridge()
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
        )
        assert len(result) > 0

    def test_accepts_alert_thermal_hit_topic(self) -> None:
        bridge = _build_bridge()
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/alert/thermal_hit", _thermal_hit_payload())
        )
        assert len(result) > 0

    def test_accepts_thermal_reading_topic(self) -> None:
        bridge = _build_bridge()
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/thermal/coyote_cam", _thermal_reading_payload())
        )
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Fence-breach flow
# ---------------------------------------------------------------------------


class TestFenceBreachFlow:
    def test_full_cascade_against_stub_backend(self) -> None:
        broker = InMemoryBroker()
        backend = StubBackend()
        bridge = PiToMissionBridge(
            ranch_id="ranch_a",
            drone_backend=backend,
            mqtt_publish=broker.publisher(),
            ts_provider=_fixed_ts,
            seed=42,
        )
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
        )
        tool_names = [r.get("tool") for r in result]
        assert "launch_drone" in tool_names
        assert "play_deterrent" in tool_names
        # page_rancher returns status=skipped but is still executed/logged
        assert "page_rancher" in tool_names

        state = asyncio.run(backend.state())
        assert state.in_air is True
        assert state.mode == "AUTO"

        kinds = [e.kind for e in bridge.ledger.iter_events()]
        assert "wake_event" in kinds
        assert "mission.launched" in kinds
        assert "deterrent.played" in kinds

    def test_waypoint_matches_payload_coords(self) -> None:
        bridge = _build_bridge()
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
        )
        launch = next(r for r in result if r["tool"] == "launch_drone")
        assert launch["status"] == "ok"
        assert abs(launch["target_lat"] - 34.123) < 1e-6
        assert abs(launch["target_lon"] - -106.456) < 1e-6
        assert launch["alt_m"] == 60.0


# ---------------------------------------------------------------------------
# Thermal hit flow (from alert/thermal_hit)
# ---------------------------------------------------------------------------


class TestThermalHitFlow:
    def test_cascade_from_thermal_hit_topic(self) -> None:
        broker = InMemoryBroker()
        bridge = _build_bridge(broker=broker)
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/alert/thermal_hit", _thermal_hit_payload())
        )
        tool_names = [r.get("tool") for r in result]
        assert "launch_drone" in tool_names
        assert "play_deterrent" in tool_names


# ---------------------------------------------------------------------------
# Deterrent side-channel (MQTT publish)
# ---------------------------------------------------------------------------


class TestDeterrentSideChannel:
    def test_side_channel_published(self) -> None:
        broker = InMemoryBroker()
        bridge = _build_bridge(broker=broker)
        asyncio.run(bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload()))
        deterrent_msgs = broker.messages_on("skyherd/ranch_a/deterrent/play")
        assert len(deterrent_msgs) == 1
        msg = deterrent_msgs[0]
        assert "tone_hz" in msg
        assert "duration_s" in msg

    def test_side_channel_noop_when_no_publish_hook(self) -> None:
        """When no mqtt_publish hook and aiomqtt fails, bridge does not crash."""
        # Default aiomqtt path unreachable — bridge should swallow and still
        # return the launch_drone result.
        backend = StubBackend()
        bridge = PiToMissionBridge(
            ranch_id="ranch_a",
            drone_backend=backend,
            mqtt_publish=None,
            ts_provider=_fixed_ts,
            seed=42,
        )
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
        )
        # Deterrent step still executes (the local backend call succeeded);
        # side-channel publish is best-effort.
        assert any(r.get("tool") == "play_deterrent" for r in result)


# ---------------------------------------------------------------------------
# Attestation chain
# ---------------------------------------------------------------------------


class TestAttestationChain:
    def test_chain_verifies_after_multiple_events(self) -> None:
        bridge = _build_bridge()
        for _ in range(3):
            asyncio.run(
                bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
            )
        events = list(bridge.ledger.iter_events())
        assert len(events) >= 9  # 3x (wake + launch + deterrent)
        # Sequence monotonic and gap-free
        seqs = [e.seq for e in events]
        assert seqs == sorted(seqs)
        assert seqs[0] == 1 and seqs[-1] == len(events)
        # Chain + signatures verify
        assert verify_chain(bridge.ledger) is True

    def test_ts_iso_frozen_under_ts_provider(self) -> None:
        bridge = _build_bridge()
        asyncio.run(bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload()))
        events = list(bridge.ledger.iter_events())
        # All events share the same ts_iso under the frozen provider
        ts_set = {e.ts_iso for e in events}
        assert len(ts_set) == 1


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_two_runs_produce_identical_payloads(self) -> None:
        """Same seed + frozen ts → byte-identical ledger payload_json."""
        payload_lists: list[list[str]] = []
        for _ in range(2):
            bridge = _build_bridge(seed=42)
            for _ in range(2):
                asyncio.run(
                    bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
                )
            payload_lists.append([e.payload_json for e in bridge.ledger.iter_events()])
        assert payload_lists[0] == payload_lists[1]

    def test_mission_id_is_seed_deterministic(self) -> None:
        bridge1 = _build_bridge(seed=42)
        bridge2 = _build_bridge(seed=42)
        r1 = asyncio.run(
            bridge1.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
        )
        r2 = asyncio.run(
            bridge2.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
        )
        m1 = next(r for r in r1 if r["tool"] == "launch_drone")["mission_id"]
        m2 = next(r for r in r2 if r["tool"] == "launch_drone")["mission_id"]
        assert m1 == m2

    def test_different_seeds_yield_different_mission_ids(self) -> None:
        bridge1 = _build_bridge(seed=42)
        bridge2 = _build_bridge(seed=7)
        r1 = asyncio.run(
            bridge1.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
        )
        r2 = asyncio.run(
            bridge2.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
        )
        m1 = next(r for r in r1 if r["tool"] == "launch_drone")["mission_id"]
        m2 = next(r for r in r2 if r["tool"] == "launch_drone")["mission_id"]
        assert m1 != m2


# ---------------------------------------------------------------------------
# Backend failure
# ---------------------------------------------------------------------------


class TestBackendFailure:
    def test_stub_force_unavailable_logs_but_does_not_crash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the backend cannot connect, the bridge logs and stays alive."""
        monkeypatch.setattr(stub_module, "STUB_FORCE_UNAVAILABLE", True)
        broker = InMemoryBroker()
        backend = StubBackend()
        bridge = PiToMissionBridge(
            ranch_id="ranch_a",
            drone_backend=backend,
            mqtt_publish=broker.publisher(),
            ts_provider=_fixed_ts,
            seed=42,
        )
        # No raise
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
        )
        # The dispatch still returns tool-call result dicts; the launch_drone
        # entry must have failed status because takeoff raised DroneUnavailable.
        launch = next((r for r in result if r["tool"] == "launch_drone"), None)
        assert launch is not None
        assert launch["status"] == "failed"
        kinds = [e.kind for e in bridge.ledger.iter_events()]
        assert "mission.failed" in kinds


# ---------------------------------------------------------------------------
# Non-breach events are noops
# ---------------------------------------------------------------------------


class TestNonBreachEventsNoOp:
    def test_thermal_reading_without_predator_flag_still_triggers(self) -> None:
        """Per `_normalise` contract: any `/thermal/` topic becomes
        `thermal.hotspot`, which the dispatcher treats as a breach."""
        bridge = _build_bridge()
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/thermal/coyote_cam", _thermal_reading_payload())
        )
        # thermal/ becomes thermal.hotspot — dispatcher fires full cascade
        tool_names = [r.get("tool") for r in result]
        assert "launch_drone" in tool_names

    def test_unknown_topic_kind_ignored_silently(self) -> None:
        bridge = _build_bridge()
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/water/trough_1", {"kind": "water.low"})
        )
        assert result == []


# ---------------------------------------------------------------------------
# Run loop best-effort
# ---------------------------------------------------------------------------


class TestRunLoopBestEffort:
    def test_run_exits_gracefully_when_aiomqtt_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """run() must never propagate broker failures."""
        bridge = _build_bridge()

        # Monkey-patch aiomqtt.Client to raise on connect
        import aiomqtt  # type: ignore[import-untyped]

        class _BrokenClient:  # noqa: D401
            def __init__(self, *a: Any, **kw: Any) -> None:
                raise ConnectionRefusedError("broker offline")

            async def __aenter__(self) -> Any:  # pragma: no cover
                return self

            async def __aexit__(self, *a: Any) -> None:  # pragma: no cover
                pass

        monkeypatch.setattr(aiomqtt, "Client", _BrokenClient)
        # Should exit cleanly, NOT raise
        asyncio.run(asyncio.wait_for(bridge.run(), timeout=1.0))


# ---------------------------------------------------------------------------
# CoyoteHarness → PiToMissionBridge end-to-end (sanity)
# ---------------------------------------------------------------------------


class TestCoyoteHarnessIntegration:
    def test_thermal_hit_from_harness_dispatches_mission(self) -> None:
        broker = InMemoryBroker()
        bridge = _build_bridge(broker=broker, seed=42)

        async def forward_to_bridge(topic: str, raw: bytes) -> None:
            payload = json.loads(raw.decode())
            # Also mirror into broker for assertions
            await broker.publisher()(topic, raw)
            await bridge.handle_event(topic, payload)

        harness = CoyoteHarness(
            seed=42,
            ts_provider=_fixed_ts,
            mqtt_publish=forward_to_bridge,
        )
        asyncio.run(harness.run_once())

        # Harness emits reading + alert; the thermal-hit alert triggers a mission
        # After `/alert/thermal_hit` arrival, the bridge should have executed
        # launch_drone against StubBackend.
        kinds = [e.kind for e in bridge.ledger.iter_events()]
        assert "mission.launched" in kinds


# ---------------------------------------------------------------------------
# Ledger appends and verify_chain helper
# ---------------------------------------------------------------------------


class TestLedgerAppendsAndVerify:
    def test_verify_chain_returns_true_for_pristine_chain(self) -> None:
        bridge = _build_bridge()
        asyncio.run(bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload()))
        assert verify_chain(bridge.ledger) is True

    def test_verify_chain_returns_false_when_chain_broken(self) -> None:
        """Tamper with the sqlite store and show verify_chain detects it."""
        bridge = _build_bridge()
        asyncio.run(bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload()))
        # Corrupt one prev_hash in-place
        bridge.ledger._conn.execute(  # type: ignore[attr-defined]
            "UPDATE events SET prev_hash=? WHERE seq=2",
            ("deadbeef",),
        )
        bridge.ledger._conn.commit()  # type: ignore[attr-defined]
        assert verify_chain(bridge.ledger) is False

    def test_ranch_id_property_exposed(self) -> None:
        bridge = _build_bridge()
        assert bridge.ranch_id == "ranch_a"


# ---------------------------------------------------------------------------
# Failover ledger entry
# ---------------------------------------------------------------------------


class TestFailoverLedgerEntry:
    def test_failover_writes_sitl_failover_entry(self) -> None:
        bridge = _build_bridge()
        # Call connect so RTL against StubBackend succeeds
        asyncio.run(bridge.connect())
        asyncio.run(bridge.failover("test failure"))
        kinds = [e.kind for e in bridge.ledger.iter_events()]
        assert "sitl.failover" in kinds
        entry = next(e for e in bridge.ledger.iter_events() if e.kind == "sitl.failover")
        parsed = json.loads(entry.payload_json)
        assert parsed["status"] == "rtl_ok"
        assert parsed["reason"] == "test failure"


# ---------------------------------------------------------------------------
# Extra coverage: unseeded mission_id, thermal clip tool, side-channel swallow
# ---------------------------------------------------------------------------


class TestMissionIdUnseeded:
    def test_unseeded_counter_increments_monotonically(self) -> None:
        bridge = _build_bridge(seed=None)
        r1 = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
        )
        r2 = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
        )
        m1 = next(r for r in r1 if r["tool"] == "launch_drone")["mission_id"]
        m2 = next(r for r in r2 if r["tool"] == "launch_drone")["mission_id"]
        assert m1.startswith("mission-")
        assert m2.startswith("mission-")
        assert m1 != m2


class TestSideChannelSwallowsException:
    def test_publish_hook_exception_swallowed(self) -> None:
        async def broken_publish(topic: str, raw: bytes) -> None:
            raise RuntimeError("broker fell over")

        backend = StubBackend()
        bridge = PiToMissionBridge(
            ranch_id="ranch_a",
            drone_backend=backend,
            mqtt_publish=broken_publish,
            ts_provider=_fixed_ts,
            seed=42,
        )
        # Must not raise even though publish hook always explodes
        result = asyncio.run(
            bridge.handle_event("skyherd/ranch_a/fence/sw_fence", _fence_breach_payload())
        )
        assert any(r.get("tool") == "play_deterrent" for r in result)


class TestRunLoopSubscribe:
    def test_run_processes_one_message_then_stops(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Drive run() through a fake aiomqtt Client that yields one message."""
        import aiomqtt  # type: ignore[import-untyped]

        class _FakeMessage:
            def __init__(self, topic: str, payload: bytes) -> None:
                self.topic = topic
                self.payload = payload

        class _FakeClient:
            def __init__(self, *a: Any, **kw: Any) -> None:
                self._subscribed: list[str] = []
                payload = json.dumps(_fence_breach_payload()).encode()
                self._queue = [_FakeMessage("skyherd/ranch_a/fence/sw_fence", payload)]

            async def __aenter__(self) -> Any:
                return self

            async def __aexit__(self, *a: Any) -> None:
                return None

            async def subscribe(self, topic: str) -> None:
                self._subscribed.append(topic)

            @property
            def messages(self):  # type: ignore[no-untyped-def]
                async def _gen():
                    for msg in self._queue:
                        yield msg

                return _gen()

        monkeypatch.setattr(aiomqtt, "Client", _FakeClient)

        bridge = _build_bridge()
        # run() consumes the single fake message and exits cleanly
        asyncio.run(asyncio.wait_for(bridge.run(), timeout=2.0))
        # A wake_event should have been appended from the fake message
        kinds = [e.kind for e in bridge.ledger.iter_events()]
        assert "wake_event" in kinds

    def test_run_drops_bad_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Messages with invalid JSON are skipped, loop keeps running."""
        import aiomqtt  # type: ignore[import-untyped]

        class _FakeMessage:
            def __init__(self, topic: str, payload: bytes) -> None:
                self.topic = topic
                self.payload = payload

        class _FakeClient:
            def __init__(self, *a: Any, **kw: Any) -> None:
                # First message has bad JSON, second is valid — both should
                # be handled without crash.
                good = json.dumps(_fence_breach_payload()).encode()
                self._queue = [
                    _FakeMessage("skyherd/ranch_a/fence/sw_fence", b"{not-json"),
                    _FakeMessage("skyherd/ranch_a/fence/sw_fence", good),
                ]

            async def __aenter__(self) -> Any:
                return self

            async def __aexit__(self, *a: Any) -> None:
                return None

            async def subscribe(self, topic: str) -> None:
                return None

            @property
            def messages(self):  # type: ignore[no-untyped-def]
                async def _gen():
                    for msg in self._queue:
                        yield msg

                return _gen()

        monkeypatch.setattr(aiomqtt, "Client", _FakeClient)
        bridge = _build_bridge()
        asyncio.run(asyncio.wait_for(bridge.run(), timeout=2.0))
        kinds = [e.kind for e in bridge.ledger.iter_events()]
        # At least one wake_event from the valid message
        assert kinds.count("wake_event") >= 1

    def test_stop_signals_loop_exit(self) -> None:
        bridge = _build_bridge()
        bridge.stop()
        # run() with pre-stopped flag should exit immediately even with broken aiomqtt
        # (no need to even mock — the inner loop won't iterate once _running is False).
        # We just assert the stop() flag is observable.
        assert bridge._running is False  # type: ignore[attr-defined]
