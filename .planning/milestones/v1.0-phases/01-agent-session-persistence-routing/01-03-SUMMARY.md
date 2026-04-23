---
phase: 01-agent-session-persistence-routing
plan: 03
plan_id: P1-03
subsystem: agents-tests
tags: [tests, managed-agents, checkpoint, idle-pause, test-only, ma-04, ma-05]
requirements: [MA-04, MA-05]
dependency_graph:
  requires:
    - "src/skyherd/agents/cost.py::CostTicker (unchanged — already correct)"
    - "src/skyherd/agents/session.py::SessionManager.checkpoint + restore_from_checkpoint (unchanged)"
    - "src/skyherd/agents/predator_pattern_learner.py::PREDATOR_PATTERN_LEARNER_SPEC (unchanged)"
  provides:
    - "tests/agents/test_cost.py::TestRunTickLoop — 3 new tests pinning MA-04 aggregation contract"
    - "tests/agents/test_session.py::TestCheckpointPersistence — 3 new tests pinning MA-05 checkpoint contract"
  affects:
    - "Phase 5 DASH-03 aggregator refactor: MA-04 tests document the expected all_idle/rate_per_hr_usd formula inline; any drift in server/events.py::_real_cost_tick is flagged"
tech_stack:
  added: []
  patterns:
    - "Inline aggregation formula in test (decoupled from events.py) — contract test pattern"
    - "monkeypatch.setattr(sess_mod, '_RUNTIME_DIR', tmp_path) — mirrors existing test_checkpoint_writes_file pattern"
    - "Pre-register session in fresh SessionManager (mgr2._sessions[id] = session) — matches session.py:284 spec-recovery path"
key_files:
  created:
    - ".planning/phases/01-agent-session-persistence-routing/01-03-SUMMARY.md"
  modified:
    - "tests/agents/test_cost.py"
    - "tests/agents/test_session.py"
decisions:
  - "Inline _aggregate helper in TestRunTickLoop mirrors events.py:347-377 so MA-04 contract is legible without cross-file import; if Phase 5 refactors into a shared helper, tests can be updated to call it"
  - "Kept all 3 MA-05 tests in a new TestCheckpointPersistence class (rather than extending TestSessionLifecycle) for clean grep/discovery and future extension"
  - "Test 1 walks two wake/sleep cycles to simulate a literal sim-day boundary (thermal.clip + nightly.analysis); test 2 is a minimal regression; test 3 pins the on-disk file shape"
metrics:
  duration: "~11 minutes wall (666s)"
  completed: "2026-04-22"
  tasks: 2
  commits: 2
  tests_added: 6
  tests_pass_delta: "+6 new, 0 regressions"
---

# Phase 1 Plan 3: MA-04 + MA-05 Test Pin Summary

Pure test-only plan closing the last two Managed Agents phase requirements: pin the idle-pause cost-ticker aggregation contract (MA-04) and the PredatorPatternLearner checkpoint round-trip across a sim-day boundary (MA-05). Zero production code changes — the underlying behaviors were already correctly implemented; this plan prevents future regressions.

## Task-by-Task Trace

**Task 1 — MA-04 aggregation tests (commit `a154095`)**
- Added `_aggregate(tickers)` helper method inside `TestRunTickLoop` that mirrors `src/skyherd/server/events.py::_real_cost_tick` lines 347-377 (`any_active` → `all_idle` → `rate_per_hr_usd`).
- Added 3 tests:
  - `test_all_sessions_idle_emits_zero_rate` — two idle tickers → `all_idle=True`, `rate_per_hr_usd=0.0`.
  - `test_mixed_active_idle_emits_active_rate` — one idle + one active → `all_idle=False`, `rate=0.08`.
  - `test_single_idle_ticker_emits_zero_rate` — single idle ticker edge case → rate=0.0.
- All 3 tests GREEN immediately (no production change required; CostTicker state machine is already correct).
- `uv run pytest tests/agents/test_cost.py::TestRunTickLoop` → 5 passed (2 existing + 3 new).
- `uv run pytest tests/agents/test_cost.py` → 22 passed.

**Task 2 — MA-05 checkpoint round-trip (commit `667261c`)**
- Added new class `TestCheckpointPersistence` at EOF of `tests/agents/test_session.py`, after `TestOnWebhook`.
- Added 3 tests:
  - `test_predator_pattern_learner_checkpoint_round_trip` — walks two wake/sleep cycles (thermal.clip + nightly.analysis), checkpoints, instantiates fresh `SessionManager`, pre-registers the session for spec resolution (per `session.py:284`), restores from disk, asserts `wake_events_consumed` length is 2, both event types present, `agent_name == "PredatorPatternLearner"`, and `state == "idle"` (per `session.py:304` always-idle-on-restore invariant).
  - `test_checkpoint_preserves_agent_name` — minimal regression guard.
  - `test_checkpoint_file_written_to_runtime_dir` — pins the JSON file path contract.
