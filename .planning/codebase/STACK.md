# Technology Stack

**Analysis Date:** 2026-04-22

## Languages

**Primary:**
- Python 3.11+ — all backend, sensors, agents, drone, attestation, voice
- TypeScript 5.8 — React SPA dashboard (`web/`)

**Secondary:**
- Kotlin 2.0 — Android companion app (`android/SkyHerdCompanion/`)
- Swift — iOS companion app (`ios/SkyHerdCompanion/`) — directory exists, not verified beyond scaffold

## Runtime

**Environment:**
- Python 3.11+ (matrix-tested against 3.11 and 3.12 in CI)
- Node 20 (web build), pnpm 9

**Package Manager:**
- Python: `uv` with hatchling build backend
- Lockfile: `uv.lock` — present and resolves to PyPI packages (not git sources)
- Web: `pnpm` — lockfile `web/pnpm-lock.yaml` present

## Frameworks

**Core:**
- FastAPI 0.136.0 — HTTP API + SSE (`src/skyherd/server/app.py`)
- uvicorn 0.45.0 — ASGI server with `[standard]` extras
- sse-starlette — SSE EventSourceResponse for `/events` endpoint
- React 19.1.0 — SPA dashboard (`web/src/`)
- Vite 6.3.5 — frontend build tool (`web/vite.config.ts`)
- Tailwind v4.1.7 — CSS utility framework (via `@tailwindcss/vite` plugin)

**Testing (Python):**
- pytest 8 + pytest-asyncio 0.24 — `asyncio_mode = "auto"` in pyproject.toml
- pytest-cov — 80% floor enforced (`fail_under = 80`)
- 111 test files across `tests/`

**Testing (Web):**
- Vitest 3.2.3 with `@vitest/coverage-v8`
- `@testing-library/react` 16.3.0

**Build/Dev:**
- ruff — lint + format (`line-length = 100`, `target-version = "py311"`)
- pyright — type checking
- pre-commit hooks present

## Key Dependencies

**Critical (resolved in uv.lock):**
- `anthropic` 0.96.0 — Anthropic SDK (supports `client.beta.*`)
- `claude-agent-sdk` 0.1.64 — Claude Agent SDK from PyPI (uploaded 2026-04-20); provides `McpSdkServerConfig`, `create_sdk_mcp_server`, `tool` decorator — used in all 4 MCP servers
- `aiomqtt` 2.x — async MQTT client (persistent publish client in `SensorBus`)
- `amqtt` — embedded MQTT broker used when `MQTT_URL` env var is unset
- `mavsdk` 3.15.3 — MAVSDK-Python for ArduPilot SITL (`SitlBackend`)
- `pymavlink` — alternative MAVLink backend (`pymavlink_backend.py`)
- `pydantic` 2.x — data models throughout
- `cryptography` 42-44 — Ed25519 signing in attestation chain (`src/skyherd/attest/signer.py`)

**Voice:**
- `elevenlabs` 2.44.0 — TTS SDK (`ElevenLabsBackend` in `src/skyherd/voice/tts.py`)
- `twilio` 9.10.5 — voice calls via `client.calls.create()` in `src/skyherd/voice/call.py`)

**Vision:**
- `pillow` — image rendering (synthetic frames)
- `numpy` 1.26+ — thermal frame generation, disease head thresholds
- `supervision` 0.20+ — referenced in `.refs/` and optional `edge` extra; used for detection result parsing in `MegaDetectorHead`
- `PytorchWildlife` — `edge` optional extra; lazy-imported in `MegaDetectorHead` (`src/skyherd/edge/detector.py:107`)

**Web (npm):**
- `react` 19.1.0, `react-dom` 19.1.0
- `framer-motion` 12.38.0 — animations
- `lucide-react` 0.511.0 — icons
- `tailwind-merge`, `clsx` — CSS utilities

**Android:**
- DJI Mobile SDK V5 5.8.0 (`dji-sdk-v5-aircraft`, `dji-sdk-v5-networkImp`)
- OkHttp 4.12 — WebSocket transport
- Eclipse Paho MQTT 1.2.5 — MQTT client

## Configuration

**Environment:**
- `.env.example` documents all required vars (see INTEGRATIONS.md)
- `python-dotenv` loaded at runtime; `SKYHERD_MOCK=1` for demo-without-hardware mode
- Key routing env vars: `SKYHERD_AGENTS=managed|local` (default auto), `DRONE_BACKEND=sitl|mavlink`

**Build:**
- `pyproject.toml` — build system, deps, pytest config, coverage, ruff config
- `web/vite.config.ts` — Vite/React/Tailwind build
- `android/SkyHerdCompanion/gradle/libs.versions.toml` — Android versions

## Platform Requirements

**Development:**
- Python 3.11+ via uv
- Node 20 + pnpm 9 for web
- Optional: Docker for SITL (`docker-compose.sitl.yml` referenced in CI)
- Optional: ArduPilot SITL on UDP port 14540 for real drone sim

**Production:**
- Raspberry Pi 4 (`src/skyherd/edge/`) for edge runtime
- Android device with DJI Mavic Air 2 (`android/SkyHerdCompanion/`)
- Mosquitto MQTT broker (or embedded amqtt)

---

*Stack analysis: 2026-04-22*
