---
phase: 3
slug: code-hygiene-sweep
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 3 — Validation Strategy

> Per-phase validation contract. See "Validation Architecture" section of `03-RESEARCH.md` for full test specs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + ruff + pyright |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/agents/test_cost.py tests/voice/ -x && uv run ruff check src/skyherd/` |
| **Full suite command** | `uv run pytest --cov=src/skyherd --cov-fail-under=80 && uv run pyright src/skyherd/ && uv run ruff check src/skyherd/` |
| **Estimated runtime** | ~15-30s (quick) / ~3-5min (full with pyright) |

---

## Sampling Rate

- **After every task commit:** Quick run + category-specific test for the silent-except sweep category in flight
- **After every plan wave:** Full suite + `rg 'except.*:\s*pass' src/skyherd/` returns 0 sites outside typed-shutdown allowlist
- **Before `/gsd-verify-work`:** Full suite + ruff clean + pyright clean
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

*Filled during planning. Every plan task MUST have a row with an `<automated>` command.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|

---

## Wave 0 Requirements

- [ ] `tests/agents/test_cost.py` — extend with 4 new test classes (MqttPublishCallback, LedgerCallback, Properties, RunTickLoopBody)
- [ ] `tests/voice/test_twilio_env.py` — new test for `_get_twilio_auth_token()` helper + deprecation warning
- [ ] Verify `pyright` already configured in `pyproject.toml` (it is per audit)

---

## Manual-Only Verifications

*None — all hygiene targets have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
