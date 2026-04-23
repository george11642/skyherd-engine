# CLAUDE_CONTEXT.md — Deep Project Context

> Detailed stack, conventions, and architecture for Claude sessions that need more than the fast-loader in `CLAUDE.md`. Portions are GSD-auto-generated — regenerate via `/gsd-docs-update`.

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

### Languages
- Python 3.11+ — all backend, sensors, agents, drone, attestation, voice
- TypeScript 5.8 — React SPA dashboard (`web/`)
- Kotlin 2.0 — Android companion app (`android/SkyHerdCompanion/`)
- Swift — iOS companion app (`ios/SkyHerdCompanion/`) — scaffold

### Runtime
- Python 3.11+ (matrix-tested 3.11 and 3.12 in CI), `uv` + hatchling, `uv.lock`
- Node 20 + pnpm 9 for web (`web/pnpm-lock.yaml`)

### Frameworks
- FastAPI 0.136.0 + uvicorn 0.45.0 + sse-starlette (`src/skyherd/server/app.py`)
- React 19.1.0 + Vite 6.3.5 + Tailwind v4.1.7 (via `@tailwindcss/vite`)
- pytest 8 + pytest-asyncio 0.24 (`asyncio_mode = "auto"`), pytest-cov `fail_under = 80`, 111 test files
- Vitest 3.2.3 + `@vitest/coverage-v8` + `@testing-library/react` 16.3.0
- ruff (`line-length = 100`, `target-version = "py311"`) + pyright, pre-commit hooks

### Key Python Dependencies
- `anthropic` 0.96.0 — `client.beta.*` path
- `claude-agent-sdk` 0.1.64 — `McpSdkServerConfig`, `create_sdk_mcp_server`, `tool` decorator (all 4 MCP servers)
- `aiomqtt` 2.x (persistent publish client in `SensorBus`) + `amqtt` (embedded broker when `MQTT_URL` unset)
- `mavsdk` 3.15.3 (`SitlBackend`) + `pymavlink` (`pymavlink_backend.py`)
- `pydantic` 2.x, `cryptography` 42-44 (Ed25519 in `src/skyherd/attest/signer.py`)
- `elevenlabs` 2.44.0 (`ElevenLabsBackend`), `twilio` 9.10.5 (`client.calls.create()` in `src/skyherd/voice/call.py`)
- `pillow`, `numpy` 1.26+, `supervision` 0.20+, `PytorchWildlife` (edge extra, lazy-imported `src/skyherd/edge/detector.py:107`)

### Key Web Dependencies
- `react` / `react-dom` 19.1.0, `framer-motion` 12.38.0, `lucide-react` 0.511.0, `tailwind-merge`, `clsx`

### Android Dependencies
- DJI Mobile SDK V5 5.8.0 (`dji-sdk-v5-aircraft`, `dji-sdk-v5-networkImp`), OkHttp 4.12, Eclipse Paho MQTT 1.2.5

### Configuration
- `.env.example` documents required vars (see `INTEGRATIONS.md`)
- `python-dotenv` at runtime; `SKYHERD_MOCK=1` for demo-without-hardware
- Routing env: `SKYHERD_AGENTS=managed|local` (default auto), `DRONE_BACKEND=sitl|mavlink|mavic|stub|f3_inav`

### Platform Requirements
- Python 3.11+ via uv; Node 20 + pnpm 9 for web
- Optional: Docker for SITL (`docker-compose.sitl.yml`), ArduPilot SITL UDP 14540
- Optional: Raspberry Pi 4, Android + DJI Mavic Air 2, Mosquitto broker (or embedded amqtt)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

### Python Style
- Line length 100, target py311, rule sets `E,F,I,B,UP,N`, `E501` ignored in docstrings, `.refs/` excluded
- Test files lenient ignores: `S101,B017,B905,E741,F841,N806,UP017`
- Core app code (agents, sensors, scenarios, world) passes cleanly; 15 errors/6 warnings remain in hardware-specific files

### Naming
- Python modules `snake_case.py`; tests `test_<module>.py` mirror source tree
- Skills `kebab-case.md` under domain subdir (`skills/predator-ids/coyote.md`)
- Classes `PascalCase`; functions `snake_case`; private `_prefix`; module constants `UPPER_SNAKE_CASE`; spec constants all-caps no prefix (`FENCELINE_DISPATCHER_SPEC`)
- React components `PascalCase`; props `{Component}Props`; utils `camelCase.ts`

