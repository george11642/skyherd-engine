"""Tests for :class:`~skyherd.drone.mavic_adapter.MavicAdapter`.

Both legs are mocked (``AsyncMock`` implementing the ``DroneBackend`` ABC)
so no real network, no DJI SDK, no MAVSDK binary is required.

Coverage target for ``src/skyherd/drone/mavic_adapter.py`` is ≥ 85 %.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from skyherd.drone.interface import (
    DroneError,
    DroneState,
    DroneUnavailable,
    Waypoint,
)
from skyherd.drone.mavic_adapter import MavicAdapter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_leg(
    *,
    connect_ok: bool = True,
    connect_exc: Exception | None = None,
    state: DroneState | None = None,
) -> MagicMock:
    """Construct an AsyncMock implementing the DroneBackend surface."""
    leg = MagicMock()
    if connect_exc is not None:
        leg.connect = AsyncMock(side_effect=connect_exc)
    elif connect_ok:
        leg.connect = AsyncMock()
    else:
        leg.connect = AsyncMock(side_effect=DroneUnavailable("leg unavailable"))
    leg.takeoff = AsyncMock()
    leg.patrol = AsyncMock()
    leg.return_to_home = AsyncMock()
    leg.play_deterrent = AsyncMock()
    leg.get_thermal_clip = AsyncMock(return_value=Path("/tmp/thermal.png"))
    leg.state = AsyncMock(return_value=state or DroneState(battery_pct=90.0))
    leg.disconnect = AsyncMock()
    return leg


class _FakeLedger:
    """Minimal Ledger stub that captures appended events."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    def append(self, *, kind: str, data: dict) -> None:
        self.events.append({"kind": kind, "data": data})


# ---------------------------------------------------------------------------
# Connect-time selection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_prefers_dji_when_available() -> None:
    ledger = _FakeLedger()
    dji = _make_leg(connect_ok=True)
    mav = _make_leg(connect_ok=True)
    adapter = MavicAdapter(
        primary=dji,
        fallback=mav,
        ledger=ledger,
        ts_provider=lambda: 1_700_000_000.0,
    )

    await adapter.connect()

    assert adapter.active_leg == "dji"
    dji.connect.assert_awaited_once()
    mav.connect.assert_not_awaited()
    assert ledger.events[0]["kind"] == "adapter.leg_selected"
    assert ledger.events[0]["data"]["leg"] == "dji"
    assert ledger.events[0]["data"]["ts"] == 1_700_000_000.0


@pytest.mark.asyncio
async def test_connect_falls_back_to_mavsdk_when_dji_unreachable() -> None:
    ledger = _FakeLedger()
    dji = _make_leg(connect_exc=DroneUnavailable("companion app not reachable"))
    mav = _make_leg(connect_ok=True)
    adapter = MavicAdapter(primary=dji, fallback=mav, ledger=ledger)

    await adapter.connect()

    assert adapter.active_leg == "mavsdk"
    mav.connect.assert_awaited_once()
    assert ledger.events[0]["data"]["leg"] == "mavsdk"
    assert "dji_error" in ledger.events[0]["data"]


@pytest.mark.asyncio
async def test_connect_raises_when_both_legs_fail() -> None:
    ledger = _FakeLedger()
    dji = _make_leg(connect_exc=DroneUnavailable("dji down"))
    mav = _make_leg(connect_exc=DroneUnavailable("mavsdk down"))
    adapter = MavicAdapter(primary=dji, fallback=mav, ledger=ledger)

    with pytest.raises(DroneUnavailable) as excinfo:
        await adapter.connect()

    assert "dji" in str(excinfo.value)
    assert "mavsdk" in str(excinfo.value)
    assert adapter.active_leg is None
    assert any(e["kind"] == "adapter.both_legs_failed" for e in ledger.events)


@pytest.mark.asyncio
async def test_connect_timeout_triggers_fallback() -> None:
    """A hanging DJI connect is timed out and fallback is used."""

    async def _hang() -> None:
        await asyncio.sleep(10.0)

    dji = MagicMock()
    dji.connect = AsyncMock(side_effect=_hang)
    dji.disconnect = AsyncMock()
    mav = _make_leg(connect_ok=True)
    adapter = MavicAdapter(
        primary=dji,
        fallback=mav,
        connect_timeout_s=0.05,
    )

    await adapter.connect()
    assert adapter.active_leg == "mavsdk"


