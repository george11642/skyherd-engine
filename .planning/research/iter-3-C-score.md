# SkyHerd iter-3-C Score Report

**Generated:** 2026-04-25T11:33:20.174108+00:00

---

## Aggregate Scores

| Source | Impact (30%) | Demo (25%) | Opus (25%) | Depth (20%) | **Aggregate** |
|--------|-------------|------------|------------|-------------|---------------|
| Opus stills | 7.80 | 7.40 | 6.50 | 7.80 | **7.3750** |
| Gemini critique | 9.40 | 8.20 | 9.60 | 10.00 | **9.2700** |
| **Final (avg)** | **8.60** | **7.80** | **8.05** | **8.90** | **8.3225** |

---

## Ship Gate

Status: ❌ FAILS

- Aggregate 8.3225 < 9.46
- Impact 8.60 < 9.5
- Demo 7.80 < 9.5
- Opus 8.05 < 8.5
- Depth 8.90 < 10.0

## Plateau Detection

Status: 🔄 CONTINUING

Reason: Mean 8.3283 < threshold 9.5

### Iteration History

| Iter | Opus | Gemini | Final |
|------|------|--------|-------|
| 1 | 7.4750 | 8.9750 | 8.2250 |
| 2 | 7.6250 | 9.2500 | 8.4375 |
| 3 | 7.3750 | 9.2700 | 8.3225 |

## Top Fix Suggestions

### Fix 1 (priority 1)

- **Frame:** `f0001.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Replace empty opening frame with an immediate visceral cold-open: a coyote-at-fence b-roll still or a stat slam ('1 rancher, 10,000 acres, 0 sleep') before the 'I'm George' caption appears. Move George intro to ~1.5s in.

### Fix 2 (priority 2)

- **Frame:** `f0011.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Stagger the text stack: fade out 'I'm George, UNM senior, Drone-Op' caption before introducing '10,000-acre ranch / Every fence' so only 2-3 elements are on screen simultaneously. Reduces cognitive load.

### Fix 3 (priority 3)

- **Frame:** `f0005.jpg`
- **File:** `remotion-video/src/acts/v2/ABAct1Hook.tsx`
- **Change:** Add a small 'powered by Claude Opus 4.7' badge or brand chip near the $4.17 price to start establishing Opus-specific differentiation in the opening 6 seconds (currently scores low on Opus criterion).
