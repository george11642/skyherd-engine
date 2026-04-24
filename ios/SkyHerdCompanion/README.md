# SkyHerdCompanion — iOS

SkyHerdCompanion is the iOS companion app for the DJI Mavic Air 2 that bridges
the SkyHerd Engine laptop backend to the drone via DJI Mobile SDK V5. The app
runs on iPhone or iPad (iOS 16+), maintains an MQTT connection to the laptop
ranch broker, translates incoming JSON commands into DJI SDK calls, and
publishes telemetry + acknowledgements back to the broker.

> **Phase 7.2:** WebSocket transport was removed — MQTT is the sole
> command path. MissionV1 envelopes are accepted natively (see
> `docs/MAVIC_MISSION_SCHEMA.md`).

## Architecture

```
SkyHerd Engine (laptop)
  └─ MavicAdapter (Python)  → mosquitto broker on laptop
       └─ MQTT JSON (MissionV1 envelope or legacy {cmd,args,seq})
            └─ SkyHerdCompanion (iPhone/iPad)
                 ├─ CommandRouter → SafetyGuards → DJIBridge
                 ├─ LostSignalWatchdog (30 s MQTT loss → RTH)
                 └─ DJI Mobile SDK V5
                      └─ Mavic Air 2 remote controller (USB-C / Lightning)
```

Published topics (see `docs/MAVIC_MISSION_SCHEMA.md` §5):

| Direction  | Topic                        | Payload                      |
|------------|------------------------------|------------------------------|
| ← broker   | `skyherd/drone/cmd/#`        | DroneCommand or MissionV1     |
| → broker   | `skyherd/drone/ack/ios`      | DroneAck                      |
| → broker   | `skyherd/drone/state/ios`    | DroneStateSnapshot            |
| → broker   | `skyherd/drone/status/ios`   | `online` / `offline` retained |

## Prerequisites (Mac path)

- macOS 13+ with Xcode 15+
- `brew install xcodegen ios-deploy`
- Apple Developer account (free tier works for device sideloading — 7-day
  cert)
- DJI API key registered at <https://developer.dji.com> — bundle ID
  `com.skyherd.companion`

## Prerequisites (no-Mac / Sideloadly path)

You can install the app on an iPhone **without a Mac** using the unsigned
IPA produced by GitHub Actions + [Sideloadly](https://sideloadly.io/) on
Windows or another Mac.  Phase 7.2 reworked `.github/workflows/ios-app.yml`
to emit a Sideloadly-compatible unsigned IPA:

1. Push a commit to `ios/**`; wait for **Actions → iOS Companion App
   Build** to go green.
2. Download the `skyherd-companion-ios-build` artifact.  The `build/ipa/`
   folder contains `SkyHerdCompanion-unsigned.ipa`.
3. Install [Sideloadly](https://sideloadly.io) on any computer (Windows or
   macOS works).
4. Drag the IPA into Sideloadly, enter your Apple ID, click **Start**.
   The app is re-signed with a 7-day free-tier cert and copied onto your
   iPhone over USB.
5. On iPhone, **Settings → General → VPN & Device Management → Trust** your
   Apple ID profile so the newly installed app is permitted to run.
6. Launch SkyHerd.  Go to **Settings → SkyHerd** and set
   `MAVIC_MQTT_HOST` to your laptop's LAN IP.

> **DJI SDK caveat:** even with the app sideloaded, real flight requires
> `DJISDK.xcframework` (~350 MB, proprietary, not checked in).  Sideloadly
> installs only the **stub** build that runs CommandRouter, SafetyGuards,
> and the watchdog — but every DJI call degrades to `AppLogger.dji.warning`.
> For a flying demo you still need a Mac + the xcframework drop in
> `Frameworks/DJISDK.xcframework`.

## DJI SDK version pin

| Component           | Version                                     |
|---------------------|---------------------------------------------|
| DJI Mobile SDK V5   | **5.11.x** (tested Apr 2026; newer should work) |
| XCFramework path    | `ios/SkyHerdCompanion/Frameworks/DJISDK.xcframework` |
| Flag to enable      | `SKYHERD_SWIFT_FLAGS = DJI_SDK_AVAILABLE` in `Config.xcconfig` |

## Quick Start (Mac)

```bash
cd ios/SkyHerdCompanion

# One-time: copy the xcconfig template and fill in your DJI key
cp SupportingFiles/Config.xcconfig.template SupportingFiles/Config.xcconfig
${EDITOR:-vi} SupportingFiles/Config.xcconfig

./bootstrap.sh          # runs xcodegen
open SkyHerdCompanion.xcodeproj
```

1. `Config.xcconfig` feeds `$(DJI_API_KEY)` into Info.plist automatically.
2. Select your iPhone as the run destination in Xcode.
3. Press ⌘R to build and install on device.
4. Connect the Mavic Air 2 remote controller to the iPhone via USB.

## DJI API Key Provisioning

Register the app at <https://developer.dji.com/user/apps>:

- **Bundle ID**: `com.skyherd.companion`
- **Platform**: iOS (register a separate entry for Android if not already done)
- Paste the generated key into `SupportingFiles/Config.xcconfig` under
  `DJI_API_KEY = ...`.  Never commit the populated `Config.xcconfig`
  (`.gitignore` excludes it).

## Environment / Config (laptop side)

```bash
export DRONE_BACKEND=mavic
export MAVIC_MQTT_HOST=<laptop-ip>      # or "localhost" for direct
export MAVIC_MQTT_PORT=1883
```

Both phone and laptop must share a LAN (or be on a dev-laptop hotspot with
the broker reachable).

App-side overrides (set on the iPhone via Settings or env when testing):

| Key (env / UserDefaults)       | Purpose                                  |
|--------------------------------|------------------------------------------|
| `MAVIC_MQTT_HOST`              | Broker host (required)                   |
| `MAVIC_MQTT_PORT`              | Broker port (default 1883)               |
| `DJI_API_KEY`                  | Override xcconfig key (CI / tests)       |
| `MAVIC_BATTERY_FLOOR_PCT`      | Per-build battery floor override         |

## Tests (Swift)

```bash
make test
# or directly:
xcodebuild test \
  -project SkyHerdCompanion.xcodeproj \
  -scheme SkyHerdCompanion \
  -destination 'platform=iOS Simulator,name=iPhone 15'
```

Phase 7.2 test suites:

- `SafetyGuardTests`        — geofence, battery, wind, altitude
- `CommandRouterTests`      — dispatch + MissionV1 envelope + seq eviction
- `ProtocolTests`           — JSON wire compat with Python
- `LostSignalWatchdogTests` — 30 s grace → RTH behaviour
- `DJIBridgeTests`          — gotoLocation unsupported, stub takeoff, key gating
- `MQTTBridgeTests`         — decode + dispatch pipeline

## Tests (Python protocol schema)

From the repo root:

```bash
uv run pytest tests/hardware/test_mavic_protocol.py -v
```
