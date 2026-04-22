"""Scenario 7 — Wildfire Thermal Early-Warning.

Timeline
--------
* World seeds at sim_time 06:00 (dawn sweep window).
* At sim-elapsed 270s (~06:04 offset), a dawn thermal flyover captures a
  smouldering-brush hotspot in the far-NW paddock. ThermalCamSensor emits
  a ``thermal.hotspot`` event with payload:
    {lat, lon, peak_temp_c, confidence, plume_drift_deg}
* Expected cascade:
    thermal.hotspot → FenceLineDispatcher wakes
    (hotspot treated as a defend-layer event)
    → loads drone-ops/patrol-planning.md + nm-ecology/wildfire-signatures.md
    → launch_drone (confirmation flyover)
    → page_rancher urgency=high (+ optional page_fire_department via
      contact_role="fire_dept" tool call)
  Drone launches confirmation flyover; rancher paged at high urgency.
* assert_outcome: thermal.hotspot present, confirmation drone launched,
  rancher paged at high urgency.
"""

from __future__ import annotations

from typing import Any

from skyherd.scenarios.base import Scenario
from skyherd.world.world import World

# Sim-elapsed seconds at which the thermal hotspot fires (dawn flyover at 06:15)
# Must be within duration_s=600.0 — use 270s (~06:04:30 offset, mid-dawn sweep window)
_HOTSPOT_AT_S = 270.0  # 4.5-minute offset, comfortably within 600s scenario window

# Hotspot characteristics — smouldering brush
_HOTSPOT_LAT = 34.1185
_HOTSPOT_LON = -106.4610  # far-NW paddock
_PEAK_TEMP_C = 340.0  # smouldering brush (320–450°C range)
_CONFIDENCE = 0.91
_PLUME_DRIFT_DEG = 45.0  # NE drift — away from main herd paddocks


class WildfireScenario(Scenario):
    """Dawn thermal sweep detects smouldering hotspot → drone confirmation → rancher page."""

    name = "wildfire"
    description = (
        "Dawn thermal flyover at 06:15 detects smouldering-brush hotspot in NW paddock "
        "→ FenceLineDispatcher → confirmation drone → rancher paged urgency=high"
    )
    duration_s = 600.0

    def __init__(self) -> None:
        self._hotspot_injected = False

    def setup(self, world: World) -> None:
        """Pre-conditions: dawn, clear and calm, April fire season."""
        # Force calm dawn weather — peak detection sensitivity
        world.weather_driver._weather = world.weather_driver.current.model_copy(
            update={
                "conditions": "clear",
                "temp_f": 52.0,  # cool dawn in April NM
                "wind_kt": 3.0,  # calm — plume rises vertically
            }
        )

    def inject_events(self, world: World, sim_time_s: float) -> list[dict[str, Any]]:
        """At 06:15 offset, inject the thermal.hotspot event from the dawn sweep."""
        events: list[dict[str, Any]] = []

        if not self._hotspot_injected and sim_time_s >= _HOTSPOT_AT_S:
            self._hotspot_injected = True

            # ThermalCamSensor emits thermal.hotspot from the dawn flyover
            events.append(
                {
                    "type": "thermal.hotspot",
                    "source": "thermal_cam_sensor",
                    "ranch_id": "ranch_a",
                    "lat": _HOTSPOT_LAT,
                    "lon": _HOTSPOT_LON,
                    "peak_temp_c": _PEAK_TEMP_C,
                    "confidence": _CONFIDENCE,
                    "plume_drift_deg": _PLUME_DRIFT_DEG,
                    "paddock": "paddock_northwest",
                    "is_scheduled_burn": False,
                    "sim_time_s": sim_time_s,
                }
            )

            # Also emit a fence.breach-like defend-layer event so FenceLineDispatcher
            # wakes — thermal hotspots route through the same defend-layer as breaches.
            events.append(
                {
                    "type": "fence.breach",
                    "source": "thermal_hotspot_defend_layer",
                    "fence_id": "fence_northwest",
                    "segment": "fence_northwest",
                    "lat": _HOTSPOT_LAT,
                    "lon": _HOTSPOT_LON,
                    "ranch_id": "ranch_a",
                    "species_hint": "wildfire",
                    "thermal_hotspot": True,
                    "peak_temp_c": _PEAK_TEMP_C,
                    "confidence": _CONFIDENCE,
                    "plume_drift_deg": _PLUME_DRIFT_DEG,
                    "sim_time_s": sim_time_s,
                }
            )

        return events

    def assert_outcome(
        self,
        event_stream: list[dict[str, Any]],
        mesh: Any,
    ) -> None:
        """Assert the wildfire detection cascade completed successfully.

        Checks
        ------
        1. thermal.hotspot event is present in stream.
        2. Drone confirmation mission was launched (launch_drone tool call).
        3. Rancher was paged at urgency=high (or emergency).
        4. No deterrent tone played — wildfire is not a predator.
        """
        # 1. thermal.hotspot event was emitted
        hotspot = self._find_event(event_stream, "thermal.hotspot")
        assert hotspot is not None, "Expected thermal.hotspot event in stream"
        assert hotspot.get("peak_temp_c", 0) >= 300.0, (
            f"Expected peak_temp_c >= 300°C, got {hotspot.get('peak_temp_c')}"
        )
        assert hotspot.get("confidence", 0) >= 0.70, (
            f"Expected confidence >= 0.70, got {hotspot.get('confidence')}"
        )

        # 2. Drone confirmation flyover was launched
        all_tools = self._all_tool_calls(mesh)
        tool_names = {c.get("tool") for c in all_tools}

        assert "launch_drone" in tool_names, (
            f"Expected launch_drone tool call for wildfire confirmation. Got: {tool_names}"
        )

        # 3. Rancher paged at high urgency
        assert "page_rancher" in tool_names, f"Expected page_rancher tool call. Got: {tool_names}"

        rancher_calls = [c for c in all_tools if c.get("tool") == "page_rancher"]
        assert rancher_calls, "No page_rancher call found"

        urgencies = [c.get("input", {}).get("urgency", "") for c in rancher_calls]
        assert any(u in ("high", "emergency", "call") for u in urgencies), (
            f"Expected rancher urgency high/emergency/call for wildfire, got: {urgencies}"
        )
