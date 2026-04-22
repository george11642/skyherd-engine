# External Integrations

**Analysis Date:** 2026-04-22

---

## Status Key

- **IMPLEMENTED** — code exists, wires to real API, tested path confirmed
- **PARTIAL** — code exists but has fallback/stub that activates in most run paths
- **STUB** — code exists but does not reach the real API in any reachable path
- **MISSING** — claimed in docs/CLAUDE.md but no implementation found in source

---

## Anthropic / Claude Agent SDK

**Claude Managed Agents Platform — IMPLEMENTED (with conditional activation)**

The managed-agents beta API (`client.beta.agents`, `client.beta.sessions`, `client.beta.environments`) is implemented with real API calls in `src/skyherd/agents/managed.py`. The handler base in `src/skyherd/agents/_handler_base.py:87` dispatches to the managed path when `SKYHERD_AGENTS=managed` is set AND the session has a `platform_session_id`.

- `ManagedSessionManager` at `src/skyherd/agents/managed.py:110` calls:
  - `client.beta.environments.create()` at line 185
  - `client.beta.agents.create()` at line 216
  - `client.beta.sessions.create()` at line 240
  - `client.beta.sessions.events.send()` at line 376
  - `client.beta.sessions.events.stream()` at line 388
- Beta header note: per docstring at `managed.py:8`, the SDK adds `managed-agents-2026-04-01` automatically on every `client.beta.*` call — no manual injection
- Tool type used: `{"type": "agent_toolset_20260401"}` at `managed.py:222`
- Webhook receiver at `src/skyherd/agents/webhook.py` mounts at `/webhooks/managed-agents` with HMAC-SHA256 signature verification (SKYHERD_WEBHOOK_SECRET env var)

**Default runtime is LOCAL (simulation), not managed.** The `get_session_manager()` factory at `src/skyherd/agents/session.py:392` only activates `ManagedSessionManager` when both `ANTHROPIC_API_KEY` is set AND `SKYHERD_AGENTS=managed`. Without those vars, `LocalSessionManager` (emulation shim) runs.

**Claude Agent SDK — IMPLEMENTED**

`claude-agent-sdk` 0.1.64 (PyPI, uploaded 2026-04-20) is the live SDK. All 4 MCP servers import from it:
- `src/skyherd/mcp/drone_mcp.py:14` — `from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool`
- `src/skyherd/mcp/sensor_mcp.py:15`
- `src/skyherd/mcp/rancher_mcp.py:18`
- `src/skyherd/mcp/galileo_mcp.py:15`

**Anthropic messages API (local runtime) — IMPLEMENTED**

When running locally with an API key but not in managed mode, `_handler_base.py:97` calls `_run_local_with_cache()` which uses `client.messages.create()` with `cache_control` blocks via `build_cached_messages()` at `src/skyherd/agents/session.py:110`.

**Required env vars:**
- `ANTHROPIC_API_KEY` — required for any live API call
- `SKYHERD_AGENTS=managed` — activates managed platform path

---

## MQTT (Mosquitto / amqtt)

**Status: IMPLEMENTED**

`SensorBus` at `src/skyherd/sensors/bus.py` implements the MQTT publish/subscribe bus with `aiomqtt` 2.x as client.

- Embedded broker: when `MQTT_URL` is not set, an in-process `amqtt` broker starts on `localhost:1883` (`bus.py:62`). This is the default for local development.
- External broker: when `MQTT_URL=mqtt://...` is set, connects to that broker. This is the Mosquitto path for production.
- All 7 sensor emitters publish to `skyherd/{ranch_id}/{sensor_type}/{entity_id}` topics
- `SensorBus.subscribe()` is an async context manager for consuming messages
- Reconnect with exponential back-off (1s→2s→4s→...→30s cap) at `bus.py:211`
- Ring buffer of last 256 readings per kind in module-level `_BUS_STATE` at `bus.py:43`

**Required env vars:**
- `MQTT_URL` — optional; if absent, embedded broker is used

---

## ChirpStack LoRaWAN

**Status: MISSING (from Python code) / REFERENCED only in skills and docs**

ChirpStack is present as a git submodule reference at `.refs/chirpstack/` (Rust codebase, not integrated). No Python source in `src/` imports or connects to ChirpStack. LoRa is mentioned only:
- In `src/skyherd/sensors/collar.py:19` as a comment (`real LoRa is ~0.01%/hr`)
- In skill files (`skills/ranch-ops/water-tank-sops.md:10`, `skills/ranch-ops/fence-line-protocols.md:10`) as domain context

The collar sensor (`src/skyherd/sensors/collar.py`) and fence sensor (`src/skyherd/sensors/fence.py`) are pure simulators emitting synthetic MQTT payloads with no real LoRaWAN radio interface.

---

