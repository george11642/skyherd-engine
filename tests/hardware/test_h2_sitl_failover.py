"""Chaos-monkey SITL failover tests for Phase 6 (H2-04).

Drives :class:`skyherd.edge.pi_to_mission.PiToMissionBridge` with a
:class:`tests.fixtures.fake_sitl.FakeSITLBackend` that injects
:class:`~skyherd.drone.interface.DroneUnavailable` at strategic points —
takeoff, mid-patrol, and RTL.  Asserts the bridge:

* writes a ``mission.failed`` ledger entry before falling back,
* triggers :meth:`PiToMissionBridge.failover` which issues RTL,
* records a ``sitl.failover`` entry with the correct status,
* never propagates exceptions out of :meth:`handle_event`,
* keeps the attestation chain verifiable end-to-end,
* produces byte-identical ledger payloads on replay.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.edge.pi_to_mission import PiToMissionBridge, verify_chain
from tests.fixtures.fake_sitl import FakeSITLBackend

FENCE_TOPIC = "skyherd/ranch_a/fence/sw_fence"


def _fixed_ts() -> float:
    return 1_714_000_000.0


def _fence_payload() -> dict:
    return {
        "kind": "fence.breach",
        "ranch": "ranch_a",
        "segment": "sw_fence",
        "lat": 34.123,
        "lon": -106.456,
    }


def _fresh_ledger(tmp_path: Path, name: str = "ledger.db") -> Ledger:
    signer = Signer.generate()
    return Ledger.open(tmp_path / name, signer, ts_provider=_fixed_ts)


def _build_bridge(backend: FakeSITLBackend, ledger: Ledger) -> PiToMissionBridge:
    return PiToMissionBridge(
        ranch_id="ranch_a",
        drone_backend=backend,
        ledger=ledger,
        ts_provider=_fixed_ts,
        seed=42,
    )


class TestFailover:
    def test_takeoff_failure_triggers_failover(self, tmp_path: Path) -> None:
        backend = FakeSITLBackend(fail_on_takeoff=True)
        ledger = _fresh_ledger(tmp_path)
        bridge = _build_bridge(backend, ledger)

        result = asyncio.run(bridge.handle_event(FENCE_TOPIC, _fence_payload()))

        # Launch reported failed
        launch = next(r for r in result if r["tool"] == "launch_drone")
        assert launch["status"] == "failed"

        kinds = [e.kind for e in ledger.iter_events()]
        assert "mission.failed" in kinds
        assert "sitl.failover" in kinds

        # Failover succeeded via RTL on the underlying stub (after reset state)
        failover = next(e for e in ledger.iter_events() if e.kind == "sitl.failover")
        parsed = json.loads(failover.payload_json)
        assert parsed["status"] == "rtl_ok"

    def test_patrol_mid_mission_failure(self, tmp_path: Path) -> None:
        # fail on first patrol waypoint (waypoint 0 triggers failure)
        backend = FakeSITLBackend(fail_after_waypoints=0)
        ledger = _fresh_ledger(tmp_path)
        bridge = _build_bridge(backend, ledger)

        result = asyncio.run(bridge.handle_event(FENCE_TOPIC, _fence_payload()))

        launch = next(r for r in result if r["tool"] == "launch_drone")
        assert launch["status"] == "failed"

        events = list(ledger.iter_events())
        mission_failed = next(e for e in events if e.kind == "mission.failed")
        sitl_failover = next(e for e in events if e.kind == "sitl.failover")
        # mission.failed precedes sitl.failover in the ledger
        assert mission_failed.seq < sitl_failover.seq

    def test_rtl_double_fault(self, tmp_path: Path) -> None:
        """Patrol fails AND rtl fails — sitl.failover status=rtl_failed."""
        backend = FakeSITLBackend(
            fail_after_waypoints=0, fail_on_return_to_home=True
        )
        ledger = _fresh_ledger(tmp_path)
        bridge = _build_bridge(backend, ledger)

        # Must NOT raise
        asyncio.run(bridge.handle_event(FENCE_TOPIC, _fence_payload()))

        failover = next(e for e in ledger.iter_events() if e.kind == "sitl.failover")
        parsed = json.loads(failover.payload_json)
        assert parsed["status"] == "rtl_failed"
        assert "error" in parsed

    def test_failover_ledger_chain_intact(self, tmp_path: Path) -> None:
        backend = FakeSITLBackend(fail_after_waypoints=0)
        ledger = _fresh_ledger(tmp_path)
        bridge = _build_bridge(backend, ledger)

        asyncio.run(bridge.handle_event(FENCE_TOPIC, _fence_payload()))

        assert verify_chain(ledger) is True

    def test_deterministic_failover_replay(self, tmp_path: Path) -> None:
        """Same scenario twice with seed=42 + frozen ts → identical payloads."""
        ledgers = []
        for i in range(2):
            backend = FakeSITLBackend(fail_after_waypoints=0)
            ledger = _fresh_ledger(tmp_path, name=f"ledger_{i}.db")
            bridge = _build_bridge(backend, ledger)
            asyncio.run(bridge.handle_event(FENCE_TOPIC, _fence_payload()))
            ledgers.append(ledger)
        payloads = [
            [e.payload_json for e in ledger.iter_events()] for ledger in ledgers
        ]
        assert payloads[0] == payloads[1]

    def test_happy_path_no_failover_entry(self, tmp_path: Path) -> None:
        """No failure injected → no sitl.failover in the ledger."""
        backend = FakeSITLBackend()  # no failure hooks
        ledger = _fresh_ledger(tmp_path)
        bridge = _build_bridge(backend, ledger)

        asyncio.run(bridge.handle_event(FENCE_TOPIC, _fence_payload()))

        kinds = [e.kind for e in ledger.iter_events()]
        assert "mission.launched" in kinds
        assert "sitl.failover" not in kinds
        assert "mission.failed" not in kinds


class TestFakeSITLBackend:
    """Direct tests of the fixture so the failure-injection contract is
    explicit and regression-resistant."""

    def test_fail_on_takeoff_raises(self) -> None:
        backend = FakeSITLBackend(fail_on_takeoff=True)
        asyncio.run(backend.connect())
        with pytest.raises(Exception):
            asyncio.run(backend.takeoff())

    def test_fail_after_one_waypoint(self) -> None:
        from skyherd.drone.interface import Waypoint

        backend = FakeSITLBackend(fail_after_waypoints=1)
        asyncio.run(backend.connect())
        asyncio.run(backend.takeoff())
        waypoints = [
            Waypoint(lat=34.0, lon=-106.0, alt_m=60.0),
            Waypoint(lat=34.1, lon=-106.1, alt_m=60.0),
        ]
        with pytest.raises(Exception):
            asyncio.run(backend.patrol(waypoints))
        # First waypoint should have been "executed" (counter advanced)
        assert backend._patrol_waypoint_count == 1

    def test_fail_on_rtl_raises(self) -> None:
        backend = FakeSITLBackend(fail_on_return_to_home=True)
        asyncio.run(backend.connect())
        asyncio.run(backend.takeoff())
        with pytest.raises(Exception):
            asyncio.run(backend.return_to_home())

    def test_state_and_deterrent_delegate_to_stub(self) -> None:
        backend = FakeSITLBackend()
        asyncio.run(backend.connect())
        asyncio.run(backend.takeoff())
        state = asyncio.run(backend.state())
        assert state.in_air is True
        asyncio.run(backend.play_deterrent(tone_hz=14000, duration_s=1.0))
        clip = asyncio.run(backend.get_thermal_clip(duration_s=1.0))
        assert str(clip).endswith(".png")
