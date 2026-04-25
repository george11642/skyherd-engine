# SkyHerd iter-3-A Score Report

**Generated:** 2026-04-25T08:55:47.914475+00:00

---

## Aggregate Scores

| Source | Impact (30%) | Demo (25%) | Opus (25%) | Depth (20%) | **Aggregate** |
|--------|-------------|------------|------------|-------------|---------------|
| Opus stills | 6.50 | 6.20 | 7.00 | 7.00 | **6.6500** |
| Gemini critique | 10.00 | 9.00 | 10.00 | 10.00 | **9.7500** |
| **Final (avg)** | **8.25** | **7.60** | **8.50** | **8.50** | **8.2000** |

---

## Ship Gate

Status: ❌ FAILS

- Aggregate 8.2000 < 9.46
- Impact 8.25 < 9.5
- Demo 7.60 < 9.5
- Depth 8.50 < 10.0

## Plateau Detection

Status: 🔄 CONTINUING

Reason: Only 1/3 iterations available

### Iteration History

| Iter | Opus | Gemini | Final |
|------|------|--------|-------|
| 3 | 6.6500 | 9.7500 | 8.2000 |

## Top Fix Suggestions

### Fix 1 (priority 1)

- **Frame:** `f0001.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Eliminate the blank opening frame. Start 'Everyone thinks' fade-in at frame 0 (t=0) instead of ~t=0.5s. Compress total hook line reveals so 'They need a nervous system' lands by 5.0s, freeing 1s for a b-roll cut (rancher silhouette at dawn or dead-calf stat) before the 6s mark.

### Fix 2 (priority 2)

- **Frame:** `f0005.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Remove the redundant lower karaoke caption box entirely OR replace it with a single quantified stat overlay (e.g. '$2.4B/yr lost to undetected herd events') — the duplicated word echo currently adds visual noise without information density and hurts Demo + Impact scores.

### Fix 3 (priority 3)

- **Frame:** `f0006.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Add a faint background layer behind the text: muted ranch photo (fenceline at dusk) at 8-12% opacity, or animated agent-mesh nodes pulsing. Pure cream background reads as Keynote slide and undermines Technical Depth + Opus Use perception during the most-watched 6 seconds.
