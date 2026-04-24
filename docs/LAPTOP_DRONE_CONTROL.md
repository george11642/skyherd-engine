# LAPTOP_DRONE_CONTROL — fly the Mavic from a laptop (no Mac, no phone)

**Phase 7.1 · 2026-04-25**
**Audience:** George running Friday's field test on an Ubuntu 24.04 laptop
with a DJI Mavic Air 2 and its RC controller. No Mac needed. No phone
needed. One USB-C cable + one terminal.

---

## TL;DR — Friday morning

```bash
# 1) Power on the Mavic + RC. Pair per the DJI quick-start card.
# 2) Plug USB-C (data cable) from laptop → RC controller (not the drone body).
# 3) Set the manual-override token (any random string, matches dashboard).
export SKYHERD_MANUAL_OVERRIDE_TOKEN="$(openssl rand -hex 16)"

# 4) Launch the laptop-primary live dashboard.
DRONE_BACKEND=mavic_direct uv run python -m skyherd.server.live \
    --port 8000 --host 127.0.0.1 --seed 42

# 5) Open http://localhost:8000/?drone=1 in a browser.
# 6) In the browser console, paste the token so the panel can send it:
#      window.__DRONE_MANUAL_TOKEN = "<paste-token-here>"
# 7) Right-rail → "Laptop Drone" tab → hold ARM 3s → hold TAKEOFF 3s → LAND.
```

If you want to verify the wiring without a drone: `make laptop-drone-smoke`
runs 14 mocked end-to-end tests in under 10 s.

---

## Why laptop-as-controller

Phase 7 shipped iOS and Android companion apps, but:

- George has no Mac, so iOS TestFlight is out.
- Android works but installing an unsigned APK on the DJI-required phone
  adds a failure point on a tight filming schedule.
- The demo is already deterministic on the laptop — adding a phone in the
  loop is gratuitous complexity.

The **MAVSDK-over-USB-C** leg of `MavicAdapter` already exists and is
tested at the wire level (`src/skyherd/drone/pymavlink_backend.py`). All
we need is a cable, a panel, and one env var. That's this doc.

---

## Cable spec

- **Type:** USB-C to USB-C, **data-capable** (not charge-only).
- **Length:** 1–2 m is ideal; longer cables can drop link on Linux kernels
  with low default `usb-serial` buffer sizes.
- **Known-good example:** Anker PowerLine III USB-C 3.1 Gen 2 (the 10 Gbps
  model; the 480 Mbps version also works but has less margin).

**Charge-only cables look identical.** If `dmesg | tail` shows no device
enumeration when you plug in, swap cables before doing anything else.

Optional fallback: USB-C-to-USB-A adapter + USB-A cable. Adds one point
of failure; use only if no direct USB-C cable is handy.

---

## Which port

Plug into the **USB-C on the RC controller**, not the aircraft directly.
The RC is the MAVLink endpoint; the aircraft's USB-C (behind the
propellers) is for firmware flashing only.

```
   [ Laptop ]                          [ DJI RC ]                [ Mavic Air 2 ]
       |                                   ^                            ^
       | USB-C ─────(data cable)──────────▶                             │
       |                                   └───── 2.4/5.8 GHz radio ───▶│
```

---

## Linux (Ubuntu 24.04) — primary path

### 1. Install udev rules

Create `/etc/udev/rules.d/99-skyherd-drone.rules`:

```
# SkyHerd — MAVLink USB-serial devices for laptop-as-controller.
# Covers DJI RC (2ca3), 3DR Pixhawk / Cube Black (26ac), STM32-based FCs (0483).
SUBSYSTEM=="tty", ATTRS{idVendor}=="2ca3", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="tty", ATTRS{idVendor}=="26ac", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0483", MODE="0666", GROUP="plugdev"

# Generic MAVLink USB-serial fallback (CP210x, FTDI, CH340 adapters).
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666", GROUP="plugdev"
```

Reload + trigger without rebooting:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Add yourself to `plugdev`:

```bash
sudo usermod -aG plugdev $USER
newgrp plugdev          # or log out/in
```

### 2. Install MAVSDK/pymavlink

Already in `pyproject.toml` (`mavsdk>=3,<4`, `pymavlink`). If a fresh
clone:

```bash
uv sync --all-extras
```

The `mavsdk` wheel bundles its own `mavsdk_server` — no apt install is
needed.

### 3. Verify the plug

```bash
lsusb | grep -iE 'dji|pixhawk|3d robotics|stm|silicon labs'
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

Expected: one line per plugged device, and a `/dev/ttyACM0` (or similar)
that you can `cat` without `sudo` (thanks to the udev rule above).

### 4. Smoke-test without flying

```bash
make laptop-drone-smoke
```

14 tests, ~10 s, no network, no drone. Proves the HTTP surface plus the
MAVLink ARM + TAKEOFF command path.

---

## WSL2 — secondary, manual verify Friday

If you're stuck on Windows, WSL2 can reach the RC via `usbipd-win`. This
has NOT been validated in the sandbox — treat it as a Friday-morning
manual verify, not a proven path.

On the Windows host (PowerShell as admin):

```powershell
winget install --id=dorssel.usbipd-win
usbipd list
# Find the DJI RC row, note its BUSID (e.g. "2-3").
usbipd bind --busid 2-3
usbipd attach --wsl --busid 2-3
```

Inside WSL2:

```bash
dmesg | tail -20       # should show the device enumerate
ls /dev/ttyACM*        # same as bare Linux
```

Rules of thumb if it misbehaves:
- Re-run `usbipd attach` after every WSL shutdown.
- Check Windows USB power-management isn't suspending the RC port.

---

## Windows native

Not recommended. The user runs Ubuntu per `/etc/os-release`. If you must
use Windows, install the DJI RC USB driver from the DJI website, then
`mavsdk` should enumerate the device on `COMx`. Use the WSL2 section above
as the fallback.

---

## Troubleshooting

### No device detected

```bash
# verify: does the kernel see it?
lsusb | grep -iE 'dji|pixhawk'
dmesg | tail -20

