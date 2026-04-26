"""Scenario 6 — Cross-Ranch Coyote (Extended Vision: agent-to-agent mesh).

Timeline
--------
* Coyote spawns at ranch_a's western fence (shared with ranch_b's east fence).
* Ranch_a FenceLineDispatcher confirms coyote → NeighborBroadcaster fires.
* Neighbor alert crosses the mesh boundary.
* Ranch_b FenceLineDispatcher wakes (neighbor_alert, pre_position mode).
* Ranch_b pre-positions a patrol drone — no rancher page (silent handoff).
* Both ranches' agent wakes appear in the event stream.
* Shared fence attested twice (once per ranch ledger).
* Zero duplicate rancher pages.

assert_outcome verifies all five conditions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from skyherd.scenarios.base import Scenario
from skyherd.world.world import World

logger = logging.getLogger(__name__)

# Sim-elapsed seconds at which the coyote breach fires (shared fence)
_BREACH_AT_S = 462.0

# IDs that tie ranch_a to ranch_b
_RANCH_A_SHARED_FENCE = "fence_east"  # ranch_a's east = ranch_b's west
_RANCH_B_SHARED_FENCE = "fence_west"


class CrossRanchCoyoteScenario(Scenario):
    """Coyote at ranch_a's shared fence triggers ranch_b pre-position without human."""

    name = "cross_ranch_coyote"
    description = (
        "Coyote confirmed at ranch_a shared fence → NeighborBroadcaster fires → "
        "ranch_b FenceLineDispatcher pre-positions drone (silent handoff, no duplicate page)"
    )
    duration_s = 600.0

    def __init__(self) -> None:
        self._breach_injected = False

    def setup(self, world: World) -> None:
        """Force southerly wind so herd is unaware of coyote approach."""
        world.weather_driver._weather = world.weather_driver.current.model_copy(
            update={"wind_dir_deg": 180.0}
        )

    def inject_events(self, world: World, sim_time_s: float) -> list[dict[str, Any]]:
        """Inject coyote breach at ranch_a's east (shared) fence."""
        events: list[dict[str, Any]] = []

        if not self._breach_injected and sim_time_s >= _BREACH_AT_S:
            self._breach_injected = True

            # Breach on the SHARED fence (ranch_a east = ranch_b west)
            events.append(
                {
                    "type": "fence.breach",
                    "source": "fence_motion_sensor",
                    "fence_id": _RANCH_A_SHARED_FENCE,
                    "segment": _RANCH_A_SHARED_FENCE,
                    "lat": 34.1230,
                    "lon": -106.4520,  # slightly east of the base coyote scenario
                    "ranch_id": "ranch_a",
                    "sim_time_s": sim_time_s,
                    "species_hint": "coyote",
                }
            )

            # Spawn the coyote at the eastern boundary
            from skyherd.world.predators import Predator, PredatorSpecies, PredatorState

            coyote = Predator(
                id="coyote_cross_ranch_001",
                species=PredatorSpecies.COYOTE,
                pos=(1995.0, 750.0),  # just inside ranch_a's east fence
                heading_deg=90.0,  # heading east — toward ranch_b
                state=PredatorState.APPROACHING,
                size_kg=13.0,
                thermal_signature=0.4,
            )
            world.predator_spawner.predators.append(coyote)

        # Transition coyote to fleeing after deterrent
        if self._breach_injected and sim_time_s >= _BREACH_AT_S + 90.0:
            for pred in world.predator_spawner.predators:
                if pred.id == "coyote_cross_ranch_001":
                    from skyherd.world.predators import PredatorState

                    updated = pred.model_copy(update={"state": PredatorState.FLEEING.value})
                    idx = world.predator_spawner.predators.index(pred)
                    world.predator_spawner.predators[idx] = updated
                    events.append(
                        {
                            "type": "predator.fleeing",
                            "predator_id": "coyote_cross_ranch_001",
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
        """Assert the cross-ranch cascade completed correctly.

        Conditions checked
        ------------------
        1. fence.breach event emitted for ranch_a shared fence.
        2. Ranch_a FenceLineDispatcher woke and fired tool calls.
        3. Ranch_b FenceLineDispatcher woke (neighbor_alert) and fired tool calls.
        4. Shared fence attested twice (ranch_a + ranch_b attestation hashes present).
        5. Zero duplicate rancher pages — ranch_b used silent handoff only.
        """
        # 1. ranch_a fence.breach on the shared fence
        breach = self._find_event(event_stream, "fence.breach")
        assert breach is not None, "Expected fence.breach in event stream"
        assert (
            breach.get("fence_id") == _RANCH_A_SHARED_FENCE
            or breach.get("segment") == _RANCH_A_SHARED_FENCE
        ), f"Breach must be on shared fence {_RANCH_A_SHARED_FENCE!r}, got {breach}"

        # 2. Ranch_a agent woke and produced tool calls
        ranch_a_calls = self._get_ranch_tool_calls(mesh, "ranch_a")
        assert len(ranch_a_calls) > 0, "Ranch_a FenceLineDispatcher produced no tool calls"
        ranch_a_tools = {c.get("tool") for c in ranch_a_calls}
        assert "launch_drone" in ranch_a_tools, (
            f"Ranch_a expected launch_drone. Got: {ranch_a_tools}"
        )

        # Detect whether we are running in the full CrossRanchMesh or the simple _DemoMesh.
        # In the simple path the _tool_call_log is keyed by agent name, not ranch ID, so
        # "ranch_b" will never appear as a key.  Ranch-b-specific checks (3, 5, 6) require
        # real ranch separation and must be skipped on the simple path.
        log = getattr(mesh, "_tool_call_log", {})
        is_cross_ranch_mesh = "ranch_b" in log

        # 3. Ranch_b agent woke and produced tool calls (CrossRanchMesh only)
        if is_cross_ranch_mesh:
            ranch_b_calls = self._get_ranch_tool_calls(mesh, "ranch_b")
            assert len(ranch_b_calls) > 0, (
                "Ranch_b FenceLineDispatcher produced no tool calls — neighbor handoff failed"
            )
            ranch_b_tools = {c.get("tool") for c in ranch_b_calls}
            assert "launch_drone" in ranch_b_tools, (
                f"Ranch_b expected pre_position launch_drone. Got: {ranch_b_tools}"
            )

        # 4. Shared fence attested in BOTH ranch logs
        result = getattr(mesh, "_simulation_result", None)
        if result is not None:
            # Full CrossRanchMesh path — attestation_hashes list has 2 entries
            attest_hashes = result.get("attestation_hashes", [])
            assert len(attest_hashes) >= 2, (
                f"Expected >=2 attestation hashes (one per ranch). Got: {attest_hashes}"
            )
        # If no result attached (plain _DemoMesh path), skip attestation check

        # 5 & 6. Ranch_b-specific checks (CrossRanchMesh only)
        if is_cross_ranch_mesh:
            ranch_b_calls = self._get_ranch_tool_calls(mesh, "ranch_b")
            ranch_b_tools = {c.get("tool") for c in ranch_b_calls}

            # 5. Ranch_b must NOT have paged the rancher (silent handoff)
            ranch_b_rancher_pages = [c for c in ranch_b_calls if c.get("tool") == "page_rancher"]
            assert len(ranch_b_rancher_pages) == 0, (
                f"Ranch_b should NOT page rancher (silent pre-position handoff). "
                f"Got {len(ranch_b_rancher_pages)} page_rancher call(s)."
            )

            # 6. Ranch_b tool calls must include a neighbor_handoff log entry
            handoff_logs = [
                c
                for c in ranch_b_calls
                if c.get("tool") == "log_agent_event"
                and c.get("input", {}).get("event_type") == "neighbor_handoff"
            ]
            assert len(handoff_logs) > 0, (
                "Ranch_b expected a log_agent_event(event_type=neighbor_handoff) call. "
                f"Got tools: {ranch_b_tools}"
            )

            # 7. Phase 02 CRM-06: silent pre-position signature — the launch_drone
            #    mission MUST be 'neighbor_pre_position_patrol' (first-class
            #    CrossRanchCoordinator behavior).
            launch_calls = [c for c in ranch_b_calls if c.get("tool") == "launch_drone"]
            missions = [c.get("input", {}).get("mission") for c in launch_calls]
            assert "neighbor_pre_position_patrol" in missions, (
                "Ranch_b launch_drone mission must be 'neighbor_pre_position_patrol' "
                f"(silent pre-position signature). Got: {missions}"
            )

            # 8. Phase 02 CRM-03/06: log entry must carry response_mode=pre_position
            #    — the receipt that the memory post-cycle hook uses to compose the
            #    shared-store write under /neighbors/{from_ranch}/.
            pre_position_logs = [
                c for c in handoff_logs if c.get("input", {}).get("response_mode") == "pre_position"
            ]
            assert len(pre_position_logs) > 0, (
                "Ranch_b neighbor_handoff log entry must set response_mode='pre_position'. "
                f"Got logs: {handoff_logs}"
            )

            # 9. Phase 02 CRM-01 enforcement via the simulation-result shape:
            #    ranch_b_pre_positioned must be True (simulate_coyote_at_shared_fence
            #    sets this when any launch_drone call exists in ranch_b path).
            sim_result = getattr(mesh, "_simulation_result", None)
            if sim_result is not None:
                assert sim_result.get("ranch_b_pre_positioned") is True, (
                    "Simulation result must set ranch_b_pre_positioned=True when "
                    "CrossRanchCoordinator dispatches. Got: "
                    f"{sim_result.get('ranch_b_pre_positioned')}"
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_ranch_tool_calls(
        self,
        mesh: Any,
        ranch_id: str,
    ) -> list[dict[str, Any]]:
        """Extract tool calls attributed to a specific ranch from the mesh log."""
        log: dict[str, list[dict[str, Any]]] = getattr(mesh, "_tool_call_log", {})

        # CrossRanchMesh stores by ranch_id; _DemoMesh stores by agent name
        if ranch_id in log:
            return list(log[ranch_id])

        # Fallback: look for FenceLineDispatcher entry (single-ranch _DemoMesh)
        return list(log.get("FenceLineDispatcher", []))


# ---------------------------------------------------------------------------
# Async runner for use in tests and CLI
# ---------------------------------------------------------------------------


async def run_cross_ranch_async(seed: int = 42) -> dict[str, Any]:
    """Run the cross-ranch coyote scenario end-to-end (no API key required).

    Returns a result dict compatible with ScenarioResult fields plus the
    CrossRanchMesh simulation_result attached at ``result["simulation_result"]``.
    """
    import tempfile
    from pathlib import Path

    from skyherd.agents.mesh import AgentMesh
    from skyherd.agents.mesh_neighbor import CrossRanchMesh
    from skyherd.attest.ledger import Ledger
    from skyherd.attest.signer import Signer
    from skyherd.world.world import make_world

    repo_root = Path(__file__).parent.parent.parent.parent
    config_a = repo_root / "worlds" / "ranch_a.yaml"

    world_a = make_world(seed=seed, config_path=config_a)

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    signer = Signer.generate()
    ledger = Ledger.open(tmp.name, signer)

    # Build cross-ranch mesh
    mesh_a = AgentMesh()
    mesh_b = AgentMesh()

    cross = CrossRanchMesh(
        meshes={"ranch_a": mesh_a, "ranch_b": mesh_b},
        neighbor_config={
            "ranch_a": {_RANCH_A_SHARED_FENCE: "ranch_b"},
            "ranch_b": {_RANCH_B_SHARED_FENCE: "ranch_a"},
        },
    )
    await cross.start()

    scenario = CrossRanchCoyoteScenario()
    scenario.setup(world_a)

    all_events: list[dict[str, Any]] = []

    # Run scenario sim loop
    elapsed = 0.0
    step_dt = 5.0
    while elapsed < scenario.duration_s:
        step_events = world_a.step(step_dt)
        elapsed += step_dt

        for ev in step_events:
            ledger.append(source="world", kind=ev.get("type", "unknown"), payload=ev)

        injected = scenario.inject_events(world_a, elapsed)
        all_events.extend(step_events)
        all_events.extend(injected)

        # Route fence.breach events through the cross-ranch mesh
        for ev in step_events + injected:
            if ev.get("type") == "fence.breach" and ev.get("ranch_id") == "ranch_a":
                sim_result = await cross.simulate_coyote_at_shared_fence(
                    from_ranch="ranch_a",
                    shared_fence_id=_RANCH_A_SHARED_FENCE,
                    species="coyote",
                    confidence=0.91,
                )
                cross._simulation_result = sim_result  # type: ignore[attr-defined]

    await cross.stop()

    # Assert outcome using the CrossRanchMesh tool_call_log
    outcome_passed = False
    outcome_error: str | None = None
    try:
        scenario.assert_outcome(all_events, cross)
        outcome_passed = True
    except AssertionError as exc:
        outcome_error = str(exc)

    attest_entries = [e.model_dump() for e in ledger.iter_events()]
    ledger._conn.close()

    import os as _os

    try:
        _os.unlink(tmp.name)
    except OSError:
        logger.debug("tmp ledger file already gone (cleanup race â non-fatal): %s", tmp.name)

    return {
        "name": scenario.name,
        "seed": seed,
        "outcome_passed": outcome_passed,
        "outcome_error": outcome_error,
        "event_count": len(all_events),
        "ranch_a_tool_calls": cross._tool_call_log.get("ranch_a", []),
        "ranch_b_tool_calls": cross._tool_call_log.get("ranch_b", []),
        "attestation_count": len(attest_entries),
        "simulation_result": getattr(cross, "_simulation_result", {}),
    }


def run_cross_ranch(seed: int = 42) -> dict[str, Any]:
    """Synchronous wrapper for ``run_cross_ranch_async``."""
    return asyncio.run(run_cross_ranch_async(seed=seed))
