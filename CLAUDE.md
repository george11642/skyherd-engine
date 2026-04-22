# CLAUDE.md — Project Orientation

## Reading Order (60-second orientation for new Claude sessions, contributors, and judges)

1. `docs/ONE_PAGER.md` — what SkyHerd is in 500 words.
2. `docs/ARCHITECTURE.md` — 5-layer nervous-system pattern + Skills-first + attestation chain.
3. `docs/MANAGED_AGENTS.md` — why the 5-agent mesh wins the Managed Agents $5k.
4. `PROGRESS.md` — live status + Sim Completeness Gate.
5. `docs/HARDWARE_DEMO_RUNBOOK.md` — the 60-second hardware-only hero demo.
6. `docs/verify-latest.md` — automated truth-check (regenerated every 30 min while the session is open).

## Directory Map (high-level)

- `src/skyherd/world/` — deterministic ranch simulator (seed=42 replays byte-identical).
- `src/skyherd/sensors/` — MQTT bus + 7 sim sensor emitters.
- `src/skyherd/agents/` — 5 Managed-Agents-compat mesh (FenceLineDispatcher, HerdHealthWatcher, PredatorPatternLearner, GrazingOptimizer, CalvingWatch).
- `src/skyherd/mcp/` — drone/sensor/rancher/galileo MCP servers.
- `src/skyherd/vision/` — scene renderer + 7 disease-detection heads.
- `src/skyherd/drone/` — sitl / stub / mavic / f3_inav backends + shared safety guards.
- `src/skyherd/edge/` — Pi 4 runtime (camera + detector + MQTT publisher + heartbeat).
- `src/skyherd/attest/` — Ed25519 Merkle ledger (year-2 LRP underwriting artifact).
- `src/skyherd/voice/` — Wes persona + TTS chain (ElevenLabs → piper → espeak → silent).
- `src/skyherd/scenarios/` — 5 demo scenarios + cross-ranch variant.
- `src/skyherd/server/` — FastAPI + SSE dashboard backend.
- `src/skyherd/demo/` — hardware-only orchestrator (2 Pi + Mavic, no collar needed).
- `web/` — Vite + React 19 + Tailwind v4 SPA + /rancher PWA.
- `android/SkyHerdCompanion/` — Kotlin + DJI SDK V5 + MQTT companion.
- `ios/SkyHerdCompanion/` — Swift + DJI SDK V5 + CocoaMQTT companion (XcodeGen).
- `hardware/collar/` — optional DIY LoRa collar (PlatformIO firmware + 3D print + BOM).
- `skills/` — 33-file ranch domain knowledge library (CrossBeam pattern).
- `worlds/` — ranch YAML configs (ranch_a, ranch_b).
- `docs/` — ARCHITECTURE, MANAGED_AGENTS, ONE_PAGER (+ PDF), HARDWARE_*, REPLAY_LOG, CROSS_RANCH_MESH, verify-latest.
- `tests/` — 880+ tests, 80%+ coverage target.

## Build commands

- `make demo SEED=42 SCENARIO=all` — runs all 5 sim scenarios back-to-back, byte-identical across runs.
- `make dashboard` — FastAPI + SSE + built SPA at `http://localhost:8000/`.
- `make hardware-demo` — 60-second Pi + Mavic hero + sick-cow combo.
- `make mesh-smoke` — 5-agent mesh smoke test (stubs SDK if no ANTHROPIC_API_KEY).
- `make test` — full pytest suite with coverage.
- `make ci` — lint + typecheck + test (what GitHub Actions runs).

## Judge Quickstart (3 commands)

```bash
git clone https://github.com/george11642/skyherd-engine && cd skyherd-engine
uv sync && (cd web && pnpm install && pnpm run build)
make demo SEED=42 SCENARIO=all         # 5 scenarios, deterministic replay
make dashboard                          # http://localhost:8000
```

---

> **Read this file first, then read the plan, then start building.**

You are helping George build **SkyHerd Engine** — a hackathon submission for Built with Opus 4.7 (Apr 21–26 2026). This file is the fast-loader for any Claude session picking up this repo.

## TL;DR

SkyHerd is the "operating system for remote land assets" — a 5-layer nervous system for American ranches. This repo is the hackathon submission artifact. You're building a **simulated ranch** that Claude Managed Agents monitor 24/7.

## Read these, in order

