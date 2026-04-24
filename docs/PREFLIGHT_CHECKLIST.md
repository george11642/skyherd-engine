# PREFLIGHT_CHECKLIST — Friday Morning Hardware Plug-In

**Phase 9 deliverable · PF-03 · 2026-04-24**

20-item checklist George runs Friday morning before filming. Each item has:

- **Action** — the thing to do.
- **`verify:`** — the exact command/observation.
- **`expect:`** — the expected output or pattern.

Target total time: **< 30 minutes, coffee to first heartbeat green**.

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

## Group 2 — Pi readiness (5 items)

### 6. Both Pis reachable via SSH

- [ ] Action: Pi-A + Pi-B are on LAN and SSH works key-free.
- `verify:` `ssh -o BatchMode=yes pi@edge-house.local 'hostname' && ssh -o BatchMode=yes pi@edge-barn.local 'hostname'`
- `expect:` `edge-house` and `edge-barn`.

### 7. Credentials file present on each Pi

- [ ] Action: confirm `skyherd-credentials.json` was dropped in `/boot/firmware/` during flash.
- `verify:` `ssh pi@edge-house.local 'sudo jq .edge_id /boot/firmware/skyherd-credentials.json'`
- `expect:` `"edge-house"` — and same check on edge-barn returns `"edge-barn"`.

### 8. Bootstrap completes without errors on Pi-A

- [ ] Action: run bootstrap over SSH pipe from laptop.
- `verify:` `ssh pi@edge-house.local 'curl -sSfL https://raw.githubusercontent.com/george11642/skyherd-engine/main/hardware/pi/bootstrap.sh | bash' 2>&1 | tail -5`
- `expect:` output ending in `Provisioning complete` or the first `edge_status` heartbeat JSON line.

### 9. systemd unit active on both Pis

- [ ] Action: query the service.
- `verify:` `ssh pi@edge-house.local 'systemctl is-active skyherd-edge' && ssh pi@edge-barn.local 'systemctl is-active skyherd-edge'`
- `expect:` `active` on both.

### 10. `/api/edges` reports both nodes online

- [ ] Action: query the dashboard API.
- `verify:` `curl -s http://localhost:8000/api/edges | jq '.edges | map({edge_id, online})'`
- `expect:` array containing both `edge-house` and `edge-barn` with `online: true` within 90 s of bootstrap finish.

---

## Group 3 — Mavic readiness (4 items)

### 11. DJI RC + Mavic Air 2 powered + paired

- [ ] Action: power on RC → power on Mavic → confirm pairing handshake.
- `verify:` RC screen shows **Aircraft Connected** and battery > 50%.
- `expect:` both green. If red, swap battery or re-pair per DJI RC manual.

### 12. Companion APK installed on phone

- [ ] Action: download APK from URL in `docs/HARDWARE_H3_RUNBOOK.md` §Companion App APK Download, sideload.
- `verify:` Android → Settings → Apps → SkyHerdCompanion version string matches CI run.
- `expect:` version present, opens without crash.

### 13. App reports DJI + MQTT both green

- [ ] Action: open app, enter MQTT URL (matches laptop), connect Mavic.
- `verify:` two badges top-right of the app screen.
- `expect:` **DJI: connected** + **MQTT: connected** — both green.

### 14. SITL test takeoff passes offline

- [ ] Action: optional sanity check — `make sitl-smoke`.
- `verify:` exit code 0 in < 60 s.
- `expect:` `PASS` line in the test output; means the MAVLink stack is valid
  even if the real Mavic is unavailable.

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
