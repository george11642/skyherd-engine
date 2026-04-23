# Phase 2: Cross-Ranch Mesh Promotion — Context

**Gathered:** 2026-04-23
**Status:** Ready for planning
**Mode:** Auto-generated from orchestrator mission (workflow.skip_discuss=true)
**Deadline:** 2026-04-26 20:00 EST (~68h remaining)

<domain>
## Phase Boundary

Promote the cross-ranch coyote bonus scenario to a first-class feature. Phase 1
gave us the Memory topology (1 shared read-only + 5 per-agent read_write). Phase
2 adds a **sixth agent** (CrossRanchCoordinator), wires a /api/neighbors REST
endpoint, drops a CrossRanchPanel into the dashboard, and hardens the
cross_ranch_coyote scenario so judges see a full agent dispatch (not just an
event-presence assert).

### Scope (locked from orchestrator mission)

1. **CrossRanchCoordinator agent (6th agent)** — new module
   `src/skyherd/agents/cross_ranch_coordinator.py`, spec
   `CROSS_RANCH_COORDINATOR_SPEC`, system-prompt file
   `src/skyherd/agents/prompts/cross_ranch_coordinator.md`. Triggers on
   `skyherd/neighbor/+/+/predator_confirmed`. Tools: `drone_mcp`, `sensor_mcp`,
   `galileo_mcp`. Skills: 4-6 from `predator-ids/`, `nm-ecology/`,
   `voice-persona/`.
2. **Neighbor mesh API** — `GET /api/neighbors` in `src/skyherd/server/app.py`
   returns the neighbor-handoff log (inbound + outbound). Data source:
   `mesh_neighbor.py` log entries + an in-memory ring buffer on the broadcaster.
3. **CrossRanchPanel.tsx** — `web/src/components/CrossRanchPanel.tsx` showing
   inbound/outbound neighbor alerts with ranch names + timestamps. Mount in
   App.tsx aside-column grid (alongside MemoryPanel).
4. **Memory integration** — CrossRanchCoordinator writes to the shared store
   `memstore_ranch_a_shared` under path prefix `/neighbors/{ranch_id}/` via
   Phase 1's `memory_hook` → extends `memory_paths._DISPATCH` with the new
   agent branch. Uses `get_memory_store_manager()` factory.
5. **Scenario upgrade** — promote `cross_ranch_coyote` bonus scenario: full
   agent dispatch (not just event presence), assertions that
   CrossRanchCoordinator was dispatched AND wrote to shared memory AND drone
   was silently pre-positioned.
6. **New SSE event**: `neighbor.alert` registered in `web/src/lib/sse.ts`
   eventTypes registry. Companion `neighbor.handoff` event already exists from
   Phase 0 bonus work — distinct semantics:
     - `neighbor.alert` = inbound alert RECEIVED by CrossRanchCoordinator.
     - `neighbor.handoff` = outbound pre-position executed by ranch_b.

### Depends on

Phase 1 (Memory-Powered Agent Mesh, shipped 2026-04-23). Specifically:
- `AgentMesh._ensure_memory_stores` registers `_shared` + 5 per-agent stores;
  we add a 6th entry for `CrossRanchCoordinator` keyed the same way.
- `memory_hook.post_cycle_write` is the write path; we extend
  `memory_paths.decide_write_path` to handle the new agent name.
- `LocalMemoryStore` + deterministic memver IDs already in place; determinism
  sanitizer covers `memver_/mem_/memstore_` so a new agent's writes stay
  byte-identical across replays.

</domain>

<decisions>
## Implementation Decisions

### Claude's discretion (skip_discuss=true)

All choices locked inline. Use the Phase 1 pattern throughout — AgentSpec +
handler + simulate.py entry + memory_paths branch + app.py mount +
React component + sse.ts eventTypes + tests at every layer.

### Locked constraints (inherited from v1.0 and Phase 1)

- **Beta header** — `managed-agents-2026-04-01` unchanged; Memory rides same
  header. SDK auto-applies.
- **Prompt caching** — every `messages.create` / `sessions.events.send` emits
  `cache_control: ephemeral` on system + skills. Use `build_cached_messages`
  exactly like existing 5 agents.
