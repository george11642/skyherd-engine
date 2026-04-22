# HARDWARE_MAVIC_ANDROID.md — Mavic Air 2 + SkyHerdCompanion Runbook

## What this gives you

`DRONE_BACKEND=mavic` routes every agent drone call through a WebSocket/MQTT
JSON bridge to an Android app (`SkyHerdCompanion`) on your phone.  The app
holds the DJI SDK connection to your Mavic Air 2 remote.

```
Agent tool call
  → MavicBackend (Python)
    → MQTT (laptop Mosquitto)
      → SkyHerdCompanion (Android)
        → DJI SDK V5
          → Mavic Air 2 remote → drone
```

---

## Prerequisites

- Android Studio Iguana (2023.2.1) or newer
- Android phone with USB debugging enabled (Android 8.0+ / API 26+)
- DJI Mavic Air 2 + RC remote
- USB-C cable (phone ↔ laptop for sideload; USB-C ↔ RC remote for control)
- Mosquitto MQTT broker running on your laptop (port 1883)

---

## Step 1 — Get a DJI API key

1. Go to [developer.dji.com](https://developer.dji.com) and sign in.
2. Create an app → select **Mobile SDK V5** → fill in `com.skyherd.companion`.
3. Copy the API key (a long alphanumeric string).

---

## Step 2 — Clone and configure

```bash
git clone https://github.com/george11642/skyherd-engine
cd skyherd-engine
```

Create `android/SkyHerdCompanion/local.properties` (never commit this file):

```properties
sdk.dir=/path/to/your/Android/Sdk
dji.sdk.api.key=YOUR_DJI_API_KEY_HERE
```

---

## Step 3 — Build and sideload

```bash
cd android/SkyHerdCompanion

# Plug phone into laptop, enable USB debugging (Settings → Developer Options)
make install
# or: ./gradlew installDebug
```

Accept the USB debugging prompt on the phone.

---

## Step 4 — Connect drone remote to phone

1. Launch **SkyHerdCompanion** on the phone.
2. Connect the DJI RC remote to the phone via USB-C (the cable that came with
   the Mavic Air 2 kit).
3. The app should show: **DJI SDK: registered** and **Connected to DJI: \<SN\>**
   within ~10 seconds.

---

## Step 5 — Start the MQTT broker (laptop)

```bash
# One-time: install mosquitto
sudo apt install mosquitto mosquitto-clients   # Ubuntu/Debian
brew install mosquitto                         # macOS

# Start the broker (or use make bus-up if you want Docker)
mosquitto -p 1883 &
```

---

## Step 6 — Configure the companion app

In the **SkyHerdCompanion** app:
1. Enter your laptop's IP in the broker URL field:
   `tcp://192.168.1.X:1883`  (find your laptop IP with `ip addr` or `ifconfig`)
2. Tap **Connect to SkyHerd**.
3. The status line should show **MQTT: tcp://... connected**.

---

## Step 7 — Configure Python backend

Add to `.env` (or export in your shell):

```bash
DRONE_BACKEND=mavic
MAVIC_WS_URL=ws://192.168.1.X:8765   # if using WebSocket mode
MAVIC_MQTT_URL=tcp://192.168.1.X:1883
```

---

## Step 8 — Smoke test

```bash
# In skyherd-engine repo root:
uv run python -c "
import asyncio
from skyherd.drone import get_backend

async def main():
    b = get_backend('mavic')
    await b.connect()
    print('Connected. Taking off to 5m...')
    await b.takeoff(5)
    print('Airborne. Returning home...')
    await b.return_to_home()
    await b.disconnect()
    print('Done.')

asyncio.run(main())
"
```

The Mavic Air 2 should lift to approximately 5 m and return to launch.

---

## Safety notes

- Always fly in an open area, clear of people and obstacles.
- The Python backend hard-caps altitude at 60 m (Part 107 compliance).
- Battery below 30% blocks takeoff; below 25% triggers automatic RTH.
- Wind above 21 kt vetoes takeoff (`WindGuard`).
- All waypoints are geofence-checked against `worlds/ranch_a.yaml` if a
  `geofence:` key is present in that file.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "DJI SDK: not registered" | Check `local.properties` has the right API key; re-run `make install` |
| "Drone: not connected" | Verify USB-C cable is plugged into RC; power on RC and drone |
| MQTT connection failed | Check laptop IP, broker is running on port 1883, same Wi-Fi network |
| `DroneUnavailable` from Python | Check MAVIC_WS_URL / MAVIC_MQTT_URL env vars match laptop IP |
| Takeoff rejected (battery) | Charge battery above 30% before flying |
