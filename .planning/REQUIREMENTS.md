# Requirements: SkyHerd Engine — MVP Completion Milestone

**Defined:** 2026-04-22
**Core Value:** The 3-minute demo video must land "oh damn" inside the first 30 seconds on a pure-sim run, deterministically, every replay. Sim perfection beats hardware novelty every time a battery dies mid-demo.

**Scope note:** This is the FIRST milestone on an already-brownfield codebase. v1 requirements close the audit-surfaced gaps (`.planning/codebase/CONCERNS.md`) that break narrative credibility or Gate truthfulness. Subsequent milestones (hardware tiers H1–H5, voice hardening, cross-ranch mesh promotion, attestation year-2, demo video + submission) each get their own `/gsd-new-milestone` cycle.

---

## v1 Requirements

### Managed Agents Persistence (the $5k Managed Agents prize architecture)

- [ ] **MA-01**: Each of the 5 agents (FenceLineDispatcher / HerdHealthWatcher / PredatorPatternLearner / GrazingOptimizer / CalvingWatch) runs on exactly ONE long-lived platform session that persists across events within a scenario run. Zero fresh `SessionManager()` instantiations per event.
- [ ] **MA-02**: `src/skyherd/scenarios/base.py::_DemoMesh` holds a session registry keyed by agent name; dispatch reuses the existing session or creates it lazily on first wake.
- [ ] **MA-03**: Coyote scenario end-to-end creates at most 5 platform sessions total (one per agent) vs current 241. Verified by `SessionManager` instantiation count in test harness.
- [ ] **MA-04**: Cost ticker shows idle-pause behavior: when no events are routed to an agent for N seconds, its `rate_per_hr_usd` drops to 0.0 and `all_idle: True` appears on the SSE stream.
- [ ] **MA-05**: Checkpoint persistence works — `PredatorPatternLearner` running nightly keeps context across sim-day boundaries within a scenario run.

### Agent Routing Correctness

- [ ] **ROUT-01**: `PredatorPatternLearner` is present in `_registry` dict in `scenarios/base.py`.
- [ ] **ROUT-02**: Routing table in `scenarios/base.py` includes entries for `thermal.anomaly` → `[FenceLineDispatcher, PredatorPatternLearner]` and `skyherd/+/cron/nightly` → `[PredatorPatternLearner]`.
- [ ] **ROUT-03**: Rustling scenario assertions verify agent dispatch count (not just event presence in the stream).
- [ ] **ROUT-04**: All 5 agents have at least one assertion in at least one scenario that proves they actually ran (`AgentDispatched` counter ≥ 1 per agent across the scenario suite).

### Vision Credibility (the Keep Thinking $5k pattern-match)

- [ ] **VIS-01**: At least one disease head (target: pinkeye — most visually obvious for a judge-facing demo) is rewritten to perform real pixel-level inference on the rendered PNG frame. Not threshold classification on `Cow.ocular_discharge`.
- [ ] **VIS-02**: The pixel-head uses a MIT/BSD-licensed backbone (e.g. MegaDetector V6 as animal detector + small task-specific head, or a distilled CNN on rendered frames). No Ultralytics / AGPL imports.
- [ ] **VIS-03**: The pixel-head and the remaining 6 rule-based heads share the same `DiseaseHead` ABC interface; pipeline output format unchanged.
- [ ] **VIS-04**: Pixel-head inference runs on synthetic frames in under 500ms per frame on CPU (dev-box baseline) — cannot slow the sim below 2× real time.
- [ ] **VIS-05**: One scenario (e.g. sick_cow) has a visible dashboard panel showing the pixel-head's detection with bounding box + confidence — real, not faked.

### Build & Quickstart Health

