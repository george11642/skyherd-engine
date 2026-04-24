# Phase 7 CONTEXT — Hardware H3 Software Prep (Mavic Air 2 DJI SDK V5 + MAVSDK failover)

**Phase:** 07
**Phase slug:** hardware-h3-software-prep-mavic-air-2-dji-sdk-v5-hardening-m
**Status:** planning → executing
**Deadline:** 2026-04-26 20:00 EST (submit target 18:00 EST)

## Vision

All *software* for flying a DJI Mavic Air 2 under agent command — the companion apps (iOS + Android), an MAVSDK USB-C OTG failover path, a versioned mission JSON schema, a recorded-packet replay test, and CI build artifacts — must be shippable **without access to the physical drone**. When the hardware arrives on Friday Apr 24, the path from unboxing to agent-commanded flight is already proven in sim.

Phase 6 already routed every sensor event through `src/skyherd/edge/pi_to_mission.py` and gated it on `DRONE_BACKEND=sitl`. Phase 7 slots in a new `DRONE_BACKEND=mavic` that:

1. Presents the same `DroneBackend` ABC so zero call-site changes are needed.
2. Tries DJI SDK (via companion app over MQTT/WebSocket) first.
3. Falls back to MAVSDK over USB-C OTG if DJI fails mid-mission.

The Mavic Air 2 path is the hackathon's **hero combo demo** when paired with the H1 Pi fleet — so this phase is the last software gate before Saturday's filming slot.

## Prior art (read-only reference)

- `src/skyherd/drone/interface.py` — `DroneBackend` ABC + `get_backend(name)` factory; registers `"mavic"` → `MavicBackend` lazily.
- `src/skyherd/drone/mavic.py` — **existing** `MavicBackend` (v1.0). 471 lines. WebSocket to companion app, safety guards, synthetic thermal frame, `get_state` cache. No MAVSDK failover. **Will be extended, not replaced.**
- `src/skyherd/drone/sitl.py` — 504 lines, reference for how a real backend handles connect/takeoff/patrol/RTH.
- `src/skyherd/drone/pymavlink_backend.py` — already has MAVSDK-adjacent MAVLink plumbing; H3-02 reuses this for the failover leg.
- `src/skyherd/drone/safety.py` — shared `GeofenceChecker`, `BatteryGuard`, `WindGuard` (wind ceiling 21 kt for Mavic).
- `src/skyherd/edge/pi_to_mission.py` — consumer side. Already `DRONE_BACKEND=mavic` ready (no changes needed unless failover observability requires it).
- `src/skyherd/mcp/drone_mcp.py` — MCP tool definitions (`launch_drone`, `return_to_home`, `play_deterrent`, `capture_thermal`) that agents call. Don't touch.
- `ios/SkyHerdCompanion/Sources/SkyHerdCompanion/DJIBridge.swift` — 340 lines. `DJISDKManagerDelegate`, guarded behind `#if DJI_SDK_AVAILABLE`; stub mode compiles without the xcframework. Known gap: `gotoLocation` still calls `startGoHome` as placeholder, no waypoint mission yet.
- `android/SkyHerdCompanion/app/src/main/kotlin/com/skyherd/companion/DroneControl.kt` — 232 lines. MQTT listener dispatches to DJI FlightControllerManager. Known gap: `cmdGoto` also stubs to ack-ok, `play_deterrent` logs only, `getBatteryPercent` returns hardcoded 100.
- `docs/HARDWARE_H2_RUNBOOK.md` — template for H3 runbook structure and cadence.
- `docs/HARDWARE_MAVIC_ANDROID.md`, `docs/HARDWARE_MAVIC_IOS.md`, `docs/HARDWARE_MAVIC_PROTOCOL.md` — existing protocol specs. **H3-03 schema must not contradict these.**

## Scope — software only, no drone access

### H3-01 — DJI SDK V5 integration audit

Produce `docs/H3_DJI_AUDIT.md` covering both iOS and Android companion apps. Per-app checklist:

