# HARDWARE_PI_FLEET.md — Pi + Galileo Edge Fleet Commissioning Guide

George runs two heterogeneous edge nodes on the ranch LAN:

- **`edge-house`** — **Raspberry Pi 4.** Vision compute for every trough camera
  (troughs 1–6). MegaDetector V6 on the CPU, rule-mode fallback.
- **`edge-tank`** — **Intel Galileo Gen 1.** Environmental telemetry:
  water-tank level (Scenario 3) and weather (Scenario 5). No vision.
  400 MHz Quark X1000, 256 MB RAM, Arduino Uno R3 headers, Yocto Linux.

This doc covers naming, per-node topology, MQTT fan-in, and the one-command
provisioning flow for both. Read [`docs/HARDWARE_PI_EDGE.md`](HARDWARE_PI_EDGE.md)
first for the single-Pi H1 runbook; read
[`docs/HARDWARE_GALILEO.md`](HARDWARE_GALILEO.md) for the Galileo runbook.
This file is additive — both runbooks still apply to their node.

> **Why split this way?** The Pi has ARM + a camera interface + enough RAM
> for MegaDetector. The Galileo has Arduino-compat GPIO for cheap analog
> sensors and a tiny power budget. Pairing them keeps each node doing what
> its silicon is good at — agents never notice, because they subscribe to
> topics, not hardware.

---

## Fleet topology at a glance

```
ranch LAN (iPhone hotspot 172.20.10.0/28 OR home router)
│
├── edge-house  — Raspberry Pi 4      EDGE_ID=edge-house
│     role:     vision (all trough cameras)
│     network:  iPhone hotspot wifi   172.20.10.x
│     troughs:  trough_1..trough_6
│     topics:   skyherd/ranch_a/trough_cam/edge-house
│               skyherd/ranch_a/events/camera.motion
│               skyherd/ranch_a/edge_status/edge-house    (heartbeat 30 s)
│
└── edge-tank   — Intel Galileo Gen 1                EDGE_ID=edge-tank
      role:     water-tank level + weather telemetry
      network:  Windows ICS ethernet  192.168.137.x  (or home router LAN)
                Ethernet only — Gen 1 has no wifi (no mPCIe slot).
      topics:   skyherd/ranch_a/water_tank/edge-tank    (tank level, 60 s)
                skyherd/ranch_a/weather/edge-tank       (temp/humidity, 60 s)
                skyherd/ranch_a/edge_status/edge-tank   (heartbeat 30 s)

Both nodes publish to the same Mosquitto broker (laptop). No peer-to-peer.
Agents subscribe to skyherd/ranch_a/# and consume both nodes identically.
```

---

## Naming convention

| Unit | Hostname | `EDGE_ID` | Role | Troughs |
|------|----------|-----------|------|---------|
| Pi 4 — ranch house | `edge-house` | `edge-house` | Vision (trough cams) | `trough_1..trough_6` |
| Galileo Gen 1 — tank | `edge-tank` | `edge-tank` | Water + weather | — |

Hostnames are set at flash time via Raspberry Pi Imager (Pi) or the Yocto
`/etc/hostname` file (Galileo). `EDGE_ID` is set in `/etc/skyherd/edge.env`
(Pi) or `/etc/skyherd/galileo.env` (Galileo). Both values can be overridden
freely — they only need to be unique per ranch.

> **Legacy note:** the older two-Pi-4 layout used `edge-house` (troughs 1–2) +
> `edge-barn` (troughs 3–6). `edge-barn` is still accepted by the scripts and
> tests for backward compatibility; new deployments should use
> `edge-house` covering all six troughs and `edge-tank` for telemetry.

---

## Network split

The two nodes sit on different physical links because the Galileo has no
built-in wifi.

### Pi 4 — `edge-house`

- Joins the **iPhone hotspot wifi** (subnet `172.20.10.0/28`).
- Credentials come from `/boot/firmware/skyherd-credentials.json` at first boot.
- MQTT URL points at the laptop on the hotspot side:
  `mqtt://172.20.10.2:1883` (or whatever IP the laptop holds).

