# HARDWARE_H4_RUNBOOK — DIY LoRa GPS Cattle Collar + ChirpStack Bridge

**Phase:** 8 · **Last updated:** 2026-04-23
**Scope:** From a blank RAK3172 module to a live dashboard pin that moves
with a real cow, via a DIY LoRaWAN collar, a ChirpStack v4 instance, and
the SkyHerd ChirpStack bridge. **Software path only** — this runbook
exists so the Friday hardware-integration day can succeed without
writing new code.

Time estimate: ~90 min (hardware assembly already done) or ~4 h from a
pile of parts. Skills required: basic soldering, PlatformIO, Docker.

---

## 1. Prerequisites

### Hardware

- Assembled collar per [`hardware/collar/BOM.md`](../hardware/collar/BOM.md)
  and [`hardware/collar/wiring.md`](../hardware/collar/wiring.md).
- Working 915 MHz LoRaWAN gateway within ~3 km line-of-sight of the
  pasture. RAK7289 or Mikrotik wAP LR8 recommended; Raspberry Pi + RAK2245
  HAT acceptable. See `BOM.md` "Alternatives if primary parts unavailable".
- USB-C cable from laptop → collar for initial flashing.
- A charged 2500 mAh LiPo.

### Software / accounts

- Laptop with PlatformIO Core on PATH — `pip install platformio` (or
  `pipx install platformio`).
- Docker + docker-compose (for ChirpStack v4 container stack).
- Python 3.11+ + `uv sync` already run in this repo.
- A Mosquitto broker reachable — `make bus-up` from repo root starts one
  on `localhost:1883`.

### Environment

```bash
export MQTT_URL=mqtt://localhost:1883
export CHIRPSTACK_HOST=localhost
export CHIRPSTACK_APP_ID=skyherd-ranch-a    # set per ranch
export SKYHERD_COLLAR_REGISTRY=$PWD/runtime/collars/registry.json
```

---

## 2. Step 1 — Assemble the collar

Follow `hardware/collar/README.md` and the wiring diagram at
`hardware/collar/wiring.md`. High-level:

1. Solder RAK3172 module onto the carrier PCB (or proto-board).
2. Wire MAX-M10S GPS to UART1 (PA9/PA10), GPS VCC through 2N7000 gate
   driven by PA2 (enables power-gating).
3. Wire MPU-6050 to I²C (PB6/PB7), pull-ups on the breakout.
4. Wire battery voltage divider (100 kΩ / 47 kΩ) to PA0.
5. TP4056 charger inline between LiPo and the 3V3 LDO input.
6. Mount in PETG enclosure with silicone gasket; thread through the
   nylon cattle strap.

---

## 3. Step 2 — Flash the firmware

From the repo root, with the collar in **DFU bootloader mode** (hold
BOOT0, tap RESET, release BOOT0):

```bash
./hardware/collar/flash.sh --monitor
```

On first run the script will copy `firmware/include/secrets.h.example`
to `secrets.h` and abort with exit code 2 — edit the file, paste in your
DevEUI / AppEUI / AppKey from the ChirpStack device page (Step 4), then
re-run.

If `pio` is not on PATH the script exits 2 with install hints. See
`hardware/collar/flash.sh --help` for all flags (`--env heltec` switches
to the ESP32 alt target).

**Expected serial output** (on success, once joined):

```
[SkyHerd] collar firmware v1.1 booting
[GPS] UART ready at 9600
[IMU] MPU-6050 OK at 0x68
[LoRa] starting OTAA join...
[LoRa] join successful
[loop] wake -- acquiring GPS fix
[GPS] fix acquired in 42315ms -- sats=9 hdop=1.1
[payload] lat=34.0523401 lon=-106.5342812 alt=1540m act=1 bat=87% fix_age=0s
[LoRa] uplink sent -- sleeping 900 s
```

---

## 4. Step 3 — Launch ChirpStack v4

From a scratch directory (NOT inside this repo):

```bash
git clone https://github.com/chirpstack/chirpstack-docker
cd chirpstack-docker
docker compose up -d
```