- Mission upload error handling — is every async throw surfaced as an ACK-error?
- GPS-denied behavior — does `takeoff` gate on GPS fix, not just SDK state?
- Low-battery triggers — does the app abort mission on `battery_pct < 30` independently of the Python-side `BatteryGuard`?
- Lost-signal recovery — is there an app-side timeout that triggers RTH if MQTT bridge drops?
- Mission-JSON schema compliance — do ACKs match the schema defined in H3-03?

Fix small/obvious bugs inline (auto-Rule-1/2). Complex gaps → log to `deferred-features.md` as MEDIUM and reference in the runbook.

### H3-02 — MAVSDK failover adapter

New file: `src/skyherd/drone/mavic_adapter.py` — a `MavicAdapter` class that implements `DroneBackend` and:

1. Constructs an inner `MavicBackend` (DJI leg) + an inner `PymavlinkBackend` (MAVSDK-over-USB-C OTG leg). Both share the same `Waypoint` sequence.
2. On `connect()`, tries DJI first (3 s timeout). If success, `mode="dji"`. If timeout/unavailable, tries MAVSDK (`mode="mavsdk"`). If both fail, raises `DroneUnavailable`.
3. On each actuator call (`takeoff`, `patrol`, `return_to_home`, `play_deterrent`, `get_thermal_clip`, `state`), delegates to the active leg. On `DroneError` from DJI, fails over to MAVSDK mid-mission (single retry) and continues.
4. Emits `adapter.failover` ledger entry (with `from_leg=dji`, `to_leg=mavsdk`, `reason`) on every failover.
5. Factory: register `"mavic"` in `get_backend()` to return `MavicAdapter` instead of bare `MavicBackend`. **This is a soft breaking change** — `DRONE_BACKEND=mavic_direct` preserves old behavior. The existing `MavicBackend` tests keep running against `mavic_direct`.
6. Coverage ≥ 85 %.

### H3-03 — Mission JSON schema (versioned Pydantic v1)

Two new files:

- `src/skyherd/drone/mission_schema.py` — Pydantic models: `MissionV1`, `Waypoint` (reuse existing), `MissionMetadata`, `FailoverHint`. `MissionV1.version = Literal[1]`. Forward-compat via `model_config = {"extra": "allow"}` on top-level.
- `docs/MAVIC_MISSION_SCHEMA.md` — schema reference with example JSON, field-by-field explanations, versioning policy.

`MavicAdapter.patrol()` serializes the incoming `list[Waypoint]` into a `MissionV1` before sending to either leg; companion apps parse using a Kotlin/Swift mirror of the schema.

Coverage ≥ 85 %.

### H3-04 — DJI replay E2E test

`tests/hardware/test_h3_dji_replay.py` + `tests/hardware/fixtures/dji_packet_stream.jsonl` (canned fixture).

- Fixture: a 30-ack sequence representing a typical patrol mission (connect → takeoff → 4 waypoints → RTH → disconnect). Each line is a JSON ACK from the companion app.
- Replay test: injects a fake `_WSTransport` that yields each fixture line in order on `send_command`. Asserts:
  - Backend state transitions match expected sequence.
  - Ledger entries at each hop have the expected `kind`.
  - Mid-mission failure ACK (line 18: `"result": "error", "message": "signal_lost"`) triggers `MavicAdapter` failover to MAVSDK and completes the mission.
  - Total wall time < 500 ms.

### H3-05 — CI companion app builds

Two new workflows:

- `.github/workflows/android-app.yml` — Gradle build of `android/SkyHerdCompanion`. Unsigned APK. Publishes to Actions artifact. Triggered on pushes that touch `android/**` or `.github/workflows/android-app.yml`.
- `.github/workflows/ios-app.yml` — XcodeGen → xcodebuild build on macOS runner. Unsigned archive. Publishes to Actions artifact. Triggered on pushes that touch `ios/**` or `.github/workflows/ios-app.yml`.

