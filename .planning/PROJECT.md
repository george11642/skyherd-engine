# SkyHerd Engine

## What This Is

SkyHerd Engine is George's submission for the **"Built with Opus 4.7" Claude Code hackathon** (Apr 21–26 2026). It's a deterministic ranch simulator wrapped around a 5-agent **Claude Managed Agents** mesh that monitors a simulated American ranch 24/7 — coyote at the fence, sick cow flagged, water tank drop, calving detected, storm incoming — driving an ArduPilot SITL drone, a "Wes" cowboy voice persona, and an Ed25519-attested event ledger. The submission is 100% sim-first; hardware (Pi + Mavic + DIY LoRa collar) integrates one-piece-at-a-time in later milestones only after the Sim Completeness Gate passes.

## Core Value

**The 3-minute demo video must land "oh damn" inside the first 30 seconds on a pure-sim run, deterministically, every replay.** Hardware is bonus; narrative credibility with Anthropic-team judges (Mike Brown / Thariq Shihipar / Michael Cohen lineage) is not. If anything else fails — but sim plays cleanly, agents *actually* persist across events, vision has real-enough pixel inference to withstand inspection, and the cost ticker demonstrably pauses on idle — we ship.

## Requirements

### Validated

<!-- Ground-truth from skeptical audit 2026-04-22 — verified implemented in `src/skyherd/` -->

- ✓ **Deterministic ranch world simulator** (`src/skyherd/world/`) — seed=42 byte-identical replay, 100% coverage — existing
- ✓ **7 sensor emitters on MQTT bus** (`src/skyherd/sensors/` — water, trough cam, thermal, fence, collar GPS+IMU, acoustic, weather) — existing
- ✓ **5 agent specs with real Managed Agents beta integration** — `client.beta.agents/sessions/environments.*` wired; live agent IDs in `runtime/agent_ids.json`, live env in `runtime/ma_environment_id.txt` — existing
- ✓ **34 domain skills organized CrossBeam-style** (`skills/` — cattle-behavior, drone-ops, nm-ecology, predator-ids, ranch-ops, voice-persona) consumed via `cache_control: ephemeral` — existing
- ✓ **4 MCP servers** (drone / sensor / rancher / galileo) with real Twilio + MAVSDK + ElevenLabs tool implementations — existing
- ✓ **8 demo scenarios pass** `make demo SEED=42 SCENARIO=all` in ~3s (coyote / sick_cow / water_drop / calving / storm + bonus cross_ranch_coyote / wildfire / rustling) — existing
- ✓ **Ed25519 + Merkle attestation ledger** (`src/skyherd/attest/`) — 97%/98% coverage — existing
- ✓ **Wes TTS fallback chain** (ElevenLabs → piper → espeak → silent; Twilio live-call path behind credentials) — existing
- ✓ **FastAPI + SSE dashboard backend** (`src/skyherd/server/`) — `/health`, `/api/snapshot`, `/api/agents`, `/api/attest`, `/events`, `/metrics` — existing
- ✓ **High-quality React 19 + Tailwind v4 SPA** — custom Canvas 2D ranch map, design tokens (sage/dust/thermal), Fraunces/Inter/JetBrains Mono, PWA manifest, 497-line RancherPhone — existing
- ✓ **ArduPilot SITL backend via MAVSDK-Python** (real `arm()` / `takeoff()` / `mission_upload()` / `start_mission()` / `return_to_launch()`) — existing
- ✓ **Hardware collar firmware** (RAK3172 + TinyGPS++ + MPU-6050, 312 lines) — existing
- ✓ **iOS + Android companion app scaffolds** with DJI SDK V5 wiring — existing
- ✓ **1106 tests passing / 87.42% coverage** (exceeds "880+ / 80%" claim) — existing

### Active

<!-- Current milestone: MVP Completion — close the audit-surfaced gaps that break narrative credibility or Gate truthfulness. -->

