# Codebase Concerns — Honest Gap Analysis

**Analysis Date:** 2026-04-22
**Methodology:** Skeptical ground-truth audit. PROGRESS.md and CLAUDE.md claims NOT trusted; every gate item verified by running code or reading implementation.

---

## 1. Per-Subsystem Completeness Audit

### `src/skyherd/world/` — **IMPLEMENTED**
Deterministic seed=42 replay verified by direct execution: two identical runs produce byte-identical event streams. `make_world()` requires `config_path` argument (not default-arg friendly, callers must pass `worlds/ranch_a.yaml`). World has Clock, Terrain, Herd, PredatorSpawner, WeatherDriver. `world.py` 100% covered.

### `src/skyherd/sensors/` — **IMPLEMENTED (7 emitters)**
All 7 sensor emitters present: `water.py`, `trough_cam.py`, `thermal.py`, `fence.py`, `collar.py`, `acoustic.py`, `weather.py`. Registry in `sensors/registry.py` wires them via asyncio tasks onto an MQTT bus. Hardware-override support (`HARDWARE_OVERRIDES` env var) allows real Pi nodes to displace specific sim emitters. Silent `except` blocks on publish errors in `acoustic.py:72,82`, `trough_cam.py:94`, `bus.py:201,269` swallow exceptions without logging.

### `src/skyherd/agents/` — **IMPLEMENTED (with critical caveat)**

All 5 agents present and functional in simulation path:
- `fenceline_dispatcher.py` — IMPLEMENTED
- `herd_health_watcher.py` — IMPLEMENTED
- `predator_pattern_learner.py` — IMPLEMENTED
- `grazing_optimizer.py` — IMPLEMENTED
- `calving_watch.py` — IMPLEMENTED

**Real Managed Agents API:** `managed.py` uses `client.beta.{agents,sessions,environments}.*` with proper beta header (automatically applied by SDK). `ensure_agent()`, `create_session_async()`, `send_wake_event()`, `stream_session_events()` all implemented and tested at 88% coverage.

**CRITICAL: Session-per-event leak in demo runner.** `src/skyherd/scenarios/base.py:179` creates a brand new `SessionManager()` and session for EVERY single agent dispatch call. The coyote scenario alone creates 241 sessions (verified by running `skyherd-demo play coyote --seed 42`). In the real MA runtime this would create 241 platform agent/session pairs. This is not a valid multi-session persistent agent architecture — it is a stateless function call disguised as session-based agents. The demo "passes" only because simulation handlers don't use real API calls.

**PredatorPatternLearner absent from scenario base routing table.** `src/skyherd/scenarios/base.py:326-337` routing dict has no entry for `thermal.anomaly` or `skyherd/+/cron/nightly` — PredatorPatternLearner's declared wake topics. The rustling scenario works only because the event is already injected in the event stream and assertions check event presence, not that the agent was actually dispatched. `_registry` dict at line 234 also omits `PredatorPatternLearner`.

**Skills consumed correctly:** Each agent spec declares a `skills` list with relative paths (e.g. `skills/predator-ids/coyote.md`). `_load_text()` reads and includes them in cached messages. This is real CrossBeam-style usage.

**Tool bindings:** MCP tools defined with `@tool` decorator in `src/skyherd/mcp/*.py` and wired via `claude_agent_sdk.McpSdkServerConfig`. Tools call actual `DroneBackend`, Twilio, ElevenLabs — real implementations. MCP coverage: drone 83%, rancher 81%, galileo 90%, sensor 94%.

### `skills/` — **IMPLEMENTED (34 files, claimed 33)**
Actual count is 34 files (not 33 as claimed). Organized into 6 subdirectories: `cattle-behavior/` (13 files including 7 disease subdirectory), `drone-ops/` (4), `nm-ecology/` (4), `predator-ids/` (5), `ranch-ops/` (5), `voice-persona/` (3). Each file is substantive (~4-5KB), written in rancher domain language, references specific thresholds (discharge scores, temp ranges, etc). CrossBeam pattern usage is genuine — files are loaded into prompt cache prefix.

### `src/skyherd/mcp/` — **IMPLEMENTED**
Four MCP servers present: `drone_mcp.py`, `sensor_mcp.py`, `rancher_mcp.py`, `galileo_mcp.py`. Tools are real Claude-callable functions with validation. `rancher_mcp.py` calls Twilio when env vars present, falls back to JSONL log. `drone_mcp.py` delegates to `DroneBackend` interface. No placeholders or TODO stubs found in these files.

