# SkyHerd — Demo Video Script (Reproducible Scenario Harness, 3:00 Total)

> ## v2 status (2026-04-24)
>
> **This file is the v1 fallback script.** Wes cowboy persona, 3-act 25/115/40s
> layout. Preserved for the v1 fallback render at
> `docs/demo-assets/video/skyherd-demo-v1-sim-first.mp4`.
>
> **The v2 submission script lives across three variant files** — the dual-vision
> iteration loop (Phase H of `/home/george/.claude/plans/smooth-leaping-popcorn.md`)
> picks the winner:
>
> - **Variant A — Winner-pattern** · `docs/scripts/skyherd-script-A-winner-pattern.md`
>   3-act Setup/Demo/Close (60/90/30s). Identity/contrarian hook. Emphasis-only captions.
> - **Variant B — Hybrid** · `docs/scripts/skyherd-script-B-hybrid.md`
>   3-act same skeleton. Metric-first hook ("$4.17/week"). Emphasis-only captions.
> - **Variant C — Differentiated** · `docs/scripts/skyherd-script-C-differentiated.md`
>   5-act Hook/Story/Demo/Substance/Close (20/50/55/35/20s). Metric hook.
>   Word-level kinetic captions throughout.
>
> All three v2 variants share: neutral 19yo male voice (**Antoni — ElevenLabs
> voice ID `ErXwobaYiN019PkySvjV`**), no Wes cowboy-isms, same B-roll inventory,
> same dashboard MP4s, same hackathon-criteria coverage signals. Filenames migrate
> `wes-*.mp3` → `vo-*.mp3` for v2 render paths.
>
> Reasoning for the voice pick: per `/home/george/.claude/plans/smooth-leaping-popcorn.md`
> Phase C audition cues, Antoni's tone reads as "neutral 19yo guy who built this
> in his dorm" — the brief for v2. Arnold-young (`VR6AewLTigWG4xSOukaG`) trends
> heavier/older; Bill-Liam (`pqHfZKP75CvOlQylNhV4`) trends middle-aged narrator.
> Antoni clocks ~3.6s on the test cue (good cadence) and matches the
> college-student-engineer brand we want post-Wes.
>
> Detailed rationale for the 3-variant track is in plan §"3-variant render track"
> and Phase A's `.planning/research/winner-top3-analysis.md`.

---

**Version:** Phase 9 canonical cut · 2026-04-24 (hardware deferred to Year-2) — **superseded by v2 variant scripts above**
**This doc:** the **v1 fallback submission script**, recording end-to-end from a
laptop against a deterministic scenario harness. Every beat is keyed to a
pause-point in `make demo SEED=42 SCENARIO=all` — byte-stable across replays
(per `tests/test_determinism_e2e.py`), so any judge can clone the repo, run the
command, and scrub to the same pixels shown in the video. Reproducibility is a
feature, not a fallback: the entire submission is designed so a reviewer can
verify every claim themselves.

> `docs/VIDEO_SCRIPT.md` (the hybrid field+sim cut) is retained as a Year-2
> reference but is **not** the submission cut.

**Deadline:** Sun 2026-04-26 20:00 EST (target submit 18:00 EST).
**Format:** 3:00 total, 1080p60 H.264, ≤500 MB, YouTube unlisted.
**Prize tracks:**
- Best Use of Claude Managed Agents ($5k)
- Keep Thinking ($5k)
- Most Creative Opus 4.7 Exploration ($5k)

---

## Three-act layout

```
┌──────── ACT 1 — Hook ──────────────────┐ 0:00 – 0:25  (25 s)
│ Cold open · one-line pitch             │
├──────── ACT 2 — Deterministic Demo ────┤ 0:25 – 2:20  (115 s)
│ Five scenarios @ scrub-point tags      │
├──────── ACT 3 — Substance & Close ─────┤ 2:20 – 3:00  (40 s)
│ Attestation · fresh-clone · wordmark   │
└────────────────────────────────────────┘
```

---

## Pre-record setup (read before rolling)

```bash
# Terminal 1 — stable dashboard (keep running for all takes):
make record-ready        # launches web at :8000, prints scrub-points

# Terminal 2 — triggering specific scenarios one at a time:
uv run skyherd-demo play coyote    --seed 42
uv run skyherd-demo play sick_cow  --seed 42
uv run skyherd-demo play water     --seed 42
uv run skyherd-demo play calving   --seed 42
uv run skyherd-demo play storm     --seed 42

# Or all at once (for ambient b-roll takes):
make demo SEED=42 SCENARIO=all
```

