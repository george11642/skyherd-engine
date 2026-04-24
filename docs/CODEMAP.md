# CODEMAP — File-by-file purpose map

Generated Apr 22 2026. Excludes `.refs/`, `.venv/`, `runtime/`, `node_modules/`, `web/dist/`, `__pycache__/`.

---

## Python (`src/skyherd/`)

### `world/` — deterministic ranch simulator

| File | Purpose |
|------|---------|
| `world.py` | World facade — assembles all sim subsystems (cattle, predators, terrain, weather, clock) and drives them forward one tick at a time. |
| `cattle.py` | Cow dataclass and Herd stepping logic — positions, health states, activity levels. |
| `predators.py` | Predator agents (coyote, mountain lion) — spawn rules, movement, threat escalation. |
| `terrain.py` | Ranch terrain grid — paddocks, fence lines, water tank locations, GPS bounding box. |
| `weather.py` | Weather state machine — temperature, wind, precipitation, storm front logic. |
| `clock.py` | Sim clock — accelerated time, day/night cycle, season-of-year derivation. |
| `cli.py` | `skyherd-world` CLI entry point — `run`, `snapshot` sub-commands. |

### `sensors/` — MQTT bus + 7 sim sensor emitters

| File | Purpose |
|------|---------|
| `bus.py` | SensorBus — MQTT publish/subscribe with optional embedded amqtt broker; env-driven URL. |
| `base.py` | BaseSensor — abstract async emitter with `emit()` loop and topic convention. |
| `registry.py` | SensorRegistry — discovers and instantiates all sensor modules by world config. |
| `water.py` | Water tank pressure + level sensor — drop events trigger drone flyover. |
| `trough_cam.py` | Trough camera emitter — synthetic frames annotated with cattle IDs. |
| `thermal.py` | Thermal sensor — heat signatures for cattle and predator discrimination. |
| `fence.py` | Fence motion detector — breach events with GPS segment and confidence score. |
| `collar.py` | CollarSensor — GPS+IMU collar on a single cow, emits position and activity. |
| `acoustic.py` | Acoustic emitter — frequency sweeps used by Neural Nudge deterrent. |
| `weather.py` | Weather sensor — wraps world weather state into MQTT telemetry. |

### `agents/` — 5 Managed-Agents-compat mesh

| File | Purpose |
|------|---------|
| `mesh.py` | AgentMesh — orchestrates all 5 managed-agent sessions; `smoke_test()` confirms all 5 present. |
| `mesh_neighbor.py` | NeighborBroadcaster + NeighborListener — cross-ranch MQTT bridge for multi-ranch mesh. |
| `fenceline_dispatcher.py` | FenceLineDispatcher — responds to fence breach + thermal confirmation; dispatches drone. |
| `herd_health_watcher.py` | HerdHealthWatcher — trough-cam + collar activity anomaly detection; escalates to Doc. |
| `predator_pattern_learner.py` | PredatorPatternLearner — nightly multi-day thermal crossing analysis; updates threat map. |
| `grazing_optimizer.py` | GrazingOptimizer — weekly paddock rotation + weather-triggered override proposals. |
| `calving_watch.py` | CalvingWatch — seasonal (Mar–Apr) labor behavior + dystocia paging. |
| `session.py` | AgentSession — thin wrapper around Claude Managed Agents SDK session lifecycle. |
| `spec.py` | AgentSpec — dataclass carrying agent name, system prompt path, tool list. |
| `cost.py` | CostTracker — per-agent token/cost accounting, idle-pause detection for cost ticker. |
| `cli.py` | `skyherd-agents` CLI — `run`, `mesh-smoke` sub-commands. |
| `prompts/` | Per-agent system prompt `.md` files (Skills-first: prompts stay short; domain knowledge lives in `skills/`). |

### `mcp/` — MCP servers

| File | Purpose |
|------|---------|
| `drone_mcp.py` | Drone MCP server — wraps DroneBackend as Claude-callable tools (`launch_drone`, `land`, `get_telemetry`). |
| `sensor_mcp.py` | Sensor MCP server — exposes live sensor readings as tools for agent queries. |
| `rancher_mcp.py` | Rancher MCP server — `page_rancher(urgency, context)` → Twilio SMS or Wes voice call. |
| `galileo_mcp.py` | Galileo MCP server — attestation chain tools (`log_event`, `verify_chain`, `export_report`). |

### `vision/` — scene renderer + 7 disease-detection heads

