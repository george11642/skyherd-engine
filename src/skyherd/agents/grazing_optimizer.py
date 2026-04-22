"""GrazingOptimizer — weekly paddock rotation + weather-triggered overrides.

Wake topics : cron ``0 6 * * 1`` (Monday 06:00), ``skyherd/+/weather/+`` (storm override)
MCP servers : sensor_mcp, rancher_mcp, galileo_mcp
Runtime     : IDLES FOR DAYS waiting for rancher approval — the cost-ticker money shot.

Handler flow
------------
1. Load paddock-rotation, water-tank, nm-ecology, voice-persona skills.
2. Query NDVI proxy + water telemetry + herd density from sensor_mcp.
3. Propose paddock rotation sequence.
4. Wait for rancher approval via page_rancher (session goes idle).
5. On approval: execute acoustic nudge via rancher_mcp.
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


GRAZING_OPTIMIZER_SPEC = AgentSpec(
    name="GrazingOptimizer",
    system_prompt_template_path="src/skyherd/agents/prompts/grazing_optimizer.md",
    wake_topics=[
        "skyherd/+/cron/weekly_monday",
        "skyherd/+/weather/+",
    ],
    mcp_servers=["sensor_mcp", "rancher_mcp", "galileo_mcp"],
    skills=[
        _skill("ranch-ops/paddock-rotation.md"),
        _skill("ranch-ops/water-tank-sops.md"),
        _skill("nm-ecology/nm-forage.md"),
        _skill("nm-ecology/seasonal-calendar.md"),
        _skill("cattle-behavior/feeding-patterns.md"),
        _skill("voice-persona/wes-register.md"),
    ],
    checkpoint_interval_s=86400,  # nightly checkpoints between weekly wakes
    max_idle_s_before_checkpoint=3600,
    model="claude-opus-4-7",
)

_SYSTEM_PROMPT_INLINE = """\
You are GrazingOptimizer for the SkyHerd ranch monitoring system.

Weekly (Monday 06:00 MST) or on storm alerts:
1. Review NDVI proxy + water telemetry + herd density data.
2. Propose an optimal paddock rotation sequence for the coming week.
3. Page the rancher with the proposal and WAIT for their approval.
4. Only after rancher approval: execute the acoustic nudge to guide herd movement.

CRITICAL CONSTRAINT:
- Never trigger acoustic nudge without explicit rancher approval.
- Storm overrides may accelerate the schedule; always check weather data first.
- Keep proposals concise and in plain-English Wes-persona language.

You will idle for extended periods waiting for rancher response — this is expected.
"""


async def handler(
    session: Session,
    wake_event: dict[str, Any],
    sdk_client: Any,
) -> list[dict[str, Any]]:
    """Run one GrazingOptimizer wake cycle."""
    ranch_id = wake_event.get("ranch_id", "ranch_a")
    event_type = wake_event.get("type", "weekly.schedule")

    skill_texts = [_load_text(p) for p in session.agent_spec.skills]

    user_message = (
        f"WAKE EVENT: {event_type}\n"
        f"Ranch: {ranch_id}\n"
        f"Raw payload: {wake_event}\n\n"
        "Review grazing data and propose this week's paddock rotation. "
        "Page the rancher with your proposal and await approval before any action."
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
    """Deterministic simulation path — delegates to :mod:`skyherd.agents.simulate`."""
    from skyherd.agents.simulate import grazing_optimizer

    return grazing_optimizer(wake_event, session)
