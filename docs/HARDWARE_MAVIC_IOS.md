# HARDWARE_MAVIC_IOS — iOS Companion App Runbook

George-facing runbook for getting SkyHerdCompanion (iOS) running on a real
iPhone or iPad connected to the DJI Mavic Air 2.

---

## Prerequisites

1. **macOS 13+** with **Xcode 15+** installed from the Mac App Store.
2. Install build tools:
   ```bash
   brew install xcodegen ios-deploy
   ```
3. An **Apple Developer account** — the free tier is sufficient for direct device
   sideloading (7-day cert); a paid account ($99/year) is needed for TestFlight.
4. DJI API key (see below).

---

## Get a DJI API Key

1. Sign in at <https://developer.dji.com>.
2. Go to **My Apps → Create App**.
3. Set:
   - **Bundle ID**: `com.skyherd.companion`
   - **Platform**: iOS
   - (Register a separate entry for Android if not already done — same bundle ID is fine)
4. Copy the generated key; you'll paste it in the next section.

---

## Build & Install

```bash
cd /path/to/skyherd-engine
cd ios/SkyHerdCompanion
./bootstrap.sh          # installs XcodeGen, generates SkyHerdCompanion.xcodeproj
open SkyHerdCompanion.xcodeproj
```

1. In Xcode, open **SupportingFiles/Info.plist**.
2. Find the key `DJIAppKey` and replace `$(DJI_API_KEY)` with your real key.
   (Alternatively, create `ios/SkyHerdCompanion/Config.xcconfig` and set
   `DJI_API_KEY = your_key_here` — Xcode will expand the variable automatically.)
3. Select your iPhone as the run destination in the scheme selector.
4. Press **⌘R** to build and install on the device.
   - On first run, go to **iPhone > Settings > General > VPN & Device Management**
     and trust your developer certificate.

### Add DJISDK.xcframework

The DJI Mobile SDK V5 ships as a closed-source binary XCFramework:

1. Download from <https://developer.dji.com/mobile-sdk/> (iOS SDK V5).
2. Extract and place `DJISDK.xcframework` in `ios/SkyHerdCompanion/Frameworks/`.
3. In `project.yml`, uncomment:
   ```yaml
   - framework: Frameworks/DJISDK.xcframework
     embed: true
   ```
4. Re-run `./bootstrap.sh` to regenerate the Xcode project with the framework linked.
5. Add the compile flag `DJI_SDK_AVAILABLE` to the build settings (XcodeGen will
   pick it up if you add it to `settings.base` in `project.yml`).

Without the framework the app compiles in **stub mode** — all DJI calls log
warnings and return stub values.  This is sufficient for protocol / safety-guard
testing without hardware.

---

## Connect Mavic Air 2

1. Turn on the Mavic Air 2 and its remote controller.
2. Connect the remote controller to the iPhone via **USB-C** (newer iPhones) or
   **Lightning → USB-C adapter** (iPhone XS / 11 era).
3. The DJI SDK detects the aircraft automatically once the app is running.
4. In the app you should see **"DJI: Connected"** within ~10 seconds.

---

## Configure Laptop Backend

On the laptop running SkyHerd Engine:

```bash
# In .env or shell
export DRONE_BACKEND=mavic
export MAVIC_WS_URL=ws://<iphone-local-ip>:8765
```

Find the iPhone's local IP in **Settings → Wi-Fi → (your network) → IP address**.
Both laptop and iPhone must be on the same LAN (or direct USB tether).

The iOS app opens a WebSocket **server** on port 8765.  The Python MavicBackend
is the **client** that connects to it.

### Quick Connectivity Test

```bash
uv run python -c "
import asyncio
from skyherd.drone.mavic import MavicBackend

async def test():
    b = MavicBackend()
    await b.connect()
    state = await b.state()
    print(state)
    await b.disconnect()

asyncio.run(test())
"
```

### Takeoff Test (5 m)

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

| Symptom | Fix |
|---|---|
| "DJI: Registering…" hangs | API key wrong or network blocked |
| "DJI: Disconnected" after cable insert | USB trust not accepted on iPhone |
| `MAVIC_WS_URL` refused | iPhone behind firewall; check iOS > Settings > Privacy > Local Network |
| `E_BATTERY_LOW` | Charge Mavic to >25% before ops |
| `E_WIND_CEILING` | Wind >21 kt — wait for calmer conditions |
| Python `DroneUnavailable` | iPhone IP changed; update `MAVIC_WS_URL` |
