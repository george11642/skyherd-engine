# `hardware/galileo/` — One-command Galileo bringup

Intel Galileo (Gen 1 or Gen 2) as the SkyHerd `edge-tank` telemetry node.
Water-tank level (Scenario 3) + optional weather telemetry (Scenario 5).
No vision — this is the environmental half of the two-node edge fleet.

## One-command path (recommended)

From the laptop, once the Galileo is flashed + booted + reachable over SSH:

```bash
make edge-galileo-setup
```

`scripts/setup-edge-galileo.sh` currently prints the manual flash + bootstrap
steps in a friendly format (the Galileo flash is a one-time microSD task; no
automated flasher yet, Pi Imager writes the image fine).

## Manual flash + bootstrap

1. **Flash microSD (≥4 GB)** — Intel IoT Developer Kit Yocto image. Grab the
   latest `iot-devkit-prof-dev-image-galileo-*.hddimg` from
   https://iotdk.intel.com/images/ and flash via Raspberry Pi Imager (choose
   "Use custom") or `dd`:
   ```bash
   sudo dd if=iot-devkit-prof-dev-image-galileo-20170818.hddimg \
           of=/dev/sdX bs=4M status=progress conv=fsync && sync
   ```

2. **Drop credentials on the FAT32 boot partition.** Copy
   `credentials.example.json`, fill in, save as
   `/boot/skyherd-galileo-credentials.json` on the microSD. Also copy
   `bootstrap.sh` and `sensor_publisher.py` + `skyherd-galileo.service` to
   `/boot/` so they are accessible after first boot.

3. **First boot.** Plug USB-Ethernet adapter + Cat5 into the laptop (Windows
   ICS path) or attach the Galileo to the home router. Insert microSD, power
   the Galileo with its 5V/2A PSU. Give it about 60 s.

4. **Run bootstrap over SSH.**
   ```bash
   # IP comes from Windows ICS (usually 192.168.137.x) or your router.
   ssh root@192.168.137.xxx
   bash /media/mmcblk0p1/bootstrap.sh
   ```

5. **Watch it come up on the laptop.**
   ```bash
   mosquitto_sub -h 192.168.137.1 -v -t 'skyherd/ranch_a/+/edge-tank'
   ```

Within 60 s you should see `edge_status` heartbeats and `water_tank.reading`
payloads.

## Files

- `bootstrap.sh` — idempotent one-shot installer. Reads
  `/boot/skyherd-galileo-credentials.json`, installs Python 3 + paho-mqtt via
  opkg, writes `/etc/skyherd/galileo.env`, installs and enables the systemd
  unit.
- `credentials.example.json` — annotated template. Fill, rename, drop on the
  boot partition. **Never** commit a filled-in copy.
- `sensor_publisher.py` — the publisher itself. Small, pure Python 3
  (+ paho-mqtt). Runs on the Galileo via systemd; also runnable on a laptop in
  `SENSOR_MODE=sim` as the demo fallback.
- `skyherd-galileo.service` — systemd unit. `Restart=on-failure`, reads env
  from `/etc/skyherd/galileo.env`, starts after `network-online.target`.

## Dry-run mode

Bootstrap can be tested on a dev machine without touching anything:

```bash
SKYHERD_CREDS_FILE=hardware/galileo/credentials.example.json \
    bash hardware/galileo/bootstrap.sh --dry-run
```

Prints the derived `opkg` / `systemctl` commands and exits 0.

## Sim mode on the laptop

If the Galileo is uncooperative (or you haven't flashed it yet), run the
publisher on the laptop — payloads on the wire are identical to the real
Galileo:

```bash
SENSOR_MODE=sim \
MQTT_URL=mqtt://127.0.0.1:1883 \
RANCH_ID=ranch_a \
EDGE_ID=edge-tank \
python3 hardware/galileo/sensor_publisher.py
```

The dashboard badge will read `sim` instead of `hardware` — everything else
stays the same.

## Pointers

- Galileo runbook (Gen 1 + Gen 2): [`../../docs/HARDWARE_GALILEO.md`](../../docs/HARDWARE_GALILEO.md)
- Pi + Galileo fleet topology: [`../../docs/HARDWARE_PI_FLEET.md`](../../docs/HARDWARE_PI_FLEET.md)
- Demo video tie-in: [`../../docs/HARDWARE_DEMO_RUNBOOK.md`](../../docs/HARDWARE_DEMO_RUNBOOK.md)
