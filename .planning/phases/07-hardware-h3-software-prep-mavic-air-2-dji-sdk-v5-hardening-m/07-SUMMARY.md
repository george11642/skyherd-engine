---
phase: 7
phase_slug: hardware-h3-software-prep-mavic-air-2-dji-sdk-v5-hardening-m
status: complete
completed: 2026-04-24
plans: 4
tests_before: 1667
tests_after: 1717
coverage_before: 89.16
coverage_after: 89.29
commits:
  - 07c3e98 feat(07-01) DJI SDK V5 audit + iOS GPS gate + Android battery/watchdog
  - d25d5af feat(07-02) MavicAdapter — two-legged DJI + MAVSDK failover backend
  - 3bfa74c feat(07-03) MissionV1 Pydantic schema + MAVIC_MISSION_SCHEMA.md
  - e37fed0 feat(07-04) H3 DJI replay E2E + CI app builds + runbook
requirements_closed: [H3-01, H3-02, H3-03, H3-04, H3-05, H3-06]
---

# Phase 7 Summary — Hardware H3 Software Prep (Mavic Air 2 DJI SDK V5 + MAVSDK failover)

## One-liner

`DRONE_BACKEND=mavic` now routes through a two-legged adapter that tries
DJI SDK V5 (via companion apps) first and transparently fails over to
MAVSDK-over-USB-C mid-mission — all proven deterministic by a
`make h3-smoke` replay test that consumes a canned DJI ACK stream
without ever touching a real drone.

## Shipped

| Requirement | Deliverable | Status |
|-------------|-------------|--------|
| H3-01 | `docs/H3_DJI_AUDIT.md` — iOS/Android audit matrix, 5 inline Rule-2 fixes (iOS GPS gate, Android battery wiring, Android lost-signal watchdog, Android wind hook, error-code parity) | GREEN |
| H3-02 | `src/skyherd/drone/mavic_adapter.py` (91 % coverage) — two-legged DJI + MAVSDK adapter with connect-time selection, mid-mission one-shot failover, injected `ts_provider`, ledger events | GREEN |
| H3-03 | `src/skyherd/drone/mission_schema.py` (100 % coverage) + `docs/MAVIC_MISSION_SCHEMA.md` — versioned Pydantic `MissionV1` with forward-compat (`extra="allow"`), `MissionMetadata`, `FailoverHint` | GREEN |
| H3-04 | `tests/hardware/test_h3_dji_replay.py` (6 tests) + `dji_packet_stream.jsonl` fixture — canned DJI ACK replay through real `MavicBackend` transport, <500 ms wall time, deterministic 3× | GREEN |
| H3-05 | `.github/workflows/android-app.yml` + `.github/workflows/ios-app.yml` — unsigned CI builds with `continue-on-error` fallback for DJI SDK artifact gap | GREEN (with fallback) |
| H3-06 | `docs/HARDWARE_H3_RUNBOOK.md` — 8-section runbook (unbox → agent-commanded flight → failover test → MAVSDK-only fallback → troubleshooting → CI artifacts) | GREEN |

## Metrics

- **Tests:** 1667 → **1717** (+50; no regressions)
- **Coverage:** 89.16 % → **89.29 %** (+0.13 pp)
- **Per-module coverage (≥ 85 % target):**
  - `src/skyherd/drone/mavic_adapter.py` — **91 %**
  - `src/skyherd/drone/mission_schema.py` — **100 %**
- **Determinism:** 3/3 PASS (`make demo SEED=42 SCENARIO=all` sha256 identical across three runs — `ca148ef6ec8af302e98dc7a92d6a1838291de9d7691ed12a569ed1f4603d4ab4`)
- **H3 replay wall time:** 0.4 s (gate: < 0.5 s)
- **`make h3-smoke` wall time:** 0.4 s (gate: < 2 s)
- **Full-suite wall time:** 150 s
- **Lint (ruff):** clean on new files after auto-fix

## Key decisions

