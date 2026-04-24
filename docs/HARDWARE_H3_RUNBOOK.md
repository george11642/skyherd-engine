# HARDWARE_H3_RUNBOOK — Mavic Air 2 (DJI SDK V5 + MAVSDK failover)

**Phase:** 7 · **Last updated:** 2026-04-24
**Scope:** From unboxing a fresh DJI Mavic Air 2 to flying an agent-
commanded pattern mission with MAVSDK failover. **Software path only** —
this runbook exists so a Saturday shoot can happen without new code.

---

## 0. Prerequisites

### Hardware

- DJI Mavic Air 2 + RC controller + two charged batteries.
- An iOS 16+ or Android 12+ phone/tablet.
- (Optional) USB-C OTG cable for MAVSDK fallback.
- (Optional) Bluetooth speaker for deterrent tone on-ground.
- Pi 4 fleet from Phase 5 (H1) already running.

### Accounts + credentials

- **DJI developer account** (free) — needed for `DJIAppKey` in
  `ios/SkyHerdCompanion/SupportingFiles/Config.xcconfig` or
  `android/SkyHerdCompanion/app/local.properties`.
- **Apple developer account** only if you want signed iOS builds;
  unsigned stub-mode builds work in CI without one.

### Environment

On the laptop running `skyherd-live`:

```bash
export DRONE_BACKEND=mavic          # enables MavicAdapter (DJI + MAVSDK)
export MAVIC_WS_URL=ws://<phone-ip>:8765
export MAVIC_MQTT_URL=mqtt://<laptop-ip>:1883
```

To force-disable the MAVSDK fallback (diagnostic), use
`DRONE_BACKEND=mavic_direct` — the bare `MavicBackend` with no failover.

---

## 1. Step 1 — Pair the companion app

### iOS

```bash
cd ios/SkyHerdCompanion
./bootstrap.sh           # installs xcodegen, creates Config.xcconfig
# open Config.xcconfig, set DJI_API_KEY=<your_key>
xcodegen generate
open SkyHerdCompanion.xcodeproj
# Build & Run on a paired iPhone/iPad — grant location + external-accessory
```

### Android

```bash
cd android/SkyHerdCompanion
# Set DJI_API_KEY in app/src/main/res/values/strings.xml
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
# Launch SkyHerd on phone, grant permissions
```

Both apps display **"DJI Status: Registered"** then **"Connected"** when
the RC controller is plugged into the phone and the Mavic powers on.

---

## 2. Step 2 — Bind the MQTT broker

Start the laptop-side broker from the root of this repo:

```bash
make hardware-demo-sim-up     # starts mosquitto + skyherd-live + pi-to-mission
```

On the phone, in **SkyHerd → Settings → MQTT**, paste:
`tcp://<laptop-ip>:1883`. Press **Connect**. The status badge goes
green within 2 s. SkyHerd publishes a `get_state` ACK on first connect —
verify it appears in the dashboard `/attest` panel.

---

## 3. Step 3 — First agent-commanded takeoff

With the drone powered on and companion app bound:

```bash
export DRONE_BACKEND=mavic
uv run skyherd-demo-hw play --prop coyote --timeout 60
```

Observed chain:

1. Coyote harness emits `fence.breach` MQTT event.
2. `PiToMissionBridge` calls FenceLineDispatcher (sim handler).
3. `MavicAdapter.connect()` selects DJI leg (ledger:
   `adapter.leg_selected, leg=dji`).
4. `MavicAdapter.patrol_mission(MissionV1)` → DJI SDK `startTakeoff` →
   `goto` waypoints → ACK per hop.
5. `play_deterrent` → on-ground speaker bridge (if SKYHERD_DETERRENT=on).
6. `return_to_home` → auto-land on RC home.

---

## 4. Step 4 — Failover test (pull USB-C)

Run the same command as Step 3, but halfway through the flight:

