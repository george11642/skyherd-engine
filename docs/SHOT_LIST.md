# SkyHerd — Shot List for 3-Minute Submission Video

**Pairs with:** `docs/DEMO_VIDEO_SCRIPT.md` (sim-first) and `docs/VIDEO_SCRIPT.md` (hybrid field cut).
**Version:** Phase 9 · 2026-04-24

Every shot is numbered, typed, duration-budgeted, and mapped back to the
DEMO_VIDEO_SCRIPT.md time anchor. Duration in seconds. Types:

- `screen-capture` — OBS/QuickTime of the dashboard
- `physical-hero` — on-camera field shot (George, hardware, prop)
- `b-roll` — filler footage (landscape, dawn, cattle, weather)
- `overlay` — motion-graphic or text overlay composited in post
- `title-card` — full-frame text on solid background
- `split-screen` — two simultaneous sources

---

## Master shot list

| # | Type | Time | Dur | Subject | Source / Capture | Script anchor |
|---|------|------|-----|---------|------------------|---------------|
| 1 | title-card | 0:00 | 3.0 | Black card: "A cow can be dying for 72 hours before anyone sees it." | Editor | ACT1 cold open |
| 2 | screen-capture | 0:03 | 5.0 | Dashboard reveal — warm StatBand, 5 idle lanes, $4.17/wk cost ticker, ambient glyphs | OBS scene 1 @ 1080p60 | `dashboard/ambient/t0` |
| 3 | physical-hero | 0:08 | 10.0 | George on camera, head-and-shoulders — "ranch checks itself" pitch | Camera A | 0:08 – 0:18 |
| 4 | overlay | 0:08 | 10.0 | PIP 20% bottom-right: ambient dashboard loop | OBS scene 2 PIP | 0:08 – 0:18 |
| 5 | b-roll | 0:18 | 7.0 | Dashboard full-frame with SkyHerd wordmark animating in | OBS + After Effects | 0:18 – 0:25 |
| 6 | screen-capture | 0:25 | 13.0 | Slow vertical pan of full dashboard (StatBand → map → attest) | OBS zoom+pan preset | 0:25 – 0:38 |
| 7 | screen-capture | 0:38 | 14.0 | **Scenario 1 — coyote** — map zoom SW fence, FenceLineDispatcher flash, drone mini-cap, speaker pulse, HashChip | OBS — run `skyherd-demo play coyote --seed 42` | `scenario/coyote/*` |
| 8 | screen-capture | 0:52 | 14.0 | **Scenario 2 — sick cow** — VetIntakePanel slide-in, PixelDetectionChip bbox on left eye, Wes voice cue | OBS — run `skyherd-demo play sick_cow --seed 42` | `scenario/sick_cow/*` |
| 9 | screen-capture | 1:06 | 14.0 | **Scenario 3 — water tank** — tank 7 red glyph, drone flyover mission, IR still | OBS — run `skyherd-demo play water --seed 42` | `scenario/water/*` |
| 10 | screen-capture | 1:20 | 14.0 | **Scenario 4 — calving** — behavior trace, priority rancher page | OBS — run `skyherd-demo play calving --seed 42` | `scenario/calving/*` |
| 11 | screen-capture | 1:34 | 14.0 | **Scenario 5 — storm** — weather overlay, paddock redirect arrow, acoustic pulses | OBS — run `skyherd-demo play storm --seed 42` | `scenario/storm/*` |
| 12 | screen-capture | 1:48 | 22.0 | Ambient 30× — all 5 lanes idle, cost ticker resumes | OBS + `/api/ambient/speed` = 30 | `ambient/30x/*` |
| 13 | overlay | 1:48 | 8.0 | "5 Managed Agents · 1 session each · idle-pause" | Editor motion-graphic | synthesis beat |
| 14 | overlay | 1:56 | 8.0 | "33 skill files · CrossBeam pattern" | Editor motion-graphic | synthesis beat |
| 15 | overlay | 2:04 | 8.0 | "Ranch + Mavic + Wes voice · Physical loop, sim-first" | Editor motion-graphic | synthesis beat |
| 16 | split-screen | 2:20 | 20.0 | **LEFT** terminal `skyherd-attest verify` green · **RIGHT** fresh clone + timer sticker | OBS dual source | ACT3 substance |
| 17 | physical-hero | 2:40 | 15.0 | George over-shoulder at dashboard, "beef at record highs" close | Camera A | ACT3 close |
| 18 | title-card | 2:55 | 5.0 | Full wordmark + 3 lines (URL, stack, name) | Editor | ACT3 sign-off |
| 19 | title-card | 3:00 | — | Cut to black | Editor | End |

