---
phase: 01-agent-session-persistence-routing
verified: 2026-04-22T22:00:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 8/9
  gaps_closed:
    - "uv run pyright src/skyherd/agents/managed.py src/skyherd/agents/session.py exits with zero errors"
  gaps_remaining: []
  regressions: []
---

# Phase 1: Agent Session Persistence & Routing — Verification Report

**Phase Goal:** Each of the 5 agents runs on ONE long-lived Managed Agents session reused across all events in a scenario run, and every agent (including PredatorPatternLearner) is actually dispatched by the routing table.
**Verified:** 2026-04-22T22:00:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (commit 9322bb2)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 (SC-1) | Coyote scenario creates at most 5 platform sessions | VERIFIED | `test_creates_at_most_five_sessions` PASSES: count["n"]=1 after run; monkeypatch on `SessionManager.__init__` confirms single instantiation. Pre-fix baseline was 241. |
| 2 (SC-2) | Rustling scenario dispatches PredatorPatternLearner verified by AgentDispatched counter | VERIFIED | `test_predator_pattern_learner_dispatched` PASSES: `result.agent_tool_calls["PredatorPatternLearner"]` contains 2 tool calls (`get_thermal_history`, `log_pattern_analysis`) |
| 3 (SC-3) | All 5 agents dispatched >= 1 time across the scenario suite | VERIFIED | `test_every_agent_dispatched_at_least_once_across_suite` PASSES: union of keys across 8 scenarios = {CalvingWatch, FenceLineDispatcher, GrazingOptimizer, HerdHealthWatcher, PredatorPatternLearner} |
| 4 (SC-4) | SSE stream emits rate_per_hr_usd=0.0 and all_idle=True when all sessions idle | VERIFIED | `TestRunTickLoop::test_all_sessions_idle_emits_zero_rate` PASSES; `test_single_idle_ticker_emits_zero_rate` PASSES; aggregation logic confirmed correct |
| 5 (SC-5) | PredatorPatternLearner retains context across sim-day boundaries (checkpoint persistence) | VERIFIED | `TestCheckpointPersistence::test_predator_pattern_learner_checkpoint_round_trip` PASSES: two wake events survive checkpoint/restore into fresh SessionManager; wake_events_consumed length=2 preserved |
| 6 (SC-6) | uv run pyright src/skyherd/agents/managed.py src/skyherd/agents/session.py exits with zero errors | VERIFIED | `0 errors, 0 warnings, 0 informations` — commit 9322bb2 added pyright suppression on managed.py:388 (AsyncStream SDK type mismatch) and explicit cast + kwarg annotations in session.py get_session_manager(). Exit code 0 confirmed. |
| 7 (SCEN-02) | All 8 scenarios PASS make demo SEED=42 SCENARIO=all | VERIFIED | 8/8 PASS: coyote, sick_cow, water_drop, calving, storm, cross_ranch_coyote, wildfire, rustling all PASS (0.23s–1.04s wall). No regressions introduced by 9322bb2. |
| 8 (MA-04 + MA-05 detail) | Cost ticker and checkpoint round-trip tests pass | VERIFIED | 325 passed, 2 skipped — zero failures across tests/agents/ + tests/scenarios/ |
| 9 (ROUT detail) | PredatorPatternLearner in routing table for thermal.anomaly and nightly.analysis | VERIFIED | base.py lines 420-421 confirmed present; `test_routing_table_thermal_anomaly` and `test_routing_table_nightly_analysis` PASS |

