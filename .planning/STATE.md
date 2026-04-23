---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: completed
last_updated: "2026-04-23T13:09:48.533Z"
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 22
  completed_plans: 22
  percent: 100
---

# STATE: SkyHerd Engine — Project Memory

**Milestone:** MVP Completion
**Initialized:** 2026-04-22
**Last Updated:** 2026-04-22 (roadmap complete)

---

## Project Reference

**Core Value:** The 3-minute demo video must land "oh damn" inside the first 30 seconds on a pure-sim run, deterministically, every replay. Sim perfection beats hardware novelty every time a battery dies mid-demo.

**Current Focus:** Phase 06 — sitl-ci-determinism-gate

**Submission Deadline:** 2026-04-26 20:00 EST (target submit: 2026-04-26 18:00 EST with 2hr buffer).

---

## Current Position

**v1.0 milestone shipped 2026-04-23** (6/6 phases, 22/22 plans, 32/32 requirements). Archived at `.planning/milestones/v1.0-*`.

**Post-v1.0 standalone phase (pre-milestone):**

Phase: 1 (memory-powered-agent-mesh) — NOT PLANNED
Plan: —
**Status:** Phase added via `/gsd-add-phase`; scope written to ROADMAP.md.
**Next action:** `/gsd-plan-phase 1` to decompose into executable plans.

### Phase Status Board

| Phase | Status | Depends On | Can Parallelize With |
|-------|--------|------------|----------------------|
| 1. Memory-Powered Agent Mesh | Not planned | v1.0 (shipped) | — (standalone post-v1.0) |

---

## Performance Metrics

**Baseline (pre-milestone, audit 2026-04-22):**

- Tests: 1106 passing / 13 skipped / 0 failed
- Coverage: 87.42% (gate: 80%)
- Scenarios: 8/8 PASS in ~3s wall time
- Sim Completeness Gate: 7 GREEN / 2 YELLOW / 1 UNVERIFIABLE
- Known gaps: 241-sessions-per-scenario leak, PredatorPatternLearner un-routed, rule-based vision heads

**Targets (end of milestone):**

- Tests: maintain or exceed 1106 passing; coverage ≥ 87%
- `agents/cost.py` coverage ≥ 90% (HYG-03)
- `server/` live-path coverage ≥ 85% (DASH-02)
- Scenarios: 8/8 PASS unchanged (SCEN-02)
- Sessions per coyote scenario: ≤ 5 (MA-03, down from 241)
- SITL CI smoke: < 2 min (BLD-04)
- Fresh-clone quickstart: < 5 min (BLD-02)
- Pixel-head inference: < 500ms/frame CPU (VIS-04)
- Lighthouse SPA: ≥ 90 (DASH-06)

---

## Accumulated Context

### Key Decisions Logged

| Decision | Rationale | Locked |
|----------|-----------|--------|
| Session persistence fix = #1 priority (front-load Phase 1) | 241-session leak breaks the Managed Agents $5k prize narrative on any judge inspection | 2026-04-22 |
| One pixel-level vision head, keep other 6 rule-based | Protects credibility without slowing sim or risking scope blow-up; pinkeye is most visually obvious for demo | 2026-04-22 |
| MegaDetector V6 only (no Ultralytics/YOLOv12) | AGPL-3.0 would infect SkyHerd's MIT repo — hard license constraint | 2026-04-22 |
| Defer all hardware tiers (H1–H5) to subsequent milestones | v5.1 sim-first hardline; each hardware tier gets own `/gsd-new-milestone` | 2026-04-22 |
| Keep existing dashboard, polish + live-mode wire only | Audit confirmed custom Canvas renderer + design tokens are judge-worthy, not stock shadcn | 2026-04-22 |
| BLD-04 (SITL-CI) isolated to Phase 6 with failure-tolerant wiring | Docker SITL image build is infra-risky; isolation prevents infra flakiness from masking real regressions | 2026-04-22 |
| SCEN-02 = milestone-wide acceptance criterion, not a standalone plan | Every phase must leave the 8-scenario suite passing; verified in Phase 6 | 2026-04-22 |

### Roadmap Evolution

- 2026-04-23: Phase 1 added (Memory-Powered Agent Mesh) — post-v1.0 standalone phase to adopt the Claude Managed Agents Memory public beta across the 5-agent mesh before the 2026-04-26 submission.

### Todos Carried Across Sessions

*(populated as phases execute)*

### Active Blockers

None.

### Risk Register

| Risk | Phase | Mitigation |
|------|-------|------------|
| SITL Docker image fails to pull in CI | 6 | BLD-04 isolated as non-blocking CI job; failure reported but doesn't gate merge |
| Pixel-head inference exceeds 500ms on CPU | 2 | Fallback to smaller distilled CNN; escape hatch: hybrid (pixel head for sick_cow demo only, rule fallback otherwise) |
| Phase 1 session persistence changes break scenario determinism | 1 | SCEN-02 zero-regression criterion; Phase 1 verifier re-runs full scenario suite before merge |
| `make dashboard` live-mode surface breaks existing mock path | 5 | Preserve `SKYHERD_MOCK=1` fallback; DASH-01 acceptance asserts both paths work |
| Merge conflicts across parallel worktrees on `scenarios/base.py` | 1 | Phase 1 holds exclusive write access to `scenarios/base.py`; other phases read-only until merge |

---

## Session Continuity

**Last session ended:** 2026-04-22 (post-roadmap-creation)

**Artifacts on disk for next session:**

- `.planning/PROJECT.md` — project context, validated + active + out-of-scope requirements
- `.planning/REQUIREMENTS.md` — 32 v1 requirements with full phase traceability
- `.planning/ROADMAP.md` — 6-phase structure with dependencies + success criteria
- `.planning/codebase/CONCERNS.md` — audit ground truth (top-10 gaps)
- `.planning/codebase/ARCHITECTURE.md` — 5-layer nervous-system ground truth
- `.planning/config.json` — granularity: standard, model: quality, parallelization: true, YOLO mode
- `.planning/STATE.md` — this file

**Next action:** `/gsd-plan-phase 1` to decompose Phase 1 (Memory-Powered Agent Mesh) into executable plans.

**Parallel opportunity:** N/A — single standalone post-v1.0 phase.

---

*STATE.md initialized: 2026-04-22*
