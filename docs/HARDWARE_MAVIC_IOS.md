# HARDWARE_MAVIC_IOS — iOS Companion App Runbook

George-facing runbook for getting SkyHerdCompanion (iOS) running on a real
iPhone or iPad connected to the DJI Mavic Air 2.

> **Phase 7.2 update (2026-04-23):** WebSocket transport was removed;
> MQTT is now the only command path. A no-Mac Sideloadly install path
> is documented below for quick judge demos.

---

## Two install paths

| Path                         | Needs Mac? | DJI SDK? | Use when                            |
|------------------------------|------------|----------|-------------------------------------|
| **Xcode + cable**            | yes        | yes      | Real flight, dev iteration          |
| **Sideloadly + unsigned IPA**| **no**     | no (stub)| Protocol demo, no-Mac judge laptop  |

---

## Prerequisites

### Xcode path

1. **macOS 13+** with **Xcode 15+** from the Mac App Store.
2. Install build tools:
   ```bash
   brew install xcodegen ios-deploy
   ```
3. An **Apple Developer account** — free tier is enough for direct device
   sideloading (7-day cert); paid ($99/year) is needed for TestFlight.
4. DJI API key (see below).

### Sideloadly path

1. Any computer (Windows or macOS) with [Sideloadly](https://sideloadly.io)
   installed.
2. The `skyherd-companion-ios-build` artifact from a green GitHub Actions
   **iOS Companion App Build** run.
3. An Apple ID (free).
4. Phase 7.2's unsigned IPA lives at
   `build/ipa/SkyHerdCompanion-unsigned.ipa` inside the artifact zip.

No DJI SDK calls will work in the sideloaded build — only MQTT, CommandRouter,
safety guards, and the lost-signal watchdog run (stub mode).

---

## Get a DJI API Key

1. Sign in at <https://developer.dji.com>.
2. Go to **My Apps → Create App**.
3. Set:
   - **Bundle ID**: `com.skyherd.companion`
   - **Platform**: iOS (register a separate entry for Android if not already done —
     same bundle ID is fine)
4. Copy the generated key; you'll paste it in the next section.

---

## Xcode Build & Install

```bash
cd /path/to/skyherd-engine
cd ios/SkyHerdCompanion

# One-time: copy the xcconfig template
cp SupportingFiles/Config.xcconfig.template SupportingFiles/Config.xcconfig
${EDITOR:-vi} SupportingFiles/Config.xcconfig   # fill in DJI_API_KEY

./bootstrap.sh          # installs XcodeGen, generates SkyHerdCompanion.xcodeproj
open SkyHerdCompanion.xcodeproj
```

1. `Config.xcconfig` feeds `DJI_API_KEY` into Info.plist automatically.
   Never edit Info.plist directly.
2. Select your iPhone as the run destination in the scheme selector.
3. Press **⌘R** to build and install on the device.
   - On first run, go to **iPhone → Settings → General → VPN & Device
     Management** and trust your developer certificate.

### Add DJISDK.xcframework (required for real flight)

The DJI Mobile SDK V5 ships as a closed-source binary XCFramework:

1. Download **DJI Mobile SDK V5 iOS 5.11.x** (or newer) from
   <https://developer.dji.com/mobile-sdk/>.
2. Extract and place `DJISDK.xcframework` at:
   ```
   ios/SkyHerdCompanion/Frameworks/DJISDK.xcframework
   ```
3. In `project.yml`, uncomment the framework dependency:
   ```yaml
   dependencies:
     - framework: Frameworks/DJISDK.xcframework
       embed: true
   ```
4. In `SupportingFiles/Config.xcconfig`, set:
   ```xcconfig
   SKYHERD_SWIFT_FLAGS = DJI_SDK_AVAILABLE
   ```
   `project.yml` threads this into `SWIFT_ACTIVE_COMPILATION_CONDITIONS`, so
   `#if DJI_SDK_AVAILABLE` inside `DJIBridge.swift` lights up the real SDK
   calls.  Without this flag the app compiles in **stub mode** — every DJI
   call logs a warning and returns placeholder state, sufficient for
   protocol / safety-guard testing without hardware.
5. Re-run `./bootstrap.sh`.

---

## Sideloadly Install (no Mac)

1. Open the GitHub Actions run for your commit → **iOS Companion App Build**
   → Artifacts → download `skyherd-companion-ios-build.zip`.
2. Unzip.  You'll see `build/ipa/SkyHerdCompanion-unsigned.ipa`.
3. Launch Sideloadly, drag the IPA onto the main window.
4. Enter your Apple ID, keep the bundle ID `com.skyherd.companion` (match
   the DJI dev app registration if you plan to reuse for a real SDK build
   later), click **Start**.
5. On iPhone, **Settings → General → VPN & Device Management → Trust**
   your Apple ID profile.
6. Launch SkyHerd.  Enter `MAVIC_MQTT_HOST` (laptop LAN IP) in the
   bundled settings panel or rely on the default `localhost` if using a
   USB-tethered broker.

This build runs stub-mode DJI — the watchdog, router, and MQTT pipeline are
real; drone actuation is logs only.

---

## Connect Mavic Air 2 (Xcode path only)

1. Turn on the Mavic Air 2 and its remote controller.
2. Connect the remote controller to the iPhone via **USB-C** (newer iPhones) or
   **Lightning → USB-C adapter** (iPhone XS / 11 era).
3. The DJI SDK detects the aircraft automatically once the app is running.
4. In the app you should see **"DJI: Connected"** within ~10 seconds.

---

## Configure Laptop Backend

```bash
# In .env or shell
export DRONE_BACKEND=mavic
export MAVIC_MQTT_HOST=<laptop-ip>     # or 127.0.0.1 for direct
export MAVIC_MQTT_PORT=1883
```

Find the iPhone's local IP in **Settings → Wi-Fi → (your network) → IP
address**.  Both laptop and iPhone must be on the same LAN (or direct USB
tether with reverse proxy).

### Quick Connectivity Test

```bash
# Start the ranch broker + adapter
make hardware-demo-sim-up

# On the phone, check the Connection Status row reads:
#   DJI SDK: Registered  (or Stub on sideloaded builds)
#   MQTT:    Connected
#   Watchdog: Running
```

### Takeoff Test (5 m, real SDK only)

With the app running, from the laptop:

```bash
uv run python -c "
import asyncio
from skyherd.drone import get_backend

async def test():
    b = get_backend('mavic')
    await b.connect()
    await b.takeoff(5)
    await asyncio.sleep(3)
    await b.return_to_home()
    await b.disconnect()

asyncio.run(test())
"
```

---

## TestFlight Distribution (Optional)

For over-the-air testing or demo to judges without a cable:

```bash
# Archive
xcodebuild archive \
  -project ios/SkyHerdCompanion/SkyHerdCompanion.xcodeproj \
  -scheme SkyHerdCompanion \
  -archivePath build/SkyHerdCompanion.xcarchive

# Export IPA (requires ExportOptions.plist — see Apple docs)
xcodebuild -exportArchive \
  -archivePath build/SkyHerdCompanion.xcarchive \
  -exportPath build/SkyHerdCompanion-ipa \
  -exportOptionsPlist ExportOptions.plist

# Upload to App Store Connect / TestFlight
xcrun altool --upload-app \
  -f build/SkyHerdCompanion-ipa/SkyHerdCompanion.ipa \
  -t ios \
  --apiKey <API_KEY> \
  --apiIssuer <ISSUER_ID>
```

---

## Troubleshooting

| Symptom                                    | Fix                                                   |
|--------------------------------------------|-------------------------------------------------------|
| `DJI API key missing` banner at launch     | Config.xcconfig not populated; see Xcode path step 1  |
| DJI SDK status stays "Registering…"        | API key wrong or network blocked                      |
| DJI SDK status "Disconnected" after cable  | USB trust not accepted on iPhone — unplug + replug    |
| MQTT status "Disconnected"                 | Check `MAVIC_MQTT_HOST`; ensure LAN allows :1883      |
| `E_BATTERY_LOW`                            | Charge Mavic battery to >30 % (Phase 7.2 floor)       |
| `E_WIND_CEILING`                           | Wind ≥ 21 kt — wait for calmer conditions             |
| `E_UNSUPPORTED: gotoLocation requires...` | Expected for `patrol` commands until DJIWaypointV2     |
| Watchdog fires RTH unexpectedly            | MQTT dropped > 30 s while airborne; check LAN         |
| Python `DroneUnavailable`                  | iPhone IP changed; update `MAVIC_MQTT_HOST`           |
| Sideloaded app says "Stub (no SDK)"        | Expected — Sideloadly path cannot include xcframework |