## Twilio (Voice Calls)

**Status: PARTIAL — implemented but dashboard-ring is the actual default**

Twilio integration is real and functional when credentials are configured. Implementation in `src/skyherd/voice/call.py`.

- `twilio.rest.Client` imported at `call.py:62` via try/except (soft dependency)
- Calls `client.calls.create(to=..., from_=..., twiml=...)` with TwiML `<Play>` pointing to WAV
- But `_demo_mode()` at `call.py:49` returns `True` when `DEMO_PHONE_MODE=dashboard` (the default in `.env.example`)
- Even when Twilio creds are present, actual calls are only placed if `DEMO_PHONE_MODE != "dashboard"` AND `message.urgency in ("call", "emergency")` at `call.py:151`
- WAV delivery requires `CLOUDFLARE_TUNNEL_URL` env var to expose the file publicly (`call.py:70`)
- Fallback: writes to `runtime/phone_rings.jsonl` and emits a `rancher.ringing` SSE event for the PWA

Also used in `src/skyherd/mcp/rancher_mcp.py` for `page_rancher` tool (Twilio SMS path not yet visible from a brief read; rancher_mcp mainly writes to `runtime/rancher_pages.jsonl`)

**Required env vars:**
- `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_FROM` — for real calls
- `CLOUDFLARE_TUNNEL_URL` — to expose WAV files to Twilio's callback
- `DEMO_PHONE_MODE=twilio` — override default dashboard mode
- `RANCHER_PHONE` — defaults to `+15055550100` (fake number)

---

## ElevenLabs (TTS)

**Status: PARTIAL — real backend selected only when API key is present**

`ElevenLabsBackend` at `src/skyherd/voice/tts.py:66` uses the official `elevenlabs` SDK 2.44.0.

- Calls `client.text_to_speech.convert()` at `tts.py:77`
- Returns MP3 bytes, converts to WAV via pydub/ffmpeg fallback at `tts.py:178`
- Voice ID: `pNInz6obpgDQGcFmaJgB` (Adam premade, free-tier) — configurable via `ELEVENLABS_VOICE_ID`
- Model: `eleven_multilingual_v2` — configurable via `ELEVENLABS_MODEL_ID`
- Backend selection via `get_backend()` at `tts.py:240`: ElevenLabs → piper → espeak → SilentBackend
- Without `ELEVENLABS_API_KEY`, silently falls back to piper, then espeak, then a 250ms silence WAV (CI-safe)

**Required env vars:**
- `ELEVENLABS_API_KEY` — for real TTS; without it, falls through to offline backends

---

## ArduPilot SITL / MAVSDK

**Status: IMPLEMENTED (SitlBackend) + requires external Docker container**

`SitlBackend` at `src/skyherd/drone/sitl.py` uses `mavsdk` 3.15.3 to connect to ArduPilot SITL on `udpin://0.0.0.0:14540`.

- Implements full `DroneBackend` interface: `connect`, `takeoff`, `patrol` (MAVLink mission upload), `return_to_home`, `play_deterrent`, `get_thermal_clip`, `state`
- `patrol()` uploads real MAVLink `MissionPlan` via `drone.mission.upload_mission()` at `sitl.py:187`
- `get_thermal_clip()` generates synthetic greyscale PNG (Gaussian blob), NOT real thermal data (`sitl.py:282`)
- `mavsdk` is lazy-imported at `sitl.py:74` — module loads without SITL running
- SITL container: `docker-compose.sitl.yml` (not yet read — exists per CI references)
- CI runs SITL E2E only on `workflow_dispatch` (not on every push)
- `SitlEmulatorBackend` at `src/skyherd/drone/sitl_emulator.py` is a lightweight emulator for CI without Docker (used via `SITL_EMULATOR=1`)

Backend is excluded from coverage: `pyproject.toml:115` omits `sitl.py`, `sitl_emulator.py`, `pymavlink_backend.py`.

---

## MegaDetector V6 / PytorchWildlife

**Status: PARTIAL — implemented with RuleDetector fallback (fallback activates in CI)**

`MegaDetectorHead` at `src/skyherd/edge/detector.py:80` wraps `PytorchWildlife.models.detection.MegaDetectorV6`.

- Lazy-initialises at `detector.py:106` via try/except
- Falls back silently to `RuleDetector` (brightness heuristic) when `PytorchWildlife` is not installed (`detector.py:114`)
- `PytorchWildlife` is in the `edge` optional extra (`pyproject.toml:70`) — NOT installed in the default `uv sync`
- The disease-detection heads in `src/skyherd/vision/heads/` are rule-based Python (no ML model) — they run in sim and CI

The vision pipeline (`src/skyherd/vision/pipeline.py`) uses rule-based heads, not `MegaDetectorHead`. `MegaDetectorHead` is used in the edge runtime (`src/skyherd/edge/watcher.py` and `detector.py`), which only runs on Raspberry Pi with `uv sync --extra edge`.

