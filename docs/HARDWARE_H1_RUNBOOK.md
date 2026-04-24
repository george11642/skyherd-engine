# HARDWARE_H1_RUNBOOK — Pi 4 + PiCamera + cardboard-coyote end-to-end

The one-page **judge-facing** consolidation: from blank SD card to live events
on the dashboard.

> This runbook composes the following existing deep docs:
> - [`HARDWARE_PI_EDGE.md`](HARDWARE_PI_EDGE.md) — per-unit Pi setup
> - [`HARDWARE_PI_FLEET.md`](HARDWARE_PI_FLEET.md) — Pi + Galileo fleet topology
> - [`HARDWARE_GALILEO.md`](HARDWARE_GALILEO.md) — Galileo `edge-tank` runbook
> - [`HARDWARE_DEMO_RUNBOOK.md`](HARDWARE_DEMO_RUNBOOK.md) — 60-sec hero demo
>
> Read this page first; follow pointers for depth.

---

## 60-second version

1. **Flash SD card** — Raspberry Pi OS Bookworm 64-bit Lite via
   [Pi Imager](https://www.raspberrypi.com/software/). Advanced options: set
   hostname (`edge-house`), enable SSH, configure wifi. For the Galileo
   telemetry node (`edge-tank`), see [`HARDWARE_GALILEO.md`](HARDWARE_GALILEO.md).
2. **Drop `skyherd-credentials.json` on the boot partition.** Schema is at
   [`hardware/pi/credentials.example.json`](../hardware/pi/credentials.example.json).
3. **Boot the Pi and run bootstrap:**
   ```bash
   ssh pi@edge-house
   curl -sSfL https://raw.githubusercontent.com/george11642/skyherd-engine/main/hardware/pi/bootstrap.sh | bash
   ```
4. **Watch it come up** on your laptop:
   ```bash
   mosquitto_sub -v -t 'skyherd/ranch_a/#'
   ```

Done. Expected within 30 s: `edge_status` heartbeats + `trough_cam.reading`
events at 10 s cadence.

---

## What Phase 5 ships

| Artefact | Path | Purpose |
| --- | --- | --- |
| **Pi bootstrap** | `hardware/pi/bootstrap.sh` | Curl-pipe one-shot installer. Reads credentials.json, delegates to `scripts/provision-edge.sh`. |
| **Credentials schema** | `hardware/pi/credentials.example.json` | Required fields for Pi bringup. |
| **PiCamSensor** | `src/skyherd/edge/picam_sensor.py` | Pinkeye MobileNetV3-Small pixel classifier sensor; emits `trough_cam.reading`. |
| **CoyoteHarness** | `src/skyherd/edge/coyote_harness.py` | Deterministic thermal clip player; emits `thermal.reading` + `predator.thermal_hit`. |
| **Edge CLI** | `src/skyherd/edge/cli.py` | `skyherd-edge run / smoke / picam / coyote / verify-bootstrap`. |
| **Integration test** | `tests/hardware/test_h1_mqtt_bridge.py` | End-to-end Pi→MQTT→subscriber fabric (no real Pi needed). |

---

## credentials.json schema

Required fields:

```json
{
  "wifi_ssid": "YourWifi",
  "wifi_psk": "YourPassword",
  "mqtt_url": "mqtt://192.168.1.100:1883",
  "ranch_id": "ranch_a",
  "edge_id": "edge-house",
  "trough_ids": "trough_1,trough_2,trough_3,trough_4,trough_5,trough_6"
}
```

Optional sub-object `"_optional"` can set detector mode, cadence, etc. — see
[`credentials.example.json`](../hardware/pi/credentials.example.json).

**Validate before provisioning:**

```bash
uv run skyherd-edge verify-bootstrap \
    --credentials-file /boot/firmware/skyherd-credentials.json
# verify-bootstrap OK — … has all required fields.
```

Exit code 2 lists missing / malformed fields with context.

---

## bootstrap.sh flow

```
bootstrap.sh
    │
    ├── read $SKYHERD_CREDS_FILE (default /boot/firmware/skyherd-credentials.json)
    ├── validate JSON via jq
    ├── extract wifi_ssid/psk, mqtt_url, ranch_id, edge_id, trough_ids
    ├── (if offline) write /etc/wpa_supplicant/wpa_supplicant.conf, bring up wifi
    └── exec scripts/provision-edge.sh <edge_id> <trough_ids>
                └── system apt packages (picamera2, mosquitto-clients, libcamera)
                └── uv install
                └── clone skyherd-engine → /opt/skyherd-engine
                └── uv sync --extra edge
                └── write /etc/skyherd/edge.env
                └── install + start skyherd-edge systemd service
                └── tail journalctl -u skyherd-edge for 15 s
```

Test on a dev machine without touching anything:

```bash
SKYHERD_CREDS_FILE=tests/hardware/fixtures/creds_good.json \
    bash hardware/pi/bootstrap.sh --dry-run
# DRY-RUN: env RANCH_ID=ranch_a MQTT_URL=mqtt://192.168.1.100:1883 \
#           bash /…/scripts/provision-edge.sh edge-house trough_1,trough_2
```

---

## skyherd-edge CLI

```bash
skyherd-edge --help
```

| Subcommand | Purpose | Example |
| --- | --- | --- |
| `run` | Start the production `EdgeWatcher` capture loop (MegaDetector V6 default). | `skyherd-edge run -v` |
| `smoke` | Capture one mock frame + publish in-process; exit 0 if pipeline works. | `skyherd-edge smoke` |
| `picam` | Run `PiCamSensor` with pinkeye pixel classifier on every frame. | `skyherd-edge picam --max-ticks=5 --seed=42` |
| `coyote` | Run `CoyoteHarness` (cardboard-coyote thermal playback). | `skyherd-edge coyote --max-ticks=5 --seed=42 --species=coyote` |
| `verify-bootstrap` | Parse credentials.json, exit 0 if valid. | `skyherd-edge verify-bootstrap -c /boot/firmware/…` |

Every loop subcommand accepts:

- `--ranch-id RANCH_A` — ranch identifier used in MQTT topics.
- `--mqtt-url mqtt://…:1883` — broker URL; defaults to `mqtt://localhost:1883`.
- `--max-ticks N` — exit after N iterations (test mode; omit for long-running service).
- `--seed S` — deterministic frame-ordering seed.
- `-v / --verbose` — enable DEBUG logging.

### `picam` payload (trough_cam.reading schema)

Matches `skyherd.sensors.trough_cam.TroughCamSensor` 1:1, plus extras:

```json
{
  "ts": 1714000000.123,
  "kind": "trough_cam.reading",
  "ranch": "ranch_a",
  "entity": "picam_0",
  "trough_id": "picam_0",
  "cows_present": 1,
  "ids": ["cow_picam_0"],
  "frame_uri": "runtime/picam_frames/picam_0_1714000000.jpg",
  "source": "picam",
  "pinkeye_result": {"severity": "escalate", "confidence": 0.92, "class_idx": 3},
  "seed": 42,
  "tick": 0
}
```

### `coyote` payloads (dual fan-out)

Two topics per tick:

1. `skyherd/ranch_a/thermal/coyote_cam` (thermal.reading)
2. `skyherd/ranch_a/alert/thermal_hit` (predator.thermal_hit)

Both match `ThermalCamSensor` wire format + `cardboard_coyote` source tag.

---

## Integration test (no Pi required)

Runs entirely in-process — no mosquitto, no real hardware.

```bash
uv run pytest tests/hardware/test_h1_mqtt_bridge.py -v
```

Exercises: `PiCamSensor` + `CoyoteHarness` → injected in-memory MQTT → subscriber
receives canonical JSON → schema matches wire format.

Wall-time budget: < 10 s. Use this in CI.

For the full project regression suite (1500+ tests, 26 min):

```bash
uv run pytest --cov=src/skyherd
```

---

## Troubleshooting grid

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `bootstrap.sh: jq: not found` | Clean Pi image — fresh install | Script auto-installs via apt; re-run |
| `verify-bootstrap` exit 2 | Required field missing in credentials.json | Error message lists missing field(s) |
| `picam`: pinkeye model unavailable | Torch/torchvision missing or weights absent | Re-run `uv sync --extra edge` |
| `coyote`: fixture frames missing | `tests/fixtures/thermal_clips/` empty | `uv run python -m tests.fixtures.thermal_clips._generate` |
| `picam`: `Picamera2` instantiation fails | On dev machine `picamera2` absent | **Expected**; CLI falls back to PIL sample loop automatically |
| MQTT publish fails silently | Broker unreachable / wrong URL | All publish paths are best-effort; check mosquitto listening on the configured port |
| `skyherd-edge run` crash-looping | Bad env var in `/etc/skyherd/edge.env` | `journalctl -u skyherd-edge -n 50` |
| Pi CPU temp >80 °C | Sustained MegaDetector inference | Fit heatsink / Flirc case; drop to `rule` mode; see `HARDWARE_PI_EDGE.md` thermal section |

---

## Pointers (deep docs)

| Topic | File |
| --- | --- |
| Full per-Pi bringup walkthrough | [`HARDWARE_PI_EDGE.md`](HARDWARE_PI_EDGE.md) |
| Pi + Galileo fleet topology | [`HARDWARE_PI_FLEET.md`](HARDWARE_PI_FLEET.md) |
| Galileo `edge-tank` runbook | [`HARDWARE_GALILEO.md`](HARDWARE_GALILEO.md) |
| 60-sec demo runbook | [`HARDWARE_DEMO_RUNBOOK.md`](HARDWARE_DEMO_RUNBOOK.md) |
| Architecture (5-layer nervous system) | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Attestation chain (verifies edge events) | [`ATTESTATION.md`](ATTESTATION.md) |

---

## Determinism guarantee

- `CoyoteHarness` with a fixed `ts_provider` is **byte-identical** across replays
  given the same `seed`.
- `PiCamSensor` with `seed=N` produces the same frame-index sequence.
- Nothing in Phase 5 feeds into `make demo SEED=42 SCENARIO=all`; the sim
  scenario determinism gate is preserved unchanged (Phase 4 gate holds).

---

## License

All Phase 5 code and fixtures are MIT (same as the rest of skyherd-engine).
No AGPL dependencies; no proprietary weights.
