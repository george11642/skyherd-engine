"""FakeSITLBackend — deterministic DroneBackend that simulates connection loss.

Wraps :class:`skyherd.drone.stub.StubBackend` and lets tests inject a
:class:`~skyherd.drone.interface.DroneUnavailable` on takeoff, on the N-th
patrol call, or on return-to-home.  All hooks are deterministic — there is
no wall-clock state — so chaos-monkey failover tests remain reproducible
across replays.

Design
------
* Everything delegates to a real :class:`StubBackend`; the Fake only
  interposes on the methods that are being tested to fail.
* Counters are plain ints — resetting the backend is as simple as
  constructing a new instance.
* Implements the full :class:`DroneBackend` abstract surface so it can be
  passed wherever a real backend is expected.
"""

from __future__ import annotations

from pathlib import Path

from skyherd.drone.interface import DroneBackend, DroneState, DroneUnavailable, Waypoint
from skyherd.drone.stub import StubBackend

__all__ = ["FakeSITLBackend"]


class FakeSITLBackend(DroneBackend):
    """DroneBackend that injects DroneUnavailable on configured operations.

    Parameters
    ----------
    fail_on_takeoff:
        Raise :class:`DroneUnavailable` on the first :meth:`takeoff` call.
    fail_after_waypoints:
        Raise :class:`DroneUnavailable` on patrol when the Nth waypoint
        (0-indexed) is about to be sent.  ``None`` disables the hook.
    fail_on_return_to_home:
        Raise :class:`DroneUnavailable` on the first :meth:`return_to_home`
        call.
    """

    def __init__(
        self,
        *,
        fail_on_takeoff: bool = False,
        fail_after_waypoints: int | None = None,
        fail_on_return_to_home: bool = False,
    ) -> None:
        self._stub = StubBackend()
        self._fail_takeoff = fail_on_takeoff
        self._fail_after = fail_after_waypoints
        self._fail_rtl = fail_on_return_to_home
        self._patrol_waypoint_count = 0
        # Introspection hooks
        self.takeoff_calls = 0
        self.patrol_calls = 0
        self.rtl_calls = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        await self._stub.connect()

    async def disconnect(self) -> None:
        await self._stub.disconnect()

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def takeoff(self, alt_m: float = 30.0) -> None:
        self.takeoff_calls += 1
        if self._fail_takeoff:
            raise DroneUnavailable("FakeSITLBackend: takeoff injection failure")
        await self._stub.takeoff(alt_m=alt_m)

    async def patrol(self, waypoints: list[Waypoint]) -> None:
        self.patrol_calls += 1
        # Emulate per-waypoint execution; fail when we reach the configured index.
        executed: list[Waypoint] = []
        for wp in waypoints:
            if self._fail_after is not None and self._patrol_waypoint_count >= self._fail_after:
                raise DroneUnavailable(
                    f"FakeSITLBackend: patrol injection failure after {self._fail_after} waypoints"
                )
            executed.append(wp)
            self._patrol_waypoint_count += 1
        if executed:
            await self._stub.patrol(executed)

    async def return_to_home(self) -> None:
        self.rtl_calls += 1
        if self._fail_rtl:
            raise DroneUnavailable("FakeSITLBackend: return_to_home injection failure")
        await self._stub.return_to_home()

    async def play_deterrent(self, tone_hz: int = 12000, duration_s: float = 6.0) -> None:
        await self._stub.play_deterrent(tone_hz=tone_hz, duration_s=duration_s)

    async def get_thermal_clip(self, duration_s: float = 10.0) -> Path:
        return await self._stub.get_thermal_clip(duration_s=duration_s)

    async def state(self) -> DroneState:
        return await self._stub.state()
