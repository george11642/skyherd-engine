---
phase: 1
slug: agent-session-persistence-routing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. See the "Validation Architecture" section of `01-RESEARCH.md` for full test specs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/agents/ tests/scenarios/ -x` |
| **Full suite command** | `uv run pytest --cov=src/skyherd --cov-fail-under=80` |
| **Estimated runtime** | ~30-60s (quick) / ~3-5min (full) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/agents/test_session.py tests/agents/test_mesh.py tests/scenarios/test_routing.py -x`
- **After every plan wave:** Run `make demo SEED=42 SCENARIO=all && uv run pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite green + zero-regression scenarios
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

*Filled during planning (`/gsd-plan-phase 1`). Each plan task MUST have a row here with an `<automated>` test command.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|

---

## Wave 0 Requirements

- [ ] `tests/agents/test_session_registry.py` — new file for session-count assertions
- [ ] `tests/scenarios/test_routing.py` — new file for dispatch assertions (already exists? verify)
- [ ] `tests/conftest.py` — add `counting_session_manager` fixture that monkeypatches `SessionManager.__init__` to count instantiations

---

## Manual-Only Verifications

*None planned — all Phase 1 behaviors have automated verification per RESEARCH.md Validation Architecture.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
