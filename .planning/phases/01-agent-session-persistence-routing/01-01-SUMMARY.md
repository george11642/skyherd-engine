---
phase: 01-agent-session-persistence-routing
plan: 01
plan_id: P1-01
subsystem: agents-scenarios
tags: [session-persistence, managed-agents, refactor, tdd, routing]
requirements: [MA-01, MA-02, MA-03, ROUT-01]
dependency_graph:
  requires:
    - "src/skyherd/agents/mesh.py::AgentMesh (template — unchanged)"
    - "src/skyherd/agents/session.py::SessionManager, Session (unchanged)"
    - "src/skyherd/agents/*_SPEC + handler exports (unchanged)"
  provides:
    - "src/skyherd/scenarios/base.py::_DemoMesh with persistent session registry"
    - "_DemoMesh.agent_sessions() public accessor (Phase 5 API)"
    - "_DemoMesh.agent_tickers() public accessor (Phase 5 API)"
    - "_SCENARIO_AGENT_REGISTRY module-level constant"
  affects:
    - "src/skyherd/scenarios/base.py::_run_async _registry dict (now includes PredatorPatternLearner)"
tech_stack:
  added: []
  patterns:
    - "Mirrored AgentMesh.start() eager session creation pattern in _DemoMesh.__init__"
    - "try/finally guaranteed sleep() matches AgentMesh._run_handler"
    - "Module-level canonical agent registry mirrors mesh.py::_AGENT_REGISTRY"
key_files:
  created: []
  modified:
    - "src/skyherd/scenarios/base.py"
    - "tests/scenarios/test_base.py"
    - "tests/scenarios/test_coyote.py"
decisions:
  - "Eager session creation (5x at __init__) chosen over lazy — matches AgentMesh, create_session is microseconds"
  - "Kept spec/handler_fn parameters in dispatch() for _route_event API compat (unused; handler resolved via self._handlers registry)"
  - "agent_sessions() returns shallow copy via dict(self._sessions) to prevent callers mutating the registry keys"
metrics:
  duration: "~10 minutes wall"
  completed: "2026-04-22"
  tasks: 2
  commits: 2
  tests_added: 5
  tests_pass_delta: "+5 new, 0 regressions"
---

# Phase 1 Plan 1: Agent Session Persistence Refactor Summary

Closes the 241-sessions-per-coyote-scenario leak by making `_DemoMesh` hold one `SessionManager` and five persistent `Session` objects reused across all dispatches — mirrors the proven `AgentMesh` pattern and exposes stable accessors for Phase 5 dashboard consumption.

## Final Session Count (from verification run)

```
SessionManager instances during coyote run (post-fix): 1
Pre-fix baseline: 241
Target: <= 5
Result: 1 (exceeds target — single manager eagerly creates 5 sessions at __init__)
```

The single `SessionManager` instance manages all 5 `Session` objects. Before the refactor, `_DemoMesh.dispatch()` imported `SessionManager` locally and constructed a fresh one on every call — 241 in a full coyote run. The fix eliminates that per-dispatch allocation entirely.

## Registered Agents (Session IDs)

From `_DemoMesh(ledger=None).agent_sessions()`:

| Agent | Session ID (first 8) |
|-------|----------------------|
| FenceLineDispatcher | `dbf391d0` |
| HerdHealthWatcher | `aa9ae22b` |
| PredatorPatternLearner | `f5948fcb` |
| GrazingOptimizer | `d9f78e6a` |
| CalvingWatch | `de2cdc48` |

All five start in `state == "idle"` immediately after `__init__` returns. `PredatorPatternLearner` is registered (ROUT-01 satisfied) — it will be fully wake-routable after Plan 02 adds `thermal.anomaly` and `nightly.analysis` to the routing table.

## Phase 5 API Exposed

Both accessors exist and are callable from outside the class (no private-attribute reach-through required):

```python
>>> m = _DemoMesh(ledger=None)
>>> len(m.agent_sessions()), len(m.agent_tickers())
(5, 5)
```

- `agent_sessions()` returns `dict[str, Session]` (shallow copy — callers cannot mutate the registry).
- `agent_tickers()` returns `list[CostTicker]` by delegating to `self._session_manager.all_tickers()`.

Phase 5 DASH-03 cost-tick aggregator can now iterate tickers without reaching through `_mesh._session_manager._tickers` (the bug documented in RESEARCH.md Pitfall 6, which this phase explicitly does NOT fix).

## Task-by-Task Trace

**Task 1 — RED (commit `896d117`)**
- Added `TestDemoMesh` class in `tests/scenarios/test_base.py` with 4 tests: registry shape, PredatorPatternLearner presence, `agent_sessions()` accessor, `agent_tickers()` accessor.
- Added `test_creates_at_most_five_sessions` in `tests/scenarios/test_coyote.py::TestCoyoteScenario` using `monkeypatch.setattr` on `SessionManager.__init__`.
- All 5 tests fail as expected. Coyote counter shows `241 SessionManager instances` in failure output — confirms instrumentation works against the pre-fix code.
- Zero production code touched.

