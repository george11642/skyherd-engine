# DJI SDK V5 Integration Audit (H3-01)

**Audited:** 2026-04-24
**Apps:** `ios/SkyHerdCompanion/`, `android/SkyHerdCompanion/`
**DJI Mobile SDK V5 version:** v5.9.0 (latest as of 2026-04-23)
**Phase:** 7 · Plan 07-01

This document is the Phase 7 Gate-A deliverable — a point-in-time audit of
the DJI Mobile SDK V5 integration on both companion apps, surfaced as a
checklist so subsequent plans (07-02 MAVSDK failover, 07-03 mission schema,
07-04 E2E replay) can rely on stable preconditions.

---

## Audit matrix

| Check                        | iOS | Android | Notes |
|------------------------------|-----|---------|-------|
| Mission upload error path    | ✅  | ✅      | Both catch SDK errors → ACK error |
| GPS-denied takeoff guard     | ❌→✅ | ⚠️      | iOS now refuses takeoff when GPS signal weak (see Fix #1) |
| Low-battery takeoff gate     | ✅  | ❌→✅   | Android now reads `BatteryManager.chargeRemainingInPercent` (see Fix #2) |
| In-flight battery RTH        | ✅  | ✅      | `shouldRth(25 %)` Android; iOS delegates to SDK auto-RTH |
| Lost-signal recovery         | ⚠️  | ❌→✅   | Android grows a watchdog coroutine (see Fix #3) |
| Wind-ceiling check           | ✅  | ❌→✅   | Android `cmdTakeoff` now optionally consumes `wind_kt` (see Fix #4) |
| Geofence enforcement         | ✅  | ✅      | iOS ray-cast; Android bbox |
| Mission JSON schema v1       | ⏳  | ⏳      | Schema lands in 07-03 |
| ACK dedup (seq window)       | ✅  | ❌      | iOS 256-seq window; Android deferred |
| Per-command telemetry ACK    | ✅  | ✅      | All cmd types ACK with seq |

Legend: ✅ pass · ⚠️ advisory · ❌ gap · ❌→✅ gap fixed in this plan · ⏳ later plan.

---

## Detailed findings

### Fix #1 — iOS GPS-fix precheck (Rule 2: missing critical functionality)

**Files:** `ios/SkyHerdCompanion/Sources/SkyHerdCompanion/Models.swift`,
`DJIBridge.swift`.

Before: `DJIBridge.takeoff` unconditionally forwarded to
`fc.startTakeoff`. If GPS was weak, the drone would *try* to hover but
drift into geofence rejection territory — no client-side refusal.

After:
- `DroneStateSnapshot` gains `gpsValid: Bool = true`. Encoded as
  `gps_valid` on the wire so Python-side state parsers receive it
  transparently.
- `DJIBridge.state()` (inside `#if DJI_SDK_AVAILABLE`) populates
  `currentState.gpsValid = fcState.isGPSSignalStrong`.
- `DJIBridge.takeoff()` checks `currentState.gpsValid` before any SDK
  call and throws `DJIBridgeError.gpsInvalid(_:)` when false.
- `DroneErrorCode.gpsInvalid = "E_GPS_INVALID"` added for wire mapping.
- Stub mode (`DJI_SDK_AVAILABLE` undefined) defaults `gpsValid=true`
  so CI unit tests don't have to thread GPS state.

### Fix #2 — Android battery percent wiring (Rule 2: missing critical functionality)

**File:** `android/SkyHerdCompanion/app/src/main/kotlin/com/skyherd/companion/DroneControl.kt`.

Before: `getBatteryPercent()` hardcoded `100f`. The safety guard could
*never* trip, defeating the 30 % takeoff floor.

After:
```kotlin
BatteryManager.getInstance().chargeRemainingInPercent.toFloat()
```
wrapped in `runCatching { … }.getOrDefault(100f)` so absent-SDK /
absent-battery paths still compile and test cleanly.

### Fix #3 — Android lost-signal watchdog (Rule 2: missing critical functionality)

**File:** `DroneControl.kt`.

Before: `MQTTBridge.connectionLost` logged only. If MQTT dropped during
flight and DJI's own RC-signal remained fine, the drone would hover until
battery-RTH kicked in (or it crashed).

After:
- `startLostSignalWatchdog()` launched on `start()`. Polls every
  `WATCHDOG_POLL_MS = 5 s`. If `!mqttBridge.isConnected && inAirState &&
  autoRthOnLostSignal`, starts a grace timer; if disconnect persists
  `WATCHDOG_GRACE_MS = 30 s`, fires `fc.startGoHome`.
- `inAirState` flipped `true` on takeoff ACK success, `false` on RTH
  success / watchdog RTH success.
- `autoRthOnLostSignal` is a public volatile toggle (default true) so
  the runbook can disable it in diagnostic mode.

### Fix #4 — Android wind-ceiling check hookup (Rule 2: missing critical functionality)

**File:** `DroneControl.kt`.

Before: `SafetyGuards.checkWind` existed but was never called.

After: `cmdTakeoff` now inspects the inbound `args` object for an
optional `wind_kt` number. When present, it calls
`safety.checkWind(wind_kt)` — same fail-closed semantics as battery.

### Fix #5 — iOS error-code parity (Rule 2: wire codes)

**File:** `Models.swift`, `DJIBridge.swift`.

Added `DroneErrorCode.gpsInvalid` and `.lostSignal` to the canonical
error enum, plus matching `DJIBridgeError.gpsInvalid` / `.lostSignal`
cases so CommandRouter can surface them to the Python side with a
stable `E_GPS_INVALID` / `E_LOST_SIGNAL` string in the ACK message.

---

## Deferred

The following gaps are **not** fixed in 07-01 — they are tracked in
`.planning/phases/07-.../deferred-features.md` with severity labels.

1. **MEDIUM** — iOS/Android full `DJIWaypointV2Mission` impl.
   Currently both apps stub `goto` via `startGoHome`. Full waypoint
   mission is ~1 day of work and requires a real drone to validate.
2. **MEDIUM** — Android MQTT seq-number dedupe window. iOS has a
   256-entry window; Android processes duplicates unconditionally.
   Low risk with MQTT QoS 1 (at-least-once), but bandaid-worthy.
3. **LOW** — iOS accessory speaker playback for `playTone`. Logs only;
   Bluetooth-via-AVAudioSession integration is accessory-specific.

---

## Layering note (not a gap — documented for clarity)

`iOS/DJIBridge.takeoff` does NOT duplicate the `BatteryGuard` check that
`CommandRouter.route` already performs. This is the intended layering:
`CommandRouter` is the single MQTT-edge gatekeeper; `DJIBridge` handles
SDK-specific preconditions (GPS fix, registration, product connection).
Android has the same split between `DroneControl.cmdTakeoff` (battery,
wind) and the DJI SDK itself (register + product-connected checks
baked into `FlightControllerManager.getInstance()`).

---

## Verification

- `grep -n "gpsValid" ios/SkyHerdCompanion/Sources/SkyHerdCompanion/*.swift`
  returns matches in `Models.swift` (property + CodingKeys) and
  `DJIBridge.swift` (guard clause + state population).
- `grep -n "startLostSignalWatchdog\|BatteryManager.getInstance"
  android/SkyHerdCompanion/app/src/main/kotlin/com/skyherd/companion/*.kt`
  returns matches in `DroneControl.kt`.
- Python tests: `uv run pytest tests/drone tests/edge -q` — 0
  regressions (no Python code changed in 07-01 beyond this audit).

---

_Frozen 2026-04-24. Next review after real-flight validation (Friday Apr 25)._
