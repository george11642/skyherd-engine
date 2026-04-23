---
phase: 5
slug: dashboard-live-mode-vet-intake
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-22
updated: 2026-04-22
---

# Phase 5 — Validation Strategy

> Per-phase validation contract. See "Validation Architecture" section of `05-RESEARCH.md` for full test specs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + Vitest 3.x (frontend) + @lhci/cli 0.14 |
| **Config file** | `pyproject.toml` + `web/vite.config.ts` + `web/lighthouserc.json` + `.github/workflows/lighthouse.yml` |
| **Quick run command** | `uv run pytest tests/server/ tests/agents/test_vet_intake.py tests/scenarios/test_sick_cow.py -x && (cd web && pnpm test:run)` |
| **Full suite command** | `uv run pytest --cov=src/skyherd --cov-fail-under=80 && uv run pytest tests/server/ --cov=src/skyherd/server --cov-fail-under=85 && (cd web && pnpm test:run && pnpm run build && pnpm dlx @lhci/cli@0.14 autorun)` |
| **Estimated runtime** | ~40-60s (quick) / ~6-9min (full with Lighthouse) |

---

## Sampling Rate

- **After every task commit:** Quick run scoped to server or web files touched.
- **After every plan wave:** Full suite + `make dashboard` smoke (boot + `curl /api/snapshot`).
- **Before `/gsd-verify-work`:** Lighthouse ≥90 + server live-path coverage ≥85% + sick-cow scenario produces vet-intake packet.
- **Max feedback latency:** ~60 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01/T1 | 05-01 | 1 | DASH-02 | T-05-01 | Graceful fallback on missing accessor | TDD-RED unit | `uv run pytest tests/server/test_app_coverage.py::test_real_cost_tick_via_public_accessors tests/server/test_app_coverage.py::test_real_cost_tick_falls_back_when_no_accessor tests/server/test_events_live.py --tb=no -q` | New (Wave 0) | pending |
| 05-01/T2 | 05-01 | 1 | DASH-02 | T-05-01 / T-05-03 | Public-accessor contract enforced | TDD-GREEN refactor | `uv run pytest tests/server/ tests/scenarios/ --tb=short -q` | Existing | pending |
| 05-02/T1 | 05-02 | 1 | SCEN-01 | T-05-05 | Path traversal guarded | TDD-RED unit + scenario | `uv run pytest tests/agents/test_vet_intake.py tests/scenarios/test_sick_cow.py -k "vet_intake or draft_vet_intake" --tb=no -q` | New (Wave 0) | pending |
| 05-02/T2 | 05-02 | 1 | SCEN-01 | T-05-05 / T-05-07 | Path traversal + schema validation | TDD-GREEN unit | `uv run pytest tests/agents/test_vet_intake.py --tb=short -q` | New | pending |
| 05-02/T3 | 05-02 | 1 | SCEN-01 | T-05-06 / T-05-08 | SSE broadcast + deterministic sim mirror | TDD-GREEN scenario + SSE | `uv run pytest tests/agents/test_vet_intake.py tests/scenarios/test_sick_cow.py tests/server/ --tb=short -q && make demo SEED=42 SCENARIO=sick_cow` | Existing | pending |
| 05-03/T1 | 05-03 | 2 | DASH-01, DASH-04, SCEN-01 | T-05-11 / T-05-12 | Endpoint + XSS-safe renderer RED tests | TDD-RED unit + component | `uv run pytest tests/server/test_app_coverage.py -k "attest_verify or vet_intake_endpoint" --tb=no -q && (cd web && pnpm test:run -- VetIntakePanel AttestationPanel 2>&1 | tail -10)` | New (Wave 0) | pending |
| 05-03/T2 | 05-03 | 2 | DASH-01, DASH-02, DASH-04, SCEN-01 | T-05-10 / T-05-14 / T-05-15 | Endpoints + SSE buffering header | TDD-GREEN integration | `uv run pytest tests/server/test_app_coverage.py -k "attest_verify or vet_intake_endpoint" --tb=short -q` | Existing | pending |
| 05-03/T3 | 05-03 | 2 | DASH-04, DASH-06, SCEN-01 | T-05-12 | Inline markdown renderer (no react-markdown) | TDD-GREEN component | `cd web && pnpm test:run 2>&1 | tail -10 && pnpm build 2>&1 | tail -3` | New | pending |
| 05-04/T1 | 05-04 | 3 | DASH-03, DASH-05 | — | Paused-state visible + ring motion | TDD-RED component | `cd web && pnpm test:run -- CostTicker RanchMap --reporter=verbose 2>&1 | tail -15` | New (Wave 0) | pending |
| 05-04/T2 | 05-04 | 3 | DASH-03, DASH-05, DASH-06 | — | Motion polish + chunk split + preload | TDD-GREEN component + build | `cd web && pnpm test:run -- CostTicker RanchMap 2>&1 | tail -6 && pnpm build 2>&1 | tail -3` | Existing | pending |
| 05-04/T3 | 05-04 | 3 | DASH-01, DASH-02, DASH-06 | T-05-19 | Lighthouse + coverage gates | CI + coverage | `test -f web/lighthouserc.json && test -f .github/workflows/lighthouse.yml && grep -c "cov-fail-under=85" .github/workflows/ci.yml && uv run pytest tests/server/ --cov=src/skyherd/server --cov-fail-under=85 --tb=no -q` | New | pending |