### `src/skyherd/vision/` — **IMPLEMENTED (rule-based, not neural)**
All 7 disease heads present: `pinkeye.py`, `screwworm.py`, `foot_rot.py`, `brd.py`, `lsd.py`, `heat_stress.py`, `bcs.py`. Each head is a deterministic threshold classifier operating on `Cow` object attributes (discharge score, disease_flags, etc.) — NOT a neural network, NOT MegaDetector V6. The claim of "7 disease-detection heads running on synthetic frames" is technically fulfilled but misleading: these are rule engines on structured sim data, not vision model inference on pixel data. `renderer.py` generates synthetic PNG frames (PIL-based), but heads never actually process image pixels. All heads 100% covered, `pipeline.py` 100%.

### `src/skyherd/drone/` — **IMPLEMENTED (Tier 1 SITL requires external process)**
`SitlBackend` (`sitl.py`) implements real MAVSDK-Python calls: `arm()`, `takeoff()`, `mission upload`, `start_mission()`, `return_to_launch()`. Requires `make sitl-up` (Docker + ~25-40 min first build from source, or pre-built image via `SITL_IMAGE` env var). A pure-Python emulator (`sitl_emulator.py`, 742 lines) enables in-process testing without the Docker container. Stub, Mavic, f3_inav, and pymavlink backends also present. `SitlBackend.play_deterrent()` while on the ground only logs intent and sleeps — no actual audio output. SITL tests skip cleanly when Docker not running. No test runs the actual SITL Docker path in CI.

### `src/skyherd/attest/` — **IMPLEMENTED**
Real SQLite-backed Merkle-chained ledger with Ed25519 signatures. `ledger.py` uses `blake2b` hash chaining with `hmac.compare_digest`. `signer.py` uses `cryptography` library Ed25519 keypairs. 97% and 98% coverage respectively. Verify chain command exists in `cli.py`.

### `src/skyherd/voice/` — **IMPLEMENTED**
TTS fallback chain: ElevenLabs → piper → espeak → SilentBackend. `wes.py` applies Wes-persona text transformation before synthesis. `call.py` uses Twilio for real voice calls when env vars set; falls back to WAV playback via `subprocess`. Uncovered lines are in the Twilio live-call branch (lines 63-65, 73) — only reachable with real credentials.

### `src/skyherd/scenarios/` — **IMPLEMENTED (8 scenarios, all PASS)**
Eight scenarios run and pass: `coyote`, `sick_cow`, `water_drop`, `calving`, `storm`, `cross_ranch_coyote`, `wildfire`, `rustling`. All pass `make demo SEED=42 SCENARIO=all` in ~3 seconds wall time total. Replay JSONL files written. NOTE: "5 demo scenarios" in CLAUDE.md is understated — 8 scenarios exist including 3 bonus ones (cross-ranch, wildfire, rustling).

**Determinism caveat:** Scenarios are deterministic in event counts and tool-call structure but not byte-identical at JSONL hash level (wall timestamps vary). The `test_demo_seed42_is_deterministic` test in `tests/test_determinism_e2e.py` sanitizes timestamps before hashing, so the test passes but "byte-identical" is a soft claim.

### `src/skyherd/server/` — **IMPLEMENTED (live path partially covered)**
FastAPI app with `/health`, `/api/snapshot`, `/api/agents`, `/api/attest`, `/events` (SSE), `/metrics`, SPA serving. `SKYHERD_MOCK=1` enables fully synthetic event generation — this is what `make dashboard` uses. Live path (real mesh + world + ledger injection) at `app.py:88-94, 164-181, 189-195` is 73% covered. `events.py` live broadcaster path (lines 293-315, 349-370) is 76% covered. CORS defaults to localhost-only, SSE capped at 100 connections.

### `web/` — **HIGH QUALITY (judge-worthy)**
Custom dark ops-console aesthetic. Design system uses Tailwind v4 `@theme` tokens (not stock shadcn defaults): `--color-bg-0: rgb(10 12 16)`, sage/dust/thermal accent palette, three variable fonts (Fraunces for display, Inter body, JetBrains Mono). `RanchMap` is a custom Canvas 2D renderer (~250 lines) with RAF loop, drone motion trail, forage bars, paddock fills, predator pulse ring — not a library map. `AgentLane.tsx` is custom ops-console styling. `RancherPhone.tsx` is 497 lines, phone-first dark layout. PWA manifest and service worker (`sw.ts`) present. UI is genuinely polished, not placeholder.

No TODOs found in web source files.

