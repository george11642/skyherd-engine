# Phase 8 CONTEXT — Hardware H4 Software Prep (DIY LoRa GPS Collar + ChirpStack bridge)

**Phase:** 08
**Phase slug:** hardware-h4-software-prep-diy-lora-gps-collar-firmware-chirp
**Status:** planning → executing
**Deadline:** 2026-04-26 20:00 EST (submit target 18:00 EST)

## Vision

All *software* for the DIY LoRa GPS cattle collar must ship **without access to a physical RAK3172 module**. When hardware arrives Fri Apr 24, the path from a blank RAK3172 → ChirpStack v4 → live dashboard pins is already proven: firmware compiles clean, flash script exists, ChirpStack uplink frames decode through a tested bridge that republishes to the existing MQTT topic schema (`skyherd/{ranch}/collar/{cow_tag}`) — indistinguishable from a sim collar.

Phase 7 proved the Mavic drone software chain without a drone. Phase 8 does the same for the collar: sim-first discipline preserved. Real collar events land on the same MQTT topics the sim emits; agents see no difference. Zero changes required to FenceLineDispatcher, HerdHealthWatcher, CalvingWatch, PredatorPatternLearner, or GrazingOptimizer.

## Prior art (read-only reference)

- `src/skyherd/sensors/collar.py` — existing `CollarSensor` (sim-side, 126 lines). Publishes `collar.reading` to `skyherd/{ranch}/collar/{cow_id}` with `pos`, `activity`, `battery_pct`. Fires `collar.low_battery` below 15%. **Sim baseline — the real collar must match this exact schema.**
- `hardware/collar/firmware/src/main.cpp` — existing RAK3172 firmware (313 lines). RAK RUI3 API, TinyGPS++, MPU-6050, 16-byte CollarPayload struct. Already packs lat/lon/alt/activity/battery/fix_age/uptime. **H4-01 polishes; does not rewrite.**
- `hardware/collar/firmware/platformio.ini` — RAK3172 + Heltec ESP32 alt envs, native test env. Already configured.
- `hardware/collar/provisioning/decode_payload.py` — server-side codec (296 lines, MIT). Decodes 16-byte payload → `CollarReading` dataclass matching sim schema. `to_mqtt_payload()` produces the canonical dict. **H4-02 bridge consumes this.**
- `hardware/collar/BOM.md` — existing BOM (~$52, 36 lines). Already has alternatives, DigiKey search notes. **H4-03 polishes.**
- `hardware/collar/README.md` — collar overview + quick start. **H4-05 runbook links from here.**
- `hardware/collar/Makefile` — build/flash/test/monitor/shell/clean targets.
- `tests/hardware/test_decode_payload.py` — 9.7 KB, ~20 tests on encode/decode round-trip. Coverage proof for codec.
- `src/skyherd/edge/` — Phase 5+6 home for Pi-side + bridge services. New `chirpstack_bridge.py` lands here.
- `tests/hardware/` — existing hardware integration tests (H1 MQTT, H2 E2E, H3 DJI replay). H4 bridge test goes here.
- `src/skyherd/sensors/bus.py` — `SensorBus` abstraction; bridge publishes through this or directly to `aiomqtt`.

## Scope — SOFTWARE ONLY, no physical RAK3172

### H4-01 — Firmware polish (battery save, GPS duty cycle, OTA placeholder)

- `hardware/collar/firmware/src/main.cpp` — code review existing. Add:
  - **Deep-sleep discipline**: MCU + SX1262 both enter `api.system.sleep.all(ms)` between cycles (already present — verify path always hits it, even on join failure).
  - **GPS duty cycle**: power-gate GPS UART between cycles. Cut VCC via a MOSFET pin (PA2) before deep sleep; repower on wake. Document tradeoff: losing hot-fix advantage to save ~30 mA.
  - **Battery-save mode**: when `battery_pct < LOW_BATTERY_THRESHOLD_PCT`, extend `send_interval_ms` to 4× (from 15 min → 1 hr) and log `[batsave]`.
  - **OTA placeholder**: structured TODO block referencing LoRaWAN FUOTA (RFC on-the-air update), RAK RUI3 `api.fwUpdate`, and the alternative BLE DFU path on ESP32. No implementation — just sign-posts.
  - **Docs block at top**: pin map, power tree, power budget estimate (grazing cycle), LoRaWAN regions.
- Keep total < 500 lines.
- Verify `platformio.ini` build flags unchanged except for new `-D GPS_PWR_PIN=PA2` and `-D BATSAVE_MULTIPLIER=4`.
- Smoke build via `pio run -e native -t checkprogsize` if `pio` is available; else defer to manual verify (runbook).

### H4-02 — ChirpStack bridge

- New file: `src/skyherd/edge/chirpstack_bridge.py` — ingests uplink frames from ChirpStack v4 **MQTT integration** (simpler than REST polling — ChirpStack v4 already publishes every uplink to `application/{app_id}/device/{dev_eui}/event/up`). Decodes via `decode_payload.decode(...)` (imported from provisioning dir). Republishes to `skyherd/{ranch}/collar/{cow_tag}` on the existing Mosquitto broker. Matches sim schema exactly.
- A lightweight `ChirpStackClient` class:
  - `async connect(host, port, username, password, app_id)` — subscribes to uplink topic pattern.
  - `async run(on_reading: Callable[[CollarReading], Awaitable[None]])` — forever loop, surfaces decoded readings via callback.
  - `async close()` — graceful shutdown.
  - Internal: `_resolve_cow_tag(dev_eui)` reads `runtime/collars/registry.json` (or `collars_registry.json` env-configurable) to map LoRaWAN DevEUI → (ranch_id, cow_tag).
