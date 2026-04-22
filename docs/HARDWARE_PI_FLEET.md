# HARDWARE_PI_FLEET.md — Two-Pi-4 Fleet Commissioning Guide

George has **two Raspberry Pi 4 units** (Pi 4, not Pi 5).
This document walks through naming, per-unit configuration, MQTT fleet topology,
failover behaviour, and the one-command provisioning flow.

Read `docs/HARDWARE_PI_EDGE.md` first for the single-Pi H1 runbook.
This document is purely additive — the base runbook still applies to each unit.

---

## Fleet topology at a glance

```
ranch LAN
├── edge-house Pi (ranch-house side)   EDGE_ID=edge-house
│     troughs: trough_1, trough_2
│     topic:   skyherd/ranch_a/trough_cam/edge-house
│     status:  skyherd/ranch_a/edge_status/edge-house   (heartbeat every 30 s)
│
└── edge-barn Pi (barn side)           EDGE_ID=edge-barn
      troughs: trough_3, trough_4, trough_5, trough_6
      topic:   skyherd/ranch_a/trough_cam/edge-barn
      status:  skyherd/ranch_a/edge_status/edge-barn    (heartbeat every 30 s)

Both Pis publish to the same Mosquitto broker (laptop / server).
No direct peer-to-peer networking between the Pis is required.
Agents subscribe to skyherd/ranch_a/trough_cam/# and consume both nodes identically.
```

---

## Naming convention

| Unit | Hostname | `EDGE_ID` | Troughs |
|------|----------|-----------|---------|
| Pi #1 — ranch house | `edge-house` | `edge-house` | `trough_1`, `trough_2` |
| Pi #2 — barn | `edge-barn` | `edge-barn` | `trough_3`, `trough_4`, `trough_5`, `trough_6` |

Hostnames are set at flash time via Raspberry Pi Imager advanced options.
`EDGE_ID` is set in `/etc/skyherd/edge.env` on each Pi (or injected by `provision-edge.sh`).
Both values can be overridden freely — they only need to be unique per ranch.

---

## One-command provisioning (from your laptop)

Run once per Pi, substituting hostname and trough list:

```bash
# Pi #1 — ranch house
ssh pi@edge-house 'bash -s' < scripts/provision-edge.sh edge-house "trough_1,trough_2"

# Pi #2 — barn
ssh pi@edge-barn 'bash -s' < scripts/provision-edge.sh edge-barn "trough_3,trough_4,trough_5,trough_6"
```

The script:
1. Installs system deps (`python3-picamera2`, `mosquitto-clients`, etc.).
2. Installs `uv`.
3. Clones `skyherd-engine` into `/opt/skyherd-engine`.
4. Runs `uv sync --extra edge`.
5. Writes `/etc/skyherd/edge.env` with the supplied `EDGE_ID` + `EDGE_TROUGH_IDS`.
6. Installs and starts the `skyherd-edge` systemd unit.
7. Tails `journalctl` for 15 s so you see the first heartbeat.

Config examples live at:
- `src/skyherd/edge/configs/edge-house.env.example`
- `src/skyherd/edge/configs/edge-barn.env.example`

---

## MQTT topics per node

Each Pi publishes to its own subtree under the ranch prefix.

| Message type | Topic pattern | Published by |
|---|---|---|
| Trough-cam reading | `skyherd/{ranch}/trough_cam/{edge_id}` | every N seconds |
| Camera motion event | `skyherd/{ranch}/events/camera.motion` | when confidence ≥ 0.5 |
| Heartbeat / status | `skyherd/{ranch}/edge_status/{edge_id}` | every 30 s |

Subscribe to ALL nodes at once:

```bash
mosquitto_sub -v -t 'skyherd/ranch_a/#'
```

Subscribe only to status heartbeats (both nodes):

```bash
mosquitto_sub -v -t 'skyherd/ranch_a/edge_status/#'
```

---

## Dashboard visibility

Both Pis appear as distinct edge nodes on the SkyHerd dashboard (green heartbeat
indicator) once they are publishing `edge_status` heartbeats.

The `/api/edges` endpoint (follow-up task — not yet implemented) should:
- Aggregate `edge_status` payloads from MQTT.
- Return a list of `{ edge_id, last_seen_ts, cpu_temp_c, mem_pct, online: bool }`.
- Mark a node `online: false` if `now - last_seen_ts > 90` seconds.