### `android/SkyHerdCompanion/` — **PARTIAL (functional scaffold, no tests)**
5 Kotlin files (MainActivity, SkyHerdApp, MQTTBridge, DroneControl, SafetyGuards). DJI SDK V5 referenced as import. Real MQTT + coroutine wiring. No tests. `app/src/main/` has only `main/` directory with no layout XMLs found. Build likely fails without DJI SDK credentials/license. Not buildable out of the box.

### `ios/SkyHerdCompanion/` — **PARTIAL (functional scaffold, 3 tests)**
10 Swift source files (App, ContentView, DJIBridge, MQTTBridge, CommandRouter, SafetyGuards, AppState, Models, Config, Logging). 3 test files present (SafetyGuardTests, CommandRouterTests, ProtocolTests). XcodeGen project.yml present. DJI SDK V5 referenced. Not buildable without DJI SDK and Xcode.

### `hardware/collar/` — **IMPLEMENTED**
Real 312-line PlatformIO firmware (`firmware/src/main.cpp`) for RAK3172 (STM32WL53 + LoRaWAN). Reads TinyGPS++, MPU-6050 IMU, battery ADC. 16-byte LoRaWAN payload struct documented. Deep-sleep cycle implemented. Secrets in `secrets.h` (gitignored). BOM.md, wiring diagrams, 3D print directory present.

---

## 2. Sim Completeness Gate Re-Audit

| Gate Item | Claimed | Actual Verdict |
|-----------|---------|----------------|
| All 5 Managed Agents live and cross-talking via shared MQTT | TRULY-GREEN | **YELLOW** — agents exist and have MA wiring, but demo path creates a fresh session per event rather than persistent sessions. Cross-talk works in `mesh_neighbor.py`. |
| All 7+ sim sensors emitting | TRULY-GREEN | **GREEN** — 7 sensor emitters confirmed, bus registry wires them correctly. |
| Disease-detection heads running on synthetic frames | TRULY-GREEN | **YELLOW** — 7 heads confirmed, but "running on synthetic frames" is misleading: they operate on structured `Cow` object attributes, not image pixels. No pixel-level inference. |
| ArduPilot SITL drone executing real MAVLink missions | TRULY-GREEN | **YELLOW** — code is real MAVSDK, but requires Docker SITL container that takes 25-40 min to build. Demo scenarios use `StubBackend` by default, not SITL. CI does not test SITL path. |
| Dashboard: ranch map + 5 agent lanes + cost ticker + attestation + rancher PWA | TRULY-GREEN | **GREEN** — all panels present, polished, real SSE wiring. |
| Wes voice end-to-end | TRULY-GREEN | **GREEN** — chain confirmed. Twilio + ElevenLabs + piper + espeak + silent fallback all wired. Live path requires credentials. |
| 5 scenarios playable back-to-back | TRULY-GREEN | **GREEN** (and then some — 8 scenarios all pass). |
| Deterministic replay `make sim SEED=42` | TRULY-GREEN | **GREEN** — world events byte-identical; scenario outcomes sanitized-deterministic. |
| Fresh-clone `make sim` boots on second machine | TRULY-GREEN | **UNVERIFIABLE** — depends on `uv sync` success and `worlds/ranch_a.yaml` presence. Both exist. Plausible. |
| Cost ticker visibly pauses during idle | TRULY-GREEN | **GREEN** — `cost.py` returns `None` on idle ticks; mock generator emits `rate_per_hr_usd: 0.0` and `all_idle: True`. |

---

## 3. Tech Debt, TODOs, FIXMEs

No explicit `TODO`, `FIXME`, `XXX`, or `HACK` comments found in `src/` or `web/`. The pattern used instead is silent `except: pass` blocks:

- `src/skyherd/sensors/acoustic.py:72,82` — silently swallows MQTT publish errors
- `src/skyherd/sensors/bus.py:201,269` — silent pass on bus errors
- `src/skyherd/sensors/trough_cam.py:94` — silent pass
- `src/skyherd/agents/mesh.py:163,170` — silent agent wake errors
- `src/skyherd/agents/fenceline_dispatcher.py:153` — silent pass after simulate check
- `src/skyherd/scenarios/base.py:312` — silent `os.unlink` failure
- `src/skyherd/server/events.py:299,315` — silent SSE disconnect handling
- `src/skyherd/drone/f3_inav.py:370,377,386,393,400` — five consecutive silent passes in serial framing
- `src/skyherd/drone/sitl_emulator.py:445,466,742` — silent UDP receive errors
- `src/skyherd/voice/tts.py:195` — silent subprocess error
- `src/skyherd/edge/watcher.py:111,238,323,454,480` — multiple silent passes in Pi runtime

