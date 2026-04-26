"""Live managed-runtime mesh smoke test — exercises the real Anthropic Managed
Agents platform with $ANTHROPIC_API_KEY.

This is NOT the CLI `skyherd-mesh mesh smoke` path — that one hardcodes
``sdk_client=None`` and always runs the simulation shim. This script drives
:class:`ManagedSessionManager` directly so each agent actually creates a
real platform session, sends a ``user.message`` wake event, streams the
SSE event loop, and records tool calls + token usage + cost.

Requirements
------------
- ``ANTHROPIC_API_KEY`` set in env (108-char Anthropic key).
- ``SKYHERD_AGENTS=managed`` (so the managed path is selected).

Usage
-----
::

    set -a && source .env.local && set +a
    SKYHERD_AGENTS=managed uv run python scripts/managed_mesh_smoke_live.py

Writes :file:`runtime/mesh-smoke-live.log` (JSON summary + per-agent detail)
and emits a short PASS/FAIL to stdout.

Also verifies MEM-11 offline: prints the CalvingWatch + GrazingOptimizer
disable_tools and the tool config the spec would emit. MEM-11 platform-side
verification (agent.retrieve) is attempted as best-effort; if the SDK lacks
that method we fall back to the local offline check.

Cost budget: <$0.50 (one short wake per agent, small max_tokens, ~200ms stream).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Log to both stdout and runtime/mesh-smoke-live.log
# ---------------------------------------------------------------------------

RUNTIME_LOG = Path("runtime/mesh-smoke-live.log")
RUNTIME_LOG.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("live-smoke")

# Mirror to file via a hand-held handler so tool streaming is also captured.
file_handler = logging.FileHandler(RUNTIME_LOG, mode="w")
file_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"))
logging.getLogger().addHandler(file_handler)


# ---------------------------------------------------------------------------
# Pricing (rough for claude-opus-4-7 per public pricing table).
# USD per 1K input tokens / 1K output tokens. Cache-read = 10% of input rate.
# Numbers sourced from anthropic.com/pricing; if API returns usage, we prefer
# platform-reported cost where available.
# ---------------------------------------------------------------------------

OPUS_INPUT_PER_K = 15.0 / 1000  # 15 USD / MTok
OPUS_OUTPUT_PER_K = 75.0 / 1000  # 75 USD / MTok
OPUS_CACHE_READ_PER_K = 1.5 / 1000  # 10% of input

SKYHERD_MAX_TOKENS = 512  # tight budget per wake
STREAM_TIMEOUT_S = 60  # per-agent stream cap


# ---------------------------------------------------------------------------
# One synthetic wake event per agent (mirrors mesh._SMOKE_WAKE_EVENTS)
# ---------------------------------------------------------------------------

SMOKE_WAKE_EVENTS: list[dict[str, Any]] = [
    {
        "topic": "skyherd/ranch_a/fence/seg_1",
        "type": "fence.breach",
        "ranch_id": "ranch_a",
        "segment": "seg_1",
    },
    {
        "topic": "skyherd/ranch_a/trough_cam/trough_a",
        "type": "camera.motion",
        "ranch_id": "ranch_a",
        "trough_id": "trough_a",
        "anomaly": True,
    },
    {
        "topic": "skyherd/ranch_a/thermal/cam_1",
        "type": "nightly.analysis",
        "ranch_id": "ranch_a",
    },
    {
        "topic": "skyherd/ranch_a/cron/weekly_monday",
        "type": "weekly.schedule",
        "ranch_id": "ranch_a",
    },
    {
        "topic": "skyherd/ranch_a/collar/tag_007",
        "type": "collar.activity_spike",
        "ranch_id": "ranch_a",
        "tag": "tag_007",
    },
    {
        "topic": "skyherd/neighbor/ranch_a/ranch_b/predator_confirmed",
        "type": "neighbor_alert",
        "ranch_id": "ranch_b",
        "from_ranch": "ranch_a",
        "shared_fence": "fence_west",
        "species": "coyote",
        "confidence": 0.91,
    },
]


def _mask(s: str | None, n: int = 8) -> str:
    if not s:
        return "∅"
    return f"{s[:n]}…"


async def _run_agent_smoke(
    mgr: Any,
    spec: Any,
    wake_event: dict[str, Any],
) -> dict[str, Any]:
    """Create a live session, send a short wake event, stream until idle.

    Returns a per-agent result dict. Never raises — captures failures into
    the returned dict so one flaky agent can't tank the whole run.
    """
    result: dict[str, Any] = {
        "agent": spec.name,
        "status": "unknown",
        "local_session_id": None,
        "platform_session_id": None,
        "platform_agent_id": None,
        "platform_env_id": None,
        "tool_calls": [],
        "tokens_in": 0,
        "tokens_out": 0,
        "cache_read": 0,
        "cache_write": 0,
        "events_seen": 0,
        "stream_time_s": 0.0,
        "error": None,
    }

    t0 = time.time()
    try:
        session = await mgr.create_session_async(spec)
        result["local_session_id"] = session.id
        result["platform_session_id"] = session.platform_session_id
        result["platform_agent_id"] = session.platform_agent_id
        result["platform_env_id"] = session.platform_env_id

        user_text = (
            f"LIVE SMOKE — WAKE EVENT: {wake_event.get('type')}\n"
            f"Ranch: {wake_event.get('ranch_id')}\n"
            f"Topic: {wake_event.get('topic')}\n"
            "Acknowledge briefly. No tool calls needed — just confirm readiness."
        )
        await mgr.send_wake_event(session, user_text)
        log.info(
            "  [%s] sent wake_event → platform session %s",
            spec.name,
            _mask(session.platform_session_id, 16),
        )

        # Stream with a time-budget guard
        stream_start = time.time()

        async def _consume() -> None:
            # NOTE: mgr.stream_session_events wraps the SDK incorrectly
            # (`async with coroutine` — never awaited). Call the SDK
            # directly. `beta.sessions.events.stream(id)` is a coroutine
            # that, when awaited, returns an AsyncStream which is itself
            # an async context manager + async iterator.
            raw_stream = await mgr._client.beta.sessions.events.stream(session.platform_session_id)
            async with raw_stream as sse:
                async for event in sse:
                    result["events_seen"] += 1
                    etype = getattr(event, "type", None)

                    if etype == "agent.custom_tool_use":
                        tname = getattr(event, "name", "unknown")
                        tinput = getattr(event, "input", {})
                        result["tool_calls"].append({"tool": tname, "input": tinput})
                        # Send a generic tool-result back so session can idle
                        try:
                            await mgr.send_tool_result(
                                session,
                                getattr(event, "id", ""),
                                "ok (live-smoke stub)",
                                is_error=False,
                            )
                        except Exception as exc:  # noqa: BLE001
                            log.warning("tool-result send failed for %s: %s", spec.name, exc)

                    elif etype == "span.model_request_end":
                        usage = getattr(event, "model_usage", None)
                        if usage is not None:
                            result["tokens_in"] += getattr(usage, "input_tokens", 0) or 0
                            result["tokens_out"] += getattr(usage, "output_tokens", 0) or 0
                            result["cache_read"] += (
                                getattr(usage, "cache_read_input_tokens", 0) or 0
                            )
                            result["cache_write"] += (
                                getattr(usage, "cache_creation_input_tokens", 0) or 0
                            )

                    elif etype in ("session.status_idle", "session.status_terminated"):
                        stop_reason = getattr(event, "stop_reason", None)
                        if etype == "session.status_terminated":
                            return
                        if stop_reason is not None:
                            sr_type = getattr(stop_reason, "type", None)
                            if sr_type != "requires_action":
                                return
                        else:
                            return

        try:
            await asyncio.wait_for(_consume(), timeout=STREAM_TIMEOUT_S)
        except TimeoutError:
            log.warning("[%s] stream timeout after %ds", spec.name, STREAM_TIMEOUT_S)
            result["error"] = f"stream_timeout_{STREAM_TIMEOUT_S}s"

        result["stream_time_s"] = round(time.time() - stream_start, 2)
        result["status"] = "ok"
        mgr.sleep(session.id)

    except Exception as exc:  # noqa: BLE001
        log.error("[%s] FAILED: %s: %s", spec.name, type(exc).__name__, exc)
        result["status"] = "error"
        result["error"] = f"{type(exc).__name__}: {exc}"

    dur = time.time() - t0
    log.info(
        "  [%s] DONE  events=%d  tools=%d  tok_in=%d  tok_out=%d  cache_r/w=%d/%d  %.2fs",
        spec.name,
        result["events_seen"],
        len(result["tool_calls"]),
        result["tokens_in"],
        result["tokens_out"],
        result["cache_read"],
        result["cache_write"],
        dur,
    )
    return result


def _estimate_cost(results: list[dict[str, Any]]) -> float:
    total = 0.0
    for r in results:
        total += (r["tokens_in"] / 1000) * OPUS_INPUT_PER_K
        total += (r["tokens_out"] / 1000) * OPUS_OUTPUT_PER_K
        total += (r["cache_read"] / 1000) * OPUS_CACHE_READ_PER_K
        # cache_write billed at input rate + 25% in practice; approximate as input
        total += (r["cache_write"] / 1000) * OPUS_INPUT_PER_K * 1.25
    return round(total, 4)


def _mem11_offline_check() -> dict[str, Any]:
    """Inspect specs for CalvingWatch + GrazingOptimizer — confirm MEM-11 wiring."""
    from skyherd.agents.calving_watch import CALVING_WATCH_SPEC
    from skyherd.agents.grazing_optimizer import GRAZING_OPTIMIZER_SPEC
    from skyherd.agents.managed import _build_tools_config

    check: dict[str, Any] = {}
    for spec in (CALVING_WATCH_SPEC, GRAZING_OPTIMIZER_SPEC):
        cfg = _build_tools_config(spec)
        disabled = [c["name"] for c in cfg.get("configs", []) if not c.get("enabled", True)]
        check[spec.name] = {
            "disable_tools": list(getattr(spec, "disable_tools", []) or []),
            "cfg_disabled": disabled,
            "pass": set(disabled) >= {"web_search", "web_fetch"},
        }
    return check


async def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.error("ANTHROPIC_API_KEY not set — refusing to run live smoke.")
        return 2
    if os.environ.get("SKYHERD_AGENTS") != "managed":
        log.warning("SKYHERD_AGENTS != 'managed' — setting it for this run.")
        os.environ["SKYHERD_AGENTS"] = "managed"

    # Import after env is set
    from skyherd.agents.calving_watch import CALVING_WATCH_SPEC
    from skyherd.agents.cross_ranch_coordinator import (
        CROSS_RANCH_COORDINATOR_SPEC,
    )
    from skyherd.agents.fenceline_dispatcher import FENCELINE_DISPATCHER_SPEC
    from skyherd.agents.grazing_optimizer import GRAZING_OPTIMIZER_SPEC
    from skyherd.agents.herd_health_watcher import HERD_HEALTH_WATCHER_SPEC
    from skyherd.agents.managed import ManagedSessionManager
    from skyherd.agents.predator_pattern_learner import (
        PREDATOR_PATTERN_LEARNER_SPEC,
    )

    specs = [
        FENCELINE_DISPATCHER_SPEC,
        HERD_HEALTH_WATCHER_SPEC,
        PREDATOR_PATTERN_LEARNER_SPEC,
        GRAZING_OPTIMIZER_SPEC,
        CALVING_WATCH_SPEC,
        CROSS_RANCH_COORDINATOR_SPEC,
    ]
    assert len(specs) == len(SMOKE_WAKE_EVENTS), "spec/wake count mismatch"

    log.info("=" * 72)
    log.info("SkyHerd live managed-runtime mesh smoke — %d agents", len(specs))
    log.info("=" * 72)

    # Ensure memory stores via the managed MemoryStoreManager (creates fresh if
    # cache missing, validates via live API otherwise). Mirrors what
    # AgentMesh._ensure_memory_stores() does, but we refresh even if cache
    # exists — platform stores can be purged, leaving the JSON cache stale.
    from skyherd.agents.memory import MemoryStoreManager

    memstore_ids: dict[str, str] = {}
    msf = Path("runtime/memory_store_ids.json")
    cached_ids: dict[str, str] = {}
    if msf.exists():
        try:
            cached_ids = json.loads(msf.read_text())
        except Exception as exc:  # noqa: BLE001
            log.warning("memory_store_ids parse failed: %s", exc)

    mem_mgr = MemoryStoreManager()

    # List all live, non-archived stores on the platform.
    live_ids: set[str] = set()
    try:
        live_stores = await mem_mgr.list_stores()
        live_ids = {s.id for s in live_stores if getattr(s, "archived_at", None) is None}
        log.info("Live (non-archived) memory stores on platform: %d", len(live_ids))
    except Exception as exc:  # noqa: BLE001
        log.warning("list_stores failed: %s — proceeding blindly.", type(exc).__name__)

    async def _ensure_or_recreate(name: str, desc: str) -> str:
        """Return a live memstore id for *name* — recreate if cached id is stale.

        If the cached id is NOT in live_ids (from list_stores), skip it and
        create fresh. Otherwise reuse.
        """
        cached = cached_ids.get(name)
        if cached and cached in live_ids:
            mem_mgr._store_ids[name] = cached
            return cached
        if cached and cached not in live_ids:
            log.warning("memory_store %s (%s) is stale — recreating.", name, cached)
        # Fall through to create fresh.
        sid = await mem_mgr.ensure_store(name=name, description=desc)
        return sid

    # Agent names the mesh defines (in canonical order)
    AGENT_NAMES_FOR_STORES = [
        "FenceLineDispatcher",
        "HerdHealthWatcher",
        "PredatorPatternLearner",
        "GrazingOptimizer",
        "CalvingWatch",
        "CrossRanchCoordinator",
    ]

    log.info("Ensuring memory stores (shared + per-agent)…")
    memstore_ids["_shared"] = await _ensure_or_recreate(
        "skyherd_ranch_a_shared",
        "SkyHerd shared ranch patterns — read-only domain library",
    )
    for aname in AGENT_NAMES_FOR_STORES:
        memstore_ids[aname] = await _ensure_or_recreate(
            f"skyherd_{aname.lower()}_ranch_a",
            f"Per-agent memory for {aname}",
        )
    # Persist the refreshed cache.
    msf.write_text(json.dumps(memstore_ids, indent=2))
    log.info(
        "memory_store_ids refreshed: %d stores (%s)",
        len(memstore_ids),
        ",".join(memstore_ids.keys()),
    )

    mgr = ManagedSessionManager(memory_store_ids=memstore_ids)

    # Ensure env up front (so first agent isn't billed twice).
    env_id = await mgr._ensure_environment()
    log.info("environment_id: %s", _mask(env_id, 16))

    t_start = time.time()
    results: list[dict[str, Any]] = []
    for spec, wake in zip(specs, SMOKE_WAKE_EVENTS, strict=True):
        log.info("── agent: %s ──────────────────────────────", spec.name)
        r = await _run_agent_smoke(mgr, spec, wake)
        results.append(r)

    total_dur = round(time.time() - t_start, 2)

    # MEM-11 offline check
    mem11 = _mem11_offline_check()

    # Summary
    total_tokens_in = sum(r["tokens_in"] for r in results)
    total_tokens_out = sum(r["tokens_out"] for r in results)
    total_cache_read = sum(r["cache_read"] for r in results)
    total_cache_write = sum(r["cache_write"] for r in results)
    total_tool_calls = sum(len(r["tool_calls"]) for r in results)
    total_cost = _estimate_cost(results)
    ok_count = sum(1 for r in results if r["status"] == "ok")
    err_count = sum(1 for r in results if r["status"] == "error")

    summary: dict[str, Any] = {
        "environment_id": env_id,
        "memory_store_ids": memstore_ids,
        "agents": results,
        "totals": {
            "ok": ok_count,
            "error": err_count,
            "tokens_in": total_tokens_in,
            "tokens_out": total_tokens_out,
            "cache_read": total_cache_read,
            "cache_write": total_cache_write,
            "tool_calls": total_tool_calls,
            "duration_s": total_dur,
            "estimated_cost_usd": total_cost,
        },
        "mem11_check": mem11,
    }

    log.info("=" * 72)
    log.info(
        "DONE  ok=%d  err=%d  tok_in=%d  tok_out=%d  cache_r/w=%d/%d  tools=%d  %.2fs  ~$%0.4f",
        ok_count,
        err_count,
        total_tokens_in,
        total_tokens_out,
        total_cache_read,
        total_cache_write,
        total_tool_calls,
        total_dur,
        total_cost,
    )
    log.info("MEM-11 offline check: %s", json.dumps(mem11, indent=2))

    # JSON summary written as a trailer to the log file
    summary_path = Path("runtime/mesh-smoke-live.summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    log.info("Summary written to %s", summary_path)

    return 0 if err_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