---

## DJI SDK V5 (Android Companion)

**Status: IMPLEMENTED (Android app) + PARTIAL (Python bridge)**

Android app at `android/SkyHerdCompanion/` uses DJI Mobile SDK V5 5.8.0:
- `dji-sdk-v5-aircraft` + `dji-sdk-v5-networkImp` in `gradle/libs.versions.toml:7`
- `SkyHerdApp.kt` registers the SDK on startup with `SDKManager.getInstance().init()` and handles callbacks
- `DroneControl.kt` (inferred, not read) bridges MQTT commands to DJI SDK calls

Python bridge: `MavicBackend` at `src/skyherd/drone/mavic.py` communicates with the Android app via WebSocket (`_WSTransport`). It sends JSON commands (`{"cmd": "takeoff", "args": {...}, "seq": N}`) and awaits ACK. No direct DJI SDK access from Python.

**Required env vars:**
- `MAVIC_WS_URL` — WebSocket URL of companion app, defaults to `ws://localhost:8765`
- `dji.sdk.api.key` — Gradle property for Android build, required for DJI SDK registration

---

## Cloudflare Tunnel

**Status: PARTIAL — env var consumed, tunnel management is external**

`CLOUDFLARE_TUNNEL_URL` is read at `src/skyherd/voice/call.py:70` to construct the WAV URL for Twilio TwiML `<Play>`. No code starts or manages the tunnel — that is expected to be an externally-running `cloudflared` process. Without this var, Twilio calls are skipped and dashboard-ring fallback is used.

---

## NOAA / External Weather APIs

**Status: MISSING**

No Python source connects to NOAA, NWS, open-meteo, OpenWeatherMap, or any external weather API. Weather state (`src/skyherd/world/weather.py`) is fully deterministic simulation driven by `WeatherDriver.schedule_storm()`. NOAA is mentioned only in skill reference docs (`skills/nm-ecology/weather-patterns.md:96-97`) as domain knowledge, not as a live data source.

---

## Data Storage

**Attestation Ledger:**
- SQLite (`src/skyherd/attest/ledger.py`) — Ed25519 Merkle-chained event ledger
- WAL mode + `synchronous=NORMAL` for crash safety
- Path: `runtime/ledger.db` (default)

**Runtime State:**
- JSONL flat files: `runtime/drone_events.jsonl`, `runtime/rancher_pages.jsonl`, `runtime/phone_rings.jsonl`, `runtime/sse_events.jsonl`
- Session checkpoints: `runtime/sessions/{session_id}.json`
- MA environment/agent IDs: `runtime/ma_environment_id.txt`, `runtime/agent_ids.json`

**File Storage:**
- Local filesystem only — thermal frames at `runtime/thermal/`, voice WAVs at `runtime/voice/`

**Caching:**
- None external (no Redis, Valkey, etc.)

---

## CI/CD & Deployment

**CI:**
- GitHub Actions at `.github/workflows/ci.yml`
- Matrix: Ubuntu + macOS × Python 3.11 + 3.12
- Jobs: lint (ruff), typecheck (pyright), tests (pytest 80% floor), web build (pnpm), pip-audit (weekly CVE scan)
- SITL E2E (`workflow_dispatch` only): emulator mode and Docker SITL smoke

**Hosting:**
- Web: `vercel.json` present at `web/vercel.json` — Vercel deployment configured
- Backend: no cloud deployment config found (FastAPI run locally or via `make dashboard`)

---

## Environment Variables Summary

| Var | Service | Default | Required for |
|-----|---------|---------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic | — | Any live API call |
| `SKYHERD_AGENTS` | Agent runtime | `local` | `=managed` for MA platform |
| `SKYHERD_WEBHOOK_SECRET` | Webhook HMAC | — | Production webhook security |
| `ELEVENLABS_API_KEY` | ElevenLabs | — | Real TTS |
| `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_FROM` | Twilio | — | Real voice calls |
| `CLOUDFLARE_TUNNEL_URL` | Cloudflare | — | Twilio WAV delivery |
| `DEMO_PHONE_MODE` | Call routing | `dashboard` | Set to `twilio` for real calls |
| `RANCHER_PHONE` | Twilio target | `+15055550100` | Real call target |
| `MQTT_URL` | MQTT broker | embedded | External Mosquitto |
| `DRONE_BACKEND` | Drone backend | `sitl` | `mavlink` for real drone |
| `MAVIC_WS_URL` | Android bridge | `ws://localhost:8765` | Mavic companion |
| `SKYHERD_MOCK` | Server mock mode | `0` | `=1` for no-hardware dashboard |

---

*Integration audit: 2026-04-22*
