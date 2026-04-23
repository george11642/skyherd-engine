"""Deterministic simulation handlers for all SkyHerd agents.

Each function here is the ``_simulate_handler`` for one agent — the fallback
path used when no real Anthropic API key is present (smoke tests, CI, demos).

Dispatch table
--------------
``HANDLERS`` maps agent name (as defined in each agent's ``_SPEC.name``) to its
handler callable.  Call ``dispatch(agent_name, wake_event, session)`` to route.

Adding a new agent
------------------
1. Implement ``_handle_<agent_name>(wake_event, session) -> list[dict]`` here.
2. Register it in ``HANDLERS``.
3. Replace the local ``_simulate_handler`` in the agent module with::

       from skyherd.agents.simulate import dispatch as _simulate_dispatch
       def _simulate_handler(wake_event, session):
           return _simulate_dispatch(__name__.split(".")[-1], wake_event, session)

   or simply import the specific handler directly.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from skyherd.agents.session import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FenceLineDispatcher
# ---------------------------------------------------------------------------


def fenceline_dispatcher(
    wake_event: dict[str, Any],
    session: Session,
) -> list[dict[str, Any]]:
    """Deterministic simulation path for smoke testing without a real API key.

    Event-type routing
    ------------------
    * ``fence.breach`` with ``silent_mode=True`` (rustling_suspected):
        get_thermal_clip + launch_drone (silent observation) + page_rancher(urgency=text)
        NO play_deterrent — audible tone alerts suspects.
    * ``fence.breach`` with ``thermal_hotspot=True`` (wildfire defend-layer):
        get_thermal_clip + launch_drone (confirmation flyover) + page_rancher(urgency=high)
        NO play_deterrent — wildfire is not a predator.
    * ``fence.breach`` / ``predator.spawned`` / ``thermal.hotspot`` (normal predator):
        get_thermal_clip + launch_drone + play_deterrent + page_rancher(urgency=call)
    * Everything else (water.low, sensor.heartbeat, ...):
        Return [] — these events are handled by GrazingOptimizer/HerdHealthWatcher.
    """
    lat = wake_event.get("lat", 34.0)
    lon = wake_event.get("lon", -106.0)
    segment = wake_event.get("segment", "seg_1")
    event_type = wake_event.get("type", "")

    is_silent = bool(wake_event.get("silent_mode", False))
    is_wildfire = bool(wake_event.get("thermal_hotspot", False))
    is_breach = event_type in ("fence.breach", "thermal.hotspot", "predator.spawned")

    # Non-breach events are handled by other agents (GrazingOptimizer, etc.)
    if not is_breach and not is_silent and not is_wildfire:
        return []

    calls: list[dict[str, Any]] = []

    # Always fetch thermal clip for breach-class events
    calls.append(
        {
            "tool": "get_thermal_clip",
            "input": {"segment": segment},
        }
    )

    # Dispatch drone — mission type depends on context
    if is_silent:
        mission = "silent_observation"
        alt_m = 65.0
    elif is_wildfire:
        mission = "confirmation_flyover"
        alt_m = 80.0
    else:
        mission = "fence_patrol"
        alt_m = 60.0

    calls.append(
        {
            "tool": "launch_drone",
            "input": {
                "mission": mission,
                "target_lat": lat,
                "target_lon": lon,
                "alt_m": alt_m,
            },
        }
    )

    # Audible deterrent: only for normal predator breach, NOT rustling or wildfire
    if is_breach and not is_silent and not is_wildfire:
        calls.append(
            {
                "tool": "play_deterrent",
                "input": {"tone_hz": 14000, "duration_s": 5, "lat": lat, "lon": lon},
            }
        )

    # Page rancher with urgency matching the event context
    if is_wildfire:
        urgency = "high"
        context = f"Thermal hotspot detected near {segment}. Confirmation flyover dispatched."
    elif is_silent:
        urgency = "text"
        context = (
            f"SILENT ALERT — rustling_suspected at {segment}. "
            "Observation drone launched. DO NOT call back — suspects may be monitoring radio."
        )
    else:
        urgency = "call"
        context = (
            f"Potential predator at fence {segment}. "
            "Drone dispatched. Awaiting rancher confirmation."
        )

    calls.append(
        {
            "tool": "page_rancher",
            "input": {"urgency": urgency, "context": context},
        }
    )

    return calls


# ---------------------------------------------------------------------------
# GrazingOptimizer
# ---------------------------------------------------------------------------


def grazing_optimizer(
    wake_event: dict[str, Any],
    session: Session,
) -> list[dict[str, Any]]:
    """Deterministic simulation path for GrazingOptimizer."""
    is_storm = "weather" in wake_event.get("topic", "")

    calls: list[dict[str, Any]] = [
        {
            "tool": "get_latest_readings",
            "input": {"kind": "water_pressure", "n": 10},
        },
    ]

    if is_storm:
        calls.append(
            {
                "tool": "page_rancher",
                "input": {
                    "urgency": "text",
                    "context": "Storm alert: recommending early paddock rotation to higher ground. "
                    "Awaiting your approval before acoustic nudge.",
                },
            }
        )
    else:
        calls.append(
            {
                "tool": "page_rancher",
                "input": {
                    "urgency": "text",
                    "context": "Weekly rotation proposal: move herd from north paddock to east "
                    "paddock Monday. Forage levels nominal. Reply APPROVE to confirm.",
                },
            }
        )

    return calls


# ---------------------------------------------------------------------------
# HerdHealthWatcher
# ---------------------------------------------------------------------------


def herd_health_watcher(
    wake_event: dict[str, Any],
    session: Session,
) -> list[dict[str, Any]]:
    """Deterministic simulation path — invokes ClassifyPipeline stub.

    When the wake event indicates a pinkeye escalation (anomaly=True + cow_tag + disease_flags
    containing 'pinkeye'), this path also calls draft_vet_intake to produce the SCEN-01
    artifact.  A synthetic pixel-head bbox signal is injected for DASH-06 coverage
    (signals_structured).
    """
    trough_id = wake_event.get("trough_id", "trough_a")
    cow_tag = wake_event.get("cow_tag", "")
    is_pinkeye_escalation = (
        (wake_event.get("anomaly", False) or wake_event.get("type") == "camera.motion")
        and bool(cow_tag)
        and "pinkeye" in wake_event.get("disease_flags", [])
    )

    pipeline_result = _try_run_classify_pipeline(wake_event)

    calls: list[dict[str, Any]] = [
        {
            "tool": "classify_pipeline",
            "input": {"trough_id": trough_id},
            "result": pipeline_result,
        },
    ]

    # Simulate an escalation if the wake event signals anomaly
    if wake_event.get("anomaly", False) or wake_event.get("type") == "camera.motion":
        if is_pinkeye_escalation:
            # Draft vet intake packet (SCEN-01) with synthetic pixel bbox (DASH-06)
            intake_call = _try_draft_vet_intake(wake_event, session)
            if intake_call is not None:
                calls.append(intake_call)

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


def _try_draft_vet_intake(
    wake_event: dict[str, Any],
    session: Session,
) -> dict[str, Any] | None:
    """Attempt to call draft_vet_intake; return tool-call dict or None on failure.

    Injects a synthetic pixel-head bbox signal for DASH-06 test coverage
    in scenarios that run without an Anthropic API key.
    """
    import re

    try:
        from skyherd.server.vet_intake import draft_vet_intake

        cow_tag = wake_event.get("cow_tag", "")
        # Validate tag shape before calling (must be ^[A-Z][0-9]{3}$)
        if not re.match(r"^[A-Z][0-9]{3}$", cow_tag):
            logger.debug("_try_draft_vet_intake: invalid cow_tag %r — skipping", cow_tag)
            return None

        disease_flags: list[str] = list(wake_event.get("disease_flags", []))
        primary_disease = disease_flags[0] if disease_flags else "unknown"

        # Synthetic pixel bbox for DASH-06 coverage (simulate what Phase 2 VIS-05 would produce)
        signals_structured = [
            {
                "kind": "pixel_detection",
                "head": primary_disease,
                "bbox": [280, 110, 380, 200],  # synthetic but plausible trough-cam crop
                "confidence": 0.83,
            }
        ]

        session_id = getattr(session, "id", "sim_session")
        rec = draft_vet_intake(
            cow_tag=cow_tag,
            severity="escalate",
            disease=primary_disease,
            signals=[
                f"ocular_discharge={wake_event.get('ocular_discharge', 0.7):.2f}",
                f"disease_flags={disease_flags}",
            ],
            cow_snapshot={
                "tag": cow_tag,
                "bcs": 5.2,
                "health_score": wake_event.get("health_score", 0.55),
            },
            session_id=str(session_id),
            herd_context=(
                f"Ranch {wake_event.get('ranch_id', 'ranch_a')} · "
                f"trough {wake_event.get('trough_id', 'trough_a')} · "
                "sim deterministic path"
            ),
            signals_structured=signals_structured,
        )
        return {
            "tool": "draft_vet_intake",
            "input": {
                "cow_tag": cow_tag,
                "severity": "escalate",
                "disease": primary_disease,
                "signals_structured": signals_structured,
            },
            "output": rec.model_dump(),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("draft_vet_intake failed in simulate path: %s", exc)
        return None


def _try_run_classify_pipeline(wake_event: dict[str, Any]) -> dict[str, Any]:
    """Attempt to run ClassifyPipeline; return stub result on failure."""
    try:
        from pathlib import Path as _Path

        from skyherd.vision.pipeline import ClassifyPipeline  # type: ignore[import]
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


# ---------------------------------------------------------------------------
# CalvingWatch
# ---------------------------------------------------------------------------


def calving_watch(
    wake_event: dict[str, Any],
    session: Session,
) -> list[dict[str, Any]]:
    """Deterministic simulation path for CalvingWatch."""
    tag = wake_event.get("tag", "cow_001")
    event_type = wake_event.get("type", "collar.activity_spike")

    calls: list[dict[str, Any]] = [
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


# ---------------------------------------------------------------------------
# PredatorPatternLearner
# ---------------------------------------------------------------------------


def predator_pattern_learner(
    wake_event: dict[str, Any],
    session: Session,
) -> list[dict[str, Any]]:
    """Deterministic simulation path for PredatorPatternLearner."""
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


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_HandlerFn = Any  # Callable[[dict, Session], list[dict]]

HANDLERS: dict[str, _HandlerFn] = {
    "FenceLineDispatcher": fenceline_dispatcher,
    "GrazingOptimizer": grazing_optimizer,
    "HerdHealthWatcher": herd_health_watcher,
    "CalvingWatch": calving_watch,
    "PredatorPatternLearner": predator_pattern_learner,
}


def dispatch(
    agent_name: str,
    wake_event: dict[str, Any],
    session: Session,
) -> list[dict[str, Any]]:
    """Route *wake_event* to the registered handler for *agent_name*.

    Falls back to an empty list and logs a warning if no handler is found.
    """
    handler = HANDLERS.get(agent_name)
    if handler is None:
        logger.warning("simulate.dispatch: no handler for agent %r — returning []", agent_name)
        return []
    return handler(wake_event, session)
