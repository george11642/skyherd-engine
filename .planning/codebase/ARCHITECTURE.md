# Architecture

**Analysis Date:** 2026-04-22
**Source:** Ground-truth file inspection — PROGRESS.md and CLAUDE.md claims not trusted; every assertion below verified from source.

---

## Pattern Overview

**Overall:** Event-driven, 5-layer nervous system with dual-runtime managed agent mesh.

**Key Characteristics:**
- MQTT-bussed sensor layer feeds a 5-agent mesh that drives drone and voice actuators
- Agents run on either a real Anthropic Managed Agents platform (`client.beta.*`) or a local shim (`SessionManager`) depending on env vars — same public API either way
- Scenarios are deterministic sim playbacks (seed=42); all randomness is seeded at world level
- All events flow through a SQLite+Ed25519 attestation ledger (append-only Merkle chain)
- Skills (domain `.md` files) are injected as `cache_control` blocks at wake time — not hardcoded in system prompts

---

## 5-Layer Nervous System

### Layer 1 — Sense
**Status: IMPLEMENTED**

**Purpose:** Physical and simulated sensor data ingestion; MQTT publish to bus.

**Implementation:**
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

**Edge sensors (Pi 4 runtime):**
- `src/skyherd/edge/camera.py` — `Camera` + `get_camera()` factory (picamera2 or stub)
- `src/skyherd/edge/detector.py` — `Detector` + `MegaDetectorHead` (PytorchWildlife)
- `src/skyherd/edge/watcher.py` — `EdgeWatcher`: async capture/detect/publish loop; reads CPU temp from `/sys/class/thermal/`; heartbeat at `_DEFAULT_HEALTHZ_PORT = 8787`

**Data flow:** Sensor emitter → `SensorBus.publish(topic, payload)` → MQTT broker → `AgentMesh._mqtt_loop()` subscription

---

### Layer 2 — See
**Status: IMPLEMENTED**

**Purpose:** Vision inference (7-head disease detection) on synthetic and real camera frames.

**Implementation:**
- `src/skyherd/vision/renderer.py` — `render_trough_frame()` + `annotate_frame()`: generates synthetic PNG frames from `World` state
- `src/skyherd/vision/heads/base.py` — `DiseaseHead` ABC with `classify(frame_meta) → DetectionResult`
- `src/skyherd/vision/heads/pinkeye.py`, `screwworm.py`, `foot_rot.py`, `brd.py`, `lsd.py`, `heat_stress.py`, `bcs.py` — 7 disease detection heads (rule-based on sensor metadata; no actual CNN weight loading)
- `src/skyherd/vision/registry.py` — `classify(frame_meta) → list[DetectionResult]` dispatcher
- `src/skyherd/vision/pipeline.py` — `ClassifyPipeline.run(world, trough_id)`: render frame → classify all cows → annotate → return `PipelineResult`
- `src/skyherd/vision/result.py` — `DetectionResult` dataclass

**Note:** Disease heads are rule-based simulations operating on sensor metadata (respiration_bpm, temp, etc.), not pixel-level CNN inference. MegaDetector V6 is referenced in edge tier only.

---

### Layer 3 — Respond
**Status: IMPLEMENTED**

**Purpose:** 5-agent mesh — Claude-driven decision-making that calls MCP tools.

**Implementation:**
- `src/skyherd/agents/spec.py` — `AgentSpec` dataclass: `name`, `system_prompt_template_path`, `wake_topics` (MQTT patterns), `mcp_servers`, `skills`, `model`
- `src/skyherd/agents/session.py` — `SessionManager` (local shim): `create_session()`, `sleep()`, `wake()`, `checkpoint()`, `on_webhook()`. Models Managed Agents semantics — cost meter pauses when `state == "idle"`. `build_cached_messages()` emits `cache_control: {"type": "ephemeral"}` blocks for system prompt + each skill file.
- `src/skyherd/agents/managed.py` — `ManagedSessionManager`: real `client.beta.agents/sessions/environments.*` calls. Persists agent IDs in `runtime/agent_ids.json`, env ID in `runtime/ma_environment_id.txt`. **Real platform agents provisioned** (verified: 5 agent IDs present).
- `src/skyherd/agents/_handler_base.py` — `run_handler_cycle()`: selects managed SSE stream path vs local `messages.create()` path vs simulation path based on `SKYHERD_AGENTS` env and `platform_session_id` presence.
- `src/skyherd/agents/mesh.py` — `AgentMesh`: starts all 5 sessions, runs cost-tick loop, runs `_mqtt_loop()` subscriber, routes events to handlers.

**The 5 Managed Agents (all IMPLEMENTED as real MA-SDK classes):**

