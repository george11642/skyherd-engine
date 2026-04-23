"""CrossRanchCoordinator — Phase 02 agent: receives cross-ranch neighbor alerts.

Wake topic  : ``skyherd/neighbor/+/+/predator_confirmed``
Target      : silent pre-positioning of a patrol drone when a neighboring ranch
              confirms a predator near a shared fence. NO rancher page. NO
              audible deterrent. Leading-indicator response only.
MCP servers : drone_mcp (launch_drone), sensor_mcp (get_thermal_clip),
              galileo_mcp (log_agent_event).

Handler flow
------------
1. Load predator-id + voice-persona skills (for prompt caching).
2. Build a cached wake message naming the incoming ranch + shared fence.
3. If a real Anthropic API key is available, delegate to ``run_handler_cycle``
   which drives Managed Agents + memory post-cycle hook.
4. Otherwise fall back to the pure simulation path in ``simulate.py``.

Memory contract
---------------
Post-cycle hook writes under the shared store at
``/neighbors/{from_ranch}/{shared_fence}.md`` (see ``memory_paths.py``).

Never escalate
--------------
The ONLY path to ``page_rancher`` is a direct ``fence.breach`` on the SAME
segment within 5 minutes of a neighbor alert. This handler does not emit
that — FenceLineDispatcher does. Coordinator stays silent by design.
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


CROSS_RANCH_COORDINATOR_SPEC = AgentSpec(
    name="CrossRanchCoordinator",
    system_prompt_template_path="src/skyherd/agents/prompts/cross_ranch_coordinator.md",
    wake_topics=[
        "skyherd/neighbor/+/+/predator_confirmed",
    ],
    mcp_servers=["drone_mcp", "sensor_mcp", "galileo_mcp"],
    skills=[
        _skill("predator-ids/coyote.md"),
        _skill("predator-ids/thermal-signatures.md"),
        _skill("nm-ecology/nm-predator-ranges.md"),
        _skill("voice-persona/wes-register.md"),
        _skill("voice-persona/urgency-tiers.md"),
    ],
    checkpoint_interval_s=1800,
    max_idle_s_before_checkpoint=300,
    model="claude-opus-4-7",
)

# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_INLINE = """\
You are CrossRanchCoordinator for the SkyHerd ranch monitoring system.

When a neighboring ranch confirms a predator near a shared fence:
1. Call get_thermal_clip to correlate our side of the fence.
2. Call launch_drone with mission='neighbor_pre_position_patrol' at
   altitude 60 m. This is a SILENT pre-position — no deterrent playback.
3. Call log_agent_event with event_type='neighbor_handoff' and
   response_mode='pre_position'. The post-cycle hook will write a pattern
   summary to the shared memory store under /neighbors/{from_ranch}/.

CRITICAL: Never call page_rancher on a leading-indicator neighbor alert
alone. The rancher is only paged when a direct fence.breach on the SAME
segment arrives within 5 minutes — FenceLineDispatcher handles that
escalation, not you. Your job is silent readiness.
"""


async def handler(
    session: Session,
    wake_event: dict[str, Any],
    sdk_client: Any,
) -> list[dict[str, Any]]:
    """Run one CrossRanchCoordinator wake cycle.

    Parameters
    ----------
    session:
        The active ``Session`` (or ``ManagedSession``) for this agent.
    wake_event:
        Neighbor-alert wake event with keys ``from_ranch``, ``shared_fence``,
        ``species``, ``confidence``, ``ranch_id``.
    sdk_client:
        ``anthropic.AsyncAnthropic`` instance, or ``None`` to force the
        deterministic simulation path.
    """
    ranch_id = wake_event.get("ranch_id", "ranch_b")
    from_ranch = wake_event.get("from_ranch", "unknown")
    species = wake_event.get("species", "unknown")
    shared_fence = wake_event.get("shared_fence", "unknown")
    confidence = wake_event.get("confidence", 0.0)

    skill_texts = [_load_text(p) for p in session.agent_spec.skills]

    user_message = (
        f"WAKE EVENT: neighbor.alert\n"
        f"Ranch: {ranch_id}\n"
        f"Inbound from: {from_ranch}\n"
        f"Shared fence: {shared_fence}\n"
        f"Species: {species}\n"
        f"Confidence: {confidence}\n"
        f"Raw payload: {wake_event}\n\n"
        "Pre-position patrol per your protocols. Do NOT page the rancher."
    )

    cached_payload = build_cached_messages(_SYSTEM_PROMPT_INLINE, skill_texts, user_message)

    if sdk_client is not None and os.environ.get("ANTHROPIC_API_KEY"):
        return await run_handler_cycle(session, wake_event, sdk_client, cached_payload)
    return _simulate_handler(wake_event, session)


def _simulate_handler(
    wake_event: dict[str, Any],
    session: Session,
) -> list[dict[str, Any]]:
    """Deterministic simulation path — delegates to :mod:`skyherd.agents.simulate`."""
    from skyherd.agents.simulate import cross_ranch_coordinator

    return cross_ranch_coordinator(wake_event, session)