### Galileo Gen 1 — `edge-tank`

Gen 1 has no wifi option at all (no mPCIe slot, and USB wifi dongles are out
of scope). **Ethernet is the only supported path.** Pick one of three setups:

1. **Ethernet-over-USB bridge on the laptop (recommended).** Laptop runs
   Windows Internet Connection Sharing (ICS) from the wifi NIC (iPhone hotspot)
   to a USB-Ethernet adapter. Galileo plugs into the adapter with a short
   Cat5/6 cable.
   - Galileo DHCPs to `192.168.137.x` (Windows ICS default).
   - Laptop ICS side: `192.168.137.1`.
   - MQTT broker must bind to `192.168.137.1:1883` (or `0.0.0.0:1883`).
   - Add a netsh portproxy so the broker is reachable from the ICS subnet:
     ```
     netsh interface portproxy add v4tov4 listenaddress=192.168.137.1 \
         listenport=1883 connectaddress=127.0.0.1 connectport=1883
     ```
2. **Home router.** Put the laptop and the Galileo on the same router's LAN
   and skip the iPhone hotspot entirely. Simpler if you're at home and don't
   need cellular backhaul.
3. **Sim mode.** Run a simulated sensor publisher on the laptop in a Docker
   stand-in for `edge-tank`. The real Galileo becomes a "nice to have" for
   the on-stage demo only. See [`docs/HARDWARE_GALILEO.md`](HARDWARE_GALILEO.md)
   § Sim mode. This is the fallback the video can use if the Galileo acts up.

---

## One-command provisioning

One command per node:

```bash
# Pi 4 — ranch house (vision)
make edge-pi-setup EDGE_ID=edge-house

# Intel Galileo — tank (telemetry)
make edge-galileo-setup
```

`edge-pi-setup` runs the five-phase WSL2-aware bringup in
`scripts/setup-edge-pi.sh`: broker, portproxy, wifi capture, SD flash, Pi
discovery, bootstrap over SSH, heartbeat verification.

`edge-galileo-setup` prints the manual flash + bootstrap steps from
[`hardware/galileo/README.md`](../hardware/galileo/README.md). The Galileo
flash is a one-time microSD task; after that, every boot self-registers
via `hardware/galileo/bootstrap.sh`.

Config examples live at:
- `src/skyherd/edge/configs/edge-house.env.example`
- `hardware/galileo/credentials.example.json`

---

## MQTT topics per node

| Message type | Topic pattern | Published by |
|---|---|---|
| Trough-cam reading | `skyherd/{ranch}/trough_cam/edge-house` | Pi every N seconds |
| Camera motion event | `skyherd/{ranch}/events/camera.motion` | Pi when confidence ≥ 0.5 |
| Water-tank reading | `skyherd/{ranch}/water_tank/edge-tank` | Galileo every 60 s |
| Weather reading | `skyherd/{ranch}/weather/edge-tank` | Galileo every 60 s (if sensor) |
| Heartbeat / status | `skyherd/{ranch}/edge_status/{edge_id}` | Both every 30 s |

Subscribe to everything at once:

```bash
mosquitto_sub -v -t 'skyherd/ranch_a/#'
```

Subscribe only to heartbeats (both nodes):

```bash
mosquitto_sub -v -t 'skyherd/ranch_a/edge_status/#'
```

---

## Dashboard visibility

Both nodes appear as distinct edges on the SkyHerd dashboard (green heartbeat
indicator) once they start publishing `edge_status`. The Galileo row carries
`kind=telemetry` in its heartbeat so the dashboard can hide the
MegaDetector-specific fields (CPU temp is still reported — Galileo reads
it from its own thermal sysfs).

`/api/edges` aggregates `edge_status` and returns
`{ edge_id, last_seen_ts, cpu_temp_c, mem_pct, online }`. A node is marked
`online: false` if `now - last_seen_ts > 90` seconds.

