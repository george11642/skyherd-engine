#!/usr/bin/env bash
# setup-edge-galileo.sh — friendly stub that prints manual flash + bootstrap
# steps for the Intel Galileo Gen 1 `edge-tank` node.
#
# The Galileo flash is a one-time microSD task. We don't automate it yet —
# Raspberry Pi Imager writes the Yocto image fine, and after first boot the
# bootstrap.sh on the microSD does the rest.
#
# Usage:
#   make edge-galileo-setup
#   bash scripts/setup-edge-galileo.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cat <<EOF
=============================================================
  SkyHerd Galileo Gen 1 setup (edge-tank)
=============================================================

The Galileo bringup is a one-time manual flash + first-boot bootstrap.
All files you need live in:

  ${REPO_ROOT}/hardware/galileo/

Step-by-step:

  1. Flash a microSD (>=4 GB) with the Intel IoT Devkit Yocto image.
     Download:   https://iotdk.intel.com/images/
     File:       iot-devkit-prof-dev-image-galileo-*.hddimg (last: 2017-08-18)
     Flash with: Raspberry Pi Imager ("Use custom") or dd.

  2. Copy these onto the FAT32 boot partition of the microSD:

       ${REPO_ROOT}/hardware/galileo/credentials.example.json
            -> rename to skyherd-galileo-credentials.json, fill in values
       ${REPO_ROOT}/hardware/galileo/bootstrap.sh
       ${REPO_ROOT}/hardware/galileo/sensor_publisher.py
       ${REPO_ROOT}/hardware/galileo/skyherd-galileo.service

  3. Power the Galileo with its bundled Intel 5V/2A barrel-jack adapter.
     (NOT a USB phone charger. The Gen 1 does not have USB power input.)
     Connect Ethernet (Windows ICS on 192.168.137.x, or your home router).
     Insert microSD. Boot.

  4. SSH in (root, no password on the stock image):

       ssh root@192.168.137.xxx

  5. Run the bootstrap:

       bash /media/mmcblk0p1/bootstrap.sh

  6. From the laptop, watch edge-tank come up:

       mosquitto_sub -h 192.168.137.1 -v -t 'skyherd/ranch_a/+/edge-tank'

     Expect a heartbeat within 30 s and the first water_tank.reading
     within 60 s.

Full runbook (Gen 1 specifics, wiring, sim mode fallback, troubleshooting):

  ${REPO_ROOT}/docs/HARDWARE_GALILEO.md
  ${REPO_ROOT}/hardware/galileo/README.md

Sim-mode fallback (if the hardware acts up or isn't here yet):

  SENSOR_MODE=sim \\
  MQTT_URL=mqtt://127.0.0.1:1883 \\
  RANCH_ID=ranch_a \\
  EDGE_ID=edge-tank \\
  python3 ${REPO_ROOT}/hardware/galileo/sensor_publisher.py

=============================================================
EOF