**Task 2 — GREEN (commit `4f1fff2`)**
- Lifted agent-spec imports to module top of `src/skyherd/scenarios/base.py`, mirroring `mesh.py`.
- Added `_SCENARIO_AGENT_REGISTRY` constant (5-tuple list in canonical order).
- Replaced `_DemoMesh.__init__` body: one `SessionManager`, loop over `_SCENARIO_AGENT_REGISTRY` creating five `Session` objects, stored in `self._sessions` + `self._handlers` dicts keyed by name.
- Added public accessors `agent_sessions()` and `agent_tickers()`.
- Replaced `dispatch()` body: lookup `self._sessions[agent_name]`, `self._session_manager.wake(...)`, await handler inside `try`, `self._session_manager.sleep(...)` in `finally` block guaranteeing idle-pause.
- Added `PredatorPatternLearner` entry to the `_registry` dict in `_run_async`.
- Dropped the local spec imports inside `_run_async` (now module-level).
- Left `except OSError: pass` (line 391) untouched — Phase 3 HYG-01 reservation.
- Left the routing table at lines 406-417 untouched — Plan 02 reservation.

## Verification Results

All five verification steps pass:

1. **Static checks** — `ruff check src/skyherd/scenarios/base.py tests/scenarios/`: All checks passed. `pyright src/skyherd/scenarios/base.py`: 0 errors, 0 warnings, 0 informations.
2. **Unit + integration** — `pytest tests/scenarios/test_base.py::TestDemoMesh`: 4 passed. `pytest tests/scenarios/test_coyote.py`: 12 passed (11 existing + 1 new). `pytest tests/scenarios/ tests/agents/test_session.py tests/agents/test_cost.py`: 181 passed, 2 skipped.
3. **Scenario suite (SCEN-02 zero-regression)** — `make demo SEED=42 SCENARIO=all`: 8/8 PASS (coyote 0.95s, sick_cow 2.91s, water_drop 0.74s, calving 0.94s, storm 0.88s, cross_ranch_coyote 0.99s, wildfire 0.99s, rustling 0.91s).
4. **Phase 5 API smoke** — `python3 -c "from skyherd.scenarios.base import _DemoMesh; ... print(5 5)"`: exit 0.
5. **Leak regression** — coyote observed `SessionManager instances = 1` (below the `<= 5` target; tool calls unchanged at 244; events unchanged at 131).

## Acceptance Criteria Grep Summary

| Criterion | Command | Result |
|-----------|---------|--------|
| Exactly one `_DemoMesh` class | `grep -cE "class _DemoMesh" src/skyherd/scenarios/base.py` | 1 |
| Both public accessors | `grep -cE "def agent_sessions\|def agent_tickers" src/skyherd/scenarios/base.py` | 2 |
| Exactly one `SessionManager(` in init | `grep -cE "self\._session_manager\s*=\s*SessionManager\(" src/skyherd/scenarios/base.py` | 1 |
| No stray `SessionManager()` elsewhere | `grep -cE "SessionManager\(\)" src/skyherd/scenarios/base.py` | **1** (line 201 only) |
| `_SCENARIO_AGENT_REGISTRY` defined + used | `grep -cE "_SCENARIO_AGENT_REGISTRY" src/skyherd/scenarios/base.py` | 2 |
| `PREDATOR_PATTERN_LEARNER_SPEC` present | `grep -cE "PREDATOR_PATTERN_LEARNER_SPEC" src/skyherd/scenarios/base.py` | 3 (import + constant + _registry) |
| `PredatorPatternLearner` in `_registry` | registry at line 316 | present |
| `finally:` in `dispatch` | guarded sleep() | present |
| OSError reservation untouched | line 391-392 `except OSError: pass` | unchanged |
| Routing table reservation untouched | lines 406-417 | unchanged (10 entries, no `thermal.anomaly`/`nightly.analysis` — Plan 02 owns those) |

## Deviations from Plan

None — plan executed exactly as written.

## Deferred Issues

None introduced by this plan. Pre-existing known issues out of scope and still open:
- `server/events.py:353` `_tickers` lookup bug (RESEARCH.md Pitfall 6) — Phase 5 DASH-03 owns it; `agent_tickers()` accessor added in this plan is the replacement path.
- Routing table missing `thermal.anomaly` and `nightly.analysis` — Plan 02 owns.
- `except OSError: pass` silent swallow at line 391 — Phase 3 HYG-01 owns.

## Commits

- `896d117` — `test(01-01): add failing tests for _DemoMesh session registry + coyote leak guard`
- `4f1fff2` — `refactor(01-01): _DemoMesh session registry + eager 5-agent creation (MA-01, MA-02, MA-03, ROUT-01)`

## Self-Check: PASSED

**Files verified on disk:**
- `src/skyherd/scenarios/base.py`: FOUND
- `tests/scenarios/test_base.py`: FOUND (with `TestDemoMesh` class)
- `tests/scenarios/test_coyote.py`: FOUND (with `test_creates_at_most_five_sessions`)

**Commits verified:**
- `896d117`: FOUND in `git log --oneline`
- `4f1fff2`: FOUND in `git log --oneline`

**Behavioral assertions verified:**
- `uv run python3 -c "from skyherd.scenarios.base import _DemoMesh; m=_DemoMesh(ledger=None); assert len(m.agent_sessions())==5 and len(m.agent_tickers())==5"` exits 0.
- `uv run pytest tests/scenarios/test_base.py::TestDemoMesh tests/scenarios/test_coyote.py::TestCoyoteScenario::test_creates_at_most_five_sessions` shows 5 passed.
- `make demo SEED=42 SCENARIO=all` shows 8/8 PASS.