# fix:
# 1) Try the other end of the cable (USB-C plugs are reversible but some
#    ports are picky).
# 2) Swap to a known-good data cable.
# 3) Reboot the RC (hold power for 5 s).
```

### Permission denied on /dev/ttyACM0

```bash
# verify:
ls -l /dev/ttyACM0            # should be crw-rw---- root plugdev
groups | grep plugdev         # should include plugdev

# fix:
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG plugdev $USER && newgrp plugdev
```

### Heartbeat timeout on connect

```bash
# verify: is the RC actually forwarding MAVLink?
sudo cat /dev/ttyACM0          # garbled bytes every ~1 s = heartbeat OK
```

If no heartbeat:
1. Confirm the RC is paired to the Mavic (solid LEDs, not blinking).
2. Power-cycle the RC. DJI RC firmware sometimes wedges the USB ACM
   endpoint after a firmware update.
3. Try a fresh port; the Mavic RC occasionally boots without MAVLink
   bridge enabled and needs a cold start.

### Manual override returns 401 or 503

- 401 = missing `X-Manual-Override-Token` header. Paste the token into
  the dashboard console: `window.__DRONE_MANUAL_TOKEN = "…"`.
- 503 = `SKYHERD_MANUAL_OVERRIDE_TOKEN` unset on the server. Export it
  before `python -m skyherd.server.live`.
- 503 "no drone backend attached" = the server was started without
  `DRONE_BACKEND=mavic_direct`. Restart the server.

### `make laptop-drone-smoke` fails

```bash
uv run pytest tests/hardware/test_laptop_drone_control.py \
    tests/server/test_drone_control.py -v --no-cov
```

Expected: 14 passed in < 10 s. If a single test fails, read the diff
— most common cause is an interrupted `uv sync` leaving `mavsdk`
half-installed. Re-run `uv sync --all-extras`.

---

## Security notes

- The manual-override endpoints bind to `127.0.0.1` by default.  They
  are **not** exposed to the LAN in the standard `make dashboard` path.
  Double-check with `ss -ltn | grep 8000`.
- The token is a belt-and-suspenders check: even if you accidentally
  bind to 0.0.0.0, no one without the token can ARM the drone.
- Rotate the token between demo sessions: `export
  SKYHERD_MANUAL_OVERRIDE_TOKEN="$(openssl rand -hex 16)"`.
- Never commit `.env.local` — the repo gitignores it, but check with
  `git status` before pushing.

---

## What this replaces

- iOS companion app install (requires a Mac + signed dev cert) — no longer
  needed.
- Android APK sideload + DJI pairing handshake — no longer needed.
- MQTT broker between phone and laptop — no longer needed (direct USB-C
  MAVLink path).

The iOS and Android code stays in the tree (`ios/SkyHerdCompanion`,
`android/SkyHerdCompanion`) as a premium fallback. See
`docs/HARDWARE_H3_RUNBOOK.md` §9 for phone-based control.

---

## Friday morning workflow (copy-paste checklist)

```bash
cd ~/projects/active/skyherd-engine
git status --short
uv sync --all-extras
(cd web && pnpm install --frozen-lockfile && pnpm run build)

# Token (fresh each session)
export SKYHERD_MANUAL_OVERRIDE_TOKEN="$(openssl rand -hex 16)"
echo "TOKEN=$SKYHERD_MANUAL_OVERRIDE_TOKEN"      # copy this

# Plug USB-C into the DJI RC
lsusb | grep -iE 'dji|pixhawk|silicon labs'       # expect one hit
ls /dev/ttyACM* /dev/ttyUSB*                      # expect one tty

# Launch
DRONE_BACKEND=mavic_direct uv run python -m skyherd.server.live \
    --port 8000 --host 127.0.0.1 --seed 42

# Open http://localhost:8000/?drone=1, paste token into console,
# then ARM → TAKEOFF → demo → LAND.
```

Expected wall-clock: cable in pocket → airborne in 3 minutes.

---

## See also

- `src/skyherd/server/drone_control.py` — backend source of truth.
- `src/skyherd/drone/pymavlink_backend.py` — MAVLink wire-level layer.
- `web/src/components/LaptopDroneControl.tsx` — dashboard panel source.
- `docs/HARDWARE_H3_RUNBOOK.md` — full Phase 7 hardware runbook (laptop is §1).
- `docs/PREFLIGHT_CHECKLIST.md` Group 6 — Friday preflight laptop-path items.
