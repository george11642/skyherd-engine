# SkyHerdCompanion — iOS

SkyHerdCompanion is the iOS companion app for the DJI Mavic Air 2 that bridges
the SkyHerd Engine laptop backend to the drone via DJI Mobile SDK V5. The app
runs on iPhone or iPad (iOS 16+), maintains a WebSocket connection to the Python
`MavicBackend`, translates incoming JSON commands into DJI SDK calls, and streams
telemetry back as acknowledgement messages.

## Architecture

```
SkyHerd Engine (laptop)
  └─ MavicBackend (Python)
       └─ WebSocket JSON {"cmd":…,"args":…,"seq":…}
            └─ SkyHerdCompanion (this app, iPhone/iPad)
                 └─ DJI Mobile SDK V5
                      └─ Mavic Air 2 remote controller (USB-C / Lightning)
```

## Prerequisites

- macOS 13+ with Xcode 15+
- `brew install xcodegen ios-deploy`
- Apple Developer account (free tier works for device sideloading)
- DJI API key registered at <https://developer.dji.com> — bundle ID `com.skyherd.companion`

## Quick Start

```bash
cd ios/SkyHerdCompanion
./bootstrap.sh          # installs XcodeGen if needed, generates .xcodeproj
open SkyHerdCompanion.xcodeproj
```

1. Open `SupportingFiles/Info.plist` and replace `$(DJI_API_KEY)` with your key.
2. Select your iPhone as the run destination in Xcode.
3. Press ⌘R to build and install on device.
4. Connect the Mavic Air 2 remote controller to the iPhone via USB.

## DJI API Key Provisioning

Register the app at <https://developer.dji.com/user/apps>:

- **Bundle ID**: `com.skyherd.companion`
- **Platform**: iOS (register a separate entry for Android if not already done)
- Copy the generated key into `SupportingFiles/Info.plist` under the key `DJIAppKey`.

## Environment / Config

On the laptop, set:

```bash
export DRONE_BACKEND=mavic
export MAVIC_WS_URL=ws://<iphone-ip>:8765
```

The iPhone IP must be on the same LAN as the laptop. The app binds a WebSocket
server on port 8765 by default (configurable in Settings > SkyHerd).

## Tests (Swift)

```bash
make test
# or directly:
xcodebuild test \
  -project SkyHerdCompanion.xcodeproj \
  -scheme SkyHerdCompanion \
  -destination 'platform=iOS Simulator,name=iPhone 15'
```

## Tests (Python protocol schema)

From the repo root:

```bash
uv run pytest tests/hardware/test_mavic_protocol.py -v
```
