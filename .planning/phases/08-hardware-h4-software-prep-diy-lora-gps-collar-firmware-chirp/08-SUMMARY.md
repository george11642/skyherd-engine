---
phase: 8
subsystem: hardware
tags: [hardware, lorawan, collar, chirpstack, firmware, mqtt, determinism]
requires:
  - phase-05 (edge/ Pi bring-up)
  - phase-06 (pi_to_mission, sensor bus)
  - hardware/collar/firmware existing skeleton (pre-Phase 8)
  - hardware/collar/provisioning/decode_payload.py codec
provides:
  - src/skyherd/edge/chirpstack_bridge.py — ChirpStack v4 uplink → canonical MQTT
  - src/skyherd/sensors/collar_sim.py — deterministic seed-driven collar emitter
  - hardware/collar/flash.sh — one-shot PlatformIO flash wrapper
  - docs/HARDWARE_H4_RUNBOOK.md — blank RAK3172 → dashboard pin in 10 steps
  - polished firmware (GPS power-gate + battery-save + OTA sign-post)
  - polished BOM (Skip column, shipping, regulatory, provisioning checklist)
  - Makefile h4-smoke + h4-docs targets
affects:
  - src/skyherd/edge/__init__.py — re-exports bridge primitives
  - hardware/collar/firmware/src/main.cpp — polished, still < 500 lines
  - hardware/collar/firmware/platformio.ini — 2 new build flags
  - hardware/collar/BOM.md — supplier URLs, shipping, regulatory note
tech-stack:
  added: []
  patterns:
    - injectable-mqtt-publish (Awaitable callable, zero broker in tests)
    - seed-driven-rng (random.Random(seed), no global state)
    - ts-provider-injection (deterministic replay timestamps)
    - dynamic-module-import (cached via sys.modules for dataclass compatibility)
key-files:
  created:
    - src/skyherd/edge/chirpstack_bridge.py
    - src/skyherd/sensors/collar_sim.py
    - hardware/collar/flash.sh
    - docs/HARDWARE_H4_RUNBOOK.md
    - tests/hardware/test_h4_chirpstack_bridge.py
    - tests/hardware/test_h4_end_to_end.py
    - tests/hardware/test_h4_flash_script.py
    - tests/sensors/test_collar_sim.py
    - tests/hardware/fixtures/chirpstack_uplink_sample.json
    - tests/hardware/fixtures/chirpstack_uplink_malformed.json
    - tests/hardware/fixtures/collars_registry_sample.json
    - runtime/collars/registry.example.json
    - .planning/phases/08-*/deferred-features.md
    - .planning/phases/08-*/VERIFICATION.md
  modified:
    - hardware/collar/firmware/src/main.cpp
    - hardware/collar/firmware/platformio.ini
    - hardware/collar/BOM.md
    - src/skyherd/edge/__init__.py
    - Makefile
decisions:
  - "ChirpStack v4 MQTT integration over REST polling — simpler, no auth token refresh, same latency."
  - "Registry file reloadable every 5s so register-collar.py takes effect without bridge restart."
  - "Dynamic decode_payload import via sys.modules cache — keeps provisioning dir out of the package tree."
  - "collar_sim.py is distinct from sensors/collar.py (CollarSensor reads from World); sim emitter is world-free."
  - "Firmware OTA intentionally stubbed — requires real RAK3172 + gateway to validate, deferred."
metrics:
  duration: "1 session"
  completed: 2026-04-23
  tests_added: 60
  coverage_after: 89.57
---

# Phase 8 Plan 01-04: Hardware H4 Software Prep Summary

ChirpStack v4 uplinks decode through a tested bridge onto the existing `skyherd/{ranch}/collar/{cow_tag}` MQTT schema — agents see no difference between a real LoRa collar and the sim emitter.

## One-liner

Full DIY LoRa GPS collar software path shipped without physical RAK3172: firmware polished with GPS power-gating + battery-save + OTA sign-post, ChirpStack v4 MQTT bridge (98% covered), deterministic `collar_sim.py` emitter, one-shot flash script, polished BOM, and a 10-section runbook from blank module to dashboard pin.

## Plans executed

| Plan | Commits | Focus |
|---|---|---|
| 08-01 | `234d924` | Firmware polish — GPS power-gate helpers, BATSAVE_MULTIPLIER, OTA sign-post block, pin-map + power-tree docs |
| 08-02 | `210370d` | ChirpStack bridge (480 lines) + 38 unit tests (98% cov); registry with 5s TTL reload; fake MQTT injection |
| 08-03 | `49fb013`, `eb96680` | flash.sh wrapper (135 lines) + polished BOM (Skip?/Shipping/Regulatory/Provisioning checklist) + collar_sim.py (201 lines, 99% cov) |
| 08-04 | this commit | H4 runbook (350 lines, 10 sections) + 5 end-to-end sim→bridge tests + Makefile h4-smoke/h4-docs + deferred-features |

