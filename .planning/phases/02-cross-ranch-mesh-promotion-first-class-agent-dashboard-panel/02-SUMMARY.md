---
phase: 02
plan: all
status: complete
completed: 2026-04-23
plans: 4/4
tests_before: 1365
tests_after: 1407
vitest_before: 77
vitest_after: 84
coverage_total: 88.96% (target ≥ 80%)
coverage_cross_ranch_coordinator: 100% (target ≥ 90%)
coverage_memory_paths: 100%
coverage_mesh_neighbor: 95%
coverage_server_app: 84%
---

# Phase 02 — Cross-Ranch Mesh Promotion — SUMMARY

## Scope shipped

Promoted cross-ranch coyote scenario to first-class feature:

1. **CrossRanchCoordinator agent (6th agent)** — `src/skyherd/agents/cross_ranch_coordinator.py`
   + system prompt at `src/skyherd/agents/prompts/cross_ranch_coordinator.md`. Triggers
   on `skyherd/neighbor/+/+/predator_confirmed`. Uses `build_cached_messages` (prompt
   caching mandatory).
2. **AgentMesh wiring** — appended to `_AGENT_REGISTRY` and `_SMOKE_WAKE_EVENTS`;
   `AGENT_NAMES` extended to 6 in `src/skyherd/server/events.py`.
3. **Memory integration** — `memory_paths.decide_write_path` handles the new agent,
   writing under `/neighbors/{from_ranch}/{shared_fence}.md` (caller `_normalize_path`
   prepends `/`).
4. **Neighbor log ring buffer** — `NeighborBroadcaster.recent_events` +
   `NeighborListener.recent_events` (deque maxlen=100); `CrossRanchMesh.recent_events()`
   merges in+out sorted by ts desc.
5. **`/api/neighbors` endpoint** — new route in `src/skyherd/server/app.py`; mock
   entries when no mesh, live entries via `mesh.recent_events()` callable; exception
   path returns `[]`.
6. **SSE events** — `neighbor.alert` added to `web/src/lib/sse.ts` eventTypes;
   `EventBroadcaster.broadcast_neighbor_alert` helper for server-side fan-out.
7. **CrossRanchPanel dashboard** — `web/src/components/CrossRanchPanel.tsx` with
   inbound/outbound two-column layout, flash animation on SSE events, dedupe
   by composite key, mounted in `App.tsx` below MemoryPanel.
8. **Scenario upgrade** — `cross_ranch_coyote.assert_outcome` gains 3 new
   assertions: launch_drone mission == `neighbor_pre_position_patrol`,
   log_agent_event response_mode == `pre_position`, `sim_result.ranch_b_pre_positioned`
   == True.

## Plans completed

| Plan | Focus | Status | Commit |
|------|-------|--------|--------|
| 02-01 | CrossRanchCoordinator agent + spec + prompt + sim + tests | PASS | `feat(02-01)` |
| 02-02 | Mesh wiring + memory_paths + recent_events + broadcast_neighbor_alert | PASS | `feat(02-02)` |
| 02-03 | /api/neighbors + SSE eventTypes + scenario upgrade | PASS | `feat(02-03)` |
| 02-04 | CrossRanchPanel.tsx + App mount + vitest | PASS | `feat(02-04)` |

## Requirements (CRM-01..CRM-06)

All 6 Phase 2 requirements satisfied — see `02-VERIFICATION.md`.

## Files shipped

**New (Python):**
- `src/skyherd/agents/cross_ranch_coordinator.py` (143 lines, 100% coverage)
- `src/skyherd/agents/prompts/cross_ranch_coordinator.md` (~55 lines)
- `tests/agents/test_cross_ranch_coordinator.py` (19 tests)
- `tests/server/test_app_neighbors.py` (6 tests)

**New (TypeScript):**
- `web/src/components/CrossRanchPanel.tsx` (~240 lines)
- `web/src/components/CrossRanchPanel.test.tsx` (7 tests)

**Modified:**
- `src/skyherd/agents/mesh.py` — CROSS_RANCH_COORDINATOR_SPEC registered.
- `src/skyherd/agents/simulate.py` — `cross_ranch_coordinator` handler + HANDLERS entry.
- `src/skyherd/agents/memory_paths.py` — `_cross_ranch_coordinator` + `_KNOWN_AGENTS` +1.
- `src/skyherd/agents/mesh_neighbor.py` — deque ring buffers + `CrossRanchMesh.recent_events()`.
- `src/skyherd/server/events.py` — `AGENT_NAMES` +1, `_MOCK_LOG_LINES` entry,
  `broadcast_neighbor_alert` helper.
- `src/skyherd/server/app.py` — `/api/neighbors` endpoint + `_mock_neighbor_entries`
  + `_live_neighbor_entries`.
- `src/skyherd/scenarios/cross_ranch_coyote.py` — `assert_outcome` upgraded.
- `web/src/App.tsx` — `CrossRanchPanel` mounted.
- `web/src/lib/sse.ts` — `neighbor.alert` eventType registered.

**Tests cascaded** (hard-coded `== 5` → `== 6`):
- `tests/agents/test_memory_hook.py::TestMeshEnsureMemoryStores` — 6 → 7 stores.
- `tests/agents/test_mesh.py` — 3 assertions.
- `tests/server/test_app.py` — `test_agents_returns_six_agents`.
- `tests/server/test_app_coverage.py` — 4 assertions.
- `tests/server/test_events.py` — `test_mock_cost_tick_shape`.
- `tests/server/test_events_live.py` — `test_live_cost_tick_emits_six_agents`.

## Commits (4 atomic)

1. `feat(02-01): CrossRanchCoordinator agent (6th agent) — spec, handler, sim, tests`
2. `feat(02-02): mesh wiring + memory_paths branch + neighbor recent_events ring buffer`
3. `feat(02-03): /api/neighbors endpoint + SSE neighbor.alert + first-class scenario`
4. `feat(02-04): CrossRanchPanel dashboard component + App mount + vitest`

Plus 2 docs commits (`docs(02): auto-generated context`, `docs(02): plans 02-01..02-04`).

## Metrics

- Tests: 1365 → 1407 (+42) backend; 77 → 84 (+7) web.
- New Python code: ~410 LOC new + ~140 LOC modified.
- New TypeScript: ~690 LOC new.
- Repo coverage: 88.77% → 88.96%.
- CrossRanchCoordinator: 100% line coverage.
- Bundle size: `index-*.js` 228 KB → 232 KB (gzip 69 → 70 KB).
- Determinism: 3x seed=42 replay PASS (non-slow + slow gates).
- `make demo SEED=42 SCENARIO=all`: 8/8 scenarios PASS.
- `make mesh-smoke`: 6 agents, 15 tool calls (was 5/12) — CrossRanchCoordinator
  emits `get_thermal_clip`, `launch_drone` (silent), `log_agent_event`.

## Ready for Phase 3

Yes. All automated gates pass. No deferred items.
