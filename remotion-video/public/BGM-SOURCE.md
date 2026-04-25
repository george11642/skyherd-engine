# BGM Source Disclosure

Generated: 2026-04-24 (Phase 6 Stage 1)

---

## `music/bgm-main.mp3` — Primary BGM (180s)

**Track**: "Time" by Hans Zimmer  
**Source**: Inception Original Motion Picture Soundtrack (2010, Reprise Records / WaterTower Music)  
**YouTube ID**: `c56t7upa8Bk`  
**Trim**: 1:35–4:35 (95s–275s of the original 4:35 track)  
**Processing**: fade-in 3s, fade-out 3s, loudnorm I=-16:TP=-1:LRA=11  
**Format**: 44.1 kHz stereo, 192 kbps MP3  
**Duration**: 180.01s  
**Gemini Score**: 8.5/10 (emotional arc match, build quality, screenshot moment synergy)

**Copyright status**: Copyrighted. Used per locked-decision-#8 — YouTube Content ID
auto-flag risk accepted. Will swap to MusicGen-generated audio post-launch if takedown
issued. MusicGen Path A was blocked: torch==2.1.0 (required by audiocraft) is no longer
available from PyPI (minimum now 2.2.0), and project venv's torchaudio requires
libcudart.so.13 which is not installed on this machine.

**Winning MusicGen prompt** (for future regeneration when toolchain is available):
```
"cinematic neo-noir score, modern Hans Zimmer x Daft Punk, slow build, tense bass drone,
percussive crescendo at 60s, drop into triumphant lead at 120s, mastered for film, 180 seconds"
```
Gemini rated this prompt 9.5/10 — highest of 5 candidates.

---

## `music/bgm-bass.mp3` — Bass Stem

Frequency-split from `bgm-main.mp3` via ffmpeg:
- LPF at 250 Hz
- 80 Hz +6 dB boost
- volume ×1.4
- Used for Remotion ducking: stays under VO bus, minimal duck

**License**: Derivative of copyrighted work (same as bgm-main.mp3).

---

## `music/bgm-perc.mp3` — Percussion Stem

Frequency-split from `bgm-main.mp3` via ffmpeg:
- HPF at 3000 Hz
- 8 kHz +4 dB shelf (cymbal/strings transient emphasis)
- Used for Remotion ducking: moderate duck during VO

**License**: Derivative of copyrighted work (same as bgm-main.mp3).

---

## `music/bgm-lead.mp3` — Lead Stem

Frequency-split from `bgm-main.mp3` via ffmpeg:
- BPF 300 Hz – 3000 Hz (piano and strings melody range)
- 1 kHz +3 dB presence boost
- Used for Remotion ducking: most aggressive duck during VO, recovers on stings

**License**: Derivative of copyrighted work (same as bgm-main.mp3).

---

## `sfx/sting-open.mp3` — Cold Open Punch (1.83s)

**Source**: Synthesized via ffmpeg lavfi (55 Hz sub sine + white noise burst + 880 Hz shimmer)  
**License**: Unencumbered (procedurally synthesized, no external asset)

---

## `sfx/sting-scenario1.mp3` — Scenario 1 Climax / Coyote Alert (1.54s)

**Source**: Synthesized via ffmpeg lavfi (220 Hz + 330 Hz vibrato tension chord)  
**License**: Unencumbered (procedurally synthesized)

---

## `sfx/sting-scenario2.mp3` — Scenario 2 Climax / Sick Cow (1.83s)

**Source**: Synthesized via ffmpeg lavfi (110 Hz + 165 Hz low somber chord)  
**License**: Unencumbered (procedurally synthesized)

---

## `sfx/sting-cost.mp3` — Cost Ticker Reveal (0.68s)

**Source**: Synthesized via ffmpeg lavfi (1200/1400/1800 Hz ascending blip sequence)  
**License**: Unencumbered (procedurally synthesized)

---

## `sfx/sting-meta.mp3` — Meta-Loop Reveal (1.83s)

**Source**: Synthesized via ffmpeg lavfi (G4/B4/D5 = G major chord stab, 392/494/587 Hz)  
**License**: Unencumbered (procedurally synthesized)

---

## `sfx/sting-wordmark.mp3` — Wordmark Drop (2.04s)

**Source**: Synthesized via ffmpeg lavfi (60 Hz sub boom + 1200 Hz ring)  
**License**: Unencumbered (procedurally synthesized)

---

## Scoring Summary

See `out/bgm-scores.json` for full Gemini scoring of all 5 MusicGen prompts and 3 copyrighted track candidates.
