"""End-to-end replay test — a canned DJI ACK stream walks through the
:class:`~skyherd.drone.mavic_adapter.MavicAdapter`, exercising the
mid-mission failover path **without a real drone**.

Fixture: ``tests/hardware/fixtures/dji_packet_stream.jsonl``.  Each line
is a JSON ACK that the companion app would publish over WebSocket/MQTT.
A fake transport yields one line per ``send_command`` call so the
``MavicBackend`` under the adapter's primary leg sees authentic wire
shapes.

The MAVSDK leg is mocked: when failover triggers, ``patrol`` on the
fallback leg succeeds immediately.

This is the Phase 7-04 verification gate — proves the whole chain
runs deterministically in under 500 ms.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from skyherd.drone.interface import DroneState, Waypoint
from skyherd.drone.mavic import MavicBackend
from skyherd.drone.mavic_adapter import MavicAdapter
from skyherd.drone.mission_schema import MissionMetadata, MissionV1

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "dji_packet_stream.jsonl"


# ---------------------------------------------------------------------------
# Fixture loader + fake WebSocket transport
# ---------------------------------------------------------------------------


def _load_fixture() -> list[dict]:
    return [json.loads(line) for line in FIXTURE_PATH.read_text().splitlines() if line.strip()]


class _FakeFixtureTransport:
    """Replay recorded ACK packets in order.

    The transport skips over packets whose ``ack`` doesn't match the
    incoming ``cmd`` — this lets the fixture record telemetry (frequent
    ``get_state`` probes) interleaved with mission commands.
    ``get_state`` calls that exhaust the matching fixture packets fall
    back to a canned OK (avoids spurious failures from the MavicBackend
    internal state-sync loop).
    """

    def __init__(self, packets: list[dict]) -> None:
        self._packets: list[dict | None] = list(packets)
        self._closed = False

    async def connect(self, timeout_s: float | None = None) -> None:
        return None

    async def send_command(self, cmd: str, args: dict, seq: int) -> dict:
        """Return the next matching fixture packet without disturbing other commands.

        Strategy: find the first unconsumed packet whose ``ack`` matches
        ``cmd``, consume it, return it.  This lets ``get_state`` probes
        interleaved with mission commands drain independently — we
        don't accidentally consume a queued ``patrol`` ACK when the
        backend polls state.

        When the fixture is exhausted for ``cmd``, ``get_state`` calls
        get a canned in-flight OK and everything else gets a trailing
        OK (so ``disconnect`` and leftover telemetry don't crash).
        """
        for i, pkt in enumerate(self._packets):
            if pkt is None:
                continue
            if pkt.get("ack") == cmd:
                self._packets[i] = None  # consume in place
                pkt = dict(pkt)
                pkt["seq"] = seq
                return pkt
        if cmd == "get_state":
            return {
                "ack": "get_state",
                "result": "ok",
                "seq": seq,
                "data": {
                    "armed": True,
                    "in_air": True,
                    "altitude_m": 30.0,
                    "battery_pct": 75.0,
                    "mode": "AUTO",
                    "lat": 34.1234,
                    "lon": -106.5678,
                },
            }
        return {"ack": cmd, "result": "ok", "seq": seq}

    async def close(self) -> None:
        self._closed = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mavsdk_mock() -> MagicMock:
    """AsyncMock MAVSDK leg that accepts every actuator call."""
    mav = MagicMock()
    mav.connect = AsyncMock()
    mav.takeoff = AsyncMock()
    mav.patrol = AsyncMock()
    mav.return_to_home = AsyncMock()
    mav.play_deterrent = AsyncMock()
    mav.get_thermal_clip = AsyncMock(return_value=Path("/tmp/t.png"))
    mav.state = AsyncMock(return_value=DroneState(battery_pct=75.0, mode="AUTO"))
    mav.disconnect = AsyncMock()
    return mav


class _CapturingLedger:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def append(self, *, kind: str, data: dict) -> None:
        self.events.append({"kind": kind, "data": data})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replay_happy_path_no_failover() -> None:
    """Filter out the error line → mission completes on DJI, no failover."""
    # Strip the signal-lost packet so the happy path can run to completion.
    packets = [
        p for p in _load_fixture() if not (p.get("ack") == "patrol" and p.get("result") == "error")
    ]
    # Append a patrol=ok so the single patrol() call finds its ACK.
    packets.insert(3, {"ack": "patrol", "result": "ok", "seq": 99})

    dji_real = MavicBackend(transport=_FakeFixtureTransport(packets))
    mav_mock = _make_mavsdk_mock()
    ledger = _CapturingLedger()
    adapter = MavicAdapter(
        primary=dji_real,
        fallback=mav_mock,
        ledger=ledger,
        ts_provider=lambda: 1.0,
    )

    await adapter.connect()
    await adapter.takeoff(alt_m=30.0)
    await adapter.patrol([Waypoint(lat=34.124, lon=-106.567, alt_m=30.0)])

    # Assert before disconnect (disconnect clears active_leg by design).
    assert adapter.active_leg == "dji"
    assert adapter.failover_count == 0
    mav_mock.patrol.assert_not_awaited()

    await adapter.disconnect()


@pytest.mark.asyncio
async def test_replay_failover_on_signal_lost() -> None:
    """Full fixture — mid-patrol error forces failover to MAVSDK."""
    packets = _load_fixture()

    dji_real = MavicBackend(transport=_FakeFixtureTransport(packets))
    mav_mock = _make_mavsdk_mock()
    ledger = _CapturingLedger()
    adapter = MavicAdapter(
        primary=dji_real,
        fallback=mav_mock,
        ledger=ledger,
        ts_provider=lambda: 2.0,
    )

    await adapter.connect()
    await adapter.takeoff(alt_m=30.0)
    # This patrol is the one that returns the error packet.
    await adapter.patrol([Waypoint(lat=34.124, lon=-106.567, alt_m=30.0)])

    # Failover must have happened; mavsdk leg served the retry.
    assert adapter.failover_count == 1
    assert adapter.active_leg == "mavsdk"
    mav_mock.patrol.assert_awaited_once()

    await adapter.return_to_home()
    await adapter.disconnect()


@pytest.mark.asyncio
async def test_replay_ledger_chain_integrity() -> None:
    """Every adapter-level hop emits a ledger entry in monotonic order."""
    packets = _load_fixture()
    dji_real = MavicBackend(transport=_FakeFixtureTransport(packets))
    mav_mock = _make_mavsdk_mock()
    ledger = _CapturingLedger()
    adapter = MavicAdapter(
        primary=dji_real,
        fallback=mav_mock,
        ledger=ledger,
        ts_provider=lambda: 3.0,
    )

    await adapter.connect()
    await adapter.takeoff(alt_m=30.0)
    await adapter.patrol([Waypoint(lat=34.124, lon=-106.567, alt_m=30.0)])
    await adapter.return_to_home()
    await adapter.disconnect()

    kinds = [e["kind"] for e in ledger.events]
    # leg_selected → failover (mid-patrol)
    assert kinds[0] == "adapter.leg_selected"
    assert "adapter.failover" in kinds
    # Monotonic ts (we fixed it at 3.0, so all entries have ts=3.0 — monotonic trivially)
    tss = [e["data"]["ts"] for e in ledger.events]
    assert all(t == 3.0 for t in tss)


@pytest.mark.asyncio
async def test_replay_wall_time_under_500ms() -> None:
    """Whole replay completes in <500 ms — fast CI gate."""
    packets = _load_fixture()
    dji_real = MavicBackend(transport=_FakeFixtureTransport(packets))
    mav_mock = _make_mavsdk_mock()
    adapter = MavicAdapter(primary=dji_real, fallback=mav_mock)

    start = time.monotonic()
    await adapter.connect()
    await adapter.takeoff(alt_m=30.0)
    await adapter.patrol([Waypoint(lat=34.124, lon=-106.567, alt_m=30.0)])
    await adapter.return_to_home()
    await adapter.disconnect()
    elapsed = time.monotonic() - start

    assert elapsed < 0.5, f"replay too slow: {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_replay_mission_id_survives_failover() -> None:
    """Patrol passed an explicit MissionV1 — the mission_id appears in the failover ledger entry."""
    packets = _load_fixture()
    dji_real = MavicBackend(transport=_FakeFixtureTransport(packets))
    mav_mock = _make_mavsdk_mock()
    ledger = _CapturingLedger()
    adapter = MavicAdapter(
        primary=dji_real,
        fallback=mav_mock,
        ledger=ledger,
    )

    await adapter.connect()
    await adapter.takeoff(alt_m=30.0)
    mission = MissionV1(
        metadata=MissionMetadata(mission_id="replay_test_mission", ranch_id="ranch_a"),
        waypoints=[Waypoint(lat=34.124, lon=-106.567, alt_m=30.0)],
    )
    await adapter.patrol_mission(mission)

    failovers = [e for e in ledger.events if e["kind"] == "adapter.failover"]
    assert len(failovers) == 1
    assert failovers[0]["data"]["mission_id"] == "replay_test_mission"


@pytest.mark.asyncio
async def test_replay_deterministic_three_runs() -> None:
    """Three replays with identical fixture + fixed ts → identical ledger ordering."""
    packets = _load_fixture()
    runs: list[list[str]] = []
    for _ in range(3):
        dji_real = MavicBackend(transport=_FakeFixtureTransport(packets))
        mav_mock = _make_mavsdk_mock()
        ledger = _CapturingLedger()
        adapter = MavicAdapter(
            primary=dji_real,
            fallback=mav_mock,
            ledger=ledger,
            ts_provider=lambda: 9.0,
        )
        await adapter.connect()
        await adapter.takeoff(alt_m=30.0)
        await adapter.patrol([Waypoint(lat=34.124, lon=-106.567, alt_m=30.0)])
        await adapter.return_to_home()
        runs.append([e["kind"] for e in ledger.events])

    assert runs[0] == runs[1] == runs[2]
