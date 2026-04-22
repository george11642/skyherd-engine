---
phase: 4
slug: build-quickstart-health
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 4 — Validation Strategy

> Per-phase validation contract. See "Validation Architecture" section of `04-RESEARCH.md` for full test specs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + bash script + GH Actions |
| **Config file** | `pyproject.toml` + `scripts/fresh_clone_smoke.sh` + `.github/workflows/*.yml` |
| **Quick run command** | `uv run pytest tests/world/test_make_world.py tests/server/test_live_app.py -x` |
| **Full suite command** | `uv run pytest && bash scripts/fresh_clone_smoke.sh` |
| **Estimated runtime** | ~10-20s (quick) / ~3-5min (full, fresh-clone adds ~3min) |

---

## Sampling Rate

- **After every task commit:** Quick run scoped to the file being modified
- **After every plan wave:** Full suite + `uv build && unzip -l dist/*.whl | grep worlds/` (asserts world YAML ships in wheel)
- **Before `/gsd-verify-work`:** `bash scripts/fresh_clone_smoke.sh` completes in <5min on CI
- **Max feedback latency:** ~20 seconds (quick) / ~5min (full with fresh-clone)

---

## Per-Task Verification Map

*Filled during planning. Every plan task MUST have a row with an `<automated>` command.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|

---

## Wave 0 Requirements

- [ ] `tests/world/test_make_world.py` — BLD-01 assertion that `make_world(seed=42)` works with no args
- [ ] `tests/server/test_live_app.py` — BLD-03 assertion that `create_app(mock=False, ...)` returns live data
- [ ] `tests/docs/test_readme_quickstart.py` — BLD-02 doc-drift guard; greps canonical quickstart command strings
- [ ] `scripts/fresh_clone_smoke.sh` — mktemp+clone+full quickstart flow

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Judge clones repo on a machine with uv already installed and runs 3-command quickstart | BLD-02 | True "fresh" requires a non-CI machine | Pull repo on a second laptop, run the 3 README commands, time it, confirm all scenarios PASS |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s (quick) / < 5min (fresh-clone)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
