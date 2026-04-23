# Phase 1: Memory-Powered Agent Mesh - Pattern Map

**Mapped:** 2026-04-23
**Files analyzed:** 11 new/modified files (7 new Python, 3 new TS, 1 MODIFY site)
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/skyherd/agents/memory.py` | API client + factory | request-response (REST wrap) | `src/skyherd/agents/managed.py` (`ManagedSessionManager`) | exact (runtime-gated manager pattern) |
| `src/skyherd/agents/memory_paths.py` | utility (pure functions) | transform | `src/skyherd/agents/spec.py` (small dataclass/enum module) + `web/src/lib/sse.ts` eventTypes list | role-match (small pure module) |
| `src/skyherd/agents/memory_local.py` *(note: RESEARCH folds this into `memory.py` as `LocalMemoryStore` alongside `MemoryStoreManager`; keep as single file per RESEARCH §Pattern 1)* | file-backed shim | file-I/O | `src/skyherd/agents/session.py` (`LocalSessionManager = SessionManager`, JSON checkpoint under `runtime/sessions/`) | exact |
| `src/skyherd/agents/memory_hook.py` | service (post-cycle hook) | event-driven | `src/skyherd/attest/ledger.py::Ledger.append` (receipt emitter) | role-match |
| `src/skyherd/server/memory_api.py` | FastAPI endpoint module | request-response | `src/skyherd/server/app.py` `/api/attest` (lines 159-165) + `/api/attest/verify` (167-180) | exact |
| `src/skyherd/server/events.py` (MODIFY) | SSE broadcaster (add `memory.written` / `memory.read`) | pub-sub | same file: `attest.append` broadcast at lines 403-435 | self-analog |
| `src/skyherd/agents/_handler_base.py` (MODIFY) | event-driven hook insertion | event-driven | same file: current `return` sites at lines 88-101 | self-analog |
| `src/skyherd/agents/managed.py` (MODIFY) | session attachment of memory resources | request-response | same file: `create_session_async` at line 235-262 | self-analog |
| `web/src/components/MemoryPanel.tsx` | React component | streaming (SSE) + fetch | `web/src/components/AttestationPanel.tsx` (HashChip lines 48-113, SSE wire-up 171-194) | exact |
| `web/src/lib/sse.ts` (MODIFY) | SSE client registry | pub-sub | same file, `eventTypes` array lines 69-81 | self-analog |
| `tests/agents/test_memory.py` | unit tests (httpx mocked) | test | `tests/agents/test_managed.py` (AsyncMock pattern + ManagedAgentsUnavailable guard, lines 60-95) | exact |
| `tests/agents/test_memory_hook.py` | unit tests (hook behaviour) | test | `tests/agents/test_managed.py::TestRunHandlerCycleNoKey` (lines 136-149) | exact |
| `tests/agents/test_memory_determinism.py` | determinism guard | test | `tests/test_determinism_e2e.py` (referenced in RESEARCH); unit-level analog: `tests/agents/test_fenceline.py` simulation-path assertion | role-match |
| `tests/server/test_memory_api.py` | API tests (httpx AsyncClient) | test | `tests/server/test_app.py` (mock_app + httpx ASGITransport fixture, lines 18-31) | exact |
| `web/src/components/MemoryPanel.test.tsx` | vitest component test | test | `web/src/components/AttestationPanel.test.tsx` (mock fetch + sseHandlers map, lines 6-27) | exact |

---

## Hook Insertion Site (MUST reference when writing `memory_hook.py`)

**File:** `src/skyherd/agents/_handler_base.py`

**Current code** (lines 80-101, the two return sites of `run_handler_cycle`):

```python
    if sdk_client is None or not os.environ.get("ANTHROPIC_API_KEY"):
        return []  # signal: caller should use _simulate_handler()

    # Check for managed runtime: session has platform_session_id attribute
    platform_session_id: str | None = getattr(session, "platform_session_id", None)

    if platform_session_id and os.environ.get("SKYHERD_AGENTS") == "managed":
        return await _run_managed(
            session=session,
            sdk_client=sdk_client,
            cached_payload=cached_payload,
            platform_session_id=platform_session_id,
            tool_dispatcher=tool_dispatcher,
        )

    # Local runtime — C1 fix: pass system + messages with cache_control
    return await _run_local_with_cache(
        session=session,
        sdk_client=sdk_client,
        cached_payload=cached_payload,
    )