| Agent | File | Wake Topics | Model |
|-------|------|-------------|-------|
| FenceLineDispatcher | `src/skyherd/agents/fenceline_dispatcher.py` | `skyherd/+/fence/+`, `skyherd/+/thermal/+`, `skyherd/neighbor/+/+/predator_confirmed` | claude-opus-4-7 |
| HerdHealthWatcher | `src/skyherd/agents/herd_health_watcher.py` | `skyherd/+/trough_cam/+`, cron | claude-opus-4-7 |
| PredatorPatternLearner | `src/skyherd/agents/predator_pattern_learner.py` | `skyherd/+/thermal/+`, nightly | claude-opus-4-7 |
| GrazingOptimizer | `src/skyherd/agents/grazing_optimizer.py` | `skyherd/+/cron/weekly_monday` | claude-opus-4-7 |
| CalvingWatch | `src/skyherd/agents/calving_watch.py` | `skyherd/+/collar/+`, activity spikes | claude-opus-4-7 |

**Critical finding — Managed Agents wiring:**
- `ManagedSessionManager` uses `client.beta.agents.create()`, `client.beta.sessions.create()`, `client.beta.environments.create()` — genuine beta SDK calls, not stubs.
- Beta header `managed-agents-2026-04-01` is applied automatically by the SDK on `client.beta.*` calls (documented in `managed.py` line 8-9).
- The MCP tools are wired via `claude_agent_sdk.McpSdkServerConfig` + `create_sdk_mcp_server` — package installed and imports verified.
- In practice, each agent has an `AgentSpec` (not an SDK `Agent` subclass). Handlers are async Python functions, not MA-native agent definitions. The "managed" path sends wake events to the platform via `client.beta.sessions.events.send()` and streams responses via `client.beta.sessions.events.stream()`.
- **Runtime evidence:** `runtime/agent_ids.json` contains 5 provisioned agent IDs; `runtime/ma_environment_id.txt` contains a live env ID — confirming real platform registration has occurred.

**Simulation fallback path:** When `ANTHROPIC_API_KEY` absent or `SKYHERD_AGENTS != managed`, each agent calls `_simulate_handler()` which imports from `src/skyherd/agents/simulate.py` — deterministic tool-call lists without real API calls.

---

### Layer 4 — Intervene
**Status: IMPLEMENTED (with backend tiers)**

**Purpose:** Physical actuation — drone dispatch, deterrent, voice call.

**Drone backends (interface: `DroneBackend` ABC in `src/skyherd/drone/interface.py`):**
- `src/skyherd/drone/stub.py` — `StubBackend`: in-memory log only (CI/tests)
- `src/skyherd/drone/sitl.py` — `SitlBackend`: real MAVLink via `mavsdk.System`, connects to UDP 14540, full mission upload/execute. Generates synthetic thermal PNGs via NumPy+Pillow.
- `src/skyherd/drone/sitl_emulator.py` — pure-Python SITL emulator (no Docker required)
- `src/skyherd/drone/mavic.py` — `MavicBackend`: WebSocket bridge to Android companion app
- `src/skyherd/drone/f3_inav.py` — `F3InavBackend`: pymavlink serial bridge (F3 flight controller)
- `src/skyherd/drone/safety.py` — `SafetyGuard`: geofence, battery floor, wind limit enforcement
- `src/skyherd/drone/interface.py` — `get_backend()` factory: reads `DRONE_BACKEND` env var

**Voice actuation:**
- `src/skyherd/voice/wes.py` — `WesMessage` + `wes_script()`: template-based cowboy persona composer with AI-telltale scrub
- `src/skyherd/voice/tts.py` — TTS backend factory (ElevenLabs → piper → espeak → silent fallback)
- `src/skyherd/voice/call.py` — `render_urgency_call()`: full pipeline WesMessage → WAV → deliver. Delivery priority: Twilio voice call (if `TWILIO_SID`+`CLOUDFLARE_TUNNEL_URL` set) → dashboard ring (`runtime/phone_rings.jsonl`) → log-only.

**MCP servers (4 servers, all using `claude_agent_sdk`):**
- `src/skyherd/mcp/drone_mcp.py` — tools: `launch_drone`, `return_to_home`, `play_deterrent`, `get_thermal_clip`, `drone_status`
- `src/skyherd/mcp/sensor_mcp.py` — tools: read from `_BUS_STATE` ring buffer
- `src/skyherd/mcp/rancher_mcp.py` — tools: `page_rancher` → calls `render_urgency_call()`
- `src/skyherd/mcp/galileo_mcp.py` — tools: cross-ranch mesh coordination

---

### Layer 5 — Defend
**Status: IMPLEMENTED**

**Purpose:** Attestation and cross-ranch mesh.

**Attestation (`src/skyherd/attest/`):**
- `src/skyherd/attest/ledger.py` — `Ledger`: SQLite WAL, Blake2b-256 hash chain, Ed25519 signatures per row. `append()` is atomic; `verify()` walks full chain.
- `src/skyherd/attest/signer.py` — `Signer`: Ed25519 key pair generation + sign/verify
- Every `SensorBus.publish()` call optionally mirrors to ledger if `ledger=` kwarg supplied
- Every scenario run appends events to ledger

