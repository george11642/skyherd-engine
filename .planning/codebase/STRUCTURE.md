# Codebase Structure

**Analysis Date:** 2026-04-22
**Source:** Ground-truth `find` traversal — all directory counts verified from filesystem.

---

## Directory Layout

```
skyherd-engine/
├── src/skyherd/           # Python package (all backend logic)
│   ├── world/             # Deterministic ranch simulator (8 .py files)
│   ├── sensors/           # MQTT bus + 7 sim sensor emitters (11 .py files)
│   ├── agents/            # 5-agent Managed Agents mesh (16 .py files)
│   │   └── prompts/       # 5 agent system prompt .md files
│   ├── mcp/               # 4 MCP servers (claude_agent_sdk) (5 .py files)
│   ├── vision/            # Scene renderer + 7 disease-detection heads (14 .py files)
│   │   └── heads/         # 7 disease head .py files
│   ├── drone/             # SITL/stub/mavic/f3_inav backends (10 .py files)
│   ├── edge/              # Pi 4 runtime: camera+detector+watcher (5 .py files)
│   │   ├── configs/       # Edge configuration files
│   │   └── systemd/       # Systemd service units
│   ├── attest/            # Ed25519 Merkle ledger (4 .py files)
│   ├── voice/             # Wes persona + TTS chain (5 .py files)
│   ├── scenarios/         # 5 demo scenarios + cross-ranch + extras (11 .py files)
│   ├── server/            # FastAPI + SSE dashboard backend (4 .py files)
│   ├── demo/              # Hardware-only demo orchestrator (3 .py files)
│   └── obs/               # Optional observability (structlog/prometheus/OTel) (4 .py files)
├── tests/                 # pytest suite (95 test files across 14 subdirs)
├── web/                   # Vite + React 19 + Tailwind v4 SPA
│   ├── src/               # TypeScript/TSX components + hooks
│   └── dist/              # Built SPA (committed, served by FastAPI)
├── skills/                # 33 ranch domain knowledge .md files (CrossBeam pattern)
│   ├── cattle-behavior/   # Disease, calving, lameness, heat stress
│   ├── drone-ops/         # Patrol planning, deterrent protocols, battery
│   ├── nm-ecology/        # NM predator ranges, forage, weather, seasonal
│   ├── predator-ids/      # Coyote, mountain lion, wolf, LGD, thermal sigs
│   ├── ranch-ops/         # Fence protocols, paddock rotation, water SOPs
│   └── voice-persona/     # Wes register, urgency tiers, never-panic
├── worlds/                # Ranch YAML configs (ranch_a.yaml, ranch_b.yaml)
├── android/SkyHerdCompanion/  # Kotlin + DJI SDK V5 + MQTT companion (5 .kt files)
├── ios/SkyHerdCompanion/      # Swift + DJI SDK V5 + CocoaMQTT (10 .swift files)
├── hardware/collar/       # LoRa collar: PlatformIO firmware + 3D print + BOM
├── docs/                  # Architecture, managed agents docs, runbooks
├── scripts/               # PDF renderer, replay builder, cloudflared setup
├── docker/                # Docker configs
├── runtime/               # Generated at runtime — not committed (except agent IDs)
│   ├── agent_ids.json     # Provisioned MA platform agent IDs (5 agents)
│   ├── ma_environment_id.txt  # Provisioned MA environment ID
│   ├── sessions/          # Session checkpoint JSONs
│   ├── scenario_runs/     # JSONL replay logs per scenario run
│   ├── thermal/           # Synthetic thermal frame PNGs
│   └── phone_rings.jsonl  # Rancher page log
├── .planning/codebase/    # GSD codebase analysis documents
├── .refs/CameraTraps/     # MegaDetector V6 reference repo (git submodule)
├── Makefile               # All build/run/test targets
├── pyproject.toml         # Python project config + all deps
└── CLAUDE.md              # Project fast-loader for Claude sessions
```

---

## Directory Purposes