This brings up ChirpStack v4 + PostgreSQL + Redis + MQTT bridge on
`localhost:8080`. See [Appendix A](#appendix-a--chirpstack-docker-compose-snippet)
for the minimum self-contained compose snippet if you prefer not to
clone upstream.

Open `http://localhost:8080` (default credentials: `admin / admin` —
change them immediately).

---

## 5. Step 4 — Create tenant, application, device profile

In the ChirpStack web UI:

1. **Tenants → Add** → name `skyherd`.
2. **Device Profiles → Add** → name `skyherd-collar-v1`:
   - Region: `us915_0` (or your region; see BOM regulatory note).
   - MAC version: 1.0.4.
   - Expected uplink interval: 900 s.
   - Allow roaming: no (single-gateway deployment).
3. **Applications → Add** → name `skyherd-ranch-a`, select the tenant
   and device profile.
4. **Integrations → MQTT → Enable** (this is the default in v4 —
   verify it's green).
5. **Devices → Add** inside the application:
   - DevEUI: generate or paste from the RAK3172 label (16 hex chars).
   - Name: e.g. `collar-A001`.
   - Keys: paste the AppKey into the device detail panel (32 hex chars).
6. Copy DevEUI, AppEUI (a.k.a. JoinEUI), AppKey into
   `hardware/collar/firmware/include/secrets.h` then re-flash
   (Step 2 with `--no-warn` to skip the prompt).

**Screenshots** for each of these sub-steps live in
`docs/HARDWARE_H4_SCREENSHOTS/` (TBD — add during recording).

---

## 6. Step 5 — Register the collar in SkyHerd

Map the ChirpStack DevEUI to a ranch + cow tag so the bridge knows
where to publish:

```bash
python hardware/collar/provisioning/register-collar.py \
    --dev-eui A8610A3453210A00 \
    --ranch ranch_a \
    --cow-tag A001
```

This appends to `runtime/collars/registry.json`, which is the file the
bridge reads. Example content:

```json
{
  "A8610A3453210A00": {"ranch": "ranch_a", "cow_tag": "A001"},
  "A8610A3453210A01": {"ranch": "ranch_a", "cow_tag": "A002"}
}
```

The example file under version control is
`runtime/collars/registry.example.json` — copy it as a starting point
if your runtime dir is empty.

---

## 7. Step 6 — Start the ChirpStack bridge

Run in a terminal (keep it open):

```bash
python -m skyherd.edge.chirpstack_bridge \
    --chirpstack-host localhost --chirpstack-port 1883 \
    --app-id skyherd-ranch-a \
    --mqtt-host localhost --mqtt-port 1883
```

For persistent deployment, drop a systemd unit at
`/etc/systemd/system/skyherd-chirpstack-bridge.service`:

```ini
[Unit]
Description=SkyHerd ChirpStack → MQTT bridge
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/skyherd
Environment=SKYHERD_COLLAR_REGISTRY=/opt/skyherd/runtime/collars/registry.json
ExecStart=/opt/skyherd/.venv/bin/python -m skyherd.edge.chirpstack_bridge
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Then `systemctl enable --now skyherd-chirpstack-bridge`.

---

## 8. Step 7 — Verify on dashboard

With `make dashboard` running, open `http://localhost:8000`. Within one
uplink interval (~15 min default, settable per device) the
`collar-A001` pin turns **green** and follows the cow in real time.

**Shortcut for bring-up:** send a LoRaWAN downlink on Port 1 with a
single byte `60` (decimal) to drop the cadence to 60 seconds — much
faster feedback during field debugging. ChirpStack UI → device → Queue
→ Add downlink → port 1, hex `3C`.

---

## 9. Troubleshooting

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| Serial shows no `join successful` | AppEUI / AppKey / region mismatch | Verify each against ChirpStack device page; rebuild with correct region flag |
| Uplink visible in ChirpStack but bridge is silent | MQTT integration disabled or wrong `app_id` | Check ChirpStack → Application → Integrations → MQTT; verify `--app-id` on bridge matches |
| Bridge publishes but dashboard pin stays red | Unknown DevEUI — `registry.json` miss | Run `register-collar.py` with the right DevEUI + cow tag; bridge reloads within 5 s |
| Battery drains in < 24 h | `GPS_PWR_PIN` not wired OR `BATSAVE_MULTIPLIER` inactive | Verify PA2 → 2N7000 gate; check serial for `[batsave]` lines when battery < 15 % |
| Collar disappears from map | `fix_age_s` > 3600 → stale-fix filter | Power-cycle collar; check GPS antenna + sky view; on repeat, bump filter in `src/skyherd/agents/herd_health_watcher.py` |

If no `[SkyHerd]` serial chatter at all, it's almost always one of:
wrong baud (115 200 on the USB-to-serial), BOOT0 not held during reset,
or a brown-out during upload (try a beefier USB cable / supply).

---

## 10. Runbook test (no hardware required)

A fully-mocked version of the pipeline — sim collar → 16-byte encode →
ChirpStack JSON wrap → bridge → MQTT publish — runs in CI:

```bash
make h4-smoke
```

If this target is green, the bridge + decode + registry chain is
healthy. Hardware-only failures (OTAA, physical radio coverage,
downlink acceptance) are the remaining known-unknowns once real
hardware arrives.

---

## Appendix A — ChirpStack docker-compose snippet

Drop this as `docker-compose.chirpstack.yml` anywhere outside this repo,
then `docker compose -f docker-compose.chirpstack.yml up -d`:

```yaml
# Minimum ChirpStack v4 stack — see github.com/chirpstack/chirpstack-docker
# for the full production example with redis persistence, TLS, etc.
services:
  chirpstack:
    image: chirpstack/chirpstack:4
    command: -c /etc/chirpstack
    restart: unless-stopped
    volumes:
      - ./configuration/chirpstack:/etc/chirpstack
      - ./lorawan-devices:/opt/lorawan-devices
    depends_on:
      - postgres
      - redis
      - mosquitto
    ports:
      - "8080:8080"
    environment:
      MQTT_BROKER_HOST: mosquitto
      POSTGRESQL_HOST: postgres
      REDIS_HOST: redis

  chirpstack-gateway-bridge:
    image: chirpstack/chirpstack-gateway-bridge:4
    restart: unless-stopped
    ports:
      - "1700:1700/udp"
    volumes:
      - ./configuration/chirpstack-gateway-bridge:/etc/chirpstack-gateway-bridge
    depends_on:
      - mosquitto

  postgres:
    image: postgres:14-alpine
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: chirpstack
      POSTGRES_USER: chirpstack
      POSTGRES_DB: chirpstack
    volumes:
      - postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data

  mosquitto:
    image: eclipse-mosquitto:2
    restart: unless-stopped
    ports:
      - "1883:1883"
    volumes:
      - ./configuration/mosquitto/config/:/mosquitto/config/

volumes:
  postgres-data:
  redis-data:
```

Upstream maintains the full config tree at
[`chirpstack/chirpstack-docker`](https://github.com/chirpstack/chirpstack-docker)
— recommended over this trimmed version for long-running deployments.

---

## Appendix B — Known deferred items

The following are intentionally out-of-scope for Phase 8 and require
real-hardware validation before landing:

- **LoRaWAN FUOTA OTA** (RFC-draft multicast fragment transport).
  Firmware has a sign-post block in `main.cpp` under `#ifdef OTA_ENABLED`.
  Unblocks after a real RAK3172 + gateway are on the bench.
- **BLE DFU fallback** (RAK RUI3 bootloader / ESP32 `esp_ota_*`).
  Demo-quality only — requires phone/laptop within 10 m.
- **Geofence-driven uplink cadence** — drop interval to 60 s when a cow
  is near a known fence breach-point, raise to 1 h in deep pasture.
- **MQTT integration real-broker integration test** — this runbook's
  Step 5–7 chain exercised against a live Mosquitto + ChirpStack in CI.
  Needs a Docker-in-CI setup that Phase 6's H2 hardware-demo stack
  already uses; port remains on `deferred-features.md`.
- **Multi-region antenna stocking** — EU868 / AS923 variants. Not
  cross-border legal; add to BOM as ranch-specific when deploying
  outside the US.

---

_See also: [`hardware/collar/BOM.md`](../hardware/collar/BOM.md),
[`hardware/collar/wiring.md`](../hardware/collar/wiring.md),
[`hardware/collar/README.md`](../hardware/collar/README.md),
[`docs/HARDWARE_COLLAR.md`](HARDWARE_COLLAR.md),
[`docs/HARDWARE_H3_RUNBOOK.md`](HARDWARE_H3_RUNBOOK.md)._
