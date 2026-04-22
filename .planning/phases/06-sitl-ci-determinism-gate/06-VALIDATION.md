---
phase: 6
slug: sitl-ci-determinism-gate
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 6 — Validation Strategy

> Per-phase validation contract. See "Validation Architecture" section of `06-RESEARCH.md` for full test specs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + `skyherd-sitl-e2e --emulator` CLI + `make gate-check` |
| **Config file** | `pyproject.toml` + `.github/workflows/*.yml` + `Makefile` |
| **Quick run command** | `uv run pytest tests/drone/ tests/test_determinism_e2e.py -x` |
| **Full suite command** | `uv run pytest && make determinism-3x && make sitl-smoke && make gate-check` |
| **Estimated runtime** | ~15-30s (quick) / ~2-3min (full with gate-check) |

---

## Sampling Rate

- **After every task commit:** Quick run scoped to drone/ or scenarios/
- **After every plan wave:** `make sitl-smoke` + `make determinism-3x`
- **Before `/gsd-verify-work`:** `make gate-check` prints 10/10 GREEN and exits 0
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

*Filled during planning. Every plan task MUST have a row with an `<automated>` command.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|

---

## Wave 0 Requirements

- [ ] `scripts/gate_check.py` — new file; iterates 10 Gate items and prints GREEN/YELLOW/RED
- [ ] `Makefile` — new targets `sitl-smoke`, `determinism-3x`, `gate-check`
- [ ] `.github/workflows/ci.yml` — promote existing `sitl-e2e` `workflow_dispatch` job to `push + pull_request` trigger
- [ ] `tests/test_determinism_e2e.py` — parameterize existing test to 3-run in-body loop with hash equality assertion

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `make gate-check` output legible to a judge skim-reading | SCEN-02 | Human-readable UX judgment | Run locally, confirm 10-row table format matches CLAUDE.md's Gate list |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
