# HARDWARE_PI_EDGE.md — Pi H1 Edge Runtime Runbook

One live trough-cam sensor on the SkyHerd MQTT bus from a Raspberry Pi.
No code changes required — install, configure two env vars, enable the service.

---

## What you need

| Item | Notes |
|------|-------|
| Raspberry Pi 4 or 5 | 2 GB+ RAM recommended |
| SD card | 8 GB minimum, 32 GB recommended |
| Raspberry Pi Camera Module | Any CSI camera (v2, HQ, or v3) |
| Network | Pi and laptop/server on same LAN, or VPN |
| Laptop/server | Running `skyherd-engine` with Mosquitto on port 1883 |

---

## Step 1 — Flash SD card

Flash **Raspberry Pi OS Bookworm 64-bit** (Lite or Desktop) using
[Raspberry Pi Imager](https://www.raspberrypi.com/software/).

In the imager's advanced options:
- Set hostname (e.g. `skyherd-pi`)
- Enable SSH
- Set username/password or add your public key

---

## Step 2 — First-boot setup

SSH into the Pi, then:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-picamera2 mosquitto-clients libcamera-apps
```

Verify the camera is detected:

```bash
libcamera-hello --list-cameras
```

You should see at least one camera entry.  If not, enable the camera interface:

```bash
sudo raspi-config   # Interface Options → Camera → Enable
sudo reboot
```

---

## Step 3 — Install uv

```bash
curl -sSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc   # or open a new shell
uv --version       # should print uv x.y.z
```

---

## Step 4 — Clone and install skyherd-engine

```bash
git clone https://github.com/george11642/skyherd-engine
cd skyherd-engine
uv sync --extra edge
```

The `--extra edge` flag installs `picamera2` and `PytorchWildlife` (MegaDetector V6).
On Pi OS, `picamera2` may already be present system-wide — `uv` will use it.

---

## Step 5 — Create the skyherd system user

```bash
sudo useradd --system --shell /bin/false --home-dir /opt/skyherd-engine skyherd
sudo mv ~/skyherd-engine /opt/skyherd-engine
sudo chown -R skyherd:skyherd /opt/skyherd-engine
```

If you prefer to keep it in your home directory, adjust
`WorkingDirectory` in the service file accordingly.

---

## Step 6 — Configure environment

```bash
sudo mkdir -p /etc/skyherd
sudo cp /opt/skyherd-engine/src/skyherd/edge/systemd/edge.env.example /etc/skyherd/edge.env
sudo nano /etc/skyherd/edge.env
```

Minimum required edits:

```ini
RANCH_ID=ranch_a          # must match your skyherd-engine RANCH_ID
MQTT_URL=mqtt://192.168.1.100:1883   # IP of the machine running Mosquitto
```

To find the laptop/server IP:

```bash
# on the laptop/server
ip route get 1 | awk '{print $7; exit}'   # Linux
ipconfig | grep 'IPv4'                     # Windows
```

---

## Step 7 — Install and enable the systemd service

```bash
sudo cp /opt/skyherd-engine/src/skyherd/edge/systemd/skyherd-edge.service \
        /etc/systemd/system/skyherd-edge.service

sudo systemctl daemon-reload
sudo systemctl enable --now skyherd-edge
```

Check it is running:

```bash
systemctl status skyherd-edge
# Should show: Active: active (running)
```

Follow live logs:

```bash
journalctl -u skyherd-edge -f
```

---

## Step 8 — Verify end-to-end

On the **laptop/server** (where skyherd-engine is running):

```bash
mosquitto_sub -v -t 'skyherd/ranch_a/trough_cam/#'
```

Within 10 seconds you should see a JSON line like:

```json
skyherd/ranch_a/trough_cam/skyherd-pi {"cows_present":1,"entity":"skyherd-pi","frame_uri":"runtime/edge_frames/skyherd-pi_1714000000.jpg","ids":["animal"],"kind":"trough_cam.reading","ranch":"ranch_a","source":"edge","trough_id":"skyherd-pi","ts":1714000000.123}
```

The `"kind":"trough_cam.reading"` field confirms the Pi is publishing in the
same wire format as the 500 sim sensors — agents consume both identically.

---

## Smoke test (optional, run on Pi)

```bash
cd /opt/skyherd-engine
uv run skyherd-edge smoke
# smoke ok — 1 mock frame published, 1 detection(s)
```

Exit code 0 confirms the full capture → detect → publish pipeline works
without needing a live broker.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Active: failed` in systemctl | Bad env var or permission | `journalctl -u skyherd-edge -n 50` |
| No MQTT messages on laptop | Wrong `MQTT_URL` IP | Ping Pi from laptop; check firewall |
| `PiCameraUnavailable` in logs | picamera2 missing or no camera | `sudo apt install python3-picamera2`; reboot |
| `MegaDetectorV6 unavailable` | Weights not downloaded | First run downloads automatically (needs internet) |
| Service restarts every 5s | Crash loop | Check logs; confirm `/dev/video0` exists |

---

## Uninstall / reset

```bash
sudo systemctl disable --now skyherd-edge
sudo rm /etc/systemd/system/skyherd-edge.service
sudo rm -rf /etc/skyherd
sudo systemctl daemon-reload
```

---

## Pi 4 performance reality

> This section is specific to the **Raspberry Pi 4** (ARM Cortex-A72).
> It does NOT apply to Pi 5 or to x86 dev machines.

### Raspberry Pi OS recommendation

Flash **Raspberry Pi OS Bookworm 64-bit** (Debian 12) — this is the only
supported target for `--extra edge`.

- Bookworm ships `picamera2` via `libcamera` (apt package `python3-picamera2`).
- Bullseye's `picamera2` is incompatible with the H1 runtime.
- Use the 64-bit variant; 32-bit will hit numpy / PytorchWildlife compat issues.

Minimum specs: **Pi 4 4 GB RAM**. Preferred: **Pi 4 8 GB** for OS + model headroom.

### Detector mode and inference latency

Set `EDGE_DETECTOR_MODE` in `/etc/skyherd/edge.env`:

| Mode | Pi 4 latency | Notes |
|---|---|---|
| `rule` | ~0 ms | Heuristic brightness/contrast. No model. CI-safe baseline. |
| `megadetector` | ~3–5 s/frame | CPU-only MegaDetector V6. Fine at 10 s cadence (~30–50% duty). |
| `coral` | ~200 ms/frame | Coral USB Accelerator (Edge TPU). See below. |

Start with `rule` for bringup, switch to `megadetector` once the pipeline
is verified end-to-end. The 10-second capture cadence leaves 5–7 s of idle
headroom between frames even at the slowest CPU inference.

> **If you need sub-second throughput**: add a Coral USB Accelerator.
> Purchase: Amazon ASIN B07S214S5Y or Mouser 2221-G950-06809-01-ND (~$60 USD).
> Install: `sudo apt install libedgetpu1-std` + `uv pip install pycoral`.
> Set: `EDGE_DETECTOR_MODE=coral` in edge.env.
> The Edge TPU reduces inference from ~3–5 s to ~200 ms — a 15–25× speedup.

### Thermal management

The Pi 4 SoC **throttles above ~80 °C**, reducing clock speed and inference
throughput. Under sustained MegaDetector load outdoors this is reachable.

Recommended mitigations (inexpensive):
1. **Passive heatsink kit** — included in most Pi 4 starter kits. Drops idle
   temp by 10–15 °C.
2. **Flirc aluminium case** (~$15 USD) — turns the entire enclosure into a
   heatsink. Effective for sustained inference without active cooling.
3. **Monitor via heartbeat**: the `cpu_temp_c` field in the `edge_status`
   heartbeat reads `/sys/class/thermal/thermal_zone0/temp` every 30 s.
   Alert at 75 °C; investigate at 80 °C.

### Two-Pi fleet

George has **two Pi 4 units** — see `docs/HARDWARE_PI_FLEET.md` for the
naming convention (`edge-house` + `edge-barn`), per-Pi config files, MQTT
fleet topology, failover behaviour, and the one-command provisioning script.
