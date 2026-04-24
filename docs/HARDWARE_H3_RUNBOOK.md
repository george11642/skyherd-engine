# HARDWARE_H3_RUNBOOK — Mavic Air 2 (laptop-primary · DJI + MAVSDK failover)

**Phase:** 7 · **Last updated:** 2026-04-25 (Phase 7.1 — laptop path promoted to primary)
**Scope:** From unboxing a fresh DJI Mavic Air 2 to flying an agent-
commanded pattern mission with MAVSDK failover. **Software path only** —
this runbook exists so a Saturday shoot can happen without new code.

> **2026-04-25 update:** The laptop-as-controller path (§1) is now the
> primary route. Phone-based iOS/Android control is retained in §9 as an
> alternative for teams with a Mac + iPhone combo. No code removed — only
> the documented default changed.

---

## 0. Prerequisites

### Hardware

- DJI Mavic Air 2 + RC controller + two charged batteries.
- A laptop (Linux / WSL2 — macOS and Windows work; Ubuntu 24.04 is the
  reference target).
- **USB-C data cable** (not charge-only) from laptop to RC controller.
- (Optional) iOS 16+ or Android 12+ phone/tablet — only for the §9
  phone-based path.
- (Optional) Bluetooth speaker for deterrent tone on-ground.
- Pi 4 fleet from Phase 5 (H1) already running.

### Accounts + credentials

- **None required for the laptop path.**
- **DJI developer account** (free) — needed only for §9 (iOS / Android
  `DJIAppKey` in `ios/SkyHerdCompanion/SupportingFiles/Config.xcconfig` or
  `android/SkyHerdCompanion/app/local.properties`).
- **Apple developer account** — needed only for §9 (signed iOS builds).

### Environment

**Laptop path (primary):**

```bash
export SKYHERD_MANUAL_OVERRIDE_TOKEN="$(openssl rand -hex 16)"
export DRONE_BACKEND=mavic_direct    # direct MAVSDK-over-USB-C to RC
```

**Phone path (§9, alternative):**

```bash
export DRONE_BACKEND=mavic           # enables MavicAdapter (DJI + MAVSDK)
export MAVIC_WS_URL=ws://<phone-ip>:8765
export MAVIC_MQTT_URL=mqtt://<laptop-ip>:1883
```

---

## 1. Step 1 — Laptop path (primary, 2026-04-25)

Full procedure: `docs/LAPTOP_DRONE_CONTROL.md`. Quick version:

```bash
# 1. Plug USB-C from laptop into the DJI RC (not the aircraft).
lsusb | grep -iE 'dji|silicon labs'     # expect one hit
ls /dev/ttyACM*                          # expect one tty

# 2. Launch the live dashboard with the MAVLink-over-USB-C backend.
export SKYHERD_MANUAL_OVERRIDE_TOKEN="$(openssl rand -hex 16)"
DRONE_BACKEND=mavic_direct uv run python -m skyherd.server.live \
    --port 8000 --host 127.0.0.1 --seed 42

# 3. Open http://localhost:8000/?drone=1
# 4. In browser console: window.__DRONE_MANUAL_TOKEN = "<your-token>"
# 5. Right-rail → Laptop Drone tab → hold ARM 3s → hold TAKEOFF 3s → LAND.
```

Test the wiring without flying anything: `make laptop-drone-smoke` —
14 mocked tests in under 10 s.

Friday preflight: see `docs/PREFLIGHT_CHECKLIST.md` Group 6 for the three
sanity checks that gate takeoff.

---

> **Sections 2–5 below assume the phone-based path (§9 alternative).** If
> you followed §1 (laptop-primary), skip to §6 Troubleshooting — the
> laptop path needs no MQTT broker, no companion app pairing, and no
> mid-flight failover test.

## 2. Step 2 — Bind the MQTT broker *(phone-based path only)*

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

**Phase 7.2 update (2026-04-23):** The iOS workflow now builds for the
device slice (`generic/platform=iOS`) and emits a Sideloadly-compatible
unsigned IPA at `build/ipa/SkyHerdCompanion-unsigned.ipa`. The build step
runs **without** `continue-on-error` — a failing Swift build is now a real
CI regression. Optional steps (xcarchive, simulator tests) keep
`continue-on-error: true` because they depend on runner capabilities.

To turn on the real DJI SDK, both platforms need the proprietary
artifact (iOS xcframework, Android AAR) to be manually placed:

