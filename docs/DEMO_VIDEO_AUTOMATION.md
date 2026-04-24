# SkyHerd Demo Video — Automation & Submission Playbook

**Status:** v1 guaranteed (sim-first, autonomous) + v2 planned (hybrid hardware-field)
**Audience:** judges, future-George, collaborators
**Deadline:** Sun 2026-04-26 20:00 EST (target submit 18:00 EST)

## TL;DR

We built two videos in parallel — a fully-autonomous **sim-first** version (v1) that
does not need George on camera, and a **hybrid hero-field** version (v2) whose fate
depends on Fri 2026-04-25 weather at the ranch. v1 is already shipped, byte-stable,
and re-renderable from `seed=42` with a single `make` target. If v2 renders in time,
we submit v2; otherwise v1 is the safety net and goes up to YouTube unlisted by
18:00 EST Sun. Either way, a submittable 3-min demo exists today.

---

## Section 1 — Guaranteed Sim-First Video (v1, shipped)

### What it is

- 3:00 exactly (1920×1080 @ 30 fps master; `--scale=0.5` 960×540 for iteration proofs).
- Built with **Remotion 4.0.451** as the conductor — React 19 + TypeScript, Tailwind v4,
  Inter font. The whole composition is code; there is no Adobe Premiere / After
  Effects / DaVinci project file.
- **Zero human-on-camera footage.** George's two scripted on-camera segments are
  replaced by kinetic-typography treatments layered over dimmed ambient b-roll of
  the live dashboard, with the Wes ElevenLabs voice re-narrating George's script
  words.
- **Byte-stable, re-renderable from `seed=42`** via `make video-pipeline` — the
  Playwright recorder drives the same deterministic scenarios the sim uses, so
  every frame of dashboard footage is reproducible.

