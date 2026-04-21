"""Scenario 4 — Calving detected.

Timeline
--------
* One cow B007 is set to pregnancy_days_remaining=2 on world setup.
* At sim-elapsed ~120s (minute 2), pre-labor behavior markers are injected:
  - collar activity spike (isolation from herd, tail-flag via IMU)
  - trough-cam isolation sighting
* Expected cascade:
    collar.activity_spike → CalvingWatch wakes
    → get_latest_readings (collar IMU, last 20 points)
    → classify: pre-labor (2 days remaining, elevated activity)
    → page_rancher urgency=high (or call)
"""

from __future__ import annotations

from typing import Any

from skyherd.scenarios.base import Scenario
from skyherd.world.world import World

_PRELABOR_AT_S = 120.0  # inject pre-labor markers at 2 minutes


class CalvingScenario(Scenario):
    name = "calving"
    description = (
        "B007 (2 days from calving) shows pre-labor collar spike at minute 2 "
        "→ CalvingWatch wakes → page_rancher urgency=high"
    )
    duration_s = 600.0

    def __init__(self) -> None:
        self._prelabor_injected = False

    def setup(self, world: World) -> None:
        """Set B007 to pregnancy_days_remaining=2 (imminent calving)."""
        updated: list[Any] = []
        for cow in world.herd.cows:
            if cow.tag == "B007":
                cow = cow.model_copy(
                    update={
                        "pregnancy_days_remaining": 2,
                    }
                )
            updated.append(cow)
        world.herd.cows = updated

    def inject_events(
        self, world: World, sim_time_s: float
    ) -> list[dict[str, Any]]:
        """At minute 2, inject collar activity spike and isolation sighting."""
        events: list[dict[str, Any]] = []
        if not self._prelabor_injected and sim_time_s >= _PRELABOR_AT_S:
            self._prelabor_injected = True

            # Collar IMU spike — restlessness + isolation from herd
            events.append(
                {
                    "type": "collar.activity_spike",
                    "source": "collar_sensor",
                    "ranch_id": "ranch_a",
                    "cow_id": "cow_016",  # B007 index in 50-cow herd
                    "tag": "B007",
                    "imu_magnitude": 4.2,  # > 2.5 threshold = spike
                    "isolation_score": 0.85,  # isolated from herd centroid
                    "tail_flag": True,
                    "behavior": "pre-labor",
                    "pregnancy_days_remaining": 2,
                    "sim_time_s": sim_time_s,
                }
            )

            # Camera motion at a distant trough (cow isolating herself)
            events.append(
                {
                    "type": "camera.motion",
                    "source": "trough_cam",
                    "ranch_id": "ranch_a",
                    "trough_id": "trough_b",
                    "cow_tag": "B007",
                    "isolated": True,
                    "anomaly": True,
                    "sim_time_s": sim_time_s,
                }
            )

            # CalvingWatch-specific pre-labor classification event
            events.append(
                {
                    "type": "calving.prelabor",
                    "source": "calving_watch",
                    "ranch_id": "ranch_a",
                    "cow_tag": "B007",
                    "pregnancy_days_remaining": 2,
                    "confidence": 0.91,
                    "sim_time_s": sim_time_s,
                }
            )

        return events

    def assert_outcome(
        self,
        event_stream: list[dict[str, Any]],
        mesh: Any,
    ) -> None:
        """Assert CalvingWatch woke and paged rancher with high urgency."""
        # 1. collar.activity_spike was emitted for B007
        spike = None
        for ev in event_stream:
            if ev.get("type") == "collar.activity_spike" and ev.get("tag") == "B007":
                spike = ev
                break
        assert spike is not None, "Expected collar.activity_spike for cow B007"

        # 2. calving.prelabor event in stream
        prelabor = self._find_event(event_stream, "calving.prelabor")
        assert prelabor is not None, "Expected calving.prelabor event in stream"
        assert prelabor.get("cow_tag") == "B007", (
            f"Pre-labor event was for wrong cow: {prelabor.get('cow_tag')!r}"
        )

        # 3. CalvingWatch tool calls present
        all_tools = self._all_tool_calls(mesh)
        assert len(all_tools) > 0, "Expected CalvingWatch to emit tool calls"

        # 4. get_latest_readings (collar IMU) was called
        tool_names = {c.get("tool") for c in all_tools}
        assert "get_latest_readings" in tool_names, (
            f"Expected get_latest_readings tool call. Got: {tool_names}"
        )

        # 5. page_rancher at high urgency
        assert "page_rancher" in tool_names, (
            f"Expected page_rancher tool call. Got: {tool_names}"
        )
        rancher_calls = [c for c in all_tools if c.get("tool") == "page_rancher"]
        urgency = rancher_calls[0].get("input", {}).get("urgency", "")
        assert urgency in ("call", "high", "emergency", "text"), (
            f"Expected rancher urgency for calving, got {urgency!r}"
        )
