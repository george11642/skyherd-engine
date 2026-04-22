# Roadmap: SkyHerd Engine — MVP Completion Milestone

**Milestone:** MVP Completion (audit-surfaced gap closure)
**Granularity:** standard (6 phases)
**Parallelization:** enabled (see dependency graph)
**Coverage:** 32/32 v1 requirements mapped
**Defined:** 2026-04-22

---

## Core Value Anchor

The 3-minute demo video must land "oh damn" inside the first 30 seconds on a pure-sim run, deterministically, every replay. Sim perfection beats hardware novelty every time a battery dies mid-demo.

## Milestone-Wide Acceptance Criterion (every phase inherits)

**SCEN-02 (zero-regression):** All 8 scenarios (coyote / sick_cow / water_drop / calving / storm / cross_ranch_coyote / wildfire / rustling) MUST continue to PASS `make demo SEED=42 SCENARIO=all` after every phase lands. Each phase's verifier re-runs the scenario suite.

---

## Phases

- [ ] **Phase 1: Agent Session Persistence & Routing** — Replace 241-session-per-scenario leak with one long-lived session per agent; wire PredatorPatternLearner into the dispatch graph. The $5k Managed Agents prize architecture.
- [ ] **Phase 2: Vision Pixel Inference** — Replace one rule-based disease head (pinkeye) with real pixel-level inference on rendered frames. The Keep Thinking $5k pattern-match.
- [ ] **Phase 3: Code Hygiene Sweep** — Eliminate silent except blocks, normalize Twilio env vars, raise cost.py coverage, clean pyright errors.
- [ ] **Phase 4: Build & Quickstart Health** — `make_world()` default config_path; fresh-clone boot verified; live-mode `make dashboard` serves from clean checkout.
- [ ] **Phase 5: Dashboard Live-Mode & Vet-Intake** — Wire real mesh/world/ledger into FastAPI app; vet-intake packet render; motion polish; visible idle-pause on camera.
- [ ] **Phase 6: SITL-CI & Determinism Gate** — Fast SITL smoke test in CI with pre-built image; strengthened deterministic replay; final zero-regression gate.

---

## Dependency Graph

```
Phase 1 (MA + ROUT) ────────┐
                            ├──► Phase 5 (DASH + SCEN-01) ──► Phase 6 (BLD-04 + SCEN-03)
Phase 2 (VIS) ──────────────┤
                            │
Phase 4 (BLD-01..03) ───────┘

Phase 3 (HYG) — fully parallel with 1, 2, 4 (no shared files)
```

**Parallelization guidance:**
- Phases 1, 2, 3, 4 can execute **in parallel worktrees** (disjoint file surfaces).
- Phase 5 depends on Phase 1 (needs session registry for real mesh injection) AND Phase 2 (pixel-head panel in `DASH-06`).
- Phase 6 is the final gate — runs last, verifies no phase introduced regression.

**Shared file watch-list (for merge discipline):**
- `src/skyherd/scenarios/base.py` — Phase 1 only.
- `src/skyherd/vision/` — Phase 2 only.
- `src/skyherd/server/` — Phase 5 only.
- `src/skyherd/voice/call.py`, `src/skyherd/mcp/rancher_mcp.py` — Phase 3 (Twilio) only.
- `Makefile`, `.github/workflows/` — Phase 4 and Phase 6 must coordinate.

---

## Phase Details

### Phase 1: Agent Session Persistence & Routing
**Goal**: Each of the 5 agents runs on ONE long-lived Managed Agents session reused across all events in a scenario run, and every agent (including PredatorPatternLearner) is actually dispatched by the routing table.
**Depends on**: Nothing (first phase)
**Requirements**: MA-01, MA-02, MA-03, MA-04, MA-05, ROUT-01, ROUT-02, ROUT-03, ROUT-04
**Success Criteria** (what must be TRUE):
  1. A judge running `skyherd-demo play coyote --seed 42` and inspecting the session count observes at most 5 platform sessions created (one per agent), not 241.
  2. The rustling scenario dispatches `PredatorPatternLearner` at least once, verified by `AgentDispatched` counter assertion in the scenario test — not merely by event-presence in the stream.
  3. All 5 agents have at least one test assertion across the scenario suite proving they actually ran (`AgentDispatched ≥ 1` per agent).
  4. The SSE stream emits `rate_per_hr_usd: 0.0` and `all_idle: True` after N seconds of no routed events, demonstrating real idle-pause billing.
  5. `PredatorPatternLearner` retains context across sim-day boundaries within a scenario run (checkpoint persistence observable in session state).
