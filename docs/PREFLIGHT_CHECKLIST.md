# PREFLIGHT_CHECKLIST — Friday Morning Hardware Plug-In

**Phase 9 deliverable · PF-03 · 2026-04-24**
**Phase 7.1 update · 2026-04-25** — laptop path now primary.

20-item checklist George runs Friday morning before filming. Each item has:

- **Action** — the thing to do.
- **`verify:`** — the exact command/observation.
- **`expect:`** — the expected output or pattern.

Target total time: **< 30 minutes, coffee to first heartbeat green**.

> **Laptop is the primary controller path as of 2026-04-25.** See
> `docs/LAPTOP_DRONE_CONTROL.md`. Phone-based control (iOS / Android) is
> still documented but is no longer required for Friday's demo —
> relegated to Group 3 (optional).

> Pair with: `docs/HARDWARE_PI_FLEET.md` §Friday Morning Sequence for the
> 15-minute operational flow. This checklist is the pre-flight safety pass
> that happens **before** that sequence.

---

## Group 1 — Laptop readiness (5 items)

### 1. Repo is on the correct branch and clean

- [ ] Action: confirm repo is on `main` and has no unstaged critical changes.
- `verify:` `git rev-parse --abbrev-ref HEAD && git status --short`
- `expect:` `main` and empty (or only expected local drafts).

### 2. Python deps installed

- [ ] Action: `uv sync --all-extras`.
- `verify:` `uv run python -c "import skyherd; print(skyherd.__file__)"`
- `expect:` prints path under `src/skyherd/__init__.py`.

### 3. Web dashboard build artifacts exist

- [ ] Action: `(cd web && pnpm install --frozen-lockfile && pnpm run build)`.
- `verify:` `test -f web/dist/index.html && echo OK`
- `expect:` `OK`.

### 4. Mosquitto reachable on the LAN

- [ ] Action: start mosquitto if not running — `make bus-up` (or use system broker).
- `verify:` `mosquitto_pub -h localhost -t 'skyherd/preflight' -m ping; mosquitto_sub -h localhost -t 'skyherd/preflight' -C 1 -W 2`
- `expect:` `ping` echoed within 2 s.

### 5. Dashboard boots at :8000

- [ ] Action: `make dashboard` in a spare terminal tab (leave running).
- `verify:` `curl -fsS http://localhost:8000/api/health | jq .status`
- `expect:` `"ok"` (or `"healthy"`, whichever the server emits).

---

## Group 2 — Edge-node readiness (5 items)

> Fleet = 1× Pi 4 (`edge-house`, all six trough cameras) + 1× Intel Galileo
> Gen 1 (`edge-tank`, water-tank + weather telemetry). Galileo is on the
> Windows ICS subnet `192.168.137.x`; Pi is on the iPhone-hotspot wifi at
> `172.20.10.x`. `edge-barn` Pi naming is still accepted by the scripts
> for the legacy two-Pi split.

### 6. Both edge nodes reachable

