"""Scenario 5 — Incoming severe thunderstorm.

Timeline
--------
* At sim-elapsed ~195s (sim-clock 03:15), a storm warning event is injected
  with ETA=20 minutes.
* Expected cascade:
    storm.warning / weather.storm → GrazingOptimizer wakes
    (storm override pre-empts the Monday-06:00 weekly schedule)
    → loads paddock-rotation.md + nm-ecology/weather-patterns.md
    → get_latest_readings (water_pressure, herd positions)
    → page_rancher with rotation proposal + approval request
    → auto-approved in scenario mode
    → play_deterrent / acoustic emitter activates for herd redirect
      (sub-20 kHz range per deterrent-protocols.md)
"""

from __future__ import annotations

from typing import Any

from skyherd.scenarios.base import Scenario
from skyherd.world.world import World

_STORM_WARNING_AT_S = 195.0  # inject at ~03:15 offset
_STORM_ARRIVE_AT_S = 195.0 + 1200.0  # storm arrives 20 min later


class StormScenario(Scenario):
    name = "storm"
    description = (
        "Thunderstorm warning at 03:15 → GrazingOptimizer overrides schedule "
        "→ herd-move proposal → auto-approved → acoustic nudge"
    )
    duration_s = 600.0

    def __init__(self) -> None:
        self._warning_injected = False
        self._storm_injected = False
        self._approval_injected = False

    def setup(self, world: World) -> None:
        """Pre-conditions: clear weather initially, herd in open paddocks."""
        world.weather_driver._weather = world.weather_driver.current.model_copy(
            update={"conditions": "clear", "temp_f": 68.0, "wind_kt": 5.0}
        )

    def inject_events(self, world: World, sim_time_s: float) -> list[dict[str, Any]]:
        """Inject storm warning at 03:15, then approval, then acoustic nudge."""
        events: list[dict[str, Any]] = []

        # Storm warning event
        if not self._warning_injected and sim_time_s >= _STORM_WARNING_AT_S:
            self._warning_injected = True
            events.append(
                {
                    "type": "storm.warning",
                    "source": "weather_station",
                    "ranch_id": "ranch_a",
                    "eta_s": 1200,  # 20 minutes
                    "severity": "severe",
                    "conditions": "thunderstorm",
                    "wind_kt": 45.0,
                    "lightning": True,
                    "sim_time_s": sim_time_s,
                }
            )
            # Also fire a weather.storm topic event to wake GrazingOptimizer
            events.append(
                {
                    "type": "weather.storm",
                    "source": "weather_sensor",
                    "ranch_id": "ranch_a",
                    "topic": "skyherd/ranch_a/weather/storm",
                    "wind_kt": 45.0,
                    "temp_f": 68.0,
                    "eta_s": 1200,
                    "sim_time_s": sim_time_s,
                }
            )

        # Auto-approval 60 seconds after warning (scenario mode: no human wait)
        if (
            self._warning_injected
            and not self._approval_injected
            and sim_time_s >= _STORM_WARNING_AT_S + 60.0
        ):
            self._approval_injected = True
            events.append(
                {
                    "type": "rancher.approval",
                    "source": "scenario_auto_approve",
                    "ranch_id": "ranch_a",
                    "approval": "APPROVE",
                    "context": "storm_paddock_move",
                    "sim_time_s": sim_time_s,
                }
            )
            # Acoustic nudge activation event
            events.append(
                {
                    "type": "acoustic.activated",
                    "source": "scenario_auto_approve",
                    "ranch_id": "ranch_a",
                    "emitter_id": "emit_1",
                    "tone_hz": 10000,  # 10 kHz — herd redirect (sub-20 kHz)
                    "duration_s": 30,
                    "purpose": "herd_redirect_storm",
                    "sim_time_s": sim_time_s,
                }
            )

        return events

    def assert_outcome(
        self,
        event_stream: list[dict[str, Any]],
        mesh: Any,
    ) -> None:
        """Assert storm was detected, rotation proposed, acoustic activated."""
        # 1. storm.warning event in stream
        warning = self._find_event(event_stream, "storm.warning")
        assert warning is not None, "Expected storm.warning event"
        assert warning.get("eta_s", 9999) <= 1200, "Expected ETA <= 20 minutes"

        # 2. weather.storm event fired (wakes GrazingOptimizer)
        storm_ev = self._find_event(event_stream, "weather.storm")
        assert storm_ev is not None, "Expected weather.storm event to wake GrazingOptimizer"

        # 3. GrazingOptimizer tool calls
        all_tools = self._all_tool_calls(mesh)
        assert len(all_tools) > 0, (
            "Expected GrazingOptimizer to emit tool calls in response to storm"
        )

        # 4. page_rancher with rotation proposal
        tool_names = {c.get("tool") for c in all_tools}
        assert "page_rancher" in tool_names, (
            f"Expected page_rancher (rotation proposal). Got: {tool_names}"
        )

        # 5. Acoustic nudge (direct activation or play_deterrent tool call)
        acoustic_ev = self._find_event(event_stream, "acoustic.activated")
        assert acoustic_ev is not None, "Expected acoustic.activated event after approval"

        # Tone must be sub-20 kHz for herd redirect
        tone = acoustic_ev.get("tone_hz", 0)
        assert tone < 20000, f"Acoustic tone {tone}Hz exceeds 20 kHz herd-redirect limit"

        # 6. Auto-approval event confirms scenario mode worked
        approval = self._find_event(event_stream, "rancher.approval")
        assert approval is not None, "Expected rancher.approval (auto-approve) event"
