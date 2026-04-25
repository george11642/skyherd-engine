# SkyHerd iter-99-C Score Report

**Generated:** 2026-04-25T12:07:49.227467+00:00

---

## Aggregate Scores

| Source | Impact (30%) | Demo (25%) | Opus (25%) | Depth (20%) | **Aggregate** |
|--------|-------------|------------|------------|-------------|---------------|
| Opus stills | 8.20 | 8.00 | 6.50 | 8.30 | **7.7450** |
| Gemini critique | 10.00 | 9.00 | 9.50 | 10.00 | **9.6250** |
| **Final (avg)** | **9.10** | **8.50** | **8.00** | **9.15** | **8.6850** |

---

## Ship Gate

Status: ❌ FAILS

- Aggregate 8.6850 < 9.46
- Impact 9.10 < 9.5
- Demo 8.50 < 9.5
- Opus 8.00 < 8.5
- Depth 9.15 < 10.0

## Plateau Detection

Status: 🔄 CONTINUING

Reason: Mean 8.4817 < threshold 9.5

### Iteration History

| Iter | Opus | Gemini | Final |
|------|------|--------|-------|
| 1 | 7.4750 | 8.9750 | 8.2250 |
| 2 | 7.6250 | 9.2500 | 8.4375 |
| 3 | 7.3750 | 9.2700 | 8.3225 |
| 99 | 7.7450 | 9.6250 | 8.6850 |

## Top Fix Suggestions

### Fix 1 (priority 1)

- **Frame:** `f0008.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Replace harsh cream-background cut with a 6-frame crossfade or hold dark theme through the $4.17 reveal to maintain visual continuity; cream theme should be reserved for a deliberate act break, not mid-hook

### Fix 2 (priority 2)

- **Frame:** `f0003.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Crossfade dashboard underlay to <15% opacity OR delay it until after '0 sleep' text exits; current overlap creates competing focal points

### Fix 3 (priority 3)

- **Frame:** `f0007.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Trim caption stack: drop 'UNM senior, Drone-Op' here and reveal credentials in a later scene; let '$1.8B/yr' breathe alone for at least 1.0s to land the stake