| File | Purpose |
|------|---------|
| `renderer.py` | SceneRenderer — converts world snapshot to synthetic RGB frame (PIL-based). |
| `pipeline.py` | ClassifyPipeline — end-to-end world-snapshot → annotated frame + detections. |
| `registry.py` | HeadRegistry — discovers and loads all disease-detection head modules. |
| `result.py` | DetectionResult dataclass — head name, confidence, bounding box, metadata. |
| `heads/base.py` | BaseHead — abstract classify interface all 7 heads implement. |
| `heads/pinkeye.py` | Pinkeye / IBK detector — ocular region classifier. |
| `heads/screwworm.py` | New World Screwworm detector — wound region + fly cluster heuristic (2026-timely). |
| `heads/foot_rot.py` | Foot rot / lameness detector — gait and weight-bearing analysis. |
| `heads/brd.py` | Bovine Respiratory Disease (BRD) detector — posture + nasal discharge features. |
| `heads/lsd.py` | Lumpy Skin Disease (LSD) detector — coat texture anomaly classifier. |
| `heads/heat_stress.py` | Heat stress detector — panting rate + shade-seeking behavior. |
| `heads/bcs.py` | Body Condition Score (BCS 1–9) estimator — spine prominence + rib visibility. |

### `drone/` — drone backends + safety guards

| File | Purpose |
|------|---------|
| `interface.py` | Drone abstraction layer — DroneInterface ABC, telemetry dataclass, backend factory. |
| `sitl.py` | ArduPilot SITL backend — MAVSDK-Python; executes real MAVLink missions. |
| `stub.py` | StubBackend — in-memory stub for fast unit tests without SITL process. |
| `mavic.py` | MavicBackend — DJI Mavic Air 2 via WebSocket bridge to Android/iOS companion apps. |
| `f3_inav.py` | F3InavBackend — SP Racing F3 iNav flight controller via serial/USB. |
| `safety.py` | Shared safety guards — geofence check, battery floor, wind ceiling, home-lock. |

### `edge/` — Pi 4 H1 runtime

| File | Purpose |
|------|---------|
| `watcher.py` | EdgeWatcher — async capture/detect/publish loop; core Pi H1 process. |
| `camera.py` | CameraSource — OpenCV capture wrapper with Pi camera + USB fallback. |
| `detector.py` | EdgeDetector — MegaDetector V6 inference runner (Coral TPU path documented). |
| `cli.py` | `skyherd-edge` CLI — `start`, `healthz` sub-commands; reads per-Pi `.env` config. |
| `configs/` | Per-Pi environment configs: `edge-house.env.example`, `edge-barn.env.example`. |
| `systemd/` | systemd unit file (`skyherd-edge.service`) + env example for production Pi install. |

### `attest/` — Ed25519 Merkle ledger

| File | Purpose |
|------|---------|
| `ledger.py` | SQLite-backed Merkle-chained event ledger — each event hashes previous entry; tamper-evident. |
| `signer.py` | Ed25519 signing primitives — key generation, sign, verify. |
| `cli.py` | `skyherd-attest` CLI — `log`, `verify`, `export` sub-commands. |

### `voice/` — Wes persona + TTS chain

| File | Purpose |
|------|---------|
| `wes.py` | Wes persona — message model + script composer; cowboy register, urgency tiers, never-panic rule. |
| `tts.py` | TTS chain — ElevenLabs → piper → espeak → silent fallback. |
| `call.py` | Call orchestrator — Twilio outbound call trigger + voice webhook handler. |
| `cli.py` | `skyherd-voice` CLI — `say`, `call` sub-commands. |

### `scenarios/` — 5 demo scenarios + cross-ranch variant

| File | Purpose |
|------|---------|
| `base.py` | BaseScenario — deterministic seed-driven playback; `run()` → list of events with timestamps. |
| `coyote.py` | Scenario 1: Coyote at fence — FenceLineDispatcher → SITL drone → deterrent → Wes call. |
| `sick_cow.py` | Scenario 2: Sick cow flagged — HerdHealthWatcher → Doc escalation → vet-intake packet. |
| `water_drop.py` | Scenario 3: Water tank pressure drop — LoRaWAN alert → drone flyover → attestation logged. |
| `calving.py` | Scenario 4: Calving detected — CalvingWatch pre-labor behavior → priority rancher page. |
| `storm.py` | Scenario 5: Storm incoming — GrazingOptimizer herd-move → acoustic nudge. |
| `cross_ranch_coyote.py` | Cross-ranch variant — coyote pattern shared via NeighborBroadcaster to ranch_b. |
| `cli.py` | `skyherd-scenarios` CLI — `run SCENARIO`, `run-all` sub-commands. |

