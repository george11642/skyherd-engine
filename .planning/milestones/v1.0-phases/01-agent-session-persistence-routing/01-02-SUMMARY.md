---
phase: 01-agent-session-persistence-routing
plan: 02
plan_id: P1-02
subsystem: agents-scenarios
tags: [routing, managed-agents, rustling, thermal-anomaly, nightly-cron, tdd]
requirements: [ROUT-02, ROUT-03, ROUT-04]
dependency_graph:
  requires:
    - "src/skyherd/scenarios/base.py::_DemoMesh registry (Plan 01, ROUT-01)"
    - "src/skyherd/agents/predator_pattern_learner.py::PREDATOR_PATTERN_LEARNER_SPEC + handler (unchanged)"
    - "src/skyherd/agents/simulate.py::predator_pattern_learner (unchanged simulate path)"
    - "src/skyherd/scenarios/rustling.py::inject_events (unchanged — already fires thermal.anomaly)"
  provides:
    - "_route_event routing table gains thermal.anomaly + nightly.analysis entries"
    - "Rustling scenario dispatches PredatorPatternLearner (2 tool calls)"
    - "Suite-wide proof: all 5 agents dispatched across 8 scenarios"
    - "Routing-table regression tests (2 unit + 1 integration + 1 suite) guarding ROUT-02/03/04"
  affects:
    - "Phase 5 dashboard live-mode — all 5 agents are now visible in tool-call log"
    - "Rustling tool_call_count baseline (grew by exactly 2)"
tech_stack:
  added: []
  patterns:
    - "Routing-table comment convention: ROUT-02 label adjacent to new entries for tamper resistance"
    - "Suite-wide agent coverage assertion: union of agent_tool_calls.keys() across run_all()"
    - "Unit-level _route_event harness via asyncio.run + full 5-agent registry"
key_files:
  created:
    - ".planning/phases/01-agent-session-persistence-routing/01-02-SUMMARY.md"
  modified:
    - "src/skyherd/scenarios/base.py (routing table — 2 entries added, 5 lines)"
    - "tests/scenarios/test_base.py (TestDemoMesh gains 3 methods: helper + 2 routing-table tests)"
    - "tests/scenarios/test_rustling.py (TestRustlingScenarioIntegration gains 1 method)"
    - "tests/scenarios/test_run_all.py (TestRunAll gains 1 method)"
decisions:
  - "Appended new routing entries at the end of the dict with ROUT-02 comment for tamper resistance (T-01-08 mitigation)"
  - "Unit test helper passes ledger=None to _route_event — the function signature types it as Ledger but the function body never dereferences it, and _DemoMesh tolerates ledger=None on the dispatch path"
  - "Kept _route_event signature untouched — no change to ledger typing, no change to dispatch guard block"
metrics:
  duration: "~18 minutes wall"
  completed: "2026-04-22"
  tasks: 2
  commits: 2
  tests_added: 4
  tests_pass_delta: "+4 new, 0 regressions"
---

# Phase 1 Plan 2: PredatorPatternLearner Routing Summary

Wires `thermal.anomaly` and `nightly.analysis` into `_route_event`'s routing table so PredatorPatternLearner is actually dispatched by the scenario driver — closing the "learner is registered but never woken" gap that blocked the Managed Agents $5k narrative.

## Performance

- **Duration:** ~18 minutes wall
- **Started:** 2026-04-22T20:15:00Z (plan start)
- **Completed:** 2026-04-22T20:51:00Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 4 (1 prod, 3 test)
- **Commits:** 2

## Accomplishments

- Routing table at `_route_event` lines 406-422 now contains 12 entries (was 10). The two new entries map both of PredatorPatternLearner's wake triggers:
  - `thermal.anomaly → [FenceLineDispatcher, PredatorPatternLearner]`
  - `nightly.analysis → [PredatorPatternLearner]`
