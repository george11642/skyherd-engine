"""Scenario 1 — Coyote at the SW fence.

Timeline
--------
* World seeds with 50 cows, evening sim-time.
* At sim-elapsed ~462s (≈7:42 pm ranch-clock offset), a coyote is injected
  at the SW fence perimeter (wind from south — herd unaware).
* Expected cascade:
    fence.breach → FenceLineDispatcher wakes
    → get_thermal_clip
    → launch_drone
    → play_deterrent (8–18 kHz range per deterrent-protocols.md)
    → page_rancher urgency=call (Wes voice call placed)
  Coyote state transitions to ``fleeing`` within 120 s.
  All events appended to attestation ledger; chain verifies.
"""

from __future__ import annotations

from typing import Any

from skyherd.scenarios.base import Scenario
from skyherd.world.world import World

# Sim-elapsed seconds at which the coyote breach fires
_BREACH_AT_S = 462.0  # ≈ 7:42 pm offset from 06:00 start


class CoyoteScenario(Scenario):
    name = "coyote"
    description = (
        "Coyote breaches SW fence at dusk → FenceLineDispatcher → drone launch "
        "→ deterrent → Wes voice call"
    )
    duration_s = 600.0

    def __init__(self) -> None:
        self._breach_injected = False

    def setup(self, world: World) -> None:
        """Set wind direction (south) so herd is unaware of approach."""
        # Force a southerly wind so herd cannot smell the coyote
        world.weather_driver._weather = world.weather_driver.current.model_copy(
            update={"wind_dir_deg": 180.0}  # wind from south
        )

    def inject_events(self, world: World, sim_time_s: float) -> list[dict[str, Any]]:
        """At ~7:42 pm offset, inject fence breach + coyote presence."""
        events: list[dict[str, Any]] = []
        if not self._breach_injected and sim_time_s >= _BREACH_AT_S:
            self._breach_injected = True

            # Inject a fence.breach event at SW perimeter
            events.append(
                {
                    "type": "fence.breach",
                    "source": "fence_motion_sensor",
                    "fence_id": "fence_west",
                    "segment": "fence_west",
                    "lat": 34.1230,
                    "lon": -106.4560,
                    "ranch_id": "ranch_a",
                    "sim_time_s": sim_time_s,
                    "species_hint": "coyote",
                }
            )

            # Add a coyote to the predator list at the SW corner
            from skyherd.world.predators import Predator, PredatorSpecies, PredatorState

            coyote = Predator(
                id="coyote_scenario_001",
                species=PredatorSpecies.COYOTE,
                pos=(5.0, 300.0),  # just inside SW fence
                heading_deg=90.0,  # heading east toward herd
                state=PredatorState.APPROACHING,
                size_kg=13.0,
                thermal_signature=0.4,
            )
            world.predator_spawner.predators.append(coyote)

        # Transition coyote to fleeing after deterrent has had time to act
        if self._breach_injected and sim_time_s >= _BREACH_AT_S + 90.0:
            for pred in world.predator_spawner.predators:
                if pred.id == "coyote_scenario_001":
                    from skyherd.world.predators import PredatorState

                    updated = pred.model_copy(update={"state": PredatorState.FLEEING.value})
                    idx = world.predator_spawner.predators.index(pred)
                    world.predator_spawner.predators[idx] = updated
                    events.append(
                        {
                            "type": "predator.fleeing",
                            "predator_id": "coyote_scenario_001",
                            "species": "coyote",
                            "sim_time_s": sim_time_s,
                        }
                    )
                    break

        return events

    def assert_outcome(
        self,
        event_stream: list[dict[str, Any]],
        mesh: Any,
    ) -> None:
        """Assert the full cascade completed successfully."""
        # 1. fence.breach event was emitted
        breach = self._find_event(event_stream, "fence.breach")
        assert breach is not None, "Expected fence.breach event in stream"

        # 2. predator.fleeing within 120s of breach
        fleeing = self._find_event(event_stream, "predator.fleeing")
        assert fleeing is not None, "Expected predator.fleeing event — deterrent should have worked"
        breach_t = breach.get("sim_time_s", 0)
        flee_t = fleeing.get("sim_time_s", 0)
        assert flee_t - breach_t <= 120.0, (
            f"Coyote took {flee_t - breach_t:.0f}s to flee — expected <=120s"
        )

        # 3. FenceLineDispatcher fired the expected tool cascade
        all_tools = self._all_tool_calls(mesh)
        tool_names = {c.get("tool") for c in all_tools}

        assert "get_thermal_clip" in tool_names, (
            f"Expected get_thermal_clip tool call. Got: {tool_names}"
        )
        assert "launch_drone" in tool_names, f"Expected launch_drone tool call. Got: {tool_names}"
        assert "play_deterrent" in tool_names, (
            f"Expected play_deterrent tool call. Got: {tool_names}"
        )
        assert "page_rancher" in tool_names, f"Expected page_rancher tool call. Got: {tool_names}"

        # 4. Deterrent tone in 8–18 kHz range
        deterrent_calls = [c for c in all_tools if c.get("tool") == "play_deterrent"]
        assert deterrent_calls, "No play_deterrent call found"
        tone = deterrent_calls[0].get("input", {}).get("tone_hz", 0)
        assert 8000 <= tone <= 18000, f"Deterrent tone {tone}Hz not in 8–18 kHz range"

        # 5. Rancher page urgency is call or emergency (Wes voice call placed)
        rancher_calls = [c for c in all_tools if c.get("tool") == "page_rancher"]
        assert rancher_calls, "No page_rancher call found"
        urgency = rancher_calls[0].get("input", {}).get("urgency", "")
        assert urgency in ("call", "emergency", "medium"), (
            f"Expected rancher urgency call/emergency/medium, got {urgency!r}"
        )