- **Determinism** — `make demo SEED=42 SCENARIO=all` byte-identical across 3
  replays. Phase 1 sanitizer already covers `memver_`. Any new IDs that flow
  into log lines need adding to `DETERMINISM_SANITIZE` (list in
  `tests/test_determinism_e2e.py:21`).
- **Coverage floor** — ≥ 80% repo-wide. New `cross_ranch_coordinator.py`
  targets ≥ 90%.
- **Licensing** — MIT only. Zero AGPL. No new deps.
- **Attribution** — zero Claude/Anthropic attribution on commits.
- **No user delegation** — all automation; no "check your email" prompts.

### Design choices (pre-decided)

- **Agent placement** — register in AgentMesh's `_AGENT_REGISTRY` as the 6th
  entry. `AGENT_NAMES` in `events.py` extends to length 6. All existing
  5-agent counters (MemoryPanel tabs, cost tick names) extend transparently.
- **Skills selection (5 files, 3 directories):**
  - `predator-ids/coyote.md`
  - `predator-ids/thermal-signatures.md`
  - `nm-ecology/nm-predator-ranges.md`
  - `voice-persona/wes-register.md`
  - `voice-persona/urgency-tiers.md`
- **System prompt theme** — Judge-visible: "You are CrossRanchCoordinator.
  Neighbor alerts are LEADING indicators. Pre-position silently. Do NOT page
  the rancher unless threat cascades. Write a pattern summary to shared
  memory under /neighbors/{from_ranch}/…"
- **Memory path convention** — `/neighbors/{from_ranch}/{shared_fence}.md`
  in the shared store. Content = predator species, confidence, ts, and the
  response chosen (pre_position | escalate).
- **Tool surface** — `get_thermal_clip`, `launch_drone` (pre_position mission
  kind), `log_agent_event`. No `page_rancher` in the normal path; only when
  threat cascades (direct breach on same segment within 5 min).
- **Handler simulation path** — reuse `mesh_neighbor._simulate_neighbor_handler`
  where possible. Add a thin CrossRanchCoordinator-specific simulation that
  augments the existing output with a `memstore.write` tool record so the
  assertion "CrossRanchCoordinator wrote to memory" can inspect the tool log.
- **SSE event split**:
  - `neighbor.alert` (new) — fired when CrossRanchCoordinator WAKES on an
    inbound neighbor event. Payload: `{from_ranch, to_ranch, species,
    confidence, shared_fence, ts}`.
  - `neighbor.handoff` (existing) — fired AFTER pre-position mission uploaded.
    Payload: same + `response_mode` + `tool_calls` + `rancher_paged`.
- **/api/neighbors** — mirrors `/api/attest` and `/api/memory/{agent}` shape:
  `{"entries": [...], "ts": <epoch>}`. Sources: `NeighborBroadcaster` +
  `NeighborListener` in-memory log (both extend those classes with a
  `recent_events` ring buffer, cap 100).
- **CrossRanchPanel layout** — mount in App.tsx's right-side `<aside>` column
  below MemoryPanel. Two-column split: inbound | outbound, each a table with
  ranch name + timestamp + species. Flash animation on new entries (mirror
  MemoryPanel pattern).
- **Scenario upgrade** — `cross_ranch_coyote` scenario's `assert_outcome`
  adds three new assertions: (a) CrossRanchCoordinator appears in the mesh's
  tool_call_log, (b) a `memstore.write` tool call was recorded with a
  `/neighbors/` path, (c) the `launch_drone` mission kind is
  `neighbor_pre_position_patrol` (silent signature, not page-worthy).

### Non-regressions (hard requirements)

- Phase 1's MemoryPanel + /api/memory/{agent} still work — new agent name
  must render as a 6th tab without breaking tests (update MemoryPanel.test.tsx
  expectation if the list is hard-coded).
- Determinism across 3 replays must hold — run
  `uv run pytest tests/test_determinism_e2e.py -v -m slow` before closing.