- [ ] **Persistent managed-agent sessions** — Rewire `src/skyherd/scenarios/base.py` + `_DemoMesh` so each of the 5 agents has ONE long-lived session reused across events; eliminate the 241-fresh-`SessionManager()`-per-scenario leak. This is the real "Best Use of Claude Managed Agents $5k" prize architecture.
- [ ] **PredatorPatternLearner actually dispatched** — Add to `_registry` and add `thermal.anomaly` + `skyherd/+/cron/nightly` to the routing table in `scenarios/base.py`. Rustling scenario must prove agent dispatch, not just event-presence.
- [ ] **At least one real pixel-level vision head** — Replace one rule-engine head (e.g. pinkeye or BRD) with actual MegaDetector V6 or CNN inference on rendered PNG frames. Protects narrative credibility if judges inspect. Keep other 6 as rule-based for demo speed.
- [ ] **SITL runs in CI** — Fast SITL smoke test with pre-built `ardupilot/ardupilot-sitl` image; fresh-clone `make demo SEED=42` works on second machine; `make_world()` gains default `config_path`.
- [ ] **Dashboard live-mode + polish pass** — Wire non-mock live path end-to-end (inject real mesh + world + ledger into FastAPI app). Add motion polish. Verify cost ticker *visibly* pauses on idle on camera. NO rebuild — keep the existing Canvas renderer + design system.
- [ ] **Silent-except sweep + Twilio env normalization** — Replace 15+ bare `except: pass` blocks with logged warnings; standardize on `TWILIO_AUTH_TOKEN`; add `cost.py` tests for idle-pause billing.
- [ ] **Vet-intake packet rendering for HerdHealthWatcher** — Sick-cow scenario must produce and log a rancher-readable vet-intake draft; add to scenario assertions.
- [ ] **Fresh-clone boot verification** — On a clean checkout, `uv sync && make demo SEED=42 SCENARIO=all` must pass and `make dashboard` must serve. Documented + asserted.

### Out of Scope

<!-- Explicit boundaries for this milestone. Each becomes its own /gsd-new-milestone later per George's direction. -->

- **Dashboard rebuild** — Audit confirmed existing dashboard is judge-worthy (custom Canvas renderer, design tokens, not stock shadcn). Only polish + live-mode wiring in this milestone.
- **Tier H1 + H2 hardware** (first Pi sensor + desk cardboard-coyote) — Deferred to "Hardware H1+H2" milestone per v5.1 sim-first hardline.
- **Tier H3 real drone under agent command** (Mavic DJI SDK or F3 iNav) — Deferred to "Hardware H3" milestone.
- **Tier H4 DIY LoRa collar field node** — Deferred to "Hardware H4" milestone.
- **Tier H5 outdoor field demo + video** — Deferred to "Demo Video + Submission" milestone.
- **Voice/Wes live Twilio call with credentials** — Twilio chain exists; full voice-persona hardening (voice clone QA, live-call path coverage) deferred to "Voice Hardening" milestone.
- **Cross-ranch mesh as first-class feature** (dashboard panel, dedicated agent) — Bonus scenario exists; promoting to first-class deferred to "Cross-Ranch Mesh" milestone.
- **Attestation year-2 LRP-rider hardening** (public viewer, signature rotation, verify-chain CLI polish) — Core chain exists; year-2 product deferred to "Attestation Hardening" milestone.
- **Claude Design handoff bundle build-time design layer** — Skip unless slack; not a runtime component.
- **Tier 5 Extended Vision bonus features** (Wes-Memory digital twin, Doc 6th agent, Broker market-timing agent, wildfire thermal) — README roadmap only.
- **Layer 6 Sequester** — Year 3+ per VISION.md.
- **All hardcoded Halter-parity collars** — DIY LoRa collar is the unit-economics honest path; premium collars are a pilot-time decision, not a v1 decision.
- **Ultralytics / YOLOv12** — AGPL-3.0; would infect SkyHerd's MIT license. MegaDetector V6 only.

## Context

**Event**: *Built with Opus 4.7* hackathon, Apr 21–26 2026, submission 8pm EST Apr 26. Prize pool $50k / $30k / $10k main + three $5k specials (Managed Agents, Keep Thinking, Most Creative). George is sole registered entrant; Gavin (engineering) and Josh (pitch/narrative) pair behind the scenes.

**Source of truth plan**: `/home/george/.claude/plans/update-ur-memory-project-context-splendid-swan.md` (v5.1 sim-first hardline, locked Apr 21 2026).