# ---------------------------------------------------------------------------
# Actuator delegation + failover
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_takeoff_delegates_to_active_leg() -> None:
    dji = _make_leg()
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav)

    await adapter.connect()
    await adapter.takeoff(alt_m=15.0)

    dji.takeoff.assert_awaited_once_with(alt_m=15.0)
    mav.takeoff.assert_not_awaited()


@pytest.mark.asyncio
async def test_takeoff_failover_mid_mission() -> None:
    ledger = _FakeLedger()
    dji = _make_leg()
    dji.takeoff = AsyncMock(side_effect=DroneError("signal_lost"))
    mav = _make_leg()
    adapter = MavicAdapter(
        primary=dji,
        fallback=mav,
        ledger=ledger,
        ts_provider=lambda: 42.0,
    )

    await adapter.connect()
    await adapter.takeoff(alt_m=10.0)

    assert adapter.active_leg == "mavsdk"
    assert adapter.failover_count == 1
    mav.takeoff.assert_awaited_once_with(alt_m=10.0)

    failover_events = [e for e in ledger.events if e["kind"] == "adapter.failover"]
    assert len(failover_events) == 1
    assert failover_events[0]["data"]["from_leg"] == "dji"
    assert failover_events[0]["data"]["to_leg"] == "mavsdk"
    assert failover_events[0]["data"]["reason"] == "signal_lost"
    assert failover_events[0]["data"]["ts"] == 42.0


@pytest.mark.asyncio
async def test_patrol_failover_preserves_waypoints() -> None:
    dji = _make_leg()
    dji.patrol = AsyncMock(side_effect=DroneError("fault"))
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav)
    await adapter.connect()

    wps = [Waypoint(lat=34.1, lon=-106.1, alt_m=30.0)]
    await adapter.patrol(wps)

    # Fallback leg received exactly the same waypoints.
    mav.patrol.assert_awaited_once()
    call_args = mav.patrol.await_args
    assert call_args.kwargs["waypoints"] == wps
    assert adapter.failover_count == 1


@pytest.mark.asyncio
async def test_both_legs_fail_in_takeoff_raises() -> None:
    dji = _make_leg()
    dji.takeoff = AsyncMock(side_effect=DroneError("dji ko"))
    mav = _make_leg()
    mav.takeoff = AsyncMock(side_effect=DroneError("mavsdk ko"))
    adapter = MavicAdapter(primary=dji, fallback=mav)
    await adapter.connect()

    with pytest.raises(DroneError) as excinfo:
        await adapter.takeoff(alt_m=5.0)

    msg = str(excinfo.value)
    assert "dji" in msg
    assert "mavsdk" in msg


@pytest.mark.asyncio
async def test_failover_count_toggles_and_is_monotonic() -> None:
    dji = _make_leg()
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav)
    await adapter.connect()

    # First failure: dji -> mavsdk
    dji.takeoff = AsyncMock(side_effect=DroneError("e1"))
    await adapter.takeoff(alt_m=5.0)
    assert adapter.active_leg == "mavsdk"
    assert adapter.failover_count == 1

    # Second failure: mavsdk -> dji.  Swap takeoff mocks so new dji succeeds.
    dji.takeoff = AsyncMock()
    mav.takeoff = AsyncMock(side_effect=DroneError("e2"))
    await adapter.takeoff(alt_m=6.0)
    assert adapter.active_leg == "dji"
    assert adapter.failover_count == 2


@pytest.mark.asyncio
async def test_disconnect_closes_both_legs() -> None:
    dji = _make_leg()
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav)
    await adapter.connect()

    await adapter.disconnect()

    dji.disconnect.assert_awaited_once()
    mav.disconnect.assert_awaited_once()
    assert adapter.active_leg is None


@pytest.mark.asyncio
async def test_get_thermal_clip_failover_returns_path() -> None:
    dji = _make_leg()
    dji.get_thermal_clip = AsyncMock(side_effect=DroneError("clip fail"))
    mav = _make_leg()
    mav.get_thermal_clip = AsyncMock(return_value=Path("/tmp/fallback.png"))
    adapter = MavicAdapter(primary=dji, fallback=mav)
    await adapter.connect()

    path = await adapter.get_thermal_clip(duration_s=2.0)
    assert path == Path("/tmp/fallback.png")


