# HARDWARE_GALILEO.md — Intel Galileo Gen 1 `edge-tank` Runbook

One live environmental-telemetry node on the SkyHerd MQTT bus from an Intel
Galileo Gen 1. No code changes required — flash microSD, drop the credentials
JSON on the boot partition, enable the systemd service. Publishes water-tank
level every 60 s (real sensor or simulated) and weather every 60 s (if a
sensor is wired). Heartbeat every 30 s.

This node replaces the old `edge-barn` Pi in the fleet. See
[`docs/HARDWARE_PI_FLEET.md`](HARDWARE_PI_FLEET.md) for topology and
[`docs/HARDWARE_PI_EDGE.md`](HARDWARE_PI_EDGE.md) for the Pi-side runbook.

---

## What you need

| Item | Notes |
|------|-------|
| Intel Galileo **Gen 1** | This runbook targets Gen 1 specifically |
| Bundled Intel **5V / 2A barrel-jack adapter** | **Not a phone charger** — Gen 1 uses a DC barrel jack, not USB |
| microSD card | ≥4 GB, Class 10 |
| Cat5/6 cable | Short is fine (1–2 m); Ethernet is the only reliable network path |
| USB-Ethernet adapter on the laptop | Only if using the Windows ICS path |
| Laptop with Mosquitto on port 1883 | Windows ICS, home router, or sim path |
| Optional: HC-SR04 ultrasonic sensor | For real water-tank level |
| Optional: DHT22 temp/humidity sensor | For real weather telemetry |

> **PSU warning.** Gen 1 takes a **5V DC barrel-jack adapter at 2 A** (the
> Intel-branded one shipped in the box). A USB phone charger will not fit
> the connector and the board will not boot reliably off under-spec supplies.
> This is the same class of warning as the Pi 4's **5V / 3A USB-C PSU** — use
> the right brick for each board.

---

## Gen 1 reality (budget + limits)

| Constraint | Value | Impact |
|---|---|---|
| CPU | Intel Quark X1000, single-core @ 400 MHz | No threads, no async runtime, no vision |
| RAM | **256 MB DDR3** (hard ceiling) | Python 3 + paho-mqtt is already tight |
| Network | 10/100 Ethernet (RJ45) | No wifi. Period. |
| Power | 5V / 2A barrel jack | Intel-branded adapter only |
| Storage | 8 MB SPI flash onboard; rootfs lives on microSD | Use ≥4 GB card; ≥8 GB gives you headroom |
| Arduino headers | Uno R3-compatible | HC-SR04 on D2/D3 works directly |

At this budget, `sensor_publisher.py` deliberately avoids threads and stays
on the plain paho-mqtt callback loop. One tank read + one MQTT publish every
30 s is the comfortable ceiling. Don't push for faster cadence.

---

## Flashing the Intel IoT Developer Kit Yocto image

Intel's last official image is from 2017. It still works. Download from the
archived repository:

```
https://iotdk.intel.com/images/
```

Pick the latest `iot-devkit-prof-dev-image-galileo-*.hddimg` (around 3.6 GB).
The `prof-dev` variant ships `opkg` + a usable toolchain; the `bare` image
strips too much.

Flash to microSD with **Raspberry Pi Imager** (choose "Use custom") or `dd`:

```bash
# macOS / Linux — replace /dev/sdX with your SD device. DOUBLE-CHECK THIS.
sudo dd if=iot-devkit-prof-dev-image-galileo-20170818.hddimg \
        of=/dev/sdX bs=4M status=progress conv=fsync
sudo sync
```

The Yocto image lays down one FAT32 boot partition + one ext3 root. The
boot partition is where you drop the SkyHerd credentials JSON, the
`sensor_publisher.py`, `bootstrap.sh`, and `skyherd-galileo.service`.

---

## First-boot network config

The Yocto image uses `systemd-networkd`, not NetworkManager. Default DHCP on
`eth0` works out of the box, which is what you want for the Windows ICS path
(ICS acts as the DHCP server at `192.168.137.1`).

If the default doesn't pick up, create
`/etc/systemd/network/10-eth0.network`:

```ini
[Match]
Name=eth0

[Network]
DHCP=yes
```

Then:

