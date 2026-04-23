# Phase 1: Memory-Powered Agent Mesh - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Adopt the Claude Managed Agents **Memory** public beta (shipped 2026-04-23, existing `managed-agents-2026-04-01` header) across the 5-agent mesh so agents learn per-ranch patterns across sessions, with judge-visible Memory receipts on the dashboard — before the 2026-04-26 8pm EST submission.

### Scope (from ROADMAP.md)

1. **Memory store topology** — one `memstore_ranch_a_shared` read-only domain library + 5 per-agent `read_write` stores, attached via `resources[]` at `client.beta.sessions.create()` in `src/skyherd/agents/managed.py:240`. Workspace-scoped stores enable cross-agent coordination (PredatorPatternLearner writes → FenceLineDispatcher reads on breach).
2. **Memory write hooks in agents** — PredatorPatternLearner writes nightly crossing-pattern summaries; HerdHealthWatcher writes per-cow health baselines; FenceLineDispatcher reads patterns pre-dispatch; CalvingWatch writes labor-signal baselines.
3. **Memory Panel in dashboard** — new `/api/memory/{agent}` endpoint in `src/skyherd/server/app.py` backed by `client.beta.memory_stores.memories.list()` + `memory_versions.list()`; new `MemoryPanel.tsx` in `web/src/components/` with live `memver_…` attestation chain.
4. **Toolset determinism** — `agent_toolset_20260401` selective disable (no `web_search` / `web_fetch`) on CalvingWatch + GrazingOptimizer; preserves `make demo SEED=42 SCENARIO=all` byte-identical.
5. **Runtime guard** — Memory reads/writes stubbed in LocalSessionManager; real `client.beta.memory_stores.*` calls gated on `SKYHERD_AGENTS=managed`.

### Depends on

v1.0 milestone (shipped 2026-04-23) — specifically persistent sessions (one long-lived session per agent, from v1.0 Phase 1) and the `ManagedSessionManager` in `src/skyherd/agents/managed.py`.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

All implementation choices are at Claude's discretion — discuss phase was skipped per `workflow.skip_discuss=true`. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

### Locked constraints (inherited from v1.0 and ROADMAP)

- **Beta header** — `managed-agents-2026-04-01` remains; Memory rides on the same header (no new beta flag). SDK auto-applies.
- **Prompt caching** — every `messages.create` / `sessions.events.send` must emit `cache_control: ephemeral`. Non-negotiable.
- **Determinism** — `make demo SEED=42 SCENARIO=all` byte-identical across 3 replays; wall-timestamps sanitized. Memory calls stubbed in local runtime; real calls only when `SKYHERD_AGENTS=managed`.
- **Coverage floor** — ≥ 80% (`fail_under = 80`). New `memory_*.py` files target ≥ 90% coverage.
- **Licensing** — MIT only; zero AGPL.
- **Attribution** — zero Claude/Anthropic attribution on commits (global git config).

### Design choices (pre-decided from research)

- **Store topology** — `memstore_ranch_a_shared` (read-only, domain library) + 5 per-agent `memstore_<agent>_<ranch>` (read_write). Workspace-scoped per Anthropic docs.
- **Path convention** — `/patterns/<topic>.md` for shared; `/notes/<entity_id>.md` and `/baselines/<metric>.md` for per-agent.
- **Memory vs Skills** — Skills stay packaged/versioned domain knowledge (CrossBeam pattern); Memory is mutable learned facts. No skill → memory migration.
- **Attestation** — Memory `memver_…` chain complements Ed25519 ledger; both logged on every write. The "two independent receipts agree" demo moment.
- **Toolset disable** — CalvingWatch + GrazingOptimizer disable `web_search`/`web_fetch` via `configs` array at `agents.create()`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (from codebase map)

- `src/skyherd/agents/managed.py:185-404` — `ManagedSessionManager` handles env/agent/session lifecycle + event stream. Memory `resources[]` attach point is at `client.beta.sessions.create()` (line 240).
- `src/skyherd/agents/session.py:110-152` — `build_cached_messages()` CrossBeam-style prompt cache with system + skills as separate `cache_control: ephemeral` blocks. DO NOT touch cache structure when adding memory.
- `src/skyherd/agents/mesh.py` — `AgentMesh` orchestrates all 5 sessions. Good place for a shared `memory_store_ids` registry.
- `src/skyherd/mcp/` — 4 MCP servers (`drone_mcp`, `sensor_mcp`, `rancher_mcp`, `galileo_mcp`). Memory does NOT need an MCP server — it's a session resource, not a tool. Direct `client.beta.memory_stores.*` calls inside a helper module.
- `src/skyherd/attest/` — Ed25519 + Merkle attestation ledger. Memory versions are the complementary receipt — pair them in the dashboard display.
- `src/skyherd/server/app.py` — FastAPI live backend; add `/api/memory/{agent}` here. Mirror the `/api/attest` endpoint pattern.
- `web/src/components/` — existing React 19 + Tailwind v4 pattern; add `MemoryPanel.tsx` mirroring `AttestationPanel.tsx` structure.

