"""FenceLineDispatcher — responds to fence breach + thermal confirmation events.

Wake topics : ``skyherd/+/fence/+``, ``skyherd/+/thermal/+``
              ``skyherd/neighbor/+/<ranch>/predator_confirmed``  (cross-ranch)
Target latency : <30s per wake cycle
MCP servers : drone_mcp, sensor_mcp, rancher_mcp, galileo_mcp

Handler flow
------------
1. Load skills (predator-id, fence-protocol, drone-ops, voice-persona).
2. Call ``sensor_mcp.get_thermal_clip`` to fetch the most recent thermal frame.
3. Ask Claude to classify the threat.
4. Based on classification:
   * Real predator / trespass → ``drone_mcp.launch_drone`` + ``drone_mcp.play_deterrent``
   * Also page rancher with appropriate urgency.
5. For ``neighbor_alert`` events (response_mode="pre_position"):
   * Pre-position patrol drone on the shared fence — no deterrent, no rancher page.
   * Emit a ``neighbor_handoff`` log entry for the dashboard.
   * Only escalate to page_rancher if the threat cascades into a direct observation.
6. Return list of tool call records.

System prompt addendum for neighbor alerts
------------------------------------------
"Neighbor alerts arrive in advance of direct observation; treat them as leading
indicators, NOT confirmed breaches.  Pre-position a drone on the shared fence
and log a neighbor_handoff entry.  Do NOT page the rancher unless you receive a
direct fence.breach event on the same segment."
"""

from __future__ import annotations

import logging
import os
from typing import Any

from skyherd.agents._handler_base import run_handler_cycle
from skyherd.agents.session import Session, _load_text, build_cached_messages
from skyherd.agents.spec import AgentSpec

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------

_SKILLS_BASE = "skills"


def _skill(path: str) -> str:
    return f"{_SKILLS_BASE}/{path}"


FENCELINE_DISPATCHER_SPEC = AgentSpec(
    name="FenceLineDispatcher",
    system_prompt_template_path="src/skyherd/agents/prompts/fenceline_dispatcher.md",
    wake_topics=[
        "skyherd/+/fence/+",
        "skyherd/+/thermal/+",
        "skyherd/neighbor/+/+/predator_confirmed",  # cross-ranch neighbor alerts
    ],
    mcp_servers=["drone_mcp", "sensor_mcp", "rancher_mcp", "galileo_mcp"],
    skills=[
        _skill("predator-ids/coyote.md"),
        _skill("predator-ids/mountain-lion.md"),
        _skill("predator-ids/wolf.md"),
        _skill("predator-ids/livestock-guardian-dogs.md"),
        _skill("predator-ids/thermal-signatures.md"),
        _skill("ranch-ops/fence-line-protocols.md"),
        _skill("ranch-ops/human-in-loop-etiquette.md"),
        _skill("drone-ops/patrol-planning.md"),
        _skill("drone-ops/deterrent-protocols.md"),
        _skill("voice-persona/wes-register.md"),
        _skill("voice-persona/urgency-tiers.md"),
        _skill("nm-ecology/nm-predator-ranges.md"),
    ],
    checkpoint_interval_s=600,
    max_idle_s_before_checkpoint=120,
    model="claude-opus-4-7",
)

# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_INLINE = """You are FenceLineDispatcher for ranch {ranch_id}.

When a fence breach event fires:
1. Call get_thermal_clip to fetch the latest thermal frame from that segment.
2. Classify the heat signature as one of: coyote, mountain_lion, livestock_guardian_dog, tag_drift, trespass, or unknown.
3. For genuine threats (coyote, mountain_lion, trespass): call launch_drone to dispatch a patrol drone to the breach coordinates, then call play_deterrent with appropriate tone.
4. Page the rancher via page_rancher at urgency matching the threat level.

CRITICAL CONSTRAINT: Never authorize lethal force autonomously. Always escalate to the rancher for any escalated response.
"""


async def handler(
    session: Session,
    wake_event: dict[str, Any],
    sdk_client: Any,
) -> list[dict[str, Any]]:
    """Run one FenceLineDispatcher wake cycle.

    Parameters
    ----------
    session:
        The active ``Session`` for this agent.
    wake_event:
        The MQTT event dict that triggered this wake (contains topic, payload).
    sdk_client:
        A ``ClaudeSDKClient`` instance (or stub in tests).

    Returns
    -------
    list[dict]
        Tool call records emitted during this cycle.
    """
    tool_calls: list[dict[str, Any]] = []

    ranch_id = wake_event.get("ranch_id", "ranch_a")
    event_type = wake_event.get("type", "fence.breach")
    segment = wake_event.get("segment", "unknown")
    lat = wake_event.get("lat", 34.0)
    lon = wake_event.get("lon", -106.0)

    # Load skill texts for prompt caching
    skill_texts = [_load_text(p) for p in session.agent_spec.skills]
    system_prompt = _SYSTEM_PROMPT_INLINE.format(ranch_id=ranch_id)

    # Build wake-cycle user message
    user_message = (
        f"WAKE EVENT: {event_type}\n"
        f"Ranch: {ranch_id}\n"
        f"Fence segment: {segment}\n"
        f"GPS: {lat}, {lon}\n"
        f"Raw payload: {wake_event}\n\n"
        "Please respond to this fence event per your protocols."
    )

    cached_payload = build_cached_messages(system_prompt, skill_texts, user_message)

    # Route neighbor alerts to the pre-position handler (no API key needed)
    if event_type == "neighbor_alert":
        from skyherd.agents.mesh_neighbor import _simulate_neighbor_handler

        tool_calls = _simulate_neighbor_handler(wake_event, session)
        return tool_calls

    # Use SDK client if available; otherwise simulate tool calls for smoke test
    if sdk_client is not None and os.environ.get("ANTHROPIC_API_KEY"):
        tool_calls = await run_handler_cycle(session, wake_event, sdk_client, cached_payload)
        if not tool_calls and not os.environ.get("SKYHERD_AGENTS"):
            pass
    else:
        # Simulation path — dispatch based on event type
        tool_calls = _simulate_handler(wake_event, session)

    return tool_calls


def _simulate_handler(
    wake_event: dict[str, Any],
    session: Session,
) -> list[dict[str, Any]]:
    """Deterministic simulation path — delegates to :mod:`skyherd.agents.simulate`."""
    from skyherd.agents.simulate import fenceline_dispatcher

    return fenceline_dispatcher(wake_event, session)