- All 1365 current tests still pass; target ≥ 1380 after Phase 2.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `src/skyherd/agents/mesh_neighbor.py` (688 lines) — `NeighborBroadcaster` +
  `NeighborListener` + `CrossRanchMesh`. Already has
  `simulate_coyote_at_shared_fence` that drives the end-to-end cascade without
  API keys. Extend with a `recent_events` ring buffer on broadcaster+listener.
- `src/skyherd/agents/mesh.py` — `AgentMesh` orchestrator, `_AGENT_REGISTRY`
  is the registration point. `_ensure_memory_stores` already creates 1 shared
  + 5 per-agent; extend to include the new 6th agent.
- `src/skyherd/agents/spec.py` — `AgentSpec` dataclass. Nothing new needed.
- `src/skyherd/agents/fenceline_dispatcher.py` — closest analog (also reacts
  to fence events); use as template for handler shape.
- `src/skyherd/agents/_handler_base.py` — `run_handler_cycle` auto-hooks
  `memory_hook.post_cycle_write` — all we do is inherit through the standard
  handler shape.
- `src/skyherd/agents/memory_paths.py` — pure module with `_DISPATCH`
  registry. Add `_cross_ranch_coordinator(event, tool_calls) -> (path, content)`
  branch + `_KNOWN_AGENTS` set update.
- `src/skyherd/server/events.py:33-39` — `AGENT_NAMES` list of 5. Extend to
  6. All downstream (MemoryPanel tabs, mock generators) read this list.
- `src/skyherd/server/app.py` — add a `@app.get("/api/neighbors")` route
  near existing `/api/attest` and `/api/memory` mounts. Mock mode returns
  synthesised entries.
- `src/skyherd/scenarios/cross_ranch_coyote.py` — existing bonus scenario.
  Upgrade `assert_outcome` to demand CrossRanchCoordinator dispatch + memory
  write + silent launch_drone.
- `web/src/components/MemoryPanel.tsx` — reference for tab layout + HashChip
  flash animation.
- `web/src/components/AgentLane.tsx` — reference for per-agent rows.
- `web/src/lib/sse.ts:69-82` — eventTypes list. Add `neighbor.alert` (keep
  existing `neighbor.handoff`).

### Established Patterns

- **Runtime switch** — `SKYHERD_AGENTS=managed` flips `LocalSessionManager`
  to `ManagedSessionManager`. Memory code already respects the same gate. The
  new agent must too — use `os.environ.get("ANTHROPIC_API_KEY")` guard pattern
  in the handler.
- **Prompt cache** — skills + system in separate `cache_control` blocks; user
  message is volatile. `session_prompt_cached_hash` at `session.py:72` tracks
  staleness. No touches here.
- **GC prevention** — `_inflight_handlers` set + done_callback(discard) in
  `AgentMesh`. New agent's handler wakes flow through the same path; no extra
  wiring needed.
- **SSE event types** — `web/src/lib/sse.ts:eventTypes` registry is the
  single source of truth. Add `neighbor.alert` and ensure the REST API + the
  broadcaster emit this type.

### Integration Points

- **Agent registration** — `mesh.py:_AGENT_REGISTRY` — add the new tuple.
- **Memory store ensure** — `mesh.py:_ensure_memory_stores` — its loop
  iterates over `AGENT_NAMES`, so extending that list does the work. No code
  change to `_ensure_memory_stores` itself.
- **Memory path dispatch** — `memory_paths.py` — add new branch +
  `_KNOWN_AGENTS` update; call sites automatic.
- **Dashboard mount** — `web/src/App.tsx` — add `<CrossRanchPanel />`
  inside the right-hand `<aside>` column below MemoryPanel.
- **Neighbor log ring buffer** — add `_recent: collections.deque` to both
  `NeighborBroadcaster` and `NeighborListener`. `/api/neighbors` reads this.

</code_context>

<requirements>
## Phase 2 Requirements (derived CRM-01..CRM-06)

