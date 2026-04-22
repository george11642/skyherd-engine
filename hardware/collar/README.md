# SkyHerd DIY LoRa GPS Cattle Collar — Tier H4

A sub-$55 hardware collar that joins the SkyHerd mesh and publishes GPS+IMU readings on the **exact same MQTT topics** as the simulated collars. From the dashboard's perspective, a real collar is indistinguishable from a sim collar — it just shows a green dot instead of a pink one.

## What it is

The collar pairs a **RAK3172 STM32WL LoRaWAN module** with a **u-blox MAX-M10S GPS** and an **MPU-6050 6-axis IMU** in a 3D-printed PETG shell that bolts onto a standard cattle neck strap. Every 15 minutes (configurable) it wakes from deep sleep, acquires a GPS fix, reads motion data, encodes a 16-byte payload, and fires a LoRaWAN uplink to ChirpStack. A Python decoder on the server side inflates that payload and publishes it to `skyherd/{ranch}/collar/{cow_tag}` — the same topic the sim engine uses.

## How it talks to ChirpStack

OTAA join → ChirpStack HTTP integration webhook → `decode_payload.py` → Mosquitto MQTT → all five Managed Agents. No code changes to agents required.

## BOM cost

~$52 total (see `BOM.md`).

## One-command provisioning

```bash
python hardware/collar/provisioning/register-collar.py \
    --dev-eui A8610A3453210A00 \
    --ranch ranch_a \
    --cow-tag A001
```

This registers the device in ChirpStack, writes it to `runtime/collars/registry.json`, and verifies the MQTT topic route. Five seconds later cow A001 flips from sim-pink to real-green on the dashboard.

## Quick start

```bash
make -C hardware/collar build   # compile firmware
make -C hardware/collar flash   # upload via USB-C DFU
make -C hardware/collar test    # run host-side payload unit tests
make -C hardware/collar shell   # regenerate STL from SCAD
```

Full end-to-end runbook: `docs/HARDWARE_COLLAR.md`.
