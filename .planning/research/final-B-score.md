# SkyHerd iter-99-B Score Report

**Generated:** 2026-04-25T12:34:52.980101+00:00

---

## Aggregate Scores

| Source | Impact (30%) | Demo (25%) | Opus (25%) | Depth (20%) | **Aggregate** |
|--------|-------------|------------|------------|-------------|---------------|
| Opus stills | 7.20 | 6.50 | 6.90 | 6.90 | **6.8900** |
| Gemini critique | 10.00 | 9.00 | 8.50 | 10.00 | **9.3750** |
| **Final (avg)** | **8.60** | **7.75** | **7.70** | **8.45** | **8.1325** |

---

## Ship Gate

Status: ❌ FAILS

- Aggregate 8.1325 < 9.46
- Impact 8.60 < 9.5
- Demo 7.75 < 9.5
- Opus 7.70 < 8.5
- Depth 8.45 < 10.0

## Plateau Detection

Status: 🔄 CONTINUING

Reason: Mean 7.9937 < threshold 9.5

### Iteration History

| Iter | Opus | Gemini | Final |
|------|------|--------|-------|
| 1 | 7.0050 | 9.2250 | 8.1150 |
| 2 | 6.7050 | 9.2500 | 7.9775 |
| 3 | 6.5925 | 9.1500 | 7.8712 |
| 99 | 6.8900 | 9.3750 | 8.1325 |

## Top Fix Suggestions

### Fix 1 (priority 1)

- **Frame:** `f0002.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Add a brief connective micro-caption (e.g., 'vs.' or '→ SkyHerd') between $1,800 and $4.17 reveal to make problem→solution framing explicit within the opening 6s

### Fix 2 (priority 2)

- **Frame:** `f0001.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Match drop-shadow treatment between $1,800 and $4.17 (either both crisp or both shadowed) for typographic consistency

### Fix 3 (priority 3)

- **Frame:** `f0011.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Consider reinforcing Opus 4.7 attribution very early — even a tiny 'powered by Opus 4.7' kicker under '24/7 nervous system' would lift Opus score in the hook window