---

## 4. Security + Secrets Hygiene

- `.env.local` EXISTS at project root. It is listed in `.gitignore` under `.env.local` (confirmed). Currently NOT tracked by git (clean `git status`). Contents not read.
- `.env.example` is committed — contains placeholder values only (correct practice).
- No hardcoded API keys or tokens found in source. All secrets via `os.environ.get()`.
- Twilio credentials referenced as `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM` — note two different env var names for Twilio auth token: `TWILIO_TOKEN` in `call.py:44,68` vs `TWILIO_AUTH_TOKEN` in `rancher_mcp.py` — inconsistency that will silently fail one path.
- CORS locked to localhost origins; no wildcard `*` (confirmed in `app.py:71`).
- No SQL injection vectors (SQLite calls use parameterized queries in `ledger.py`).
- `hardware/collar/firmware/src/main.cpp` includes `secrets.h` which is gitignored — correct.
- `firmware/src/` has no `secrets.h` committed (correct).

---

## 5. Build Health

| Command | Status | Notes |
|---------|--------|-------|
| `make demo SEED=42 SCENARIO=all` | **PASSES** | 8 scenarios all PASS, ~3s wall |
| `make test` | **PASSES** | 1106 passed, 13 skipped, 0 failed; 87.42% coverage |
| `make dashboard` | **PASSES** (mock) | Requires `pnpm` + prior `web/dist` build; uses `SKYHERD_MOCK=1` |
| `make sitl-up` | **ASPIRATIONAL** | Requires Docker; first build 25-40 min; not tested in CI |
| `make hardware-demo` | **ASPIRATIONAL** | Requires physical Pi + Mavic hardware |
| `make mesh-smoke` | **PASSES** (stub) | Uses stub SDK when no API key |
| `uv run pyright` | **UNKNOWN** (not run in this audit) | |

---

## 6. Top 10 Most Urgent Gaps

**Priority 1 — Session-per-event architecture breaks live agent persistence**
- Files: `src/skyherd/scenarios/base.py:169-183`
- `_DemoMesh.dispatch()` instantiates a fresh `SessionManager()` and calls `create_session()` for every single agent invocation. One coyote scenario creates 241 sessions. In the real Managed Agents platform this would create 241 separate platform sessions with separate billing, no shared context. The demo only "works" because simulation handlers are stateless functions. Fix: Create sessions once at scenario/mesh startup and reuse them across dispatch calls.

**Priority 2 — PredatorPatternLearner never dispatched in scenario runner**
- Files: `src/skyherd/scenarios/base.py:234-237`, `src/skyherd/scenarios/base.py:326-337`
- `_registry` dict omits `PredatorPatternLearner`. Routing table has no entry for `thermal.anomaly` or `skyherd/+/cron/nightly`. The rustling scenario passes assertions by checking event presence in the injected stream, not that the agent was called. Fix: Add `PredatorPatternLearner` to `_registry` and add `"thermal.anomaly": ["FenceLineDispatcher", "PredatorPatternLearner"]` to routing.

**Priority 3 — Vision heads are rule engines, not pixel classifiers**
- Files: `src/skyherd/vision/heads/*.py`, `src/skyherd/vision/pipeline.py`
- All 7 "disease-detection heads" classify based on `Cow.ocular_discharge`, `Cow.disease_flags`, etc. — structured attributes, not image pixels. `renderer.py` generates PNG frames but `classify()` never reads them. MegaDetector V6 is listed in pyproject.toml implicitly (via supervision) but never imported. For a video demo, `pipeline.py` does produce annotated PNGs. The framing as "vision model heads" will be scrutinized by judges if any video shows them. Impact: narrative credibility, not build health.

**Priority 4 — SITL MAVLink path untested in CI**
- Files: `docker-compose.sitl.yml`, `src/skyherd/drone/sitl.py`, `tests/drone/`
- `make sitl-up` requires Docker + 25-40 min build. No CI job runs the SITL container. All drone tests use the in-process `MavlinkSitlEmulator` or `StubBackend`. The claim "SITL drone executing real MAVLink missions" is true in code but has no automated verification path a judge can run in under 5 min. Fix: Add `SITL_IMAGE=ardupilot/ardupilot-sitl:Copter-4.5.7` to CI env and add a fast SITL smoke test job.

