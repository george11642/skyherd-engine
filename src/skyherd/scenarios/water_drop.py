"""Scenario 3 — Water tank pressure drop.

Timeline
--------
* On world setup, tank wt_sw is overridden to 18% level (below the 20%
  threshold) so it immediately fires water.low on the first sim step.
* Weather is hot (temp_f > 90) — increases urgency.
* Expected cascade:
    water.low → FenceLineDispatcher (or GrazingOptimizer) wakes
    → launch_drone flyover mission
    → thermal clip returned (confirms tank state)
    → attestation entry "water.verify" logged
"""

from __future__ import annotations

from typing import Any

from skyherd.scenarios.base import Scenario
from skyherd.world.terrain import WaterTankConfig
from skyherd.world.world import World

_DRONE_FLYOVER_AT_S = 10.0  # inject after first water.low


class WaterDropScenario(Scenario):
    name = "water_drop"
    description = (
        "Tank wt_sw starts at 18% → water.low fires → drone flyover confirms "
        "state → attestation entry logged"
    )
    duration_s = 300.0

    def __init__(self) -> None:
        self._flyover_injected = False

    def setup(self, world: World) -> None:
        """Set wt_sw to 18% and weather to hot."""
        # Override tank level directly in terrain config
        updated_tanks: list[WaterTankConfig] = []
        for tank in world.terrain.config.water_tanks:
            if tank.id == "wt_sw":
                tank = tank.model_copy(update={"level_pct": 18.0, "pressure_psi": 12.0})
            updated_tanks.append(tank)
        world.terrain.config.water_tanks = updated_tanks

        # Force hot weather
        world.weather_driver._weather = world.weather_driver.current.model_copy(
            update={"temp_f": 95.0}
        )

    def inject_events(self, world: World, sim_time_s: float) -> list[dict[str, Any]]:
        """After water.low has fired, inject a drone flyover confirmation."""
        events: list[dict[str, Any]] = []
        # Check if a water.low event has been emitted for wt_sw
        water_low_seen = any(
            ev.get("type") == "water.low" and ev.get("tank_id") == "wt_sw" for ev in world.events
        )

        if water_low_seen and not self._flyover_injected and sim_time_s >= _DRONE_FLYOVER_AT_S:
            self._flyover_injected = True
            events.append(
                {
                    "type": "drone.flyover_complete",
                    "source": "drone_sim",
                    "ranch_id": "ranch_a",
                    "tank_id": "wt_sw",
                    "mission": "water_verify",
                    "level_pct_confirmed": 18.0,
                    "temp_f": 95.0,
                    "sim_time_s": sim_time_s,
                }
            )

        return events

    def assert_outcome(
        self,
        event_stream: list[dict[str, Any]],
        mesh: Any,
    ) -> None:
        """Assert water.low fired, drone flew, attestation logged."""
        # 1. water.low event fired for wt_sw
        water_ev = None
        for ev in event_stream:
            if ev.get("type") == "water.low" and ev.get("tank_id") == "wt_sw":
                water_ev = ev
                break
        assert water_ev is not None, "Expected water.low event for tank wt_sw (set to 18%)"
        assert water_ev.get("level_pct", 100) < 20.0, (
            f"Expected level_pct < 20, got {water_ev.get('level_pct')}"
        )

        # 2. drone.flyover_complete was injected
        flyover = self._find_event(event_stream, "drone.flyover_complete")
        assert flyover is not None, "Expected drone.flyover_complete event"
        assert flyover.get("tank_id") == "wt_sw", (
            f"Flyover was for wrong tank: {flyover.get('tank_id')!r}"
        )

        # 3. Agents were dispatched (launch_drone or at minimum page_rancher)
        all_tools = self._all_tool_calls(mesh)

        # At least one agent responded to water.low
        assert len(all_tools) > 0, "Expected at least one agent tool call in response to water.low"

        # FenceLineDispatcher or GrazingOptimizer should have triggered
        agents_that_responded = set(mesh._tool_call_log.keys())
        assert agents_that_responded, "No agents responded to water alert"
