"""Post-cycle memory write hook — invoked by _handler_base after every handler run.

Responsibilities:
  1. Summarise the wake cycle into (path, content) via memory_paths.decide_write_path.
  2. Write via get_memory_store_manager() (local shim or real REST, runtime-gated).
  3. Pair with Ed25519 ledger (source='memory', kind='memver.written').
  4. Fan out via EventBroadcaster 'memory.written' for dashboard live feed.

Design contract:
  - write_memory failure PROPAGATES (hook raises) — the caller in _handler_base
    wraps in try/except as the safety net.
  - Ledger + broadcaster calls are best-effort and wrapped individually so one
    broken sink does NOT block the other.

Reference: .planning/phases/01-memory-powered-agent-mesh/01-RESEARCH.md §Pattern 3.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def post_cycle_write(
    session: Any,
    wake_event: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    ledger: Any | None = None,
    broadcaster: Any | None = None,
    store_id_map: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Write one memory per wake cycle. Returns the Memory dict or None on no-op.

    No-ops when:
      - ``store_id_map`` is None or empty.
      - ``session.agent_name`` is missing.
      - The agent has no entry in ``store_id_map``.
    """
    if not store_id_map:
        return None
    agent_name = getattr(session, "agent_name", None)
    if not agent_name:
        return None
    store_id = store_id_map.get(agent_name)
    if not store_id:
        return None

    # Lazy import so callers that never hit this path don't pull memory.py in.
    from skyherd.agents.memory import get_memory_store_manager  # noqa: PLC0415
    from skyherd.agents.memory_paths import decide_write_path  # noqa: PLC0415

    try:
        path, content = decide_write_path(agent_name, wake_event, tool_calls)
    except ValueError as exc:
        logger.warning("decide_write_path rejected agent %s: %s", agent_name, exc)
        return None
    if not content:
        return None

    mgr = get_memory_store_manager()
    memory = await mgr.write_memory(store_id, path, content)

    # Dual-receipt pairing: Ed25519 ledger + SSE fan-out.
    if ledger is not None:
        try:
            # memver_id kwarg is Phase-4 only; fall back to the pre-Phase-4
            # signature if the underlying ledger does not support it.
            try:
                ledger.append(
                    source="memory",
                    kind="memver.written",
                    payload={
                        "agent": agent_name,
                        "memory_store_id": store_id,
                        "memory_id": memory.id,
                        "memory_version_id": memory.memory_version_id,
                        "content_sha256": memory.content_sha256,
                        "path": memory.path,
                    },
                    memver_id=memory.memory_version_id,
                )
            except TypeError:  # noqa: PERF203 — narrow compat fallback
                ledger.append(
                    source="memory",
                    kind="memver.written",
                    payload={
                        "agent": agent_name,
                        "memory_store_id": store_id,
                        "memory_id": memory.id,
                        "memory_version_id": memory.memory_version_id,
                        "content_sha256": memory.content_sha256,
                        "path": memory.path,
                    },
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ledger.append failed for memver %s: %s",
                memory.memory_version_id,
                type(exc).__name__,
            )

    if broadcaster is not None:
        try:
            broadcaster._broadcast(
                "memory.written",
                {
                    "agent": agent_name,
                    "memory_store_id": store_id,
                    "memory_id": memory.id,
                    "memory_version_id": memory.memory_version_id,
                    "content_sha256": memory.content_sha256,
                    "path": memory.path,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "broadcaster._broadcast failed for memver %s: %s",
                memory.memory_version_id,
                type(exc).__name__,
            )

    return memory.model_dump()


__all__ = ["post_cycle_write"]