**Plans**: TBD

### Phase 2: Vision Pixel Inference
**Goal**: The pinkeye disease head performs real pixel-level inference on rendered PNG frames using an MIT/BSD-licensed backbone, sharing the `DiseaseHead` ABC with the other 6 rule-based heads.
**Depends on**: Nothing (parallel with Phase 1)
**Requirements**: VIS-01, VIS-02, VIS-03, VIS-04, VIS-05
**Success Criteria** (what must be TRUE):
  1. A judge inspecting `src/skyherd/vision/heads/pinkeye.py` sees real pixel inference (PIL/numpy frame → model → detection), not threshold classification on `Cow.ocular_discharge`.
  2. The vision module imports only MIT/BSD-licensed dependencies — no Ultralytics, no AGPL imports anywhere in the dependency tree.
  3. `ClassifyPipeline.run()` output format (list of `DetectionResult`) is unchanged — the other 6 rule-based heads still work alongside the pixel head.
  4. On the dev-box baseline (CPU), pixel-head inference completes in under 500ms per frame; sim still runs at 2× real time or faster.
  5. Running the sick-cow scenario surfaces a visible pixel-head detection in the dashboard with real bounding box + confidence — not a mocked overlay.
**Plans**: TBD

### Phase 3: Code Hygiene Sweep
**Goal**: All silent-except blocks replaced with logged warnings; Twilio auth env var standardized; cost.py billing logic fully tested; ruff + pyright run clean.
**Depends on**: Nothing (parallel with Phases 1, 2, 4)
**Requirements**: HYG-01, HYG-02, HYG-03, HYG-04, HYG-05
**Success Criteria** (what must be TRUE):
  1. A `grep -rn "except.*pass" src/skyherd/` returns zero bare silent catches (all 15+ CONCERNS.md §3 sites converted to `except Exception as exc: logger.warning(...)`).
  2. Twilio voice calls succeed regardless of code path — both `voice/call.py` and `mcp/rancher_mcp.py` read `TWILIO_AUTH_TOKEN`, with a deprecation warning emitted if the legacy `TWILIO_TOKEN` is set instead.
  3. `agents/cost.py` coverage ≥ 90%, with explicit tests proving idle-pause billing, active-state delta accumulation, and the `all_idle` aggregation path behave as specified.
  4. `uv run pyright` exits clean (the 15 pre-existing drone errors resolved or carried with rationale comments); `uv run ruff check` exits clean.
  5. Project-wide coverage holds or exceeds 87% — no regression on the global gate.
**Plans**: TBD

### Phase 4: Build & Quickstart Health
**Goal**: A judge cloning the repo fresh and running the documented 3-command quickstart succeeds in under 5 minutes, with `make_world(seed=42)` usable without arguments and `make dashboard` serving live-mode (not mock-only).
**Depends on**: Nothing (parallel with Phases 1, 2, 3)
**Requirements**: BLD-01, BLD-02, BLD-03
**Success Criteria** (what must be TRUE):
  1. `from skyherd.world import make_world; make_world(seed=42)` succeeds in any Python context without a `config_path` argument, resolving to `worlds/ranch_a.yaml` via package-relative path.
  2. On a clean worktree, `uv sync && make demo SEED=42 SCENARIO=all` completes in under 5 minutes and all 8 scenarios PASS — documented in README and asserted by a CI job that uses a fresh checkout.
  3. `make dashboard` (without `SKYHERD_MOCK=1`) serves a functional dashboard from a clean clone — real `/api/snapshot` returns live sim data, not mock fixtures.
  4. README Judge Quickstart (3 commands) is verified executable as written; no hidden setup steps.
**Plans**: TBD

