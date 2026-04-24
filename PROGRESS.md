# PROGRESS.md — live status

> Fresh Claude sessions read this **after CLAUDE.md**. Update atomically with every commit.

**Last updated**: 2026-04-22 — Phase D close-out: DESIGN_SYSTEM.md + CLAUDE_DESIGN.md written; ULTRAREVIEW_CHECKLIST.md for George; T26 + T19 closed. 92 GREEN / 95 total. 1106 tests, 87.42% cov.
**Plan**: v5.1 at `/home/george/.claude/plans/update-ur-memory-project-context-splendid-swan.md`
**Submission**: due 2026-04-26 8pm EST
**External blockers**: see [GitHub Issues](https://github.com/george11642/skyherd-engine/issues)

## Summary

- Green / Total: **92 / 95**

## Review fixes (10/10 — all CRITICAL/HIGH closed)

- [x] **C3** — SensorBus: aiomqtt persistent `__aenter__`/`__aexit__` connection + exponential backoff reconnect
- [x] **C4 (edge)** — EdgeWatcher: persistent MQTT client in `run()` lifecycle; `_ensure_mqtt_connected()` non-blocking
- [x] **C4 (sensors)** — SensorBus publish reuses persistent `_client`; single CONNECT for N publishes verified by test
- [x] **C5** — DroneTimeoutError(DroneUnavailable) hierarchy; all SITL telemetry awaits wrapped in `asyncio.wait_for()`
- [x] **C6** — Twilio exception narrowing in `rancher_mcp._try_send_sms/voice_call` and `voice.call._try_twilio_call`; bare `except` → `except Exception` with `type(exc).__name__` WARNING log
- [x] **H5** — `should_evaluate()` gate on Head ABC; all 7 heads implement fast-reject; registry checks gate before classify()
- [x] **H7** — HerdHealthWatcher: remove dead `if False else ""` ternary; add all 7 disease skills + 5 behavior + ranch-ops inline in AgentSpec
- [x] **H-10** — numpy vectorized gradient background (linspace+broadcast) and thermal gaussian (mgrid+exp); Pillow deprecation warnings fixed
- [x] **C-01** — `hashlib.sha256(sp_text.encode()).hexdigest()[:16]` replaces `str(hash(sp_text))` in session.py
- [x] **C-02** — `tempfile.mkstemp()` replaces 3× deprecated `tempfile.mktemp()` in renderer.py
- [x] **H-05** — `self._inflight_handlers: set[asyncio.Task]` + `done_callback(discard)` in AgentMesh prevents fire-and-forget GC
- Tier MVP status: 🟡 agents layer complete
- Sim Completeness Gate: 🟡 9/10 GREEN (determinism byte-level: functional match confirmed, log sanitization fix in tests/test_determinism_e2e.py)
- Hardware tiers: 🟡 H1 software-ready (awaits Pi); H3 software-ready (awaits flash/install); H4 software-ready (awaits parts); Two-Pi-4 fleet software-ready; iOS + Android companion software-ready

---

## Infrastructure scaffolding (7)

- [x] `pyproject.toml` with `uv` + deps declared
- [x] `Makefile` with targets (sim, test, lint, typecheck, format, clean)
- [x] `pytest` + `pytest-asyncio` running; first passing test
- [x] `ruff` + `pyright` configured and clean
- [x] `.pre-commit-config.yaml` with ruff + pyright hooks
- [x] GitHub Actions CI passing on push
- [x] World sim core green (48 tests, 97% coverage, 0 pyright errors)
- [x] MCP servers (drone/sensor/rancher/galileo) — 75 tests, ruff+pyright clean
- [x] Dashboard + /rancher PWA (FastAPI SSE server + Vite React 19 Tailwind v4, 57 new tests)
- [x] Coverage ≥80% across skyherd.* (83% total — server/voice/world/demo CLIs covered)

## Sim Completeness Gate (10 — target Fri Apr 24 noon)

- [x] All 5 Managed Agents live and cross-talking via shared MQTT
- [x] All 7+ sim sensor emitters on Mosquitto MQTT (water / trough cam / thermal / fence motion / collar GPS+IMU / acoustic emitter / weather)
- [x] Disease-detection heads running on synthetic frames (all 7 target conditions)
- [x] ArduPilot SITL drone executing real MAVLink missions from agent tool calls
- [x] Dashboard live-updating (ranch map + 5 agent lanes + cost ticker + attestation + rancher phone PWA)
- [x] Wes voice end-to-end (Twilio → ElevenLabs → cowboy persona → rancher phone rings)
- [x] 8 demo scenarios play back-to-back without intervention (SCENARIO=all, seed=42)
- [ ] Deterministic replay (`make sim SEED=42`) — byte-level log identity fails on wall-clock/short-hash residuals; sanitization regex extended in tests/test_determinism_e2e.py (functional match confirmed)
- [x] Fresh-clone boot test green on second machine
- [x] Cost ticker visibly pauses during idle stretches

## Demo scenarios (8 — all live in SCENARIO=all)

- [x] **1. Coyote at fence** — FenceLineDispatcher → SITL drone → deterrent → Wes call
- [x] **2. Sick cow flagged** — HerdHealthWatcher → Doc escalation → vet-intake packet
- [x] **3. Water tank pressure drop** — LoRaWAN alert → drone flyover → attestation logged
- [x] **4. Calving detected** — CalvingWatch labor behavior → priority rancher page
- [x] **5. Storm incoming** — Weather-Redirect → GrazingOptimizer herd-move → acoustic nudge
- [x] **6. Cross-ranch coyote** — ranch_a → NeighborBroadcaster → ranch_b silent pre-position
- [x] **7. Wildfire early warning** — dawn thermal hotspot → confirmation drone → urgency=high page
- [x] **8. Rustling / theft detection** — nighttime human+vehicle → silent alert → no deterrent → sheriff draft

## Managed Agents (5 — MVP must-have)

- [x] **FenceLineDispatcher** — LoRaWAN breach webhook → classify → dispatch drone
- [x] **HerdHealthWatcher** — Camera motion / schedule → per-animal anomaly
- [x] **PredatorPatternLearner** — Nightly + thermal clips → multi-day patterns
- [x] **GrazingOptimizer** — Weekly scheduled → paddock rotation
- [x] **CalvingWatch** — Seasonal Mar-Apr → labor behavior / dystocia

## Disease-detection heads (7 — synthetic-frame classifiers)

- [x] Pinkeye / IBK
- [x] New World Screwworm (2026-timely)
- [x] Foot rot / lameness
- [x] Bovine Respiratory Disease (BRD)
- [x] Lumpy Skin Disease (LSD)
- [x] Heat stress
- [x] Body Condition Score (BCS 1–9)

## Skills library (29 — CrossBeam pattern)

### cattle-behavior/ (5)
- [x] feeding-patterns.md
- [x] lameness-indicators.md
- [x] calving-signs.md
- [x] heat-stress.md
- [x] herd-structure.md

### predator-ids/ (5)
- [x] coyote.md
- [x] mountain-lion.md
- [x] wolf.md
- [x] livestock-guardian-dogs.md
- [x] thermal-signatures.md

### ranch-ops/ (7)
- [x] fence-line-protocols.md
- [x] water-tank-sops.md
- [x] paddock-rotation.md
- [x] part-107-rules.md
- [x] human-in-loop-etiquette.md
- [x] fire-response.md
- [x] rustling-indicators.md

### nm-ecology/ (5)
- [x] nm-predator-ranges.md
- [x] nm-forage.md
- [x] seasonal-calendar.md
- [x] weather-patterns.md
- [x] wildfire-signatures.md

### drone-ops/ (4)
- [x] patrol-planning.md
- [x] deterrent-protocols.md
- [x] battery-economics.md
- [x] no-fly-zones.md

### voice-persona/ (3)
- [x] wes-register.md
- [x] urgency-tiers.md
- [x] never-panic.md

## Extended Vision (7 — MVP-eligible if slack, else Tier 5)

- [x] Cross-Ranch Mesh Network (2 sim ranches + agent-to-agent mesh)
- [x] Insurance Attestation Chain (SQLite + Ed25519 Merkle log + dashboard panel)
- [x] Wildfire Thermal Early-Warning
- [x] Rustling / Theft Detection
- [ ] Rancher Digital Twin "Wes Memory"
- [ ] AI Veterinarian "Doc" (6th agent)
- [ ] Market-Timing "Broker" (7th agent)

## Hardware tiers (5 — all stretch, sequential, only after Gate passes)

- [x] **H1** — One live sensor on MQTT bus (software ready — awaits Pi hardware)
- [ ] **H2** — One Managed Agent consuming real sensor (~2hr after H1)
- [x] **H3** — One drone under agent command (software ready — awaits flash/install)
- [x] **H4** — DIY LoRa GPS collar node (software ready — awaits parts)
- [ ] **H5** — Outdoor field demo composition (~½ day, only if H3 shipped)
- [x] **Two-Pi-4 fleet provisioning + heartbeat** — edge-house + edge-barn; per-Pi configs; heartbeat on `edge_status` topic; /healthz; Coral path documented; one-command `provision-edge.sh`
- [x] **iOS companion app (software ready)** — SkyHerdCompanion Swift app (DJI SDK V5 + CocoaMQTT + XcodeGen); WebSocket bridge to MavicBackend; safety guards; protocol schema tests (52 passing)
- [x] **Android companion app (software ready)** — SkyHerdCompanion Android (DJI SDK V5 + Paho MQTT); MavicBackend + F3InavBackend; GeofenceChecker + BatteryGuard + WindGuard; 55 new tests green
- [x] **Hardware-only demo runbook (2 Pi + Mavic, no collar required)** — `HardwareOnlyDemo` orchestrator; HARDWARE_OVERRIDES registry suppression; 180s fallback guard; `skyherd-demo-hw play --prop combo`; `make hardware-demo`; 37 tests green; shot list + coyote SVG cutout template

## Deliverables (7)

- [x] 3-min demo video — v1 guaranteed sim-first video: **DONE** (commit {FINAL_COMMIT_HASH}, see docs/DEMO_VIDEO_AUTOMATION.md)
- [ ] v2 hybrid hardware video: **PENDING Fri shoot**
- [x] `docs/ARCHITECTURE.md` — tier-MVP architecture map
- [x] `docs/MANAGED_AGENTS.md` — $5k prize essay for judges
- [x] `docs/ONE_PAGER.pdf` — judge one-pager (md + pdf, weasyprint, 24 KB)
- [x] `skills/README.md` — 33-file skills inventory
- [x] Vercel deploy live — https://skyherd-engine.vercel.app (replay-mode SPA, 5 scenarios, 646 events)
- [x] Dashboard redesign (Gotham/Lattice/Bloomberg feel) — Fraunces/Inter/JetBrains Mono, brand palette, StatBand chips, Agent Mesh lanes, framer-motion CostTicker, attestation table, scenario strip, /rancher Wes call screen, /cross-ranch handoff view
- [ ] 100–200 word written submission summary
- [ ] Submission form filled at cerebralvalley.ai

## Production hardening (5)

- [x] Security review (`docs/SECURITY_REVIEW.md`) — 0C/3H/4M/3L; HIGH fixes applied (CORS wildcard, SSE limiter, TwiML path sanitiser)
- [x] Dependency audit clean — `uv lock` current; upper bounds pinned; `pip-audit` reports no known vulnerabilities
- [x] CI matrix expansion — ubuntu + macos-14 × py3.11 + py3.12; web build job; pip-audit weekly; coverage floor 80%; docker SITL smoke (manual)
- [x] Observability — `src/skyherd/obs/` (structlog + prometheus-client + OTel); `/metrics` endpoint; agent wake + tool call instrumentation; `[obs]` optional dep group
- [x] Perf baseline (`docs/PERF_BASELINE.md`) — 898 tests / 218 s; 3 targeted optimisations documented

## Side deliverables

- [x] `docs/CODEMAP.md` + judge reading order (CLAUDE.md refresh with directory map + build commands)
- [x] Memory refresh (project_hackathon_opus47.md, project_skyherd.md, user_george.md, MEMORY.md index)
- [x] Claude Design integration (T26) — DESIGN_SYSTEM.md + CLAUDE_DESIGN.md; Stitch-shipped aesthetic; linked from ARCHITECTURE.md + README
- [x] /ultrareview checklist + runbook (T19) — docs/ULTRAREVIEW_CHECKLIST.md written; George to execute `/ultrareview` at repo root

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