### Established Patterns

- **Runtime switch** — `SKYHERD_AGENTS=managed` flips `LocalSessionManager` to `ManagedSessionManager`; memory code MUST respect same gate.
- **Prompt cache** — skills + system in separate `cache_control` blocks; user message is volatile (not cached). `system_prompt_cached_hash` at `session.py:72` tracks staleness.
- **GC prevention** — `_inflight_handlers` set + done_callback(discard) in `AgentMesh` (v1.0 H-05 fix). Memory writes inside handlers MUST hold references via same pattern.
- **SSE event types** — `web/src/lib/sse.ts:eventTypes` registry; add `memory.written` / `memory.read` events here for dashboard live stream.

### Integration Points

- **Environment creation** — `client.beta.environments.create()` at `managed.py:185` — unchanged; Memory attaches at session level, not environment.
- **Session creation** — `client.beta.sessions.create()` at `managed.py:240` — add `resources=[{"type": "memory_store", "memory_store_id": msid, "mode": "read_write" | "read_only"}, ...]`.
- **Agent creation** — `client.beta.agents.create()` at `managed.py:216` — add `tools=[{"type": "agent_toolset_20260401", "configs": [{"name": "web_search", "enabled": False}, ...]}]` for deterministic agents.
- **Event handler** — `_handler_base.py:126` — emit `memory.written` SSE after memory writes for dashboard.

</code_context>

<specifics>
## Specific Ideas

### Demo-critical moment

The 3-min video MUST show Memory Panel populating live during `coyote` scenario — PredatorPatternLearner writes `patterns/coyote-crossings.md` with time + location cluster, panel flashes new `memver_…` receipt, FenceLineDispatcher reads it on the next fence breach. This is the "oh damn" for the Managed Agents $5k narrative.

### File layout (new)

- `src/skyherd/agents/memory.py` — MemoryStoreManager (create/attach/list/read/write helpers, runtime-gated)
- `src/skyherd/agents/memory_paths.py` — path conventions (`/patterns/...`, `/notes/...`, `/baselines/...`) + redaction helpers
- `src/skyherd/server/memory_api.py` — `/api/memory/{agent}` endpoint module
- `web/src/components/MemoryPanel.tsx` — dashboard panel with memver chips + content preview
- `tests/agents/test_memory.py` — unit tests (stubbed SDK)
- `tests/server/test_memory_api.py` — API tests
- `tests/agents/test_memory_determinism.py` — determinism guard test (Memory stubbed → no wall drift)
- `web/src/components/MemoryPanel.test.tsx` — vitest component test

### Runtime stub behavior

- `LocalMemoryStore` in-process dict; same API surface as `MemoryStoreManager` but no API calls
- Writes append to `runtime/memory/{agent}.jsonl` for replay visibility
- Reads return latest write per path

### Dashboard integration

- New tile in live grid, slotted after AttestationPanel (mirror styling)
- Per-agent tab switcher (FenceLineDispatcher / HerdHealthWatcher / PredatorPatternLearner / GrazingOptimizer / CalvingWatch)
- Memver chip with click-to-copy full `memver_…` ID (HashChip pattern from v1.1 Part B)
- Live `memory.written` / `memory.read` SSE drives the write-flash animation

</specifics>

<deferred>
## Deferred Ideas

- **Callable agents / multi-agent threads** — research preview feature; skip unless access arrives before Sat. Memory alone gets 80% of the coordination narrative.
- **Advisor tool** (`advisor-tool-2026-03-01`) — nice but doesn't add to Memory narrative; defer to post-hackathon.
- **Memory export endpoint** — `memories.list()` + `memory_versions.list()` dump to tarball. Not in scope for demo; add if time permits.
- **Memory redaction UI** — admin panel for `memory_versions.redact()`. Defer to post-hackathon.
- **Cross-ranch memory sharing** — `memstore_ranch_b_shared` etc.; covered by existing "Cross-Ranch Mesh" milestone plan.
- **Memory → Skills promotion pipeline** — learned facts graduating to versioned skills. Defer.

</deferred>