**`src/skyherd/world/`:**
- Purpose: Deterministic ranch simulator, all randomness seeded
- Key files: `world.py` (`World` class + `WorldSnapshot`), `cattle.py` (`Cow`, `Herd`), `predators.py` (`Predator`, `PredatorSpawner`), `clock.py`, `terrain.py`, `weather.py`
- Entry CLI: `world/cli.py` → `uv run python -m skyherd.world.cli --seed 42 --duration 300`

**`src/skyherd/sensors/`:**
- Purpose: MQTT-based sensor data bus + 7 sensor emitters
- Key files: `bus.py` (`SensorBus` — embedded amqtt or external broker), `base.py` (`BaseSensor` ABC), `registry.py`, 7 emitter files (water, fence, collar, thermal, trough_cam, acoustic, weather)

**`src/skyherd/agents/`:**
- Purpose: 5-agent managed mesh with dual-runtime (MA platform or local shim)
- Key files:
  - `spec.py` — `AgentSpec` dataclass (declarative agent config)
  - `session.py` — `SessionManager` (local shim), `build_cached_messages()`, `get_session_manager()` factory
  - `managed.py` — `ManagedSessionManager` (real `client.beta.*` calls)
  - `_handler_base.py` — `run_handler_cycle()` (selects MA vs local vs sim path)
  - `mesh.py` — `AgentMesh` orchestrator
  - `simulate.py` — deterministic simulation fallback for all 5 agents
  - `webhook.py` — FastAPI router at `POST /webhooks/managed-agents`
  - `mesh_neighbor.py` — cross-ranch neighbor alert handler
  - `cost.py` — `CostTicker` (pauses when session idle)
  - `fenceline_dispatcher.py`, `herd_health_watcher.py`, `predator_pattern_learner.py`, `grazing_optimizer.py`, `calving_watch.py` — individual agent specs + handlers
- `prompts/` — 5 system prompt `.md` files (one per agent)

**`src/skyherd/mcp/`:**
- Purpose: 4 MCP servers exposing tools to agents via `claude_agent_sdk`
- Key files: `drone_mcp.py` (launch_drone, play_deterrent, thermal), `sensor_mcp.py`, `rancher_mcp.py` (page_rancher → voice), `galileo_mcp.py` (cross-ranch)

**`src/skyherd/vision/`:**
- Purpose: Synthetic frame renderer + 7 disease classification heads
- Key files: `renderer.py` (generates PNG from world state), `pipeline.py` (`ClassifyPipeline`), `registry.py` (`classify()` dispatcher), `result.py` (`DetectionResult`), `heads/` (7 rule-based heads)
- Note: Heads are rule-based on sensor metadata — no actual CNN inference in sim path

**`src/skyherd/drone/`:**
- Purpose: Multi-backend drone abstraction
- Key files: `interface.py` (`DroneBackend` ABC + `get_backend()` + `Waypoint`), `stub.py` (test/CI), `sitl.py` (MAVSDK + real MAVLink), `sitl_emulator.py` (pure-Python SITL), `mavic.py` (WebSocket to Android), `f3_inav.py` (serial pymavlink), `safety.py` (`SafetyGuard`)

**`src/skyherd/edge/`:**
- Purpose: Pi 4 runtime: camera capture → MegaDetector inference → MQTT publish
- Key files: `camera.py` (picamera2 or stub), `detector.py` (`MegaDetectorHead`), `watcher.py` (`EdgeWatcher` async loop + HTTP healthz on port 8787), `cli.py`

**`src/skyherd/attest/`:**
- Purpose: Append-only Ed25519-signed Merkle hash chain ledger
- Key files: `ledger.py` (`Ledger`: SQLite WAL, Blake2b-256, Ed25519), `signer.py` (`Signer`), `cli.py`

**`src/skyherd/voice/`:**
- Purpose: Wes cowboy persona synthesis and delivery
- Key files: `wes.py` (`WesMessage`, `wes_script()`, AI-telltale scrub), `tts.py` (ElevenLabs→piper→espeak→silent chain), `call.py` (`render_urgency_call()` → Twilio or dashboard ring)

