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

---

## Friday Morning Sequence (exact 15-minute plug-in)

> **Target state after this sequence:** two Pi heartbeats green on the
> dashboard (`/api/edges`) and a Mavic Air 2 paired via the companion app.
> **Zero code edits required** — George plugs in, runs three one-liners,
> and starts filming.

### 0. Night-before prep (one-time, does not count against 15-min budget)

- Laptop: `uv sync --all-extras && (cd web && pnpm install && pnpm run build)`.
- SD cards (2×): flash Raspberry Pi OS **Bookworm 64-bit** via Raspberry Pi
  Imager ≥ 1.8. In Imager **Advanced Options**:
  - Hostname: `edge-house` (SD #1) / `edge-barn` (SD #2).
  - Enable SSH — "Use password authentication" OR paste laptop's `~/.ssh/id_ed25519.pub`.
  - Wifi SSID + PSK + country = US.
  - Username: `pi` (default).
- On each SD card's `/boot/firmware/` partition (mount after flash, before eject):
  copy `hardware/pi/credentials.example.json` → rename to `skyherd-credentials.json`
  → edit `wifi_ssid`, `wifi_psk`, `mqtt_url` (point at laptop IP), `edge_id`
  (`edge-house` or `edge-barn`), `trough_ids` (per naming table above).

### 1. Plug in Pi-A (ranch-house side) — 3 min

```bash
# From laptop — Pi-A is powered on and joined wifi via Imager advanced options:
ssh pi@edge-house.local     # first login — no password if SSH key was added
# On the Pi:
curl -sSfL https://raw.githubusercontent.com/george11642/skyherd-engine/main/hardware/pi/bootstrap.sh | bash
```

The script is idempotent — see `## Idempotency Audit` below. Expected output:
~15 s of apt-install log, then "Provisioning complete" and the first heartbeat
within another 15–30 s.

### 2. Plug in Pi-B (barn side) — 3 min (run in parallel with step 1)

```bash
ssh pi@edge-barn.local
curl -sSfL https://raw.githubusercontent.com/george11642/skyherd-engine/main/hardware/pi/bootstrap.sh | bash
```

### 3. Launch dashboard on laptop — 1 min

```bash
make dashboard     # http://localhost:8000
```

### 4. Verify both Pi heartbeats are green — 1 min

```bash
curl -s http://localhost:8000/api/edges | jq '.edges[] | {edge_id, online, last_seen_ts}'
# Expect both edge-house + edge-barn with online:true within 30s of bootstrap finish
```

Alternative, from any machine on the LAN:

```bash
mosquitto_sub -h <laptop-ip> -v -t 'skyherd/ranch_a/edge_status/#'
# Both nodes publish every 30s.
```

### 5. Pair Mavic Air 2 via companion app — 4 min

- On Android phone: install the SkyHerdCompanion APK from the GitHub Actions
  artifact. URL is documented in
  `docs/HARDWARE_H3_RUNBOOK.md` → §Companion App APK Download.
- Power on DJI RC → pair with Mavic Air 2 (standard DJI pairing procedure).
- Open SkyHerdCompanion → enter laptop MQTT URL (matches `mqtt_url` in
  credentials.json) → confirm both badges green:
  - **DJI: connected**
  - **MQTT: connected**

### 6. End-to-end smoke test — 3 min

Publish a mock coyote event on Pi-A's topic from the laptop to confirm the full
dispatch chain fires (drone mission is dispatched to the stub or live Mavic,
Wes voice page triggers, attestation ledger appends):

```bash
mosquitto_pub -h <laptop-ip> \
    -t 'skyherd/ranch_a/events/camera.motion' \
    -m '{"ranch":"ranch_a","edge_id":"edge-house","kind":"camera.motion","confidence":0.9,"label":"coyote","ts":1714000000}'
```

Watch the dashboard (http://localhost:8000) for:
1. **FenceLineDispatcher** lane flashes orange within 2 s.
2. **Agent log** row: `launch_drone(FENCE_SW, deterrent)`.
3. **Attestation panel** appends a new HashChip row.

**Total wall time: ~15 min.** Any step that exceeds 2× expected →
check `docs/PREFLIGHT_CHECKLIST.md` §Troubleshooting.

---

## Idempotency Audit (Phase 9 PF-01, 2026-04-24)

The Pi bootstrap path was re-audited Friday morning for zero-config
re-runnability. Findings:

| Check | Result | Notes |
|---|---|---|
| `bash -n hardware/pi/bootstrap.sh` syntax | PASS | — |
| `bash -n scripts/provision-edge.sh` syntax | PASS | — |
| Re-running `bootstrap.sh --dry-run` twice produces identical stdout | PASS | `diff /tmp/br1.txt /tmp/br2.txt` clean |
| All `apt-get install` invocations use `-y` | PASS | 2 call sites, both `-y` |
| No interactive `read`/`prompt`/`confirm` in Friday-path scripts | PASS | Only `read_text()` in Python (unrelated) |
| `credentials.example.json` parses as valid JSON | PASS | `jq . hardware/pi/credentials.example.json` clean |
| Wifi fallback only fires when no default route | PASS | Guarded by `ip route grep default` |
| `provision-edge.sh` is idempotent (systemd unit re-enable safe) | PASS | `systemctl enable` is idempotent |

**Verdict: Friday plug-in requires zero code edits.** The only user inputs
are the values George fills into `skyherd-credentials.json` on each SD card
before flashing — and those are plain config, not code.

---

## Companion App APK URL

See `docs/HARDWARE_H3_RUNBOOK.md` § Companion App APK Download for the exact
URL + manual-build fallback. In an emergency, the APK can be produced locally:

```bash
cd android/SkyHerdCompanion
./gradlew assembleDebug
# Output: app/build/outputs/apk/debug/app-debug.apk
```

Install via `adb install app-debug.apk` or sideload via USB transfer.
