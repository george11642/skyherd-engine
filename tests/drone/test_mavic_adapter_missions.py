"""Integration: MavicAdapter.patrol now builds MissionV1 internally."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from skyherd.drone.interface import DroneState, Waypoint
from skyherd.drone.mavic_adapter import MavicAdapter
from skyherd.drone.mission_schema import MissionMetadata, MissionV1


def _make_leg() -> MagicMock:
    leg = MagicMock()
    leg.connect = AsyncMock()
    leg.takeoff = AsyncMock()
    leg.patrol = AsyncMock()
    leg.return_to_home = AsyncMock()
    leg.play_deterrent = AsyncMock()
    leg.get_thermal_clip = AsyncMock(return_value=Path("/tmp/t.png"))
    leg.state = AsyncMock(return_value=DroneState(battery_pct=80.0))
    leg.disconnect = AsyncMock()
    return leg


class _FakeLedger:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def append(self, *, kind: str, data: dict) -> None:
        self.events.append({"kind": kind, "data": data})


@pytest.mark.asyncio
async def test_patrol_forwards_waypoints_to_active_leg() -> None:
    dji = _make_leg()
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav, ranch_id="ranch_a")
    await adapter.connect()

    wps = [
        Waypoint(lat=34.1, lon=-106.1, alt_m=30.0),
        Waypoint(lat=34.2, lon=-106.2, alt_m=30.0),
    ]
    await adapter.patrol(wps)

    dji.patrol.assert_awaited_once()
    kwargs = dji.patrol.await_args.kwargs
    assert kwargs["waypoints"] == wps


@pytest.mark.asyncio
async def test_patrol_mission_with_handcrafted_missionv1() -> None:
    dji = _make_leg()
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav)
    await adapter.connect()

    mission = MissionV1(
        metadata=MissionMetadata(mission_id="handcrafted_001", ranch_id="ranch_a"),
        waypoints=[Waypoint(lat=1.0, lon=2.0, alt_m=3.0)],
    )
    await adapter.patrol_mission(mission)

    dji.patrol.assert_awaited_once()
    kwargs = dji.patrol.await_args.kwargs
    assert len(kwargs["waypoints"]) == 1
    assert kwargs["waypoints"][0].lat == 1.0


@pytest.mark.asyncio
async def test_mission_id_is_monotonic_across_patrol_calls() -> None:
    dji = _make_leg()
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav)
    await adapter.connect()

    wps = [Waypoint(lat=0.0, lon=0.0, alt_m=5.0)]
    id_before = adapter._next_mission_id()
    await adapter.patrol(wps)
    await adapter.patrol(wps)
    id_after = adapter._next_mission_id()

    # Counter increments monotonically across both internal builds and
    # external _next_mission_id calls.
    assert id_before != id_after
    # Two patrol calls in between consumed two ids.
    # id_before -> 00000001; after two patrol builds -> 00000002, 00000003;
    # next -> 00000004.
    assert id_before == "mission_00000001"
    assert id_after == "mission_00000004"


@pytest.mark.asyncio
async def test_patrol_mission_failover_includes_mission_id_in_ledger() -> None:
    from skyherd.drone.interface import DroneError

    dji = _make_leg()
    dji.patrol = AsyncMock(side_effect=DroneError("dji lost mid-patrol"))
    mav = _make_leg()
    ledger = _FakeLedger()
    adapter = MavicAdapter(
        primary=dji,
        fallback=mav,
        ledger=ledger,
        ts_provider=lambda: 7.0,
    )
    await adapter.connect()

    mission = MissionV1(
        metadata=MissionMetadata(
            mission_id="tracked_mission_42",
            ranch_id="ranch_a",
        ),
        waypoints=[Waypoint(lat=0.0, lon=0.0, alt_m=5.0)],
    )
    await adapter.patrol_mission(mission)

    failovers = [e for e in ledger.events if e["kind"] == "adapter.failover"]
    assert len(failovers) == 1
    assert failovers[0]["data"]["mission_id"] == "tracked_mission_42"
    assert failovers[0]["data"]["method"] == "patrol"