```

**Required refactor** — capture `tool_calls` into a local, fire the hook, then return. The CONTEXT reference to line 126 refers to the *point where tool dispatches happen inside `_run_managed`* — but the cleanest single-codepath hook site is at the top-level `run_handler_cycle` return. Pattern to adopt:

```python
    # ... both branches become:
    if platform_session_id and os.environ.get("SKYHERD_AGENTS") == "managed":
        tool_calls = await _run_managed(...)
    else:
        tool_calls = await _run_local_with_cache(...)

    # NEW — memory post-cycle hook (non-blocking; never raises into caller).
    # wake_event is NOT currently a parameter of run_handler_cycle; must be
    # plumbed through (see per-agent handlers that already pass the raw event).
    try:
        from skyherd.agents.memory_hook import post_cycle_write  # noqa: PLC0415
        store_id_map = getattr(session, "_memory_store_id_map", None)
        ledger = getattr(session, "_ledger_ref", None)
        broadcaster = getattr(session, "_broadcaster_ref", None)
        await post_cycle_write(
            session, wake_event, tool_calls, ledger, broadcaster, store_id_map,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("memory post-cycle write failed for %s: %s",
                       getattr(session, "agent_name", "?"), exc)

    return tool_calls
```

**Plumbing note for planner:** `run_handler_cycle` currently does NOT take `wake_event` — it extracts `user_text` from `cached_payload["messages"][0]`. The planner must add `wake_event: dict[str, Any]` as a new parameter and thread it from every caller (one per agent handler in `src/skyherd/agents/{fenceline_dispatcher,herd_health_watcher,predator_pattern_learner,grazing_optimizer,calving_watch}.py` — all already have `wake_event` in scope). Alternatively, attach `wake_event` onto `session.wake_events_consumed[-1]` and read from there (zero-signature-change path, preferred).

---

## Pattern Assignments

### `src/skyherd/agents/memory.py` (API client + factory, request-response)

**Analog:** `src/skyherd/agents/managed.py` — `ManagedSessionManager` + `get_session_manager` factory.

**Imports pattern** (mirror `managed.py:31-41`):

```python
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
```

**Sentinel exception pattern** (copy from `managed.py:48-49`):

```python
class ManagedAgentsUnavailable(RuntimeError):
    """Raised when MA runtime is requested but prerequisites are not met."""
```

New file should REUSE `ManagedAgentsUnavailable` by importing it from `managed.py` (do NOT define a sibling; RESEARCH §Pattern 1 already calls `from skyherd.agents.managed import ManagedAgentsUnavailable`).

**Runtime-gated `__init__`** (copy-pattern from `managed.py:132-166`):

```python
def __init__(
    self,
    api_key: str | None = None,
    client: Any | None = None,      # async anthropic client, injectable for tests
    store_ids_path: str = "runtime/memory_store_ids.json",
) -> None:
    import anthropic
    _key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not _key:
        raise ManagedAgentsUnavailable(
            "ANTHROPIC_API_KEY not set — cannot initialise MemoryStoreManager. "
            "Set ANTHROPIC_API_KEY or use runtime='local'."
        )
    self._client = client or anthropic.AsyncAnthropic(api_key=_key)
    self._store_ids_path = Path(store_ids_path)
    self._store_ids: dict[str, str] = {}
    if self._store_ids_path.exists():
        try:
            self._store_ids = json.loads(self._store_ids_path.read_text())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load memory_store_ids.json: %s", exc)
```

**Idempotent create pattern** (copy `ensure_agent` from `managed.py:202-229` — JSON cache of IDs):

```python
async def ensure_store(self, name: str, description: str | None = None) -> str:
    import json
    if name in self._store_ids:
        return self._store_ids[name]
    logger.info("Creating memory store %s…", name)
    store = await self.create_store(name=name, description=description)
    self._store_ids[name] = store.id
    self._store_ids_path.parent.mkdir(parents=True, exist_ok=True)
    self._store_ids_path.write_text(json.dumps(self._store_ids, indent=2))
    logger.info("memory store created: %s → %s", name, store.id)
    return store.id
```

**REST call pattern** (verbatim from RESEARCH §Pattern 1 — `client.post`/`client.get` with `cast_to=dict` and explicit beta header). New code MUST replicate the `options={"headers": {"anthropic-beta": "managed-agents-2026-04-01"}}` shape on every call — the SDK does NOT auto-inject the beta header on `client.post`/`client.get` (it auto-injects only on `client.beta.*` methods).

**Factory pattern** (mirror `session.py::get_session_manager` at lines 391-447):

```python
def get_memory_store_manager(runtime: str = "auto") -> "MemoryStoreBase":
    """runtime: 'local' | 'managed' | 'auto' (= managed iff SKYHERD_AGENTS=managed + key)"""
    if runtime == "local":
        return LocalMemoryStore()
    if runtime == "managed":
        return MemoryStoreManager()
    # auto
    if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("SKYHERD_AGENTS") == "managed":
        try:
            return MemoryStoreManager()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "MemoryStoreManager unavailable (%s) — falling back to LocalMemoryStore",
                exc,
            )
    return LocalMemoryStore()
