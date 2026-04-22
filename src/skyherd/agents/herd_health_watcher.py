"""HerdHealthWatcher — trough-cam + collar activity anomaly detection.

Wake topics : ``skyherd/+/trough_cam/+`` (daily 06:00 schedule + motion)
MCP servers : sensor_mcp, rancher_mcp, galileo_mcp

Handler flow
------------
1. Load cattle-behavior and disease skills.
2. Run ``ClassifyPipeline.run()`` on the relevant trough.
3. Consolidate per-cow findings.
4. If any finding severity >= escalate → call ``page_rancher``.
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


HERD_HEALTH_WATCHER_SPEC = AgentSpec(
    name="HerdHealthWatcher",
    system_prompt_template_path="src/skyherd/agents/prompts/herd_health_watcher.md",
    wake_topics=[
        "skyherd/+/trough_cam/+",
    ],
    mcp_servers=["sensor_mcp", "rancher_mcp", "galileo_mcp"],
    skills=[
        _skill("cattle-behavior/feeding-patterns.md"),
        _skill("cattle-behavior/lameness-indicators.md"),
        _skill("cattle-behavior/heat-stress.md"),
        _skill("cattle-behavior/herd-structure.md"),
        # disease sub-skills
        _skill("cattle-behavior/disease/pinkeye.md") if False else "",  # loaded if exists
        _skill("ranch-ops/human-in-loop-etiquette.md"),
    ],
    checkpoint_interval_s=86400,  # nightly checkpoint
    max_idle_s_before_checkpoint=3600,
    model="claude-opus-4-7",
)

# Override skills with all that actually exist
HERD_HEALTH_WATCHER_SPEC.skills = [
    _skill("cattle-behavior/feeding-patterns.md"),
    _skill("cattle-behavior/lameness-indicators.md"),
    _skill("cattle-behavior/heat-stress.md"),
    _skill("cattle-behavior/herd-structure.md"),
    _skill("cattle-behavior/calving-signs.md"),
    _skill("ranch-ops/human-in-loop-etiquette.md"),
]

_SYSTEM_PROMPT_INLINE = """\
You are HerdHealthWatcher for the SkyHerd ranch monitoring system.

Your job:
1. Review trough-cam detections from the ClassifyPipeline.
2. Correlate with collar activity data (eating, ruminating, lying, standing anomalies).
3. Make a per-cow decision: log / observe / escalate to rancher or vet.

Severity levels:
- log: Normal or minor variation — write to ledger only.
- observe: Unusual but not urgent — monitor for 24h.
- escalate: Requires rancher or vet attention within 2 hours.

Do not escalate for single data-point anomalies. Require at least 2 corroborating signals.
Always include the cow tag ID in your assessment.
"""


async def handler(
    session: Session,
    wake_event: dict[str, Any],
    sdk_client: Any,
) -> list[dict[str, Any]]:
    """Run one HerdHealthWatcher wake cycle."""
    tool_calls: list[dict[str, Any]] = []

    ranch_id = wake_event.get("ranch_id", "ranch_a")
    trough_id = wake_event.get("trough_id", "trough_a")
    event_type = wake_event.get("type", "camera.motion")

    # Load skills for prompt caching
    skill_texts = [_load_text(p) for p in session.agent_spec.skills if p]

    user_message = (
        f"WAKE EVENT: {event_type}\n"
        f"Ranch: {ranch_id}\n"
        f"Trough: {trough_id}\n"
        f"Raw payload: {wake_event}\n\n"
        "Run the classify pipeline on this trough and report your findings."
    )

    cached_payload = build_cached_messages(_SYSTEM_PROMPT_INLINE, skill_texts, user_message)

    if sdk_client is not None and os.environ.get("ANTHROPIC_API_KEY"):
        tool_calls = await _run_with_sdk(sdk_client, cached_payload, session)
    else:
        tool_calls = _simulate_handler(wake_event, session)

    return tool_calls


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
    """Deterministic simulation path — invokes ClassifyPipeline stub."""
    trough_id = wake_event.get("trough_id", "trough_a")

    # Attempt to run the real ClassifyPipeline if world is available
    pipeline_result = _try_run_classify_pipeline(wake_event)

    calls = [
        {
            "tool": "classify_pipeline",
            "input": {"trough_id": trough_id},
            "result": pipeline_result,
        },
    ]

    # Simulate an escalation if the wake event signals anomaly
    if wake_event.get("anomaly", False) or wake_event.get("type") == "camera.motion":
        calls.append(
            {
                "tool": "page_rancher",
                "input": {
                    "urgency": "text",
                    "context": f"HerdHealthWatcher: anomaly detected at {trough_id}. "
                    "Review recommended within 24h.",
                },
            }
        )

    return calls


def _try_run_classify_pipeline(wake_event: dict[str, Any]) -> dict[str, Any]:
    """Attempt to run the ClassifyPipeline; return stub result if unavailable."""
    try:
        from pathlib import Path as _Path

        from skyherd.vision.pipeline import ClassifyPipeline
        from skyherd.world.world import make_world

        _repo_root = _Path(__file__).parent.parent.parent.parent
        world = make_world(seed=42, config_path=_repo_root / "worlds" / "ranch_a.yaml")
        trough_id = wake_event.get("trough_id", "trough_a")
        pipeline = ClassifyPipeline()
        result = pipeline.run(world, trough_id)
        return {
            "detection_count": result.detection_count,
            "annotated_frame": str(result.annotated_frame_path),
        }
    except Exception as exc:  # noqa: BLE001
        logger.debug("classify pipeline unavailable: %s", exc)
        return {"detection_count": 0, "annotated_frame": None}