**Cross-ranch mesh (`src/skyherd/agents/mesh_neighbor.py`):**
- `_simulate_neighbor_handler()` handles `neighbor_alert` events from `skyherd/neighbor/+/+/predator_confirmed` topics
- FenceLineDispatcher spec includes cross-ranch wake topic; pre-positions drone without paging rancher

---

## Data Flow

### Primary Cascade (Coyote scenario)

1. `World.step()` → `CoyoteScenario.inject_events()` returns `fence.breach` event dict at `sim_time_s >= 462`
2. Scenario runner publishes event to MQTT via `SensorBus.publish("skyherd/ranch_a/fence/fence_west", payload)`
3. `AgentMesh._mqtt_loop()` receives topic, calls `SessionManager.on_webhook(event)`
4. `on_webhook()` matches topic `skyherd/+/fence/+` → wakes `FenceLineDispatcher` session
5. `AgentMesh._run_handler()` calls `fenceline_dispatcher.handler(session, wake_event, sdk_client)`
6. Handler calls `run_handler_cycle()` → either MA SSE stream or `messages.create()` with cache_control blocks
7. Claude calls tools: `get_thermal_clip` → `launch_drone` → `play_deterrent` → `page_rancher`
8. Tool results: drone MCP executes via `DroneBackend`; rancher MCP calls `render_urgency_call()` → Twilio or dashboard ring
9. All events appended to `Ledger`
10. `SessionManager.sleep()` halts cost ticker

### Dashboard Flow

1. `EventBroadcaster` in `src/skyherd/server/events.py` polls mesh + ledger + world periodically
2. FastAPI `/events` endpoint streams SSE to browser via `EventSourceResponse`
3. React SPA (`web/src/`) receives SSE events; `AgentLane`, `RanchMap`, `AttestationPanel`, `CostTicker` components render live state
4. `/rancher` route serves same SPA; `RancherPhone` component rings on `rancher.ringing` events

---

## Entry Points

**`make demo SEED=42 SCENARIO=all`:**
- Invokes `skyherd-demo play all --seed 42`
- CLI: `src/skyherd/scenarios/cli.py`
- Runs all 5 scenarios back-to-back via `Scenario.run()` in `src/skyherd/scenarios/base.py`
- Seeds `World` from YAML config `worlds/ranch_a.yaml`; deterministic replay guaranteed

**`make dashboard`:**
- Builds Vite SPA (`web/`), then `uvicorn skyherd.server.app:app --port 8000` with `SKYHERD_MOCK=1`
- App factory: `src/skyherd/server/app.py`
- Mock mode: no live mesh/bus required; `EventBroadcaster` generates mock data

**`make mesh-smoke`:**
- Invokes `skyherd-mesh mesh smoke --verbose`
- CLI: `src/skyherd/agents/cli.py`
- `AgentMesh.smoke_test()`: fires one synthetic wake event per agent; simulation path runs without API key

**`make hardware-demo`:**
- Invokes `skyherd-demo-hw play --prop combo`
- CLI: `src/skyherd/demo/cli.py`
- Orchestrator: `src/skyherd/demo/hardware_only.py`
- Sets `DRONE_BACKEND=mavic`; subscribes to Pi-owned trough_cam MQTT topics; 180s timeout before fallback to sim

---

## Error Handling

**Strategy:** Explicit fallbacks at every layer; never crash the demo.

**Patterns:**
- Agent handlers: simulation path if no `ANTHROPIC_API_KEY` or `sdk_client is None`
- `ManagedSessionManager` init: raises `ManagedAgentsUnavailable` if no API key; `get_session_manager()` catches and falls back to local
- Drone backends: `DroneUnavailable` / `DroneTimeoutError` exceptions; `SafetyGuard` raises `GeofenceViolation` / `BatteryTooLow`
- Voice: TTS chain waterfall (ElevenLabs → piper → espeak → silent)
- MQTT: embedded `amqtt` broker starts automatically if `MQTT_URL` not set; reconnect with exponential backoff (1s → 30s cap)
- Hardware demo: 180s timeout → fallback coyote sim scenario; logs `PROP_NOT_DETECTED`

---

## Cross-Cutting Concerns

**Logging:** Python stdlib `logging`; structlog optional (`SKYHERD_OBS=1`) — see `src/skyherd/obs/logging.py`

**Metrics:** Prometheus text format at `/metrics` via `prometheus_client` (optional dep) — `src/skyherd/obs/metrics.py`

**Validation:** Pydantic v2 models for `WorldSnapshot`, `Event`, `DetectionResult`, `WesMessage`, `AgentSpec`; input validation at MCP tool boundaries

**Authentication:** No user auth on dashboard; CORS restricted to localhost origins by default (`SKYHERD_CORS_ORIGINS` env var). Webhook endpoint requires HMAC-SHA256 signature (`SKYHERD_WEBHOOK_SECRET`).

**State persistence:** Sessions serialised to `runtime/sessions/{uuid}.json` on checkpoint; agent IDs and env IDs cached in `runtime/`; events logged to `runtime/scenario_runs/*.jsonl`

---

*Architecture analysis: 2026-04-22*