**Operator notes:**
- Dashboard at `http://localhost:8000` on second monitor (OBS scene 1: fullscreen).
- Primary camera: laptop webcam or DSLR on George, tight head-and-shoulders.
- Audio: lav on George; ambient Wes voice pre-rendered in `docs/demo-assets/audio/`.
- System notifications off (macOS: Do Not Disturb; Linux: `gsettings set ...`).

---

## ACT 1 — Hook (0:00 – 0:25)

### 0:00 – 0:08 · Cold open (black → title card → dashboard reveal)

**Scrub point:** freeze-frame dashboard with 5 idle agent lanes + ambient
coyote glyph creeping on the map (ambient loop at 15×). Pre-roll the sim 30 s
before the cut to get this state naturally.

- Black card, white Inter: *"A cow can be dying for 72 hours before anyone sees it."* Hold 3 s silent.
- Fade through to dashboard: warm StatBand, 5 agent lanes idle, cost ticker at **$4.17/week**.

### 0:08 – 0:18 · The ask (George on camera, head-and-shoulders)

> "I'm George. Licensed drone op, I've spent a lot of time on ranches in New Mexico. I wanted to know — what if the ranch checked *itself*?"

B-roll overlay (PIP 20%, bottom-right): ambient dashboard, sensor glyph
blinking on the map.

### 0:18 – 0:25 · One-line pitch (VO over dashboard)

> "SkyHerd. Five Claude Managed Agents watching a ranch 24/7, pausing their own billing between alerts. Built on Opus 4.7."

Wordmark animates in over top of the dashboard. Cut.

---

## ACT 2 — Deterministic Demo (0:25 – 2:20)

**Operator:** run scenarios individually (not `SCENARIO=all`) so you can hit
clean pause/cut points between beats. Each scenario is ~8–12 s wall-clock. Pad
with dashboard B-roll as needed.

### 0:25 – 0:38 · Scene setup (dashboard establish, 13 s)

Pan the dashboard top-to-bottom on OBS (slow vertical pan, 4 s):
- StatBand (top): 5 agent lanes, cost ticker, session counter.
- LiveRanchMap (center): 50 cows grazing, ambient glyphs (water tanks, fence sensors, trough cams).
- AttestationPanel (right): last 10 signed events.

**Voiceover:**
> "One ranch. Five agents. Thirty-three domain skill files. Idle until the sensors call them."

**Scrub anchor:** `dashboard/ambient/t0` — the baseline frame before any event.

### 0:38 – 0:52 · Scenario 1 — Coyote at the fence (14 s)

**Trigger:** `uv run skyherd-demo play coyote --seed 42`

| Beat | Visual | Dashboard trigger |
|------|--------|-------------------|
| 0:38 | Map zooms to SW fence, thermal glyph appears | `camera.motion(coyote, 0.91)` |
| 0:41 | FenceLineDispatcher lane flashes orange | `FenceLineDispatcher WAKE · fence.breach` |
| 0:43 | Agent log scrolls: `launch_drone(FENCE_SW, deterrent)` | tool-call row |
| 0:46 | Mavic mini-cap appears, 20m altitude, SW heading | `drone.telemetry` |
| 0:49 | Speaker icon pulses — 8–18 kHz deterrent tone | `play_deterrent(8000-18000Hz)` |
| 0:51 | Wes voice cue (lower-third): *"Boss. Coyote at the south fence. Drone's on it."* | `page_rancher(urgency=high)` |
| 0:52 | AttestationPanel: new HashChip row | `attest.fence.breach.*` |

**Scrub anchor:** `scenario/coyote/attest_row` — pause tight on the HashChip.

### 0:52 – 1:06 · Scenario 2 — Sick cow (14 s)

**Trigger:** `uv run skyherd-demo play sick_cow --seed 42`

| Beat | Visual | Dashboard trigger |
|------|--------|-------------------|
| 0:53 | Map pans to trough 3, A014 highlighted | `classify_pipeline(A014)` |
| 0:57 | VetIntakePanel slides in, markdown packet | `pinkeye_flag(83%, escalate)` |
| 1:00 | PixelDetectionChip draws bbox on cow's left eye | VIS-05 artifact |
| 1:02 | Wes voice (softer): *"Boss. A014's got something in her left eye."* | `page_rancher(urgency=medium)` |
| 1:05 | Vet packet ready in `/rancher` PWA | Phone mock in PIP |

**Scrub anchor:** `scenario/sick_cow/packet` — pause on VetIntakePanel full.

### 1:06 – 1:20 · Scenario 3 — Water tank pressure drop (14 s)

**Trigger:** `uv run skyherd-demo play water --seed 42`

