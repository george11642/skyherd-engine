# SkyHerd iter-2-B Score Report

**Generated:** 2026-04-25T11:05:50.384396+00:00

---

## Aggregate Scores

| Source | Impact (30%) | Demo (25%) | Opus (25%) | Depth (20%) | **Aggregate** |
|--------|-------------|------------|------------|-------------|---------------|
| Opus stills | 6.75 | 6.25 | 6.75 | 7.15 | **6.7050** |
| Gemini critique | 9.50 | 8.50 | 9.50 | 9.50 | **9.2500** |
| **Final (avg)** | **8.12** | **7.38** | **8.12** | **8.32** | **7.9775** |

---

## Ship Gate

Status: ❌ FAILS

- Aggregate 7.9775 < 9.46
- Impact 8.12 < 9.5
- Demo 7.38 < 9.5
- Opus 8.12 < 8.5
- Depth 8.32 < 10.0

## Plateau Detection

Status: 🔄 CONTINUING

Reason: Only 2/3 iterations available

### Iteration History

| Iter | Opus | Gemini | Final |
|------|------|--------|-------|
| 1 | 7.0050 | 9.2250 | 8.1150 |
| 2 | 6.7050 | 9.2500 | 7.9775 |

## Top Fix Suggestions

### Fix 1 (priority 1)

- **Frame:** `f0001.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Eliminate the blank opening frame. Start the price reveal at frame 0 or precede with a 0.5s pain-establishing image (coyote silhouette, dead calf headline, or '$1,800 lost per coyote kill' stat) to establish stakes BEFORE showing price.

### Fix 2 (priority 2)

- **Frame:** `f0005.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Remove the redundant lower gray caption pill that duplicates '$4.17' / 'a week'. The hero number is already large and clear; the duplicate creates visual noise and looks like a captioning bug. Reserve that lower slot for a single impact stat like 'vs $14k/yr ranch hand'.

### Fix 3 (priority 3)

- **Frame:** `f0011.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Promote '10,000-acre ranch' to appear simultaneously with $4.17 (not 5s later) and add a contrast anchor like '$4.17/wk replaces $14,000/yr night-watch hand' to instantly quantify impact and meet the Impact-10 anchor (quantified stakes in <30s).