### `server/` — FastAPI dashboard backend

| File | Purpose |
|------|---------|
| `app.py` | SkyHerd FastAPI application factory — `/health`, `/api/snapshot`, `/events` SSE stream, SPA static serve. |
| `events.py` | SSE event emitter — bridges world tick loop to browser clients via `text/event-stream`. |
| `cli.py` | `skyherd-server` CLI — `start` sub-command with host/port/mock flags. |

### `demo/` — hardware-only orchestrator

| File | Purpose |
|------|---------|
| `hardware_only.py` | HardwareOnlyDemo — 2-Pi + Mavic Air 2 hybrid orchestrator; HARDWARE_OVERRIDES registry suppression; 180s fallback guard. |
| `cli.py` | `skyherd-demo-hw` CLI — `play --prop [coyote|sick_cow|combo]` sub-commands. |

---

## Tests (`tests/`)

| Module | What it covers |
|--------|---------------|
| `test_smoke.py` | Top-level import smoke test — all packages importable. |
| `world/` | Clock, herd stepping, predator spawning, weather state, determinism (5 files). |
| `sensors/` | Each of the 7 emitters + bus + registry (12 files). |
| `agents/` | Cost tracker, FenceLineDispatcher, HerdHealthWatcher, mesh smoke, neighbor mesh, session, spec, webhook routing (8 files). |
| `mcp/` | Drone/sensor/rancher/galileo MCP servers + wiring (5 files). |
| `vision/` | Renderer, pipeline, 7 heads, annotator (10 files). |
| `scenarios/` | All 5 scenarios + cross-ranch + determinism + run-all (10 files). |
| `attest/` | Ledger, signer, CLI (3 files). |
| `voice/` | Wes, TTS, call, humanize, get_backend (5 files). |
| `server/` | FastAPI app + SSE events (2 files). |
| `drone/` | SITL smoke, stub, mavic, F3-iNav, interface, safety (6 files). |
| `edge/` | Camera, watcher, fleet, heartbeat (4 files). |
| `hardware/` | Collar payload decode, Mavic protocol (2 files). |
| `demo/` | Hardware-only flow, fallback sim, overrides registry (3 files). |

---

## Web (`web/`)

| File | Purpose |
|------|---------|
| `src/App.tsx` | Root SPA component — routes between dashboard (`/`) and rancher PWA (`/rancher`). |
| `src/routes.tsx` | React Router route definitions. |
| `src/lib/sse.ts` | SSE client hook — connects to `/events`, dispatches world snapshots to component tree. |
| `src/lib/cn.ts` | Tailwind class merge utility. |
| `src/components/AgentLane.tsx` | Single agent log lane — name, status badge, last-N events. |
| `src/components/AgentLanes.tsx` | Five-lane grid wrapper. |
| `src/components/RanchMap.tsx` | SVG ranch map — cattle positions, drone, paddock boundaries, water tanks. |
| `src/components/CostTicker.tsx` | Live cost ticker — $/hr rate, pauses on idle, flashes on agent activity. |
| `src/components/AttestationPanel.tsx` | Attestation chain panel — last N entries with hash prefix. |
| `src/components/RancherPhone.tsx` | `/rancher` PWA — Wes call alert, Answer/Dismiss, drone feed, agent reasoning log. |
| `src/components/CrossRanchView.tsx` | Cross-ranch mesh view — ranch_a / ranch_b agent status side-by-side. |
| `src/components/ui/` | Shadcn-style primitives: badge, button, card, sheet, table, tooltip. |
| `src/sw.ts` | Service worker — offline-first PWA cache for `/rancher`. |
| `vite.config.ts` | Vite config — React plugin, proxy `/api` + `/events` to FastAPI, PWA manifest. |

---

## Hardware (`hardware/`, `android/`, `ios/`)