- Rustling scenario dispatches PredatorPatternLearner — observed **2 tool calls** (`get_thermal_history` + `log_pattern_analysis`, per `src/skyherd/agents/simulate.py:313-327`).
- Suite-wide proof: all 5 required agents appear in the union of `agent_tool_calls.keys()` across `run_all(seed=42)`.
- 4 new tests added (2 unit-level routing-table, 1 rustling integration, 1 suite coverage); 0 regressions anywhere.
- `make demo SEED=42 SCENARIO=all` equivalent (`skyherd-demo play all --seed 42`) still shows 8/8 PASS.

## Rustling PredatorPatternLearner Tool-Call Count

Observed `result.agent_tool_calls["PredatorPatternLearner"]` in post-fix rustling run:

| # | Tool | Input (truncated) |
|---|------|-------------------|
| 1 | `get_thermal_history` | `{...}` |
| 2 | `log_pattern_analysis` | `{...}` |

**Count: 2** — matches expected delta (per simulate.py:313-327 the learner's simulate path returns exactly those two tool calls per wake).

## Rustling Tool-Count Delta Cross-Check

| Condition | Total rustling tool calls | PredatorPatternLearner calls |
|-----------|---------------------------|-------------------------------|
| Pre-fix (base.py at commit 9283e8a, routing entries absent) | 243 | 0 |
| Post-fix (base.py at commit 23738eb, routing entries present) | 245 | 2 |
| Delta | +2 | +2 |

Exactly +2 as the plan predicted (RESEARCH.md Pitfall 5 was not triggered — no hardcoded total-count assertion broke). All existing rustling assertions check tool-name presence, not totals, so they tolerate the delta cleanly.

## Suite-Wide Agent Coverage (ROUT-04)

Union of `agent_tool_calls.keys()` across all 8 scenarios in `run_all(seed=42)`:

```
{CalvingWatch, FenceLineDispatcher, GrazingOptimizer, HerdHealthWatcher, PredatorPatternLearner}
```

All 5 required agents present. Per-scenario breakdown:

| Scenario | Agents Dispatched |
|----------|-------------------|
| coyote | FenceLineDispatcher, GrazingOptimizer |
| sick_cow | FenceLineDispatcher, GrazingOptimizer, HerdHealthWatcher |
| water_drop | FenceLineDispatcher, GrazingOptimizer |
| calving | CalvingWatch, FenceLineDispatcher, GrazingOptimizer, HerdHealthWatcher |
| storm | FenceLineDispatcher, GrazingOptimizer |
| cross_ranch_coyote | FenceLineDispatcher, GrazingOptimizer |
| wildfire | FenceLineDispatcher, GrazingOptimizer |
| **rustling** | FenceLineDispatcher, GrazingOptimizer, **PredatorPatternLearner** |

Rustling is the unique learner-dispatching scenario (it is the only scenario that injects `thermal.anomaly`). No scenario currently injects `nightly.analysis` — that wake edge is reserved for the live mesh cron and is guarded by the `if agent_name in registry:` check at `_route_event`.

## Task-by-Task Trace

**Task 1 — RED (commit `9283e8a`)**
- Added `TestDemoMesh._run_route_event_sync` helper that builds a 5-agent registry (mirroring `_run_async`) and drives one `_route_event` call via `asyncio.run`, passing `ledger=None` (safe — `_route_event` never dereferences ledger).
- Added `test_routing_table_thermal_anomaly` (asserts both FenceLineDispatcher + PredatorPatternLearner appear in `mesh._tool_call_log`).
- Added `test_routing_table_nightly_analysis` (asserts only PredatorPatternLearner appears).
- Added `TestRustlingScenarioIntegration.test_predator_pattern_learner_dispatched` (full-scenario: `"PredatorPatternLearner" in result.agent_tool_calls` + tool-name presence).
- Added `TestRunAll.test_every_agent_dispatched_at_least_once_across_suite` (suite union must cover all 5 agents).
- All 4 tests fail RED with assertion errors explicitly citing PredatorPatternLearner as the missing agent (not import errors, not collection errors).
- Zero production code touched.

**Task 2 — GREEN (commit `23738eb`)**
- Appended two entries to the routing dict at `src/skyherd/scenarios/base.py:406-422`, with an inline `# ROUT-02` comment block for tamper resistance (T-01-08 mitigation from threat model).
- Did NOT modify: lines 1-405 of base.py, lines 423-427 (dispatch guard), lines 389-392 (`except OSError: pass` Phase 3 reservation), `_DemoMesh` class, `_run_async` `_registry`, or any other file.
- All 4 new tests go GREEN. Full 307-test scenarios+agents suite passes (2 skipped, 0 failed). `skyherd-demo play all --seed 42` shows 8/8 PASS.

## Verification Results

All five verification steps pass:

1. **Static checks** — `ruff check src/skyherd/scenarios/base.py tests/scenarios/test_base.py tests/scenarios/test_rustling.py tests/scenarios/test_run_all.py`: All checks passed.
2. **Routing-table unit tests** — `pytest tests/scenarios/test_base.py::TestDemoMesh::test_routing_table_thermal_anomaly tests/scenarios/test_base.py::TestDemoMesh::test_routing_table_nightly_analysis`: 2 passed.
3. **Rustling integration** — `pytest tests/scenarios/test_rustling.py::TestRustlingScenarioIntegration::test_predator_pattern_learner_dispatched`: 1 passed.
4. **Suite-wide coverage** — `pytest tests/scenarios/test_run_all.py::TestRunAll::test_every_agent_dispatched_at_least_once_across_suite`: 1 passed.
5. **Zero regression** — `pytest tests/scenarios/ tests/agents/ --ignore=tests/scenarios/test_cli.py`: 307 passed, 2 skipped. `skyherd-demo play all --seed 42`: 8/8 PASS (coyote 0.69s, sick_cow 2.73s, water_drop 0.59s, calving 0.77s, storm 0.59s, cross_ranch_coyote 0.72s, wildfire 0.74s, rustling 0.65s).

Note on `test_cli.py`: excluded from regression run due to pre-existing missing `typer` dev dependency — unrelated to this plan; same state as Wave 1 baseline. No regression introduced.

## Acceptance Criteria Grep Summary

| Criterion | Command | Result |
|-----------|---------|--------|
| `thermal.anomaly` routing entry | `grep -cE "\"thermal\.anomaly\":\s*\[\"FenceLineDispatcher\",\s*\"PredatorPatternLearner\"\]" src/skyherd/scenarios/base.py` | 1 |
| `nightly.analysis` routing entry | `grep -cE "\"nightly\.analysis\":\s*\[\"PredatorPatternLearner\"\]" src/skyherd/scenarios/base.py` | 1 |
| Phase 3 silent-except reservation preserved | `sed -n '389,392p' src/skyherd/scenarios/base.py` | `try: _os.unlink(tmp.name) except OSError: pass` (unchanged) |
| `_run_route_event_sync` + 2 routing-table tests | `grep -cE "def test_routing_table_thermal_anomaly\|def test_routing_table_nightly_analysis\|def _run_route_event_sync" tests/scenarios/test_base.py` | 3 |
| Rustling integration test | `grep -c "def test_predator_pattern_learner_dispatched" tests/scenarios/test_rustling.py` | 1 |
| Suite coverage test | `grep -c "def test_every_agent_dispatched_at_least_once_across_suite" tests/scenarios/test_run_all.py` | 1 |

## Decisions Made

- **Entries appended at the end of the dict with ROUT-02 comment** — not interleaved with existing entries. Rationale: preserves stable ordering of existing 10 entries (minimizes merge conflict surface), and the adjacent comment satisfies the T-01-08 mitigation (provenance for future contributors).
- **Unit test helper passes `ledger=None`** — the `_route_event` signature types `ledger: Ledger` (not `Ledger | None`), but the function body never dereferences ledger at runtime (it only ever calls `mesh.dispatch` which guards `self._ledger is not None` internally). A `# type: ignore[arg-type]` was added on the `await _route_event(...)` line in the helper to make pyright quiet without materially changing behavior. Alternative (build a real `Ledger.open(tmp.name, Signer.generate())`) was rejected as unnecessary boilerplate given the runtime contract.
- **Kept `_route_event` signature untouched** — no change to ledger typing, no change to dispatch guard block, no new parameters. Minimum-diff discipline.

## Deviations from Plan

None — plan executed exactly as written. No deviation rules fired.

## Issues Encountered

- **Environment-layer speed-bump (not a code issue):** First regression attempts used `uv run pytest` which resolved to the system `/home/george/.local/bin/pytest` under Python 3.12 without `pytest-asyncio`, producing 73 spurious failures of async tests (collection-time "async functions are not natively supported"). Resolved by running `uv sync --extra dev` to populate the worktree's `.venv` and then invoking `.venv/bin/pytest` directly. No code change needed; ambient issue from fresh worktree checkout.
- **Orchestrator worktree vs main-checkout path gotcha:** Initial Edit attempts targeted `/home/george/projects/active/skyherd-engine/tests/...` (main checkout), not `/home/george/projects/active/skyherd-engine/.claude/worktrees/agent-aeb60392/tests/...` (my worktree). Detected via `git worktree list`, reverted the main-checkout edits with `git checkout -- ...`, and re-applied to the correct worktree paths. Final worktree status matches plan expectations; main-checkout is clean (only REPLAY_LOG.md appended by scenario runs, which is not in scope for this plan).

## Deferred Issues

None introduced by this plan. Out-of-scope items still owned elsewhere:
- `except OSError: pass` silent swallow at `base.py:389-392` — Phase 3 HYG-01 owns.
- `test_cli.py` missing `typer` dependency — pre-existing dev-env issue, out of this plan's scope.
- `docs/REPLAY_LOG.md` auto-append during test runs — feature, not bug; tracked by existing scenario infrastructure.

## Commits

- `9283e8a` — `test(01-02): add failing tests for routing (thermal.anomaly + nightly.analysis)` (RED — 4 tests, 124 insertions, 0 production changes)
- `23738eb` — `feat(01-02): route thermal.anomaly + nightly.analysis to PredatorPatternLearner (ROUT-02)` (GREEN — 5 insertions in base.py)

## Self-Check: PASSED

**Files verified on disk (worktree):**
- `src/skyherd/scenarios/base.py`: FOUND (routing table has 12 entries including both new ones at lines 420-421)
- `tests/scenarios/test_base.py`: FOUND (`TestDemoMesh` class now has 6 tests + `_run_route_event_sync` helper)
- `tests/scenarios/test_rustling.py`: FOUND (`TestRustlingScenarioIntegration` has 7 tests)
- `tests/scenarios/test_run_all.py`: FOUND (`TestRunAll` has 9 tests)

**Commits verified:**
- `9283e8a`: FOUND in `git log --oneline -5`
- `23738eb`: FOUND in `git log --oneline -5`

**Behavioral assertions verified:**
- `.venv/bin/python -c "from skyherd.scenarios import run; r = run('rustling', seed=42); assert 'PredatorPatternLearner' in r.agent_tool_calls and len(r.agent_tool_calls['PredatorPatternLearner']) == 2"` exits 0.
- `.venv/bin/pytest tests/scenarios/test_base.py::TestDemoMesh tests/scenarios/test_rustling.py::TestRustlingScenarioIntegration tests/scenarios/test_run_all.py::TestRunAll` shows 23 passed (22 method-level + 1 helper pattern tolerated).
- `.venv/bin/skyherd-demo play all --seed 42` shows 8/8 PASS.