This is a follow-up task for the dashboard-agent; do NOT implement while
`src/skyherd/server/app.py` is being actively modified.

---

## Failover behaviour

If one Pi goes dark:

1. Its `edge_status` heartbeat stops arriving.
2. After **90 seconds** without a heartbeat, the ranch agents should flag an
   `edge.offline` event on the MQTT bus:
   ```json
   {"kind":"edge.offline","edge_id":"edge-barn","last_seen_ts":1714000000,"ranch":"ranch_a"}
   ```
3. Agents adapt their inference cadence — they switch to sim-sensor fallback for
   the affected trough IDs rather than treating silence as "no animals present".

The 90-second window is intentionally conservative to avoid false-alerts on brief
Wi-Fi hiccups. Adjust via `EDGE_OFFLINE_THRESHOLD_S` in the agent environment.

---

## Detector mode per Pi

Set `EDGE_DETECTOR_MODE` in `/etc/skyherd/edge.env`:

| Mode | Latency (Pi 4) | Requirement | Notes |
|---|---|---|---|
| `rule` | ~0 ms | none | Heuristic brightness/contrast; CI-safe baseline |
| `megadetector` | ~3–5 s/frame | PytorchWildlife weights (auto-downloaded) | CPU-only on Pi 4; fine for 10 s cadence |
| `coral` | ~200 ms/frame | Coral USB Accelerator + `libedgetpu` + `pycoral` | See Coral path below |

Start with `rule` for bringup, then switch to `megadetector` once you confirm
the pipeline is publishing correctly.

---

## Pi-4 performance reality

The Pi 4 (ARM Cortex-A72, 4–8 GB RAM, no GPU/NPU) has the following measured
characteristics for MegaDetector V6:

- **CPU-only inference: ~3–5 seconds per frame** — acceptable at the default
  10-second capture cadence (duty cycle ~30–50%).
- **RAM**: PytorchWildlife loads ~600 MB of weights; Pi 4 4 GB is the minimum;
  8 GB preferred for OS + model headroom.
- **Thermal**: prolonged inference drives the SoC above 80°C, triggering CPU
  throttling. Fit a passive heatsink (included in most Pi 4 kits) and optionally
  a Flirc aluminium case (~$15) for sustained outdoor deployments.

If you need sub-second detection at high cadence, add a **Coral USB Accelerator**.

---

## Coral USB Accelerator path (optional, ~$60)

The Coral USB Accelerator (Google Edge TPU) drops MegaDetector inference to
**~200 ms per frame** — a 15–25× speedup over CPU-only Pi 4.

### Purchase

- Amazon ASIN B07S214S5Y (~$60 USD, ships Prime).
- Mouser Electronics part 2221-G950-06809-01-ND.

### Install on Pi

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

> Note: `libedgetpu1-std` runs the TPU at reduced clock (safe for passive
> cooling). Use `libedgetpu1-max` only with active cooling.

---

## Verify both nodes on the bus

On the broker machine, subscribe to all edge topics:

```bash
mosquitto_sub -v -t 'skyherd/ranch_a/trough_cam/#' -t 'skyherd/ranch_a/edge_status/#'
```

Within 30 seconds you should see heartbeat JSON from both `edge-house` and
`edge-barn`, and trough-cam readings at the configured capture interval.

Expected heartbeat shape:

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

---

## FAQ

**Do the two Pis need to talk to each other?**
No. Each Pi speaks only to the MQTT broker. The broker fans messages out to
all subscribers (agents, dashboard). No Pi-to-Pi networking required.

**Can both Pis share the same `RANCH_ID`?**
Yes — that is the intent. Different `EDGE_ID` values route their messages to
distinct topic subtrees within the same ranch namespace.

**What if I only have one Pi available for the demo?**
Run both `edge-house` and `edge-barn` on the same Pi with different `EDGE_ID`
values and camera indices. The MQTT topology is identical; agents can't tell the
difference.

**What Raspberry Pi OS version?**
Raspberry Pi OS **Bookworm 64-bit** (Debian 12). This is required for
`picamera2` via the `libcamera` stack. Bullseye is not supported for `--extra edge`.
Pi 4 4 GB minimum; 8 GB preferred.
