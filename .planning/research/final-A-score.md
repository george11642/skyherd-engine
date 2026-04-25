# SkyHerd iter-99-A Score Report

**Generated:** 2026-04-25T12:34:47.807648+00:00

---

## Aggregate Scores

| Source | Impact (30%) | Demo (25%) | Opus (25%) | Depth (20%) | **Aggregate** |
|--------|-------------|------------|------------|-------------|---------------|
| Opus stills | 6.50 | 6.00 | 6.80 | 7.00 | **6.5500** |
| Gemini critique | 9.50 | 8.50 | 9.50 | 10.00 | **9.3500** |
| **Final (avg)** | **8.00** | **7.25** | **8.15** | **8.50** | **7.9500** |

---

## Ship Gate

Status: ❌ FAILS

- Aggregate 7.9500 < 9.46
- Impact 8.00 < 9.5
- Demo 7.25 < 9.5
- Opus 8.15 < 8.5
- Depth 8.50 < 10.0

## Plateau Detection

Status: 🔄 CONTINUING

Reason: Mean 8.0417 < threshold 9.5

### Iteration History

| Iter | Opus | Gemini | Final |
|------|------|--------|-------|
| 3 | 6.6500 | 9.7500 | 8.2000 |
| 4 | 7.1500 | 9.5250 | 8.3375 |
| 5 | 6.9050 | 9.3500 | 8.1275 |
| 6 | 7.1500 | 9.1000 | 8.1250 |
| 7 | 6.4750 | 9.6250 | 8.0500 |
| 99 | 6.5500 | 9.3500 | 7.9500 |

## Top Fix Suggestions

### Fix 1 (priority 1)

- **Frame:** `f0001.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Tighten opening: drop the first ~1s hold on 'Everyone thinks' alone — start with the full first line revealing word-by-word at 8-10 chars/sec so by 2.5s the contrarian beat 'They don't.' has already landed.

### Fix 2 (priority 2)

- **Frame:** `f0011.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** When 'They need a nervous system.' appears (~5s), animate a faint background of 5 connected agent nodes pulsing — gives judges an immediate visual hook tying the metaphor to the SkyHerd 5-agent mesh and previewing depth.

### Fix 3 (priority 3)

- **Frame:** `f0006.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Remove or reposition the duplicate karaoke caption pill — either hide it during Act 1 hook (text is already large) or replace with a stat chip like '$4.17/wk · 1106 tests' to seed depth/impact signals from second 0.
