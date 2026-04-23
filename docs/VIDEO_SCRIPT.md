# SkyHerd — 3-Minute Submission Video Script

**Deadline:** Sun 2026-04-26 20:00 EST (target submit: 18:00 EST with 2-hour buffer).
**Format:** 3:00 total, 1080p60 H.264, ≤500 MB. YouTube unlisted.
**Companion docs:** `docs/HARDWARE_DEMO_RUNBOOK.md` (60-s on-camera hero), `docs/demo-assets/shot-list.md` (day-of beats), `docs/demo-assets/captions.json` (lower-thirds).

Prize tracks every frame is earning against:
- Best Use of Claude Managed Agents ($5k) — mesh + idle-pause cost ticker visible
- Keep Thinking ($5k) — sessions persist across events (241 → 5 refactor, 33-file skills library)
- Most Creative Opus 4.7 Exploration ($5k) — ranch + Mavic + Wes voice physical loop

---

## Three-act layout

```
┌──────── ACT 1 — Hook ──────────────────┐ 0:00 – 0:25
│ Cold open · problem · one-line pitch   │
├──────── ACT 2 — Live Field Demo ───────┤ 0:25 – 2:05
│ Coyote hero + sick cow, dashboard PIP  │  (90 s)
│ pinned bottom-right @ ~22% width       │
├──────── ACT 3 — Substance & Close ─────┤ 2:05 – 3:00
│ Timelapse @ 30x · attestation · clone  │  (55 s)
│ GitHub + MIT + license card            │
└────────────────────────────────────────┘
```

---

## ACT 1 — Hook (0:00 – 0:25)

### 0:00 – 0:08 · Cold open (black → dawn ranch)

- Black title card, white text: *"A cow can be dying for 72 hours before anyone sees it."* Hold 3 s on silence.
- Cut to pre-dawn wide shot: George in truck, spotlight sweeping a water tank. Engine audio only.
- Lower-third: *"50,000 acres. Two hours a day. Just water."*

### 0:08 – 0:18 · The ask (George on camera)

George, face-on, hand-held, barn or fence in background:

> "I'm George. I'm a licensed drone operator and I've spent a lot of time on ranches. I wanted to know: what if the ranch checked itself?"

B-roll cuts: water tank close-up → trough camera → Pi heartbeat LED → Mavic on the ground.

### 0:18 – 0:25 · One-line pitch (VO over B-roll)

> "SkyHerd. Five Claude Managed Agents watching a ranch 24/7, pausing their own billing between alerts. Built on Opus 4.7."

Visual: SkyHerd wordmark animates in over the open ranch.

---

## ACT 2 — Live Field Demo (0:25 – 2:05)

Operator notes:
- Laptop runs `HARDWARE_OVERRIDES=… make hardware-demo` with **`SKYHERD_AMBIENT=0`** so the dashboard PIP *only* reflects real Pi/Mavic events during this act.
- Camera B (screen-capture OBS) grabs the laptop dashboard full-frame. Editor composites it as a PIP bottom-right 22% width overlay over Camera A field footage.

### 0:25 – 0:38 · Dashboard establish (full-screen, ambient ON @ 15×)

Cut to full-screen dashboard. StatBand warm, 5 lanes idle, ambient loop at 15× so the viewer sees a heartbeat of activity for ~5 s. George VO:

> "This is the nervous system. Five agents — fence line, herd health, predator patterns, grazing, calving. They sit idle. The cost ticker says four dollars a week. Watch what happens when the ranch needs them."

At 0:36 cut ambient OFF and switch to the field setup (laptop operator triggers `SKYHERD_AMBIENT=0` run).

### 0:38 – 1:30 · Shot A — Coyote hero (field, 52 s)

Dashboard PIP pinned bottom-right from 0:38 onward.

| Timestamp | Frame | Dashboard PIP |
|---|---|---|
| 0:40 | Gavin pulls cardboard coyote through fence gap (2-3 s) | `FenceLineDispatcher WAKE · fence.breach · 18:42:07` |
| 0:44 | Mavic lifts automatically | `launch_drone("FENCE_SW", "deterrent")` |
| 0:55 | Drone over the fence, speaker plays 8–18 kHz sweep | `play_deterrent(8000-18000Hz)` |
| 1:02 | George's phone rings; Wes voice audible | `page_rancher(urgency=high)` + attestation hash |
| 1:18 | Drone RTH | `return_to_home()` |
| 1:22 | George face-on: *"Thirty seconds from a pair of yellow eyes on the edge of property to a signed, tamper-evident record. No ranch hand had to see it."* | Tight on attestation HashChip (fingerprint bar visible) |

Lower-third pulse at 1:28: *"30 s · fence → drone → rancher → ledger"*.

### 1:30 – 1:55 · Shot B — Sick cow + vet intake (field, 25 s)

Cut to Pi #2 at trough stand. Plush cow with red wet-erase "discharge" on left eye. PIP continues.

| Timestamp | Frame | Dashboard PIP |
|---|---|---|
| 1:33 | Pi #2 captures frame | `classify_pipeline(A014) → pinkeye 83%` |
| 1:40 | (PIP zooms) | VetIntakePanel renders markdown packet, PixelDetectionChip shows bbox (VIS-05 artifact) |
| 1:46 | Wes voice (softer): *"Boss. A014's got something in her left eye. Pulled together a vet packet for you."* | — |
| 1:50 | George wipes red marker, face-on: *"False alarm here — but every flag is signed. Zero vet bills for nothing. That's how this pays for itself."* | — |

