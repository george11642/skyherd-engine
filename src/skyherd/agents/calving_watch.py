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
        return await _run_with_sdk(sdk_client, cached_payload, session)
    return _simulate_handler(wake_event, session)


async def _run_with_sdk(
    sdk_client: Any,
    cached_payload: dict[str, Any],
    session: Session,
) -> list[dict[str, Any]]:
    from claude_agent_sdk import AssistantMessage, ResultMessage, ToolUseBlock

    calls: list[dict[str, Any]] = []
    prompt = cached_payload["messages"][0]["content"][0]["text"]
    async for msg in sdk_client.query(prompt=prompt):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, ToolUseBlock):
                    calls.append({"tool": block.name, "input": block.input})
            if msg.usage:
                session.cumulative_tokens_in += msg.usage.get("input_tokens", 0)
                session.cumulative_tokens_out += msg.usage.get("output_tokens", 0)
        elif isinstance(msg, ResultMessage) and msg.total_cost_usd:
            session.cumulative_cost_usd += msg.total_cost_usd
    return calls


def _simulate_handler(
    wake_event: dict[str, Any],
    session: Session,
) -> list[dict[str, Any]]:
    tag = wake_event.get("tag", "cow_001")
    event_type = wake_event.get("type", "collar.activity_spike")

    calls = [
        {
            "tool": "get_latest_readings",
            "input": {"kind": "collar_imu", "n": 20},
        },
    ]

    if event_type == "dystocia_detected":
        calls.append(
            {
                "tool": "page_rancher",
                "input": {
                    "urgency": "emergency",
                    "context": f"DYSTOCIA DETECTED: cow {tag} requires immediate intervention. "
                    "Vet has also been notified.",
                },
            }
        )
    elif event_type in ("active_labor", "collar.activity_spike"):
        calls.append(
            {
                "tool": "page_rancher",
                "input": {
                    "urgency": "call",
                    "context": f"CalvingWatch: cow {tag} showing active labor signs. "
                    "Please check immediately.",
                },
            }
        )
    else:
        calls.append(
            {
                "tool": "page_rancher",
                "input": {
                    "urgency": "text",
                    "context": f"CalvingWatch: cow {tag} showing pre-labor indicators. "
                    "Monitoring — will update if condition escalates.",
                },
            }
        )

    return calls