| Beat | Visual | Dashboard trigger |
|------|--------|-------------------|
| 1:07 | Tank 7 glyph turns red | `lora.water_tank(tank_7, pressure=0.08)` |
| 1:10 | GrazingOptimizer lane wakes | `evaluate_water_access(tank_7)` |
| 1:13 | Drone flyover mission spawns | `launch_drone(TANK_7, inspect)` |
| 1:17 | Infrared still from ArduPilot-SITL drone cam | `drone.snapshot(tank_7)` |
| 1:19 | AttestationPanel: 3 new signed events | chain grows |

**Scrub anchor:** `scenario/water/ir_still` — pause on drone IR frame.

### 1:20 – 1:34 · Scenario 4 — Calving detected (14 s)

**Trigger:** `uv run skyherd-demo play calving --seed 42`

| Beat | Visual | Dashboard trigger |
|------|--------|-------------------|
| 1:21 | CalvingWatch lane activates (rare — seasonal) | `calving_prelabor(cow_117)` |
| 1:25 | Behavior trace: isolation + pawing + tail raise | `behavior_series(cow_117)` |
| 1:28 | Priority urgency on rancher page | `page_rancher(urgency=priority)` |
| 1:31 | Wes voice: *"Boss. 117 is fixin' to calve. You'll want to see this one."* | `page_rancher` |
| 1:33 | PWA phone mock rings (visual-only cue for the edit) | — |

**Scrub anchor:** `scenario/calving/behavior_trace` — behavior series chart.

### 1:34 – 1:48 · Scenario 5 — Storm incoming (14 s)

**Trigger:** `uv run skyherd-demo play storm --seed 42`

| Beat | Visual | Dashboard trigger |
|------|--------|-------------------|
| 1:35 | Weather API overlay on map (scenario harness data) | `weather_forecast(hail, eta=45min)` |
| 1:39 | GrazingOptimizer proposes paddock redirect | `propose_redirect(paddock_3→6)` |
| 1:42 | Acoustic nudge icon pulses at 3 speakers | `acoustic_nudge(cattle_move)` |
| 1:46 | Cows animate moving on the map | `herd.relocate(paddock_6)` |
| 1:47 | StatBand cost ticker blips up ~$0.14 | session event count |

**Scrub anchor:** `scenario/storm/redirect_arrow` — arrow between paddocks.

### 1:48 – 2:20 · Synthesis beat (32 s — cost, skills, mesh callouts)

Cut to full-screen dashboard with the ambient driver at **30×** speed. All 5 agent
lanes idle again. Overlay three annotations in sequence (8–10 s each):

1. **Managed Agents callout** — *"5 Managed Agents · 1 platform session each · idle-pause billing. $4.17/week."*
2. **Keep Thinking callout** — *"33 skill files · Domain knowledge loaded per-task. CrossBeam pattern. Sessions persisted 241 → 5."*
3. **Creative callout** — *"Ranch + Mavic + Wes voice. End-to-end reproducible loop."*

**Voiceover (25 s budget):**
> "Each agent runs on its own Managed Agents session and only wakes when the sensors call it. The skills library loads just what the task needs. Sessions persist so the predator learner actually learns. And the cost ticker freezes in between — this whole ranch runs at four dollars a week."

**Scrub anchor:** `ambient/30x/t=sim_end` — the three overlays stack.

---

## ACT 3 — Substance & Close (2:20 – 3:00)

### 2:20 – 2:40 · Attestation + fresh clone (split screen, 20 s)

**Left half:** Terminal running `uv run skyherd-attest verify` → green chain of
~360 entries, Ed25519 sigs, tamper-evident.

**Right half:** Clean laptop with a physical timer sticker on the bezel.
On-screen text overlay:
```
git clone github.com/george11642/skyherd-engine
uv sync && (cd web && pnpm install && pnpm run build)
make demo SEED=42 SCENARIO=all
```
Timer ticks from 0 → sub-3-min when `make demo` exits clean.

**Voiceover:**
> "Ed25519 Merkle chain. Every tool call signed. Reproducible in a fresh clone in under three minutes — same seed, same bytes, every run. That's the underwriting data we think insurance will pay for in year two."

**Scrub anchor:** `skyherd-attest/verify/green` — terminal green state.

### 2:40 – 2:55 · Why it matters (15 s — George on camera)

Wide shot over George's shoulder at the dashboard:

> "Beef is at record highs. The cow herd is at a 65-year low. Ranchers can't hire their way out of this. The ranch has to watch itself. This is what that looks like."

### 2:55 – 3:00 · Close (5 s)

