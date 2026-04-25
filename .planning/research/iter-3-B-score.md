# SkyHerd iter-3-B Score Report

**Generated:** 2026-04-25T11:17:48.622214+00:00

---

## Aggregate Scores

| Source | Impact (30%) | Demo (25%) | Opus (25%) | Depth (20%) | **Aggregate** |
|--------|-------------|------------|------------|-------------|---------------|
| Opus stills | 7.10 | 5.75 | 6.90 | 6.50 | **6.5925** |
| Gemini critique | 9.80 | 8.00 | 9.00 | 9.80 | **9.1500** |
| **Final (avg)** | **8.45** | **6.88** | **7.95** | **8.15** | **7.8712** |

---

## Ship Gate

Status: ❌ FAILS

- Aggregate 7.8712 < 9.46
- Impact 8.45 < 9.5
- Demo 6.88 < 9.5
- Opus 7.95 < 8.5
- Depth 8.15 < 10.0

## Plateau Detection

Status: 🔄 CONTINUING

Reason: Mean 7.9879 < threshold 9.5

### Iteration History

| Iter | Opus | Gemini | Final |
|------|------|--------|-------|
| 1 | 7.0050 | 9.2250 | 8.1150 |
| 2 | 6.7050 | 9.2500 | 7.9775 |
| 3 | 6.5925 | 9.1500 | 7.8712 |

## Top Fix Suggestions

### Fix 1 (priority 1)

- **Frame:** `f0006.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Remove the duplicate redundant '$4.17' caption box at bottom of frame; if karaoke captions are needed, gate them so they never echo the main hero typography text. Move captions to a single bottom-third lockup that displays narration only.

### Fix 2 (priority 2)

- **Frame:** `f0001.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Replace the blank opening 0-0.5s with a visceral problem cold-open: a coyote silhouette at fence at dusk, or a rancher's phone alert sound, before the $4.17 typographic reveal. Establishes pain before price per Impact rubric anchor.

### Fix 3 (priority 3)

- **Frame:** `f0009.jpg`
- **File:** `remotion-video/src/captions/karaokeCaptions.ts`
- **Change:** Fix caption segmentation so partial-word frames like 'a' never render alone; chunk by full word or phrase tokens (min 2 chars or whole word) to avoid the glitchy single-letter caption frame.
