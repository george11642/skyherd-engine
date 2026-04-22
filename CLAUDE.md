# CLAUDE.md — Project Orientation

## Judge Quickstart (3 commands)

```bash
git clone https://github.com/george11642/skyherd-engine && cd skyherd-engine
uv sync && (cd web && pnpm install && pnpm run build)
make demo SEED=42 SCENARIO=all         # 5 scenarios, deterministic replay
make dashboard                          # http://localhost:8000
```

Read in order: docs/ONE_PAGER.md → docs/ARCHITECTURE.md → docs/MANAGED_AGENTS.md.

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

## What's in this repo right now

Empty directory skeleton + README + LICENSE + .gitignore + this orientation. The fresh Claude session picking this up builds the MVP from here.

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

No hardware touches the repo until all of these are green. **Target: Fri Apr 24 noon.**

- [ ] All 5 Managed Agents live and cross-talking via shared MQTT
- [ ] All 7+ sim sensors emitting (water / trough cam / thermal / fence motion / collar GPS+IMU / acoustic emitter / weather)
- [ ] Disease-detection heads running on synthetic frames (pinkeye / screwworm / foot rot / BRD / LSD / heat stress / BCS)
- [ ] ArduPilot SITL drone executing real MAVLink missions from agent tool calls
- [ ] Dashboard: ranch map + 5 agent log lanes + cost ticker + attestation panel + rancher phone PWA
- [ ] Wes voice end-to-end: Twilio → ElevenLabs → cowboy persona lands
- [ ] 5 scenarios playable back-to-back without intervention
- [ ] Deterministic replay (`make sim SEED=42`)
- [ ] Fresh-clone `make sim` boots on a second machine

## Stack decisions (from plan)

- **Python 3.11+** with `uv` package manager
- **pytest + pytest-asyncio** for tests; **ruff + pyright** for lint + types
- **Claude Agent SDK + Managed Agents** (beta header `managed-agents-2026-04-01`)
- **ChirpStack** (LoRaWAN) + **Mosquitto** (MQTT broker)
- **ArduPilot SITL + MAVSDK-Python** for drone (Tier 1 baseline)
- **MegaDetector V6** for vision (MIT, NOT Ultralytics AGPL trap)
- **Next.js + shadcn/Tailwind** for dashboard (CrossBeam aesthetic)
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