---

## Failover behaviour

If either node goes dark:

1. Its `edge_status` heartbeat stops arriving.
2. After **90 seconds** of silence, agents emit `edge.offline`:
   ```json
   {"kind":"edge.offline","edge_id":"edge-tank","last_seen_ts":1714000000,"ranch":"ranch_a"}
   ```
3. Agents adapt:
   - Pi offline → sim trough-cam fallback for all six troughs.
   - Galileo offline → sim water-tank + weather fallback; the LoRaWAN breach
     path in Scenario 3 still works via `mosquitto_pub` from the demo script.

Tune via `EDGE_OFFLINE_THRESHOLD_S` in the agent environment.

---

## Detector mode (Pi only)

Set `EDGE_DETECTOR_MODE` in `/etc/skyherd/edge.env` on the Pi:

| Mode | Latency (Pi 4) | Requirement | Notes |
|---|---|---|---|
| `rule` | ~0 ms | none | Heuristic brightness/contrast; CI-safe baseline |
| `megadetector` | ~3–5 s/frame | PytorchWildlife weights (auto-downloaded) | CPU-only on Pi 4; fine for 10 s cadence |
| `coral` | ~200 ms/frame | Coral USB Accelerator + `libedgetpu` + `pycoral` | See Coral path below |

Start with `rule` for bringup, then switch to `megadetector` once the
pipeline is publishing correctly.

The Galileo does no vision. It cannot run MegaDetector — 400 MHz Quark X1000
single-core + 256 MB RAM are nowhere near the budget.

---

## Pi 4 performance reality

The Pi 4 (ARM Cortex-A72, 4–8 GB RAM, no GPU/NPU) on MegaDetector V6:

- **CPU-only inference: ~3–5 s/frame** — acceptable at the default 10 s
  capture cadence (duty cycle ~30–50%).
- **RAM**: PytorchWildlife loads ~600 MB of weights; 4 GB minimum, 8 GB
  preferred for OS + model headroom.
- **Thermal**: sustained inference drives the SoC above 80 °C and triggers
  throttling. Passive heatsink (standard kit) and optionally a Flirc
  aluminium case (~$15) fix it.

If you need sub-second detection at high cadence, add a **Coral USB
Accelerator**.

---

## Coral USB Accelerator path (optional, ~$60)

Drops MegaDetector inference to **~200 ms/frame** — a 15–25× speedup.

### Purchase

- Amazon ASIN B07S214S5Y (~$60 USD, Prime).
- Mouser Electronics part 2221-G950-06809-01-ND.

### Install on the Pi

```bash
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" \
  | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt update
sudo apt install -y libedgetpu1-std
```

Then in your `skyherd-engine` virtual environment:

```bash
uv pip install pycoral --extra-index-url https://google-coral.github.io/py-packages/
```

Set the mode in `/etc/skyherd/edge.env`:

```ini
EDGE_DETECTOR_MODE=coral
```

> `libedgetpu1-std` runs the TPU at reduced clock (safe for passive cooling).
> Use `libedgetpu1-max` only with active cooling.

---

## Verify both nodes on the bus

On the broker machine:

```bash
mosquitto_sub -v -t 'skyherd/ranch_a/trough_cam/#' \
               -t 'skyherd/ranch_a/water_tank/#' \
               -t 'skyherd/ranch_a/edge_status/#'
```

Within 60 seconds you should see:

- heartbeats from `edge-house` and `edge-tank`,
- `trough_cam.reading` payloads from the Pi,
- `water_tank.reading` payloads from the Galileo.

Expected Pi heartbeat:

```json
{
  "edge_id": "edge-house",
  "ts": 1714000030.0,
  "capture_cadence_s": 10.0,
  "last_detection_ts": 1714000020.0,
  "cpu_temp_c": 52.3,
  "mem_pct": 34.1
}
```

Expected Galileo heartbeat:

```json
{
  "edge_id": "edge-tank",
  "ts": 1714000030.0,
  "kind": "telemetry",
  "sensor_mode": "sim",
  "cpu_temp_c": 46.0,
  "mem_pct": 62.4
}
```

---

## FAQ

**Do the nodes need to talk to each other?**
No. Each node speaks only to the MQTT broker. Agents and the dashboard fan
messages back out.

**Can both nodes share the same `RANCH_ID`?**
Yes — that is the intent. Distinct `EDGE_ID` values route messages to
separate topic subtrees within the same ranch namespace.

**What if the Galileo acts up before the shoot?**
Run `docker compose up edge-tank-sim` on the laptop and carry on. Scenario 3
reads `water_tank` regardless of publisher, so the demo shows the same
tank-drop event. See `docs/HARDWARE_GALILEO.md` § Sim mode.

**What if I only have one Pi and no Galileo?**
Run `edge-house` on the Pi (all six troughs) and use the sim publisher for
tank/weather. Scenarios 3 and 5 still fire on the bus; the dashboard badge
for `edge-tank` reads "sim" instead of "hardware".

**What Raspberry Pi OS version?**
Raspberry Pi OS **Bookworm 64-bit** (Debian 12). Required for `picamera2`
via the `libcamera` stack. Pi 4 4 GB minimum; 8 GB preferred.

**What Galileo Yocto image?**
Intel IoT Devkit `iot-devkit-prof-dev-image-galileo-*.hddimg`. Last build
from Intel is 2017 — still works. See `docs/HARDWARE_GALILEO.md`.

**What PSU for each node?**
Each board needs its own brick:
- **Pi 4**: 5V / 3A USB-C PSU (the official Raspberry Pi one). A phone
  charger will throttle the SoC.
- **Galileo Gen 1**: 5V / 2A DC **barrel jack** adapter — the Intel-branded
  one in the original box. Not USB, not a phone charger. Wrong PSU = random
  reboots.

---

## Friday Morning Sequence (exact 15-minute plug-in)

> **Target state:** Pi + Galileo heartbeats both green on the dashboard
> (`/api/edges`) and a Mavic Air 2 paired via the companion app.
> **Zero code edits** — plug in, run a couple of one-liners, start filming.

### 0. Night-before prep (one-time)

- Laptop: `uv sync --all-extras && (cd web && pnpm install && pnpm run build)`.
- Pi SD card: flash Raspberry Pi OS **Bookworm 64-bit** via Raspberry Pi
  Imager ≥ 1.8.
  - Hostname: `edge-house`.
  - Enable SSH (password or `~/.ssh/id_ed25519.pub`).
  - Wifi SSID + PSK + country = US (the iPhone hotspot).
  - Username: `pi`.
  - On `/boot/firmware/`, copy `hardware/pi/credentials.example.json` →
    rename to `skyherd-credentials.json` → fill in `wifi_ssid`, `wifi_psk`,
    `mqtt_url` (laptop IP), `edge_id` (`edge-house`), `trough_ids`
    (`trough_1,trough_2,trough_3,trough_4,trough_5,trough_6`).
- Galileo Gen 1 microSD: flash the Yocto IoT Devkit image via Raspberry Pi
  Imager (or `dd`). On first boot, drop
  `hardware/galileo/credentials.example.json` filled in as
  `/boot/skyherd-galileo-credentials.json`. Full steps in
  [`docs/HARDWARE_GALILEO.md`](HARDWARE_GALILEO.md) § First-boot network config.
  Use the **Intel 5V / 2A barrel-jack adapter** — not a USB phone charger.

### 1. Bring up the Pi (3 min)

```bash
make edge-pi-setup EDGE_ID=edge-house
```

Or manual:

```bash
ssh pi@edge-house.local
curl -sSfL https://raw.githubusercontent.com/george11642/skyherd-engine/main/hardware/pi/bootstrap.sh | bash
```

### 2. Bring up the Galileo (3 min, parallel with step 1)

