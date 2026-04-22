---
phase: 2
slug: vision-pixel-inference
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 2 — Validation Strategy

> Per-phase validation contract. See "Validation Architecture" section of `02-RESEARCH.md` for full test specs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-benchmark (for latency) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/vision/ -x` |
| **Full suite command** | `uv run pytest --cov=src/skyherd/vision --cov-fail-under=85` |
| **Estimated runtime** | ~20-40s (quick, excluding training) / ~2-3min (full) |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/vision/test_heads/test_pinkeye.py tests/test_licenses.py -x`
- **After every plan wave:** Full vision suite + license-clean assertion
- **Before `/gsd-verify-work`:** Full suite + `make demo SCENARIO=sick_cow` green
- **Max feedback latency:** ~40 seconds

---

## Per-Task Verification Map

*Filled during planning. Every plan task MUST have a row with an `<automated>` command.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|

---

## Wave 0 Requirements

- [ ] `tests/vision/conftest.py` — synthetic-frame fixture generator (positive / negative pinkeye frames)
- [ ] `tests/test_licenses.py` — AGPL import-guard test; asserts no `ultralytics` / `yolov5` in base install
- [ ] `src/skyherd/vision/_models/` — scaffold directory for weights (`.gitignore` weights, ship download script)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sick-cow scenario dashboard panel shows real bbox overlay | VIS-05 | Visual — hard to assert pixel-perfect in CI | Run `make dashboard` live mode, play sick_cow scenario, verify bbox renders on rendered PNG |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