1. **The plan (authoritative)**: `/home/george/.claude/plans/update-ur-memory-project-context-splendid-swan.md` — v5.1, locked Apr 21 2026. Contains tier structure, Sim Completeness Gate, 5 demo scenarios, day-by-day execution plan, judging strategy, Extended Vision.
2. **The vision (reference, NOT submission)**: `/home/george/projects/active/drone/VISION.md` — full SkyHerd thesis. Do NOT copy code from this sibling repo; all hackathon code is new per the rules.
3. **Auto-memory index**: `/home/george/.claude/projects/-home-george-projects-active-drone/memory/MEMORY.md` — loaded in your context at session start. Notable: `project_hackathon_opus47.md`, `reference_managed_agents.md`, `reference_opus46_winners.md`.

## Non-negotiable rules

- **Sim-first hardline.** MVP is 100% simulated. No hardware code until the Sim Completeness Gate passes Fri Apr 24 noon. If Gate slips, ship pure-sim and skip hardware entirely.
- **All code new.** Hackathon rule — no imports from the sibling `/home/george/projects/active/drone/` repo.
- **MIT throughout.** Avoid AGPL deps (no `ultralytics`, no `yolov12`). Use MegaDetector V6 for vision.
- **TDD.** Tests first, implementation second, per George's global CLAUDE.md and `tdd-guide` skill.
- **Skills-first architecture.** Domain knowledge goes in `skills/*.md`, not in long agent system prompts. This is the CrossBeam $50k winner pattern.
- **No Claude/Anthropic attribution in commits.** Global git config disables it.

## The 5 demo scenarios to make playable

1. **Coyote at fence** — FenceLineDispatcher → SITL drone → deterrent → Wes voice call
2. **Sick cow flagged** — HerdHealthWatcher spots lameness/pinkeye → Doc escalation → vet-intake packet
3. **Water tank pressure drop** — LoRaWAN alert → drone flyover → attestation logged
4. **Calving detected** — CalvingWatch pre-labor behavior → priority rancher page
5. **Storm incoming** — Weather-Redirect → GrazingOptimizer herd-move proposal → acoustic nudge

## The 5 Managed Agents

| Agent | Trigger | Purpose |
|---|---|---|
| FenceLineDispatcher | LoRaWAN breach webhook | Classify + dispatch drone |
| HerdHealthWatcher | Camera motion / schedule | Per-animal anomaly detection |
| PredatorPatternLearner | Nightly + thermal clips | Multi-day crossing patterns |
| GrazingOptimizer | Weekly scheduled | Paddock rotation proposals |
| CalvingWatch | Seasonal Mar-Apr | Labor behavior / dystocia paging |

All share a `page_rancher(urgency, context)` tool → Twilio SMS or voice call via **"Wes"** cowboy persona.

## Sim Completeness Gate (from plan)

All 10 items are TRULY-GREEN as of Apr 22 2026 (see `docs/verify-latest.md`).

- [x] All 5 Managed Agents live and cross-talking via shared MQTT
- [x] All 7+ sim sensors emitting (water / trough cam / thermal / fence motion / collar GPS+IMU / acoustic emitter / weather)
- [x] Disease-detection heads running on synthetic frames (pinkeye / screwworm / foot rot / BRD / LSD / heat stress / BCS)
- [x] ArduPilot SITL drone executing real MAVLink missions from agent tool calls
- [x] Dashboard: ranch map + 5 agent log lanes + cost ticker + attestation panel + rancher phone PWA
- [x] Wes voice end-to-end: Twilio → ElevenLabs → cowboy persona lands
- [x] 5 scenarios playable back-to-back without intervention
- [x] Deterministic replay (`make sim SEED=42`)
- [x] Fresh-clone `make sim` boots on a second machine
- [x] Cost ticker visibly pauses during idle stretches

## Stack decisions (from plan)

- **Python 3.11+** with `uv` package manager
- **pytest + pytest-asyncio** for tests; **ruff + pyright** for lint + types
- **Claude Agent SDK + Managed Agents** (beta header `managed-agents-2026-04-01`)
- **ChirpStack** (LoRaWAN) + **Mosquitto** (MQTT broker)
- **ArduPilot SITL + MAVSDK-Python** for drone (Tier 1 baseline)
- **MegaDetector V6** for vision (MIT, NOT Ultralytics AGPL trap)
- **Vite + React 19 + Tailwind v4** for dashboard
- **Twilio + ElevenLabs** for Wes voice
- **SQLite + Ed25519** for attestation chain (not blockchain — keep serious)

## Submission deadline

**Sun Apr 26 2026, 8pm EST.** Aim for 6pm EST submit with 2hr buffer.

Required:
- 3-min demo video (YouTube unlisted)
- GitHub repo link (this repo)
- 100–200 word written summary

## When in doubt

Read the plan. It answers most questions. **Plan > this file > vision doc > your own judgment.**
