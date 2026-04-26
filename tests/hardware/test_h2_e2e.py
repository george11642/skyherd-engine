"""End-to-end Phase 6 (H2-05) integration tests.

Full in-process chain — no docker, no MAVSDK, no Anthropic API — drives a
:class:`skyherd.edge.coyote_harness.CoyoteHarness` through an
:class:`InMemoryBroker` into :class:`~skyherd.edge.pi_to_mission.PiToMissionBridge`,
which dispatches through the simulation
:func:`~skyherd.agents.simulate.fenceline_dispatcher` to a
:class:`~skyherd.drone.stub.StubBackend`.  Every externally-observable hop
lands in the attestation ledger; the chain verifies end-to-end.

Acceptance gate: the ``TestH2Smoke`` class runs under 10 seconds.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.drone.stub import StubBackend
from skyherd.edge.coyote_harness import CoyoteHarness
from skyherd.edge.pi_to_mission import PiToMissionBridge, verify_chain
from skyherd.edge.speaker_bridge import DeterrentResult, SpeakerBridge

# ---------------------------------------------------------------------------
# Shared in-memory broker fixture
# ---------------------------------------------------------------------------


class InMemoryBroker:
    def __init__(self) -> None:
        self._next_seq = 0
        self._messages: list[tuple[int, str, dict[str, Any]]] = []
        self._by_topic: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
        self._subscribers: list[Any] = []

    def publisher(self):  # type: ignore[no-untyped-def]
        async def publish(topic: str, raw: bytes) -> None:
            payload = json.loads(raw.decode())
            self._next_seq += 1
            self._messages.append((self._next_seq, topic, payload))
            self._by_topic[topic].append((self._next_seq, payload))
            # Fan out to subscribers
            for sub in list(self._subscribers):
                await sub(topic, payload)

        return publish

    def subscribe(self, callback) -> None:  # type: ignore[no-untyped-def]
        self._subscribers.append(callback)

    def messages_on(self, topic_prefix: str) -> list[dict[str, Any]]:
        return [p for _seq, t, p in self._messages if t.startswith(topic_prefix)]

    def total(self) -> int:
        return len(self._messages)


def _fixed_ts() -> float:
    return 1_714_000_000.0


def _open_ledger(path: Path) -> Ledger:
    return Ledger.open(path, Signer.generate(), ts_provider=_fixed_ts)


# ---------------------------------------------------------------------------
# Core chain builder
# ---------------------------------------------------------------------------


def _build_chain(
    tmp_path: Path, *, seed: int = 42, ledger_name: str = "ledger.db"
) -> tuple[InMemoryBroker, PiToMissionBridge, CoyoteHarness, Ledger]:
    broker = InMemoryBroker()
    ledger = _open_ledger(tmp_path / ledger_name)

    bridge = PiToMissionBridge(
        ranch_id="ranch_a",
        drone_backend=StubBackend(),
        ledger=ledger,
        mqtt_publish=broker.publisher(),
        ts_provider=_fixed_ts,
        seed=seed,
    )

    async def forward_to_bridge(topic: str, payload: dict) -> None:
        # Only forward topics the bridge cares about
        if "/fence/" in topic or "/alert/thermal_hit" in topic or "/thermal/" in topic:
            await bridge.handle_event(topic, payload)

    broker.subscribe(forward_to_bridge)

    harness = CoyoteHarness(seed=seed, ts_provider=_fixed_ts, mqtt_publish=broker.publisher())
    return broker, bridge, harness, ledger


# ---------------------------------------------------------------------------
# Smoke tests (acceptance gate: <10 s)
# ---------------------------------------------------------------------------


class TestH2Smoke:
    def test_single_thermal_hit_triggers_mission(self, tmp_path: Path) -> None:
        broker, bridge, harness, ledger = _build_chain(tmp_path)
        asyncio.run(harness.run_once())

        state = asyncio.run(bridge._drone_backend.state())  # type: ignore[attr-defined]
        assert state.in_air is True
        assert state.mode == "AUTO"

        kinds = [e.kind for e in ledger.iter_events()]
        assert "wake_event" in kinds
        assert "mission.launched" in kinds
        assert "deterrent.played" in kinds

    def test_deterrent_side_emit_published(self, tmp_path: Path) -> None:
        broker, bridge, harness, ledger = _build_chain(tmp_path)
        asyncio.run(harness.run_once())

        deterrent = broker.messages_on("skyherd/ranch_a/deterrent/play")
        assert len(deterrent) >= 1
        assert "tone_hz" in deterrent[0]
        assert "duration_s" in deterrent[0]

    def test_ledger_chain_verifies(self, tmp_path: Path) -> None:
        broker, bridge, harness, ledger = _build_chain(tmp_path)
        asyncio.run(harness.run_once())
        assert verify_chain(ledger) is True

    def test_10_event_storm_no_drops(self, tmp_path: Path) -> None:
        broker, bridge, harness, ledger = _build_chain(tmp_path)

        async def storm() -> None:
            for _ in range(10):
                await harness.run_once()

        asyncio.run(storm())
        events = list(ledger.iter_events())
        # At least 10 × (wake_event + mission.launched + deterrent.played)
        assert len(events) >= 30
        assert verify_chain(ledger) is True

    def test_speaker_bridge_consumes_side_channel(self, tmp_path: Path) -> None:
        """Full fan-out: harness → bridge emits deterrent/play → SpeakerBridge."""
        broker, bridge, harness, ledger = _build_chain(tmp_path)

        plays: list[tuple[int, float]] = []

        def recording_player(path: Path, tone: int, dur: float) -> DeterrentResult:
            plays.append((tone, dur))
            return DeterrentResult(
                played=True,
                tone_hz=tone,
                duration_s=dur,
                backend="rec",
                wav_path=path,
            )

        speaker = SpeakerBridge(ranch_id="ranch_a", backend_name="rec", player=recording_player)

        async def speaker_subscriber(topic: str, payload: dict) -> None:
            speaker.handle_message(topic, payload)

        broker.subscribe(speaker_subscriber)

        asyncio.run(harness.run_once())
        assert len(plays) >= 1


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestH2Determinism:
    def test_seed42_byte_identical_ledger_payloads(
        self, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        results: list[list[str]] = []
        for i in range(2):
            path = tmp_path_factory.mktemp(f"run_{i}")
            broker, bridge, harness, ledger = _build_chain(path, seed=42, ledger_name="ledger.db")

            async def storm(h: CoyoteHarness = harness) -> None:
                for _ in range(2):
                    await h.run_once()

            asyncio.run(storm())
            results.append([e.payload_json for e in ledger.iter_events()])
        assert results[0] == results[1]

    def test_seed42_vs_seed7_differ(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Sanity: different seeds produce different frame_path values."""
        p1 = tmp_path_factory.mktemp("seed42")
        p2 = tmp_path_factory.mktemp("seed7")
        _, _, h1, l1 = _build_chain(p1, seed=42)
        _, _, h2, l2 = _build_chain(p2, seed=7)

        asyncio.run(h1.run_once())
        asyncio.run(h2.run_once())

        p1_events = [e.payload_json for e in l1.iter_events()]
        p2_events = [e.payload_json for e in l2.iter_events()]
        # Different mission_ids (seeded differently) → different launched
        # entries at minimum.
        assert p1_events != p2_events


# ---------------------------------------------------------------------------
# Performance gate
# ---------------------------------------------------------------------------


class TestH2Performance:
    def test_e2e_10_ticks_under_10s(self, tmp_path: Path) -> None:
        broker, bridge, harness, ledger = _build_chain(tmp_path)

        async def storm() -> None:
            for _ in range(10):
                await harness.run_once()

        t0 = time.monotonic()
        asyncio.run(storm())
        elapsed = time.monotonic() - t0
        assert elapsed < 10.0, f"E2E 10-tick run took {elapsed:.2f}s (>10s)"
