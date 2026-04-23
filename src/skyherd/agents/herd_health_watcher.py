"""HerdHealthWatcher — trough-cam + collar activity anomaly detection.

Wake topics : ``skyherd/+/trough_cam/+`` (daily 06:00 schedule + motion)
MCP servers : sensor_mcp, rancher_mcp, galileo_mcp

Handler flow
------------
1. Load cattle-behavior and disease skills.
2. Run ``ClassifyPipeline.run()`` on the relevant trough.
3. Consolidate per-cow findings.
4. If any finding severity >= escalate → call ``draft_vet_intake`` (SCEN-01) to
   produce a rancher-readable markdown packet. Extract pixel-head DetectionResult.bbox
   (Phase 2 VIS-05) into ``signals_structured`` for DASH-06 when available.
5. Call ``page_rancher`` to alert rancher/vet.

The live path (``run_handler_cycle``) calls ``draft_vet_intake`` via the MCP tool
registered in ``rancher_mcp.py``. The deterministic sim path calls it directly via
``skyherd.agents.simulate.herd_health_watcher`` → ``_try_draft_vet_intake``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from skyherd.agents._handler_base import run_handler_cycle
from skyherd.agents.session import Session, _load_text, build_cached_messages
from skyherd.agents.spec import AgentSpec
from skyherd.server.vet_intake import draft_vet_intake as _draft_vet_intake  # noqa: F401

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
        # Behaviour context
        _skill("cattle-behavior/feeding-patterns.md"),
        _skill("cattle-behavior/lameness-indicators.md"),
        _skill("cattle-behavior/heat-stress.md"),
        _skill("cattle-behavior/herd-structure.md"),
        _skill("cattle-behavior/calving-signs.md"),
        # Disease decision rules (all 7 detection heads)
        _skill("cattle-behavior/disease/pinkeye.md"),
        _skill("cattle-behavior/disease/screwworm.md"),
        _skill("cattle-behavior/disease/foot-rot.md"),
        _skill("cattle-behavior/disease/brd.md"),
        _skill("cattle-behavior/disease/lsd.md"),
        _skill("cattle-behavior/disease/heat-stress-disease.md"),
        _skill("cattle-behavior/disease/bcs.md"),
        # Ranch operations
        _skill("ranch-ops/human-in-loop-etiquette.md"),
    ],
    checkpoint_interval_s=86400,  # nightly checkpoint
    max_idle_s_before_checkpoint=3600,
    model="claude-opus-4-7",
)

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
        tool_calls = await run_handler_cycle(session, wake_event, sdk_client, cached_payload)
    else:
        tool_calls = _simulate_handler(wake_event, session)

    return tool_calls


def _simulate_handler(
    wake_event: dict[str, Any],
    session: Session,
) -> list[dict[str, Any]]:
    """Deterministic simulation path — delegates to :mod:`skyherd.agents.simulate`."""
    from skyherd.agents.simulate import herd_health_watcher

    return herd_health_watcher(wake_event, session)