If either workflow proves too brittle to stand up in <60 min (common: missing DJI xcframework gate, Gradle wrapper download, xcodegen install), **defer to `deferred-features.md`** as MEDIUM and document the repo-local build path in the runbook. Don't burn a whole day on CI.

### H3-06 — Runbook

`docs/HARDWARE_H3_RUNBOOK.md` — same cadence as H2 runbook. Sections:

1. Prerequisites (hardware, accounts, API keys).
2. Unbox → companion app install → DJI account pair (5 steps).
3. Agent-commanded pattern flight (1 cmd).
4. Failover test (pull USB-C → verify adapter switches legs).
5. MAVSDK-only fallback (no DJI mobile app at all).
6. Troubleshooting.

## Constraints (hard)

- **Determinism** preserved: `make demo SEED=42 SCENARIO=all` byte-identical, three times. New adapter must inject `time_provider` (default `time.monotonic`) and accept a deterministic seeded RNG if it ever uses random (jitter, retry backoff).
- **Coverage:** ≥ 80 % overall (maintain the 89.16 % baseline from Phase 6). Per-module ≥ 85 % on `mavic_adapter.py` + `mission_schema.py`.
- **MIT only.** DJI SDK is proprietary → stays in `ios/` + `android/` app directories. `src/skyherd/` remains MIT-clean.
- **Zero-attribution commits** (global git config enforces).
- **No real drone access.** All tests use mocks, recorded fixtures, or the existing `SitlBackend` in place of `PymavlinkBackend` when MAVSDK isn't installed in CI.
- **No import from `/home/george/projects/active/drone/`** — sibling repo is reference-only (MIT hygiene rule).

## Non-goals

- Real MAVSDK library install in CI — the fallback leg uses `pymavlink_backend.PymavlinkBackend` via mock transport in tests. If MAVSDK is installed locally by user, the adapter uses it; CI runs on mock.
- DJI xcframework download in CI — the iOS build stays in `DJI_SDK_AVAILABLE` un-defined mode (stub implementations compile, no runtime behavior).
- New MCP tools — the existing `launch_drone` / `return_to_home` / `play_deterrent` / `capture_thermal` tool surface is unchanged.
- Voice control, live video stream, multi-drone swarm — all out of scope for H3.

## Plan decomposition (target: 4 plans)

| Plan | Focus | Requirements |
| --- | --- | --- |
| 07-01 | DJI SDK audit + bug-fix sweep on iOS + Android companion apps + `docs/H3_DJI_AUDIT.md` | H3-01 |
| 07-02 | `mavic_adapter.py` (MAVSDK failover) + factory + unit tests (≥ 85 % coverage) | H3-02 |
| 07-03 | `mission_schema.py` Pydantic model + `docs/MAVIC_MISSION_SCHEMA.md` + adapter integration | H3-03 |
| 07-04 | `test_h3_dji_replay.py` + packet fixture + CI app-build workflows + `docs/HARDWARE_H3_RUNBOOK.md` | H3-04, H3-05, H3-06 |

Execution is sequential (each depends on the previous for coverage + schema references).

## Verification gates

1. `uv run pytest` — target 1683 → 1720+ passing (0 failed).
2. `uv run pytest --cov=src/skyherd --cov-fail-under=80` — green.
3. Per-module coverage: `src/skyherd/drone/mavic_adapter.py` ≥ 85 %, `mission_schema.py` ≥ 85 %.
4. `make demo SEED=42 SCENARIO=all` run three times, sha256 identical after wall-timestamp sanitization.
5. `ruff check .` + `uv run pyright src/skyherd/drone/mavic_adapter.py src/skyherd/drone/mission_schema.py` — clean.
6. `git log --oneline` — 4 `feat(07-0X)` commits + 1 final `docs(07)` meta commit.

## Return format (≤400 words)

See phase mission prompt.

---

_Frozen 2026-04-24 02:30 UTC._