- iOS: drop `DJISDK.xcframework` into
  `ios/SkyHerdCompanion/Frameworks/` and set `SKYHERD_SWIFT_FLAGS =
  DJI_SDK_AVAILABLE` in `SupportingFiles/Config.xcconfig`. See
  `HARDWARE_MAVIC_IOS.md`.
- Android: follow `HARDWARE_MAVIC_ANDROID.md` §3 for the AAR flow.

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

---

## 9. Alternative: phone-based control (legacy path)

**As of 2026-04-25 this is the alternative path.** The laptop route (§1)
is the default for Friday's demo. Use the content below only if you have a
Mac + paired iPhone/Android and specifically want to run the companion
app loop. The APK download + install flow remains supported.

**For Friday morning plug-in.** Two paths — primary (CI artifact) and
fallback (local build). The local build is always available and requires no
CI state, so it is safe to use as the default.

### Path A — GitHub Actions APK artifact (primary, when available)

Workflow: `.github/workflows/android-app.yml` (runs on every push to
`android/**`).

1. Confirm a recent run exists:
   ```bash
   gh run list --workflow=android-app.yml --repo george11642/skyherd-engine --limit 3
   ```
2. Download the latest artifact:
   ```bash
   gh run download --repo george11642/skyherd-engine \
       --name skyherd-companion-android-apk \
       --dir ~/Downloads/skyherd-apk
   ```
3. Install on phone:
   ```bash
   adb install ~/Downloads/skyherd-apk/app-debug.apk
   ```

**Web UI URL pattern:**
`https://github.com/george11642/skyherd-engine/actions/runs/<RUN_ID>/artifacts`

**Status as of 2026-04-24 (Phase 9 audit):** The `android-app.yml` and
`ios-app.yml` workflows are committed in this working tree but may not have
been pushed to `origin/main` yet — the workflow list on the GitHub side only
showed `ci`, `collar-firmware`, `fresh-clone-smoke`, `lighthouse` at the
time of the audit. **Friday prep:** after `git push origin main`, the first
push that touches `android/**` will trigger the build automatically; watch
`Actions` → `Android Companion App Build` and grab the APK from the artifact
tab. No workflow edits are required.

### Path B — Local build (fallback, always works)

Takes ~3 minutes on a laptop with JDK 17 + Android SDK installed. Zero CI
dependencies.

```bash
cd android/SkyHerdCompanion

# Generate Gradle wrapper if needed (first-time):
if [ ! -f gradlew ]; then
    gradle wrapper --gradle-version 8.5
fi
chmod +x gradlew

# Build the debug APK:
./gradlew assembleDebug --no-daemon --stacktrace

# Output:
#   app/build/outputs/apk/debug/app-debug.apk

# Install to phone:
adb install app/build/outputs/apk/debug/app-debug.apk
```

On Android, enable **Install unknown apps** for your file-manager before
sideloading. The APK is unsigned; DJI SDK artifacts are fetched by Gradle
(see `HARDWARE_MAVIC_ANDROID.md` §3 for the DJI dev account flow).

### Path C — iOS (if filming on iPhone)

Two paths, pick whichever matches your hardware:

**C1 — Xcode + Mac (real DJI SDK, real flight):**

```bash
cd ios/SkyHerdCompanion
cp SupportingFiles/Config.xcconfig.template SupportingFiles/Config.xcconfig
# edit SupportingFiles/Config.xcconfig — add DJI_API_KEY=<your_key>
# (and SKYHERD_SWIFT_FLAGS = DJI_SDK_AVAILABLE once the xcframework is in place)
./bootstrap.sh
xcodegen generate
open SkyHerdCompanion.xcodeproj
# Xcode → Product → Run on paired iPhone (requires Apple Developer account)
```

**C2 — Sideloadly + unsigned IPA (no Mac, stub DJI mode, Phase 7.2):**

1. Download the `skyherd-companion-ios-build` artifact from GitHub
   Actions.  Inside: `build/ipa/SkyHerdCompanion-unsigned.ipa`.
2. Open Sideloadly, drag the IPA, enter Apple ID, click **Start**.
3. On iPhone: Settings → General → VPN & Device Management → Trust.
4. App runs in DJI stub mode — MQTT + watchdog + router work; no drone
   actuation.

Phase 7.2's CI now emits a device-slice archive (not a Simulator `.app`);
the IPA packaging step in `.github/workflows/ios-app.yml` produces a
Sideloadly-compatible bundle.  Earlier claims in this runbook about
`xcrun simctl install` on a `.app` bundle were removed — the artifact is
now an IPA targeting real iPhones.