```

**Fields/signatures the new file MUST replicate exactly:**
- Module-level `logger = logging.getLogger(__name__)`.
- `ManagedAgentsUnavailable` raised with identical message shape.
- `runtime/memory_store_ids.json` path (mirrors `runtime/agent_ids.json`).
- `get_memory_store_manager(runtime: str = "auto")` return type is the *base* class (just as `get_session_manager` returns `SessionManager` cast from `ManagedSessionManager`).
- Never accept an un-validated `Any` response — every REST payload must be parsed into a Pydantic model (see RESEARCH §Pattern 1 Pydantic definitions at lines 245-274).

---

### `src/skyherd/agents/memory_paths.py` (utility, transform)

**Analog:** `src/skyherd/agents/spec.py` (small pure module — 55 lines, no imports beyond `dataclass`).

**Imports pattern** (mirror `spec.py:16-20` — minimal stdlib only):

```python
from __future__ import annotations
from datetime import UTC, datetime
from typing import Any
```

**Pure-function pattern** (copy shape from RESEARCH §Pattern 3 `decide_write_path`, lines 552-576 of RESEARCH). The planner should treat every function in this file as a pure transform — NO filesystem, network, or I/O side effects (mirrors the `_mqtt_topic_matches` helper style in `session.py:357-380`).

**Redaction constant** (mirror naming in `events.py:33-39` AGENT_NAMES style — uppercase module-level frozenset):

```python
_REDACT_KEYS = frozenset({"rancher_phone", "vet_phone", "auth_token", "api_key"})
```

**Fields/signatures the new file MUST replicate:**
- Return type `tuple[str, str]` = `(memory_path, markdown_content)` — one call site per agent.
- `agent_name` must match literal values in `_AGENT_REGISTRY` at `mesh.py:56-62` (`FenceLineDispatcher`, `HerdHealthWatcher`, `PredatorPatternLearner`, `GrazingOptimizer`, `CalvingWatch`).
- Paths use the three prefixes locked in CONTEXT `<decisions>`: `patterns/<topic>.md`, `notes/<entity_id>.md`, `baselines/<metric>.md`.
- No `datetime.now()` anywhere — use `datetime.fromtimestamp(0, UTC).isoformat()` or pull `ts` from the wake event. This is a determinism requirement (MEM-09).

---

### `src/skyherd/agents/memory_hook.py` (service, event-driven)

**Analog:** Event-emission pattern in `Ledger.append` (`src/skyherd/attest/ledger.py:167`) + non-blocking fire-and-forget pattern in `AgentMesh._run_handler` (`mesh.py:241-253`).

**Ledger pairing excerpt** (from `ledger.py:167`):

```python
def append(self, source: str, kind: str, payload: dict) -> Event:
    """Append one event atomically; returns the committed Event."""
```

`memory_hook.py::post_cycle_write` MUST call `ledger.append(source="memory", kind="memver.written", payload={...})` — the `source="memory"` string is a NEW value to the ledger (existing values: `FenceLineDispatcher`, `HerdHealthWatcher`, etc., and topic strings like `skyherd/ranch_a/fence/seg_1`). Planner should note this in Ledger verify tests (`source="memory"` is expected, not a schema violation).

**Non-blocking wrap pattern** (copy from `mesh.py:148-172` stop() or the C1 fallback `_handler_base.py:247-250`):

```python
try:
    ...  # memory write + ledger.append + broadcaster.emit
except Exception as exc:  # noqa: BLE001
    logger.warning("memory post-cycle write failed for %s: %s", agent_name, exc)
```

**Broadcaster emit pattern** — `EventBroadcaster._broadcast` at `events.py:307-317` is synchronous (`put_nowait`); the planner should add an `async def emit(event_type, payload)` async wrapper OR call `self._broadcast` directly. Mirror the `attest.append` fan-out wiring at `events.py:411-415`:

```python
for event in self._ledger.iter_events(since_seq=last_seq):
    payload = event.model_dump()
    self._broadcast("attest.append", payload)