- [ ] **BLD-01**: `make_world()` accepts default `config_path` resolving to `worlds/ranch_a.yaml` via `importlib.resources` or package-relative `Path`. Judge quickstart `make_world(seed=42)` works without arguments.
- [ ] **BLD-02**: Fresh-clone flow documented in README verified on a second machine (or clean worktree): `git clone ... && cd skyherd-engine && uv sync && make demo SEED=42 SCENARIO=all` completes in under 5 minutes and all scenarios PASS.
- [ ] **BLD-03**: `make dashboard` in live (non-mock) mode serves a functional dashboard from a fresh clone.
- [ ] **BLD-04**: SITL smoke test added to CI using `SITL_IMAGE=ardupilot/ardupilot-sitl:Copter-4.5.7` pre-built image; single smoke scenario proves real MAVLink mission upload + arm + takeoff + RTL in under 2 minutes.

### Dashboard Live-Mode & Polish

- [ ] **DASH-01**: `make dashboard` (without `SKYHERD_MOCK=1`) injects real `mesh`, `world`, and `ledger` into the FastAPI app; `/api/snapshot` returns real sim data.
- [ ] **DASH-02**: Server live-path coverage increases to ≥85% (from current 73%).
- [ ] **DASH-03**: Cost ticker UI shows visible "paused" state when `all_idle: True`; tested on camera in a golden-path scenario run.
- [ ] **DASH-04**: Attestation panel streams live Merkle chain appends via SSE; verify-chain button in UI.
- [ ] **DASH-05**: Motion polish pass — agent-lane entry animations, ranch map drone trail fade, predator pulse ring smoothing. No design-system rebuild.
- [ ] **DASH-06**: Dashboard demonstrates all 5 agents on distinct agent lanes with real session IDs, real wake events, real tool calls (not mock-generated). Lighthouse score ≥90 on the SPA.

### Scenario Completeness

- [ ] **SCEN-01**: Sick-cow scenario produces a rendered, rancher-readable vet-intake packet (drafted by HerdHealthWatcher → Doc skill or direct) and logs it to a retrievable location. Asserted in scenario test.
- [ ] **SCEN-02**: All 8 scenarios (coyote / sick_cow / water_drop / calving / storm / cross_ranch_coyote / wildfire / rustling) continue to PASS after all other changes. Zero regression.
- [ ] **SCEN-03**: Deterministic replay strengthened — scenario JSONL output byte-identical at hash level after timestamp sanitization; `make sim SEED=42` verified stable across three back-to-back runs.

### Code Hygiene

- [ ] **HYG-01**: Replace the 15+ identified `except: pass` blocks (listed in `CONCERNS.md §3`) with `except Exception as exc: logger.warning(...)`. No bare silent-catch remains in `src/skyherd/`.
- [ ] **HYG-02**: Twilio auth token env var standardized on `TWILIO_AUTH_TOKEN` across `voice/call.py` and `mcp/rancher_mcp.py`; `.env.example` updated; deprecation warning on `TWILIO_TOKEN`.
- [ ] **HYG-03**: `agents/cost.py` coverage raised to ≥90% with tests for idle-pause billing, active-state delta accumulation, and the `all_idle` aggregation path.
- [ ] **HYG-04**: Ruff + pyright run clean. The 15 pyright errors in `drone/pymavlink_backend.py` / `drone/sitl_emulator.py` resolved or added to typed-ignore list with rationale comments.
- [ ] **HYG-05**: Test coverage gate remains 80%+; actual project-wide coverage holds or exceeds 87%.

---

## v2 Requirements

Deferred to subsequent milestones per George's direction: "the next gsd milestones will be for each of the next phases mentioned in the original plan."

### Hardware Tier Progression (own milestone each)

- **HW-H1**: First real sensor (Pi 4 + PiCamera v3 + MegaDetector) on the MQTT bus alongside sim emitters
- **HW-H2**: Real FenceLineDispatcher session woken by desk-cardboard-coyote through Pi sensor → SITL drone takeoff
- **HW-H3**: First real rotor — Mavic Air 2 via DJI Mobile SDK V5 Android companion OR SP Racing F3 reflashed to iNav + ~$15 GPS module, under Claude tool-call command
- **HW-H4**: First DIY LoRa GPS collar (RAK3172 + u-blox M10 + MPU-6050 + LiPo + 3D-printed shell) reporting into ChirpStack alongside sim collars
- **HW-H5**: Outdoor field demo composition (Pi + phone + drone pre-recorded at UNM-area open land)

