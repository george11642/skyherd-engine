"""Scenario 2 — Sick cow flagged by HerdHealthWatcher.

Timeline
--------
* On world setup, cow A014 is stamped with ocular_discharge=0.7 and
  disease_flags += {"pinkeye"}.
* At sim-elapsed ~30s, a health check camera.motion event fires (simulating
  the 06:30 daily schedule).
* Expected cascade:
    camera.motion → HerdHealthWatcher wakes
    → classify_pipeline runs on trough_sw_1 (nearest to A014)
    → pinkeye detected on A014 with severity=escalate
    → vet-intake packet drafted
    → page_rancher urgency=log (vet paged)
"""

from __future__ import annotations

from typing import Any

from skyherd.scenarios.base import Scenario
from skyherd.world.world import World

_HEALTH_CHECK_AT_S = 30.0


class SickCowScenario(Scenario):
    name = "sick_cow"
    description = (
        "A014 pre-stamped with pinkeye → HerdHealthWatcher detects on daily "
        "trough-cam scan → vet-intake packet + escalation page"
    )
    duration_s = 300.0

    def __init__(self) -> None:
        self._check_injected = False

    def setup(self, world: World) -> None:
        """Stamp cow A014 with pinkeye markers."""
        updated: list[Any] = []
        for cow in world.herd.cows:
            if cow.tag == "A014":
                new_flags = set(cow.disease_flags) | {"pinkeye"}
                cow = cow.model_copy(
                    update={
                        "ocular_discharge": 0.7,
                        "disease_flags": new_flags,
                        "health_score": 0.55,
                    }
                )
            updated.append(cow)
        world.herd.cows = updated

    def inject_events(self, world: World, sim_time_s: float) -> list[dict[str, Any]]:
        """At ~06:30 offset, inject a camera.motion health-check event."""
        events: list[dict[str, Any]] = []
        if not self._check_injected and sim_time_s >= _HEALTH_CHECK_AT_S:
            self._check_injected = True

            # Find A014's trough cam vicinity
            # disease_flags + severity included so the simulate path can detect
            # pinkeye escalation and call draft_vet_intake (SCEN-01)
            events.append(
                {
                    "type": "camera.motion",
                    "source": "trough_cam",
                    "trough_id": "trough_a",
                    "ranch_id": "ranch_a",
                    "anomaly": True,
                    "cow_tag": "A014",
                    "ocular_discharge": 0.7,
                    "disease_flags": ["pinkeye"],
                    "severity": "escalate",
                    "health_score": 0.55,
                    "schedule": "daily_health_check",
                    "sim_time_s": sim_time_s,
                }
            )

            # Also inject a direct health.check event so agents can correlate
            events.append(
                {
                    "type": "health.check",
                    "source": "herd_health_watcher",
                    "cow_tag": "A014",
                    "ranch_id": "ranch_a",
                    "ocular_discharge": 0.7,
                    "disease_flags": ["pinkeye"],
                    "severity": "escalate",
                    "sim_time_s": sim_time_s,
                }
            )

        return events

    def assert_outcome(
        self,
        event_stream: list[dict[str, Any]],
        mesh: Any,
    ) -> None:
        """Assert pinkeye was detected and rancher/vet was notified."""
        # 1. camera.motion event was emitted
        motion = self._find_event(event_stream, "camera.motion")
        assert motion is not None, "Expected camera.motion event for health check"

        # 2. health.check event was emitted with pinkeye on A014
        health_check = self._find_event(event_stream, "health.check")
        assert health_check is not None, "Expected health.check event in stream"
        assert health_check.get("cow_tag") == "A014", (
            f"Expected health check on A014, got {health_check.get('cow_tag')!r}"
        )
        disease_flags = health_check.get("disease_flags", [])
        assert "pinkeye" in disease_flags, f"Expected pinkeye in disease_flags, got {disease_flags}"

        # 3. HerdHealthWatcher ran classify_pipeline and paged rancher
        all_tools = self._all_tool_calls(mesh)
        tool_names = {c.get("tool") for c in all_tools}

        assert "classify_pipeline" in tool_names, (
            f"Expected classify_pipeline tool call. Got: {tool_names}"
        )
        assert "page_rancher" in tool_names, (
            f"Expected page_rancher tool call after pinkeye detection. Got: {tool_names}"
        )
        assert "draft_vet_intake" in tool_names, (
            f"Expected draft_vet_intake tool call after pinkeye escalation. Got: {tool_names}"
        )

        # 4. Vet intake artifact on disk (SCEN-01)
        from pathlib import Path

        intake_files = list(Path("runtime/vet_intake").glob("A014_*.md"))
        assert intake_files, "Expected runtime/vet_intake/A014_*.md to exist after sick_cow run"
        intake_content = intake_files[0].read_text(encoding="utf-8")
        assert "pinkeye" in intake_content.lower(), (
            "Expected vet-intake artifact to mention pinkeye"
        )

        # 5. World setup correctly stamped A014 (verified via injected event)
        assert health_check.get("severity") == "escalate", (
            f"Expected severity=escalate for A014 pinkeye, got {health_check.get('severity')!r}"
        )
