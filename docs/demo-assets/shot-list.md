# SkyHerd Hardware Demo — Day-of Shot List

**Crew**: George (PIC + presenter), Gavin (puppeteer + observer), Josh (camera operator)
**Location**: Closed private property, clear sight lines, < 400 ft AGL flight zone

---

## Pre-Roll Checklist (30 min before camera rolls)

- [ ] Wind < 21 kt (`windy.com`)
- [ ] Pi #1 heartbeat green: `curl http://localhost:8000/api/edges` → `edge-fence: ok`
- [ ] Pi #2 heartbeat green → `edge-barn: ok`
- [ ] Mavic: 3× full batteries, GPS lock (8+ sats), VLOS confirmed
- [ ] Phone: SkyHerdCompanion — "DJI: connected" + "MQTT: connected" both green
- [ ] Laptop: `make hardware-demo` command ready in terminal (pre-typed, not yet entered)
- [ ] Dashboard: `http://localhost:8000` visible on second monitor
- [ ] Coyote cutout: mounted on cardboard, fishing line attached
- [ ] Plush cow: red wet-erase on left eye, in frame of Pi #2

---

## Shot Order

### Shot A — Coyote Hero (35–45 sec)

| Step | Who | Action | Expected on screen |
|------|-----|--------|-------------------|
| 1 | George | Stand near laptop, face camera. Say: *"It's 7:42 pm on the south range."* | Dashboard: 50 cows grazing |
| 2 | George | Run `make hardware-demo` | Terminal: "Starting SkyHerd hardware-only demo…" |
| 3 | Gavin | Pull coyote cutout through Pi #1 frame (2–3 sec, 1–2 m/sec) | Pi logs detection; MQTT fires |
| 4 | Auto | FenceLineDispatcher fires | Dashboard: agent log lights up "Coyote detected, dispatching drone" |
| 5 | Auto | Mavic lifts off | Physical drone ascent OR SITL animation on dashboard |
| 6 | Auto | Deterrent plays | Bluetooth speaker tone / phone speaker |
| 7 | Auto | Wes call | George's phone rings — Wes voice: *"Boss. Coyote at the south fence. Drone's on it."* |
| 8 | Auto | Dashboard updates | Attestation panel: signed event hash visible |
| 9 | George | Hold phone up to camera, then gesture to dashboard | Close-up on "Cleared. Logged." status |
| 10 | George | Deliver line: *"Detection to drone to rancher — under 30 seconds."* | — |

**Cut**: tight on attestation hash panel.

---

### Shot B — Sick Cow (20 sec)

| Step | Who | Action | Expected on screen |
|------|-----|--------|-------------------|
| 1 | Josh | Frame Pi #2 + plush cow (left eye in center) | — |
| 2 | George | Say: *"Same mesh, second camera, different agent."* | — |
| 3 | Auto | HerdHealthWatcher fires (runs in background) | Dashboard: "A014 — pinkeye flag, severity: escalate" |
| 4 | Auto | Vet-intake packet populates | Dashboard panel: animal ID, GPS, symptoms, vet window |
| 5 | Auto | Wes lower-urgency call or ring | Wes: *"Boss. A014's got something in her left eye. Vet packet ready."* |
| 6 | George | Wipe red marker off plush cow | Say: *"No false-alarm vet bill — every flag is signed and logged."* |

---

### Shot C — Split-Screen Sim (15 sec)

| Step | Who | Action | Expected on screen |
|------|-----|--------|-------------------|
| 1 | Josh | Dashboard full-screen | 3 background scenarios running (water, calving, storm) + cost ticker |
| 2 | George | Narrate: *"Behind that one coyote call, three more agents are running — water tanks, calving watch, storm routing — 24/7."* | Live cost ticker ticks; agent lanes scroll |

---

## Fallback Lines

| Situation | George says |
|-----------|-------------|
| Mavic won't arm | *"Drone sim while we reset — same reasoning engine, same signed ledger."* |
| Pi timeout (sim fallback fires) | *"Here's what just played on the real Pi — our fallback re-runs the exact same cascade from sim."* |
| Wes ring instead of call | *"That's the dashboard ring — in the field, that's a real voice call to my phone."* |

---

## After-Shoot

- [ ] Wipe red marker off plush cow
- [ ] RTH Mavic, swap battery
- [ ] `git log --oneline -5` → confirm JSONL in `runtime/hardware_demo_runs/`
- [ ] Check attestation: `uv run skyherd-attest verify`
- [ ] Upload raw footage to drive