1. Pull the USB-C cable from the phone.
2. The adapter receives a `DroneError` on its next actuator call.
3. Ledger shows `adapter.failover, from_leg=dji, to_leg=mavsdk,
   reason=signal_lost: ...`.
4. If USB-C OTG is plugged to the laptop with MAVSDK running, the
   mission completes via the fallback leg.

If USB-C is not plugged, the adapter surfaces a
`DroneError: Both legs failed` and the mission aborts cleanly — no
drone crash, no dangling waypoint upload.

**CI replay:** The same chain is validated without a drone via
`make h3-smoke` — see `tests/hardware/test_h3_dji_replay.py`.

---

## 5. Step 5 — MAVSDK-only fallback (no companion app)

If the phone dies or the DJI SDK won't register:

1. Plug USB-C OTG directly to the laptop running `skyherd-live`.
2. Start an ArduPilot SITL bridge or a real pymavlink endpoint on
   UDP 14552.
3. Run with `DRONE_BACKEND=mavic` as usual — the adapter's DJI leg
   times out in 3 s and auto-falls-over to MAVSDK.
4. Mission proceeds over MAVLink only.

---

## 6. Troubleshooting

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| "DJI not ready — register and connect first" | API key wrong / phone offline | Check `DJI_API_KEY` in Config.xcconfig / strings.xml |
| Takeoff ACK = `E_GPS_INVALID` | GPS fix not yet acquired | Wait 30–60 s outdoors; re-issue takeoff |
| Takeoff ACK = `E_BATTERY_LOW` | Battery < 30 % | Swap battery |
| Mission ACK = error then adapter.failover | DJI RC signal drop | Check antennas / line of sight; MAVSDK leg auto-retries |
| `adapter.both_legs_failed` terminal | Both DJI and MAVSDK unavailable | Plug USB-C OTG + restart companion app |
| Deterrent tone inaudible | `SKYHERD_DETERRENT` unset | `export SKYHERD_DETERRENT=on` before `make hardware-demo-sim-up` |
| Android watchdog RTH fires unexpectedly | MQTT drops > 30 s during flight | Set `autoRthOnLostSignal=false` in companion app Settings → Diagnostic |

---

## 7. CI artifacts

Unsigned companion-app builds are produced by GitHub Actions on every
push touching `ios/**` or `android/**`:

- Android: **Actions → Android Companion App Build → Artifacts →
  `skyherd-companion-android-apk`**. `adb install`-able on a dev phone.
- iOS: **Actions → iOS Companion App Build → Artifacts →
  `skyherd-companion-ios-build`**. Re-sign with your dev cert before
  `xcrun simctl install` or TestFlight.

**Note:** Both workflows run with `continue-on-error: true` because the
DJI SDK artifacts (xcframework on iOS, AAR on Android) are proprietary
and not committed to the repo. Builds succeed in stub mode (no DJI
calls) but download-from-DJI + manual placement is required for
functional builds. See `HARDWARE_MAVIC_IOS.md` and
`HARDWARE_MAVIC_ANDROID.md` for the vendor download flow.

If the Actions runner fails to generate a Gradle wrapper or install
XcodeGen for > 60 min, treat it as the defer-fallback path documented in
`.planning/phases/07-.../deferred-features.md` — local repo builds
remain the canonical verification.

---

## 8. Repo-local build shortcuts

```bash
# Android APK (requires JDK 17 + Android SDK)
cd android/SkyHerdCompanion && ./gradlew assembleDebug

# iOS archive (requires macOS + Xcode 15)
cd ios/SkyHerdCompanion && xcodegen generate && \
  xcodebuild -scheme SkyHerdCompanion -configuration Debug build

# H3 replay smoke (no hardware required)
make h3-smoke

# Unit tests with coverage
uv run pytest tests/drone tests/hardware -v
```

---

_See also: `docs/H3_DJI_AUDIT.md`, `docs/MAVIC_MISSION_SCHEMA.md`,
`docs/HARDWARE_MAVIC_PROTOCOL.md`, `docs/HARDWARE_H2_RUNBOOK.md`._