```

---

### `src/skyherd/agents/managed.py` (MODIFY — `create_session_async` at lines 235-262)

**Current code** (to modify at line 240):

```python
platform_session = await self._client.beta.sessions.create(
    agent=agent_id,
    environment_id=env_id,
    title=f"skyherd-{agent_spec.name}",
)
```

**Required modification** (verbatim from RESEARCH §Pattern 2 lines 433-465):

```python
# Resolve memory store IDs (self._memory_store_ids populated at startup).
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
platform_session = await self._client.beta.sessions.create(
    agent=agent_id,
    environment_id=env_id,
    title=f"skyherd-{agent_spec.name}",
    extra_body={"resources": resources} if resources else None,
)
```

**Also modify `__init__`** (line 132-166) to accept and store `memory_store_ids: dict[str, str] | None = None` → `self._memory_store_ids: dict[str, str] = memory_store_ids or {}`.

**Also modify `ensure_agent`** (line 216-223) for CalvingWatch + GrazingOptimizer toolset disable:

```python
# Existing:
tools=[
    {"type": "agent_toolset_20260401", "default_config": {"enabled": True}},
],
# Replace with (MEM-11 — determinism guard):
tools=[_build_tools_config(agent_spec.name)],
```

Where `_build_tools_config` returns the selective-disable dict for `CalvingWatch` + `GrazingOptimizer` per CONTEXT `<decisions>` line 48.

---

### `src/skyherd/server/memory_api.py` (FastAPI endpoint module, request-response)

**Analog:** `src/skyherd/server/app.py::api_attest` + `api_attest_verify` (lines 159-180).

**Endpoint pattern** (verbatim shape to replicate):

```python
@app.get("/api/attest")
async def api_attest(since_seq: int = Query(default=0, ge=0)) -> JSONResponse:
    if use_mock or ledger is None:
        entries = [_mock_attest_entry() for _ in range(min(10, 50))]
    else:
        entries = [e.model_dump() for e in ledger.iter_events(since_seq=since_seq)][:50]
    return JSONResponse(content={"entries": entries, "ts": time.time()})
```

**APIRouter pattern** — `app.py` currently defines endpoints inline inside `create_app()`, but `src/skyherd/agents/webhook.py::webhook_router` shows the cleaner `APIRouter` pattern (lines 43 + 68). `memory_api.py` SHOULD use `APIRouter(prefix="/api/memory", tags=["memory"])` and be mounted via `app.include_router(memory_api.router)` in `app.py::create_app` (mirror `app.include_router(webhook_router)` at `app.py:123`).

**Endpoint signatures the new file MUST expose:**
- `GET /api/memory/{agent}` → list memories for that agent's store (path_prefix optional query param).
- `GET /api/memory/{agent}/versions` → list memver audit trail.
- Response envelope: `{"entries": [...], "ts": time.time()}` (identical shape to `/api/attest`).

**Mock-mode pattern** — `app.py` uses `use_mock or ledger is None`. `memory_api.py` must accept a `memory_store_manager` dep injected the same way (`ledger=` → `memory_store_manager=`) and fall back to `_mock_memory_entry()` helpers in events.py.

**Error handling pattern** (copy from `app.py::api_vet_intake` lines 182-202):

```python
try:
    path = get_intake_path(intake_id)
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
if not path.exists():
    raise HTTPException(status_code=404, detail=f"intake {intake_id!r} not found")
```

Apply the same idiom: invalid `agent` path parameter → 400, unknown agent → 404.

**Agent whitelist guard** — path parameter `{agent}` MUST be validated against `events.AGENT_NAMES` (lines 33-39) to prevent SSRF-ish path traversal into arbitrary store IDs. Pattern:

```python
from skyherd.server.events import AGENT_NAMES
if agent not in AGENT_NAMES:
    raise HTTPException(status_code=404, detail=f"unknown agent {agent!r}")
```

---

### `src/skyherd/server/events.py` (MODIFY — add `memory.written` / `memory.read` broadcast)

**Analog:** same file, `_attest_loop` at lines 403-435 + `_broadcast` at 307-317.

**Current attest fan-out** (events.py:411-415):

```python
for event in self._ledger.iter_events(since_seq=last_seq):
    payload = event.model_dump()
    self._broadcast("attest.append", payload)
