"""CalvingWatch — seasonal (Mar–Apr) labor behavior + dystocia paging.

Wake topics : ``skyherd/+/collar/+``, ``skyherd/+/trough_cam/+``,
              ``skyherd/+/cron/every_15min``
MCP servers : sensor_mcp, rancher_mcp
Runtime     : 6-week seasonal session; nightly checkpoints.

Handler flow
------------
1. Load calving-signs, herd-structure, voice-persona skills.
2. Check collar activity data for pre-labor indicators (restlessness, isolation).
3. Correlate with trough-cam isolation sighting.
4. Classify: normal / pre-labor / active-labor / dystocia.
5. Page rancher at appropriate urgency; page vet on dystocia.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from skyherd.agents._handler_base import run_handler_cycle
from skyherd.agents.session import Session, _load_text, build_cached_messages
from skyherd.agents.spec import AgentSpec

logger = logging.getLogger(__name__)

_SKILLS_BASE = "skills"


def _skill(path: str) -> str:
    return f"{_SKILLS_BASE}/{path}"


CALVING_WATCH_SPEC = AgentSpec(
    name="CalvingWatch",
    system_prompt_template_path="src/skyherd/agents/prompts/calving_watch.md",
    wake_topics=[
        "skyherd/+/collar/+",
        "skyherd/+/trough_cam/+",
        "skyherd/+/cron/every_15min",
    ],
    mcp_servers=["sensor_mcp", "rancher_mcp"],
    skills=[
        _skill("cattle-behavior/calving-signs.md"),
        _skill("cattle-behavior/herd-structure.md"),
        _skill("ranch-ops/human-in-loop-etiquette.md"),
        _skill("voice-persona/wes-register.md"),
        _skill("voice-persona/urgency-tiers.md"),
    ],
    checkpoint_interval_s=43200,  # twice-daily checkpoints during calving season
    max_idle_s_before_checkpoint=900,
    model="claude-opus-4-7",
    disable_tools=["web_search", "web_fetch"],  # MEM-11: deterministic offline agent
)

_SYSTEM_PROMPT_INLINE = """\
You are CalvingWatch for the SkyHerd ranch monitoring system.

Active seasonally: March 1 – April 30 (calving season for New Mexico ranches).

Your job:
1. Monitor pregnancy-tagged cows continuously for pre-labor and labor signs.
2. Correlate collar activity data (restlessness, isolation, increased movement) with
   camera sightings of isolation or straining behaviour.
3. Classify current status as: normal / pre-labor / active-labor / dystocia.
4. Pre-labor: notify rancher via text (non-urgent).
5. Active labor: call rancher immediately.
6. Dystocia (difficult birth): call rancher AND vet simultaneously — this is an emergency.

Urgency tiers:
- text: pre-labor, more than 2h to calving estimated.
- call: active labor.
- emergency: dystocia detected.

Always include the cow tag ID, GPS location, and your confidence score.
"""


async def handler(
    session: Session,
    wake_event: dict[str, Any],
    sdk_client: Any,
) -> list[dict[str, Any]]:
    """Run one CalvingWatch wake cycle."""
    ranch_id = wake_event.get("ranch_id", "ranch_a")
    event_type = wake_event.get("type", "collar.activity_spike")
    tag = wake_event.get("tag", "unknown")

    skill_texts = [_load_text(p) for p in session.agent_spec.skills]

    user_message = (
        f"WAKE EVENT: {event_type}\n"
        f"Ranch: {ranch_id}\n"
        f"Cow tag: {tag}\n"
        f"Raw payload: {wake_event}\n\n"
        "Assess current calving status for this cow and respond appropriately."
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
    from skyherd.agents.simulate import calving_watch

    return calving_watch(wake_event, session)