### Phase 5: Dashboard Live-Mode & Vet-Intake
**Goal**: The dashboard demonstrates the full real stack on camera — real mesh sessions with real wake events, real attestation Merkle appends, a visible idle-pause cost ticker, agent-lane motion polish, and a rendered rancher-readable vet-intake packet produced during the sick-cow scenario.
**Depends on**: Phase 1 (needs session registry to inject real mesh), Phase 2 (pixel-head panel for DASH-06)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, SCEN-01
**Success Criteria** (what must be TRUE):
  1. Running `make dashboard` (non-mock) surfaces all 5 agents on distinct lanes with real platform session IDs, real wake events, and real tool calls — inspected via DevTools, payloads match `runtime/agent_ids.json`.
  2. A judge watching the golden-path scenario on camera observes the cost ticker visibly transition to a "paused" state when `all_idle: True`, with distinguishable UI treatment — not a numeric change only.
  3. Running the sick-cow scenario produces a retrievable, human-readable vet-intake packet (rendered text / markdown / JSON) drafted by HerdHealthWatcher, asserted in the scenario test and linked from the dashboard.
  4. Agent-lane entry animations, drone trail fade on the ranch map, and predator pulse ring smoothing are present — no design-system rebuild, only motion polish.
  5. The attestation panel streams live Merkle chain appends over SSE as scenarios run; a verify-chain button in the UI invokes the existing verify-chain path.
  6. Server live-path coverage ≥ 85% (from current 73%); Lighthouse score on the SPA ≥ 90.
**Plans**: TBD
**UI hint**: yes

### Phase 6: SITL-CI & Determinism Gate
**Goal**: CI proves the SITL MAVLink path works end-to-end in under 2 minutes using a pre-built Docker image, and the deterministic-replay guarantee is strengthened to hash-stable across three back-to-back runs — with the full scenario suite as the final zero-regression gate.
**Depends on**: Phases 1, 2, 3, 4, 5 (final gate — runs last)
**Requirements**: BLD-04, SCEN-03, SCEN-02 (milestone-wide criterion verified here)
**Success Criteria** (what must be TRUE):
  1. A CI job running with `SITL_IMAGE=ardupilot/ardupilot-sitl:Copter-4.5.7` executes a single SITL smoke scenario — real MAVLink mission upload + arm + takeoff + RTL — in under 2 minutes and PASSES on every commit.
  2. Three back-to-back runs of `make sim SEED=42` produce byte-identical JSONL output (after standardized timestamp sanitization) — asserted by a determinism test that computes and compares hashes.
  3. All 8 scenarios (coyote / sick_cow / water_drop / calving / storm / cross_ranch_coyote / wildfire / rustling) PASS `make demo SEED=42 SCENARIO=all` — the milestone-wide zero-regression criterion.
  4. The SITL smoke CI job failure does NOT block other CI jobs (scenario suite, lint, tests, coverage) — isolated so infra flakiness doesn't mask real regressions.
**Plans**: TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Agent Session Persistence & Routing | 0/TBD | Not started | - |
| 2. Vision Pixel Inference | 0/TBD | Not started | - |
| 3. Code Hygiene Sweep | 0/TBD | Not started | - |
| 4. Build & Quickstart Health | 0/TBD | Not started | - |
| 5. Dashboard Live-Mode & Vet-Intake | 0/TBD | Not started | - |
| 6. SITL-CI & Determinism Gate | 0/TBD | Not started | - |

---

## Coverage Summary

**All 32 v1 requirements mapped. Zero orphans. Zero duplicates.**

| Category | Requirements | Phase |
|----------|--------------|-------|
| Managed Agents Persistence | MA-01, MA-02, MA-03, MA-04, MA-05 | Phase 1 |
| Agent Routing Correctness | ROUT-01, ROUT-02, ROUT-03, ROUT-04 | Phase 1 |
| Vision Credibility | VIS-01, VIS-02, VIS-03, VIS-04, VIS-05 | Phase 2 |
| Code Hygiene | HYG-01, HYG-02, HYG-03, HYG-04, HYG-05 | Phase 3 |
| Build & Quickstart (core) | BLD-01, BLD-02, BLD-03 | Phase 4 |
| Dashboard Live-Mode | DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06 | Phase 5 |
| Scenario Completeness (vet-intake) | SCEN-01 | Phase 5 |
| SITL-CI (infra-isolated) | BLD-04 | Phase 6 |
| Determinism Gate | SCEN-03 | Phase 6 |
| Zero-Regression (milestone-wide) | SCEN-02 | Every phase (verified in Phase 6) |

---

*Roadmap created: 2026-04-22*