**Total counted: 19 shots · budgeted 179.0s (of 180s) · 1s for clap marker.**

---

## Additional "emergency b-roll" (for overflow / cut-in needs)

These are unscripted but shot on the day; pull if any scene runs short.

| # | Type | Dur | Subject | Notes |
|---|------|-----|---------|-------|
| E1 | b-roll | 5.0 | Dawn ranch landscape (New Mexico stock or licensed Pexels) | For ACT1 warmth |
| E2 | b-roll | 5.0 | Water tank close-up (stock or local farm supply) | ACT1 pre-title |
| E3 | b-roll | 4.0 | Cattle grazing wide | Transition ACT1→ACT2 |
| E4 | b-roll | 4.0 | Mavic on the ground, props close-up | Transition ACT2→ACT3 (if field available) |
| E5 | b-roll | 3.0 | Close-up of laptop keyboard + make demo output | ACT3 fresh-clone |
| E6 | physical-hero | 3.0 | George holding phone showing PWA | ACT2 sick-cow transition |
| E7 | b-roll | 4.0 | Pi heartbeat LED blinking | ACT1 establishing tech |
| E8 | b-roll | 3.0 | Twilio SMS mock-up on phone | ACT2 calving priority page |

---

## Physical-hero shot details (George / props)

**Shot 3 — George on camera, ACT1:**
- Frame: head-and-shoulders, plain barn/fence/field behind (avoid interior rooms).
- Wardrobe: working cowboy / soft-hat look if available; otherwise clean shirt + subtle ranch element.
- Delivery: direct address, warm confidence, no reading tone.
- Take 3+ variations; pick the one where eyes land on camera twice.

**Shot 17 — George at the dashboard, ACT3:**
- Frame: over-shoulder, dashboard soft-focus ~30% visible.
- Delivery: slightly lower energy than Shot 3; this is the "substance" beat.
- Single take preferred — 15s continuous.

---

## Screen-capture hygiene (every `screen-capture` row)

- Resolution: **1080p60 H.264**, bitrate ≥ 20 Mbps.
- Dashboard window: maximized, 100% system zoom, dark or sage theme (consistent across takes).
- No browser chrome — use Chrome PWA mode (F3 or fullscreen) to hide URL bar.
- Close notifications, Dock, menubar clutter.
- Record system audio only if the scene calls for deterrent tone or Wes voice;
  otherwise mute and layer audio in post.

---

## B-roll image-gen prompts (stylized overlays + thumbnails)

Use these prompts with your preferred text-to-image tool (Midjourney v6, DALL-E 3,
Imagen 3, Stable Diffusion XL) for ACT 2 synthesis overlays and the YouTube thumbnail.

### Prompt 1 — "Wireframe ranch with glowing sensor nodes"

> Isometric wireframe illustration of a 50,000-acre New Mexico ranch at dusk.
> Glowing sage-green sensor nodes dot the landscape: water tanks pulsing cyan,
> trough cameras emitting soft light cones, a small drone silhouette tracing a
> flight path. Ultra-thin 1px line art on a deep-navy background, star-field
> above, subtle topographic contour lines. Minimal, calm, technical. No people.
> Mood: watchful. Aspect 16:9.

Use for: ACT 2 synthesis beat under the "5 Managed Agents" callout (Shot 13).

### Prompt 2 — "Attestation chain visualization"

> Abstract data visualization of an Ed25519 Merkle attestation chain: a
> vertical cascade of cryptographic HashChip tiles, each signed in sage-green
> text, linked by glowing lines. Background: subtle desert-dawn gradient
> (amber → pale sky-blue). Tile style: frosted glass on deep navy, crisp
> monospace numerals. No text overlays. Feels like a tamper-evident ledger
> meant for insurance auditors. Aspect 16:9, editorial clean.

Use for: ACT 3 attestation split-screen background (Shot 16 LEFT side underlay).

### Prompt 3 — "Wes — the cowboy voice"

> Stylized silhouette portrait of a weathered Southwestern cattle rancher in
> a wide-brim hat, backlit by desert sunrise. Thin rim light on the hat and
> shoulders, otherwise nearly a black silhouette against a peach-and-amber
> sky. Distant ranch fence in shallow focus. Cinematic, dignified, quiet.
> No face detail visible — this is a persona, not a portrait. Aspect 16:9.

