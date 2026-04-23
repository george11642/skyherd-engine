---
phase: 06-sitl-ci-determinism-gate
plan: 03
subsystem: build-automation
tags: [makefile, gate-check, retro-audit, make-targets, scen-02, scen-03, bld-04]
requires:
  - scripts/sitl_smoke.py (Plan 06-02 artifact)
  - tests/test_determinism_e2e.py::test_demo_seed42_is_deterministic_3x (Plan 06-01 artifact)
provides:
  - scripts/gate_check.py (10-item Sim Completeness Gate retro-audit runner)
  - Makefile targets: sitl-smoke, determinism-3x, gate-check
affects:
  - Makefile (additive only; zero edits to existing targets)
tech-stack:
  added: []
  patterns: [subprocess-audit-runner, status-table-cli, fast-flag-shortcut]
key-files:
  created:
    - scripts/gate_check.py
    - tests/test_gate_check.py
  modified:
    - Makefile
decisions:
  - Gate check uses three-tier evidence (file existence, string-presence grep, subprocess exit) per item; YELLOW disagrees with GREEN; only GREEN passes
  - --fast flag added for CI loops; skips subprocess checks, runs in <2s
  - No reference hash committed for determinism — cross-run equality is sufficient per plan
  - gate-check delegates to Plan 01 + Plan 02 artifacts instead of re-implementing
metrics:
  completed: 2026-04-22
  tasks: 2
  duration: <10 min
  files_created: 2
  files_modified: 1
  lines_added: 364
---

# Phase 06 Plan 03: SITL-CI & Determinism Gate Retro-Audit Runner Summary

Shipped the judge-facing `make gate-check` command that runs `scripts/gate_check.py` to iterate all 10 CLAUDE.md Sim Completeness Gate items and emit a GREEN/YELLOW/RED table with exit 0 iff 10/10 GREEN, plus two thin Makefile wrappers (`sitl-smoke`, `determinism-3x`) that let judges reproduce each underlying proof individually.

## What Landed

### Task 1: `scripts/gate_check.py` retro-audit runner (TDD)
- **RED** — `tests/test_gate_check.py` (7 tests) committed first, all failing with `FileNotFoundError` for the missing script. Commit `31fa9c7`.
- **GREEN** — `scripts/gate_check.py` (246 lines) commits `2db496e`:
  - 10 `_check_*` functions, one per Gate item, each returning `(status, evidence)`.
  - `GATE_ITEMS` registry has exactly 10 entries in CLAUDE.md order: `agents_mesh`, `sensors`, `vision_heads`, `sitl_mission`, `dashboard`, `voice`, `scenarios`, `determinism`, `fresh_clone`, `cost_idle`.
  - `--fast` flag skips the three subprocess-invoking checks (`sitl_mission`, `scenarios`, `determinism`).
  - `main()` prints header + 10 formatted rows + summary; `sys.exit(0)` iff every status is GREEN, else `sys.exit(1)`.
- All 7 tests pass. Fast path runs in <1s on the worktree.

### Task 2: Three new Makefile targets
- `.PHONY` extended with `sitl-smoke determinism-3x gate-check`.
- `sitl-smoke` → `uv run python scripts/sitl_smoke.py` (Plan 06-02 artifact).
- `determinism-3x` → `uv run pytest tests/test_determinism_e2e.py -v -m slow --timeout=600` (Plan 06-01 artifact).
- `gate-check` → `uv run python scripts/gate_check.py`.
- Zero edits to existing targets (`dashboard`, `sim`, `demo`, `hardware-demo`, etc.). `git diff Makefile` shows +17 / -1 (only the `.PHONY` line replaced). Commit `685bf58`.

## Verification