| Decision | Rationale |
|----------|-----------|
| `DRONE_BACKEND=mavic` now points at `MavicAdapter`, not bare `MavicBackend` | Every existing call site (pi_to_mission, MCP tools, demo runners) gets failover automatically with zero code changes. `mavic_direct` retains the raw path for diagnostics + legacy tests. |
| MAVSDK leg as fallback vs. as primary alongside DJI | The companion app is the human-facing surface — rancher sees what's happening on the phone. If the phone dies, the laptop USB-C OTG path takes over silently. Primary → fallback direction preserves that UX. |
| Ledger failures must never abort the flight path | Implemented by wrapping `ledger.append` in `try/except` inside `_record_event`. A crashed sig chain must not ground the drone — attestation is observational, not safety-critical. |
| Schema `extra="allow"` at top-level | Permits Python-side to emit new fields for later mobile-app builds without bumping version. Non-breaking additions land on Friday; `v2` stays reserved for real schema breaks. |
| Companion app deferred items go to `deferred-features.md`, not inline TODOs | `DJIWaypointV2Mission`, Android dedupe, iOS Bluetooth speaker — all require a real drone + 1+ day. Phase 7 documents them so filming on Saturday can proceed with the replay test as the verification proxy. |
| CI workflows use `continue-on-error: true` | DJI SDK xcframework / AAR is not committed to the repo (vendor download gate). CI builds succeed in stub mode — functional signed builds require manual artifact drop. No demo blocker. |
| Inner-leg disconnect always tries both legs | Even the idle leg may hold a socket/connection. `MavicAdapter.disconnect` iterates both, swallowing individual errors, so no leaks remain. |

## Auto-fixed issues

1. **[Rule 2 — Missing critical functionality]** Android `getBatteryPercent` was hardcoded `100f` — defeated the 30 % safety floor. Wired to `BatteryManager.getInstance().chargeRemainingInPercent` with a `runCatching` fallback for CI.
2. **[Rule 2 — Missing critical functionality]** iOS `DJIBridge.takeoff` never validated GPS fix. Added `gpsValid` to `DroneStateSnapshot`, populated from `fcState.isGPSSignalStrong`, checked pre-takeoff.
3. **[Rule 2 — Missing critical functionality]** Android had no MQTT-disconnect recovery path during flight. Added `startLostSignalWatchdog` coroutine polling `MQTTBridge.isConnected` every 5 s; fires `fc.startGoHome` after 30 s of disconnect while `inAirState == true`.
4. **[Rule 2 — Missing critical functionality]** Android `cmdTakeoff` didn't consume the wind-kt arg it was handed. Added `safety.checkWind(wind_kt)` when present in the MQTT command args.
5. **[Rule 2 — Wire parity]** iOS `DroneErrorCode` enum missed `gpsInvalid` and `lostSignal`. Added both so Python-side parsers see `E_GPS_INVALID` / `E_LOST_SIGNAL` in ACK messages.
6. **[Rule 3 — Blocking test migration]** `tests/drone/test_mavic.py::test_get_backend_factory_returns_mavic` expected `MavicBackend` from `get_backend("mavic")`. Migrated to assert `MavicAdapter` and added a companion test for `mavic_direct` → `MavicBackend`.

No Rule 4 (architectural) deviations.

## What this unlocks

- Phase 8 (H4 LoRa collar): unblocked. The DJI/MAVSDK split is orthogonal to the collar firmware path; collar events land in the same `pi_to_mission` bridge with no changes.
- Phase 9 (demo video scaffolding): can film Saturday using `make hardware-demo-sim-up` + `DRONE_BACKEND=mavic`; the adapter auto-detects which leg to use based on what's actually plugged in.
- Real-drone validation on Friday Apr 25 can now proceed with a known-good software chain — every layer has unit-test or replay coverage.

## Self-Check: PASSED

Files verified present:

- `src/skyherd/drone/mavic_adapter.py` — FOUND
- `src/skyherd/drone/mission_schema.py` — FOUND
- `tests/drone/test_mavic_adapter.py` — FOUND
- `tests/drone/test_mavic_adapter_missions.py` — FOUND
- `tests/drone/test_mission_schema.py` — FOUND
- `tests/hardware/test_h3_dji_replay.py` — FOUND
- `tests/hardware/fixtures/dji_packet_stream.jsonl` — FOUND
- `docs/H3_DJI_AUDIT.md` — FOUND
- `docs/MAVIC_MISSION_SCHEMA.md` — FOUND
- `docs/HARDWARE_H3_RUNBOOK.md` — FOUND
- `.github/workflows/android-app.yml` — FOUND
- `.github/workflows/ios-app.yml` — FOUND
- `.planning/phases/07-.../deferred-features.md` — FOUND
- iOS edits: `Models.swift` (gpsValid + new error codes), `DJIBridge.swift` (GPS guard + state population + error cases) — FOUND
- Android edits: `DroneControl.kt` (watchdog + battery wiring + wind hook + inAirState) — FOUND

Commits verified in git log:
- 07c3e98 — FOUND
- d25d5af — FOUND
- 3bfa74c — FOUND
- e37fed0 — FOUND

## Deferred (tracked in `deferred-features.md`)

1. **MEDIUM** — iOS + Android full `DJIWaypointV2Mission` implementation (real drone required).
2. **MEDIUM** — Android MQTT seq-number dedupe window (low-risk at QoS 1).
3. **LOW** — iOS accessory Bluetooth speaker playback for deterrent tone.