**Score:** 9/9 truths verified

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| MA-01 | Each of 5 agents on ONE long-lived session per scenario run | VERIFIED | `_DemoMesh.__init__` creates 1 `SessionManager` + 5 `Session` objects eagerly; `dispatch()` reuses existing sessions. Confirmed by session count test (count=1). |
| MA-02 | `_DemoMesh` holds session registry keyed by agent name | VERIFIED | `_sessions: dict[str, Session]` on `_DemoMesh`; `agent_sessions()` public accessor returns it. Test `test_demo_mesh_holds_five_sessions_keyed_by_name` PASSES. |
| MA-03 | Coyote scenario creates <= 5 platform sessions (not 241) | VERIFIED | `test_creates_at_most_five_sessions` PASSES: count=1 observed. |
| MA-04 | Cost ticker emits rate_per_hr_usd=0.0 + all_idle=True when idle | VERIFIED | Three `TestRunTickLoop` MA-04 tests PASS; aggregation logic documented inline and confirmed correct. |
| MA-05 | PredatorPatternLearner retains context across sim-day boundaries | VERIFIED | `TestCheckpointPersistence` 3 tests PASS; round-trip preserves wake_events_consumed, agent_name, and state. |
| ROUT-01 | PredatorPatternLearner in `_registry` dict | VERIFIED | `base.py` line 316: `"PredatorPatternLearner": (PREDATOR_PATTERN_LEARNER_SPEC, predator_handler)` present in `_registry`. Also in `_sessions` via `_SCENARIO_AGENT_REGISTRY`. Test `test_registry_includes_predator_pattern_learner` PASSES. |
| ROUT-02 | Routing table includes thermal.anomaly -> [FenceLineDispatcher, PredatorPatternLearner] and nightly.analysis -> [PredatorPatternLearner] | VERIFIED | `base.py` lines 420-421 confirmed present. `test_routing_table_thermal_anomaly` and `test_routing_table_nightly_analysis` PASS. |
| ROUT-03 | Rustling scenario asserts PredatorPatternLearner dispatched (not event-presence) | VERIFIED | `test_predator_pattern_learner_dispatched` checks `result.agent_tool_calls["PredatorPatternLearner"]` — tool-call count assertion, not just event presence. PASSES. |
| ROUT-04 | All 5 agents dispatched >= 1 time across 8 scenarios | VERIFIED | `test_every_agent_dispatched_at_least_once_across_suite` PASSES. |
| SC-6 (Pyright) | `managed.py` + `session.py` exit pyright clean (0 errors) | VERIFIED | `uv run pyright src/skyherd/agents/managed.py src/skyherd/agents/session.py` → `0 errors, 0 warnings, 0 informations`. Commit 9322bb2 closed this gap. |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/skyherd/scenarios/base.py` | `_DemoMesh` with session registry + routing table entries | VERIFIED | `_DemoMesh` class lines 183-284; `_sessions` dict; `agent_sessions()`/`agent_tickers()` accessors; routing dict lines 406-422 with 12 entries including thermal.anomaly + nightly.analysis |
| `src/skyherd/agents/managed.py` | pyright-clean (0 errors) | VERIFIED | Commit 9322bb2: pyright suppression on line 388 AsyncStream context manager; `0 errors, 0 warnings, 0 informations` |
| `src/skyherd/agents/session.py` | pyright-clean (0 errors) | VERIFIED | Commit 9322bb2: explicit cast + kwarg type annotations in get_session_manager(); `0 errors, 0 warnings, 0 informations` |
| `tests/scenarios/test_base.py` | `TestDemoMesh` with 6 methods + `_run_route_event_sync` helper | VERIFIED | Lines 163-304; 6 test methods + helper present |
| `tests/scenarios/test_coyote.py` | `test_creates_at_most_five_sessions` | VERIFIED | Lines 96-115 |
| `tests/scenarios/test_rustling.py` | `test_predator_pattern_learner_dispatched` | VERIFIED | Lines 172-186 |
| `tests/scenarios/test_run_all.py` | `test_every_agent_dispatched_at_least_once_across_suite` | VERIFIED | Lines 58-75 |
| `tests/agents/test_cost.py` | `TestRunTickLoop` MA-04 tests (3 new methods + `_aggregate` helper) | VERIFIED | Lines 145-201; all 3 MA-04 tests present and passing |
| `tests/agents/test_session.py` | `TestCheckpointPersistence` class with 3 MA-05 tests | VERIFIED | Lines 184-end; class and 3 test methods present and passing |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_DemoMesh.dispatch()` | existing `Session` | `self._sessions[agent_name]` lookup | VERIFIED | No `SessionManager()` constructed per-dispatch; session reused from `__init__`-time registry |
| `_route_event` routing dict | `PredatorPatternLearner` via `mesh.dispatch()` | `thermal.anomaly` -> `[FenceLineDispatcher, PredatorPatternLearner]` | VERIFIED | `test_routing_table_thermal_anomaly` confirms both agents appear in `mesh._tool_call_log` after routing |
| `_route_event` routing dict | `PredatorPatternLearner` via `mesh.dispatch()` | `nightly.analysis` -> `[PredatorPatternLearner]` | VERIFIED | `test_routing_table_nightly_analysis` confirms only learner appears |
| `SessionManager.checkpoint()` | disk JSON | `tmp_path/_RUNTIME_DIR` monkeypatch | VERIFIED | `TestCheckpointPersistence` confirms file written and restored correctly |
| `_DemoMesh.dispatch()` finally block | `SessionManager.sleep()` | `try/finally` guarantee | VERIFIED | `dispatch()` lines 264-271: `finally: self._session_manager.sleep(session.id)` — fires even on handler exception |