### Typing
- `from __future__ import annotations` in 88/101 source files
- `TYPE_CHECKING` guards for cycles; return types on all public funcs; `Any` sparingly
- 5 `type: ignore[assignment]` for pymavlink tuple casts (no stubs)
- TS strict mode; named props interfaces; no `React.FC`; `any` only twice in `src/lib/sse.ts` with eslint-disable

### Async
- `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed
- Sensor pattern: `async def tick()` + `async def run()` cancelable loop; `CancelledError` re-raised
- SSE via async generators (`src/skyherd/server/events.py`)
- `asynccontextmanager` for `SensorBus` resources; background tasks captured as `asyncio.Task`

### Error Handling
- `except Exception as exc:  # noqa: BLE001` throughout for non-fatal background tasks
- Custom drone exceptions: `DroneUnavailable`, `GeofenceViolation`, `BatteryTooLow`, `WindTooHigh` (`src/skyherd/drone/interface.py`)
- `SessionManager._get()` raises `KeyError` with context; `_load_text()` returns empty + logs WARNING on missing
- SSE client: malformed JSON silently ignored; `onerror` reconnect exponential backoff 1s→30s

### Logging
- Module-level `logger = logging.getLogger(__name__)`; no `print()` in libs
- `DEBUG` lifecycle, `INFO` state transitions, `WARNING` anomalies/breach; `ERROR` not used directly
- `%s`-style formatting (lazy evaluation)

### MQTT Topic Conventions
- Publish: `skyherd/{ranch_id}/{topic_prefix}/{entity_id}` (computed in `Sensor.__init__` at `src/skyherd/sensors/base.py:60`)
- Wake wildcards: `skyherd/+/fence/+`, `skyherd/+/thermal/+`
- Cross-ranch mesh: `skyherd/neighbor/+/+/predator_confirmed`
- Payload fields: `ts` (float), `kind`, `ranch`, `entity`

### Skills-First Discipline
- Domains: `predator-ids/`, `cattle-behavior/`, `drone-ops/`, `ranch-ops/`, `nm-ecology/`, `voice-persona/`
- `AgentSpec.skills` lists paths (`src/skyherd/agents/spec.py:50`); loaded at wake via `_load_text()` and sent as `cache_control: {"type": "ephemeral"}`
- Example: `fenceline_dispatcher.py:53-78` declares 12 skill files

### Frontend Organization
- Features `web/src/components/*.tsx` co-located with `.test.tsx`
- Shared `web/src/components/shared/` (`Chip`, `MonoText`, `PulseDot`, `ScenarioStrip`, `StatBand`)
- shadcn/ui in `web/src/components/ui/` (`badge`, `button`, `card`, `sheet`, `table`, `tooltip`)
- Utils `web/src/lib/` (`cn.ts`, `sse.ts`, `replay.ts`)
- Plain function components; `useRef`+`useEffect` for auto-scroll; Framer Motion for counters only
- SSE via global `getSSE()` singleton + `useEffect` subscriptions (no Context)
- CSS variables for tokens (`--color-text-0`, `--color-line`, `--font-mono`, `--font-display`)
- Custom utilities in `web/src/index.css`: `chip`, `chip-sage`, `chip-sky`, `chip-muted`, `log-scroll`, `tabnum`, `pulse-dot`
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

### Pattern Overview
- MQTT-bussed sensor layer → 5-agent mesh → drone + voice actuators
- Agents run on real Anthropic Managed Agents (`client.beta.*`) or local shim (`SessionManager`) — same public API
- Scenarios are deterministic sim playbacks (seed=42), all randomness seeded at world level
- Events flow through SQLite+Ed25519 attestation ledger (append-only Merkle chain)
- Skills (`.md` files) injected as `cache_control` blocks at wake time — NOT hardcoded in system prompts

### 5-Layer Nervous System