Use for: when Wes voice plays (lower-third thumbnail in the audio track) +
optional ACT 1 transition visual.

### Prompt 4 — "YouTube thumbnail — headline option A"

> Cinematic composition: far-left 1/3 a silhouette of a person in a hat looking
> at a laptop on a tailgate at dusk; center 1/3 a dashboard interface with 5
> glowing agent lanes and a green attestation chain; right 1/3 a Mavic drone
> backlit against a deep desert sky. Warm amber-to-sage gradient. Bold title
> text over the dashboard center: "THE RANCH WATCHES ITSELF". Sub-text below:
> "5 Claude Managed Agents · 24/7". High contrast, readable at 320×180. 16:9.

Use for: primary YouTube thumbnail; see `docs/YOUTUBE.md` for alternate.

### Prompt 5 — "YouTube thumbnail — headline option B"

> Split composition: left half a close-up weathered cowboy hand on a dashboard
> showing the SkyHerd interface with a coyote-detection alert pulsing; right
> half a DJI Mavic Air 2 lifting off against a blue-gold dawn sky. Center
> overlay: white bold "$4.17/week TO WATCH 50,000 ACRES". Cinematic, editorial.
> 16:9. 1280×720.

Use for: A/B alternate thumbnail test if platform allows.

---

## Captions / lower-thirds (companion to `docs/demo-assets/captions.json`)

| Time | Lower-third text |
|------|------------------|
| 0:04 | *"50,000 acres. Two hours a day. Just water."* |
| 0:25 | *"Live dashboard · sim-first · fresh clone reproducible"* |
| 0:38 | *"SCENARIO 1 · Coyote at fence"* |
| 0:52 | *"SCENARIO 2 · Pinkeye in A014"* |
| 1:06 | *"SCENARIO 3 · Water tank 7 pressure drop"* |
| 1:20 | *"SCENARIO 4 · Calving — Cow 117"* |
| 1:34 | *"SCENARIO 5 · Storm + acoustic herd move"* |
| 1:48 | *"Idle. Billing paused."* |
| 2:20 | *"Reproducible · <3 min fresh clone · SEED=42"* |
| 2:40 | *"Beef at record highs. Cow herd at 65-yr low."* |
| 2:55 | *"github.com/george11642/skyherd-engine · MIT · Opus 4.7"* |

---

## Handoff to editor

Folder layout for the editor:
```
video-project/
├── raw/
│   ├── 01_title_card.mov                (3s)
│   ├── 02_dashboard_establish.mov       (5s, OBS)
│   ├── 03_george_on_camera.mov          (10s × 3 takes)
│   ├── 04_dashboard_ambient_pip.mov     (10s, OBS scene 2)
│   ├── 07_coyote_scenario.mov           (14s, OBS)
│   ├── 08_sickcow_scenario.mov          (14s, OBS)
│   ├── 09_water_scenario.mov            (14s, OBS)
│   ├── 10_calving_scenario.mov          (14s, OBS)
│   ├── 11_storm_scenario.mov            (14s, OBS)
│   ├── 12_ambient_30x.mov               (22s, OBS)
│   ├── 16_split_attest_clone.mov        (20s, OBS dual-source)
│   ├── 17_george_close.mov              (15s × 2 takes)
│   └── 18_wordmark.png                  (static, export at 3:00 duration)
├── overlays/
│   ├── managed_agents_callout.mov       (8s, alpha)
│   ├── skills_callout.mov               (8s, alpha)
│   └── creative_callout.mov             (8s, alpha)
├── audio/
│   ├── wes_coyote_fence.wav             (pre-rendered, ElevenLabs)
│   ├── wes_sick_cow.wav
│   ├── wes_calving.wav
│   ├── wes_storm.wav
│   ├── wes_close.wav
│   └── george_vo_*.wav                  (all VO recorded to lav)
├── stills/
│   ├── wireframe_ranch_prompt1.png      (from image-gen Prompt 1)
│   ├── attestation_chain_prompt2.png    (Prompt 2)
│   └── wes_silhouette_prompt3.png       (Prompt 3)
└── project.drp / project.prproj
```

Editor delivers: `skyherd-submission-final.mp4`, 1080p60 H.264, ≤500 MB, CEA-608 captions from `docs/demo-assets/captions.json`.
