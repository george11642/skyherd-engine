# CLAUDE.md — SkyHerd Engine Fast-Loader

## TL;DR
SkyHerd = 5-layer nervous system for American ranches. Submission for **Built with Opus 4.7** hackathon. Deterministic ranch simulator + 5-agent Claude Managed Agents mesh. Sim-first; hardware is bonus.

**Deadline:** Sun Apr 26 2026 8pm EST (target 6pm EST submit). Deliver: 3-min unlisted YouTube demo, repo URL, 100–200 word summary.

## Reading order
1. `docs/ONE_PAGER.md` — what SkyHerd is in 500 words
2. `docs/ARCHITECTURE.md` — 5-layer nervous-system + Skills-first + attestation chain
3. `docs/MANAGED_AGENTS.md` — why the 5-agent mesh wins Managed Agents $5k
4. `PROGRESS.md` — live status + Sim Gate
5. `docs/verify-latest.md` — automated truth-check
6. `docs/CLAUDE_CONTEXT.md` — deep context (stack, conventions, architecture detail)
7. `docs/HARDWARE_DEMO_RUNBOOK.md` — 60-sec hardware hero demo
8. `docs/HARDWARE_PI_FLEET.md` — Pi + Galileo topology (Pi camera edge + Galileo Gen 1 telemetry node, no DIY collar)
9. `docs/HARDWARE_GALILEO.md` — Intel Galileo Gen 1 `edge-tank` runbook (water tank + weather)
10. `docs/ATTESTATION.md` — Year-2 attestation walkthrough (judge-facing): `skyherd-verify` CLI, `/attest/:hash` viewer, memver pairing, rotation
11. **Plan (authoritative):** `/home/george/.claude/plans/update-ur-memory-project-context-splendid-swan.md` — v5.1, locked Apr 21 2026

## Non-negotiable rules
- **Sim-first hardline** — no hardware code until Sim Gate passes (PASSED Apr 22 — see `docs/verify-latest.md`)
- **All code new** — no imports from `/home/george/projects/active/drone/` (sibling repo is reference-only)
- **MIT throughout** — zero AGPL deps (no Ultralytics / YOLOv12). MegaDetector V6 for vision
- **TDD** — tests first, 80%+ coverage floor (`fail_under = 80` in `pyproject.toml`)
- **Skills-first** — domain knowledge in `skills/*.md`, not in agent system prompts (CrossBeam pattern)
- **Prompt caching mandatory** — every `messages.create` / `sessions.events.send` emits `cache_control: ephemeral` on system + skills prefix
- **Beta header** — `managed-agents-2026-04-01` auto-applied by SDK on `client.beta.*` — do not override
- **No attribution in commits** — global git config enforces
- **Determinism** — `make demo SEED=42 SCENARIO=all` byte-identical across replays (after wall-timestamp sanitization)

## Quickstart (judges)
```bash
git clone https://github.com/george11642/skyherd-engine && cd skyherd-engine
uv sync && (cd web && pnpm install && pnpm run build)
make demo SEED=42 SCENARIO=all    # 5 scenarios, deterministic replay
make dashboard                     # http://localhost:8000
```

## Build commands
- `make demo SEED=42 SCENARIO=all` — all 5 sim scenarios back-to-back
- `make dashboard` — FastAPI + SSE + built SPA at `:8000`
- `make hardware-demo` — 60-sec Pi + Mavic hero combo
- `make mesh-smoke` — 5-agent mesh smoke test (stubs SDK if no `ANTHROPIC_API_KEY`)
- `make test` / `make ci` — pytest+cov / lint+typecheck+test (CI mirror)

## 5 demo scenarios
1. **Coyote at fence** — FenceLineDispatcher → SITL drone → deterrent → Wes call
2. **Sick cow** — HerdHealthWatcher → Doc escalation → vet-intake packet
3. **Water tank drop** — LoRaWAN alert → drone flyover → attestation logged
4. **Calving** — CalvingWatch pre-labor → priority rancher page
5. **Storm incoming** — Weather-Redirect → GrazingOptimizer herd-move → acoustic nudge

## 5 Managed Agents
| Agent | Trigger | Purpose |
|---|---|---|
| FenceLineDispatcher | LoRaWAN breach webhook | Classify + dispatch drone |
| HerdHealthWatcher | Camera motion / schedule | Per-animal anomaly detection |
| PredatorPatternLearner | Nightly + thermal clips | Multi-day crossing patterns |
| GrazingOptimizer | Weekly scheduled | Paddock rotation proposals |
| CalvingWatch | Seasonal Mar–Apr | Labor behavior / dystocia paging |

All share `page_rancher(urgency, context)` → Twilio SMS/voice via **"Wes"** cowboy persona.

## Directory map
- `src/skyherd/{world,sensors,agents,mcp,vision,drone,edge,attest,voice,scenarios,server,demo}/`
- `web/` Vite + React 19 + Tailwind v4 SPA (+ `/rancher` PWA)
- `android/SkyHerdCompanion/` Kotlin + DJI SDK V5 + MQTT
- `ios/SkyHerdCompanion/` Swift + DJI SDK V5 + CocoaMQTT (XcodeGen)
- `hardware/pi/` + `hardware/galileo/` one-command bringup for `edge-house` (Pi 4 camera edge) and `edge-tank` (Galileo Gen 1 telemetry)
- `hardware/collar/` optional DIY LoRa firmware (PlatformIO) + 3D print + BOM
- `skills/` 33-file ranch domain knowledge library
- `worlds/` ranch YAML (`ranch_a`, `ranch_b`) • `docs/` • `tests/` 880+ tests

## Stack (one-liner)
Python 3.11+ / uv · FastAPI + SSE · `claude-agent-sdk` 0.1.64 + `anthropic` 0.96 (`client.beta.*`, header `managed-agents-2026-04-01`) · `aiomqtt` + `amqtt` · MAVSDK + pymavlink · MegaDetector V6 · Ed25519 SQLite ledger · Twilio + ElevenLabs (Wes) · React 19 + Tailwind v4 · pytest (`asyncio_mode=auto`, 80% floor) · ruff + pyright

## Timeline (2026-04-23 Thu → 2026-04-26 Sun)
- **Thu Apr 23** — finalize software (v1.0 already closed; freeze submission branch, draft copy)
- **Fri Apr 24** — hardware integration pass (Pi + Galileo Gen 1 + Mavic via `docs/HARDWARE_PI_FLEET.md`) + **start filming**
- **Sat Apr 25** — continue filming + start preparing launch video + finalize 100–200 word summary
- **Sun Apr 26** — finalize + submit by 6pm EST (8pm EST deadline)

## When in doubt
**Plan > this file > `docs/CLAUDE_CONTEXT.md` > vision doc > your own judgment.**

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow
Before Edit/Write, start work via `/gsd-quick`, `/gsd-debug`, or `/gsd-execute-phase`. Don't make direct repo edits outside a GSD workflow unless explicitly asked to bypass.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile
> Run `/gsd-profile-user` to generate. Managed by `generate-claude-profile` — do not edit manually.
<!-- GSD:profile-end -->