**Layer 1 — Sense**
- `src/skyherd/sensors/bus.py` — `SensorBus`: async MQTT client + embedded `amqtt` fallback. Persistent `aiomqtt.Client`; module-level `_BUS_STATE` ring buffer (deque, 256 entries per kind) for MCP sensor reads
- Emitters: `water.py`, `fence.py`, `collar.py`, `thermal.py`, `trough_cam.py`, `acoustic.py`, `weather.py`; `base.py` ABC; `registry.py`
- `src/skyherd/edge/camera.py` — `Camera` + `get_camera()` factory (picamera2 or stub)
- `src/skyherd/edge/detector.py` — `Detector` + `MegaDetectorHead` (PytorchWildlife)
- `src/skyherd/edge/watcher.py` — `EdgeWatcher`: async capture/detect/publish loop; reads CPU temp from `/sys/class/thermal/`; heartbeat at `_DEFAULT_HEALTHZ_PORT = 8787`

**Layer 2 — See**
- `src/skyherd/vision/renderer.py` — `render_trough_frame()` + `annotate_frame()`: synthetic PNG frames from `World`
- `src/skyherd/vision/heads/{base,pinkeye,screwworm,foot_rot,brd,lsd,heat_stress,bcs}.py` — 7 disease heads (rule-based on sensor metadata)
- `src/skyherd/vision/registry.py` — `classify(frame_meta) → list[DetectionResult]` dispatcher
- `src/skyherd/vision/pipeline.py` — `ClassifyPipeline.run(world, trough_id)`: render → classify → annotate → `PipelineResult`

**Layer 3 — Respond**
- `src/skyherd/agents/spec.py` — `AgentSpec`: `name`, `system_prompt_template_path`, `wake_topics`, `mcp_servers`, `skills`, `model`
- `src/skyherd/agents/session.py` — local `SessionManager`: `create_session/sleep/wake/checkpoint/on_webhook`. Models MA semantics — cost pauses when `state == "idle"`. `build_cached_messages()` emits `cache_control: ephemeral` on system + each skill
- `src/skyherd/agents/managed.py` — `ManagedSessionManager`: real `client.beta.agents/sessions/environments.*`. Persists IDs in `runtime/agent_ids.json`, env in `runtime/ma_environment_id.txt`. 5 agent IDs provisioned.
- `src/skyherd/agents/_handler_base.py` — `run_handler_cycle()`: routes managed SSE / local messages / simulation based on `SKYHERD_AGENTS` + `platform_session_id`
- `src/skyherd/agents/mesh.py` — `AgentMesh`: starts all 5 sessions, cost-tick loop, `_mqtt_loop()` subscriber

| Agent | File | Wake Topics | Model |
|---|---|---|---|
| FenceLineDispatcher | `src/skyherd/agents/fenceline_dispatcher.py` | `skyherd/+/fence/+`, `skyherd/+/thermal/+`, `skyherd/neighbor/+/+/predator_confirmed` | opus-4-7 |
| HerdHealthWatcher | `src/skyherd/agents/herd_health_watcher.py` | `skyherd/+/trough_cam/+`, cron | opus-4-7 |
| PredatorPatternLearner | `src/skyherd/agents/predator_pattern_learner.py` | `skyherd/+/thermal/+`, nightly | opus-4-7 |
| GrazingOptimizer | `src/skyherd/agents/grazing_optimizer.py` | `skyherd/+/cron/weekly_monday` | opus-4-7 |
| CalvingWatch | `src/skyherd/agents/calving_watch.py` | `skyherd/+/collar/+`, activity spikes | opus-4-7 |

- Beta header `managed-agents-2026-04-01` auto-applied by SDK on `client.beta.*` (documented `managed.py:8-9`)
- MCP wired via `McpSdkServerConfig` + `create_sdk_mcp_server`
- Each agent has an `AgentSpec` (not an SDK `Agent` subclass); handlers are async Python; "managed" path → `client.beta.sessions.events.send()` + `.stream()`

