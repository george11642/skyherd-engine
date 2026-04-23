---
phase: 6
slug: sitl-ci-determinism-gate
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-22
updated: 2026-04-22
---

# Phase 6 — Validation Strategy

> Per-phase validation contract. See "Validation Architecture" section of `06-RESEARCH.md` for full test specs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8+ + `skyherd-sitl-e2e --emulator` CLI + `make gate-check` |
| **Config file** | `pyproject.toml` + `.github/workflows/ci.yml` + `Makefile` |
| **Quick run command** | `uv run pytest tests/drone/ tests/test_determinism_e2e.py -x -m "not slow"` |
| **Full suite command** | `uv run pytest && make determinism-3x && make sitl-smoke && make gate-check` |
| **Estimated runtime** | ~15-30s (quick) / ~2-3min (full with gate-check) |

---

## Sampling Rate

- **After every task commit:** Quick run scoped to drone/ or tests/test_determinism_e2e.py
- **After every plan wave:** `make sitl-smoke` + `make determinism-3x`
- **Before `/gsd-verify-work`:** `make gate-check` prints 10/10 GREEN and exits 0
- **Max feedback latency:** ~30 seconds (per-task) / ~3 minutes (full gate)

---

## Per-Task Verification Map

*Filled during planning. Every plan task has a row with an `<automated>` command.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-T1 | 01 | 1 | SCEN-03 | T-06-01, T-06-02 | Sanitizer whitelist source-controlled; cross-run hash equality asserted | integration | `uv run pytest tests/test_determinism_e2e.py --collect-only -q` + `uv run pytest tests/test_determinism_e2e.py -v -m slow --timeout=600` | existing (edit) | planned |
| 06-02-T1 | 02 | 1 | BLD-04 | T-06-08 | Five distinct evidence events required; subprocess timeout bounded | integration | `uv run python scripts/sitl_smoke.py` (exits 0 on success; non-zero on missing events) | new | planned |
| 06-02-T2 | 02 | 1 | BLD-04 | T-06-09 | Loud failure on mid-mission handshake break; skip-guard prevents accidental runs | integration | `SITL_EMULATOR=1 uv run pytest tests/drone/test_sitl_smoke_failure.py -v --timeout=120` + `uv run pytest tests/drone/test_sitl_smoke_failure.py -v` (must show 1 skipped without opt-in) | new | planned |
| 06-02-T3 | 02 | 1 | BLD-04 | T-06-04, T-06-05 | `timeout-minutes: 5` bounds CI wall-time; no `continue-on-error` on emulator path; `docker-sitl-smoke` remains `workflow_dispatch`-only | integration | `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` + grep assertions on `^  sitl-smoke:` + `! grep -q "ardupilot/ardupilot-sitl:Copter-4.5.7"` | existing (edit) | planned |
| 06-03-T1 | 03 | 2 | SCEN-02, BLD-04, SCEN-03 | T-06-10, T-06-11 | 10 Gate items iterated verbatim from CLAUDE.md; subprocesses bounded by `timeout=` kwargs; `--fast` flag skips heavy checks | integration | `uv run python scripts/gate_check.py --fast` (fast path) + `uv run python scripts/gate_check.py` (full path) | new | planned |
| 06-03-T2 | 03 | 2 | SCEN-02, SCEN-03, BLD-04 | T-06-13 | No existing target edited; Phase 4 `dashboard`/`dashboard-mock` preserved; recipes tab-indented | unit | `make -n sitl-smoke` + `make -n determinism-3x` + `make -n gate-check` + `grep -c "^dashboard:" Makefile` = 1 | existing (append) | planned |

---

## Wave 0 Requirements

Wave 0 gaps are self-supplied by the plans themselves — each plan writes the test/script it verifies against in the same task:

- [x] **Plan 01 Task 1** writes + asserts the 3-run determinism test (no separate Wave 0 needed; the test IS the deliverable).
- [x] **Plan 02 Task 1** writes `scripts/sitl_smoke.py` which is the verification tool for BLD-04.
- [x] **Plan 02 Task 2** writes `tests/drone/test_sitl_smoke_failure.py` which is the loud-failure assertion.
- [x] **Plan 02 Task 3** wires the above into `.github/workflows/ci.yml` with the YAML-parse assertion as its verify.
- [x] **Plan 03 Task 1** writes `scripts/gate_check.py` which iterates all 10 CLAUDE.md Gate items.
- [x] **Plan 03 Task 2** exposes all three runners via Makefile targets.

No orphan Wave 0 items remain. All automated-verify commands have a concrete file target.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `make gate-check` output legible to a judge skim-reading | SCEN-02 | Human-readable UX judgment | Run locally, confirm 10-row table format matches CLAUDE.md's Gate list verbatim in both key names and descriptions |
| Pre-submit Gate retro-audit on CI log of main | SCEN-02 | CI log readability is a human judgment | After Phases 1-5 merged, run `make gate-check` on a fresh clone and screenshot for the demo video B-roll if useful |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every task has one)
- [x] Wave 0 covers all MISSING references (self-supplied by Tasks)
- [x] No watch-mode flags
- [x] Feedback latency < 30s for quick-run; < 3min for full gate
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planning complete; awaiting execution

---

## Phase 6 Source Coverage Audit

All 3 requirement IDs (from ROADMAP) are mapped:

| Source Item | Covered By |
|-------------|------------|
| **GOAL**: CI proves SITL MAVLink path works end-to-end in under 2 min using pre-built image | Plan 02 (emulator path — corrects Docker Hub mirage per RESEARCH.md) |
| **GOAL**: Deterministic-replay guarantee strengthened to hash-stable across 3 back-to-back runs | Plan 01 (3-run in-body loop, not parametrize) |
| **GOAL**: Full scenario suite as final zero-regression gate | Plan 03 (`_check_scenarios` + `skyherd-demo play all --seed 42`) |
| **REQ**: BLD-04 (SITL-CI) | Plan 02 (primary) + Plan 03 (`_check_sitl_mission`) |
| **REQ**: SCEN-03 (determinism) | Plan 01 (primary) + Plan 03 (`_check_determinism`) |
| **REQ**: SCEN-02 (milestone-wide zero-regression) | Plan 03 (Gate retro-audit across all 10 items) |
| **RESEARCH**: Emulator-only primary path; Docker optional escalation; no GHCR push | Plan 02 (emulator promoted; docker-sitl-smoke stays manual; GHCR deferred) |
| **RESEARCH**: In-body 3-loop NOT parametrize | Plan 01 (explicit anti-pattern avoidance) |
| **RESEARCH**: Makefile ownership non-overlap with Phase 4 | Plan 03 (appends only; zero edits to existing targets) |
| **RESEARCH**: 10 Gate items verbatim | Plan 03 (`GATE_ITEMS` list matches CLAUDE.md) |
| **CONTEXT**: All implementation choices at Claude's discretion | All plans honor the discretion constraint |

No gaps. No deferred items. No phase split required.
