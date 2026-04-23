"""Memory API router — serves MemoryPanel.tsx (Plan 01-06).

Mirrors ``/api/attest`` response envelope shape (``{entries, ts}``).

Routes:
  GET /api/memory/{agent}          → {"agent", "entries", "ts", ...}
  GET /api/memory/{agent}/versions → {"agent", "entries", "ts", ...}

Whitelist guard: ``agent`` must be one of the 5 registered AGENT_NAMES —
returns 404 for anything else.

Mock mode: returns deterministic sample entries when ``use_mock=True`` or no
memory store manager is registered.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from skyherd.server.events import AGENT_NAMES

logger = logging.getLogger(__name__)

memory_router = APIRouter(prefix="/api/memory", tags=["memory"])

# Module-level state populated by attach_memory_api().
_state: dict[str, Any] = {
    "memory_store_manager": None,
    "store_id_map": {},
    "use_mock": False,
}


def _resolve_store_id(agent: str) -> str | None:
    store_id_map = _state.get("store_id_map") or {}
    return store_id_map.get(agent)


def _validate_agent(agent: str) -> None:
    if agent not in AGENT_NAMES:
        raise HTTPException(status_code=404, detail=f"unknown agent {agent!r}")


def _mock_memory_entry(agent: str, seq: int) -> dict[str, Any]:
    """Deterministic sample entry for mock mode."""
    h = f"{agent.lower()}{seq:02d}"
    return {
        "memory_id": f"mem_{h}",
        "memory_version_id": f"memver_{h}",
        "memory_store_id": f"memstore_{agent.lower()}_ranch_a",
        "path": f"/patterns/{agent.lower()}-sample.md",
        "content_sha256": h.ljust(64, "0"),
        "content_size_bytes": 128,
        "created_at": "1970-01-01T00:00:00Z",
        "operation": "created",
        "created_by": {"type": "api_actor", "api_key_id": "apikey_mock"},
    }


def _mock_entries_for(agent: str, count: int = 5) -> list[dict[str, Any]]:
    return [_mock_memory_entry(agent, i) for i in range(count)]


@memory_router.get("/{agent}")
async def api_memory(
    agent: str,
    path_prefix: str | None = Query(default=None),
) -> JSONResponse:
    _validate_agent(agent)
    if _state["use_mock"] or _state["memory_store_manager"] is None:
        return JSONResponse(content={
            "agent": agent,
            "entries": _mock_entries_for(agent),
            "ts": time.time(),
        })
    store_id = _resolve_store_id(agent)
    if not store_id:
        raise HTTPException(status_code=503, detail=f"no memory store registered for {agent}")
    try:
        envelope = await _state["memory_store_manager"].list_memories(
            store_id, path_prefix=path_prefix
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("list_memories failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="upstream memory list failed") from exc
    return JSONResponse(content={
        "agent": agent,
        "memory_store_id": store_id,
        "entries": envelope.data,
        "prefixes": envelope.prefixes or [],
        "ts": time.time(),
    })


@memory_router.get("/{agent}/versions")
async def api_memory_versions(agent: str) -> JSONResponse:
    _validate_agent(agent)
    if _state["use_mock"] or _state["memory_store_manager"] is None:
        return JSONResponse(content={
            "agent": agent,
            "entries": _mock_entries_for(agent),
            "ts": time.time(),
        })
    store_id = _resolve_store_id(agent)
    if not store_id:
        raise HTTPException(status_code=503, detail=f"no memory store registered for {agent}")
    try:
        versions = await _state["memory_store_manager"].list_versions(store_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("list_versions failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="upstream memory versions failed") from exc
    return JSONResponse(content={
        "agent": agent,
        "memory_store_id": store_id,
        "entries": [v.model_dump() for v in versions],
        "ts": time.time(),
    })


def attach_memory_api(
    app: Any,
    *,
    memory_store_manager: Any | None = None,
    store_id_map: dict[str, str] | None = None,
    use_mock: bool = False,
) -> None:
    """Wire dependencies into router module state + include router in the app."""
    _state["memory_store_manager"] = memory_store_manager
    _state["store_id_map"] = store_id_map or {}
    _state["use_mock"] = use_mock
    # Try to load cached IDs if not provided
    if not _state["store_id_map"]:
        cache = Path("runtime/memory_store_ids.json")
        if cache.exists():
            try:
                cached = json.loads(cache.read_text())
                if isinstance(cached, dict):
                    _state["store_id_map"] = {str(k): str(v) for k, v in cached.items()}
            except Exception as exc:  # noqa: BLE001
                logger.warning("memory_store_ids.json parse failed: %s", type(exc).__name__)
    app.include_router(memory_router)


__all__ = ["memory_router", "attach_memory_api"]
