---
phase: 03-code-hygiene-sweep
plan: "03"
subsystem: agents/cost
tags: [cost, testing, coverage, billing, tdd]
dependency_graph:
  requires: []
  provides: [HYG-03, HYG-05]
  affects: [tests/agents/test_cost.py]
tech_stack:
  added: []
  patterns: [callback-injection, monkeypatch-asyncio-sleep, emit_tick-wrapping]
key_files:
  created: []
  modified:
    - tests/agents/test_cost.py
decisions:
  - "Used real asyncio.sleep(0) inside fast_sleep to ensure stop task yields control to event loop — research doc's bare `pass` fast_sleep would have deadlocked the loop (stop_event never set)"
  - "Added `import json` to test file imports (missing from baseline)"
  - "All test assertions on BEHAVIOR (topic string, payload session_id, call counts, property values) — not mere smoke"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-22"
  tasks_completed: 1
  files_modified: 1
---

# Phase 03 Plan 03: cost.py Coverage Uplift Summary

**One-liner:** 4 new test classes exercising MQTT callback, ledger callback, property getters, and loop body via monkeypatched asyncio.sleep — raise cost.py coverage from 78% to 100%.

## Coverage Delta

| Scope | Before | After | Change |
|-------|--------|-------|--------|
| `src/skyherd/agents/cost.py` (file) | 78% (21 missing lines) | **100%** (0 missing) | +22 pp |
| Project-wide (`src/skyherd`) | 87.5% (baseline) | **87.70%** | +0.2 pp |

**Lines that were uncovered and are now covered:**
- `165-170` — `mqtt_publish_callback` invocation branch inside `emit_tick`
- `174-177` — `ledger_callback` invocation branch inside `emit_tick`
- `187` — `active_s` property getter return
- `191` — `idle_s` property getter return
- `205-216` — `run_tick_loop` body (per-ticker emit, idle-pause log, asyncio.sleep)

**No lines remain uncovered.**

## New Test Classes

| Class | Methods | Lines covered |
|-------|---------|---------------|
| `TestMqttPublishCallback` | `test_publish_callback_called_with_topic_and_payload`, `test_publish_callback_failure_swallowed` | 165-170 |
| `TestLedgerCallback` | `test_ledger_callback_called_with_payload`, `test_ledger_callback_failure_swallowed` | 174-177 |
| `TestProperties` | `test_active_s_property`, `test_idle_s_property` | 187, 191 |
| `TestRunTickLoopBody` | `test_loop_ticks_all_tickers`, `test_loop_swallows_ticker_exception` | 205-216 |

Total: **8 new test methods** appended to `tests/agents/test_cost.py`.

## Zero Source Changes Confirmation

Only `tests/agents/test_cost.py` was modified. `src/skyherd/agents/cost.py` is unchanged. Verified via `git diff --name-only HEAD~1 HEAD` — single file: `tests/agents/test_cost.py`.

## Regression Check

- All 1175 existing tests pass (13 skipped, 3 warnings — same as baseline).
- Project-wide coverage gate (`fail_under=80`) passes at 87.70%.
- `cost.py` file gate (`fail_under=90`) passes at 100%.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] fast_sleep must yield to event loop, not just `pass`**
- **Found during:** Task 1, Step 4 (analysis of stop_event task scheduling)
- **Issue:** The research doc's `fast_sleep` used bare `pass`, which returns immediately without yielding the event loop. The `stop_after_few_iters` task (created via `asyncio.create_task`) would never execute because `run_tick_loop` never suspends — it calls the patched `asyncio.sleep` which returns synchronously, never giving the task scheduler a chance to run the stop task. Result: infinite loop.
- **Fix:** `fast_sleep` calls `await real_sleep(0)` where `real_sleep` is a reference to `asyncio.sleep` captured before monkeypatching. This gives a real yield without the 1s delay.
- **Files modified:** `tests/agents/test_cost.py` (tests only)
- **Commit:** d4cc806

**2. [Rule 2 - Missing import] `json` not in baseline imports**
- **Found during:** Task 1, Step 2 (reading existing test file)
- **Fix:** Added `import json` to the import block.
- **Files modified:** `tests/agents/test_cost.py`
- **Commit:** d4cc806

## Known Stubs

None. All tests assert concrete behavior values (topic string, session_id field, call counts, property magnitudes). No stubs or smoke-only tests.

## Threat Flags

None. This plan adds tests only; no new network endpoints, auth paths, or trust boundary crossings introduced.

## Self-Check: PASSED

- [x] `tests/agents/test_cost.py` modified and committed: d4cc806
- [x] `src/skyherd/agents/cost.py` NOT modified (confirmed via git diff)
- [x] 8 new test methods all PASSED individually
- [x] `cost.py` coverage = 100% (gate ≥90% passed)
- [x] Project-wide coverage = 87.70% (gate ≥80% passed)
- [x] 1175 tests pass, 0 regressions