| Path | Purpose |
|------|---------|
| `hardware/collar/firmware/src/main.cpp` | PlatformIO LoRa collar firmware — GPS+IMU read, LoRaWAN uplink, deep-sleep cycle. |
| `hardware/collar/provisioning/register-collar.py` | ChirpStack device registration script for new collar nodes. |
| `hardware/collar/provisioning/decode_payload.py` | CayenneLPP payload decoder for collar uplinks. |
| `hardware/collar/BOM.md` | Bill of materials — RAK4631, u-blox M8, LSM6DS3, 3D-print shell. |
| `hardware/collar/3d_print/collar_shell.scad` | OpenSCAD parametric collar shell. |
| `android/SkyHerdCompanion/` | Kotlin Android app — DJI SDK V5 + Paho MQTT + GeofenceChecker + BatteryGuard + WindGuard. Entry: `MainActivity.kt`. |
| `ios/SkyHerdCompanion/Sources/SkyHerdCompanion/App.swift` | Swift iOS app entry — DJI SDK V5 + CocoaMQTT companion. |
| `ios/SkyHerdCompanion/Sources/SkyHerdCompanion/DJIBridge.swift` | DJI SDK V5 bridge — mission upload, telemetry, RTH trigger. |
| `ios/SkyHerdCompanion/Sources/SkyHerdCompanion/SafetyGuards.swift` | iOS safety guards — mirrors Android GeofenceChecker + BatteryGuard logic. |

---

## Docs (`docs/`, `skills/`, `worlds/`)

| File | Purpose |
|------|---------|
| `docs/ONE_PAGER.md` | 500-word judge one-pager — what SkyHerd is, why it wins. |
| `docs/ONE_PAGER.pdf` | PDF render of ONE_PAGER.md (WeasyPrint, 24 KB). |
| `docs/ARCHITECTURE.md` | 5-layer nervous-system pattern, data flow, attestation chain design. |
| `docs/MANAGED_AGENTS.md` | $5k prize essay — 5-agent mesh, idle-pause economics, long-idle wait design. |
| `docs/CROSS_RANCH_MESH.md` | Cross-ranch mesh design — NeighborBroadcaster protocol, ranch_b integration. |
| `docs/HARDWARE_DEMO_RUNBOOK.md` | 60-second hardware-only hero demo — 2 Pi + Mavic Air 2, shot list, coyote prop. |
| `docs/HARDWARE_PI_EDGE.md` | Pi H1 edge runtime setup — camera, detector, MQTT publish, systemd install. |
| `docs/HARDWARE_PI_FLEET.md` | Pi + Galileo fleet commissioning guide — `edge-house` (Pi 4 camera edge) + `edge-tank` (Galileo Gen 1 telemetry) provisioning. |
| `docs/HARDWARE_GALILEO.md` | Intel Galileo Gen 1 `edge-tank` runbook — water-tank + weather telemetry, mraa wiring, sim-mode fallback. |
| `docs/HARDWARE_MAVIC_PROTOCOL.md` | Mavic Air 2 WebSocket protocol spec — command schema, telemetry schema, safety interlocks. |
| `docs/HARDWARE_MAVIC_ANDROID.md` | Android companion setup + DJI SDK V5 integration guide. |
| `docs/HARDWARE_MAVIC_IOS.md` | iOS companion setup + XcodeGen + CocoaMQTT integration guide. |
| `docs/HARDWARE_F3_INAV.md` | SP Racing F3 iNav backend — USB serial setup, MSP protocol, safety config. |
| `docs/HARDWARE_COLLAR.md` | DIY LoRa collar — PlatformIO flash, ChirpStack registration, decode payload. |
| `docs/REPLAY_LOG.md` | Deterministic scenario replay log — event-by-event output of `make demo SEED=42`. |
| `docs/verify-latest.md` | Automated truth-check snapshot — lint, test, sim gate, agent mesh, dashboard DOM. |
| `docs/demo-assets/shot-list.md` | Hardware demo shot list — camera angles, props, timing marks. |
| `docs/demo-assets/coyote-silhouette.svg` | Coyote prop SVG — print + cut for fence-line demo. |
| `skills/README.md` | 33-file skills inventory — index with one-line purpose per skill. |
| `skills/cattle-behavior/` | 5 cattle behavior skills + 7 disease sub-skills (CrossBeam domain knowledge pattern). |
| `skills/predator-ids/` | 5 predator identification skills (coyote, mountain lion, wolf, LGD, thermal). |
| `skills/ranch-ops/` | 5 ranch operations skills (fence, water, paddock, Part 107, human-in-loop). |
| `skills/nm-ecology/` | 4 New Mexico ecology skills (predator ranges, forage, seasonal calendar, weather). |
| `skills/drone-ops/` | 4 drone operations skills (patrol planning, deterrent, battery economics, no-fly zones). |
| `skills/voice-persona/` | 3 Wes voice persona skills (register, urgency tiers, never-panic). |
| `worlds/ranch_a.yaml` | Ranch A world config — paddock layout, cattle count, sensor placement, GPS bounds. |
| `worlds/ranch_b.yaml` | Ranch B world config — second ranch for cross-ranch mesh demo. |