### Voice & Mesh

- **VOICE-01**: Wes Twilio live-call path with credentials wired, voice clone QA'd
- **VOICE-02**: Wes persona register + urgency tiers validated against 8 scenario variants
- **MESH-01**: Cross-ranch mesh promoted from bonus scenario to first-class feature with dedicated agent + dashboard panel
- **MESH-02**: Extended Vision Category A additions (wildfire first-class, rustling first-class)

### Attestation & Submission

- **ATT-01**: Attestation chain year-2 LRP-rider hardening (verify-chain CLI, signature rotation, public viewer)
- **SUB-01**: 3-minute demo video recorded, cut, uploaded unlisted YouTube
- **SUB-02**: Submission form filled + confirmation screenshotted
- **SUB-03**: LinkedIn launch post drafted (requires George's approval per CLAUDE.md)
- **SUB-04**: `docs/ONE_PAGER.pdf` judge one-pager exported

### Optional Depth (README roadmap only)

- **EXT-01**: Wes-Memory digital twin (6th agent stacking on Most Creative Exploration $5k)
- **EXT-02**: "Doc" AI veterinarian (6th agent, vision + structured output)
- **EXT-03**: "Broker" market-timing agent (futures × condition → sell-window)

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web dashboard rebuild | Audit confirmed existing dashboard is judge-worthy (custom Canvas renderer, design tokens). Polish + live-mode wiring only in this milestone. |
| Ultralytics / YOLOv12 | AGPL-3.0 — would infect SkyHerd's MIT repo. MegaDetector V6 is the only vision path. |
| Layer 6 Sequester | Year 3+ per VISION.md. Not on hackathon critical path. |
| Halter-parity collar hardware | Unit-economics decision for pilot-time, not v1. DIY LoRa path is honest answer for the pitch. |
| Claude Design handoff bundle | Build-time design layer only. Skip unless slack after all other milestones land. |
| Replacing all 7 vision heads with pixel inference | One head proves the capability without slowing sim or risking scope blow-up. |
| Native iOS/Android builds without DJI SDK credentials | Scaffolds exist; true build is hardware-tier milestone work. |
| Session-state compression / memory tool integration | Gated MA beta feature; defer unless access granted and slack exists. |
| Multi-tenant ranch accounts, auth, billing | Not hackathon-scope — this is a demo, not a product launch. |

---

## Traceability

Filled in by the roadmapper. Every v1 requirement must map to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MA-01 | TBD | Pending |
| MA-02 | TBD | Pending |
| MA-03 | TBD | Pending |
| MA-04 | TBD | Pending |
| MA-05 | TBD | Pending |
| ROUT-01 | TBD | Pending |
| ROUT-02 | TBD | Pending |
| ROUT-03 | TBD | Pending |
| ROUT-04 | TBD | Pending |
| VIS-01 | TBD | Pending |
| VIS-02 | TBD | Pending |
| VIS-03 | TBD | Pending |
| VIS-04 | TBD | Pending |
| VIS-05 | TBD | Pending |
| BLD-01 | TBD | Pending |
| BLD-02 | TBD | Pending |
| BLD-03 | TBD | Pending |
| BLD-04 | TBD | Pending |
| DASH-01 | TBD | Pending |
| DASH-02 | TBD | Pending |
| DASH-03 | TBD | Pending |
| DASH-04 | TBD | Pending |
| DASH-05 | TBD | Pending |
| DASH-06 | TBD | Pending |
| SCEN-01 | TBD | Pending |
| SCEN-02 | TBD | Pending |
| SCEN-03 | TBD | Pending |
| HYG-01 | TBD | Pending |
| HYG-02 | TBD | Pending |
| HYG-03 | TBD | Pending |
| HYG-04 | TBD | Pending |
| HYG-05 | TBD | Pending |

**Coverage:**
- v1 requirements: 32 total
- Mapped to phases: 0 (pre-roadmap)
- Unmapped: 32 ⚠️ (resolves when ROADMAP.md is written)

---
*Requirements defined: 2026-04-22*
*Last updated: 2026-04-22 after initial definition post-audit*