- All 3 tests use `monkeypatch.setattr(sess_mod, "_RUNTIME_DIR", tmp_path)` to isolate from disk (same pattern as the existing `test_checkpoint_writes_file`).
- All 3 tests GREEN immediately (checkpoint/restore API is already correctly implemented).
- `uv run pytest tests/agents/test_session.py::TestCheckpointPersistence` → 3 passed.
- `uv run pytest tests/agents/test_session.py` → 23 passed.

## Verification Results

All five verification steps pass:

1. **Static checks** — `ruff check tests/agents/test_cost.py tests/agents/test_session.py`: All checks passed.
2. **MA-04 aggregation** — `pytest tests/agents/test_cost.py::TestRunTickLoop -v`: **5 passed** (2 existing + 3 new).
3. **MA-05 checkpoint** — `pytest tests/agents/test_session.py::TestCheckpointPersistence -v`: **3 passed**.
4. **Agents suite zero-regression** — `pytest tests/agents/`: **179 passed** in 10.36s.
5. **Scenario gate (SCEN-02)** — `make demo SEED=42 SCENARIO=all`: **8/8 PASS** (coyote 1.04s, sick_cow 3.75s, water_drop 0.89s, calving 1.19s, storm 1.16s, cross_ranch_coyote 1.08s, wildfire 1.16s, rustling 0.99s).

## Acceptance Criteria Grep Summary

| Criterion | Command | Result |
|-----------|---------|--------|
| `_aggregate` helper + 3 MA-04 tests | `grep -cE "def _aggregate\|def test_all_sessions_idle_emits_zero_rate\|def test_mixed_active_idle_emits_active_rate\|def test_single_idle_ticker_emits_zero_rate" tests/agents/test_cost.py` | 4 lines |
| `TestRunTickLoop` passes 5 tests | `pytest tests/agents/test_cost.py::TestRunTickLoop --tb=no` | `5 passed` |
| `TestCheckpointPersistence` class exists | `grep -cE "class TestCheckpointPersistence" tests/agents/test_session.py` | 1 |
| 3 MA-05 test methods present | `grep -nE "def test_predator_pattern_learner_checkpoint_round_trip\|def test_checkpoint_preserves_agent_name\|def test_checkpoint_file_written_to_runtime_dir" tests/agents/test_session.py` | 3 lines (193, 271, 291) |
| `PREDATOR_PATTERN_LEARNER_SPEC` referenced | `grep -cE "PREDATOR_PATTERN_LEARNER_SPEC" tests/agents/test_session.py` | 6 (3 imports + 3 uses across the 3 tests) |
| `TestCheckpointPersistence` passes 3 tests | `pytest tests/agents/test_session.py::TestCheckpointPersistence --tb=no` | `3 passed` |
| Full test_session.py passes | `pytest tests/agents/test_session.py --tb=no` | `23 passed` |
| Full agents suite passes | `pytest tests/agents/ --tb=no` | `179 passed` |
| All 8 scenarios pass | `make demo SEED=42 SCENARIO=all` | `Results: 8/8 passed` |
| **Zero production code changes** | `git diff --stat HEAD~2..HEAD -- src/` | empty (no src files touched) |

## Deviations from Plan

None — plan executed exactly as written.

## Deferred Issues

None introduced by this plan. Pre-existing issues out of scope and still open:
- `server/events.py:353` `_tickers` lookup bug (RESEARCH.md Pitfall 6) — Phase 5 DASH-03 owns it; the MA-04 aggregation test documents the **expected** contract that Phase 5's refactor must preserve.
- Plan 02's parallel scenario-test changes on `tests/scenarios/test_base.py` / `test_run_all.py` / `test_rustling.py` are WIP in another worktree — not part of this plan.

## Commits

- `a154095` — `test(01-03): add MA-04 multi-ticker all-idle aggregation tests`
- `667261c` — `test(01-03): add MA-05 PredatorPatternLearner checkpoint round-trip`

## Self-Check: PASSED

**Files verified on disk:**
- `tests/agents/test_cost.py`: FOUND (with `_aggregate` helper + 3 MA-04 methods inside `TestRunTickLoop`)
- `tests/agents/test_session.py`: FOUND (with `TestCheckpointPersistence` class + 3 methods)

**Commits verified:**
- `a154095`: FOUND in `git log --oneline`
- `667261c`: FOUND in `git log --oneline`

**Behavioral assertions verified:**
- `uv run pytest tests/agents/test_cost.py::TestRunTickLoop --tb=no` shows 5 passed.
- `uv run pytest tests/agents/test_session.py::TestCheckpointPersistence --tb=no` shows 3 passed.
- `uv run pytest tests/agents/ --tb=no` shows 179 passed, 0 failures.
- `make demo SEED=42 SCENARIO=all` shows Results: 8/8 passed.
- `git diff --stat HEAD~2..HEAD -- src/` is empty (no production source changes).