- [ ] Action: Pi on wifi, Galileo on ICS Ethernet, both pingable from the laptop.
- `verify:` `ssh -o BatchMode=yes pi@edge-house.local 'hostname' && ssh -o BatchMode=yes root@192.168.137.20 'hostname'`
- `expect:` `edge-house` and `edge-tank` (substitute the Galileo's actual ICS IP — `arp -a` or `ip neigh` on the laptop).

### 7. Credentials files present on each node

- [ ] Action: confirm `skyherd-credentials.json` was dropped in `/boot/firmware/` on the Pi, and `skyherd-galileo-credentials.json` on the Galileo boot partition.
- `verify:` `ssh pi@edge-house.local 'sudo jq .edge_id /boot/firmware/skyherd-credentials.json'` and `ssh root@192.168.137.20 'python3 -c "import json; print(json.load(open(\"/boot/skyherd-galileo-credentials.json\"))[\"edge_id\"])"'`
- `expect:` `"edge-house"` and `edge-tank`.

### 8. Bootstrap completes without errors on the Pi

- [ ] Action: run bootstrap over SSH pipe from laptop.
- `verify:` `ssh pi@edge-house.local 'curl -sSfL https://raw.githubusercontent.com/george11642/skyherd-engine/main/hardware/pi/bootstrap.sh | bash' 2>&1 | tail -5`
- `expect:` output ending in `Provisioning complete` or the first `edge_status` heartbeat JSON line. Galileo equivalent: `bash /media/mmcblk0p1/bootstrap.sh` on-device (see `docs/HARDWARE_GALILEO.md`).

### 9. systemd units active on both nodes

- [ ] Action: query each service.
- `verify:` `ssh pi@edge-house.local 'systemctl is-active skyherd-edge' && ssh root@192.168.137.20 'systemctl is-active skyherd-galileo'`
- `expect:` `active` on both.

### 10. `/api/edges` reports both nodes online

- [ ] Action: query the dashboard API.
- `verify:` `curl -s http://localhost:8000/api/edges | jq '.edges | map({edge_id, online})'`
- `expect:` array containing `edge-house` and `edge-tank` with `online: true` within 90 s of bootstrap finish.

---

## Group 3 — Mavic readiness (optional phone-based path)

> **Skip this entire group unless you're using the phone companion app.**
> The laptop-primary path in Group 6 replaces items 12 and 13. Item 11
> (RC + Mavic power + pair) is still required regardless of controller
> choice. Item 14 (SITL smoke) is still useful as a standalone sanity check.

### 11. DJI RC + Mavic Air 2 powered + paired

- [ ] Action: power on RC → power on Mavic → confirm pairing handshake.
- `verify:` RC screen shows **Aircraft Connected** and battery > 50%.
- `expect:` both green. If red, swap battery or re-pair per DJI RC manual.

### 12. Companion APK installed on phone *(optional — skip unless using phone)*

- [ ] Action: download APK from URL in `docs/HARDWARE_H3_RUNBOOK.md` §Companion App APK Download, sideload.
- `verify:` Android → Settings → Apps → SkyHerdCompanion version string matches CI run.
- `expect:` version present, opens without crash.

### 13. App reports DJI + MQTT both green *(optional — skip unless using phone)*

- [ ] Action: open app, enter MQTT URL (matches laptop), connect Mavic.
- `verify:` two badges top-right of the app screen.
- `expect:` **DJI: connected** + **MQTT: connected** — both green.

### 14. SITL test takeoff passes offline

- [ ] Action: optional sanity check — `make sitl-smoke`.
- `verify:` exit code 0 in < 60 s.
- `expect:` `PASS` line in the test output; means the MAVLink stack is valid
  even if the real Mavic is unavailable.

---

## Group 6 — Laptop Drone Control path (primary · 2026-04-25 · Phase 7.1)

> **This is the default path for Friday.** See
> `docs/LAPTOP_DRONE_CONTROL.md` for the full procedure and cable spec.
> If all three items below are green, you can skip Group 3 items 12–13.

### 21. USB-C data cable plugged RC → laptop

- [ ] Action: plug the data-capable USB-C cable from the laptop into the
  **DJI RC controller's USB-C port** (not the aircraft).
- `verify:` `dmesg | tail -20` immediately after plugging.
- `expect:` a line like `cdc_acm ...: ttyACM0: USB ACM device` or similar
  USB-serial enumeration. If silent → swap the cable; many USB-C cables are
  charge-only.

### 22. Kernel sees the DJI RC and /dev/ttyACM* is readable

- [ ] Action: confirm device enumeration + permissions.
- `verify:` `lsusb | grep -iE 'dji|pixhawk|silicon labs' && ls -l /dev/ttyACM*`
- `expect:` one `lsusb` hit + a `/dev/ttyACM*` file owned by `root:plugdev`
  mode `crw-rw----`. If permission denied: `sudo udevadm control --reload-rules && sudo udevadm trigger` (requires the udev rules from `docs/LAPTOP_DRONE_CONTROL.md` §Linux §1).

### 23. Laptop-drone smoke + dashboard ready

- [ ] Action: run the mocked end-to-end smoke and verify the manual
  override token is in the environment.
- `verify:` `make laptop-drone-smoke && test -n "$SKYHERD_MANUAL_OVERRIDE_TOKEN" && echo OK`
- `expect:` 14 tests passed in < 10 s, then `OK`. If the token is unset:
  `export SKYHERD_MANUAL_OVERRIDE_TOKEN="$(openssl rand -hex 16)"` — paste
  the value into the dashboard console as `window.__DRONE_MANUAL_TOKEN`.

---

## Group 4 — Determinism (3 items)

### 15. `make demo SEED=42 SCENARIO=all` runs clean

- [ ] Action: one-shot demo, time it.
- `verify:` `time make demo SEED=42 SCENARIO=all`
- `expect:` exit code 0 in < 3 min; 5 scenarios emit expected events.

### 16. Attestation chain writes signed events

- [ ] Action: verify the ledger appended during the demo.
- `verify:` `uv run skyherd-attest verify`
- `expect:` `chain=valid sigs=N ...` with N > 0 and the tail pointing to the
  latest signed event.

### 17. 3× replay is hash-stable

- [ ] Action: run the determinism test or three manual demos.
- `verify:` `make determinism-3x` (requires slow-marker opt-in) OR three
  consecutive `make demo SEED=42 SCENARIO=all` runs diffed after sanitization.
- `expect:` identical hashes across all three runs.

---

## Group 5 — Demo content (3 items)

### 18. Wes voice takes pre-rendered

- [ ] Action: run `bash docs/demo-assets/audio/render.sh` with `ELEVENLABS_API_KEY` set.
- `verify:` `ls docs/demo-assets/audio/*.wav | wc -l`
- `expect:` ≥ 5 wav files (one per urgency + per scenario). If absent,
  fallback is mock voice — the demo still runs, just less hero-voice.

### 19. Cardboard coyote + plush cow + Bluetooth speaker on set

- [ ] Action: verify physical props per `docs/HARDWARE_DEMO_RUNBOOK.md` §Props.
- `verify:` visual count.
- `expect:` coyote cutout, plush cow + red wet-erase marker, Bluetooth speaker
  charged. Skip-safe: sim-first script in `docs/DEMO_VIDEO_SCRIPT.md` doesn't
  require physical props.

### 20. `make record-ready` launches dashboard cleanly

- [ ] Action: final one-liner preflight.
- `verify:` `make record-ready` in a spare terminal.
- `expect:` prints `READY TO RECORD`, launches dashboard on :8000, silent
  otherwise (no red warnings).

---

## Troubleshooting (run into a red step? start here)

### Pi heartbeat not arriving after 90 s

```bash
ssh pi@edge-house.local 'sudo journalctl -u skyherd-edge -n 50 --no-pager'
```

Common causes:
- MQTT URL typo in `skyherd-credentials.json` — re-edit + reboot.
- Wifi dropped — `ip route | grep default` on the Pi; if empty, re-run bootstrap (idempotent).
- systemd unit failed — `sudo systemctl status skyherd-edge`; restart with `sudo systemctl restart skyherd-edge`.

### Dashboard shows "edge offline" red dot

- Confirm `/api/edges last_seen_ts` is recent (< 90 s).
- Restart `skyherd-edge` on the offline Pi.
- Confirm laptop is on the same subnet (no VPN).

### Mavic won't pair

- Re-seat the battery on both RC and aircraft.
- Try DJI Fly app first; if that pairs, the issue is the companion APK (rebuild with fresh DJI SDK key).
- Fallback: run demo with `DRONE_BACKEND=stub` — sim takeoff still produces the dashboard event chain.

### Coyote scenario doesn't dispatch on `mosquitto_pub`

- Subscribe first: `mosquitto_sub -v -t 'skyherd/ranch_a/#'` in a second terminal.
- Confirm the payload `kind` matches `camera.motion` exactly.
- Confirm `SKYHERD_AGENTS=local` (or your chosen mesh backend) in the dashboard env.

### Determinism fails (hash mismatch)

- Almost always a wall-clock leak — check `src/skyherd/attest/*` sanitization.
- Rebuild web dist (`pnpm run build`) — stale JS can introduce timestamp ordering
  differences in SSE replay.
- Re-run with `SEED=43`; if THAT hashes stable, confirm seed propagation.

### APK install rejected

- Enable "Install unknown apps" for your browser/file-manager app on Android.
- Verify APK integrity: `shasum -a 256 skyherd-companion-android-apk.apk`.
- Fallback: local build per `docs/HARDWARE_PI_FLEET.md` §Companion App APK URL.

---

## Exit criteria

Green checklist = ready to film. If any group ends with a non-green item that
isn't covered by the troubleshooting section, escalate to the **sim-first
fallback path** in `docs/DEMO_VIDEO_SCRIPT.md` — the video can ship without
hardware by running `make record-ready` and recording the dashboard
deterministically.
