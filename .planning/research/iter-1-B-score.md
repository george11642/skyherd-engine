# SkyHerd iter-1-B Score Report

**Generated:** 2026-04-25T10:46:14.939400+00:00

---

## Aggregate Scores

| Source | Impact (30%) | Demo (25%) | Opus (25%) | Depth (20%) | **Aggregate** |
|--------|-------------|------------|------------|-------------|---------------|
| Opus stills | 7.10 | 6.25 | 7.25 | 7.50 | **7.0050** |
| Gemini critique | 9.50 | 9.00 | 8.50 | 10.00 | **9.2250** |
| **Final (avg)** | **8.30** | **7.62** | **7.88** | **8.75** | **8.1150** |

---

## Ship Gate

Status: ❌ FAILS

- Aggregate 8.1150 < 9.46
- Impact 8.30 < 9.5
- Demo 7.62 < 9.5
- Opus 7.88 < 8.5
- Depth 8.75 < 10.0

## Plateau Detection

Status: 🔄 CONTINUING

Reason: Only 1/3 iterations available

### Iteration History

| Iter | Opus | Gemini | Final |
|------|------|--------|-------|
| 1 | 7.0050 | 9.2250 | 8.1150 |

## Top Fix Suggestions

### Fix 1 (priority 1)

- **Frame:** `f0005.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Remove the secondary gray caption-preview pill box at the bottom of the frame. It appears to be a leftover dev/debug overlay duplicating the main text. If it's intentional styling, either move it off-screen during this act or restyle it as a clearly-distinct UI element (e.g., a tagged 'LIVE' chip) so it doesn't read as a duplicate.

### Fix 2 (priority 2)

- **Frame:** `f0001.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Eliminate the 0.5s blank opening — start the '$4.17' spring-in at frame 0 with a snappy scale-from-1.4-to-1.0 + opacity, so the hook lands in the first 200ms. Every blank frame in the first 3s costs Impact.

### Fix 3 (priority 3)

- **Frame:** `f0012.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Tighten the stack reveal cadence so '$4.17 a week' + 'protects 10,000-acre ranch' lands together by ~2.5s, not 6s. Consider replacing '24/7 nervous system' (vague metaphor) with a concrete number like '5 agents · 1,106 tests' to add depth and Opus credibility into the hook itself.
