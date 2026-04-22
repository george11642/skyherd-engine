# SkyHerd Hardware Demo Runbook

**Audience**: George (PIC), Gavin (puppeteer/observer), Josh (camera operator)
**Goal**: 60-second on-camera demo showing the SkyHerd nervous system with real Pi hardware and real Mavic drone

---

## Props (total < $25 if not on hand)

| Prop | Purpose | Cost |
|------|---------|------|
| Cardboard coyote cutout | Trigger Pi #1 MegaDetector | $3 at FedEx OR free from `docs/demo-assets/coyote-silhouette.svg` — fold from cardboard in 10 min |
| Fishing line + stick (30cm) | Gavin pulls cutout through frame off-screen | free |
| 1× stuffed plush cow / rubber cow toy | Sick-cow Shot B | ~$5 at Dollar Tree |
| Red wet-erase marker | Draw ocular discharge on plush cow left eye; wipe off after take | ~$2 |
| 1× Bluetooth speaker (JBL Go 4 or Sony SRS-XB100) | Deterrent audio near drone landing zone | ~$15 |

**Coyote cutout**: Print `docs/demo-assets/coyote-silhouette.svg` at 100% on 8.5"×11" paper at FedEx ($3), cut out, tape to cardboard backing. Alternatively, trace onto cardboard freehand.

---

## Pre-Shoot Checklist (morning of)

- [ ] Laptop charged + USB-C adapter in bag
- [ ] `uv sync --all-extras` done on laptop
- [ ] `make dashboard` smoke-tested: `http://localhost:8000` shows ranch map
- [ ] Pi #1 (`edge-fence`): plugged in at fence location, heartbeat green on `/api/edges`
- [ ] Pi #2 (`edge-barn`): plugged in at trough/milk-crate stand, heartbeat green
- [ ] Mavic Air 2: 3× fully charged batteries, pre-flight checklist done
- [ ] DJI Remote: charged, linked to Mavic
- [ ] Phone (Android/iOS): SkyHerdCompanion open, "DJI: connected" + "MQTT: connected" both green
- [ ] Wind check: `windy.com` — must be < 21 kt; reschedule if over
- [ ] Filming area: closed private property confirmed, no overflight of non-participants

---

## Laptop: One Command

```bash
ANTHROPIC_API_KEY=$KEY \
DRONE_BACKEND=mavic \
HARDWARE_OVERRIDES=trough_cam:trough_1:edge-fence,trough_cam:trough_2:edge-barn \
make hardware-demo
```

Dashboard auto-launches at `http://localhost:8000`. Open on George's second monitor — livestream this panel in the video. The terminal shows live event/tool-call log.

---

## Pi Side (commissioned ahead)

Each Pi already runs `skyherd-edge` via systemd (see `docs/HARDWARE_PI_FLEET.md`).

Quick verify before shoot:
```bash
curl http://<laptop-ip>:8000/api/edges
# Should show edge-fence and edge-barn both with status: green
```

If a Pi shows red: `ssh pi@edge-fence sudo systemctl restart skyherd-edge` and wait 15s.

---

## iPhone / Android Side

1. Open SkyHerdCompanion.
2. Confirm green badge: **DJI: connected** + **MQTT: connected**.
3. Keep phone in shot or on a stand beside George — Wes voice call or app phone-ring animation will appear here. This is the "rancher in the loop" moment.

---

## Shot List

### Shot A — Coyote Hero (35–45 sec)

**Setup**: Pi #1 camera on fence post, framing the gap. Gavin off-screen with fishing-line-on-stick attached to coyote cutout. George stands near laptop/dashboard, facing camera.

**Action**:
1. George: *"It's 7:42 pm on the south range."* — glances at dashboard showing 50 cows grazing.
2. Gavin pulls cardboard coyote through frame slowly (2–3 seconds across).
3. Pi #1 MegaDetector fires → MQTT event hits laptop → FenceLineDispatcher wakes → dashboard shows agent log: "Coyote detected, dispatching drone."
4. Mavic lifts off automatically (or George shows liftoff on phone screen).
5. Drone flies 20m to fence line position, plays deterrent tone through Bluetooth speaker.
6. George's phone rings — Wes voice: *"Boss. Coyote at the south fence. Drone's on it."*
7. Dashboard: "Cleared. Logged. Attestation signed." — show attestation panel briefly.
8. George: *"That's the whole loop — detection to drone to rancher, under 30 seconds."*

**Cut**: tight on dashboard showing the event chain + attestation hash.

### Shot B — Sick Cow (20 sec)

**Setup**: Pi #2 on milk crate or fence rail at trough height. Plush cow with red wet-erase "discharge" on left eye in frame.

**Action**:
1. Camera on plush cow + Pi #2 lens.
2. HerdHealthWatcher fires — dashboard: "A014 — pinkeye flag, severity: escalate."
3. Dashboard draws vet-intake packet: animal ID, symptoms, GPS location, recommended vet visit window.
4. Wes voice (lower urgency): *"Boss. A014's got something in her left eye. I pulled together a vet packet; take a look when you can."*
5. George wipes red marker off: *"No vet bill for a false alarm. Every flag is logged and signed."*

### Shot C — Split-Screen Sim (15 sec)

**Setup**: Dashboard full-screen on monitor.

**Action**: Show the 3 background sim scenarios (water drop, calving, storm) running in parallel with live cost ticker. Narration: *"Behind that one coyote call, three more agents are running — water tanks, calving watch, storm routing — all on the same mesh, 24/7."*

---

## Safety

**Part 107 rules (George is PIC):**
- Visual line of sight (VLOS) at all times
- Altitude < 400 ft AGL
- Daylight operations only
- No overflight of non-participants
- Mavic Air 2 Remote ID: built-in, compliant

**Pre-flight**:
- Wind < 21 kt (Mavic Air 2 ceiling)
- Full battery on all 3 packs
- Check `windy.com` morning-of
- GPS lock before arming (minimum 8 satellites)
- One observer (Josh), one PIC (George), one puppeteer (Gavin)

**Aborts**: If GPS lock fails or battery < 30% → do not take off. Use SITL path (dashboard still shows drone animation). Narration shifts: *"Drone sim while we reset — same reasoning engine, same attestation chain."*

---

## Fallback Plan

| Failure | Response |
|---------|---------|
| Mavic won't arm (GPS, battery) | Dashboard shows SITL drone; narration shifts to "sim while we reset" |
| Pi #1 doesn't detect coyote within 180s | `skyherd-demo-hw` auto-triggers sim coyote scenario; narration: "Same reasoning, from sim — here's what just played on the real Pi half a second too late." |
| Pi heartbeat red | `ssh pi@edge-fence sudo systemctl restart skyherd-edge` — 15s fix |
| Twilio call fails | Dashboard phone-ring animation plays + .wav written to `runtime/hardware_demo_runs/` |
| Laptop API key missing | All 5 agents run sim path — still shows full tool-call cascade |

---

## What This Demo Proves

1. **Pi-to-cloud MQTT**: Real cow/predator detection from a $75 camera lands on the same MQTT topic that 500 sim cows use — no special path.
2. **Agent → tool → drone**: Real MAVLink-via-DJI takeoff from a Managed Agent tool call. The agent doesn't know if it's talking to hardware or SITL.
3. **Rancher-in-the-loop**: Wes voice reaches a real phone. George gets a call, not an email.
4. **Attestation**: Every event from the above — signed, timestamped, on the live ledger visible in the dashboard. Replay any moment for an insurance claim.
5. **Scale**: While hardware drives the hero scenario, 3 more agents run sim scenarios in the background. One command, one mesh, any number of ranches.
