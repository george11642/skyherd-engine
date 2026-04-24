# `hardware/pi/` — One-command Pi 4 bringup

The curl-pipe path from a blank SD card to a live SkyHerd edge node.

## 60-second flow

1. **Flash SD card** — Raspberry Pi OS Bookworm 64-bit Lite via
   [Raspberry Pi Imager](https://www.raspberrypi.com/software/). In the
   advanced options, set hostname, enable SSH, and configure wifi.
2. **Drop credentials.json on `/boot/firmware/`** — copy
   `credentials.example.json`, fill it in, save as `skyherd-credentials.json`
   on the boot partition. (In the imager's advanced-options → Custom file.)
3. **Boot the Pi and run bootstrap:**

   ```bash
   ssh pi@your-pi-hostname
   curl -sSfL https://raw.githubusercontent.com/george11642/skyherd-engine/main/hardware/pi/bootstrap.sh | bash
   ```

   Or, if you already cloned the repo onto the Pi:

   ```bash
   bash /opt/skyherd-engine/hardware/pi/bootstrap.sh
   ```

4. **Watch it come up** on your laptop:

   ```bash
   mosquitto_sub -v -t 'skyherd/ranch_a/#'
   ```

That's it. Within ~30 s of the bootstrap finishing you will see
`edge_status` heartbeats and `trough_cam.reading` events streaming.

## Files

- `bootstrap.sh` — curl-pipe-able one-shot installer. Reads
  `/boot/firmware/skyherd-credentials.json` (or any path passed via
  `SKYHERD_CREDS_FILE`), validates it, delegates to
  `scripts/provision-edge.sh`.
- `credentials.example.json` — annotated credentials template. Copy, fill,
  rename, drop on the SD card. **Never** commit a filled-in copy.

## Dry-run mode

Bootstrap can be tested on a dev machine without affecting anything:

```bash
SKYHERD_CREDS_FILE=tests/hardware/fixtures/creds_good.json \
  bash hardware/pi/bootstrap.sh --dry-run
```

This prints the derived `provision-edge.sh` command it would run, then
exits 0.

## Pointers

- Deep per-unit runbook: [`docs/HARDWARE_PI_EDGE.md`](../../docs/HARDWARE_PI_EDGE.md)
- Two-Pi fleet topology: [`docs/HARDWARE_PI_FLEET.md`](../../docs/HARDWARE_PI_FLEET.md)
- Phase 5 consolidated runbook (judge-facing): [`docs/HARDWARE_H1_RUNBOOK.md`](../../docs/HARDWARE_H1_RUNBOOK.md)
- Demo video tie-in: [`docs/HARDWARE_DEMO_RUNBOOK.md`](../../docs/HARDWARE_DEMO_RUNBOOK.md)