- A `ChirpStackBridge` that wires a `ChirpStackClient` to an `aiomqtt`-style publisher. Injectable for tests (no real MQTT).
- Stubbed ChirpStack client in tests — `FakeChirpStackClient` feeds recorded uplinks to the bridge, asserts `CollarReading` round-trips to the sim-schema MQTT payload.
- Coverage ≥ 85%.

### H4-03 — Flash script + BOM finalization

- New file: `hardware/collar/flash.sh` — one-shot flash script. Wraps:
  - `cd hardware/collar/firmware && pio run -e rak3172 -t upload`
  - Pre-flash warning: ensure `BOOT0` held + `RESET` pressed.
  - Post-flash monitor tail for 20 s (optional `--monitor`).
  - Handles missing PlatformIO gracefully with install hint.
  - Executable (`chmod +x`).
- `hardware/collar/BOM.md` — already 50 lines. Polish:
  - Add **exact supplier URLs** (currently some are parent pages).
  - Add **shipping notes** (Adafruit 3-5 day, SparkFun 2-3 day, AliExpress 2-4 weeks).
  - Add **LoRaWAN regulatory note** (US915 only — no EU868 without gateway swap).
  - Add **"Can I skip this?" column** for each non-core item.

### H4-04 — Collar simulator polish (`collar_sim.py`)

- New file: `src/skyherd/sensors/collar_sim.py` — seed-driven deterministic fake collar emitter. Distinct from existing `CollarSensor` (which reads from World). Purpose: **standalone emitter** that can be run outside the sim loop (e.g. for dashboard dev without spinning the world) OR plugged in for ranches with partial hardware.
- Emits synthetic `collar.reading` payloads matching the sim schema (same topic):
  - Position: random walk around a seed point, seed-driven via `random.Random(seed)`.
  - Heart rate: 40-80 bpm (cow resting range), drift via Ornstein-Uhlenbeck-style pullback.
  - Activity: state-machine with seed-driven transitions (resting → grazing → walking → resting…).
  - Battery: drains deterministically at `drain_rate_per_tick`.
  - **No wall-clock** in the emit path — `ts_provider` injected, defaults to `0.0` base + tick count.
- `run_async(count, tick_interval_s)` coroutine yields N readings.
- Tests: seed 42 produces byte-identical output across 3 runs. Coverage ≥ 85%.

### H4-05 — End-to-end runbook

- New file: `docs/HARDWARE_H4_RUNBOOK.md` — numbered steps from blank collar → live dashboard pin.
- Sections:
  1. Prerequisites (ChirpStack v4 docker-compose one-liner, Mosquitto reachable, PlatformIO installed).
  2. Firmware flash (wires flash.sh).
  3. ChirpStack setup (create app, device profile, device, copy DevEUI + AppKey to `secrets.h`).
  4. Provisioning (`register-collar.py`).
  5. Bridge daemon (`python -m skyherd.edge.chirpstack_bridge --ranch ranch_a`).
  6. Verification (dashboard pin turns green).
  7. Troubleshooting (top 5 failure modes).
- Links to BOM, wiring diagram, flash script.
- Includes ChirpStack v4 `docker-compose.yml` snippet (official image, one-liner).

### H4-06 — Bridge tests + integration

- `tests/hardware/test_h4_chirpstack_bridge.py` — unit + integration tests:
  - Unit: `_resolve_cow_tag` lookup with missing DevEUI.
  - Unit: uplink decode → MQTT publish round-trip (schema matches sim).
  - Integration: `FakeChirpStackClient` feeds 3 uplinks → bridge publishes 3 MQTT messages on expected topics.
  - Edge: malformed base64 payload → logged + skipped (no crash).
  - Edge: payload wrong size → logged + skipped.
  - Determinism: same input + seed → identical output.
- Also covers `collar_sim.py` determinism test.

## Hard constraints

- **Determinism preserved.** `collar_sim.py` must be seed-driven; no `time.time()` / `datetime.now()` in replay path.
- **Coverage floor:** ≥ 80% overall (current 89.29%); ≥ 85% on `chirpstack_bridge.py` + `collar_sim.py`.
- **No new runtime deps.** ChirpStack integration is MQTT-only, uses existing `aiomqtt`; no `chirpstack-api` package.
- **MIT only.** PlatformIO/Arduino code exception — LGPL Arduino core is downstream-link only; source remains MIT.
- **Zero-attribution commits** (global git config enforced).
- **Schema parity:** real collar payload → `skyherd/{ranch}/collar/{cow_tag}` → same dict keys as sim `collar.reading`. No divergence.

## Execution pattern

4 plans, sequential execution. No checkpoints (fully autonomous). Each plan ends with local tests green; final plan runs full `make ci` + `make demo` 3× determinism check.

- **08-01** — Firmware polish (H4-01) + build smoke (arduino-cli fallback if pio unavailable)
- **08-02** — ChirpStack bridge + codec re-use + unit tests (H4-02, partial H4-06)
- **08-03** — Flash script + BOM polish + collar_sim module (H4-03, H4-04)
- **08-04** — Runbook + bridge integration test + coverage + determinism (H4-05, rest of H4-06)

## Resilience

- Anything blocked → defer to `deferred-features.md`.
- `pio` CLI unavailable in sandbox → smoke via `arduino-cli compile` or defer to runbook manual verify.
- Context tight → checkpoint to `.planning/RESUME.md`.