**Priority 5 — Twilio auth env var name inconsistency**
- Files: `src/skyherd/voice/call.py:44,68` (uses `TWILIO_TOKEN`), `src/skyherd/mcp/rancher_mcp.py` (uses `TWILIO_AUTH_TOKEN`)
- One path will silently fail to authenticate with Twilio because it reads a different env var. Fix: Standardize on `TWILIO_AUTH_TOKEN` everywhere and update `.env.example`.

**Priority 6 — Server live path (non-mock) has 27% uncovered lines**
- Files: `src/skyherd/server/app.py:88-94, 119-120, 164-181, 189-195, 212, 216, 221-224`; `src/skyherd/server/events.py:293-315, 349-370, 386-393`
- The paths that inject real `mesh`, `world`, and `ledger` into the FastAPI app (non-mock mode) are not tested. `make dashboard` always uses `SKYHERD_MOCK=1`. A live integrated run of the full stack (sensors + agents + dashboard) has no automated test. Fix: Add an integration test that starts the app with a real world+ledger but stubbed mesh, verifies `/api/snapshot` returns real sim data.

**Priority 7 — Silent exception swallowing hides runtime failures**
- Files: `src/skyherd/sensors/acoustic.py:72,82`, `src/skyherd/sensors/bus.py:201,269`, `src/skyherd/drone/f3_inav.py:370,377,386,393,400`, `src/skyherd/edge/watcher.py:111,238,323,454,480`
- 15+ bare `except: pass` or `except Exception: pass` blocks with no logging. In a demo run, a dropped MQTT publish or failed sensor read will produce no visible error while silently losing data. Fix: Replace with `except Exception as exc: logger.warning(...)`.

**Priority 8 — Android app not buildable without DJI SDK**
- Files: `android/SkyHerdCompanion/app/src/main/kotlin/com/skyherd/companion/MainActivity.kt`
- `import dji.v5.manager.SDKManager` requires DJI developer account + SDK license. No test coverage. No README step for DJI SDK setup. Judges who try to build it will fail. Fix: Add DJI SDK setup instructions to android README; add a no-DJI fallback stub.

**Priority 9 — `agents/cost.py` at 78% coverage with billing logic untested**
- Files: `src/skyherd/agents/cost.py:165-170, 174-177, 187, 191, 205-216`
- The cost ticker's idle-pause logic and cumulative USD tracking paths are not fully tested. If cost accounting breaks live, the "cost ticker pauses during idle" demo moment fails silently. Fix: Add tests for idle-state ticking, active-state delta accumulation, and the `all_idle` aggregation path.

**Priority 10 — `make_world()` signature requires explicit `config_path`**
- Files: `src/skyherd/world/world.py` (no `make_world` default), `src/skyherd/scenarios/base.py:223`
- `make_world(seed=42)` raises `TypeError: missing 1 required positional argument: 'config_path'`. Any code outside the scenarios module that tries to use the canonical judge quickstart invocation without knowing the config path will fail immediately. `make sim` works because it passes `--seed` only via the CLI, which internally resolves the path. Fix: Give `config_path` a default that resolves relative to the package (e.g. `Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"`).

---

## Security Considerations

**Twilio auth token naming inconsistency:**
- Risk: Silent Twilio auth failure in one code path
- Files: `src/skyherd/voice/call.py:44,68`, `src/skyherd/mcp/rancher_mcp.py`
- Current mitigation: Both paths fall back to local JSONL log on failure
- Recommendation: Standardize on `TWILIO_AUTH_TOKEN`

**`.env.local` present but gitignored:**
- Risk: Low (file is correctly gitignored)
- Current mitigation: `.gitignore` entry confirmed

---

## Test Coverage Gaps

**`src/skyherd/agents/simulate.py` — 76% (lines 70, 84-88, 116-120, 161, 241-243, 267, 289, 355-359)**
- Uncovered: edge cases in simulation handlers — unusual event types not exercised by current scenario suite.

**`src/skyherd/agents/mesh.py` — 78% (lines 155-156, 198-200, 224-253)**
- Uncovered: real MQTT mesh startup, live session wake/sleep cycles with real pub/sub.

**`src/skyherd/agents/cost.py` — 78% (lines 165-170, 174-177, 187, 191, 205-216)**
- Uncovered: idle-pause billing logic, cumulative cost aggregation across multiple sessions.

**`src/skyherd/server/app.py` — 73%`**
- Uncovered: live (non-mock) app startup with real mesh/world injection.

**`src/skyherd/server/events.py` — 76%**
- Uncovered: real mesh broadcaster, live MQTT relay, non-mock SSE event paths.

---

*Concerns audit: 2026-04-22*
