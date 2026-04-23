# Phase 1: Memory-Powered Agent Mesh - Research

**Researched:** 2026-04-23
**Domain:** Anthropic Managed Agents Memory beta adoption + 5-agent mesh integration
**Confidence:** HIGH (spike-verified REST surface + live SDK introspection)

## Summary

Adopt the Claude Managed Agents Memory public beta (shipped 2026-04-23) across SkyHerd's 5-agent mesh with judge-visible dashboard receipts, shipping in a 72-hour window while preserving determinism, prompt caching, and MIT compliance. The SDK (`anthropic==0.96.0`) does NOT expose `client.beta.memory_stores.*` — Memory is REST-only today — but `client.post()` / `client.get()` on the existing Anthropic client wrap raw HTTP cleanly and reuse auth/retries. Session-level attachment works through the already-supported `resources=` kwarg at `managed.py:240`, with a **type workaround** required because the SDK's `Resource` union lacks `memory_store` (use `extra_body={"resources":[...]}` to smuggle unknown resource types past Stainless's TypedDict validation).

**Primary recommendation:** Ship a ~220-line `MemoryStoreManager` that wraps `client.post`/`client.get` with Pydantic response models mirroring the REST spike (CONTEXT `<spike_findings>`); gate all REST calls behind `SKYHERD_AGENTS=="managed"` via a zero-network `LocalMemoryStore` JSONL shim; thread memory reads/writes through a post-tool-execution hook in `_handler_base.py` (NOT an MCP server — simpler for demo); add `memory.written` / `memory.read` SSE events; mirror `AttestationPanel.tsx` exactly for `MemoryPanel.tsx`. No agent hand-rolls memory logic — they see it via a post-cycle mesh hook that summarises the wake cycle and writes one memver per cycle per agent.

## User Constraints (from CONTEXT.md)

### Locked Decisions

Inherited from v1.0 and CONTEXT.md `<decisions>` block:

- **Beta header** — `managed-agents-2026-04-01` remains; Memory rides on the same header (no new beta flag). SDK auto-applies.
- **Prompt caching** — every `messages.create` / `sessions.events.send` must emit `cache_control: ephemeral`. Non-negotiable.
- **Determinism** — `make demo SEED=42 SCENARIO=all` byte-identical across 3 replays; wall-timestamps sanitized. Memory calls stubbed in local runtime; real calls only when `SKYHERD_AGENTS=managed`.
- **Coverage floor** — ≥ 80% (`fail_under = 80`). New `memory_*.py` files target ≥ 90% coverage.
- **Licensing** — MIT only; zero AGPL.
- **Attribution** — zero Claude/Anthropic attribution on commits (global git config).

### Design Choices (pre-decided)

- **Store topology** — `memstore_ranch_a_shared` (read-only, domain library) + 5 per-agent `memstore_<agent>_<ranch>` (read_write). Workspace-scoped per Anthropic docs.
- **Path convention** — `/patterns/<topic>.md` for shared; `/notes/<entity_id>.md` and `/baselines/<metric>.md` for per-agent.
- **Memory vs Skills** — Skills stay packaged/versioned domain knowledge (CrossBeam pattern); Memory is mutable learned facts. No skill → memory migration.
- **Attestation** — Memory `memver_…` chain complements Ed25519 ledger; both logged on every write. The "two independent receipts agree" demo moment.
- **Toolset disable** — CalvingWatch + GrazingOptimizer disable `web_search`/`web_fetch` via `configs` array at `agents.create()`.

### Claude's Discretion

All implementation choices not listed above (module layout, helper shapes, caching strategy, test layout, write-hook placement) are at Claude's discretion per `workflow.skip_discuss=true`.

### Deferred Ideas (OUT OF SCOPE)

- Callable agents / multi-agent threads (research preview — skip unless access arrives before Sat).
- Advisor tool (`advisor-tool-2026-03-01`).
- Memory export endpoint (tarball dump).
- Memory redaction UI (admin panel for `memory_versions.redact()`).
- Cross-ranch memory sharing (`memstore_ranch_b_shared`).
- Memory → Skills promotion pipeline.

## Project Constraints (from CLAUDE.md)

- **Sim-first hardline** — no hardware code until Sim Gate passes (PASSED Apr 22).
- **All code new** — no imports from `/home/george/projects/active/drone/`.
- **MIT throughout** — zero AGPL deps (blocks Ultralytics/YOLOv12).
- **TDD** — tests first, 80% floor, 90% floor for new `memory_*.py`.
- **Skills-first** — domain knowledge in `skills/*.md`, not agent system prompts.
- **Prompt caching mandatory** — every `messages.create`/`sessions.events.send` emits `cache_control: ephemeral` on system + skills prefix.
- **No attribution in commits**.
- **Determinism** — `make demo SEED=42 SCENARIO=all` byte-identical across replays.
- **GSD workflow** — no direct edits outside a GSD workflow.

## Phase Requirements

Derived from ROADMAP Phase 1 scope + CONTEXT specifics. These become the seed REQ- IDs for the planner.

| ID | Description | Research Support |
|----|-------------|------------------|
| MEM-01 | 6 memory stores created idempotently: 1 `memstore_ranch_a_shared` (read-only domain) + 5 per-agent RW stores | REST spike: `POST /v1/memory_stores`; ID cached in `runtime/memory_store_ids.json` (mirror `runtime/agent_ids.json` pattern) |
| MEM-02 | Session creation attaches `resources=[{type:memory_store, memory_store_id, mode}]` to all 5 agents | `managed.py:240` `sessions.create(resources=...)` kwarg exists; use `extra_body` to bypass SDK type check (memory_store not in `Resource` union in anthropic 0.96.0) |
| MEM-03 | `MemoryStoreManager` wraps REST via `client.post`/`client.get`; Pydantic response models; ≥90% cov | Anthropic 0.96 `client.post(path, cast_to=..., body=...)` reuses retry/rate-limit + auth; confirmed via introspection |
| MEM-04 | `LocalMemoryStore` shim — dict + `runtime/memory/{store_id}.jsonl` — exact REST response shape parity | Decision C (hybrid pattern); JSONL for replay visibility; determinism guard |
| MEM-05 | Write hooks — PredatorPatternLearner writes `patterns/coyote-crossings.md`; HerdHealthWatcher writes `notes/{cow_tag}.md`; CalvingWatch writes `baselines/{cow_tag}.md`; FenceLineDispatcher reads `patterns/` pre-dispatch | Post-cycle mesh hook in `_handler_base.py` — no per-agent code duplication |
| MEM-06 | `/api/memory/{agent}` endpoint in `server/memory_api.py`; mirrors `/api/attest` pattern | `server/app.py:159-165` is the template; Pydantic response envelope matches AttestationPanel |
| MEM-07 | `MemoryPanel.tsx` — 5-agent tab switcher, memver chips, HashChip pattern, live `memory.written`/`memory.read` animation | `AttestationPanel.tsx:48-113` HashChip is the canonical pattern; mount after AttestationPanel in grid |
| MEM-08 | SSE event types `memory.written` / `memory.read` registered in `web/src/lib/sse.ts:eventTypes` (line 69-81) + broadcasted from `server/events.py` | Mirror `attest.append` wiring |
| MEM-09 | Determinism preserved — `make demo SEED=42 SCENARIO=all` 3-run sanitized md5 match holds | `tests/test_determinism_e2e.py` sanitizer regex already strips hex UUIDs + ISO timestamps; `memver_<base62>` IDs must also be sanitized |
| MEM-10 | Attestation pairing — every memver write logs to Ed25519 ledger with `{memver_id, memstore_id, path, content_sha256}` payload | `Ledger.append(source="memory", kind="memver.written", payload={...})` at `attest/ledger.py:167` |
| MEM-11 | Toolset selective disable — CalvingWatch + GrazingOptimizer `tools=[{"type":"agent_toolset_20260401", "configs":[{"name":"web_search","enabled":false}, {"name":"web_fetch","enabled":false}]}]` | Platform side of determinism guard; `managed.py:216-223` already has `tools=[...]` scaffold |
| MEM-12 | `make mesh-smoke` exercises both local + managed memory paths | Mirror existing `tests/agents/test_managed.py` dual-runtime pattern |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Memory REST calls (create/list/read/write/archive stores + memories) | API/Backend (Python `memory.py`) | — | All `x-api-key` HTTP — server-only; never reach browser |
| Memory gate decision (managed vs local shim) | API/Backend (`memory.py:get_memory_store_manager`) | — | Same pattern as `get_session_manager()` in `session.py:391` |
| Memory write hook — per-cycle summarisation | API/Backend (mesh post-cycle hook in `_handler_base.py`) | — | Keeps agent handlers memory-unaware; one codepath to maintain |
| `memory.written` SSE broadcast | API/Backend (`server/events.py` broadcaster) | Browser (SSE consumer) | EventBroadcaster polls + mesh callback feeds it |
| Memory Panel UI — per-agent tabs + memver feed | Browser (`MemoryPanel.tsx`) | API/Backend (`/api/memory/{agent}`) | Parallel to AttestationPanel; fetches on mount + live SSE |
| Memver HashChip (4-swatch fingerprint + click-to-copy) | Browser (reuse `HashChip` from AttestationPanel) | — | Zero duplication — extract to shared component first |
| Attestation pairing (memver + Ed25519 ledger) | API/Backend (post-cycle hook) | — | Both receipts written server-side before SSE fan-out |
| Determinism gate (no HTTP under SEED=42) | API/Backend (`memory.py` runtime check) | Test infra (`tests/test_determinism_e2e.py`) | Single env var gate; test runs without `SKYHERD_AGENTS=managed` |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | `0.96.0` (verified `uv run python -c "import anthropic; print(anthropic.__version__)"` 2026-04-23) [VERIFIED] | `client.post`/`client.get` for raw HTTP + existing `beta.sessions.create` | Already installed; `pyproject.toml:16` pins `anthropic>=0.69,<1` |
| `pydantic` | v2 (already used) [VERIFIED] | Response envelope models mirroring REST shapes | Existing `WorldSnapshot`, `Event`, `VerifyResult` use Pydantic v2 |
| `httpx` | bundled by `anthropic` [VERIFIED] | HTTP transport under `client.post` | Do not add direct dep — route via `client.*` for auth/retries |
| `fastapi` | already used [VERIFIED] | `/api/memory/{agent}` endpoint | `server/app.py` factory pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sse-starlette` | already used | `memory.written` / `memory.read` SSE events | `server/app.py:41` already imports |
| `react` `19` + Tailwind v4 | already used | MemoryPanel component | Mirror AttestationPanel styling |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `client.post(path, cast_to=..., body=...)` raw HTTP | Direct `httpx.AsyncClient` with manual headers | Loses SDK retry/rate-limit/timeout handling; forces duplicate auth logic — rejected |
| Wait for `client.beta.memory_stores.*` SDK surface | Ship now with raw HTTP | SDK may ship Mon/Tue but we submit Sun 6pm — cannot block — **ship raw HTTP, easy swap** |
| MCP server `memory_mcp.py` with `memory_write` / `memory_read` tools | Post-cycle mesh hook | MCP route needs prompt changes to make agents call tools; mesh hook works uniformly across 5 agents with zero prompt/system churn — **mesh hook wins for 72hr scope** |
| `resources=[...]` via typed SDK param | `extra_body={"resources":[...]}` | SDK 0.96 `Resource` TypeAlias excludes `memory_store` — typed call raises; `extra_body` is the supported escape hatch — **use extra_body** |
| Memory as replacement for Skills | Skills stay in place | CrossBeam prize pattern would regress; Skills = versioned, Memory = mutable — **keep both** (decision locked) |

**Installation:**

```bash
# No new deps. All already present.
uv sync
# Verify:
uv run python -c "import anthropic; print(anthropic.__version__)"  # expect 0.96.0
```

**Version verification** (verified 2026-04-23 via live introspection):

- `anthropic==0.96.0` exposes `client.post`, `client.get`, `client.request` on sync + async clients [VERIFIED: inspection]
- `client.beta.sessions.create(resources=...)` accepts `Iterable[Resource]` — but `Resource = Union[GitHubRepository, File]` only. Memory_store is not in the union. [VERIFIED: inspection of `anthropic.types.beta.session_create_params`]
- Workaround: `extra_body={"resources":[{"type":"memory_store","memory_store_id":"memstore_..."}]}` — SDK merges `extra_body` into the POST payload [VERIFIED: `client.beta.sessions.create` accepts `extra_body: Body | None`]
- `client.beta.memory_stores` does NOT exist on SDK 0.96.0 [VERIFIED: CONTEXT spike]

## Architecture Patterns

### System Architecture Diagram

```
 MQTT sensor event
       |
       v
 AgentMesh._mqtt_loop  -->  SessionManager.on_webhook  -->  wake session
       |
       v
 _run_handler(session, event, handler_fn)                        (mesh.py:241)
       |
       |--> handler_fn (fenceline/health/predator/grazing/calving)
       |        |
       |        v
       |   build_cached_messages(system, skills, user)  -->  run_handler_cycle
       |                                                          |
       |                                                   local:  messages.create(cache_control)
       |                                                   managed: sessions.events.stream
       |                                                          |
       |                                                          v
       |                                                   tool calls list
       |
       |-- NEW: memory post-cycle hook ----------------------------+
       |        |                                                  |
       |        |  summarise(session.agent_name, event, tool_calls)
       |        |  decide_path() -> "patterns/..." or "notes/..." or "baselines/..."
       |        |                                                  |
       |        |                                                  v
       |        |   MemoryStoreManager.write(store_id, path, content)
       |        |        |              |
       |        |        |   managed: POST /v1/memory_stores/{id}/memories
       |        |        |   local:   append JSONL to runtime/memory/{store_id}.jsonl
       |        |        |
       |        |        v
       |        |   returns { mem_id, memver_id, content_sha256, path }
       |        |
       |        |-- Ledger.append(source="memory", kind="memver.written", payload)   (attest/ledger.py:167)
       |        |
       |        |-- EventBroadcaster emit "memory.written"   (server/events.py)
       |        |
       |        v
 sleep session                                                 (mesh.py:253)

 Dashboard path:
   MemoryPanel.tsx  ----fetch---->  GET /api/memory/{agent}   (server/memory_api.py)
                                          |
                                          v
                                    MemoryStoreManager.list_memories(store_id)
                                          |
                                          v
                                    managed: GET /v1/memory_stores/{id}/memories
                                    local:   read runtime/memory/{store_id}.jsonl
                     --SSE "memory.written"-->  append to live feed with flash animation
```

### Recommended Project Structure (new files)

```
src/skyherd/
├── agents/
│   ├── memory.py           # MemoryStoreManager (REST + local shim via a single interface)
│   ├── memory_paths.py     # path conventions + redaction helpers
│   ├── memory_hook.py      # post-cycle write hook called from _handler_base
│   └── managed.py          # MODIFY: attach resources[] + tools configs
├── server/
│   ├── memory_api.py       # /api/memory/{agent} endpoint
│   └── events.py           # MODIFY: broadcast memory.written / memory.read
web/src/
├── components/
│   ├── MemoryPanel.tsx           # mirror AttestationPanel.tsx exactly
│   ├── MemoryPanel.test.tsx
│   └── shared/HashChip.tsx       # extract from AttestationPanel (refactor)
├── lib/sse.ts                    # MODIFY: eventTypes += ["memory.written","memory.read"]
tests/
├── agents/
│   ├── test_memory.py            # unit tests (stubbed SDK via httpx.MockTransport)
│   ├── test_memory_hook.py       # write hook behaviour under local + managed
│   └── test_memory_determinism.py  # assert no HTTP under SEED=42
├── server/
│   └── test_memory_api.py
runtime/
├── memory/
│   └── {store_id}.jsonl          # LocalMemoryStore backing files (gitignored)
└── memory_store_ids.json         # cached store_id map (created on first managed run)
```

### Pattern 1: MemoryStoreManager (raw-HTTP wrapper)

**What:** Single class with sync + async facets that wraps REST Memory API via `client.post`/`client.get`, parses into Pydantic models mirroring the spike-verified shapes. Exposes the same public surface as `LocalMemoryStore` so callers (hook + API endpoint) are runtime-agnostic.
**When to use:** When `SKYHERD_AGENTS=="managed"` and `ANTHROPIC_API_KEY` is set.
**Example:**

```python
# src/skyherd/agents/memory.py   (~220 lines, target ≥90% coverage)
# Source: REST spike in CONTEXT.md <spike_findings>; client.post signature
# verified from anthropic==0.96.0 inspection 2026-04-23

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

# ---------- Pydantic models mirroring REST shapes ----------

class MemoryStore(BaseModel):
    id: str                        # memstore_018S1WJAA5mpXW9mTH3YXqzE
    name: str
    description: str | None = None
    type: str = "memory_store"
    created_at: str
    updated_at: str
    archived_at: str | None = None

class Memory(BaseModel):
    id: str                        # mem_0126mdrYVnARX4Q9iteMiNaB
    memory_version_id: str         # memver_01XRSVdKC1McTbhVbVF5T47E
    content_sha256: str
    content_size_bytes: int
    path: str
    created_at: str
    updated_at: str

class MemoryVersion(BaseModel):
    id: str                        # memver_01XRSVdKC1McTbhVbVF5T47E
    operation: Literal["created", "updated", "deleted", "redacted"]
    created_by: dict[str, Any]     # {"type": "api_actor", "api_key_id": "apikey_..."}
    path: str
    content_sha256: str | None = None
    content_size_bytes: int | None = None
    redacted_by: dict[str, Any] | None = None

class ListEnvelope(BaseModel):
    data: list[dict[str, Any]]
    prefixes: list[str] | None = None

# ---------- Base interface ----------

class MemoryStoreBase:
    async def create_store(self, name: str, description: str | None = None) -> MemoryStore: ...
    async def list_stores(self) -> list[MemoryStore]: ...
    async def archive_store(self, store_id: str) -> MemoryStore: ...
    async def write_memory(self, store_id: str, path: str, content: str) -> Memory: ...
    async def list_memories(self, store_id: str, path_prefix: str | None = None) -> ListEnvelope: ...
    async def list_versions(self, store_id: str, memory_id: str | None = None) -> list[MemoryVersion]: ...

# ---------- Managed (live REST) ----------

class MemoryStoreManager(MemoryStoreBase):
    """Real REST client — gated on SKYHERD_AGENTS=="managed" + ANTHROPIC_API_KEY."""

    def __init__(self, client: Any | None = None) -> None:
        import anthropic
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            from skyherd.agents.managed import ManagedAgentsUnavailable
            raise ManagedAgentsUnavailable("ANTHROPIC_API_KEY not set for MemoryStoreManager")
        self._client = client or anthropic.AsyncAnthropic(api_key=key)

    async def create_store(self, name: str, description: str | None = None) -> MemoryStore:
        body: dict[str, Any] = {"name": name}
        if description:
            body["description"] = description
        # anthropic client.post adds x-api-key + anthropic-version automatically.
        # We must inject the beta header explicitly — NOT managed-agents-2026-04-01-only;
        # the spike used it and got 200s.
        resp = await self._client.post(
            "/v1/memory_stores",
            cast_to=dict,  # raw dict; we parse via Pydantic after
            body=body,
            options={"headers": {"anthropic-beta": "managed-agents-2026-04-01"}},
        )
        return MemoryStore.model_validate(resp)

    async def write_memory(self, store_id: str, path: str, content: str) -> Memory:
        resp = await self._client.post(
            f"/v1/memory_stores/{store_id}/memories",
            cast_to=dict,
            body={"path": path, "content": content},
            options={"headers": {"anthropic-beta": "managed-agents-2026-04-01"}},
        )
        return Memory.model_validate(resp)

    async def list_memories(self, store_id: str, path_prefix: str | None = None) -> ListEnvelope:
        params: dict[str, Any] = {}
        if path_prefix:
            params["path_prefix"] = path_prefix
        resp = await self._client.get(
            f"/v1/memory_stores/{store_id}/memories",
            cast_to=dict,
            options={
                "headers": {"anthropic-beta": "managed-agents-2026-04-01"},
                "params": params,
            },
        )
        return ListEnvelope.model_validate(resp)

    async def list_versions(self, store_id: str, memory_id: str | None = None) -> list[MemoryVersion]:
        params: dict[str, Any] = {}
        if memory_id:
            params["memory_id"] = memory_id
        resp = await self._client.get(
            f"/v1/memory_stores/{store_id}/memory_versions",
            cast_to=dict,
            options={
                "headers": {"anthropic-beta": "managed-agents-2026-04-01"},
                "params": params,
            },
        )
        return [MemoryVersion.model_validate(v) for v in resp.get("data", [])]

    async def archive_store(self, store_id: str) -> MemoryStore:
        resp = await self._client.post(
            f"/v1/memory_stores/{store_id}/archive",
            cast_to=dict,
            body={},
            options={"headers": {"anthropic-beta": "managed-agents-2026-04-01"}},
        )
        return MemoryStore.model_validate(resp)

# ---------- Local shim (JSONL-backed, exact REST shape) ----------

class LocalMemoryStore(MemoryStoreBase):
    """Deterministic file-backed shim — same API as MemoryStoreManager, zero network.

    Writes to runtime/memory/{store_id}.jsonl for replay visibility.
    IDs are content-derived (sha256-prefixed) so seed=42 determinism survives.
    """
    def __init__(self, root: Path = Path("runtime/memory")) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._stores: dict[str, MemoryStore] = {}

    @staticmethod
    def _det_id(prefix: str, seed: str) -> str:
        import hashlib
        return f"{prefix}_{hashlib.sha256(seed.encode()).hexdigest()[:20]}"

    async def create_store(self, name: str, description: str | None = None) -> MemoryStore:
        sid = self._det_id("memstore", name)
        store = MemoryStore(
            id=sid, name=name, description=description,
            created_at="1970-01-01T00:00:00Z",   # deterministic; sanitizer strips ISO anyway
            updated_at="1970-01-01T00:00:00Z",
        )
        self._stores[sid] = store
        (self._root / f"{sid}.jsonl").touch()
        return store

    async def write_memory(self, store_id: str, path: str, content: str) -> Memory:
        import hashlib
        sha = hashlib.sha256(content.encode()).hexdigest()
        mem_id = self._det_id("mem", f"{store_id}/{path}")
        memver_id = self._det_id("memver", f"{store_id}/{path}/{sha}")
        rec = Memory(
            id=mem_id, memory_version_id=memver_id,
            content_sha256=sha, content_size_bytes=len(content),
            path=path,
            created_at="1970-01-01T00:00:00Z",
            updated_at="1970-01-01T00:00:00Z",
        )
        line = json.dumps({**rec.model_dump(), "content": content, "store_id": store_id})
        with (self._root / f"{store_id}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return rec

    # ... list_memories reads JSONL, list_versions walks JSONL, etc.

# ---------- Factory (mirrors get_session_manager pattern) ----------

def get_memory_store_manager(runtime: str = "auto") -> MemoryStoreBase:
    """runtime: 'local' | 'managed' | 'auto' (= managed iff SKYHERD_AGENTS=managed+key)"""
    if runtime == "local":
        return LocalMemoryStore()
    if runtime == "managed":
        return MemoryStoreManager()
    if os.environ.get("SKYHERD_AGENTS") == "managed" and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return MemoryStoreManager()
        except Exception:
            pass
    return LocalMemoryStore()
```

### Pattern 2: Session-Level Resource Attachment (`extra_body` workaround)

**What:** The SDK 0.96 `Resource` TypedDict union doesn't know about `memory_store`. Attach via `extra_body` which the SDK merges into the POST payload.
**When to use:** Every `client.beta.sessions.create()` call in managed runtime.
**Example:**

```python
# src/skyherd/agents/managed.py — MODIFY around line 240

async def create_session_async(self, agent_spec: Any) -> ManagedSession:
    agent_id = await self.ensure_agent(agent_spec)
    env_id = await self._ensure_environment()

    # NEW — resolve memory store IDs for this agent (self._memory_store_ids populated
    # by AgentMesh.start() via MemoryStoreManager.create_store())
    per_agent_store_id = self._memory_store_ids.get(agent_spec.name)
    shared_store_id = self._memory_store_ids.get("_shared")

    resources: list[dict[str, Any]] = []
    if per_agent_store_id:
        resources.append({
            "type": "memory_store",
            "memory_store_id": per_agent_store_id,
            "mode": "read_write",
        })
    if shared_store_id:
        resources.append({
            "type": "memory_store",
            "memory_store_id": shared_store_id,
            "mode": "read_only",
        })

    # WORKAROUND: SDK Resource union lacks memory_store; smuggle via extra_body.
    # Verified 2026-04-23: client.beta.sessions.create(extra_body=...) is supported
    # and extra_body values merge into the request payload.
    platform_session = await self._client.beta.sessions.create(
        agent=agent_id,
        environment_id=env_id,
        title=f"skyherd-{agent_spec.name}",
        extra_body={"resources": resources} if resources else None,
    )
    # ... rest unchanged
```

**Why not the typed `resources=` kwarg:** `Resource = Union[BetaManagedAgentsGitHubRepositoryResourceParams, BetaManagedAgentsFileResourceParams]` in `anthropic.types.beta.session_create_params` [VERIFIED: inspection]. Passing a memory_store dict via the typed param causes Stainless's TypedDict runtime check to fail. `extra_body` bypasses this cleanly.

### Pattern 3: Per-Cycle Mesh Hook (the judge-visible moment)

**What:** After `run_handler_cycle` completes in `_handler_base.py`, emit ONE memory write per agent per cycle summarising what the cycle learned. Zero changes to per-agent handler files. Zero prompt changes.
**When to use:** Every wake cycle (both local and managed runtimes — local writes to JSONL, managed writes to REST).
**Example:**

```python
# src/skyherd/agents/memory_hook.py  (new, ~90 lines)

from __future__ import annotations
from typing import Any
from skyherd.agents.memory import get_memory_store_manager
from skyherd.agents.memory_paths import decide_write_path

async def post_cycle_write(
    session: Any,
    wake_event: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    ledger: Any | None = None,
    broadcaster: Any | None = None,
    store_id_map: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Write one memory per wake cycle. Idempotent — no-op if content is empty.

    Returns the Memory record (or None) so tests can assert.
    """
    if store_id_map is None:
        return None
    store_id = store_id_map.get(session.agent_name)
    if not store_id:
        return None

    path, content = decide_write_path(session.agent_name, wake_event, tool_calls)
    if not content:
        return None

    mgr = get_memory_store_manager()
    memory = await mgr.write_memory(store_id, path, content)

    # Attestation pairing — the "two independent receipts agree" demo moment.
    if ledger is not None:
        ledger.append(
            source="memory",
            kind="memver.written",
            payload={
                "agent": session.agent_name,
                "memory_store_id": store_id,
                "memory_id": memory.id,
                "memory_version_id": memory.memory_version_id,
                "content_sha256": memory.content_sha256,
                "path": memory.path,
            },
        )

    # SSE fan-out — drives MemoryPanel flash animation
    if broadcaster is not None:
        await broadcaster.emit(
            "memory.written",
            {
                "agent": session.agent_name,
                "memory_store_id": store_id,
                "memory_id": memory.id,
                "memory_version_id": memory.memory_version_id,
                "path": memory.path,
                "content_sha256": memory.content_sha256,
            },
        )

    return memory.model_dump()
```

```python
# src/skyherd/agents/memory_paths.py (new, ~80 lines)

from typing import Any
from datetime import UTC, datetime

_REDACT_KEYS = {"rancher_phone", "vet_phone", "auth_token"}

def _redact(d: dict[str, Any]) -> dict[str, Any]:
    return {k: ("[REDACTED]" if k in _REDACT_KEYS else v) for k, v in d.items()}

def decide_write_path(agent_name: str, event: dict[str, Any], tool_calls: list[dict[str, Any]]) -> tuple[str, str]:
    """Map (agent, event, tool_calls) -> (memory_path, content)."""
    ts = datetime.fromtimestamp(0, UTC).isoformat()  # stable in sim
    ranch = event.get("ranch_id", "ranch_a")
    if agent_name == "PredatorPatternLearner":
        # Shared patterns/ writes — coyote crossings / mountain lion / etc.
        species = event.get("classification", event.get("type", "unknown")).split(".")[0]
        return (
            f"patterns/{species}-crossings.md",
            f"# {species.title()} crossing observed\n\nRanch: {ranch}\nEvent: {event.get('type')}\n"
            f"Tools called: {[t['tool'] for t in tool_calls]}\n",
        )
    if agent_name == "HerdHealthWatcher":
        tag = event.get("tag") or event.get("trough_id", "unknown")
        return (f"notes/{tag}.md", f"# Observation for {tag}\n\nEvent: {event.get('type')}\n")
    if agent_name == "CalvingWatch":
        tag = event.get("tag", "unknown")
        return (f"baselines/{tag}.md", f"# Calving baseline for {tag}\n\nEvent: {event.get('type')}\n")
    if agent_name == "FenceLineDispatcher":
        # Writes outcomes of dispatches; reads patterns/ pre-dispatch (separate call)
        seg = event.get("segment", "unknown")
        return (f"notes/dispatch-{seg}.md", f"# Dispatch log for {seg}\n")
    # GrazingOptimizer
    return ("notes/rotation-proposal.md", f"# Rotation proposal\n\nRanch: {ranch}\n")
```

Integrate in `_handler_base.py:run_handler_cycle`:

```python
# _handler_base.py — append at the end of run_handler_cycle, before returning:

tool_calls = ... # existing logic

# NEW — memory post-cycle hook (non-blocking; never raises into caller)
from skyherd.agents.memory_hook import post_cycle_write
try:
    store_id_map = getattr(session, "_memory_store_id_map", None)
    ledger = getattr(session, "_ledger_ref", None)
    broadcaster = getattr(session, "_broadcaster_ref", None)
    await post_cycle_write(session, wake_event, tool_calls, ledger, broadcaster, store_id_map)
except Exception as exc:  # noqa: BLE001
    logger.warning("memory post-cycle write failed for %s: %s", session.agent_name, exc)

return tool_calls
```

`AgentMesh.start()` populates `session._memory_store_id_map`, `session._ledger_ref`, `session._broadcaster_ref` after store creation.

### Pattern 4: REST endpoint + SSE event — mirror `/api/attest`

```python
# src/skyherd/server/memory_api.py (new, ~70 lines)

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from skyherd.agents.memory import get_memory_store_manager

memory_router = APIRouter()

_AGENT_TO_STORE: dict[str, str] = {}  # populated from runtime/memory_store_ids.json at app startup

@memory_router.get("/api/memory/{agent}")
async def api_memory(agent: str, path_prefix: str | None = Query(default=None)) -> JSONResponse:
    """Return recent memories + versions for an agent. Mirrors /api/attest shape."""
    store_id = _AGENT_TO_STORE.get(agent)
    if not store_id:
        raise HTTPException(status_code=404, detail=f"no memory store for agent {agent!r}")
    mgr = get_memory_store_manager()
    memories = await mgr.list_memories(store_id, path_prefix=path_prefix)
    versions = await mgr.list_versions(store_id)
    return JSONResponse(content={
        "agent": agent,
        "memory_store_id": store_id,
        "memories": memories.model_dump(),
        "versions": [v.model_dump() for v in versions],
    })
```

Register `memory_router` in `create_app()` at `server/app.py:120` alongside the existing webhook router include.

### Anti-Patterns to Avoid

- **MCP server for memory reads/writes** — forces prompt engineering to make all 5 agents remember to call `memory_read`/`memory_write`. Works long-term, wrong scope for 72hr.
- **Synchronous `anthropic.Anthropic` for memory calls inside async handlers** — blocks the asyncio loop. Use `AsyncAnthropic`.
- **Direct `httpx.AsyncClient`** — loses retries/rate-limit/auth; duplicates what `client.post` already does.
- **Typed `resources=[{...}]` kwarg with memory_store** — TypedDict validation rejects; use `extra_body`.
- **Writing memory in per-agent handler files** — creates 5 parallel code paths. Use the shared mesh hook.
- **Embedding `datetime.now().isoformat()` into memory content body** — breaks determinism. Use sim-clock timestamps already strewn through `wake_event` or omit.
- **Forgetting to register SSE eventTypes** — v1.1 shipped `scenario.active`/`scenario.ended` with the same gotcha. Both `web/src/lib/sse.ts:69-81` AND `server/events.py` broadcaster must know the event name.
- **Hand-rolling HashChip** — AttestationPanel's HashChip is 66 lines of polished click-to-copy + 4-swatch fingerprint. Extract to `shared/HashChip.tsx`, reuse from both panels.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retries + rate-limit + auth for Anthropic API | Raw `httpx.post` with manual headers | `client.post(path, cast_to=..., body=..., options={...})` | SDK already handles 429 backoff, 500 retries, `x-api-key` injection [VERIFIED: `anthropic==0.96.0`] |
| 4-swatch fingerprint + click-to-copy hash UI | New `MemverChip` component | Extract `HashChip` from `AttestationPanel.tsx:48-113` to `shared/HashChip.tsx` | 66 lines of verified UI; already covered by AttestationPanel.test.tsx |
| SSE reconnect logic | Custom EventSource loop | `getSSE()` at `web/src/lib/sse.ts:132` | Auto-reconnect with exponential backoff already implemented |
| Runtime switch (local vs managed) | `if/else` sprinkled through the codebase | `get_memory_store_manager("auto")` factory | Mirrors `get_session_manager("auto")` at `session.py:391` |
| Ed25519 signing / hash chain | New attestation primitive | `Ledger.append(source="memory", kind="memver.written", payload=...)` at `attest/ledger.py:167` | Already at 97% coverage, gracefully handles sim-clock `ts_provider` |
| Agent skills ingestion | New skills loader | `_load_text()` + `build_cached_messages()` at `session.py:110-152` unchanged | Memory is separate from skills; do NOT refactor skills path |
| Per-agent handler branching for memory | 5 copies of memory write logic | Post-cycle mesh hook in `_handler_base.py` | One codepath = one test matrix; handlers stay memory-unaware |

**Key insight:** The v1.0 codebase already has the templates for all the hard problems (retries, attestation, SSE fan-out, hash-chip UI, runtime gating). Phase 1 is assembly — resist the urge to rebuild primitives; reuse the exact shapes.

## Runtime State Inventory

> This is a rename/refactor phase only in the sense that we're introducing new state. Memory store IDs become runtime state that must survive across processes.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Memory stores themselves ARE the new stored data, managed workspace-side. Locally, `runtime/memory/{store_id}.jsonl` files. | Add `runtime/memory/` + `runtime/memory_store_ids.json` to `.gitignore` (mirror `runtime/agent_ids.json`, `runtime/ma_environment_id.txt` precedent). Local JSONL files reset per fresh clone. |
| Live service config | Memory stores created on Anthropic workspace (not in git). `archive_store()` is the cleanup primitive. | Document in `runtime/README.md` and provide `skyherd-mesh memory cleanup --archive-all` CLI for leftover stores. MUST archive the spike store `memstore_018S1WJAA5mpXW9mTH3YXqzE` — already archived 2026-04-23T20:11:15Z per CONTEXT. |
| OS-registered state | None — no system service hooks. | None |
| Secrets/env vars | `ANTHROPIC_API_KEY` reused (no new secret); `SKYHERD_AGENTS` gate reused. | None — same gate, same key. |
| Build artifacts / installed packages | None new — no new Python deps. | None |

**Nothing found in most categories; Memory adds one local JSONL directory + one cache file.**

## Common Pitfalls

### Pitfall 1: SDK TypedDict validation on `resources=[...]` typed kwarg

**What goes wrong:** `client.beta.sessions.create(resources=[{"type":"memory_store",...}])` raises a Stainless validation error because `Resource = Union[GitHubRepository, File]` only.
**Why it happens:** `anthropic==0.96.0` type stubs predate Memory.
**How to avoid:** Pass memory_store resources via `extra_body={"resources":[...]}` — SDK merges into payload without running TypedDict checks.
**Warning signs:** Pydantic ValidationError mentioning `BetaManagedAgentsFileResourceParams` or `BetaManagedAgentsGitHubRepositoryResourceParams` at session-create time.

### Pitfall 2: Wall-clock timestamps in memory content break determinism

**What goes wrong:** `make demo SEED=42 SCENARIO=all` run 1 vs run 2 md5 mismatch; `test_demo_seed42_is_deterministic_3x` fails.
**Why it happens:** The LocalMemoryStore appends `datetime.now().isoformat()` to JSONL lines; JSONL feeds into scenario output via some path (attestation ledger or SSE replay).
**How to avoid:** Use `session._ts_provider()` from `attest/ledger.py:127-131` for all memory-related timestamps. Or strip by adding to `DETERMINISM_SANITIZE` regex at `tests/test_determinism_e2e.py:19-24`. The memver ID itself is content-derived in the local shim (`_det_id`) so it's already stable.
**Warning signs:** Determinism test passes locally once, fails on CI re-run. Check with `diff <(make demo SEED=42 SCENARIO=all 2>&1 | head -500) <(make demo SEED=42 SCENARIO=all 2>&1 | head -500)`.

### Pitfall 3: Unregistered SSE eventTypes drop silently

**What goes wrong:** Server emits `memory.written` events, MemoryPanel never sees them. No errors — just nothing.
**Why it happens:** `web/src/lib/sse.ts:69-81` registers a fixed list of `eventTypes` used to attach `addEventListener`. Events not in that list are dropped by the browser.
**How to avoid:** Add `"memory.written"` AND `"memory.read"` to the array. This was the v1.1 Part B bug (commit `835adad`: "register scenario.active + scenario.ended in SSE eventTypes").
**Warning signs:** Server logs show SSE broadcast, browser devtools shows SSE frame arriving, MemoryPanel state doesn't update.

### Pitfall 4: Double writes on retry (idempotency)

**What goes wrong:** Network blip causes 5xx → SDK retries → memory written twice at different `memver_` IDs for the same logical content.
**Why it happens:** `POST /v1/memory_stores/{id}/memories` has no native idempotency; each call creates a new `memver_`.
**How to avoid:** Before writing, `list_memories(store_id, path_prefix=path)` and compare `content_sha256`. If equal, skip. For the 72hr scope, the retry-risk is low (pristine network during demo filming) — document as a known limitation, add a TODO comment referencing `If-Match` header support landing in a future Memory API release.
**Warning signs:** Dashboard MemoryPanel shows duplicate entries with different `memver_` but same content.

### Pitfall 5: Memory writes inside handler GC'd by asyncio

**What goes wrong:** `create_task(post_cycle_write(...))` fires then vanishes — no memory record, no SSE event. Silent failure.
**Why it happens:** v1.0 H-05 bug: Python GC reclaims tasks with no strong reference. Fix was `_inflight_handlers` set + `add_done_callback(discard)` in `AgentMesh`.
**How to avoid:** `post_cycle_write` is `await`ed inline inside `run_handler_cycle` in this design — no `create_task`. If we later defer to a background task, reuse the `_inflight_handlers` pattern at `mesh.py:120, 236-237`.
**Warning signs:** Random missing memver records; logs show handler completed but no `memory.written` event emitted.

### Pitfall 6: Local shim response shape drift from real REST

**What goes wrong:** Works in sim tests, breaks in managed runtime because `LocalMemoryStore.list_memories()` returned `list[Memory]` instead of `{"data":[...],"prefixes":[...]}`.
**Why it happens:** The REST envelope `{data: [...], prefixes: [...]}` isn't obvious from a single response example.
**How to avoid:** Pydantic `ListEnvelope` model MUST be the return type of both `LocalMemoryStore.list_memories` AND `MemoryStoreManager.list_memories`. Tests must hit both implementations with the same assertion set (parametrize).
**Warning signs:** `KeyError: 'data'` in `/api/memory/{agent}` when flipping `SKYHERD_AGENTS`.

### Pitfall 7: `archive_store` during demo filming

**What goes wrong:** Running integration tests during filming archives the live demo store; next `make demo` run has 0 memories; panel empty.
**Why it happens:** Tests/CI call `archive_store()` in teardown.
**How to avoid:** Integration tests create throwaway stores with a unique `name` per test run (`memstore_test_{uuid}`). Demo-visible stores are named `skyherd_<agent>_ranch_a` and NEVER archived except by explicit `skyherd-mesh memory cleanup`.
**Warning signs:** Panel was working, suddenly 0 entries after CI run.

## Code Examples

### Creating the 6 stores idempotently on mesh startup

```python
# In AgentMesh.start() — new helper _ensure_memory_stores()

async def _ensure_memory_stores(self) -> dict[str, str]:
    """Create 1 shared + 5 per-agent stores; cache IDs in runtime/memory_store_ids.json.

    Idempotent: re-running reuses cached IDs unless archived.
    Mirror of ManagedSessionManager.ensure_agent() pattern (managed.py:202).
    """
    cache = Path("runtime/memory_store_ids.json")
    if cache.exists():
        return json.loads(cache.read_text())

    mgr = get_memory_store_manager()
    ids: dict[str, str] = {}
    shared = await mgr.create_store(
        name="skyherd_ranch_a_shared",
        description="SkyHerd shared ranch patterns — read-only domain library",
    )
    ids["_shared"] = shared.id

    for spec, _handler in _AGENT_REGISTRY:
        store = await mgr.create_store(
            name=f"skyherd_{spec.name.lower()}_ranch_a",
            description=f"Per-agent memory for {spec.name}",
        )
        ids[spec.name] = store.id

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(ids, indent=2))
    return ids
```

### Disabling web tools on CalvingWatch + GrazingOptimizer

```python
# In managed.py:216 — MODIFY ensure_agent() to read disable list from agent_spec:

# Option: add `disable_tools: list[str] = field(default_factory=list)` to AgentSpec
# Then:

tools_config = [{"type": "agent_toolset_20260401", "default_config": {"enabled": True}}]
if agent_spec.disable_tools:
    tools_config[0]["configs"] = [
        {"name": tool, "enabled": False} for tool in agent_spec.disable_tools
    ]

agent = await self._client.beta.agents.create(
    name=agent_spec.name,
    model=agent_spec.model,
    system=system_prompt or f"You are {agent_spec.name} for SkyHerd.",
    tools=tools_config,
)

# CalvingWatch spec + GrazingOptimizer spec gain:
#   disable_tools=["web_search", "web_fetch"]
```

### MemoryPanel.tsx skeleton (mirror AttestationPanel exactly)

```tsx
// web/src/components/MemoryPanel.tsx  (~360 lines target, mirroring AttestationPanel 395 lines)

import { useState, useEffect, useCallback, Fragment } from "react";
import { cn } from "@/lib/cn";
import { getSSE } from "@/lib/sse";
import { HashChip } from "@/components/shared/HashChip";

interface MemoryVersion {
  id: string;                 // memver_...
  operation: "created" | "updated" | "deleted" | "redacted";
  path: string;
  content_sha256?: string | null;
  created_by: { type: string; api_key_id: string };
}

const AGENTS = [
  "FenceLineDispatcher", "HerdHealthWatcher",
  "PredatorPatternLearner", "GrazingOptimizer", "CalvingWatch",
];

export function MemoryPanel({ collapsed = false, onToggle }: { collapsed?: boolean; onToggle?: () => void }) {
  const [activeAgent, setActiveAgent] = useState<string>(AGENTS[0]);
  const [versions, setVersions] = useState<Record<string, MemoryVersion[]>>({});

  const handleWrite = useCallback((payload: { agent: string; memory_version_id: string; path: string; content_sha256: string }) => {
    setVersions(prev => ({
      ...prev,
      [payload.agent]: [
        {
          id: payload.memory_version_id,
          operation: "created",
          path: payload.path,
          content_sha256: payload.content_sha256,
          created_by: { type: "api_actor", api_key_id: "live" },
        },
        ...(prev[payload.agent] ?? []),
      ].slice(0, 50),
    }));
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("memory.written", handleWrite);
    // Fetch initial for active agent
    fetch(`/api/memory/${activeAgent}`).then(r => r.json()).then(data => {
      setVersions(prev => ({ ...prev, [activeAgent]: data.versions ?? [] }));
    }).catch(() => {});
    return () => sse.off("memory.written", handleWrite);
  }, [activeAgent, handleWrite]);

  return (
    <section aria-label="Memory panel" /* ... same section styling as AttestationPanel ... */>
      {/* Header: tabs for 5 agents + collapse chevron */}
      <div className="flex gap-2 px-3 py-2 border-b">
        {AGENTS.map(name => (
          <button
            key={name}
            onClick={() => setActiveAgent(name)}
            className={cn("chip", activeAgent === name ? "chip-sage" : "chip-muted")}
          >
            {name}
          </button>
        ))}
      </div>
      {/* Body: table of memver rows, HashChip in the hash column (click-to-copy) */}
      {!collapsed && (
        <table className="w-full text-mono-xs">
          {/* ... same table shape as AttestationPanel ... */}
          <tbody>
            {(versions[activeAgent] ?? []).map(v => (
              <tr key={v.id} className="write-flash"> {/* CSS class triggers the flash */}
                <td><span className="chip chip-sky">{v.operation}</span></td>
                <td className="truncate max-w-[12rem]">{v.path}</td>
                <td><HashChip hash={v.id} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `LocalSessionManager` shim for MA primitives | Real `client.beta.*` calls via `ManagedSessionManager` | v1.0 Phase 1 (2026-04-22) | Phase 1 Memory is the natural next step — sessions already exist |
| Hand-rolled prompt text without caching | `build_cached_messages()` with `cache_control: ephemeral` blocks | v1.0 C1 fix (2026-04-22) | Memory MUST NOT touch this shape — memver writes happen after `messages.create` returns |
| SDK-exposed memory primitives (anticipated) | REST-only via `client.post`/`client.get` | Memory beta shipped 2026-04-23; SDK 0.96.0 predates | Ship raw HTTP now; swap to `client.beta.memory_stores.*` when SDK ships (1-5 line change in `MemoryStoreManager`) |

**Deprecated/outdated:**

- **`client.messages.create` without `cache_control`** — v1.0 C1 fix closes this; Phase 1 inherits.
- **Session-per-event architecture** — v1.0 Phase 1 (MA-03) eliminated. Persistent sessions now.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (`pyproject.toml:asyncio_mode = "auto"`, `fail_under = 80`) + vitest (web) |
| Config file | `pyproject.toml` (Python); `web/vitest.config.ts` (TS) |
| Quick run command | `uv run pytest tests/agents/test_memory.py -x` (~5s) |
| Full suite command | `uv run pytest --cov=src/skyherd --cov-report=term-missing` + `(cd web && pnpm run test)` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MEM-01 | 6 stores created idempotently; IDs cached | unit | `uv run pytest tests/agents/test_memory.py::test_ensure_stores_idempotent -x` | Wave 0 |
| MEM-02 | `sessions.create` called with `extra_body={"resources":[...]}` | unit | `uv run pytest tests/agents/test_managed.py::test_session_create_attaches_memory_resources -x` | Wave 0 (extend existing file) |
| MEM-03 | `MemoryStoreManager` parses all 6 REST endpoints; Pydantic models validate | unit | `uv run pytest tests/agents/test_memory.py::test_rest_response_parsing -x` | Wave 0 |
| MEM-04 | `LocalMemoryStore` round-trip matches Pydantic envelope | unit | `uv run pytest tests/agents/test_memory.py::test_local_shim_parity -x` | Wave 0 |
| MEM-05 | Post-cycle hook writes per-agent with correct path | integration | `uv run pytest tests/agents/test_memory_hook.py -x` | Wave 0 |
| MEM-06 | `/api/memory/{agent}` returns envelope, 404 on unknown agent | integration | `uv run pytest tests/server/test_memory_api.py -x` | Wave 0 |
| MEM-07 | `MemoryPanel.tsx` renders, tab switches, memver flash on SSE | unit (vitest) | `(cd web && pnpm run test MemoryPanel)` | Wave 0 |
| MEM-08 | SSE `memory.written` eventType registered; broadcaster emits | integration | `uv run pytest tests/server/test_memory_api.py::test_sse_memory_written_broadcast -x` | Wave 0 |
| MEM-09 | `make demo SEED=42 SCENARIO=all` 3-run md5 match holds | e2e | `uv run pytest tests/test_determinism_e2e.py::test_demo_seed42_is_deterministic_3x -x` | EXISTS (extend sanitizer for `memver_`) |
| MEM-10 | Every memver write logs to Ed25519 ledger | integration | `uv run pytest tests/agents/test_memory_hook.py::test_memver_pairs_with_ledger_entry -x` | Wave 0 |
| MEM-11 | CalvingWatch + GrazingOptimizer agents.create includes `configs` disabling web tools | unit | `uv run pytest tests/agents/test_managed.py::test_toolset_disable -x` | Wave 0 (extend) |
| MEM-12 | `make mesh-smoke` covers both runtimes | smoke | `SKYHERD_AGENTS=local make mesh-smoke && echo local-ok` (skip managed locally without key) | EXISTS |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/agents/test_memory.py tests/agents/test_memory_hook.py tests/server/test_memory_api.py -x` (~15s)
- **Per wave merge:** `uv run pytest --cov=src/skyherd -x` + `(cd web && pnpm run test)` (~60s)
- **Phase gate:** Full suite green + `test_demo_seed42_is_deterministic_3x` PASS before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/agents/test_memory.py` — MemoryStoreManager REST parsing + LocalMemoryStore parity; uses `httpx.MockTransport` to stub Anthropic API
- [ ] `tests/agents/test_memory_hook.py` — post-cycle hook fires per cycle; pairs with ledger; emits SSE
- [ ] `tests/agents/test_memory_determinism.py` — assert no HTTP calls under `SEED=42` (monkeypatch `AsyncAnthropic.post` to raise)
- [ ] `tests/server/test_memory_api.py` — endpoint returns envelope, 404, SSE broadcast smoke
- [ ] `web/src/components/MemoryPanel.test.tsx` — vitest component test (tab switch, SSE handler wires, HashChip renders)
- [ ] `tests/agents/test_managed.py` — EXTEND with `test_session_create_attaches_memory_resources`, `test_toolset_disable`
- [ ] `tests/test_determinism_e2e.py` — EXTEND `DETERMINISM_SANITIZE` regex to strip `memver_[a-zA-Z0-9]+`, `mem_[a-zA-Z0-9]+`, `memstore_[a-zA-Z0-9]+`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `x-api-key` header — SDK-managed; no new auth surface |
| V3 Session Management | no | Managed Agents platform handles session auth |
| V4 Access Control | partial | Memory store `mode: "read_only"` vs `"read_write"` enforced server-side by Anthropic; verify in tests that shared store attached read_only cannot be written |
| V5 Input Validation | yes | Pydantic v2 on all REST responses; `/api/memory/{agent}` agent param must match regex `^[A-Za-z]+$` (prevent path traversal via agent name) |
| V6 Cryptography | yes (attestation) | Ed25519 via existing `Ledger` — never hand-roll. `content_sha256` attestation anchor from REST response (verified BLAKE2b-256 server-side by Anthropic) |
| V7 Error Handling | yes | `ManagedAgentsUnavailable` sentinel; 500s on REST retried by SDK; logged once at WARNING |
| V8 Data Protection | yes | **Redaction rules in `memory_paths.py`** — strip `rancher_phone`, `vet_phone`, `auth_token`, Twilio SIDs before writing. Memory content is stored cloud-side by Anthropic; assume exfiltrable |

### Known Threat Patterns for {Python async REST client + FastAPI + React}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leakage via error message | Information Disclosure | Catch `anthropic.APIError`; log `type(exc).__name__` not `str(exc)` (which includes URL + payload snippets) |
| Path traversal via `/api/memory/{agent}` | Elevation | Regex validate `agent` param — `^[A-Za-z]+$` — reject anything else with 400 |
| Memory content injection (agent writes untrusted user input) | Tampering | Redact/escape before `write_memory`; `memory_paths.py::_redact` for known PII keys |
| SSE connection exhaustion from memory events | DoS | Reuse existing `SSE_MAX_CONNECTIONS=100` cap at `server/app.py:57` |
| Double-write on retry duplicates memver | Tampering (weakly) | `content_sha256` pre-check (list existing; skip if match); accept small residual risk |
| Archived store ID resurrection | Integrity | Always re-list stores on mesh startup; if cached ID is archived, recreate |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `extra_body={"resources":[{"type":"memory_store",...}]}` is the correct shape for the memory_store Resource type at `POST /v1/sessions` | Pattern 2 | HIGH — session creation fails. **Mitigation:** First integration test hits live API with both a bare POST (raw HTTP, known-shape from spike) and the SDK `extra_body` path; if SDK path differs, fall back to full raw POST for sessions.create. Spike confirmed the REST payload shape for memory_stores; spike did NOT confirm the resource attachment payload — this is an inference. [ASSUMED] |
| A2 | Memory `write_memory` is NOT idempotent on `content_sha256` (each POST creates a new memver) | Pitfall 4 | MEDIUM — if the API DOES dedupe, retry-safe writes come free; if it doesn't and we retry, we get duplicate memvers. **Mitigation:** Document as known limitation; 72hr demo-path network reliability makes this low-prob. [ASSUMED] |
| A3 | Archived memory stores are excluded from `GET /v1/memory_stores` by default (per spike) but remain addressable by ID for archive undo. Undo path unknown. | Runtime State Inventory | LOW — we don't need undo for demo. [ASSUMED] |
| A4 | `anthropic-beta: managed-agents-2026-04-01` header covers Memory endpoints (no separate Memory beta flag) | Code Examples | MEDIUM — if a Memory-specific beta flag is required, every call 400s with "beta not enabled". **Mitigation:** Spike at 20:10 UTC 2026-04-23 confirmed `managed-agents-2026-04-01` worked for the memstore endpoints end-to-end. [VERIFIED: CONTEXT spike_findings] |
| A5 | SDK `client.post(path, cast_to=dict, body=...)` with `options={"headers": {...}}` applies custom headers per-request. | Pattern 1 | LOW — API inspection showed `options: RequestOptions = {}` param; headers in RequestOptions are merged by SDK. [VERIFIED: source inspection 2026-04-23] |
| A6 | Memory `mode: "read_only"` vs `"read_write"` is enforced server-side at attach time | Security Domain | LOW — if not enforced, shared store could be written by agents. **Mitigation:** Integration test attempts write to read-only shared store; expect 403 or server-side rejection. [ASSUMED] |
| A7 | `resources` array on `sessions.create` supports mixing memory_store + future types (future-compat) | Pattern 2 | LOW — only matters post-hackathon. [ASSUMED] |
| A8 | REST response field `created_by.api_key_id` remains stable per API key (not rotated per session) — suitable as attribution anchor | CONTEXT `<spike_findings>` | LOW — even if it rotates, the memver chain is still coherent per-store. [ASSUMED] |

**User confirmation recommended for A1 only** — the other assumptions are either verified, low-impact, or have built-in fallbacks. A1 is the only one that could block session creation for all 5 agents; validate it with a first-ten-minutes smoke test of Phase 1 execution before full buildout.

## Open Questions

1. **Does `POST /v1/sessions` accept memory_store resources via `extra_body`?**
   - What we know: `resources=` kwarg exists; SDK 0.96 `Resource` union lacks memory_store; `extra_body` merges into payload.
   - What's unclear: Whether the API server rejects unknown resource types or ignores them.
   - Recommendation: First task in Phase 1 execution — a 5-minute spike that creates one test session with a throwaway memory_store attached via `extra_body`. If it rejects, fall back to raw `client.post("/v1/sessions", ...)` for sessions.create. This is the A1 risk realisation gate.

2. **Content redaction strictness — how aggressive?**
   - What we know: Memory content is cloud-hosted by Anthropic workspace.
   - What's unclear: Whether rancher-facing vet intake content (cow tags, GPS) counts as PII for Anthropic's data-retention policy.
   - Recommendation: Conservative — strip phone numbers, Twilio SIDs, auth tokens; keep cow tags + GPS (required for the demo narrative). Document in `memory_paths.py` header.

3. **Should the local shim ALSO set `created_by.api_key_id`?**
   - What we know: Real API responses include `api_key_id: "apikey_..."`.
   - What's unclear: Whether tests depend on this field presence.
   - Recommendation: Yes — synthesize `apikey_local_shim` to preserve shape parity. One less branch in tests.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | all | ✓ | 3.11+ via `uv` | — |
| `anthropic==0.96.0` | MemoryStoreManager | ✓ | 0.96.0 [VERIFIED 2026-04-23] | — |
| `ANTHROPIC_API_KEY` | managed runtime | depends | env var | Local shim works without it |
| FastAPI + sse-starlette | /api/memory | ✓ | already in deps | — |
| React 19 + Vite | MemoryPanel | ✓ | `web/pnpm install` already in quickstart | — |
| pytest + httpx | tests | ✓ | in dev deps | — |
| `claude-agent-sdk` | MCP (not used for memory) | ✓ | in deps | N/A — memory does not need MCP |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** `ANTHROPIC_API_KEY` absent → `LocalMemoryStore` shim (expected, deterministic).

## Sources

### Primary (HIGH confidence)

- **CONTEXT.md `<spike_findings>`** (2026-04-23 20:10 UTC live test against api.anthropic.com) — REST endpoints, payload shapes, ID formats, attribution chain [VERIFIED]
- **`anthropic==0.96.0` source inspection** (2026-04-23) — `client.post`/`client.get` signatures, `sessions.create` resources kwarg, `Resource` union contents, `extra_body` support [VERIFIED]
- **Codebase ground truth:** `src/skyherd/agents/managed.py`, `session.py`, `_handler_base.py`, `mesh.py`, `attest/ledger.py`, `server/app.py`, `web/src/components/AttestationPanel.tsx`, `web/src/lib/sse.ts` [VERIFIED: direct Read]
- **`.planning/codebase/ARCHITECTURE.md` + `CONCERNS.md`** (audit 2026-04-22) — 5-layer nervous-system ground truth [VERIFIED]
- **`pyproject.toml`** — `anthropic>=0.69,<1`, `fail_under = 80`, `asyncio_mode = "auto"` [VERIFIED]

### Secondary (MEDIUM confidence)

- Anthropic Managed Agents docs: https://platform.claude.com/docs/en/managed-agents/memory [CITED: ROADMAP.md "Evidence base"]
- Release notes (2026-04-23 Memory entry): https://platform.claude.com/docs/en/release-notes/api [CITED: ROADMAP.md]

### Tertiary (LOW confidence)

- None — all critical claims anchored in primary sources.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all deps already in use, versions verified via `uv run python -c`
- Architecture: HIGH — existing codebase templates (ManagedSessionManager, Ledger, AttestationPanel/HashChip, SSE broadcaster) provide known-good shapes
- Pitfalls: HIGH (1-3) — direct codebase evidence from v1.0 bugs; MEDIUM (4, 6) — inferred from REST shape; HIGH (5, 7) — direct v1.0 precedent
- REST surface: HIGH — spike-verified end-to-end against live API
- `extra_body` attachment: MEDIUM — SDK support verified, API acceptance inferred (A1 in Assumptions Log)

**Research date:** 2026-04-23
**Valid until:** 2026-04-26 (hackathon submission). Post-hackathon, re-verify when `anthropic` SDK ships `client.beta.memory_stores.*` native support.
