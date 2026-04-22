# HARDWARE_F3_INAV.md — SP Racing F3 + iNav 7.x Runbook

## What this gives you

`DRONE_BACKEND=f3_inav` routes every agent drone call through MAVSDK-Python
directly to an SP Racing F3 flight controller flashed with iNav 7.x firmware,
bridged over USB-serial via `mavlink-router`.

```
Agent tool call
  → F3InavBackend (Python)
    → MAVSDK-Python (UDP 14550)
      → mavlink-router (laptop)
        → USB-serial (FTDI adapter)
          → F3 MAVLink UART → iNav 7.x
```

---

## Bill of Materials

| Part | Suggested model | Approx cost |
|---|---|---|
| SP Racing F3 flight controller | SP Racing F3 EVO or F3 Acro | ~$25 |
| GPS module | Matek M10Q-5883 or BN-180 | ~$15 |
| FTDI USB-TTL adapter | FTDI FT232RL breakout | ~$5 |
| 4S LiPo (or 3S for bench testing) | any 1300–1500 mAh | ~$20 |
| USB-A ↔ micro-USB cable | — | ~$3 |

**Total BOM: ~$68** (excluding frame, motors, ESCs, props — which you likely already have)

---

## Step 1 — Wire the GPS

Connect GPS to **UART2** on the F3 board:

| GPS pin | F3 pad |
|---|---|
| TX | UART2 RX |
| RX | UART2 TX |
| VCC | 3.3V or 5V (check GPS datasheet) |
| GND | GND |

---

## Step 2 — Wire the FTDI adapter (laptop bridge)

Connect FTDI to **UART1** on the F3 board for the MAVLink output:

| FTDI | F3 pad |
|---|---|
| TX | UART1 RX |
| RX | UART1 TX |
| GND | GND |

Do **not** connect 5V from FTDI when the F3 is also powered by battery/BEC —
power from only one source at a time.

---

## Step 3 — Flash iNav 7.x

1. Download [iNav Configurator](https://github.com/iNavFlight/inav-configurator/releases)
   (latest stable, v7.x).
2. Connect F3 via USB (micro-USB cable directly to F3).
3. Open iNav Configurator → **Firmware Flasher**.
4. Select target: **SPRACINGF3** (or **SPRACINGF3EVO** depending on the
   silkscreen on your board — look for the board name printed near the MCU).
5. Flash latest iNav 7.x release. Keep **Full chip erase** checked for a
   clean flash.

---

## Step 4 — Configure ports in iNav Configurator

Go to **Ports** tab:

| UART | Usage | Baud |
|---|---|---|
| USB/VCP | MSP (for configurator) | Auto |
| UART1 | MAVLink (for mavlink-router) | 115200 |
| UART2 | GPS | 115200 |

Click **Save and Reboot**.

---

## Step 5 — Configure GPS

Go to **Configuration** tab:
- Enable GPS: **ON**
- Protocol: **UBLOX**
- Ground assistance type: **none** (or SBAS if you have coverage)

Click **Save and Reboot**.  After reboot, go to **GPS** tab and confirm lock
within a few minutes outdoors.

---

## Step 6 — PID starting point (conservative baseline)

These are 50% of iNav's stock F3 defaults.  Tune from here after first hover.

| Axis | P | I | D |
|---|---|---|---|
| Roll | 20 | 30 | 23 |
| Pitch | 20 | 30 | 23 |
| Yaw | 25 | 45 | 0 |

**Important**: verify arming with **no props** first.  Hold the throttle low,
activate arming switch.  Motors should spin slowly.  Disarm.  Mount props.

---

## Step 7 — Set up mavlink-router on laptop

```bash
# Install mavlink-router (Ubuntu/Debian)
sudo apt install git cmake build-essential pkg-config
git clone https://github.com/mavlink-router/mavlink-router
cd mavlink-router
git submodule update --init --recursive
./autogen.sh && ./configure CFLAGS='-g -O2' --sysconfdir=/etc/mavlink-router
make
sudo make install

# Run: bridge F3 USB serial to UDP 14550
mavlink-router -e 0.0.0.0:14550 /dev/ttyUSB0:115200
```

Find your FTDI device: `ls /dev/ttyUSB*` after plugging in the adapter.
Use `ttyACM0` if the F3 is connected directly via USB-C (MSP mode).

---

## Step 8 — Configure Python backend

```bash
export DRONE_BACKEND=f3_inav
# Optional: set pre-flight wind reading (knots) for WindGuard
export F3_WIND_KT=0   # set to actual measured wind before outdoor flights

# Optional: if you add an IR camera later
export F3_HAS_IR=1
```

---

## Step 9 — Smoke test

```bash
# Indoors, no props, bench test:
DRONE_BACKEND=f3_inav uv run python -m skyherd.drone.cli takeoff --alt 2
```

The expected output is MAVLink telemetry confirming arm + takeoff.  If
`mavlink-router` is not running first, you'll see:

> DroneUnavailable: Cannot connect to F3/iNav at udpin://0.0.0.0:14550
> Hint: Start mavlink-router first; see docs/HARDWARE_F3_INAV.md

---

## Safety checklist before first outdoor flight

- [ ] GPS 3D fix confirmed in iNav Configurator (>6 satellites)
- [ ] Battery above 30% (`BatteryGuard.check_takeoff`)
- [ ] Wind below 18 kt (`WindGuard` ceiling for F3 quads)
- [ ] Geofence polygon set in `worlds/ranch_a.yaml` (`geofence:` key)
- [ ] Props **off** for arming / disarming bench test
- [ ] Props **on**, stand behind and to the side for first hover
- [ ] RTH home point set (iNav sets it automatically on first GPS fix after arm)
- [ ] Failsafe tested: remove RC signal → drone should hover then RTH

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'mavsdk'` | `uv add mavsdk` |
| `DroneUnavailable: Cannot connect to F3/iNav` | Start `mavlink-router` first |
| GPS not locking | Move outdoors; check UART2 wiring polarity (TX↔RX swap) |
| Arm fails in iNav | Check accelerometer calibration, level horizon in Configurator |
| `BatteryTooLow` on takeoff | Charge battery above 30%; check BEC/PDB wiring |
| Altitude drifts | Re-calibrate barometer in iNav Configurator |