### 1:55 – 2:05 · Transition (10 s)

Tight on George's face, holding phone to camera showing RancherPhone PWA at `/rancher` with the pinkeye packet.

> VO: "One rancher. Five agents. One ledger. Let me show you what's under the hood."

---

## ACT 3 — Substance & Close (2:05 – 3:00)

### 2:05 – 2:30 · Mesh + skills timelapse (screen-cap + overlay)

Full-screen dashboard. Operator: `curl -X POST http://localhost:8000/api/ambient/speed -d '{"speed":30}' -H 'Content-Type: application/json'`. All 8 scenarios cycle in ~25 s.

Overlay annotations pin on:
- *"5 Managed Agents · 1 platform session each · 241 → 5 session refactor"* — Keep Thinking prize
- *"33 skill files · Domain knowledge in `skills/*.md`, not prompts"* — CrossBeam pattern, Managed Agents
- *"Idle-pause billing · Cost ticker freezes between events"* — Managed Agents

VO (3 sentences, <25 s):

> "Each agent sits on its own Managed Agents session and wakes only when the sensors call it. Skills live in 33 markdown files loaded on demand — same pattern that won CrossBeam. And when nothing's happening, nothing's billing."

### 2:30 – 2:50 · Attestation + fresh clone (split 50/50)

Left half: terminal running `uv run skyherd-attest verify` → green chain, ~360 entries signed, Ed25519.

Right half: clean laptop, timer sticker on. Run the README quickstart:
```bash
git clone https://github.com/george11642/skyherd-engine
cd skyherd-engine
uv sync && (cd web && pnpm install && pnpm run build)
make demo SEED=42 SCENARIO=all
```
Total wall time sticker: < 3 min.

VO:
> "Ed25519 Merkle chain. Reproducible in a fresh clone in under three minutes. Same seed, same bytes, every run. That's the underwriting data we think insurance will pay for in year two."

### 2:50 – 3:00 · Close (10 s)

Full-screen SkyHerd wordmark. Three lines stacked:

- `github.com/george11642/skyherd-engine`
- `MIT · Python 3.11 · TypeScript 5.8 · Opus 4.7`
- `George Teifel · UNM`

Wes voice, 2 s:
> "That's the ranch taking care of itself, boss."

Cut to black.

---

## Pre-production checklist

- [x] Ambient driver + `/api/ambient/speed` + `/api/ambient/next` (shipped in v1.1 Part A)
- [x] Dashboard polish (shipped in v1.1 Part B)
- [x] VetIntakePanel renders real packet with pixel bbox (shipped VIS-05)
- [x] RancherPhone PWA at `/rancher` (shipped Phase 5)
- [x] Clickable SkyHerd wordmark on `/rancher` (shipped 887cc91)
- [x] `skyherd-attest verify` CLI (shipped)
- [x] `make demo SEED=42 SCENARIO=all` in <3 min on a fresh clone (shipped BLD-02)
- [ ] Pre-rendered Wes voice takes — run `bash docs/demo-assets/audio/render.sh` with `ELEVENLABS_API_KEY` set on George's laptop before the shoot. Cached under `docs/demo-assets/audio/wes-*.wav`.
- [ ] Captions/lower-thirds — see `docs/demo-assets/captions.json`.
- [ ] Cardboard coyote + plush cow + Bluetooth speaker — per `docs/HARDWARE_DEMO_RUNBOOK.md`.

## Production kit

- Camera A — 1080p60 tripod on fence/trough.
- Camera B — OBS screen-cap of laptop dashboard OR second phone tripod on the second monitor.
- Audio — lav mic on George.
- Power — laptop on wall power or 2× USB-C battery banks.
- Safety — Part 107 checklist from `HARDWARE_DEMO_RUNBOOK.md`.

## Post-production

- Sync on clap marker or SMPTE. PIP composite in Resolve/Premiere.
- Lower-thirds: Inter or San Francisco (matches `--font-body`).
- Color grade: ~5500 K warm for Act 1 dawn, match `--color-accent-sage` in Act 3 transitions.
- Audio duck: field ambient −12 dB under Wes, −18 dB under George VO.
- Export: 1080p60 H.264 ≤500 MB.
- Upload: YouTube unlisted → paste link into Devpost form + repo README.

## Fallback narrative (weather/hardware failure)

If Mavic is grounded:
- Act 2 Shot A swaps to screen-recorded coyote sim. George VO: *"Here's what it looks like from the dashboard side — same code path, same ledger."*
- Shot B runs indoors on a kitchen table with Pi + plush cow.
- Reinforce: *"Sim-first. Hardware optional. That's the point."*

## Devpost submission checklist

- [ ] YouTube unlisted link
- [ ] 100–200 word written summary (lift hero paragraphs from `docs/ONE_PAGER.md`)
- [ ] GitHub repo: `github.com/george11642/skyherd-engine`
- [ ] Prize tracks flagged: Managed Agents, Keep Thinking, Most Creative Opus 4.7
- [ ] `git push origin v1.0` (tag) before submission form
- [ ] README badge: *"Submitted to Built with Opus 4.7 · 2026-04-26"*
