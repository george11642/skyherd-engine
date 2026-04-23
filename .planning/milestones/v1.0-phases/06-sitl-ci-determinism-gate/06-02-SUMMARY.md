---
phase: 06-sitl-ci-determinism-gate
plan: 02
subsystem: ci/sitl
tags: [ci, sitl, mavlink, emulator, github-actions, bld-04]
dependency_graph:
  requires: [existing-sitl-e2e-job, skyherd-sitl-e2e-cli, MavlinkSitlEmulator]
  provides: [sitl-smoke-job, scripts/sitl_smoke.py, failure-path-test]
  affects: [.github/workflows/ci.yml]
tech_stack:
  added: []
  patterns: [evidence-event-verification, loud-failure-discipline, skip-guard-opt-in]
key_files:
  created:
    - scripts/sitl_smoke.py
    - tests/drone/test_sitl_smoke_failure.py
  modified:
    - .github/workflows/ci.yml
decisions:
  - "Removed workflow_dispatch guard on sitl-e2e job, renamed to sitl-smoke — BLD-04 now runs on every push + PR"
  - "Wrapper script asserts 5 evidence events (CONNECTED/TAKEOFF OK/PATROL OK/RTL OK/E2E PASS) — spoofing a PASS requires editing real source"
  - "Failure-path test uses emulator=False + self-managed MavlinkSitlEmulator on port offset 9 — no collision with happy-path tests (offsets 0..5)"
  - "Dropped @pytest.mark.timeout(90) marker — pytest-timeout plugin is not installed in this project and the marker produced an unknown-mark warning"
metrics:
  duration: "~15 minutes"
  tasks_completed: 3
  files_created: 2
  files_modified: 1
  commits: 3
completed: 2026-04-22
---

# Phase 06 Plan 02: SITL smoke promoted to push+PR triggers (BLD-04)

Promoted the existing `sitl-e2e` GitHub Actions job from `workflow_dispatch`-only to `push + pull_request`, renamed it to `sitl-smoke`, added an evidence-event verification wrapper (`scripts/sitl_smoke.py`), and shipped a loud-failure test (`tests/drone/test_sitl_smoke_failure.py`) — closing BLD-04 without depending on the non-existent `ardupilot/ardupilot-sitl:Copter-4.5.7` Docker Hub image.

## What shipped

| Artifact | Purpose | Commit |
|----------|---------|--------|
| `scripts/sitl_smoke.py` (75 lines) | subprocess wrapper → `skyherd-sitl-e2e --emulator` → scans stdout+stderr for 5 required evidence events | `9fbaf76` |
| `tests/drone/test_sitl_smoke_failure.py` (92 lines) | fails-loud test: kills emulator mid-mission, asserts raise OR success=False | `e07dbfa` |
| `.github/workflows/ci.yml` edits | rename `sitl-e2e` → `sitl-smoke`, drop dispatch guard, add `timeout-minutes: 5`, add wrapper step, include failure test in pytest path list | `7f7fbf2` |

## Verification

- `uv run python scripts/sitl_smoke.py` — exits 0, prints `SITL smoke OK — all 5 evidence events verified.`, wall-time ≈ 10–15 s.
- `uv run pytest tests/drone/test_sitl_smoke_failure.py -v` — **1 skipped** (no opt-in). Clean skip-guard contract preserved.
- `SITL_EMULATOR=1 uv run pytest tests/drone/test_sitl_smoke_failure.py -v` — **1 passed** in ≈ 30 s.
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` — YAML OK.
- Success-criteria greps all match target counts:
  - `^  sitl-smoke:` = 1
  - `^  sitl-e2e:` = 0
  - `timeout-minutes: 5` = 1
  - `ardupilot/ardupilot-sitl` = 0  (image does not exist; no references anywhere in file)
  - `scripts/sitl_smoke.py` = 1
  - `test_sitl_smoke_failure.py` = 1
- `docker-sitl-smoke:` job preserved unchanged, still `if: github.event_name == 'workflow_dispatch'` (manual-only escalation path).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed `@pytest.mark.timeout(90)` marker**
- **Found during:** Task 2 verification
- **Issue:** The plan prescribed `@pytest.mark.timeout(90)` on `test_sitl_smoke_handshake_break_produces_failure`, but `pytest-timeout` is not installed in this project (`pyproject.toml` has no `pytest-timeout` dep; `uv pip list | grep -i timeout` returns nothing). pytest emitted `PytestUnknownMarkWarning: Unknown pytest.mark.timeout`.
- **Fix:** Dropped the marker. The outer `timeout-minutes: 5` on the CI job and the 30-second natural runtime of the test provide sufficient wall-clock protection. Note: the existing pytest step in CI uses `--timeout=300` (CLI flag), which would also error without the plugin — pre-existing issue, out of scope for this plan.
- **Files modified:** `tests/drone/test_sitl_smoke_failure.py`
- **Commit:** `e07dbfa` (applied before commit)

## Threat model reconciliation

All STRIDE mitigations from the plan's `<threat_model>` implemented:
- T-06-04 (DoS): `timeout-minutes: 5` on job + `timeout=180` on subprocess — bounded runtime.
- T-06-05 (EoP): emulator path uses default `GITHUB_TOKEN` permissions (no `packages: write`); `docker-sitl-smoke` stays manual.
- T-06-08 (Spoofing): 5 distinct evidence events required; all emitted only by real MAVLink codepath in `src/skyherd/drone/e2e.py`.
- T-06-09 (Error/Logging): `test_sitl_smoke_failure.py` directly asserts loud-failure contract; no `continue-on-error: true` on `sitl-smoke` job.

## Self-Check: PASSED

- [x] `scripts/sitl_smoke.py` present (verified via `ls`).
- [x] `tests/drone/test_sitl_smoke_failure.py` present.
- [x] `.github/workflows/ci.yml` YAML parses, contains `sitl-smoke:` job key, no `sitl-e2e:` key.
- [x] Commit `9fbaf76` — `feat(06-02): add scripts/sitl_smoke.py emulator CI wrapper (BLD-04)`.
- [x] Commit `e07dbfa` — `test(06-02): add SITL failure-path test (BLD-04 loud-failure discipline)`.
- [x] Commit `7f7fbf2` — `ci(06-02): promote sitl-smoke to push+PR triggers; add evidence wrapper (BLD-04)`.
