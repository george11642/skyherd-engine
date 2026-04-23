---
phase: 06-sitl-ci-determinism-gate
plan: 01
subsystem: tests
tags: [determinism, pytest, hashing, test-hardening, SCEN-03]
requires: []
provides:
  - tests/test_determinism_e2e.py::test_demo_seed42_is_deterministic_3x
affects:
  - tests/test_determinism_e2e.py
tech-stack:
  added: []
  patterns:
    - "In-body `for` loop over range(3) for cross-run hash identity (not @pytest.mark.parametrize)"
    - "Reuse of existing sanitize/md5/run helpers — zero re-invention"
key-files:
  created: []
  modified:
    - tests/test_determinism_e2e.py
decisions:
  - "In-body loop vs parametrize: parametrize produces independent test IDs that cannot cross-assert siblings; loop keeps all 3 hashes in one scope and fails with all three printed."
  - "Preserve _run_demo / _sanitize / _md5 / DETERMINISM_SANITIZE byte-identical — Plan 01 owns only the test function, not helper semantics."
metrics:
  duration: "~5 min"
  completed: "2026-04-22"
  tasks: 1
  files_modified: 1
---

# Phase 06 Plan 01: Determinism 3-Run Hardening Summary

Replaced the 2-run determinism check with a 3-run in-body-loop variant that cross-asserts byte-identical MD5 hashes across three back-to-back `seed=42` scenario playbacks — closing SCEN-03.

## What Changed

- `tests/test_determinism_e2e.py`
  - Module docstring updated: "two seed=42 runs" → "three back-to-back seed=42 runs", plus explicit SCEN-03 callout and expanded sanitization list (timestamps, UUIDs, ISO dates, session hashes).
  - Removed: `test_demo_seed42_is_deterministic` (2-run variant).
  - Added: `test_demo_seed42_is_deterministic_3x` — `@pytest.mark.slow`, iterates `for run_idx in range(3)`, collects 3 sanitized MD5s into `hashes: list[str]`, asserts `len(set(hashes)) == 1` with all three hashes printed on failure for debuggability.
  - Helpers (`DETERMINISM_SANITIZE`, `_sanitize`, `_md5`, `_run_demo`) preserved byte-identical.

## Why an In-Body Loop, Not Parametrize

`@pytest.mark.parametrize("run_idx", range(3))` would create three independent test IDs that each run once and cannot see siblings' outputs. The semantic of SCEN-03 is cross-run identity — that requires one test that holds all three sanitized hashes in a single scope.

## Verification

Collection confirms exactly one test item:
```
tests/test_determinism_e2e.py::test_demo_seed42_is_deterministic_3x
```

Guard greps:
- `grep -c "def test_demo_seed42_is_deterministic_3x"` → 1
- `grep -cE "def test_demo_seed42_is_deterministic($|[^_])"` → 0 (old gone)
- `grep -c "for run_idx in range(3)"` → 1
- `grep -c "pytest.mark.parametrize"` → 0 (anti-pattern avoided)
- `grep -c "DETERMINISM_SANITIZE"` → 3 (definition + 2 reference sites)

Test execution: `uv run pytest tests/test_determinism_e2e.py -v -m slow` → 1 passed.

## Deviations from Plan

None — plan executed exactly as written.

## Commits

- `3cafa65` — `test(06-01): strengthen determinism check to 3-run in-body loop (SCEN-03)`

## Self-Check: PASSED

- File exists: `tests/test_determinism_e2e.py` — FOUND
- Commit exists: `3cafa65` — FOUND
- Test collected and passing under `uv run pytest -m slow`
- Success criteria met: single `_3x` test, in-body loop, helpers byte-identical, zero parametrize usage