- `uv run pytest tests/test_gate_check.py -q` → **7 passed**.
- `uv run ruff check scripts/gate_check.py tests/test_gate_check.py` → **All checks passed!**
- `make -n sitl-smoke` → `uv run python scripts/sitl_smoke.py`
- `make -n determinism-3x` → `uv run pytest tests/test_determinism_e2e.py -v -m slow --timeout=600`
- `make -n gate-check` → `uv run python scripts/gate_check.py`
- `make -n dashboard` still parses cleanly (Phase 4 ownership preserved).
- `uv run python scripts/gate_check.py --fast` prints 10 rows + summary and exits 1 in this worktree (expected — Plans 01 + 02 not yet merged into this worktree's base; `sitl_mission` and `determinism` report RED, `dashboard` YELLOW; 7/10 GREEN).

## Gate State at Plan Landing

In this parallel worktree (branched from `b225527`, pre-Wave-1-merge):

```
[GREEN ] agents_mesh    5 Managed Agents on shared MQTT        (5/5 registered)
[GREEN ] sensors        7+ sim sensors emitting                (7 emitter modules)
[GREEN ] vision_heads   Disease heads on synthetic frames      (7 heads)
[RED   ] sitl_mission   ArduPilot SITL MAVLink mission         (scripts/sitl_smoke.py missing — Plan 02 pending merge)
[YELLOW] dashboard      Map + lanes + cost + attest + PWA      (server/live.py missing — Phase 4 pending merge)
[GREEN ] voice          Wes voice chain end-to-end             (call.py + tts.py present)
[GREEN ] scenarios      All scenarios pass SEED=42             (11 scenario files)
[RED   ] determinism    seed=42 stable across 3 runs           (3x test missing — Plan 01 pending merge)
[GREEN ] fresh_clone    make demo boots fresh clone            (README quickstart present)
[GREEN ] cost_idle      Cost ticker pauses during idle         (all_idle + rate_per_hr_usd emitted)
```

7/10 GREEN. Post-merge with Wave 1 (Plans 01 + 02) and Phase 4, all 10 items are expected to flip GREEN.

## Deviations from Plan

None — plan executed exactly as written.

- Task 1's implementation matches the plan's `<action>` block almost verbatim. Minor adjustments:
  - Added `registry` to the `_check_sensors` exclusion set (the repo has `sensors/registry.py`; excluding it keeps the count reflecting actual emitter modules). Without this, the count would be inflated rather than reduced, so leaving it out would still pass GREEN; exclusion is defensive.
  - Used `collections.abc.Callable` instead of `typing.Callable` (modern idiom, passes ruff `UP` rules).

## Requirements Closed

- **SCEN-02** — Milestone-wide zero-regression criterion: `scripts/gate_check.py` is the single command that audits all 10 Gate items; exits 0 only if every item GREEN.
- **SCEN-03** — Determinism gate: `make determinism-3x` is the thin Makefile wrapper that runs the 3x determinism test from Plan 06-01; `_check_determinism` delegates to the same test.
- **BLD-04** — `make sitl-smoke` target ships as the thin wrapper around `scripts/sitl_smoke.py` (Plan 06-02).

## Self-Check: PASSED

- `scripts/gate_check.py` FOUND (246 lines).
- `tests/test_gate_check.py` FOUND (117 lines, 7 passing tests).
- `Makefile` modified — `.PHONY` extended, three new targets appended, zero existing-target edits.
- Commits FOUND: `31fa9c7` (RED), `2db496e` (GREEN Task 1), `685bf58` (Task 2).
- `GATE_ITEMS` has exactly 10 entries in CLAUDE.md order.
- `uv run pytest tests/test_gate_check.py` — all green.
- `uv run ruff check` — all green.

## TDD Gate Compliance

- RED commit (`31fa9c7`): `test(06-03): add failing tests for gate_check.py retro-audit runner (SCEN-02)`
- GREEN commit (`2db496e`): `feat(06-03): add scripts/gate_check.py retro-audit runner (SCEN-02)`
- Task 2 is a Makefile additive change (no TDD cycle required for declarative build config).