---

### Data-Flow Trace (Level 4)

Not applicable — all Phase 1 artifacts are session management and routing infrastructure (no dynamic data rendering). The cost ticker aggregation contract is verified via unit tests rather than end-to-end data flow.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Pyright clean on managed.py + session.py | `uv run pyright src/skyherd/agents/managed.py src/skyherd/agents/session.py` | 0 errors, 0 warnings, 0 informations | PASS |
| All agent + scenario tests pass | `uv run pytest tests/agents/ tests/scenarios/ -x -q` | 325 passed, 2 skipped | PASS |
| All 8 scenarios PASS SEED=42 | `.venv/bin/skyherd-demo play all --seed 42` | 8/8 PASS (coyote, sick_cow, water_drop, calving, storm, cross_ranch_coyote, wildfire, rustling) | PASS |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `src/skyherd/scenarios/base.py:391` | `except OSError: pass` (silent) | Info | Explicitly reserved for Phase 3 HYG-01; documented in all 3 plan summaries as out-of-scope |
| `src/skyherd/scenarios/base.py:266` | `except Exception as exc: # noqa: BLE001` | Info | Intentional broad catch in dispatch() — logs the error and falls back to empty calls; not silent |

No blockers. The two Info-level items are Phase 3 HYG-01 scope; they do not affect Phase 1's goal.

---

### Human Verification Required

None — all Phase 1 success criteria are programmatically verifiable (session counts, dispatch counters, routing assertions, checkpoint round-trip, cost ticker state, pyright exit code). No UI, real-time behavior, or external service integration in scope for this phase.

---

### Gap Closure Summary

**Gap closed:** SC-6 pyright handoff (was 6 errors in managed.py + session.py).

Commit `9322bb2` applied two targeted fixes:
- `managed.py:388` — added pyright suppression comment on the `async with stream_session(...)` line. The Anthropic SDK's type signature declares `stream_session` as returning a `Coroutine`, but the runtime object is an async context manager. The suppression is documented with rationale inline.
- `session.py:415, 422` — `get_session_manager()` factory now casts `ManagedSessionManager` returns to `SessionManager` (duck-typed siblings sharing identical public API), and `agent_ids_path` kwarg is explicitly annotated `str`. Both errors and both `Unknown | None` issues resolved without altering runtime behavior.

Result: `0 errors, 0 warnings, 0 informations`. Exit code 0.

All other 9 requirements (MA-01 through MA-05, ROUT-01 through ROUT-04) remain green. Zero regressions — 325 tests pass, 8/8 scenarios PASS.

---

*Verified: 2026-04-22T22:00:00Z*
*Verifier: Claude (gsd-verifier)*
