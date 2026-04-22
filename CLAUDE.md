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

<!-- GSD:project-start source:PROJECT.md -->
## Project

**SkyHerd Engine**

SkyHerd Engine is George's submission for the **"Built with Opus 4.7" Claude Code hackathon** (Apr 21–26 2026). It's a deterministic ranch simulator wrapped around a 5-agent **Claude Managed Agents** mesh that monitors a simulated American ranch 24/7 — coyote at the fence, sick cow flagged, water tank drop, calving detected, storm incoming — driving an ArduPilot SITL drone, a "Wes" cowboy voice persona, and an Ed25519-attested event ledger. The submission is 100% sim-first; hardware (Pi + Mavic + DIY LoRa collar) integrates one-piece-at-a-time in later milestones only after the Sim Completeness Gate passes.

**Core Value:** **The 3-minute demo video must land "oh damn" inside the first 30 seconds on a pure-sim run, deterministically, every replay.** Hardware is bonus; narrative credibility with Anthropic-team judges (Mike Brown / Thariq Shihipar / Michael Cohen lineage) is not. If anything else fails — but sim plays cleanly, agents *actually* persist across events, vision has real-enough pixel inference to withstand inspection, and the cost ticker demonstrably pauses on idle — we ship.

### Constraints

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
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.11+ — all backend, sensors, agents, drone, attestation, voice
- TypeScript 5.8 — React SPA dashboard (`web/`)
- Kotlin 2.0 — Android companion app (`android/SkyHerdCompanion/`)
- Swift — iOS companion app (`ios/SkyHerdCompanion/`) — directory exists, not verified beyond scaffold
## Runtime
- Python 3.11+ (matrix-tested against 3.11 and 3.12 in CI)
- Node 20 (web build), pnpm 9
- Python: `uv` with hatchling build backend
- Lockfile: `uv.lock` — present and resolves to PyPI packages (not git sources)
- Web: `pnpm` — lockfile `web/pnpm-lock.yaml` present
## Frameworks
- FastAPI 0.136.0 — HTTP API + SSE (`src/skyherd/server/app.py`)
- uvicorn 0.45.0 — ASGI server with `[standard]` extras
- sse-starlette — SSE EventSourceResponse for `/events` endpoint
- React 19.1.0 — SPA dashboard (`web/src/`)
- Vite 6.3.5 — frontend build tool (`web/vite.config.ts`)
- Tailwind v4.1.7 — CSS utility framework (via `@tailwindcss/vite` plugin)
- pytest 8 + pytest-asyncio 0.24 — `asyncio_mode = "auto"` in pyproject.toml
- pytest-cov — 80% floor enforced (`fail_under = 80`)
- 111 test files across `tests/`
- Vitest 3.2.3 with `@vitest/coverage-v8`
- `@testing-library/react` 16.3.0
- ruff — lint + format (`line-length = 100`, `target-version = "py311"`)
- pyright — type checking
- pre-commit hooks present
## Key Dependencies
- `anthropic` 0.96.0 — Anthropic SDK (supports `client.beta.*`)
- `claude-agent-sdk` 0.1.64 — Claude Agent SDK from PyPI (uploaded 2026-04-20); provides `McpSdkServerConfig`, `create_sdk_mcp_server`, `tool` decorator — used in all 4 MCP servers
- `aiomqtt` 2.x — async MQTT client (persistent publish client in `SensorBus`)
- `amqtt` — embedded MQTT broker used when `MQTT_URL` env var is unset
- `mavsdk` 3.15.3 — MAVSDK-Python for ArduPilot SITL (`SitlBackend`)
- `pymavlink` — alternative MAVLink backend (`pymavlink_backend.py`)
- `pydantic` 2.x — data models throughout
- `cryptography` 42-44 — Ed25519 signing in attestation chain (`src/skyherd/attest/signer.py`)
- `elevenlabs` 2.44.0 — TTS SDK (`ElevenLabsBackend` in `src/skyherd/voice/tts.py`)
- `twilio` 9.10.5 — voice calls via `client.calls.create()` in `src/skyherd/voice/call.py`)
- `pillow` — image rendering (synthetic frames)
- `numpy` 1.26+ — thermal frame generation, disease head thresholds
- `supervision` 0.20+ — referenced in `.refs/` and optional `edge` extra; used for detection result parsing in `MegaDetectorHead`
- `PytorchWildlife` — `edge` optional extra; lazy-imported in `MegaDetectorHead` (`src/skyherd/edge/detector.py:107`)
- `react` 19.1.0, `react-dom` 19.1.0
- `framer-motion` 12.38.0 — animations
- `lucide-react` 0.511.0 — icons
- `tailwind-merge`, `clsx` — CSS utilities
- DJI Mobile SDK V5 5.8.0 (`dji-sdk-v5-aircraft`, `dji-sdk-v5-networkImp`)
- OkHttp 4.12 — WebSocket transport
- Eclipse Paho MQTT 1.2.5 — MQTT client
## Configuration
- `.env.example` documents all required vars (see INTEGRATIONS.md)
- `python-dotenv` loaded at runtime; `SKYHERD_MOCK=1` for demo-without-hardware mode
- Key routing env vars: `SKYHERD_AGENTS=managed|local` (default auto), `DRONE_BACKEND=sitl|mavlink`
- `pyproject.toml` — build system, deps, pytest config, coverage, ruff config
- `web/vite.config.ts` — Vite/React/Tailwind build
- `android/SkyHerdCompanion/gradle/libs.versions.toml` — Android versions
## Platform Requirements
- Python 3.11+ via uv
- Node 20 + pnpm 9 for web
- Optional: Docker for SITL (`docker-compose.sitl.yml` referenced in CI)
- Optional: ArduPilot SITL on UDP port 14540 for real drone sim
- Raspberry Pi 4 (`src/skyherd/edge/`) for edge runtime
- Android device with DJI Mavic Air 2 (`android/SkyHerdCompanion/`)
- Mosquitto MQTT broker (or embedded amqtt)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Python Style Tooling
- Line length: 100 characters
- Target version: Python 3.11
- Rule sets: `E`, `F`, `I`, `B`, `UP`, `N` (pep8, flake8, isort, bugbear, pyupgrade, pep8-naming)
- `E501` (line-length) ignored for docstrings
- `.refs/` directory excluded from lint entirely
- Test files get lenient ignores: `S101`, `B017`, `B905`, `E741`, `F841`, `N806`, `UP017`
- Current status: 15 errors, 6 warnings (all in hardware-specific files)
- Core application code (agents, sensors, scenarios, world) passes cleanly
## Naming Patterns
- Python modules: `snake_case.py` — `fenceline_dispatcher.py`, `herd_health_watcher.py`, `sitl_emulator.py`
- Test files: `test_<module_name>.py` — mirrors source structure exactly
- Skills: `kebab-case.md` inside domain subdirectory — `skills/predator-ids/coyote.md`
- `PascalCase` throughout — `FenceMotionSensor`, `SessionManager`, `AgentSpec`, `SkyHerdSSE`
- Exceptions: `PascalCase` ending in `Error` or using established names — `DroneUnavailable`, `GeofenceViolation`
- `snake_case` for all functions — `get_bus_state()`, `build_cached_messages()`, `_mqtt_topic_matches()`
- Private helpers prefixed with `_` — `_simulate_handler()`, `_iso()`, `_load_text()`
- Boolean-returning helpers: `is_`/`has_`/`can_` prefix not enforced; some use plain names (`fence_breached_by`)
- `snake_case` — `session_id`, `wake_event`, `ranch_id`
- Module-level constants: `UPPER_SNAKE_CASE` — `_DEFAULT_BROKER_PORT`, `_DEBOUNCE_S`, `_STEP_DT`
- Exported spec constants: all-caps no underscore prefix — `FENCELINE_DISPATCHER_SPEC`
- Components: `PascalCase` — `AgentLane`, `CostTicker`, `AttestationPanel`
- Props interfaces: `{ComponentName}Props` — `AgentLaneProps`, `AgentLaneProps`
- Utility files: `camelCase.ts` — `cn.ts`, `sse.ts`, `replay.ts`
- Constants/records: `UPPER_SNAKE_CASE` — `AGENT_SHORT`, `MAX_SPARKLINE`
## Typing Discipline
- `from __future__ import annotations` used in 88 of 101 source files — near-universal
- `TYPE_CHECKING` guards for circular imports — standard pattern:
- Return types on all public functions — `async def tick(self) -> None`
- `Any` used sparingly and only where truly necessary (`sdk_client: Any`, `wake_event: dict[str, Any]`)
- `type: ignore[assignment]` used 5 times for `tuple()` casts where pymavlink types don't have stubs
- No bare `type: ignore` without inline justification comment
- Strict mode via `tsconfig.json` (inferred from `tsc -b` in build)
- All component props explicitly typed with named interfaces
- `any` appears only twice in `src/lib/sse.ts` with `// eslint-disable-next-line` comments
- Shared interfaces defined at component level (`AgentCost`, `CostTickPayload`)
- No `React.FC` usage — plain function components throughout
## Import Organization
- Path alias `@` maps to `web/src/` — configured in `vite.config.ts`
- All imports use `@/` prefix for internal modules: `import { cn } from "@/lib/cn"`
- External packages first, then `@/` internal
## Async/Await Usage
- `asyncio.mode = "auto"` in pytest — all `async def test_*` functions run without `@pytest.mark.asyncio` decorator
- Sensor base class pattern: `async def tick(self) -> None` + `async def run(self) -> None` (cancelable loop)
- `asyncio.CancelledError` explicitly re-raised in sensor loops — not swallowed
- SSE server uses async generators for event streaming (`src/skyherd/server/events.py`)
- `asynccontextmanager` used for resource management in bus (`src/skyherd/sensors/bus.py`)
- Background tasks via `asyncio.Task` — not bare `asyncio.create_task` without capture
## Error Handling Patterns
- `except Exception as exc:  # noqa: BLE001` — used throughout for non-fatal background tasks
- `except Exception as exc:  # noqa: BLE001` pattern signals intentional broad catch, not carelessness
- Specific exceptions raised for public API errors: `KeyError`, `FileNotFoundError`, `ValueError`
- Custom exceptions in `src/skyherd/drone/interface.py`: `DroneUnavailable`, `GeofenceViolation`, `BatteryTooLow`, `WindTooHigh`
- Internal helpers raise — callers catch or propagate
- `SessionManager._get()` raises `KeyError` with context: `raise KeyError(f"Unknown session: {session_id}") from None`
- `_load_text()` returns empty string on missing file + logs warning — never raises
- Malformed JSON silently ignored in `src/lib/sse.ts` with inline comment
- `onerror` handler drives reconnect with exponential backoff (1s → 30s cap)
## Logging
- Module-level logger: `logger = logging.getLogger(__name__)` — in every source module with logging
- No `print()` statements in library code
- Log levels used correctly: `DEBUG` for trace/lifecycle, `INFO` for state transitions, `WARNING` for anomalies/breach events, `ERROR` not used directly (caught and re-logged as `WARNING`)
- `%s`-style string formatting (not f-strings) in log calls — avoids eager evaluation
## MQTT Topic Conventions
- `skyherd/{ranch_id}/{self.topic_prefix}/{entity_id}` — computed in `Sensor.__init__` (`src/skyherd/sensors/base.py:60`)
- `skyherd/+/fence/+` — wake topic wildcard in `FENCELINE_DISPATCHER_SPEC`
- `skyherd/+/thermal/+` — thermal wake topic
- `skyherd/neighbor/+/+/predator_confirmed` — cross-ranch mesh topic
- `ts`: float timestamp (via `ts_provider`)
- `kind`: event type string (e.g., `"fence.breach"`, `"water.tank"`)
- `ranch`: ranch identifier
- `entity`: entity identifier
## Skills-First Architecture Discipline
- `skills/predator-ids/` — coyote, mountain-lion, wolf, livestock-guardian-dogs, thermal-signatures
- `skills/cattle-behavior/` — lameness, calving, disease (7 heads), feeding, herd-structure
- `skills/drone-ops/` — patrol-planning, deterrent-protocols, battery-economics, no-fly-zones
- `skills/ranch-ops/` — fence-line-protocols, human-in-loop-etiquette, paddock-rotation, part-107-rules, water-tank-sops
- `skills/nm-ecology/` — predator ranges, forage, seasonal calendar, weather patterns
- `skills/voice-persona/` — wes-register, urgency-tiers, never-panic
- `AgentSpec.skills` field lists file paths: `src/skyherd/agents/spec.py:50`
- Skills loaded at wake time via `_load_text()` and sent as `cache_control: {"type": "ephemeral"}` blocks
- Each agent has a concise inline system prompt + a `system_prompt_template_path` for the stable prompt
- Example from `src/skyherd/agents/fenceline_dispatcher.py:53-78`: 12 skill files declared — predator IDs, fence protocols, drone ops, voice persona
## Component Organization (Frontend)
- Feature components: `web/src/components/*.tsx` — co-located with `.test.tsx`
- Shared primitives: `web/src/components/shared/` — `Chip`, `MonoText`, `PulseDot`, `ScenarioStrip`, `StatBand`
- shadcn/ui primitives: `web/src/components/ui/` — `badge`, `button`, `card`, `sheet`, `table`, `tooltip`
- Utilities: `web/src/lib/` — `cn.ts` (clsx+tailwind-merge), `sse.ts`, `replay.ts`
- All components are plain functions — no class components, no `React.FC`
- `useRef` + `useEffect` for auto-scroll: `web/src/components/AgentLane.tsx:43-50`
- Framer Motion used for animated counters in `CostTicker` — not for layout transitions
- SSE data flows via global singleton `getSSE()` — no React context, just event subscriptions in `useEffect`
- CSS variables for design tokens: `var(--color-text-0)`, `var(--color-line)`, `var(--font-mono)`, `var(--font-display)`
- Utility classes mixed with inline `style` props for dynamic colors — not a clean split
- `cn()` helper (`clsx` + `tailwind-merge`) used for conditional classes
- Custom utilities defined in `web/src/index.css`: `chip`, `chip-sage`, `chip-sky`, `chip-muted`, `log-scroll`, `tabnum`, `pulse-dot`
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- MQTT-bussed sensor layer feeds a 5-agent mesh that drives drone and voice actuators
- Agents run on either a real Anthropic Managed Agents platform (`client.beta.*`) or a local shim (`SessionManager`) depending on env vars — same public API either way
- Scenarios are deterministic sim playbacks (seed=42); all randomness is seeded at world level
- All events flow through a SQLite+Ed25519 attestation ledger (append-only Merkle chain)
- Skills (domain `.md` files) are injected as `cache_control` blocks at wake time — not hardcoded in system prompts
## 5-Layer Nervous System
### Layer 1 — Sense
- `src/skyherd/sensors/bus.py` — `SensorBus`: async MQTT client with embedded `amqtt` broker fallback. Publishes to `skyherd/{ranch_id}/{kind}/{id}`. Holds a persistent `aiomqtt.Client`; module-level `_BUS_STATE` ring buffer (deque, 256 entries per kind) for MCP sensor reads.
- `src/skyherd/sensors/water.py` — water tank level emitter
- `src/skyherd/sensors/fence.py` — fence motion emitter
- `src/skyherd/sensors/collar.py` — GPS+IMU collar emitter
- `src/skyherd/sensors/thermal.py` — thermal camera emitter
- `src/skyherd/sensors/trough_cam.py` — trough camera emitter
- `src/skyherd/sensors/acoustic.py` — acoustic emitter
- `src/skyherd/sensors/weather.py` — weather emitter
- `src/skyherd/sensors/base.py` — `BaseSensor` ABC
- `src/skyherd/sensors/registry.py` — sensor registry
- `src/skyherd/edge/camera.py` — `Camera` + `get_camera()` factory (picamera2 or stub)
- `src/skyherd/edge/detector.py` — `Detector` + `MegaDetectorHead` (PytorchWildlife)
- `src/skyherd/edge/watcher.py` — `EdgeWatcher`: async capture/detect/publish loop; reads CPU temp from `/sys/class/thermal/`; heartbeat at `_DEFAULT_HEALTHZ_PORT = 8787`
### Layer 2 — See
- `src/skyherd/vision/renderer.py` — `render_trough_frame()` + `annotate_frame()`: generates synthetic PNG frames from `World` state
- `src/skyherd/vision/heads/base.py` — `DiseaseHead` ABC with `classify(frame_meta) → DetectionResult`
- `src/skyherd/vision/heads/pinkeye.py`, `screwworm.py`, `foot_rot.py`, `brd.py`, `lsd.py`, `heat_stress.py`, `bcs.py` — 7 disease detection heads (rule-based on sensor metadata; no actual CNN weight loading)
- `src/skyherd/vision/registry.py` — `classify(frame_meta) → list[DetectionResult]` dispatcher
- `src/skyherd/vision/pipeline.py` — `ClassifyPipeline.run(world, trough_id)`: render frame → classify all cows → annotate → return `PipelineResult`
- `src/skyherd/vision/result.py` — `DetectionResult` dataclass
### Layer 3 — Respond
- `src/skyherd/agents/spec.py` — `AgentSpec` dataclass: `name`, `system_prompt_template_path`, `wake_topics` (MQTT patterns), `mcp_servers`, `skills`, `model`
- `src/skyherd/agents/session.py` — `SessionManager` (local shim): `create_session()`, `sleep()`, `wake()`, `checkpoint()`, `on_webhook()`. Models Managed Agents semantics — cost meter pauses when `state == "idle"`. `build_cached_messages()` emits `cache_control: {"type": "ephemeral"}` blocks for system prompt + each skill file.
- `src/skyherd/agents/managed.py` — `ManagedSessionManager`: real `client.beta.agents/sessions/environments.*` calls. Persists agent IDs in `runtime/agent_ids.json`, env ID in `runtime/ma_environment_id.txt`. **Real platform agents provisioned** (verified: 5 agent IDs present).
- `src/skyherd/agents/_handler_base.py` — `run_handler_cycle()`: selects managed SSE stream path vs local `messages.create()` path vs simulation path based on `SKYHERD_AGENTS` env and `platform_session_id` presence.
- `src/skyherd/agents/mesh.py` — `AgentMesh`: starts all 5 sessions, runs cost-tick loop, runs `_mqtt_loop()` subscriber, routes events to handlers.
| Agent | File | Wake Topics | Model |
|-------|------|-------------|-------|
| FenceLineDispatcher | `src/skyherd/agents/fenceline_dispatcher.py` | `skyherd/+/fence/+`, `skyherd/+/thermal/+`, `skyherd/neighbor/+/+/predator_confirmed` | claude-opus-4-7 |
| HerdHealthWatcher | `src/skyherd/agents/herd_health_watcher.py` | `skyherd/+/trough_cam/+`, cron | claude-opus-4-7 |
| PredatorPatternLearner | `src/skyherd/agents/predator_pattern_learner.py` | `skyherd/+/thermal/+`, nightly | claude-opus-4-7 |
| GrazingOptimizer | `src/skyherd/agents/grazing_optimizer.py` | `skyherd/+/cron/weekly_monday` | claude-opus-4-7 |
| CalvingWatch | `src/skyherd/agents/calving_watch.py` | `skyherd/+/collar/+`, activity spikes | claude-opus-4-7 |
- `ManagedSessionManager` uses `client.beta.agents.create()`, `client.beta.sessions.create()`, `client.beta.environments.create()` — genuine beta SDK calls, not stubs.
- Beta header `managed-agents-2026-04-01` is applied automatically by the SDK on `client.beta.*` calls (documented in `managed.py` line 8-9).
- The MCP tools are wired via `claude_agent_sdk.McpSdkServerConfig` + `create_sdk_mcp_server` — package installed and imports verified.
- In practice, each agent has an `AgentSpec` (not an SDK `Agent` subclass). Handlers are async Python functions, not MA-native agent definitions. The "managed" path sends wake events to the platform via `client.beta.sessions.events.send()` and streams responses via `client.beta.sessions.events.stream()`.
- **Runtime evidence:** `runtime/agent_ids.json` contains 5 provisioned agent IDs; `runtime/ma_environment_id.txt` contains a live env ID — confirming real platform registration has occurred.
### Layer 4 — Intervene
- `src/skyherd/drone/stub.py` — `StubBackend`: in-memory log only (CI/tests)
- `src/skyherd/drone/sitl.py` — `SitlBackend`: real MAVLink via `mavsdk.System`, connects to UDP 14540, full mission upload/execute. Generates synthetic thermal PNGs via NumPy+Pillow.
- `src/skyherd/drone/sitl_emulator.py` — pure-Python SITL emulator (no Docker required)
- `src/skyherd/drone/mavic.py` — `MavicBackend`: WebSocket bridge to Android companion app
- `src/skyherd/drone/f3_inav.py` — `F3InavBackend`: pymavlink serial bridge (F3 flight controller)
- `src/skyherd/drone/safety.py` — `SafetyGuard`: geofence, battery floor, wind limit enforcement
- `src/skyherd/drone/interface.py` — `get_backend()` factory: reads `DRONE_BACKEND` env var
- `src/skyherd/voice/wes.py` — `WesMessage` + `wes_script()`: template-based cowboy persona composer with AI-telltale scrub
- `src/skyherd/voice/tts.py` — TTS backend factory (ElevenLabs → piper → espeak → silent fallback)
- `src/skyherd/voice/call.py` — `render_urgency_call()`: full pipeline WesMessage → WAV → deliver. Delivery priority: Twilio voice call (if `TWILIO_SID`+`CLOUDFLARE_TUNNEL_URL` set) → dashboard ring (`runtime/phone_rings.jsonl`) → log-only.
- `src/skyherd/mcp/drone_mcp.py` — tools: `launch_drone`, `return_to_home`, `play_deterrent`, `get_thermal_clip`, `drone_status`
- `src/skyherd/mcp/sensor_mcp.py` — tools: read from `_BUS_STATE` ring buffer
- `src/skyherd/mcp/rancher_mcp.py` — tools: `page_rancher` → calls `render_urgency_call()`
- `src/skyherd/mcp/galileo_mcp.py` — tools: cross-ranch mesh coordination
### Layer 5 — Defend
- `src/skyherd/attest/ledger.py` — `Ledger`: SQLite WAL, Blake2b-256 hash chain, Ed25519 signatures per row. `append()` is atomic; `verify()` walks full chain.
- `src/skyherd/attest/signer.py` — `Signer`: Ed25519 key pair generation + sign/verify
- Every `SensorBus.publish()` call optionally mirrors to ledger if `ledger=` kwarg supplied
- Every scenario run appends events to ledger
- `_simulate_neighbor_handler()` handles `neighbor_alert` events from `skyherd/neighbor/+/+/predator_confirmed` topics
- FenceLineDispatcher spec includes cross-ranch wake topic; pre-positions drone without paging rancher
## Data Flow
### Primary Cascade (Coyote scenario)
### Dashboard Flow
## Entry Points
- Invokes `skyherd-demo play all --seed 42`
- CLI: `src/skyherd/scenarios/cli.py`
- Runs all 5 scenarios back-to-back via `Scenario.run()` in `src/skyherd/scenarios/base.py`
- Seeds `World` from YAML config `worlds/ranch_a.yaml`; deterministic replay guaranteed
- Builds Vite SPA (`web/`), then `uvicorn skyherd.server.app:app --port 8000` with `SKYHERD_MOCK=1`
- App factory: `src/skyherd/server/app.py`
- Mock mode: no live mesh/bus required; `EventBroadcaster` generates mock data
- Invokes `skyherd-mesh mesh smoke --verbose`
- CLI: `src/skyherd/agents/cli.py`
- `AgentMesh.smoke_test()`: fires one synthetic wake event per agent; simulation path runs without API key
- Invokes `skyherd-demo-hw play --prop combo`
- CLI: `src/skyherd/demo/cli.py`
- Orchestrator: `src/skyherd/demo/hardware_only.py`
- Sets `DRONE_BACKEND=mavic`; subscribes to Pi-owned trough_cam MQTT topics; 180s timeout before fallback to sim
## Error Handling
- Agent handlers: simulation path if no `ANTHROPIC_API_KEY` or `sdk_client is None`
- `ManagedSessionManager` init: raises `ManagedAgentsUnavailable` if no API key; `get_session_manager()` catches and falls back to local
- Drone backends: `DroneUnavailable` / `DroneTimeoutError` exceptions; `SafetyGuard` raises `GeofenceViolation` / `BatteryTooLow`
- Voice: TTS chain waterfall (ElevenLabs → piper → espeak → silent)
- MQTT: embedded `amqtt` broker starts automatically if `MQTT_URL` not set; reconnect with exponential backoff (1s → 30s cap)
- Hardware demo: 180s timeout → fallback coyote sim scenario; logs `PROP_NOT_DETECTED`
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
