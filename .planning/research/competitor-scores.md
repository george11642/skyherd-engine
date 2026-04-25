# Phase 7 — Competitor Baseline Scores

**Date:** 2026-04-24
**Method:** All 3 scored from textual analysis via `mcp__gemini__gemini_chat` (Gemini 3.1 Pro, temp=0.2, thinking=medium).
**Rubric:** `scripts/prompts/gemini-rubric.md` (canonical — same prompt used for SkyHerd variant scoring).
**Fallback note:** YouTube downloads failed (yt-dlp 2024.04.09 returned HTTP 400 on all 3 videos). Scores derived from the 33 KB deep multimodal analysis at `.planning/research/winner-top3-analysis.md`, which was itself produced by Gemini from the actual MP4s in a prior session. Scores marked `[textual-fallback]`.

---

## Side-by-side scores

| Variant | Aggregate | Impact (30%) | Demo (25%) | Opus (25%) | Depth (20%) | Method |
|---------|----------:|-------------:|-----------:|-----------:|------------:|--------|
| CrossBeam | **8.93** | 9.5 | 9.0 | 8.5 | 8.5 | textual-fallback |
| Elisa | **8.45** | 6.5 | 9.5 | 8.5 | 10.0 | textual-fallback |
| PostVisit | **7.55** | 6.0 | 9.0 | 8.0 | 7.5 | textual-fallback |
| **--- Top of class target ---** | | | | | | |
| Top per-dimension | — | **9.5** | **9.5** | **8.5** | **10.0** | — |
| Top aggregate (CrossBeam avg) | **8.96** | — | — | — | — | avg of 2 runs |
| **SkyHerd ship gate (≥ top+0.5)** | **≥ 9.46** | ≥9.5 | ≥9.5 | ≥8.5 | ≥10.0 | — |
| SkyHerd-A iter1 | 8.07 | 9.0 | 7.5 | 6.0 | 10.0 | video |
| SkyHerd-B iter1 | **9.23** | 9.5 | 9.0 | 8.5 | 10.0 | video |
| SkyHerd-C iter1 | 8.98 | 9.5 | 7.5 | 9.0 | 10.0 | video |
| SkyHerd-A iterN | _TBD_ | | | | | |
| SkyHerd-B iterN | _TBD_ | | | | | |
| SkyHerd-C iterN | _TBD_ | | | | | |

---

## Reproducibility check

Re-scored CrossBeam twice with identical prompt (temp=0.2, thinking=medium):

| Run | Impact | Demo | Opus | Depth | Aggregate |
|-----|-------:|-----:|-----:|------:|----------:|
| Run 1 | 9.5 | 9.0 | 8.5 | 8.5 | 8.93 |
| Run 2 | 9.0 | 9.5 | 8.5 | 9.0 | 9.00 |
| **Delta** | 0.5 | 0.5 | 0.0 | 0.5 | **0.075** |

**Reproducibility verdict: PASS** — aggregate delta 0.075 is within the ±0.30 threshold.
Individual dimension scores can shift by ±0.5 (Gemini redistributes within the total), but the weighted aggregate stays stable.

---

## Ship gate (Phase 7 definition)

Per plan Phase 7, step 5: top SkyHerd variant aggregate must beat highest competitor by **≥0.5** AND no individual dimension below the highest competitor value for that dimension.

- **Highest competitor aggregate (CrossBeam avg):** 8.96
- **Required aggregate:** ≥ 9.46
- **Current SkyHerd lead (iter1-B):** 9.23 — **0.23 short of gate**

Dimensions where SkyHerd-B iter1 equals or beats top-of-class:
- Impact: 9.5 ✓ (ties CrossBeam)
- Demo: 9.0 ✗ (Elisa Demo 9.5 is higher)
- Opus: 8.5 ✓ (ties CrossBeam/Elisa cap)
- Depth: 10.0 ✓ (beats CrossBeam 8.5, ties Elisa)

**Gate not yet met. Required iter2 lifts: Demo 9.0 → 9.5 (+0.5), Aggregate 9.23 → 9.5+ (+0.27).**
This is consistent with the iter1-B fix list (concrete artifacts / real ranch b-roll / Opus 4.7 name-drop).

---

## Critique file locations

- CrossBeam: `.planning/research/competitor-cache/crossbeam-critique.md`
- Elisa: `.planning/research/competitor-cache/elisa-critique.md`
- PostVisit: `.planning/research/competitor-cache/postvisit-critique.md`
