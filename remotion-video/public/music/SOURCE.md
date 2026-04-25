# BGM Source

## `bgm-main.mp3`

- **Duration**: ~60 s (measured 61.05 s)
- **Format**: 44.1 kHz stereo MP3, 192 kbps
- **Loudness**: integrated -18 LUFS (via ffmpeg `loudnorm=I=-18:TP=-1:LRA=11`)
- **Provenance**: **SYNTHESIZED PLACEHOLDER** — generated on 2026-04-24 via ffmpeg
  `lavfi` brown-noise + echo + lowpass + fade-in/out chain (no external download):
  ```
  ffmpeg -f lavfi -i "anoisesrc=color=brown:duration=60:amplitude=0.3" \
         -af "aecho=0.8:0.9:1000:0.3,lowpass=f=1200,volume=0.4, \
              afade=t=in:st=0:d=2,afade=t=out:st=58:d=2, \
              loudnorm=I=-18:TP=-1:LRA=11" \
         -ac 2 -ar 44100 -c:a libmp3lame -b:a 192k bgm-main.mp3
  ```
- **License**: N/A (procedurally synthesized, no external asset used)
- **Status**: placeholder for Phase 1 of the autonomous demo-video pipeline. The
  track is an ambient pink/brown-noise drone suitable for ducked underlay.
  Before final submission this SHOULD be swapped for a proper cinematic
  ambient/pastoral cue from one of:
  - Pixabay Music (CC0, no attribution)
  - YouTube Audio Library (royalty-free, check license file)
  - Incompetech / Kevin MacLeod (CC-BY, add attribution to end card)
  Candidate tracks listed in `/home/george/.claude/plans/make-a-plan-to-moonlit-reddy.md`
  Phase 1, "Background music" section.

Replace this file in-place and keep the filename — the Remotion composition
reads `staticFile("music/bgm-main.mp3")` unconditionally.

## Phase E4 — AudioCraft MusicGen upgrade attempt (2026-04-24)

**Goal**: replace brown-noise placeholder with AI-generated cinematic ambient
via Meta's AudioCraft (MusicGen).

**Outcome**: **kept the placeholder** — `audiocraft` install failed in our uv
environment due to an irreconcilable PyTorch/typer dependency conflict:

```
audiocraft >=1.2.0 depends on torch==2.1.0
project depends on torch>=2.4,<3
audiocraft <1.2.0 depends on typer>=0.3.0,<0.8.0
project depends on typer>=0.12

→ resolution failed
```

We could `--frozen` past the lockfile or create a separate venv to generate
the track out-of-tree, but neither is justified before submission. The current
brown-noise bed sits comfortably under the VO bus thanks to the ducker
(-16 LUFS target after `loudnorm` in `make video-render`), so the upgrade
was deferred.

**Status**: placeholder retained. No track swap. Post-submission upgrade
candidate via either Pixabay Music (CC0) or a separate Conda env for
`audiocraft`.

