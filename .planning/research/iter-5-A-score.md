# SkyHerd iter-5-A Score Report

**Generated:** 2026-04-25T10:31:02.371661+00:00

---

## Aggregate Scores

| Source | Impact (30%) | Demo (25%) | Opus (25%) | Depth (20%) | **Aggregate** |
|--------|-------------|------------|------------|-------------|---------------|
| Opus stills | 6.80 | 6.50 | 7.20 | 7.20 | **6.9050** |
| Gemini critique | 9.50 | 8.50 | 9.50 | 10.00 | **9.3500** |
| **Final (avg)** | **8.15** | **7.50** | **8.35** | **8.60** | **8.1275** |

---

## Ship Gate

Status: ❌ FAILS

- Aggregate 8.1275 < 9.46
- Impact 8.15 < 9.5
- Demo 7.50 < 9.5
- Opus 8.35 < 8.5
- Depth 8.60 < 10.0

## Plateau Detection

Status: 🔄 CONTINUING

Reason: Mean 8.2217 < threshold 9.5

### Iteration History

| Iter | Opus | Gemini | Final |
|------|------|--------|-------|
| 3 | 6.6500 | 9.7500 | 8.2000 |
| 4 | 7.1500 | 9.5250 | 8.3375 |
| 5 | 6.9050 | 9.3500 | 8.1275 |

## Top Fix Suggestions

### Fix 1 (priority 1)

- **Frame:** `f0001.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Eliminate the blank opening frame; start 'Everyone thinks' reveal at frame 0 with a fast 6-frame fade-in so the hook lands in the first 0.25s instead of 0.5s

### Fix 2 (priority 2)

- **Frame:** `f0011.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Increase contrast and weight on the 'They need a nervous system' payoff line — use the deep-green primary or a saturated amber instead of low-contrast tan, and add a subtle scale-up keyframe to land the punchline

### Fix 3 (priority 3)

- **Frame:** `f0005.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Tighten the meta-loop caption-box reveal: the 'Everyone' / 'Everyone thinks' caption box appears AFTER the main text it captions, undermining the meta-loop story. Sync the caption-box word to appear simultaneously with each main-text word reveal so the meta-loop ('Opus styled these captions live') is legible in 6s