**Pattern-match lineage**:
- **CrossBeam** (Opus 4.6 1st place, $50k) — Skills-first architecture. SkyHerd has 34 skills already; milestone must preserve that pattern, not regress it.
- **TARA** (Opus 4.6 Keep Thinking, $5k) — Vision loop on hard domain. SkyHerd's pixel-level vision head directly answers this prize.
- **Managed Agents** (platform launched Apr 8 2026) — Session persistence, idle-pause billing, webhook wake, checkpoints. The #1 gap in SkyHerd today.

**Current ground-truth state** (audit 2026-04-22, `.planning/codebase/`):
- Code is more real than PROGRESS.md admits in most places (87% test coverage, all scenarios pass, real MA beta wiring, real attestation, real Canvas renderer dashboard).
- Code is less real than CLAUDE.md claims in three narrative-critical places: (1) session-per-event architecture breaks "persistent agents" story, (2) vision heads are threshold classifiers on Cow struct fields not pixel CNN, (3) PredatorPatternLearner is registered but never dispatched in scenarios.
- **All 10 Gate items have evidence — 7 GREEN / 2 YELLOW / 1 UNVERIFIABLE** per `CONCERNS.md §2`.

**Repo**: `/home/george/projects/active/skyherd-engine` — MIT, public. Python 3.11+ with `uv`, pytest + ruff + pyright, Vite + React 19 + Tailwind v4, FastAPI + SSE. Commits already have Claude Code attribution disabled globally.

**Sibling repo** `/home/george/projects/active/drone/` holds VISION.md (5-layer nervous-system canonical doc) and the presentation deck — **reference only, no code reuse** per hackathon "all code new" rule.

## Constraints

- **Licensing**: MIT throughout. Zero AGPL dependencies (blocks Ultralytics / YOLOv12). MegaDetector V6 is the vision base.
- **Timeline**: Submission deadline Apr 26 2026 8pm EST (audit already at Apr 22 — ~4 days of wall time for this milestone + all follow-on milestones combined). Phase 1 must close fast.
- **Sim-first hardline**: No hardware code in this milestone. Every hardware tier is its own later milestone.
- **Beta header**: `managed-agents-2026-04-01` must remain the Managed Agents SDK header. Applied automatically by SDK — do not override.
- **Prompt caching mandatory**: Every `messages.create` / `sessions.events.send` path must emit `cache_control: ephemeral` for system prompt + skills prefix (CrossBeam pattern). Non-negotiable per `claude-api` skill.
- **Attribution**: Commits carry zero Claude/Anthropic attribution (global git config).
- **Determinism**: `make demo SEED=42 SCENARIO=all` must remain byte-identical across replays (after wall-timestamp sanitization). Required for video retakes.
- **Model usage**: Opus 4.7 for agent reasoning; Haiku 4.5 acceptable for high-frequency sensor classification if it lands latency win.
- **Test gate**: 80%+ coverage remains the `fail_under` threshold. No regressions.
- **Security**: No hardcoded secrets. `.env.local` gitignored. Twilio / ElevenLabs / Anthropic API keys from env only.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Run `/gsd-map-codebase` before scoping REQUIREMENTS | User directive: don't trust PROGRESS.md/memory completion claims | ✓ Good — surfaced 3 narrative-critical gaps that would have been missed |
| Keep existing web dashboard; polish + live-mode wire only | Audit confirmed custom Canvas renderer + design tokens, not stock shadcn | — Pending (validate at Phase N) |
| Session persistence fix is the #1 priority | 241-session-per-scenario leak breaks Managed Agents prize narrative on inspection | — Pending |
| Replace ONE vision head with real pixel inference, keep other 6 rule-based | Protects judge credibility without breaking scenario speed | — Pending |
| Defer all hardware tiers to subsequent milestones | v5.1 sim-first hardline; user-reaffirmed on 2026-04-22 | ✓ Good — scope locked |
| Quality model profile (Opus) for planning agents | Hackathon-submission stakes justify higher planner cost | — Pending |
| Standard granularity (5-8 phases) | Fits the 8 Active requirements cleanly; avoids phase-sprawl | — Pending |
| YOLO mode | Matches George's orchestrator-by-default style | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-22 after initialization (post-audit of existing brownfield)*