```bash
systemctl enable systemd-networkd
systemctl start systemd-networkd
```

Check you got an address:

```bash
ip -4 addr show eth0
# expect: inet 192.168.137.x/24  (ICS) or inet 192.168.1.x/24  (home router)
```

Some Yocto kernels expose the interface as `enp0s20f6` or similar. Replace
`eth0` in the `[Match]` stanza with whatever `ip link` reports.

> **Ethernet-only by design.** Gen 1 has no mPCIe slot and no wifi. A USB
> wifi dongle with a Linux driver will technically work but is out of scope
> for SkyHerd — use Ethernet.

---

## Python and dependencies

The prof-dev Yocto image ships Python 2.7 + `pip`. SkyHerd needs Python 3.

```bash
opkg update
opkg install python3 python3-modules python3-pip python3-paho-mqtt
```

On Gen 1, the `python3-modules` meta-package runs about 60 MB. The
`prof-dev` root has roughly 350 MB free after first boot, which is enough
for the full install — but keep an eye on `df -h /`.

**If opkg runs out of space (happens on 4 GB microSD):** run the publisher
straight from the microSD rather than installing Python 3 globally. The
`bootstrap.sh` script will do this automatically if the opkg install fails —
it will copy `sensor_publisher.py` to `/opt/skyherd-galileo/` (on the same
microSD's rootfs) and the systemd unit will invoke it directly with whatever
Python 3 interpreter it can find.

**RAM pressure warning.** 256 MB leaves very little headroom for Python 3 +
paho-mqtt. `sensor_publisher.py` deliberately:

- avoids threads (Gen 1 is single-core anyway),
- uses the synchronous paho-mqtt callback loop (not the asyncio client),
- reads one sensor value per poll, no buffers.

---

## Wiring a water-level sensor (optional)

Default ships in **sim mode** — sensor readings are synthesised so the demo
still runs without physical wiring. Set `sensor_mode: "real"` in the
credentials JSON when you're ready to wire one up.

### HC-SR04 ultrasonic (water-tank level) — canonical demo wiring

| HC-SR04 pin | Galileo Gen 1 pin |
|---|---|
| VCC | 5V |
| GND | GND |
| TRIG | D2 |
| ECHO | D3 (via voltage divider — 1k/2k to step 5V → ~3.3V) |

Gen 1's Arduino pins are 3.3 V tolerant on input. Stepping the ECHO down
avoids lifetime damage.

### DHT22 temp/humidity (optional)

| DHT22 pin | Galileo Gen 1 pin |
|---|---|
| VCC | 3.3V |
| DATA | D4 (10k pull-up to 3.3V) |
| GND | GND |

### Reading from Python — `mraa`

Intel's `mraa` library is the Arduino-compat layer for Galileo GPIO.
Usually on the prof-dev image; if missing:

```bash
opkg install mraa python3-mraa
```

Minimal read (already stubbed in `hardware/galileo/sensor_publisher.py`):

```python
import mraa
trig = mraa.Gpio(2); trig.dir(mraa.DIR_OUT)
echo = mraa.Gpio(3); echo.dir(mraa.DIR_IN)
# pulse TRIG, time ECHO, divide by 58 for cm — see sensor_publisher.py
```

If you don't have a sensor wired, leave `sensor_mode: "sim"` — the publisher
generates a slow sinusoidal tank-level trace with realistic noise. Fine for
demo recording.

---

## SkyHerd MQTT publisher

The publisher lives at
[`hardware/galileo/sensor_publisher.py`](../hardware/galileo/sensor_publisher.py).

It:
- reads `/etc/skyherd/galileo.env` for MQTT URL, ranch ID, edge ID, mode,
- opens a paho-mqtt client (sync callback API, no threads),
- publishes `edge_status` heartbeat every 30 s on
  `skyherd/{ranch}/edge_status/{edge_id}`,
- publishes `water_tank.reading` every 60 s on
  `skyherd/{ranch}/water_tank/{edge_id}`,
- publishes `weather.reading` every 60 s on
  `skyherd/{ranch}/weather/{edge_id}` when `WEATHER_ENABLED=1`.

Payload schemas match
[`src/skyherd/edge/watcher.py`](../src/skyherd/edge/watcher.py) (heartbeat)
and [`src/skyherd/sensors/water.py`](../src/skyherd/sensors/water.py)
(water tank) so existing agents consume Galileo output identically to the
Pi edge and the sim sensors.

---

## Systemd service

The service file is
[`hardware/galileo/skyherd-galileo.service`](../hardware/galileo/skyherd-galileo.service).
Install:

```bash
cp /media/mmcblk0p1/skyherd-galileo.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now skyherd-galileo
systemctl status skyherd-galileo
```

The service:
- reads environment from `/etc/skyherd/galileo.env`,
- restarts on failure (`Restart=on-failure`, `RestartSec=5`),
- starts after `network-online.target`.

One-shot bootstrap — flashes microSD, drops credentials, enables the service
— lives at
[`hardware/galileo/bootstrap.sh`](../hardware/galileo/bootstrap.sh). Run once
after first boot; idempotent on re-runs.

---

## Verification

On the laptop, subscribe to every `edge-tank` topic:

```bash
mosquitto_sub -h 192.168.137.1 -v -t 'skyherd/ranch_a/+/edge-tank'
```

Within 60 seconds you should see:

```
skyherd/ranch_a/edge_status/edge-tank {"cpu_temp_c":46.0,"edge_id":"edge-tank","kind":"telemetry","mem_pct":62.4,"sensor_mode":"sim","ts":1714000030.0}
skyherd/ranch_a/water_tank/edge-tank {"entity":"edge-tank","kind":"water_tank.reading","level_pct":78.2,"ranch":"ranch_a","source":"galileo","tank_id":"tank_n","ts":1714000060.0}
```

If you see only heartbeats, the sensor loop didn't start — check
`journalctl -u skyherd-galileo -n 50`.

---

## Sim mode

When the Galileo is being uncooperative (or you haven't wired it up yet),
run the same publisher on the laptop with `SENSOR_MODE=sim`:

```bash
SENSOR_MODE=sim \
MQTT_URL=mqtt://127.0.0.1:1883 \
RANCH_ID=ranch_a \
EDGE_ID=edge-tank \
python3 hardware/galileo/sensor_publisher.py
```

Payloads are indistinguishable from the real Galileo on the wire — same
topics, same schema, same cadence. Use this as the video fallback.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Galileo won't boot (no console on serial) | microSD not seated, or wrong image | Re-seat card; re-flash with `prof-dev` image |
| Undervoltage / random reboots | Wrong PSU (USB charger, not the Intel 5V/2A barrel) | Use the bundled Intel adapter |
| `Active: failed` in systemctl | Bad env var or missing Python 3 | `journalctl -u skyherd-galileo -n 50` |
| No IP on `eth0` | Interface named differently under Yocto | `ip link`; update `[Match]` in the `.network` file |
| No MQTT messages on laptop | Broker not bound to ICS IP | `netstat -an \| grep 1883` — confirm `192.168.137.1` listener |
| `opkg install python3` fails "no space left" | 4 GB card full after image lay-down | Use a ≥8 GB card, or run publisher direct off microSD (§ Python and dependencies) |
| `mraa` import error | Not installed | `opkg install python3-mraa` |
| `paho.mqtt` missing | opkg index stale | `opkg update && opkg install python3-paho-mqtt` (fallback: `pip install paho-mqtt`) |
| Clock wrong after reboot | Gen 1 has no RTC battery stock | `timedatectl set-ntp true` and keep it online |

---

## Pointers

- Fleet topology (Pi + Galileo): [`HARDWARE_PI_FLEET.md`](HARDWARE_PI_FLEET.md)
- Pi-side runbook: [`HARDWARE_PI_EDGE.md`](HARDWARE_PI_EDGE.md)
- 60-sec demo runbook: [`HARDWARE_DEMO_RUNBOOK.md`](HARDWARE_DEMO_RUNBOOK.md)
- Galileo directory (scripts, service file, publisher): [`hardware/galileo/`](../hardware/galileo/)
- Architecture (5-layer nervous system): [`ARCHITECTURE.md`](ARCHITECTURE.md)

---

## License

All Galileo scripts and configs are MIT — same as the rest of skyherd-engine.
No AGPL dependencies.
