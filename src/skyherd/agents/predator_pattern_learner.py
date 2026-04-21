"""PredatorPatternLearner — nightly multi-day thermal crossing analysis.

Wake topics : ``skyherd/+/thermal/+``, cron ``0 2 * * *`` (nightly 2am)
MCP servers : sensor_mcp, galileo_mcp, drone_mcp (propose-only)
Runtime     : 30-day session, nightly checkpoints.

Handler flow
------------
1. Load predator-id and drone-ops skills.
2. Query sensor_mcp for recent thermal history (last 7 days).
3. Analyse crossing patterns — time-of-day distributions, entry vectors.
4. Propose updated patrol schedules via galileo_mcp (no autonomous dispatch).
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


PREDATOR_PATTERN_LEARNER_SPEC = AgentSpec(
    name="PredatorPatternLearner",
    system_prompt_template_path="src/skyherd/agents/prompts/predator_pattern_learner.md",
    wake_topics=[
        "skyherd/+/thermal/+",
        "skyherd/+/cron/nightly",
    ],
    mcp_servers=["sensor_mcp", "galileo_mcp", "drone_mcp"],
    skills=[
        _skill("predator-ids/coyote.md"),
        _skill("predator-ids/mountain-lion.md"),
        _skill("predator-ids/wolf.md"),
        _skill("predator-ids/thermal-signatures.md"),
        _skill("nm-ecology/nm-predator-ranges.md"),
        _skill("drone-ops/patrol-planning.md"),
    ],
    checkpoint_interval_s=86400,   # nightly
    max_idle_s_before_checkpoint=7200,
    model="claude-opus-4-7",
)

_SYSTEM_PROMPT_INLINE = """\
You are PredatorPatternLearner for the SkyHerd ranch monitoring system.

Your job:
1. Analyse multi-day thermal-clip history to detect coyote/mountain-lion crossing patterns.
2. Identify time-of-day clusters, entry vector segments, and seasonal trends.
3. Propose updated drone patrol schedules that pre-position coverage at high-probability windows.

IMPORTANT CONSTRAINT:
- You PROPOSE patrol schedules — you never dispatch drones autonomously.
- All schedule proposals require rancher acknowledgment before taking effect.
- Log your analysis and proposals to the galileo ledger.
"""


async def handler(
    session: Session,
    wake_event: dict[str, Any],
    sdk_client: Any,
) -> list[dict[str, Any]]:
    """Run one PredatorPatternLearner wake cycle."""
    ranch_id = wake_event.get("ranch_id", "ranch_a")
    event_type = wake_event.get("type", "nightly.analysis")

    skill_texts = [_load_text(p) for p in session.agent_spec.skills]

    user_message = (
        f"WAKE EVENT: {event_type}\n"
        f"Ranch: {ranch_id}\n"
        f"Raw payload: {wake_event}\n\n"
        "Analyse the recent thermal history and propose updated patrol schedules."
    )

    cached_payload = build_cached_messages(
        _SYSTEM_PROMPT_INLINE, skill_texts, user_message
    )

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
    return [
        {
            "tool": "get_thermal_history",
            "input": {"days": 7, "ranch_id": wake_event.get("ranch_id", "ranch_a")},
        },
        {
            "tool": "log_pattern_analysis",
            "input": {
                "summary": "Coyote activity peaks 02:00–04:00 MST near fence segments 3–5.",
                "proposed_patrols": [
                    {"time": "01:45", "segment": "seg_3"},
                    {"time": "03:30", "segment": "seg_5"},
                ],
            },
        },
    ]