**`src/skyherd/scenarios/`:**
- Purpose: 5 demo scenarios + cross-ranch variant + extras
- Key files: `base.py` (`Scenario` ABC + `ScenarioResult`), `coyote.py`, `sick_cow.py`, `water_drop.py`, `calving.py`, `storm.py`, `cross_ranch_coyote.py`, `rustling.py`, `wildfire.py`, `cli.py` (`skyherd-demo` CLI)
- All scenarios: seed world → inject events at sim-time offsets → assert tool-call cascade → write JSONL replay to `runtime/scenario_runs/`

**`src/skyherd/server/`:**
- Purpose: FastAPI app serving dashboard SPA + SSE stream + REST API
- Key files: `app.py` (`create_app()` factory, mounts webhook router, CORS, SSE limit), `events.py` (`EventBroadcaster`), `cli.py`
- Endpoints: `/health`, `/api/snapshot`, `/api/agents`, `/api/attest`, `/events` (SSE), `/metrics` (Prometheus), `/` + `/rancher` (SPA)

**`src/skyherd/demo/`:**
- Purpose: Hardware-only demo orchestrator
- Key files: `hardware_only.py` (`HardwareOnlyDemo`), `cli.py` (`skyherd-demo-hw`)

**`src/skyherd/obs/`:**
- Purpose: Optional observability (structlog, prometheus-client, OpenTelemetry)
- Key files: `logging.py`, `metrics.py`, `tracing.py`
- Enabled via `SKYHERD_OBS=1`; installed with `uv sync --extra obs`

**`web/src/`:**
- Purpose: React 19 SPA — dashboard + rancher PWA
- Key files: `App.tsx`, `routes.tsx`, `lib/sse.ts` (SSE hook), `lib/replay.ts`
- Components: `AgentLane.tsx`, `AgentLanes.tsx`, `RanchMap.tsx`, `AttestationPanel.tsx`, `CostTicker.tsx`, `RancherPhone.tsx`, `CrossRanchView.tsx`
- Shared UI: `components/shared/` (Chip, MonoText, PulseDot, ScenarioStrip, StatBand)
- Built output at `web/dist/` (committed; served by FastAPI static files)

**`skills/`:**
- Purpose: Ranch domain knowledge library (CrossBeam pattern) — loaded as `cache_control` blocks at agent wake time
- 33 `.md` files across 6 subdirectories
- Agents reference skills by path in `AgentSpec.skills` list

**`android/SkyHerdCompanion/`:**
- Purpose: Kotlin + DJI SDK V5 companion app for Mavic drone control
- Key files: `DroneControl.kt`, `MQTTBridge.kt`, `SafetyGuards.kt`, `MainActivity.kt`

**`ios/SkyHerdCompanion/`:**
- Purpose: Swift + DJI SDK V5 + CocoaMQTT companion app
- Key files: `DJIBridge.swift`, `MQTTBridge.swift`, `SafetyGuards.swift`, `CommandRouter.swift`
- Built via XcodeGen (`project.yml`)

**`hardware/collar/`:**
- Purpose: Optional DIY LoRa collar (PlatformIO firmware + 3D print)
- Key files: `firmware/src/main.cpp`, `firmware/platformio.ini`, `3d_print/collar_shell.scad`, `BOM.md`, `provisioning/register-collar.py`

**`tests/`:**
- Purpose: pytest suite — 95 test files across 14 module-mirroring subdirectories
- Subdirs: `agents/`, `attest/`, `demo/`, `drone/`, `edge/`, `hardware/`, `mcp/`, `obs/`, `scenarios/`, `sensors/`, `server/`, `vision/`, `voice/`, `world/`
- Top-level: `test_smoke.py`, `test_determinism_e2e.py`

---

## Key File Locations

**Entry Points:**
- `src/skyherd/scenarios/cli.py`: `skyherd-demo` — demo playback CLI
- `src/skyherd/agents/cli.py`: `skyherd-mesh` — mesh start/smoke CLI
- `src/skyherd/demo/cli.py`: `skyherd-demo-hw` — hardware demo CLI
- `src/skyherd/server/app.py`: `create_app()` + `app` module-level instance for uvicorn
- `src/skyherd/attest/cli.py`: `skyherd-attest` — ledger verify/export CLI