@pytest.mark.asyncio
async def test_state_failover_returns_snapshot() -> None:
    dji = _make_leg()
    dji.state = AsyncMock(side_effect=DroneError("state fail"))
    mav = _make_leg(state=DroneState(battery_pct=55.0, mode="AUTO"))
    adapter = MavicAdapter(primary=dji, fallback=mav)
    await adapter.connect()

    s = await adapter.state()
    assert s.battery_pct == 55.0
    assert s.mode == "AUTO"
    assert adapter.active_leg == "mavsdk"


@pytest.mark.asyncio
async def test_play_deterrent_failover() -> None:
    dji = _make_leg()
    dji.play_deterrent = AsyncMock(side_effect=DroneError("deterrent ko"))
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav)
    await adapter.connect()

    await adapter.play_deterrent(tone_hz=10000, duration_s=3.0)
    mav.play_deterrent.assert_awaited_once_with(tone_hz=10000, duration_s=3.0)


@pytest.mark.asyncio
async def test_return_to_home_delegates() -> None:
    dji = _make_leg()
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav)
    await adapter.connect()

    await adapter.return_to_home()
    dji.return_to_home.assert_awaited_once()
    mav.return_to_home.assert_not_awaited()


# ---------------------------------------------------------------------------
# Factory + ledger-less operation
# ---------------------------------------------------------------------------


def test_factory_registers_mavic_as_adapter() -> None:
    from skyherd.drone.interface import get_backend
    from skyherd.drone.mavic import MavicBackend

    assert isinstance(get_backend("mavic"), MavicAdapter)
    assert isinstance(get_backend("mavic_direct"), MavicBackend)


@pytest.mark.asyncio
async def test_adapter_without_ledger_still_failovers() -> None:
    """No attestation required for adapter to function."""
    dji = _make_leg()
    dji.takeoff = AsyncMock(side_effect=DroneError("x"))
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav, ledger=None)
    await adapter.connect()
    await adapter.takeoff(alt_m=5.0)
    assert adapter.failover_count == 1


@pytest.mark.asyncio
async def test_ledger_failure_does_not_break_flight_path() -> None:
    """A broken ledger must never kill the drone path."""

    class _BadLedger:
        def append(self, **_kw):  # noqa: ANN003
            raise RuntimeError("ledger corrupt")

    dji = _make_leg()
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav, ledger=_BadLedger())

    # connect still succeeds even though ledger.append raises
    await adapter.connect()
    assert adapter.active_leg == "dji"


@pytest.mark.asyncio
async def test_invoke_before_connect_raises() -> None:
    adapter = MavicAdapter(primary=_make_leg(), fallback=_make_leg())
    with pytest.raises(DroneUnavailable):
        await adapter.takeoff(alt_m=5.0)


@pytest.mark.asyncio
async def test_deterministic_ts_in_ledger_entries() -> None:
    """Injected ts_provider flows through to every ledger append."""
    ledger = _FakeLedger()
    dji = _make_leg()
    dji.takeoff = AsyncMock(side_effect=DroneError("one-shot"))
    mav = _make_leg()

    ticks = iter([100.0, 200.0, 300.0, 400.0])
    adapter = MavicAdapter(
        primary=dji,
        fallback=mav,
        ledger=ledger,
        ts_provider=lambda: next(ticks),
    )

    await adapter.connect()  # tick 100
    await adapter.takeoff(alt_m=5)  # tick 200 on failover
    tss = [e["data"]["ts"] for e in ledger.events]
    assert tss == [100.0, 200.0]


@pytest.mark.asyncio
async def test_mission_id_monotonic_across_calls() -> None:
    dji = _make_leg()
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav)
    await adapter.connect()

    id1 = adapter._next_mission_id()
    id2 = adapter._next_mission_id()
    id3 = adapter._next_mission_id()

    assert id1 != id2 != id3
    assert id1 == "mission_00000001"
    assert id2 == "mission_00000002"
    assert id3 == "mission_00000003"


@pytest.mark.asyncio
async def test_disconnect_swallows_leg_errors() -> None:
    dji = _make_leg()
    dji.disconnect = AsyncMock(side_effect=RuntimeError("dji close fail"))
    mav = _make_leg()
    adapter = MavicAdapter(primary=dji, fallback=mav)
    await adapter.connect()

    # Should not raise
    await adapter.disconnect()
    mav.disconnect.assert_awaited_once()
