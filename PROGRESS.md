# PROGRESS.md — live status

> Fresh Claude sessions read this **after CLAUDE.md**. Update atomically with every commit.

**Last updated**: 2026-04-21 (attestation chain)
**Plan**: v5.1 at `/home/george/.claude/plans/update-ur-memory-project-context-splendid-swan.md`
**Submission**: due 2026-04-26 8pm EST
**External blockers**: see [GitHub Issues](https://github.com/george11642/skyherd-engine/issues)

## Summary

- Green / Total: **6 / 78**
- Tier MVP status: 🔴 not started
- Sim Completeness Gate: 🔴 not passed (target Fri Apr 24 noon)
- Hardware tiers: 🔴 blocked on Gate

---

## Infrastructure scaffolding (7)

- [x] `pyproject.toml` with `uv` + deps declared
- [ ] `Makefile` with targets (sim, test, lint, typecheck, format, clean)
- [x] `pytest` + `pytest-asyncio` running; first passing test
- [x] `ruff` + `pyright` configured and clean
- [ ] `.pre-commit-config.yaml` with ruff + pyright hooks
- [ ] GitHub Actions CI passing on push
- [x] World sim core green (48 tests, 97% coverage, 0 pyright errors)

## Sim Completeness Gate (10 — target Fri Apr 24 noon)

- [ ] All 5 Managed Agents live and cross-talking via shared MQTT
- [ ] All 7+ sim sensor emitters on Mosquitto MQTT (water / trough cam / thermal / fence motion / collar GPS+IMU / acoustic emitter / weather)
- [ ] Disease-detection heads running on synthetic frames (all 7 target conditions)
- [x] ArduPilot SITL drone executing real MAVLink missions from agent tool calls
- [ ] Dashboard live-updating (ranch map + 5 agent lanes + cost ticker + attestation + rancher phone PWA)
- [ ] Wes voice end-to-end (Twilio → ElevenLabs → cowboy persona → rancher phone rings)
- [ ] 5 demo scenarios play back-to-back without intervention
- [ ] Deterministic replay (`make sim SEED=42`)
- [ ] Fresh-clone boot test green on second machine
- [ ] Cost ticker visibly pauses during idle stretches

## Demo scenarios (5 — MVP must-have)

- [ ] **1. Coyote at fence** — FenceLineDispatcher → SITL drone → deterrent → Wes call
- [ ] **2. Sick cow flagged** — HerdHealthWatcher → Doc escalation → vet-intake packet
- [ ] **3. Water tank pressure drop** — LoRaWAN alert → drone flyover → attestation logged
- [ ] **4. Calving detected** — CalvingWatch labor behavior → priority rancher page
- [ ] **5. Storm incoming** — Weather-Redirect → GrazingOptimizer herd-move → acoustic nudge

## Managed Agents (5 — MVP must-have)

- [ ] **FenceLineDispatcher** — LoRaWAN breach webhook → classify → dispatch drone
- [ ] **HerdHealthWatcher** — Camera motion / schedule → per-animal anomaly
- [ ] **PredatorPatternLearner** — Nightly + thermal clips → multi-day patterns
- [ ] **GrazingOptimizer** — Weekly scheduled → paddock rotation
- [ ] **CalvingWatch** — Seasonal Mar-Apr → labor behavior / dystocia

## Disease-detection heads (7 — synthetic-frame classifiers)

- [ ] Pinkeye / IBK
- [ ] New World Screwworm (2026-timely)
- [ ] Foot rot / lameness
- [ ] Bovine Respiratory Disease (BRD)
- [ ] Lumpy Skin Disease (LSD)
- [ ] Heat stress
- [ ] Body Condition Score (BCS 1–9)

## Skills library (26 — CrossBeam pattern)

### cattle-behavior/ (5)
- [ ] feeding-patterns.md
- [ ] lameness-indicators.md
- [ ] calving-signs.md
- [ ] heat-stress.md
- [ ] herd-structure.md

### predator-ids/ (5)
- [ ] coyote.md
- [ ] mountain-lion.md
- [ ] wolf.md
- [ ] livestock-guardian-dogs.md
- [ ] thermal-signatures.md

### ranch-ops/ (5)
- [ ] fence-line-protocols.md
- [ ] water-tank-sops.md
- [ ] paddock-rotation.md
- [ ] part-107-rules.md
- [ ] human-in-loop-etiquette.md

### nm-ecology/ (4)
- [ ] nm-predator-ranges.md
- [ ] nm-forage.md
- [ ] seasonal-calendar.md
- [ ] weather-patterns.md

### drone-ops/ (4)
- [ ] patrol-planning.md
- [ ] deterrent-protocols.md
- [ ] battery-economics.md
- [ ] no-fly-zones.md

### voice-persona/ (3)
- [ ] wes-register.md
- [ ] urgency-tiers.md
- [ ] never-panic.md

## Extended Vision (7 — MVP-eligible if slack, else Tier 5)

- [ ] Cross-Ranch Mesh Network (2 sim ranches + agent-to-agent mesh)
- [x] Insurance Attestation Chain (SQLite + Ed25519 Merkle log + dashboard panel)
- [ ] Wildfire Thermal Early-Warning
- [ ] Rustling / Theft Detection
- [ ] Rancher Digital Twin "Wes Memory"
- [ ] AI Veterinarian "Doc" (6th agent)
- [ ] Market-Timing "Broker" (7th agent)

## Hardware tiers (5 — all stretch, sequential, only after Gate passes)

- [ ] **H1** — One live sensor on MQTT bus (~2hr)
- [ ] **H2** — One Managed Agent consuming real sensor (~2hr after H1)
- [ ] **H3** — One drone under agent command (~1 day after H2)
- [ ] **H4** — DIY LoRa GPS collar node (~1 day after H3)
- [ ] **H5** — Outdoor field demo composition (~½ day, only if H3 shipped)

## Deliverables (6)

- [ ] 3-min demo video (YouTube unlisted)
- [ ] `docs/ARCHITECTURE.md` — tier-MVP architecture map
- [ ] `docs/MANAGED_AGENTS.md` — $5k prize essay for judges
- [ ] `docs/ONE_PAGER.pdf` — judge one-pager via Claude Design handoff
- [ ] 100–200 word written submission summary
- [ ] Submission form filled at cerebralvalley.ai

---

## How to use this file

Every commit that completes a checkbox:
1. Flip `[ ]` → `[x]` for the item(s).
2. Update `Green / Total` count at top.
3. Update `Last updated` date.
4. Stage + commit PROGRESS.md with the primary work in the same atomic commit.

If a section needs decomposing, add nested checkboxes. If a new item surfaces, add it and note in commit.

**Status emoji guide**: 🔴 not started · 🟡 in progress · 🟢 done

If the Gate flips green → update Sim Completeness Gate to 🟢.
If behind Fri noon → apply cut order from plan v5.1 (H5 → H4 → H3 → H2 → H1 → stop at sim-only).