Full-screen SkyHerd wordmark, three lines below:

- `github.com/george11642/skyherd-engine`
- `MIT · Python 3.11 · TypeScript 5.8 · Opus 4.7 · 1106 tests · 87% coverage`
- `George Teifel · UNM · 2026-04-26`

Wes voice (2 s):
> "That's the ranch takin' care of itself, boss."

Cut to black.

---

## Scrub-point index (for editor)

| Anchor | Time | Scenario / panel |
|--------|------|------------------|
| `dashboard/ambient/t0` | 0:25 | Baseline establish |
| `scenario/coyote/attest_row` | 0:52 | Coyote HashChip |
| `scenario/sick_cow/packet` | 1:06 | VetIntakePanel full |
| `scenario/water/ir_still` | 1:17 | Drone IR frame |
| `scenario/calving/behavior_trace` | 1:33 | Behavior series |
| `scenario/storm/redirect_arrow` | 1:47 | Paddock redirect |
| `ambient/30x/t=sim_end` | 2:10 | Three-callout overlay |
| `skyherd-attest/verify/green` | 2:30 | Terminal green |

Each anchor name maps to a timestamped screenshot in
`docs/screenshots/video-scrub-YYYYMMDD/` — generate those by hand from a clean
`make record-ready` run before the edit session.

---

## "If you only film one thing" fallback ordering

If recording time is tight, film in this priority order:

1. **Act 2 Scenario 1 (coyote, 14 s)** — the headline loop. Don't submit without it.
2. **Act 1 George-on-camera (10 s)** — the human anchor.
3. **Act 3 close wordmark + Wes voice (5 s)** — the sign-off.
4. **Act 2 Scenarios 2–5** (sick cow, water, calving, storm).
5. **Act 3 fresh-clone split-screen** (substitutes nicely with a screen-record).
6. **Act 2 synthesis beat** (can be replaced by a title card).

Each item is self-contained; missing items cut cleanly without orphaning later beats.

---

## Voiceover prompt sheet (Wes cowboy persona)

For pre-rendering with ElevenLabs (`bash docs/demo-assets/audio/render.sh`):

| Key | Text | Urgency |
|-----|------|---------|
| `wes_coyote_fence` | *"Boss. Coyote at the south fence. Drone's on it."* | high |
| `wes_sick_cow` | *"Boss. A014's got something in her left eye. Pulled together a vet packet for you."* | medium |
| `wes_calving` | *"Boss. 117 is fixin' to calve. You'll want to see this one."* | priority |
| `wes_close` | *"That's the ranch takin' care of itself, boss."* | low |
| `wes_storm` | *"Boss. Hail inbound. Movin' the herd to paddock six."* | high |

---

## Production kit

- Webcam or DSLR on tripod (1080p60).
- Second monitor (dashboard full-screen, OBS source).
- OBS with 3 scenes: full dashboard, George + dashboard PIP, split-screen (attest + clone).
- Lav mic; boom as backup.
- Laptop + USB-C charger (don't run on battery during take).
- Silence notifications; close Slack/Discord/Gmail tabs.

---

## Post-production notes

- Editor: DaVinci Resolve (free) or Premiere. Resolve preferred for color.
- Sync: SMPTE timecode if multi-cam, or clap marker at head of each take.
- Lower-thirds: Inter or San Francisco (matches `web/src/index.css --font-body`).
- Color: 5500K warm for Act 1 dawn, lean into `--color-accent-sage` for Act 3.
- Audio: duck field/ambient -12 dB under Wes, -18 dB under George.
- Export: 1080p60 H.264, ≤500 MB, YouTube-unlisted.

---

## Submission day checklist (Sun 2026-04-26)

- [ ] Final edit exported to `~/Downloads/skyherd-submission-final.mp4`.
- [ ] Upload to YouTube as **unlisted**.
- [ ] Copy YouTube URL into `docs/SUBMISSION.md` (replace `{{YOUTUBE_URL}}`).
- [ ] Copy YouTube URL into `docs/LINKEDIN_LAUNCH.md` and `docs/YOUTUBE.md`.
- [ ] Devpost form filled per `docs/SUBMISSION.md`.
- [ ] Final push: `git tag v1.0-submission && git push origin v1.0-submission`.
- [ ] Submit to Devpost (hit Submit by **18:00 EST**, not 20:00).
- [ ] LinkedIn post drafted in `docs/LINKEDIN_LAUNCH.md`; request George approval before posting.

---

*End of canonical script. `docs/VIDEO_SCRIPT.md` (hybrid field+sim cut) retained as Year-2 reference only.*