### Architecture diagram

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                    SkyHerd Demo Video v1 — Pipeline                  │
 └──────────────────────────────────────────────────────────────────────┘

   (seed=42)                          (ElevenLabs API,
       │                               Wes cowboy persona)
       ▼                                       │
   make dashboard  →  http://localhost:8000    │
       │                                       ▼
       ▼                              scripts/render_vo_phase1.sh
   scripts/record_dashboard.py               │
   (Playwright headless, 1920×1080)          │
       │                                     ▼
       ▼                   remotion-video/public/voiceover/*.mp3
   remotion-video/public/clips/              +  envelope.json
   ├── ambient_establish.mp4           remotion-video/public/music/
   ├── coyote.mp4                      └── bgm-main.mp3  (synth placeholder)
   ├── sick_cow.mp4                    remotion-video/public/sfx/
   ├── water.mp4                       ├── drone-whir.mp3
   ├── calving.mp4                     ├── coyote-distant.mp3
   ├── storm.mp4                       ├── ui-tick.mp3
   ├── ambient_30x_synthesis.mp4       ├── keyboard-type.mp3
   ├── attest_verify.mp4               ├── radio-static.mp3
   └── fresh_clone.mp4                 └── paper-rustle.mp3
            \                        /
             \                      /
              ▼                    ▼
     ┌──────────────────────────────────────┐
     │     remotion-video/src/Main.tsx      │
     │  <Series>                            │
     │     <Sequence> Act1Hook (0:00-0:25)  │
     │     <Sequence> Act2Demo (0:25-2:20)  │
     │     <Sequence> Act3Close(2:20-3:00)  │
     │  </Series>                           │
     │  + <Audio src="bgm-main.mp3"         │
     │           volume={duckingCurve}/>    │
     │  + SFX <Audio startFrom=…/> layers   │
     └──────────────────────────────────────┘
                       │
                       ▼
              pnpm run render
                       │
                       ▼
       remotion-video/out/skyherd-demo.mp4
                       │
                       ▼ ffmpeg loudnorm=I=-16:TP=-1:LRA=11
                       │
                       ▼
  docs/demo-assets/video/skyherd-demo-v1-sim-first.mp4
                (submittable, -16 LUFS, YouTube-spec)
```

### Files & layout

| Path | Purpose |
|------|---------|
| `remotion-video/src/Root.tsx` | Registers the `Main` composition with fps/size. |
| `remotion-video/src/Main.tsx` | Top-level `<Series>` of 3 acts + BGM + SFX bed. |
| `remotion-video/src/acts/Act1Hook.tsx` | 0:00–0:25 hook + kinetic-typography George #1. |
| `remotion-video/src/acts/Act2Demo.tsx` | 0:25–2:20 establish + 5 scenarios + synthesis beat. |
| `remotion-video/src/acts/Act3Close.tsx` | 2:20–3:00 attestation split-screen + kinetic-typography George #2 + wordmark close. |
| `remotion-video/src/compositions/calculate-main-metadata.ts` | `calculateMetadata` hook that auto-sizes `durationInFrames` from VO MP3 lengths. |
| `remotion-video/public/clips/*.mp4` | 9 headless-recorded dashboard clips (`scripts/record_dashboard.py` output). |
| `remotion-video/public/voiceover/*.mp3` | 10 Wes ElevenLabs VO cues + `envelope.json` for ducking. |
| `remotion-video/public/music/bgm-main.mp3` | 60 s ambient bed (synthesized placeholder — see `SOURCE.md`). |
| `remotion-video/public/sfx/*.mp3` | 6 synthesized SFX cues (drone-whir, coyote-distant, keyboard-type, paper-rustle, radio-static, ui-tick). |
| `scripts/record_dashboard.py` | Playwright-driven headless Chromium recorder (593 LOC). |
| `scripts/render_vo_phase1.sh` | Re-runnable ElevenLabs Wes VO renderer (idempotent). |
| `scripts/video_iterate.sh` | Dual-vision iteration loop driver (Phase 5, 6-iter cap). |
| `docs/demo-assets/video/skyherd-demo-v1-sim-first.mp4` | Final submission artifact. |

### 8 scrub-anchors → Remotion frame mapping

The original `docs/DEMO_VIDEO_SCRIPT.md` lines 235-246 define 8 anchor points the
editor uses for QA stills. At 30 fps, the anchor timestamps map to the following
absolute frame numbers in the final 5400-frame composition:

| Anchor | Script timestamp | Final frame | Act |
|--------|-----------------:|------------:|:---:|
| `dashboard/ambient/t0` | 0:25 | 750 | 2 |
| `scenario/coyote/attest_row` | 0:52 | 1560 | 2 |
| `scenario/sick_cow/packet` | 1:06 | 1980 | 2 |
| `scenario/water/ir_still` | 1:17 | 2310 | 2 |
| `scenario/calving/behavior_trace` | 1:33 | 2790 | 2 |
| `scenario/storm/redirect_arrow` | 1:47 | 3210 | 2 |
| `ambient/30x/t=sim_end` | 2:10 | 3900 | 2 |
| `skyherd-attest/verify/green` | 2:30 | 4500 | 3 |

Regenerate a still at any anchor with:

```bash
cd remotion-video
pnpm exec remotion still src/index.ts Main --frame=1560 \
    out/anchor-coyote.png
```

The iteration loop (`scripts/video_iterate.sh`) samples all 8 anchors every round
and hands the PNGs to both Claude `Read()` and `mcp__gemini__gemini_image` for
dual-vision critique.

### How to re-render

Starting from a clean clone:

```bash
# 1. Prerequisites
cd /home/george/projects/active/skyherd-engine
uv sync --all-extras
(cd web && pnpm install && pnpm run build)
(cd remotion-video && pnpm install)
uv run --with playwright playwright install chromium

# 2. Secrets (only needed if re-rendering the Wes VO from scratch)
export ELEVENLABS_API_KEY=...           # falls back to piper/espeak

# 3. End-to-end
make video-pipeline
# → docs/demo-assets/video/skyherd-demo-v1-sim-first.mp4

# 4. Individual stages
make video-record-clips   # re-record 9 dashboard clips (needs :8000 live)
make video-iterate        # run the dual-vision QA loop (cap 6)
make video-render         # final 1080p render + loudnorm to -16 LUFS
```

The VO renderer is idempotent — MP3s only regenerate if missing. The dashboard
recorder drives `seed=42` scenarios against the live FastAPI server, so its
output is byte-stable. Remotion's `calculateMetadata` auto-sizes the composition
to the measured VO durations, so small re-renders of one VO cue won't break
timing elsewhere.

### Drop-in filmed-take procedure

The composition is pre-wired to accept filmed George segments if he records them
on Fri/Sat. The file-drop contract:

1. Record two MP4s (H.264 / yuv420p / 1920×1080 / 30 fps recommended):
   - `remotion-video/public/takes/george_hook.mp4` — ~10 s, George reading the
     Act 1 hook line (see `docs/DEMO_VIDEO_SCRIPT.md` l.96–104).
   - `remotion-video/public/takes/george_why_it_matters.mp4` — ~15 s, George
     reading the Act 3 "why it matters" beat (see script l.202–214).
2. Flip the toggle in `remotion-video/src/compositions/calculate-main-metadata.ts`:
   add `useFilmedTakes: true` to the `MainProps` default and thread it into the
   kinetic-typography branches in `Act1Hook.tsx` and `Act3Close.tsx`. The Wes VO
   cues (`wes-george-hook.mp3`, `wes-why.mp3`) become inactive when filmed takes
   are enabled; the on-camera audio plays natively.
3. Re-run `make video-render`. Kinetic typography branches cut out, filmed takes
   cut in. Total duration stays within 3:00 ± 1 s because the filmed takes are
   clamped to the same slot lengths (`ACT1_GEORGE_MIN_SECONDS = 10`,
   `ACT3_WHY_SECONDS = 15`).

> NOTE: the `useFilmedTakes` prop is **planned** as of Phase 6. If a later
> iteration adds it, this doc should be updated to say "active" instead of
> "planned." Current `MainProps` = `{ actDurations, voDurationsFrames }`.

### Audio mix details

**Voiceover (Wes persona)**:
- Voice ID `pNInz6obpgDQGcFmaJgB`, model `eleven_multilingual_v2` on
  ElevenLabs. Renderer at `scripts/render_vo_phase1.sh` falls back to
  `piper` then `espeak-ng` if the API key is missing or rate-limited.
- 10 MP3s cover every scripted beat: `wes-george-hook`, `wes-establish`,
  `wes-coyote`, `wes-sick-cow`, `wes-calving`, `wes-storm`, `wes-synthesis`,
  `wes-attest`, `wes-why`, `wes-close`. Durations measured at metadata-resolution
  time and fed to `calculateMetadata`.

**Background music**:
- `remotion-video/public/music/bgm-main.mp3` — 60 s synthesized ambient bed,
  looped 3× by Remotion to cover the 180 s composition. Fade-in frames 0→150
  (5 s), fade-out frames 5250→5400 (5 s) via `interpolate`.
- **Placeholder**: generated from `ffmpeg lavfi anoisesrc=color=brown` +
  echo + lowpass + loudnorm=I=-18. See
  `remotion-video/public/music/SOURCE.md` for the exact command and swap-in
  instructions. To upgrade pre-submit: drop a real track in at the same path
  and re-run `make video-render`. Candidate sources listed in that SOURCE.md.

**SFX layer**:
- 6 synthesized MP3s cued at absolute frame positions (e.g., `drone-whir.mp3`
  at the Scenario-1 deterrent beat). Also procedurally generated — not
  royalty-encumbered.

**Ducking**:
- `public/voiceover/envelope.json` lists per-VO start frames + active-window
  spans. A `duckingCurve(frame)` in `Main.tsx` returns `0.25` when any VO
  window is active, `0.6` otherwise, and feeds `<Audio volume={...}>`. This is
  a **binary envelope duck**, not true sidechain compression — see "Known
  limitations" below.

**Final loudness**:
- `ffmpeg -af loudnorm=I=-16:TP=-1:LRA=11 -c:v copy` normalizes the master to
  -16 LUFS integrated, -1 dBTP true-peak, LRA 11 — the YouTube upload spec.

### Known limitations (v1)

From the Phase 4 agent's self-report:

1. **Binary BGM ducking** — `duckingCurve` is a 0.25↔0.6 step function keyed
   off a pre-computed envelope JSON, not a per-sample sidechain compressor. It
   sounds fine on most speakers but can feel abrupt on a hi-fi listen. _Fix if
   time:_ resample `envelope.json` at 10 Hz and interpolate with a short
   attack/release curve in `duckingCurve`.
2. **CSS-gradient placeholder in Act 3** — the ranch b-roll behind the
   "Why it matters" kinetic typography is a Tailwind gradient, not the ranch
   photo the script calls for (no royalty-free photo was sourced). _Fix if
   time:_ drop a CC-BY ranch photo into `remotion-video/public/assets/ranch-photos/`
   and replace the gradient with a Ken-Burns `<Img>`.
3. **Mocked scrub-anchor chips** — some scrub-anchor overlay chips (e.g. the
   HashChip on the coyote scenario) are mocked React elements rather than
   real dashboard-state extractions. _Fix if time:_ wire the dashboard's
   attestation row selector into the Playwright recorder so Remotion inherits
   real attestation hashes.
4. **Remotion 4.x deprecation warnings** — `getAudioDurationInSeconds` from
   `@remotion/media-utils` logs a deprecation warning at render-time. Still
   works on 4.0.451; migration to the newer `@remotion/media` API deferred
   until post-submission.
5. **BGM provenance is placeholder** — see `public/music/SOURCE.md`. Swap to
   a properly-licensed track before submission if time permits.

### Commit reference

- Phases 1-4 (VO + clips + Remotion scaffold + 3-act composition) shipped
  atomically in commit `aa8baa6f`.
- Phase 5 iteration commits follow the pattern `video(iter-N): ...` and are
  capped at 6.
- Final render + loudnorm + package commit: `{FINAL_COMMIT_HASH}` (set by the
  Phase 6 agent after the loop settles).

---

## Section 2 — Hybrid Hardware-Field Video (v2, planned)

### What it is

- Same 3-act structure, same 3:00 target, same Remotion composition —
  only specific `<Video src=...>` references swap from simulated dashboard
  clips to real field footage shot on Fri 2026-04-25.
- Hardware path: **collar-free** per `docs/HARDWARE_PI_FLEET.md`. One
  Raspberry Pi 4 (`edge-house`, all six trough cameras + thermal + MQTT)
  plus one Intel Galileo Gen 1 (`edge-tank`, water-tank + weather
  telemetry), plus one DJI Mavic 3 Enterprise for aerial shots. No DIY
  LoRa collars required.
- George appears on camera for his two scripted segments, replacing the
  kinetic-typography treatments from v1.

### Replaceable segments (v2 shot list)

Map from v1 sim-first clip to Fri field replacement, with provenance tied back
to `docs/HARDWARE_PI_FLEET.md` and `docs/HARDWARE_DEMO_RUNBOOK.md`:

| v1 clip (sim) | v2 field replacement | Provenance | Script beat |
|---------------|----------------------|------------|:-----------:|
| `public/clips/coyote.mp4` | Mavic hover over fenceline at sunset w/ deterrent audio + real Wes call overlay | Mavic thermal payload, per `HARDWARE_DEMO_RUNBOOK.md` scene 1 | Act 2 Scenario 1 (0:38–0:52) |
| `public/clips/sick_cow.mp4` | Pi-camera trough shot of A014 (or stand-in cow) + vet-intake packet overlay | `edge-house` Pi camera + dashboard `/rancher` PWA | Act 2 Scenario 2 (0:52–1:06) |
| `public/clips/water.mp4` | Mavic IR flyover of real water trough at dawn | Mavic thermal payload | Act 2 Scenario 3 (1:06–1:20) |
| `public/clips/calving.mp4` | Pi-camera pasture shot (or stock-footage stand-in) + behavior-trace overlay | `edge-house` Pi camera | Act 2 Scenario 4 (1:20–1:34) |
| `public/clips/storm.mp4` | Mavic wide shot of herd + paddock redirect arrow overlay | Mavic + dashboard overlay | Act 2 Scenario 5 (1:34–1:48) |
| `public/clips/ambient_30x_synthesis.mp4` | Time-lapse of sun moving over ranch while agent-mesh chips fire | Mavic stationary + dashboard overlay | Act 2 synthesis (1:48–2:20) |
| Kinetic-typography George #1 (Act 1) | George on-camera reading Act 1 hook line | Handheld / tripod, lav mic | Act 1 hook (0:08–0:18) |
| Kinetic-typography George #2 (Act 3) | George on-camera reading "Why it matters" beat | Same rig | Act 3 (2:40–2:55) |

Segments NOT replaced (v2 reuses v1):
- Dashboard ambient establish clips (`ambient_establish.mp4`) — the dashboard
  is the hero of the sim-first cut and still works in the hybrid.
- Attestation terminal (`attest_verify.mp4`) + fresh-clone split (`fresh_clone.mp4`) —
  these are genuinely screen-recorded from the real stack and don't benefit
  from a field replacement.
- All Wes VO — George's script stays identical; Wes-voice stays identical.

### Weather contingency

If Fri 2026-04-25 weather grounds the Mavic (wind > 25 knots, rain, or FAA
TFR over the ranch), we fall back to **v1 unchanged**. No re-edits are
required because v1 is already a complete, submittable 3-min video. The
Saturday decision meeting (see Section 3) chooses between a partial-hybrid
edit (v1 + George-on-camera only, dashboard stays simulated) and a pure-v1
submission.

### Edit workflow

Splicing hardware footage into the existing Remotion composition without
breaking determinism:

1. Drop field MP4s into `remotion-video/public/clips/hero/*.mp4` (same codec
   as Playwright output: H.264, yuv420p, 1920×1080, 30 fps — use
   `ffmpeg -c:v libx264 -pix_fmt yuv420p -r 30 …` if the camera output
   differs).
2. Edit the scenario `<Sequence>` in `Act2Demo.tsx` to point at the new file
   (e.g. `<Video src={staticFile("clips/hero/coyote-fence-sunset.mp4")} />`
   instead of `clips/coyote.mp4`).
3. If the new clip is shorter/longer than the 14-s slot, either trim with
   `startFrom`/`endAt` or adjust `ACT2_SCENARIO_SECONDS` in
   `calculate-main-metadata.ts` (all acts auto-resize).
4. Re-run `make video-render`. No Playwright recorder run needed; Phase 5
   iteration loop is optional for v2 since the field footage is pre-validated
   by human eyeball.

---

## Section 3 — Submission Decision Tree

```
Sun 2026-04-26, T-minus:
│
├─ 24 hours (Sat 18:00 EST): Hybrid (v2) edit complete?
│   ├─ YES → Submit v2. File v1 as "dev artifact" in repo (still in
│   │        docs/demo-assets/video/skyherd-demo-v1-sim-first.mp4).
│   └─ NO  → Was Fri shoot successful?
│        ├─ YES → Last-chance: 6-hr emergency edit Sat 18:00 → Sun 00:00.
│        │         Target Sun 18:00 EST submit.
│        └─ NO  → Submit v1 (sim-first). Already ready. No further work.
│
├─ 12 hours (Sun 06:00 EST): Freeze decision. Whichever video is rendered
│                             at this point wins. Ship what you have.
│
├─  6 hours (Sun 12:00 EST): Upload chosen MP4 to YouTube unlisted.
│                             Fill Devpost form (summary, repo URL, tags).
│
├─  2 hours (Sun 16:00 EST): git tag v1.0-submission, push to origin.
│
└─  0 hours (Sun 18:00 EST): Hit Submit on Devpost. Screenshot confirmation.
                              (Hard deadline Sun 20:00 EST — 2 hr buffer.)
```

---

## Section 4 — Operating the Pipeline

### Make targets

| Target | Stage | Runtime | Description |
|--------|-------|---------|-------------|
| `make video-pipeline` | End-to-end | ~60 min | Audio → clips → composition → iteration → render → package. |
| `make video-iterate` | QA loop | ~30 min | Dual-vision iteration loop (Claude + Gemini, cap 6). |
| `make video-render` | Final | ~10 min | 1080p render + loudnorm to -16 LUFS. |
| `make video-record-clips` | Clips only | ~5 min | Headless Playwright re-record of 9 dashboard clips (needs `make record-ready`). |
| `make record-ready` | Preflight | instant | Builds dashboard + starts `:8000` for the Playwright recorder to talk to. |

### Quickstart for judges

```bash
git clone https://github.com/george11642/skyherd-engine && cd skyherd-engine
uv sync --all-extras && (cd web && pnpm install && pnpm run build) && (cd remotion-video && pnpm install)
make video-pipeline   # → docs/demo-assets/video/skyherd-demo-v1-sim-first.mp4
```

### Troubleshooting

- **`ELEVENLABS_API_KEY missing`** → stage in `.env.local` at repo root (or export
  in shell). The renderer falls back to `piper` → `espeak-ng` if the key is
  absent, but the voice quality drops. See `scripts/render_vo_phase1.sh` for the
  fallback chain.
- **`Playwright chromium not installed`** → `uv run --with playwright playwright install chromium`.
  The recorder pins to Chromium; Firefox/WebKit are not supported.
- **`render:proof out of memory`** → pass `--concurrency=1` to the Remotion
  render step (edit `remotion-video/package.json` `render` script). Default
  concurrency can peg a 16 GB box on the 5400-frame composition.
- **Remotion 4.x deprecation warnings** → noted in Known Limitations, non-blocking.
  Migration to `@remotion/media` is a post-submission follow-up.
- **Dashboard `:8000` already in use** → `make record-ready` hard-codes port 8000.
  Kill the conflicting process (`lsof -i :8000`) before running the recorder.
- **Scenario-complete SSE timeout during recording** → the recorder waits up
  to 180 s for `event: scenario_complete`. If the sim stalls, check
  `uv run skyherd-demo play coyote --seed 42` in isolation first.

---

## Section 5 — Provenance & Attestations

- **Voiceover** — all 10 MP3s generated by ElevenLabs (voice ID
  `pNInz6obpgDQGcFmaJgB`, model `eleven_multilingual_v2`). The Wes persona
  re-voices George's on-camera script words; no third-party vocal sample is
  cloned. Usage falls under ElevenLabs' standard commercial TOS.
- **Background music** — `bgm-main.mp3` is procedurally synthesized via
  `ffmpeg lavfi` (brown-noise + echo + lowpass + loudnorm). No external
  audio asset is used. See `remotion-video/public/music/SOURCE.md` for the
  exact generation command. Will be swapped for a properly-licensed track
  pre-submission if time allows.
- **Sound effects** — 6 MP3s, all procedurally synthesized via `ffmpeg lavfi`
  (sine/noise/envelope chains). No third-party SFX library used.
- **Dashboard footage** — recorded headless against the SkyHerd simulator
  at `seed=42`. All visible data is from the deterministic sim; no real
  rancher PII is shown.
- **Determinism** — `make video-pipeline` is re-runnable byte-stable from
  `seed=42`. Remotion render outputs are stable within <0.5% frame delta
  (encoder non-determinism only). Sim event stream is verified byte-stable
  by `tests/test_determinism_e2e.py` (after wall-clock sanitization).
- **License** — all original code MIT (matches parent repo). All
  audio/video assets are either ElevenLabs-generated (per their TOS) or
  `ffmpeg` / Playwright-synthesized (no copyright encumbrance).

---

## Appendix A — File Inventory

To regenerate this list:

```bash
git -C /home/george/projects/active/skyherd-engine \
    log --format=%H aa8baa6f..HEAD --stat -- \
    remotion-video/ scripts/record_dashboard.py scripts/render_vo_phase1.sh \
    scripts/video_iterate.sh
```

Phases 1-4 (commit `aa8baa6f`) added these tracked files (excluding
`node_modules/` and `out/`):

```
.gitignore                                              (modified)
Makefile                                                (modified — +video-record-clips)
docs/REPLAY_LOG.md                                      (modified)
remotion-video/.gitignore                               (new)
remotion-video/.prettierrc                              (new)
remotion-video/README.md                                (new)
remotion-video/eslint.config.mjs                        (new)
remotion-video/package.json                             (new)
remotion-video/pnpm-lock.yaml                           (new)
remotion-video/public/clips/ambient_30x_synthesis.mp4   (new, ~1.8 MB)
remotion-video/public/clips/ambient_establish.mp4       (new, ~1.7 MB)
remotion-video/public/clips/attest_verify.mp4           (new, ~1.1 MB)
remotion-video/public/clips/calving.mp4                 (new, ~1.9 MB)
remotion-video/public/clips/coyote.mp4                  (new, ~1.7 MB)
remotion-video/public/clips/fresh_clone.mp4             (new, ~1.0 MB)
remotion-video/public/clips/sick_cow.mp4                (new, ~1.7 MB)
remotion-video/public/clips/storm.mp4                   (new, ~1.8 MB)
remotion-video/public/clips/water.mp4                   (new, ~1.8 MB)
remotion-video/public/music/SOURCE.md                   (new)
remotion-video/public/music/bgm-main.mp3                (new, ~1.4 MB)
remotion-video/public/sfx/coyote-distant.mp3            (new)
remotion-video/public/sfx/drone-whir.mp3                (new)
remotion-video/public/sfx/keyboard-type.mp3             (new)
remotion-video/public/sfx/paper-rustle.mp3              (new)
remotion-video/public/sfx/radio-static.mp3              (new)
remotion-video/public/sfx/ui-tick.mp3                   (new)
remotion-video/public/voiceover/envelope.json           (new)
remotion-video/public/voiceover/wes-attest.mp3          (new)
remotion-video/public/voiceover/wes-calving.mp3         (new)
remotion-video/public/voiceover/wes-close.mp3           (new)
remotion-video/public/voiceover/wes-coyote.mp3          (new)
remotion-video/public/voiceover/wes-establish.mp3       (new)
remotion-video/public/voiceover/wes-george-hook.mp3     (new)
remotion-video/public/voiceover/wes-sick-cow.mp3        (new)
remotion-video/public/voiceover/wes-storm.mp3           (new)
remotion-video/public/voiceover/wes-synthesis.mp3       (new)
remotion-video/public/voiceover/wes-why.mp3             (new)
remotion-video/remotion.config.ts                       (new)
remotion-video/src/Main.tsx                             (new, 202 LOC)
remotion-video/src/Root.tsx                             (new, 63 LOC)
remotion-video/src/acts/Act1Hook.tsx                    (new, 447 LOC)
remotion-video/src/acts/Act2Demo.tsx                    (new, 683 LOC)
remotion-video/src/acts/Act3Close.tsx                   (new, 457 LOC)
remotion-video/src/compositions/calculate-main-metadata.ts (new, 166 LOC)
remotion-video/src/index.css                            (new)
remotion-video/src/index.ts                             (new)
remotion-video/tsconfig.json                            (new)
scripts/record_dashboard.py                             (new, 779 LOC)
scripts/render_vo_phase1.sh                             (new, 78 LOC)
```

Phase 5 iteration commits + Phase 6 final commit (`{FINAL_COMMIT_HASH}`) add
`scripts/video_iterate.sh`, any iteration-specific fixes to the `.tsx` files,
and the final normalized MP4 at
`docs/demo-assets/video/skyherd-demo-v1-sim-first.mp4`.
