"""MemoryStoreBase + MemoryStoreManager (REST) + LocalMemoryStore (JSONL shim).

The Anthropic SDK (anthropic==0.96.0) does NOT expose ``client.beta.memory_stores``.
Memory is REST-only for Python today: wrap ``client.post`` / ``client.get`` on the
AsyncAnthropic client so we reuse its auth, retries, and rate-limit handling.

Every REST call ships with the ``anthropic-beta: managed-agents-2026-04-01`` header
via the ``_opts()`` helper.

All memory paths are normalized to start with "/" — the live API requires this
(regex ``^(/[^/\x00]+)+$``; see docs/A1_PROBE_RESULT.md).

Runtime gate
------------
``get_memory_store_manager()`` mirrors ``get_session_manager``:
  - ``"local"``:   always LocalMemoryStore (in-process JSONL).
  - ``"managed"``: always MemoryStoreManager (raises if no API key).
  - ``"auto"``:    MemoryStoreManager iff ``SKYHERD_AGENTS=managed`` AND
                   ``ANTHROPIC_API_KEY`` is set; LocalMemoryStore otherwise.

Determinism
-----------
LocalMemoryStore IDs are content-derived via sha256. Same (store, path, content)
tuple yields the SAME ``memver_*`` ID. No datetime/uuid/time/random imports.

Reference: .planning/phases/01-memory-powered-agent-mesh/01-CONTEXT.md §spike_findings.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from skyherd.agents.managed import ManagedAgentsUnavailable

logger = logging.getLogger(__name__)

# Parameterized generic for SDK cast_to (bare dict crashes construct_type in
# anthropic._models:570 at `_, items_type = get_args(type_)`).
_RESP = dict[str, Any]

_BETA_HEADER = "managed-agents-2026-04-01"


# ---------------------------------------------------------------------------
# Pydantic models (mirror REST shapes from docs/A1_PROBE_RESULT.md)
# ---------------------------------------------------------------------------


class MemoryStore(BaseModel):
    model_config = {"extra": "allow"}
    id: str  # "memstore_<base62>"
    name: str
    description: str | None = None
    type: str = "memory_store"
    created_at: str
    updated_at: str
    archived_at: str | None = None


class Memory(BaseModel):
    model_config = {"extra": "allow"}
    id: str  # "mem_<base62>"
    memory_version_id: str  # "memver_<base62>"
    content_sha256: str
    content_size_bytes: int
    path: str
    created_at: str
    updated_at: str


class MemoryVersion(BaseModel):
    model_config = {"extra": "allow"}
    id: str  # "memver_<base62>"
    operation: Literal["created", "updated", "deleted", "redacted"]
    created_by: dict[str, Any]  # {"type":"api_actor","api_key_id":"apikey_..."}
    path: str
    content_sha256: str | None = None
    content_size_bytes: int | None = None
    redacted_by: dict[str, Any] | None = None


class ListEnvelope(BaseModel):
    model_config = {"extra": "allow"}
    data: list[dict[str, Any]]
    prefixes: list[str] | None = None


# ---------------------------------------------------------------------------
# Base interface
# ---------------------------------------------------------------------------


def _normalize_path(path: str) -> str:
    """Ensure path starts with '/' (live API requires regex ^(/[^/\x00]+)+$)."""
    if not path:
        return "/"
    return path if path.startswith("/") else "/" + path


class MemoryStoreBase:
    """Abstract contract; both MemoryStoreManager and LocalMemoryStore implement."""

    async def create_store(self, name: str, description: str | None = None) -> MemoryStore:
        raise NotImplementedError

    async def ensure_store(self, name: str, description: str | None = None) -> str:
        raise NotImplementedError

    async def list_stores(self) -> list[MemoryStore]:
        raise NotImplementedError

    async def archive_store(self, store_id: str) -> MemoryStore:
        raise NotImplementedError

    async def write_memory(self, store_id: str, path: str, content: str) -> Memory:
        raise NotImplementedError

    async def list_memories(self, store_id: str, path_prefix: str | None = None) -> ListEnvelope:
        raise NotImplementedError

    async def list_versions(
        self, store_id: str, memory_id: str | None = None
    ) -> list[MemoryVersion]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Real REST manager
# ---------------------------------------------------------------------------


class MemoryStoreManager(MemoryStoreBase):
    """Wraps raw REST calls via the AsyncAnthropic client."""

    def __init__(
        self,
        api_key: str | None = None,
        client: Any | None = None,
        store_ids_path: str = "runtime/memory_store_ids.json",
    ) -> None:
        _key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not _key and client is None:
            raise ManagedAgentsUnavailable(
                "ANTHROPIC_API_KEY not set — cannot initialise MemoryStoreManager."
            )

        if client is not None:
            self._client = client
        else:
            import anthropic  # noqa: PLC0415

            self._client = anthropic.AsyncAnthropic(api_key=_key)

        self._store_ids_path = Path(store_ids_path)
        self._store_ids: dict[str, str] = {}
        if self._store_ids_path.exists():
            try:
                cached = json.loads(self._store_ids_path.read_text())
                if isinstance(cached, dict):
                    self._store_ids = {str(k): str(v) for k, v in cached.items()}
            except Exception as exc:  # noqa: BLE001
                logger.warning("memory_store_ids.json parse failed: %s", type(exc).__name__)

    def _opts(self, extra_params: dict[str, Any] | None = None) -> Any:
        """Build RequestOptions dict for the anthropic SDK's client.post/get.

        Return type is ``Any`` because the SDK's ``RequestOptions`` is an internal
        TypedDict that callers aren't meant to import. The runtime shape is
        validated by the SDK; pyright would otherwise complain.
        """
        opts: dict[str, Any] = {"headers": {"anthropic-beta": _BETA_HEADER}}
        if extra_params:
            opts["params"] = extra_params
        return opts

    async def create_store(self, name: str, description: str | None = None) -> MemoryStore:
        body: dict[str, Any] = {"name": name}
        if description:
            body["description"] = description
        resp = await self._client.post(
            "/v1/memory_stores",
            cast_to=_RESP,
            body=body,
            options=self._opts(),
        )
        return MemoryStore.model_validate(resp)

    async def write_memory(self, store_id: str, path: str, content: str) -> Memory:
        norm = _normalize_path(path)
        resp = await self._client.post(
            f"/v1/memory_stores/{store_id}/memories",
            cast_to=_RESP,
            body={"path": norm, "content": content},
            options=self._opts(),
        )
        return Memory.model_validate(resp)

    async def list_memories(self, store_id: str, path_prefix: str | None = None) -> ListEnvelope:
        params = {"path_prefix": path_prefix} if path_prefix else None
        resp = await self._client.get(
            f"/v1/memory_stores/{store_id}/memories",
            cast_to=_RESP,
            options=self._opts(params),
        )
        return ListEnvelope.model_validate(resp)

    async def list_versions(
        self, store_id: str, memory_id: str | None = None
    ) -> list[MemoryVersion]:
        params = {"memory_id": memory_id} if memory_id else None
        resp = await self._client.get(
            f"/v1/memory_stores/{store_id}/memory_versions",
            cast_to=_RESP,
            options=self._opts(params),
        )
        return [MemoryVersion.model_validate(v) for v in resp.get("data", [])]

    async def list_stores(self) -> list[MemoryStore]:
        resp = await self._client.get(
            "/v1/memory_stores",
            cast_to=_RESP,
            options=self._opts(),
        )
        return [MemoryStore.model_validate(s) for s in resp.get("data", [])]

    async def archive_store(self, store_id: str) -> MemoryStore:
        resp = await self._client.post(
            f"/v1/memory_stores/{store_id}/archive",
            cast_to=_RESP,
            body={},
            options=self._opts(),
        )
        return MemoryStore.model_validate(resp)

    async def ensure_store(self, name: str, description: str | None = None) -> str:
        if name in self._store_ids:
            return self._store_ids[name]
        logger.info("Creating memory store %s…", name)
        store = await self.create_store(name=name, description=description)
        self._store_ids[name] = store.id
        self._store_ids_path.parent.mkdir(parents=True, exist_ok=True)
        self._store_ids_path.write_text(json.dumps(self._store_ids, indent=2))
        return store.id


# ---------------------------------------------------------------------------
# Local JSONL-backed shim (deterministic, zero HTTP)
# ---------------------------------------------------------------------------


_FROZEN_TS = "1970-01-01T00:00:00Z"


class LocalMemoryStore(MemoryStoreBase):
    """Deterministic in-process shim mirroring MemoryStoreBase.

    Writes append JSON lines to ``runtime/memory/{store_id}.jsonl`` for replay
    visibility. IDs are content-derived — byte-identical across runs.
    """

    def __init__(
        self,
        root: Path = Path("runtime/memory"),
        store_ids_path: str = "runtime/memory_store_ids.json",
    ) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._stores: dict[str, MemoryStore] = {}
        self._store_ids_path = Path(store_ids_path)
        self._store_ids: dict[str, str] = {}
        if self._store_ids_path.exists():
            try:
                cached = json.loads(self._store_ids_path.read_text())
                if isinstance(cached, dict):
                    self._store_ids = {str(k): str(v) for k, v in cached.items()}
            except Exception as exc:  # noqa: BLE001
                logger.warning("memory_store_ids.json parse failed: %s", type(exc).__name__)

    @staticmethod
    def _det_id(prefix: str, seed: str) -> str:
        return f"{prefix}_{hashlib.sha256(seed.encode()).hexdigest()[:20]}"

    async def create_store(self, name: str, description: str | None = None) -> MemoryStore:
        sid = self._det_id("memstore", name)
        store = MemoryStore(
            id=sid,
            name=name,
            description=description,
            type="memory_store",
            created_at=_FROZEN_TS,
            updated_at=_FROZEN_TS,
        )
        self._stores[sid] = store
        # Touch the jsonl so list_memories on an empty store works.
        path = self._root / f"{sid}.jsonl"
        if not path.exists():
            path.touch()
        return store

    async def ensure_store(self, name: str, description: str | None = None) -> str:
        if name in self._store_ids:
            sid = self._store_ids[name]
            if sid not in self._stores:
                # Reconstruct in-memory record for idempotent reads.
                self._stores[sid] = MemoryStore(
                    id=sid,
                    name=name,
                    description=description,
                    type="memory_store",
                    created_at=_FROZEN_TS,
                    updated_at=_FROZEN_TS,
                )
                (self._root / f"{sid}.jsonl").touch(exist_ok=True)
            return sid
        store = await self.create_store(name, description)
        self._store_ids[name] = store.id
        self._store_ids_path.parent.mkdir(parents=True, exist_ok=True)
        self._store_ids_path.write_text(json.dumps(self._store_ids, indent=2))
        return store.id

    async def write_memory(self, store_id: str, path: str, content: str) -> Memory:
        norm = _normalize_path(path)
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        mem_id = self._det_id("mem", f"{store_id}/{norm}")
        memver_id = self._det_id("memver", f"{store_id}/{norm}/{sha}")
        rec = Memory(
            id=mem_id,
            memory_version_id=memver_id,
            content_sha256=sha,
            content_size_bytes=len(content.encode("utf-8")),
            path=norm,
            created_at=_FROZEN_TS,
            updated_at=_FROZEN_TS,
        )
        jsonl_path = self._root / f"{store_id}.jsonl"
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {**rec.model_dump(), "content": content, "store_id": store_id},
            sort_keys=True,
        )
        with jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return rec

    async def list_memories(self, store_id: str, path_prefix: str | None = None) -> ListEnvelope:
        jsonl_path = self._root / f"{store_id}.jsonl"
        if not jsonl_path.exists():
            return ListEnvelope(data=[], prefixes=[])
        # Collapse to latest-per-path (later overwrites earlier).
        latest: dict[str, dict[str, Any]] = {}
        for raw in jsonl_path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            p = rec.get("path", "")
            if path_prefix and not p.startswith(_normalize_path(path_prefix)):
                # Also accept un-normalized prefix
                if not p.startswith(path_prefix):
                    continue
            latest[p] = rec
        data = sorted(latest.values(), key=lambda r: r.get("path", ""))
        prefixes = sorted({p.split("/", 2)[1] + "/" if "/" in p.lstrip("/") else p for p in latest})
        return ListEnvelope(data=data, prefixes=prefixes)

    async def list_versions(
        self, store_id: str, memory_id: str | None = None
    ) -> list[MemoryVersion]:
        jsonl_path = self._root / f"{store_id}.jsonl"
        if not jsonl_path.exists():
            return []
        out: list[MemoryVersion] = []
        for raw in jsonl_path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if memory_id is not None and rec.get("id") != memory_id:
                continue
            out.append(
                MemoryVersion(
                    id=rec["memory_version_id"],
                    operation="created",
                    created_by={"type": "api_actor", "api_key_id": "apikey_local_shim"},
                    path=rec["path"],
                    content_sha256=rec.get("content_sha256"),
                    content_size_bytes=rec.get("content_size_bytes"),
                )
            )
        return out

    async def archive_store(self, store_id: str) -> MemoryStore:
        if store_id in self._stores:
            self._stores[store_id] = self._stores[store_id].model_copy(
                update={"archived_at": _FROZEN_TS}
            )
            return self._stores[store_id]
        # Unknown store: return a minimal object.
        return MemoryStore(
            id=store_id,
            name="unknown",
            type="memory_store",
            created_at=_FROZEN_TS,
            updated_at=_FROZEN_TS,
            archived_at=_FROZEN_TS,
        )

    async def list_stores(self) -> list[MemoryStore]:
        return [s for s in self._stores.values() if s.archived_at is None]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_memory_store_manager(runtime: str = "auto") -> MemoryStoreBase:
    """Return MemoryStoreBase implementation — mirrors get_session_manager contract."""
    if runtime == "local":
        return LocalMemoryStore()
    if runtime == "managed":
        return MemoryStoreManager()
    # auto
    if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("SKYHERD_AGENTS") == "managed":
        try:
            return MemoryStoreManager()
        except ManagedAgentsUnavailable as exc:
            logger.warning(
                "MemoryStoreManager unavailable (%s) — falling back to LocalMemoryStore",
                exc,
            )
    return LocalMemoryStore()


__all__ = [
    "ListEnvelope",
    "LocalMemoryStore",
    "Memory",
    "MemoryStore",
    "MemoryStoreBase",
    "MemoryStoreManager",
    "MemoryVersion",
    "get_memory_store_manager",
]
