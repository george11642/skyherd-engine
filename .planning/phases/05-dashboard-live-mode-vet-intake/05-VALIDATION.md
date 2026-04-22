---
phase: 5
slug: dashboard-live-mode-vet-intake
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 5 — Validation Strategy

> Per-phase validation contract. See "Validation Architecture" section of `05-RESEARCH.md` for full test specs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + Vitest (frontend) + Lighthouse CI |
| **Config file** | `pyproject.toml` + `web/vitest.config.ts` + `.github/workflows/lighthouse.yml` |
| **Quick run command** | `uv run pytest tests/server/ tests/scenarios/test_sick_cow.py -x && (cd web && pnpm vitest run)` |
| **Full suite command** | `uv run pytest --cov=src/skyherd --cov-fail-under=80 && (cd web && pnpm run test && pnpm run build && pnpm exec lhci autorun)` |
| **Estimated runtime** | ~30-60s (quick) / ~5-8min (full with Lighthouse) |

---

## Sampling Rate

- **After every task commit:** Quick run scoped to server or web touched
- **After every plan wave:** Full suite + `make dashboard-live` smoke (boot + `curl /api/snapshot`)
- **Before `/gsd-verify-work`:** Lighthouse ≥90 + server live-path coverage ≥85% + sick-cow scenario produces vet-intake packet
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

*Filled during planning. Every plan task MUST have a row with an `<automated>` command.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|

---

## Wave 0 Requirements

- [ ] `tests/server/test_live_app.py` — DASH-01, DASH-02 coverage
- [ ] `tests/server/test_attest_verify.py` — DASH-04 verify-chain endpoint
- [ ] `web/src/components/__tests__/CostTicker.test.tsx` — DASH-03 paused-state render
- [ ] `tests/scenarios/test_sick_cow_vet_intake.py` — SCEN-01 vet-intake packet assertion
- [ ] `.github/workflows/lighthouse.yml` — DASH-06 Lighthouse ≥90 CI job

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cost ticker "paused" UI treatment is visually legible in 480p video | DASH-03 | Human-perception judgment | Screen-record golden-path scenario, verify paused state is obvious at 480p |
| Agent-lane motion polish reads smoothly (no jank) | DASH-05 | Motion QA | Play all 8 scenarios, observe agent lane entries, drone trail fade, predator pulse smoothing |
| Vet-intake packet content is rancher-readable (not raw JSON) | SCEN-01 | Subjective readability | Review rendered markdown; confirm field ordering, terminology, action clarity |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
