# VO auto-editor polish log

## Phase E3 — auto-editor silence trim attempt (2026-04-24)

**Tool**: `auto-editor` 29.3.1, installed via `uv add auto-editor`.

**Run**:
```
auto-editor <vo-*.mp3> --edit "audio:threshold=0.04" --margin "0.3sec" --output <tight>.mp3 --no-open
```

**Outcome**: **All 18 cues rejected** — Antoni ElevenLabs renders are already
tightly paced (worst cut was 4.7% on `vo-bridge` and `vo-market`; mean ~1.7%).
The plan's accept threshold was >10% reduction with no quality regression.

| Cue | Orig (s) | Tight (s) | %cut | Decision |
|---|---|---|---|---|
| vo-bridge-B | 1.99 | 1.99 | 0.0% | reject |
| vo-bridge | 8.36 | 7.97 | 4.7% | reject |
| vo-calving | 5.69 | 5.67 | 0.5% | reject |
| vo-close-C | 6.71 | 6.66 | 0.8% | reject |
| vo-close-final | 5.85 | 5.77 | 1.3% | reject |
| vo-close-substance | 12.85 | 12.51 | 2.6% | reject |
| vo-coyote | 3.66 | 3.60 | 1.4% | reject |
| vo-depth-C | 12.49 | 12.46 | 0.2% | reject |
| vo-hook-C | 7.97 | 7.86 | 1.3% | reject |
| vo-intro-B | 16.25 | 16.01 | 1.4% | reject |
| vo-intro | 14.45 | 14.13 | 2.2% | reject |
| vo-market | 21.03 | 20.04 | 4.7% | reject |
| vo-mesh | 22.60 | 22.33 | 1.2% | reject |
| vo-opus-C | 24.06 | 23.38 | 2.8% | reject |
| vo-sick-cow | 6.50 | 6.43 | 1.2% | reject |
| vo-storm | 3.66 | 3.63 | 0.7% | reject |
| vo-story-C | 27.66 | 27.38 | 1.0% | reject |
| vo-synthesis-C | 7.97 | 7.97 | 0.0% | reject |

**Conclusion**: original Antoni MP3s retained. No durations changed — Phase E1
caption transcription uses the originals as-is, and `calculateMainMetadata`
doesn't need re-measuring.

**Tight candidates** still live at `/tmp/vo-tight/` for reference; not committed.