```

**Required addition** — add `_memory_queue: asyncio.Queue` drained by a new producer loop OR expose an `async def emit_memory_written(payload)` method called by the mesh post-cycle hook (RESEARCH §Pattern 3 at line 525 already shows `broadcaster.emit(...)` — the planner must add this async method).

**Fields the new code MUST replicate:**
- Stop-event check in any new loop (`while not self._stop_event.is_set()`).
- Payload `default=str` serialisation (via `_json` helper at line 42).
- Bounded queue back-pressure handling (lines 308-317 — drop oldest on full).

---

### `web/src/lib/sse.ts` (MODIFY — add `memory.written` / `memory.read` to eventTypes)

**Current code** (lines 69-81):

```typescript
const eventTypes = [
  "world.snapshot",
  "cost.tick",
  "attest.append",
  "agent.log",
  "fence.breach",
  "drone.update",
  "vet_intake.drafted",
  "neighbor.handoff",
  "scenario.active",
  "scenario.ended",
];
```

**Required modification:** append `"memory.written"` and `"memory.read"`. This is a one-line change but MUST happen in the same commit as the server-side broadcast — otherwise `SkyHerdSSE.on("memory.written", h)` silently no-ops (the handler registers but no `addEventListener` is wired for that type).

---

### `web/src/components/MemoryPanel.tsx` (React component, streaming + fetch)

**Analog:** `web/src/components/AttestationPanel.tsx` — mirror the file 1:1 with the field substitutions below.

**Imports pattern** (verbatim from `AttestationPanel.tsx:6-9`):

```typescript
import { useState, useEffect, useCallback, Fragment } from "react";
import { cn } from "@/lib/cn";
import { getSSE } from "@/lib/sse";
import { Tooltip } from "@/components/ui/tooltip";
```

**Interface pattern** (substitute fields from `AttestationPanel.tsx:11-21` — Memory REST shape from CONTEXT `<spike_findings>` lines 130-142):

```typescript
interface MemoryEntry {
  memory_id: string;           // mem_*
  memory_version_id: string;   // memver_*
  memory_store_id: string;     // memstore_*
  path: string;                // "patterns/coyote-crossings.md"
  content_sha256: string;
  content_size_bytes: number;
  created_at: string;
  operation?: "created" | "updated" | "deleted" | "redacted";
  created_by?: { type: string; api_key_id: string };
}
```

**HashChip reuse** (CRITICAL — do NOT duplicate).

`AttestationPanel.tsx` defines `HashChip` locally at lines 48-113. Per RESEARCH §Recommended Project Structure, the planner MUST extract `HashChip` to `web/src/components/shared/HashChip.tsx` BEFORE adding `MemoryPanel.tsx`. Import path then becomes:

```typescript
import { HashChip } from "@/components/shared/HashChip";
```

Render the `memory_version_id` (`memver_*`) through `HashChip`. The existing 4-swatch visual contract (4 × 6-hex-char groups at `AttestationPanel.tsx:56-63`) works for `memver_01XRSVdKC1McTbhVbVF5T47E` — base62 chars cast to hex colors by slicing the trailing portion, OR compute sha256 of the full ID and slice that (cleaner). The planner should decide and document.

**SSE wire-up pattern** (copy from `AttestationPanel.tsx:171-194`):

```typescript
useEffect(() => {
  const sse = getSSE();
  sse.on("memory.written", handleMemoryWritten);
  sse.on("memory.read", handleMemoryRead);
  fetch(`/api/memory/${activeAgent}`)
    .then((r) => r.json())
    .then((data) => {
      if (Array.isArray(data.entries)) {
        setEntries((prev) => {
          // dedupe-by-memver_id + slice to MAX_ENTRIES
        });
      }
    })
    .catch(() => {});
  return () => {
    sse.off("memory.written", handleMemoryWritten);
    sse.off("memory.read", handleMemoryRead);
  };
}, [activeAgent, handleMemoryWritten, handleMemoryRead]);
```

**Collapse + animation pattern** — mirror `collapseStyle` at `AttestationPanel.tsx:196-198`. The demo-critical write-flash animation (CONTEXT `<specifics>` line 85-86) should be added via a CSS class toggled for 800ms after each `memory.written` event (new addition; no direct analog — follow `chip-sage` / `chip-thermal` token pattern at `AttestationPanel.tsx:25-32`).

**Per-agent tab switcher** — NEW UI element not in AttestationPanel. Pattern to mirror: the per-agent lane structure in `web/src/components/AgentLanes.tsx` (horizontal tab row), consuming `AGENT_NAMES` from a const array (copy structure from `events.py:33-39`; replicate the array on the frontend as `const AGENTS = ["FenceLineDispatcher", ...]` — there is no existing TS export to import from).

**Fields/signatures the new file MUST replicate:**
- `data-testid="hash-chip"` (line 83) — drives existing test pattern.
- `data-testid="hash-swatch"` (line 99) — drives `swatches.length === 4` test (AttestationPanel.test.tsx:208-210).
- `MAX_ENTRIES = 50` (line 128).
- `navigator.clipboard.writeText` fallback try/catch (lines 66-74).
- `aria-label="Memory chain"` (mirror `aria-label="Attestation chain"` at line 208).

---

### `tests/agents/test_memory.py` (unit tests, stubbed client)

**Analog:** `tests/agents/test_managed.py` — AsyncMock pattern + `ManagedAgentsUnavailable` guard.

**Imports pattern** (copy from `test_managed.py:1-27`):

```python
"""Tests for MemoryStoreManager and LocalMemoryStore.

All external Anthropic REST calls are mocked — no real API key required.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skyherd.agents.memory import (
    LocalMemoryStore,
    MemoryStoreManager,
    get_memory_store_manager,
)
from skyherd.agents.managed import ManagedAgentsUnavailable
```

**Guard-test pattern** (copy from `test_managed.py:60-67`):

```python
class TestManagedAgentsUnavailable:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ManagedAgentsUnavailable, match="ANTHROPIC_API_KEY"):
            MemoryStoreManager(api_key="")
```

**Factory-test pattern** (copy `TestGetSessionManagerFactory` at `test_managed.py:75-95`):

```python
class TestGetMemoryStoreManagerFactory:
    def test_local_runtime_returns_local(self):
        mgr = get_memory_store_manager(runtime="local")
        assert isinstance(mgr, LocalMemoryStore)

    def test_auto_without_env_returns_local(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("SKYHERD_AGENTS", raising=False)
        mgr = get_memory_store_manager(runtime="auto")
        assert isinstance(mgr, LocalMemoryStore)
```

**REST-mocking pattern** — RESEARCH §Pattern 1 requires an injectable `client=` kwarg. Tests inject an `AsyncMock()` with `.post` and `.get` returning the REST shapes from CONTEXT `<spike_findings>` lines 130-142:

```python
@pytest.mark.asyncio
async def test_create_store_parses_response(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    client = AsyncMock()
    client.post.return_value = {
        "id": "memstore_018S1WJAA5mpXW9mTH3YXqzE",
        "name": "memstore_ranch_a_shared",
        "description": None,
        "type": "memory_store",
        "created_at": "2026-04-23T20:10:00Z",
        "updated_at": "2026-04-23T20:10:00Z",
    }
    mgr = MemoryStoreManager(api_key="sk-test-fake", client=client)
    store = await mgr.create_store("memstore_ranch_a_shared")
    assert store.id.startswith("memstore_")
    client.post.assert_awaited_once()
    _, kwargs = client.post.await_args
    assert kwargs["options"]["headers"]["anthropic-beta"] == "managed-agents-2026-04-01"
```

---

### `tests/server/test_memory_api.py` (API tests, httpx AsyncClient)

**Analog:** `tests/server/test_app.py` (lines 18-31 fixture + lines 120-133 `/api/attest` tests).

**Fixture pattern** (copy verbatim from `test_app.py:18-31`):

```python
@pytest.fixture
def mock_app():
    return create_app(mock=True)


@pytest_asyncio.fixture
async def client(mock_app):
    async with AsyncClient(
        transport=ASGITransport(app=mock_app, raise_app_exceptions=True),
        base_url="http://test",
    ) as c:
        yield c
```

**Test shape** (copy from `test_app.py:120-133`):

```python
@pytest.mark.asyncio
async def test_memory_returns_entries(client):
    resp = await client.get("/api/memory/FenceLineDispatcher")
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert isinstance(data["entries"], list)


@pytest.mark.asyncio
async def test_memory_rejects_unknown_agent(client):
    resp = await client.get("/api/memory/UnknownAgent")
    assert resp.status_code == 404
```

---

### `web/src/components/MemoryPanel.test.tsx` (vitest component test)

**Analog:** `web/src/components/AttestationPanel.test.tsx` — copy the fetch-mock + sseHandlers scaffolding verbatim, substitute fields.

**Mock scaffolding pattern** (copy verbatim from `AttestationPanel.test.tsx:1-27`):

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";
import { MemoryPanel } from "./MemoryPanel";

vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
  ok: true,
  json: () => Promise.resolve({ entries: [], ts: Date.now() / 1000 }),
}));

let sseHandlers: Record<string, ((payload: unknown) => void)[]> = {};

vi.mock("@/lib/sse", () => ({
  getSSE: () => ({
    on: (eventType: string, handler: (payload: unknown) => void) => {
      if (!sseHandlers[eventType]) sseHandlers[eventType] = [];
      sseHandlers[eventType].push(handler);
    },
    off: (eventType: string, handler: (payload: unknown) => void) => {
      sseHandlers[eventType] = (sseHandlers[eventType] ?? []).filter((h) => h !== handler);
    },
  }),
}));

function triggerSSE(eventType: string, payload: unknown) {
  (sseHandlers[eventType] ?? []).forEach((h) => h(payload));
}
```

**Sample entry** (substitute shape from REST spike):

```typescript
const SAMPLE_MEMORY = {
  memory_id: "mem_0126mdrYVnARX4Q9iteMiNaB",
  memory_version_id: "memver_01XRSVdKC1McTbhVbVF5T47E",
  memory_store_id: "memstore_018S1WJAA5mpXW9mTH3YXqzE",
  path: "patterns/coyote-crossings.md",
  content_sha256: "cafebabedeadbeef12345678aabbccdd99887766554433221100ffeeddccbbaa",
  content_size_bytes: 512,
  created_at: "2026-04-23T20:10:00Z",
  operation: "created",
};
```

**HashChip test replication** (copy from `AttestationPanel.test.tsx:197-234`):

```typescript
it("renders HashChip for memory_version_id with 4 swatches", async () => {
  await act(async () => { render(<MemoryPanel />); });
  act(() => { triggerSSE("memory.written", SAMPLE_MEMORY); });
  const chips = document.querySelectorAll("[data-testid='hash-chip']");
  expect(chips.length).toBeGreaterThanOrEqual(1);
});
```

---

## Shared Patterns

### Authentication / API key gating

**Source:** `src/skyherd/agents/managed.py:142-148` (ManagedAgentsUnavailable raise).

**Apply to:** `memory.py::MemoryStoreManager.__init__`.

```python
_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
if not _key:
    raise ManagedAgentsUnavailable(
        "ANTHROPIC_API_KEY not set — cannot initialise ManagedSessionManager. "
        "Set ANTHROPIC_API_KEY or use runtime='local'."
    )
```

### Runtime gate

**Source:** `src/skyherd/agents/session.py:391-447` (`get_session_manager` factory — checks `SKYHERD_AGENTS=="managed"` + `ANTHROPIC_API_KEY`).

**Apply to:** `memory.py::get_memory_store_manager` + the resource-attachment in `managed.py::create_session_async` (only attaches `resources=[...]` when `_memory_store_ids` is populated, which only happens in managed runtime).

```python
if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("SKYHERD_AGENTS") == "managed":
    try:
        return ManagedSessionManager(...)
    except Exception as exc:
        logger.warning("fallback to local: %s", exc)
return LocalSessionManager(...)
```

### Runtime persistence (idempotent ID cache)

**Source:** `src/skyherd/agents/managed.py:202-229` — `runtime/agent_ids.json` pattern.

**Apply to:** `memory.py` — `runtime/memory_store_ids.json` with the SAME shape (`{name: id}` dict). Path must be gitignored (mirror `.gitignore` rules — already covers `runtime/` — verify before committing).

```python
self._store_ids_path.parent.mkdir(parents=True, exist_ok=True)
self._store_ids_path.write_text(json.dumps(self._store_ids, indent=2))
```

### Non-blocking exception swallow (hook safety)

**Source:** `src/skyherd/agents/_handler_base.py:247-250` — APIError swallowed and logged.

**Apply to:** `memory_hook.py::post_cycle_write` + the hook invocation site in `_handler_base.py`. NEVER let a memory write failure cancel a handler wake cycle.

```python
except Exception as exc:  # noqa: BLE001
    logger.warning("memory post-cycle write failed for %s: %s", agent_name, exc)
```

### Prompt cache preservation (NEGATIVE pattern — do NOT touch)

**Source:** `src/skyherd/agents/session.py:110-152` (`build_cached_messages`).

**Apply to:** Every plan touching managed.py. Memory adds resources at `sessions.create()`; it does NOT modify `messages.create()` or `events.send()` payloads. The `cache_control: ephemeral` blocks on `system_blocks` at line 125-131 and on each skill block at lines 136-142 MUST remain untouched. CONTEXT `<code_context>` line 58 is explicit: "DO NOT touch cache structure when adding memory."

### SSE event registration (two-sided)

**Source:** `web/src/lib/sse.ts:69-81` (`eventTypes` array) + `src/skyherd/server/events.py:411-415` (broadcast fan-out).

**Apply to:** Every new SSE event type. Must register BOTH sides in the same commit:

1. `web/src/lib/sse.ts` `eventTypes` array → `"memory.written"`, `"memory.read"`.
2. `src/skyherd/server/events.py` → `self._broadcast("memory.written", payload)` call path.

Missing either side breaks the live demo silently (MemoryPanel mounts handler; no events fire; no error thrown).

### Determinism guard (seed=42 byte-identical)

**Source:** CONTEXT locked constraint + RESEARCH §Pattern 1 `LocalMemoryStore._det_id` (sha256-of-seed hex prefix).

**Apply to:** `LocalMemoryStore.create_store` + `write_memory` — IDs MUST be content-derived, NOT time- or uuid-derived. Same requirement bans `datetime.now()` in `memory_paths.py::decide_write_path`.

Sanitizer regex in `tests/test_determinism_e2e.py` already strips hex UUIDs + ISO timestamps; the planner MUST extend it to strip `memver_<base62>` / `mem_<base62>` / `memstore_<base62>` patterns when `SKYHERD_AGENTS=managed` is used in replay (otherwise skip replay-under-managed — it's deferred per RESEARCH).

### Attestation pairing (dual-receipt demo moment)

**Source:** `src/skyherd/attest/ledger.py:167` — `Ledger.append(source, kind, payload)`.

**Apply to:** `memory_hook.py::post_cycle_write`. Every memory write MUST also emit a ledger entry:

```python
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
```

Both receipts (memver chain + Ed25519 ledger) render side-by-side in the MemoryPanel (CONTEXT `<specifics>` + CONTEXT `<code_context>` line 61).

### AGENT_NAMES constant (single source of truth)

**Source:** `src/skyherd/server/events.py:33-39` — 5 names in list.

**Apply to:** `memory_api.py` (path validation), `memory_paths.py` (agent-name switch), `MemoryPanel.tsx` (tab switcher). Python side: `from skyherd.server.events import AGENT_NAMES`. Frontend: duplicate the array inline in `MemoryPanel.tsx` (no current export — adding a TS export is out of scope for this phase; note as tech debt).

---

## No Analog Found

No new files in this phase lack an analog. All classifications above map to concrete existing patterns in the codebase.

---

## Metadata

**Analog search scope:**
- `src/skyherd/agents/` — all 16 Python files
- `src/skyherd/server/` — all 7 Python files
- `src/skyherd/attest/ledger.py` — ledger append signature
- `web/src/components/` — all 14 TSX files
- `web/src/lib/sse.ts` — SSE client
- `tests/agents/` + `tests/server/` — 22 test files

**Files scanned for analog candidates:** 59

**Pattern extraction date:** 2026-04-23

**Key cross-cutting invariants (for planner):**
1. Runtime gate: `SKYHERD_AGENTS=="managed"` + `ANTHROPIC_API_KEY` → everything else falls back to local shim.
2. Idempotent ID cache under `runtime/<name>_ids.json`, mirroring `runtime/agent_ids.json`.
3. `ManagedAgentsUnavailable` is the only sentinel — reuse, do not redefine.
4. Prompt cache (system + skills with `cache_control: ephemeral`) is untouched by memory.
5. Every SSE event type registers on both server broadcast AND `web/src/lib/sse.ts:eventTypes`.
6. Memory write → ledger append → SSE emit = atomic three-step per cycle. All three in `memory_hook.py::post_cycle_write`.
7. Agent name whitelist = `events.py:AGENT_NAMES` (Python) + inline array (TS). Never accept arbitrary agent strings at API or path level.
8. `_handler_base.py::run_handler_cycle` currently does NOT receive `wake_event` — planner must either add it as a parameter (threaded through 5 handler files) or read from `session.wake_events_consumed[-1]` (preferred, zero-signature-change).