| ID | Requirement | Covered by |
|----|-------------|-----------|
| CRM-01 | CrossRanchCoordinator agent (6th agent) ships with SPEC, handler, system-prompt file, simulation path, and registered in AgentMesh | Plan 02-01 |
| CRM-02 | `AgentMesh._ensure_memory_stores` creates the 6th per-agent store idempotently | Plan 02-02 |
| CRM-03 | `memory_paths.decide_write_path` handles `CrossRanchCoordinator` — writes under `/neighbors/{from_ranch}/…` into shared store | Plan 02-02 |
| CRM-04 | `/api/neighbors` endpoint returns inbound + outbound handoff log; in-memory ring buffer on broadcaster/listener | Plan 02-03 |
| CRM-05 | `neighbor.alert` SSE event registered in `web/src/lib/sse.ts` eventTypes and emitted by CrossRanchMesh on ingress | Plan 02-03 |
| CRM-06 | `CrossRanchPanel.tsx` mounted in App.tsx; `cross_ranch_coyote` scenario passes upgraded assertions (dispatch + memory write + silent pre-position) | Plan 02-04 |

Coverage floor: ≥ 80% repo-wide; ≥ 90% on `cross_ranch_coordinator.py`.

</requirements>

<plan_shape>
## Plan Shape (4 plans, single wave)

All plans run sequentially in wave 1 (no parallelism — each plan touches
shared state the previous one established).

### Plan 02-01: CrossRanchCoordinator agent + spec + system prompt + tests
- `src/skyherd/agents/cross_ranch_coordinator.py` (new)
- `src/skyherd/agents/prompts/cross_ranch_coordinator.md` (new)
- `src/skyherd/agents/simulate.py` (extend with handler)
- `src/skyherd/server/events.py` (append name to AGENT_NAMES)
- `tests/agents/test_cross_ranch_coordinator.py` (new, ≥ 90% coverage)

### Plan 02-02: Mesh wiring + memory paths integration + shared store writes
- `src/skyherd/agents/mesh.py` (append agent tuple to `_AGENT_REGISTRY`)
- `src/skyherd/agents/memory_paths.py` (new branch + `_KNOWN_AGENTS` update)
- `src/skyherd/agents/mesh_neighbor.py` (add `recent_events` ring buffer;
  emit `neighbor.alert` + wire CrossRanchCoordinator dispatch)
- `tests/agents/test_memory_paths.py` (extend with CrossRanchCoordinator branch)
- `tests/agents/test_mesh.py` / `test_neighbor_mesh.py` (extend)

### Plan 02-03: /api/neighbors endpoint + scenario upgrade + SSE event type
- `src/skyherd/server/app.py` (new `/api/neighbors` route)
- `src/skyherd/server/events.py` (emit `neighbor.alert` via broadcaster;
  `broadcast_neighbor_alert` helper)
- `src/skyherd/scenarios/cross_ranch_coyote.py` (upgraded `assert_outcome`)
- `web/src/lib/sse.ts` (append `neighbor.alert` to eventTypes)
- `tests/server/test_app_neighbors.py` (new) + extend
  `tests/scenarios/test_cross_ranch_coyote.py` if present

### Plan 02-04: CrossRanchPanel.tsx + App.tsx mount + vitest coverage
- `web/src/components/CrossRanchPanel.tsx` (new)
- `web/src/components/CrossRanchPanel.test.tsx` (new, ≥ 5 tests)
- `web/src/App.tsx` (mount CrossRanchPanel)
- `web/src/components/MemoryPanel.test.tsx` (update agent count if hard-coded)
- MemoryPanel.tsx: update `AGENTS` array if it excludes the new one
  (it does — will add a gate so the new agent does NOT appear in the 5-agent
   mem tabs — it writes to the SHARED store, not a per-agent store).

</plan_shape>

<non_goals>
## Out of Scope for Phase 2

- Live Twilio/ElevenLabs voice calls for cross-ranch handoffs (Phase 3).
- Public attestation viewer (`/attest/{hash}` page — Phase 4).
- Hardware prep (Phases 5–8).
- Demo video scaffolding (Phase 9).
- Multi-neighbor fan-out (>2 ranches) — Phase 2 keeps the 2-ranch demo scope.
- Real MQTT broker wire-up for neighbor topic (remains in-memory for demo
  determinism; real broker tested elsewhere).

</non_goals>
</content>
</invoke>