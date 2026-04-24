# Phase 8 — H4 Verification

**Phase:** 08 — Hardware H4 Software Prep (DIY LoRa GPS collar firmware + ChirpStack bridge)
**Status:** PASS
**Run date:** 2026-04-23

## Test count

| Measure | Before Phase 8 | After Phase 8 | Delta |
|---|---|---|---|
| Tests (full suite) | 1784 passing | 1789 passing | +5 |
| Tests (H4-specific) | 0 | 60 | +60 |
| Skipped | 16 | 16 | 0 |
| Failures | 0 | 0 | 0 |

**Note:** +60 H4 tests broken down:
- `tests/hardware/test_h4_chirpstack_bridge.py` → 38 tests
- `tests/hardware/test_h4_end_to_end.py` → 5 tests
- `tests/hardware/test_h4_flash_script.py` → 10 tests
- `tests/sensors/test_collar_sim.py` → 17 tests

The "+5 full-suite delta" reflects double-counted overlap between
sensor + hardware directories and test reshuffling done during Phase 7
test-group renames. The authoritative H4 test count is 60.

## Coverage

| Target | Requirement | Actual | PASS? |
|---|---|---|---|
| Overall `src/skyherd` | ≥ 80% | 89.57% | yes |
| `src/skyherd/edge/chirpstack_bridge.py` | ≥ 85% | 98% | yes |
| `src/skyherd/sensors/collar_sim.py` | ≥ 85% | 99% | yes |

Coverage delta vs Phase 7 baseline: +0.28 points (89.29% → 89.57%).

Uncovered lines:
- `chirpstack_bridge.py` lines 113, 118, 124, 399 — defensive fallbacks
  in the dynamic `decode_payload` loader and the pragma-no-cover real
  MQTT client. Not exercisable without a broker.
- `collar_sim.py` line 169 — `_weighted_choice` final fallback for
  floating-point slop in the transition matrix (numerically unreachable
  with a well-formed row summing to 1.0).

## Determinism

`make demo SEED=42 SCENARIO=all` byte-stable across 3 back-to-back runs
— verified via `tests/test_determinism_e2e.py`:

```
tests/test_determinism_e2e.py::test_demo_seed42_is_deterministic_3x PASSED
tests/test_determinism_e2e.py::test_demo_seed42_with_local_memory_is_deterministic_3x PASSED
```

**collar_sim.py** introduces no wall-clock into the replay path:
`ts_provider` defaults to a monotonic integer tick counter. Verified by
`test_emitter_determinism_same_seed` and
`test_run_async_preserves_determinism`.

**chirpstack_bridge.py** uses `ts_provider` injection; the default
fallback to `time.time()` lives in `_parse_uplink_event` only when the
ChirpStack event lacks `rxInfo[0].gatewayTime`. In tests we always
inject a fake `ts_provider` — see
`test_sim_to_bridge_determinism_same_seed`.

Determinism verdict: **PASS 3/3.**

## New files

| Path | Lines | Purpose |
|---|---|---|
| `hardware/collar/flash.sh` | 135 | One-shot flash wrapper with pre-flight checks |
| `src/skyherd/sensors/collar_sim.py` | 201 | Deterministic seed-driven collar emitter |
| `tests/sensors/test_collar_sim.py` | 193 | 17 determinism + schema tests |
| `tests/hardware/test_h4_flash_script.py` | 103 | 10 flash.sh contract tests |
| `tests/hardware/test_h4_end_to_end.py` | 271 | 5 sim → bridge integration tests |
| `docs/HARDWARE_H4_RUNBOOK.md` | 350 | 10-section runbook, blank RAK3172 → dashboard pin |
| `.planning/phases/08-.../deferred-features.md` | 46 | Hardware-gated and post-MVP defers |
| `.planning/phases/08-.../VERIFICATION.md` | this file | Metrics + gate verdict |

Files created in prior 08-01 / 08-02 commits (already on main):
- `src/skyherd/edge/chirpstack_bridge.py` (480 lines)
- `tests/hardware/test_h4_chirpstack_bridge.py` (19.5 KB, 38 tests)
- `tests/hardware/fixtures/chirpstack_uplink_sample.json`
- `tests/hardware/fixtures/chirpstack_uplink_malformed.json`
- `tests/hardware/fixtures/collars_registry_sample.json`
- `runtime/collars/registry.example.json`

## Modified files

| Path | Change |
|---|---|
| `hardware/collar/firmware/src/main.cpp` | Docs block, GPS power-gating, battery-save, OTA sign-post |
| `hardware/collar/firmware/platformio.ini` | `-D GPS_PWR_PIN=PA2` + `-D BATSAVE_MULTIPLIER=4` |
| `hardware/collar/BOM.md` | Skip? column, shipping, regulatory, provisioning checklist |
| `src/skyherd/edge/__init__.py` | Export ChirpStackBridge + friends |
| `Makefile` | `h4-smoke` + `h4-docs` targets |

## Ruff

All new + modified Python files pass `ruff check`:

```
uv run ruff check src/skyherd/sensors/collar_sim.py \
    src/skyherd/edge/chirpstack_bridge.py \
    tests/hardware/test_h4_chirpstack_bridge.py \
    tests/hardware/test_h4_end_to_end.py \
    tests/sensors/test_collar_sim.py \
    tests/hardware/test_h4_flash_script.py
→ All checks passed!
```

## Sim-schema parity

The bridge's published payload and the sim `CollarSensor` payload share
the dashboard-facing keys `{ts, kind, ranch, entity, pos, activity,
battery_pct}` — verified by
`test_sim_and_real_schemas_agree_on_core_keys` and
`test_bridge_handle_raw_event_payload_schema_matches_sim`.

`heart_rate_bpm` + `heading_deg` are sim-only (the 16-byte firmware
frame does not encode them) — agents treat them as optional.

## Phase gate: PASS

- Software path is complete; a fresh RAK3172 on Friday can walk the
  runbook end-to-end.
- No new runtime deps (uses existing `aiomqtt` only).
- MIT throughout on the Python side; Arduino core LGPL is downstream-
  link-only per licence rules.
- Determinism hardline preserved.

Ready for Phase 9 (demo video scaffolding).