**Configuration:**
- `pyproject.toml`: all deps, scripts, pytest config, coverage config, ruff config
- `worlds/ranch_a.yaml`: primary ranch world config (loaded by `make_world()`)
- `worlds/ranch_b.yaml`: second ranch (cross-ranch scenarios)
- `.env.example`: reference for required env vars
- `Makefile`: all operational targets

**Core Logic:**
- `src/skyherd/agents/managed.py`: `ManagedSessionManager` — real MA platform client
- `src/skyherd/agents/session.py`: `SessionManager` + `build_cached_messages()` + `get_session_manager()`
- `src/skyherd/agents/_handler_base.py`: `run_handler_cycle()` — MA vs local vs sim routing
- `src/skyherd/sensors/bus.py`: `SensorBus` — MQTT backbone
- `src/skyherd/attest/ledger.py`: `Ledger` — attestation chain

**Prompt Files:**
- `src/skyherd/agents/prompts/fenceline_dispatcher.md`
- `src/skyherd/agents/prompts/herd_health_watcher.md`
- `src/skyherd/agents/prompts/predator_pattern_learner.md`
- `src/skyherd/agents/prompts/grazing_optimizer.md`
- `src/skyherd/agents/prompts/calving_watch.md`

---

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `fenceline_dispatcher.py`, `sensor_mcp.py`)
- Test files: `test_{module}.py` mirroring source module name
- Skills: `kebab-case.md` (e.g., `fence-line-protocols.md`, `wes-register.md`)
- Prompts: `snake_case.md` matching agent name

**Classes:** `PascalCase` (`AgentMesh`, `SensorBus`, `ManagedSession`, `ClassifyPipeline`)
**Functions:** `snake_case` (`run_handler_cycle`, `build_cached_messages`, `get_backend`)
**Constants:** `UPPER_SNAKE_CASE` (`_BREACH_AT_S`, `GENESIS_PREV_HASH`)
**Private:** single-underscore prefix (`_simulate_handler`, `_mqtt_topic_matches`)

---

## Where to Add New Code

**New sensor emitter:**
- Implementation: `src/skyherd/sensors/{sensor_name}.py` extending `BaseSensor`
- Register in: `src/skyherd/sensors/registry.py`
- Tests: `tests/sensors/test_{sensor_name}.py`

**New disease detection head:**
- Implementation: `src/skyherd/vision/heads/{disease}.py` extending `DiseaseHead`
- Register in: `src/skyherd/vision/registry.py`
- Tests: `tests/vision/test_heads/test_{disease}.py`

**New demo scenario:**
- Implementation: `src/skyherd/scenarios/{name}.py` extending `Scenario` ABC
- Register in: `src/skyherd/scenarios/cli.py` scenario registry
- Tests: `tests/scenarios/test_{name}.py`

**New agent skill:**
- Add `.md` file to appropriate `skills/{category}/` subdirectory
- Reference in the relevant agent's `AgentSpec.skills` list in its handler file

**New MCP tool:**
- Add `@tool(...)` function inside appropriate `_build_tools()` in `src/skyherd/mcp/{server}_mcp.py`
- Tests: `tests/mcp/test_{server}_mcp.py`

**New API endpoint:**
- Add to `src/skyherd/server/app.py` inside `create_app()`
- Tests: `tests/server/test_app.py`

**Utilities/shared helpers:**
- Ranch domain constants: add to relevant `skills/` `.md` file
- Python utilities: add to the module they most closely relate to (no generic `utils.py`)

---

## Special Directories

**`runtime/`:**
- Purpose: All generated output — session checkpoints, drone event logs, scenario JSONL, thermal frames, phone rings
- Generated: Yes (most files)
- Committed: Partially — `runtime/agent_ids.json` and `runtime/ma_environment_id.txt` committed (contain live Anthropic MA platform IDs)

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis documents
- Generated: Yes
- Committed: Yes

**`.refs/CameraTraps/`:**
- Purpose: MegaDetector V6 reference repo for edge detector
- Generated: No (git submodule)
- Committed: Yes (submodule reference)

**`web/dist/`:**
- Purpose: Pre-built Vite SPA (served by FastAPI without requiring pnpm at runtime)
- Generated: Yes (by `pnpm run build`)
- Committed: Yes

---

*Structure analysis: 2026-04-22*