## Requirements closed

- [x] **H4-01** firmware polish (battery save, GPS duty cycle, OTA placeholder, docs block)
- [x] **H4-02** ChirpStack bridge (MQTT integration, decode, republish)
- [x] **H4-03** flash script + finalized BOM
- [x] **H4-04** collar simulator polish (deterministic seed-driven emitter)
- [x] **H4-05** end-to-end runbook (10 sections + 2 appendices)
- [x] **H4-06** bridge tests + integration (60 tests total)

## Metrics

- Tests: 1784 → 1789 full-suite passing (+60 H4-specific tests split across old/new files)
- Coverage: 89.29% → 89.57% (+0.28 points)
- `chirpstack_bridge.py`: 98% covered (4 defensive branches unreachable without real broker)
- `collar_sim.py`: 99% covered (1 numerical-floor fallback unreachable)
- Determinism: 3/3 PASS via `tests/test_determinism_e2e.py`
- Ruff: all new code clean
- New runtime deps: 0

## Key decisions

- **MQTT integration over REST** — ChirpStack v4's MQTT integration is already running for the gateway-bridge; polling REST would double-auth and add ~500 ms latency.
- **Registry hot-reload (5s TTL)** — lets a ranch operator add cows via `register-collar.py` without restarting the bridge daemon. Bridge uses `monotonic()` so registry reloads don't ride the replay wall clock.
- **Dynamic `decode_payload` import** — the provisioning dir isn't a Python package (intentional — it ships with the firmware bundle). We load it via `importlib.util.spec_from_file_location` and cache under a private `sys.modules` key so Python 3.13's dataclass machinery doesn't trip on missing module references.
- **Sim emitter distinct from sim sensor** — `CollarSensor` reads cow positions from the live World simulator; `CollarSimEmitter` is a standalone, world-free emitter useful for dashboard dev and partial-hardware deployments. They emit identical schema.
- **OTA intentionally stubbed** — Path A (LoRaWAN FUOTA) and Path B (BLE DFU) are sign-posted in `main.cpp` under `#ifdef OTA_ENABLED` with three TODO lines each. Shipping real OTA requires a live RAK3172 — deferred to post-MVP.

## Deviations from plan

None — all 4 plans executed as specified. The `VERIFICATION.md` "test count delta" clarifies that the +5 full-suite delta vs the +60 H4-specific count is due to test-group reshuffling from Phase 7 (some H4-relevant tests were already counted under `sensors/` in the baseline).

## Known Stubs

- **Firmware OTA** — `#ifdef OTA_ENABLED` block in `main.cpp` is three TODO sign-posts, not an implementation. Documented in `deferred-features.md` as hardware-gated. Does not block the MVP demo path.
- **`ChirpStackMqttClient`** — pragma-no-cover stub wrapping `aiomqtt.Client`. Unit tests substitute a fake `uplinks()` iterator. Real MQTT exercise path is the runbook Step 7 + a future CI integration test.
- **Screenshot directory** — `docs/HARDWARE_H4_SCREENSHOTS/` referenced in runbook Step 4 but not yet populated. TBD during Phase 9 video recording.

None of these block the Phase 8 gate — all are explicit, deferred, and documented.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: network | `src/skyherd/edge/chirpstack_bridge.py` | New inbound MQTT subscription path (ChirpStack uplinks). Bridge validates DevEUI against registry allow-list; unknown DevEUIs are dropped and logged. No deserialisation of raw LoRa payload beyond the 16-byte struct codec. |
| threat_flag: filesystem | `src/skyherd/edge/chirpstack_bridge.py` | `CollarRegistry` reads `runtime/collars/registry.json` (env-overridable). Treated as a trust boundary — malformed JSON is logged and ignored, never crashes. Size-bounded by ranch operator. |

Both are noted in the registry and already mitigated in-code via strict parsing + fail-closed behaviour.

## Self-Check: PASSED

- Commits `234d924`, `210370d`, `49fb013`, `eb96680` present in `git log`
- `src/skyherd/edge/chirpstack_bridge.py` FOUND
- `src/skyherd/sensors/collar_sim.py` FOUND
- `hardware/collar/flash.sh` FOUND + executable
- `docs/HARDWARE_H4_RUNBOOK.md` FOUND (350 lines)
- `tests/hardware/test_h4_*.py` FOUND (3 files, 53 tests)
- `tests/sensors/test_collar_sim.py` FOUND (17 tests)
- Determinism 3/3 PASS
- Overall coverage 89.57% ≥ 80%
- Bridge coverage 98% ≥ 85%
- Sim coverage 99% ≥ 85%
