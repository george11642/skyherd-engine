# Milestones

## v1.0 — MVP Completion (Shipped: 2026-04-23)

**Status:** SHIPPED
**Phases:** 6
**Plans:** 22
**Requirements:** 32/32 satisfied
**Sim Completeness Gate:** 10/10 GREEN
**Audit:** `.planning/milestones/v1.0-MILESTONE-AUDIT.md`
**Archive:** `.planning/milestones/v1.0-ROADMAP.md`, `.planning/milestones/v1.0-REQUIREMENTS.md`

### Key Accomplishments

- **Agent session persistence** — replaced 241-session-per-scenario leak with one long-lived Managed Agents session per agent; PredatorPatternLearner wired into routing; idle-pause billing (`all_idle`/`rate_per_hr_usd: 0.0`) streaming over SSE.
- **Real pixel-level vision** — pinkeye disease head rewritten as MIT-licensed MobileNetV3-Small pixel inference (<500 ms/frame CPU), shipping with committed weights, training script, and bounding-box surface in the sick-cow scenario.
- **Dashboard live-mode + vet-intake** — real mesh/world/ledger injected into FastAPI; vet-intake packet drafted by HerdHealthWatcher; `/api/attest/verify` + `/api/vet-intake` + VetIntakePanel; CostTicker paused-state polish.
- **Fresh-clone quickstart** — `make_world(seed=42)` works no-arg via `importlib.resources`; `make dashboard` flipped to live; nightly fresh-clone-smoke CI job; 3-command judge quickstart verified.
- **Code hygiene sweep** — 15+ silent-except blocks replaced with logged warnings; Twilio auth standardized on `TWILIO_AUTH_TOKEN` with deprecation path; `cost.py` coverage ≥ 90%; ruff + pyright clean.
- **Determinism + SITL-CI gate** — 3-run byte-identical hash determinism test; SITL smoke CI on `ardupilot/ardupilot-sitl:Copter-4.5.7` in < 2 min, isolated from main gates; all 8 scenarios pass `make demo SEED=42 SCENARIO=all`.

### Phase Summary

| Phase | Name | Plans |
|-------|------|-------|
| 1 | Agent Session Persistence & Routing | 3 |
| 2 | Vision Pixel Inference | 5 |
| 3 | Code Hygiene Sweep | 4 |
| 4 | Build & Quickstart Health | 3 |
| 5 | Dashboard Live-Mode & Vet-Intake | 4 |
| 6 | SITL-CI & Determinism Gate | 3 |

### Stats

- Timeline: 2026-04-22 → 2026-04-23 (~36 hours wall time)
- LOC (Python): ~39,826
- LOC (TS/TSX): ~51,262
- Tests: 1106+ passing, coverage ≥ 87% (gate 80%)
- Scenarios: 8/8 pass `make demo SEED=42 SCENARIO=all`

---
