# SkyHerd iter-7-A Score Report

**Generated:** 2026-04-25T10:58:38.415232+00:00

---

## Aggregate Scores

| Source | Impact (30%) | Demo (25%) | Opus (25%) | Depth (20%) | **Aggregate** |
|--------|-------------|------------|------------|-------------|---------------|
| Opus stills | 6.50 | 6.00 | 6.50 | 7.00 | **6.4750** |
| Gemini critique | 10.00 | 9.00 | 9.50 | 10.00 | **9.6250** |
| **Final (avg)** | **8.25** | **7.50** | **8.00** | **8.50** | **8.0500** |

---

## Ship Gate

Status: ❌ FAILS

- Aggregate 8.0500 < 9.46
- Impact 8.25 < 9.5
- Demo 7.50 < 9.5
- Opus 8.00 < 8.5
- Depth 8.50 < 10.0

## Plateau Detection

Status: 🔄 CONTINUING

Reason: Mean 8.1008 < threshold 9.5

### Iteration History

| Iter | Opus | Gemini | Final |
|------|------|--------|-------|
| 3 | 6.6500 | 9.7500 | 8.2000 |
| 4 | 7.1500 | 9.5250 | 8.3375 |
| 5 | 6.9050 | 9.3500 | 8.1275 |
| 6 | 7.1500 | 9.1000 | 8.1250 |
| 7 | 6.4750 | 9.6250 | 8.0500 |

## Top Fix Suggestions

### Fix 1 (priority 1)

- **Frame:** `f0001.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Eliminate the blank opening frame: start 'Everyone thinks' fade-in at frame 0 (t=0) rather than t≈0.5s. Every half-second of the first 6s is critical for impact scoring.

### Fix 2 (priority 2)

- **Frame:** `f0011.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Move the 'They need a nervous system.' reveal earlier (target ~4.0s instead of ~5.5s) so the full thesis lands within the 6s hook window. Consider replacing the redundant caption pill with a concrete stat (e.g. '$4.17/week · 1106 tests') to seed credibility immediately.

### Fix 3 (priority 3)

- **Frame:** `f0005.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Remove or restyle the bottom caption pill that mirrors the headline. Replace with a small Opus 4.7 attribution badge ('Captions styled by Opus 4.7') to seed the meta-loop differentiator from second 1.