**Layer 4 — Intervene**
- `src/skyherd/drone/stub.py` — `StubBackend` (CI/tests, in-memory log)
- `src/skyherd/drone/sitl.py` — `SitlBackend`: real MAVLink via `mavsdk.System`, UDP 14540, mission upload/execute; synthetic thermal via NumPy+Pillow
- `src/skyherd/drone/sitl_emulator.py` — pure-Python emulator (no Docker)
- `src/skyherd/drone/mavic.py` — `MavicBackend`: WebSocket bridge to Android
- `src/skyherd/drone/f3_inav.py` — `F3InavBackend`: pymavlink serial bridge
- `src/skyherd/drone/safety.py` — `SafetyGuard`: geofence, battery floor, wind limit
- `src/skyherd/drone/interface.py` — `get_backend()` reads `DRONE_BACKEND`
- `src/skyherd/voice/wes.py` — `WesMessage` + `wes_script()`: template cowboy persona with AI-telltale scrub
- `src/skyherd/voice/tts.py` — TTS waterfall (ElevenLabs → piper → espeak → silent)
- `src/skyherd/voice/call.py` — `render_urgency_call()`: full pipeline WesMessage → WAV → deliver. Priority: Twilio (if `TWILIO_SID`+`CLOUDFLARE_TUNNEL_URL`) → dashboard ring (`runtime/phone_rings.jsonl`) → log-only
- MCP servers: `drone_mcp.py` (`launch_drone`, `return_to_home`, `play_deterrent`, `get_thermal_clip`, `drone_status`), `sensor_mcp.py`, `rancher_mcp.py`, `galileo_mcp.py` (cross-ranch mesh)

**Layer 5 — Defend**
- `src/skyherd/attest/ledger.py` — `Ledger`: SQLite WAL, Blake2b-256 hash chain, Ed25519 per row. `append()` atomic; `verify()` walks chain
- `src/skyherd/attest/signer.py` — Ed25519 keypair + sign/verify
- `SensorBus.publish()` mirrors to ledger when `ledger=` kwarg supplied; every scenario run appends events
- Cross-ranch: `_simulate_neighbor_handler()` handles `skyherd/neighbor/+/+/predator_confirmed` — FenceLineDispatcher pre-positions drone without paging rancher

### Entry Points
- `make demo` → `skyherd-demo play all --seed 42` (CLI `src/skyherd/scenarios/cli.py`) → `Scenario.run()` in `src/skyherd/scenarios/base.py`; seeded from `worlds/ranch_a.yaml`
- `make dashboard` → Vite build + `uvicorn skyherd.server.app:app --port 8000` with `SKYHERD_MOCK=1`; `EventBroadcaster` generates mock data in mock mode
- `make mesh-smoke` → `skyherd-mesh mesh smoke --verbose` (CLI `src/skyherd/agents/cli.py`) → `AgentMesh.smoke_test()` fires one synthetic wake per agent
- `make hardware-demo` → `skyherd-demo-hw play --prop combo` (CLI `src/skyherd/demo/cli.py`, orchestrator `src/skyherd/demo/hardware_only.py`). Sets `DRONE_BACKEND=mavic`; subscribes to Pi-owned trough_cam MQTT; 180s timeout → fallback coyote sim

### Error Handling (cross-cutting)
- Agent handlers: simulation path if no `ANTHROPIC_API_KEY` or `sdk_client is None`
- `ManagedSessionManager` init: `ManagedAgentsUnavailable` if no API key; `get_session_manager()` catches and falls back to local
- Drone: `DroneUnavailable`, `DroneTimeoutError`; `SafetyGuard` raises `GeofenceViolation`, `BatteryTooLow`
- Voice: TTS chain waterfall (silent is valid fallback)
- MQTT: embedded `amqtt` if `MQTT_URL` unset; reconnect exponential backoff 1s→30s
- Hardware demo: 180s timeout → fallback sim, logs `PROP_NOT_DETECTED`
<!-- GSD:architecture-end -->

## Sim Completeness Gate (historical)

All 10 items TRULY-GREEN as of Apr 22 2026 (see `docs/verify-latest.md` for latest):

- [x] 5 Managed Agents live + cross-talking via shared MQTT
- [x] 7+ sim sensors emitting (water / trough cam / thermal / fence motion / collar GPS+IMU / acoustic / weather)
- [x] Disease heads on synthetic frames (pinkeye / screwworm / foot rot / BRD / LSD / heat stress / BCS)
- [x] ArduPilot SITL drone executing real MAVLink missions from agent tool calls
- [x] Dashboard: ranch map + 5 agent lanes + cost ticker + attestation panel + rancher PWA
- [x] Wes voice end-to-end: Twilio → ElevenLabs → cowboy persona
- [x] 5 scenarios playable back-to-back
- [x] Deterministic replay (`make sim SEED=42`)
- [x] Fresh-clone boots on second machine
- [x] Cost ticker visibly pauses during idle
