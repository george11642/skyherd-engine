"""memory_paths.py — pure, deterministic path + content decider per-agent.

Returns the (memory_path, markdown_content) tuple that `post_cycle_write` uses
to persist one memory per wake cycle. Every agent has its own branch; unknown
agents raise ValueError (fail fast — no silent default).

Invariants (enforced by tests):
  - No `datetime.now()`, no `uuid`, no `time.time()`, no `random` — pure.
  - No filesystem I/O.
  - Output byte-identical for identical inputs.
  - Redaction is applied before any secret-bearing field lands in content.

Reference: .planning/phases/01-memory-powered-agent-mesh/01-RESEARCH.md §Pattern 3.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

# Keys whose values are replaced by "[REDACTED]" before they can land in a
# memory content body. Conservative — add here when new secret classes appear.
_REDACT_KEYS: frozenset[str] = frozenset({
    "rancher_phone",
    "vet_phone",
    "auth_token",
    "api_key",
    "twilio_sid",
})

# Agent names lifted from skyherd.server.events.AGENT_NAMES — keep in sync.
_KNOWN_AGENTS: frozenset[str] = frozenset({
    "FenceLineDispatcher",
    "HerdHealthWatcher",
    "PredatorPatternLearner",
    "GrazingOptimizer",
    "CalvingWatch",
})


def _redact(d: dict[str, Any]) -> dict[str, Any]:
    """Return a NEW dict with secret-bearing keys replaced by "[REDACTED]"."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if k in _REDACT_KEYS:
            out[k] = "[REDACTED]"
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# Per-agent branches
# ---------------------------------------------------------------------------


def _predator_pattern_learner(event: dict[str, Any], tool_calls: list[dict[str, Any]]) -> tuple[str, str]:
    classification = str(event.get("classification", "unknown"))
    ranch_id = str(event.get("ranch_id", "ranch_a"))
    topic = classification.split(".", 1)[0]  # "coyote.confirmed" -> "coyote"
    path = f"patterns/{topic}-crossings.md"
    ts = str(event.get("ts", ""))
    content = (
        f"# {topic.capitalize()} crossings — {ranch_id}\n\n"
        f"- classification: {classification}\n"
        f"- tool_calls: {len(tool_calls)}\n"
        f"- ts: {ts}\n"
    )
    return path, content


def _herd_health_watcher(event: dict[str, Any], tool_calls: list[dict[str, Any]]) -> tuple[str, str]:
    tag = str(event.get("tag", "unknown"))
    path = f"notes/{tag}.md"
    ts = str(event.get("ts", ""))
    content = (
        f"# HerdHealth note — {tag}\n\n"
        f"- event_type: {event.get('type', 'unknown')}\n"
        f"- tool_calls: {len(tool_calls)}\n"
        f"- ts: {ts}\n"
    )
    return path, content


def _calving_watch(event: dict[str, Any], tool_calls: list[dict[str, Any]]) -> tuple[str, str]:
    tag = str(event.get("tag", "unknown"))
    path = f"baselines/{tag}.md"
    ts = str(event.get("ts", ""))
    content = (
        f"# Calving baseline — {tag}\n\n"
        f"- event_type: {event.get('type', 'unknown')}\n"
        f"- tool_calls: {len(tool_calls)}\n"
        f"- ts: {ts}\n"
    )
    return path, content


def _fenceline_dispatcher(event: dict[str, Any], tool_calls: list[dict[str, Any]]) -> tuple[str, str]:
    segment = str(event.get("segment", "unknown"))
    path = f"notes/dispatch-{segment}.md"
    ts = str(event.get("ts", ""))
    content = (
        f"# FenceLine dispatch — {segment}\n\n"
        f"- event_type: {event.get('type', 'unknown')}\n"
        f"- tool_calls: {len(tool_calls)}\n"
        f"- ts: {ts}\n"
    )
    return path, content


def _grazing_optimizer(event: dict[str, Any], tool_calls: list[dict[str, Any]]) -> tuple[str, str]:
    ranch_id = str(event.get("ranch_id", "ranch_a"))
    path = "notes/rotation-proposal.md"
    ts = str(event.get("ts", ""))
    content = (
        f"# Rotation proposal — {ranch_id}\n\n"
        f"- event_type: {event.get('type', 'unknown')}\n"
        f"- tool_calls: {len(tool_calls)}\n"
        f"- ts: {ts}\n"
    )
    return path, content


_DISPATCH = {
    "PredatorPatternLearner": _predator_pattern_learner,
    "HerdHealthWatcher": _herd_health_watcher,
    "CalvingWatch": _calving_watch,
    "FenceLineDispatcher": _fenceline_dispatcher,
    "GrazingOptimizer": _grazing_optimizer,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def decide_write_path(
    agent_name: str,
    event: dict[str, Any],
    tool_calls: list[dict[str, Any]],
) -> tuple[str, str]:
    """Return the (memory_path, markdown_content) tuple for a wake cycle.

    Pure: identical inputs produce byte-identical output. No datetime.now(),
    no uuid, no time.time(), no random — if a timestamp is needed, pull
    ``event.get("ts")`` (caller's responsibility to seed deterministically).

    Raises
    ------
    ValueError
        If ``agent_name`` is not one of the five registered SkyHerd agents.
    """
    if agent_name not in _KNOWN_AGENTS:
        raise ValueError(f"unknown agent: {agent_name!r}")
    redacted = _redact(event)
    handler = _DISPATCH[agent_name]
    return handler(redacted, tool_calls)


__all__ = ["decide_write_path"]