Plug the USB-Ethernet adapter into the laptop, enable ICS in Windows,
connect the Cat5 cable to the Galileo, power on.

```bash
# From the laptop, once eth0 DHCPs
ssh root@192.168.137.xxx
bash /media/mmcblk0p1/bootstrap.sh
```

Full steps: [`docs/HARDWARE_GALILEO.md`](HARDWARE_GALILEO.md) § SkyHerd MQTT
publisher.

### 3. Launch dashboard (1 min)

```bash
make dashboard     # http://localhost:8000
```

### 4. Verify both heartbeats green (1 min)

```bash
curl -s http://localhost:8000/api/edges | jq '.edges[] | {edge_id, online, last_seen_ts}'
# Expect edge-house + edge-tank with online:true within 60s of bootstrap finish.
```

Or from any machine on the LAN:

```bash
mosquitto_sub -h <laptop-ip> -v -t 'skyherd/ranch_a/edge_status/#'
```

### 5. Pair Mavic Air 2 via companion app (4 min)

- Android: install the SkyHerdCompanion APK from the GitHub Actions
  artifact. URL in [`docs/HARDWARE_H3_RUNBOOK.md`](HARDWARE_H3_RUNBOOK.md)
  § Companion App APK Download.
- Power on DJI RC → pair with Mavic Air 2 (standard DJI procedure).
- Open SkyHerdCompanion → enter laptop MQTT URL → confirm both badges green:
  **DJI: connected** and **MQTT: connected**.

### 6. End-to-end smoke test (3 min)

Publish a mock coyote event to verify the full dispatch chain:

```bash
mosquitto_pub -h <laptop-ip> \
    -t 'skyherd/ranch_a/events/camera.motion' \
    -m '{"ranch":"ranch_a","edge_id":"edge-house","kind":"camera.motion","confidence":0.9,"label":"coyote","ts":1714000000}'
```

Watch the dashboard for:
1. **FenceLineDispatcher** lane flashes orange within 2 s.
2. Agent log row: `launch_drone(FENCE_SW, deterrent)`.
3. Attestation panel appends a new HashChip row.

**Total wall time: ~15 min.** Anything exceeding 2× expected → check
`docs/PREFLIGHT_CHECKLIST.md` § Troubleshooting.

---

## Idempotency Audit (Phase 9 PF-01, 2026-04-24; re-run 2026-04-24)

Both bootstraps were audited Friday morning for zero-config re-runnability.

| Check | Pi | Galileo | Notes |
|---|---|---|---|
| `bash -n` syntax on bootstrap | PASS | PASS | — |
| Re-running `bootstrap.sh --dry-run` twice produces identical stdout | PASS | PASS | `diff /tmp/br1.txt /tmp/br2.txt` clean |
| All `apt-get` / `opkg` invocations non-interactive | PASS | PASS | Pi uses `-y`; Galileo uses `--force-overwrite` where needed |
| No interactive `read`/`prompt`/`confirm` in Friday-path scripts | PASS | PASS | — |
| `credentials.example.json` parses as valid JSON | PASS | PASS | `jq .` clean |
| Wifi fallback only fires on Pi when no default route | PASS | N/A | Galileo is Ethernet-only |
| `provision-edge.sh` / `skyherd-galileo.service` re-enable safe | PASS | PASS | `systemctl enable` is idempotent |

**Verdict: Friday plug-in requires zero code edits.** The only user inputs
are the values filled into `skyherd-credentials.json` (Pi) and
`skyherd-galileo-credentials.json` (Galileo) before flashing.

---

## Companion App APK URL

See [`docs/HARDWARE_H3_RUNBOOK.md`](HARDWARE_H3_RUNBOOK.md) § Companion App
APK Download for the exact URL + manual-build fallback. Emergency local build:

```bash
cd android/SkyHerdCompanion
./gradlew assembleDebug
# Output: app/build/outputs/apk/debug/app-debug.apk
```

Install via `adb install app-debug.apk` or sideload via USB.