---

## Wave 0 Requirements (created in RED tasks)

- [x] `tests/server/test_events_live.py` — DASH-02 coverage scaffold (Plan 05-01 Task 1)
- [x] `tests/server/test_app_coverage.py` extensions — public-accessor + verify + vet-intake + fallback (Plans 05-01 T1 + 05-03 T1)
- [x] `tests/agents/test_vet_intake.py` — SCEN-01 schema + path-traversal + markdown (Plan 05-02 Task 1)
- [x] `tests/scenarios/test_sick_cow.py` extensions — tool-call + artifact + treatment (Plan 05-02 Task 1)
- [x] `web/src/components/VetIntakePanel.test.tsx` — SCEN-01 UI component tests (Plan 05-03 Task 1)
- [x] `web/src/components/AttestationPanel.test.tsx` extensions — DASH-04 verify button tests (Plan 05-03 Task 1)
- [x] `web/src/components/CostTicker.test.tsx` extensions — DASH-03 paused state (Plan 05-04 Task 1)
- [x] `web/src/components/RanchMap.test.tsx` extensions — DASH-05 predator ring motion (Plan 05-04 Task 1)
- [x] `web/lighthouserc.json` + `.github/workflows/lighthouse.yml` — DASH-06 Lighthouse ≥90 CI gate (Plan 05-04 Task 3)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cost ticker "paused" UI treatment legible in 480p video | DASH-03 | Human-perception judgment at target bitrate | Screen-record golden-path scenario; verify paused state is obvious at 480p on a phone |
| Agent-lane motion polish reads smoothly (no jank) | DASH-05 | Motion QA | Play all 8 scenarios; observe agent lane entries, drone trail fade, predator pulse smoothing |
| Vet-intake packet content is rancher-readable (not raw JSON) | SCEN-01 | Subjective readability | Review a generated `runtime/vet_intake/A014_*.md`; confirm field ordering, terminology, action clarity |
| Verify Chain button animation + chip state transition reads cleanly | DASH-04 | Visual QA | Click verify in live mode; confirm chip transitions muted → … → VALID/INVALID |

---

## Requirement → Plan Map

| Requirement | Plans | Primary Gate |
|-------------|-------|--------------|
| DASH-01 | 05-03 (endpoints), 05-04 (verified via Phase 4 + 05-01 live-path) | live /api/snapshot returns real sim data |
| DASH-02 | 05-01 (events.py refactor + test scaffolds), 05-03 (endpoint coverage), 05-04 (CI gate) | pytest --cov=src/skyherd/server --cov-fail-under=85 |
| DASH-03 | 05-04 (CostTicker polish + Vitest) | Vitest paused-state assertion |
| DASH-04 | 05-03 (verify endpoint + button) | curl POST /api/attest/verify returns VerifyResult + Vitest button transitions |
| DASH-05 | 05-04 (RanchMap predator RAF + Vitest) | Vitest alpha-varies assertion |
| DASH-06 | 05-04 (Lighthouse CI + manualChunks + font preload) | lhci assert performance >= 0.9 |
| SCEN-01 | 05-02 (drafter + scenario), 05-03 (UI modal + endpoint) | tests/scenarios/test_sick_cow.py + runtime/vet_intake/A014_*.md exists |
| SCEN-02 (milestone-wide) | all plans | make demo SEED=42 SCENARIO=all shows 8 PASS |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands in their PLAN `<verify>` blocks.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (each of 11 tasks has one).
- [x] Wave 0 covers all MISSING test references (new files + extensions to existing).
- [x] No watch-mode flags (all commands are one-shot).
- [x] Feedback latency < 60s for the quick run.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** pending execution — gates will activate as plans land.
