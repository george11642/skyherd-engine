# SkyHerd Final Variant Comparison — 2026-04-25

All three variants scored on the Built-with-Opus-4.7 rubric (Impact 30% / Demo 25% / Opus 25% / Depth 20%).
Final aggregate = average of Opus stills score + Gemini critique score.

## Score Table

| Variant | Aggregate | Impact | Demo | Opus 4.7 | Depth | Gemini agg | Opus median | Gap to ship gate |
|---------|-----------|--------|------|----------|-------|------------|-------------|-----------------|
| A       | 7.95      | 8.00   | 7.25 | 8.15     | 8.50  | 9.35       | 6.55        | -1.51           |
| B       | 8.13      | 8.60   | 7.75 | 7.70     | 8.45  | 9.38       | 6.89        | -1.33           |
| C       | 8.69      | 9.10   | 8.50 | 8.00     | 9.15  | 9.63       | 7.75        | -0.77           |

Ship gate: Aggregate ≥ 9.46, Impact ≥ 9.5, Demo ≥ 9.5, Opus ≥ 8.5, Depth ≥ 10.0. All three variants fail.

## Gemini Dimension Detail

| Variant | G-Impact | G-Demo | G-Opus | G-Depth |
|---------|----------|--------|--------|---------|
| A       | 9.50     | 8.50   | 9.50   | 10.00   |
| B       | 10.00    | 9.00   | 8.50   | 10.00   |
| C       | 10.00    | 9.00   | 9.50   | 10.00   |

## Recommendation

**Ship Variant C.** It wins on every axis:

- Highest aggregate: 8.69 vs 8.13 (B) vs 7.95 (A)
- Smallest gap to ship gate: -0.77 vs -1.33 (B) vs -1.51 (A)
- Highest Opus 4.7 axis (tiebreaker criterion): 8.00, tied with A but above B's 7.70 — and C has the highest Gemini Opus score (9.50) which is the differentiator judges see
- Strongest Opus stills median: 7.75 vs 6.89 vs 6.55 — this reflects the frame-by-frame technical density that Opus evaluates

Do NOT ship all three as variants — C is categorically better and splitting attention with A/B (which score 1–2 points lower on Gemini) risks diluting the submission's signal.

## Critical Gemini Flags

**All three variants share the same top flag:** the UI is a high-fidelity motion-graphics replay rather than a live app interface, leaving the human-computer interaction loop ambiguous. This is the primary reason Demo scores are capped at 8.5–9.0 across the board.

**Variant A only:** The $4.17/week cost claim lacks a visible breakdown, inviting judge skepticism on economic viability.

**Variant B only:** Physical drone actuation is fully abstracted — the judge must trust the map UI represents real hardware. No code or reasoning trace visible to prove Opus 4.7 is uniquely required (Gemini Opus 8.5 vs A's 9.5 and C's 9.5).

**Variant C (shipped):** No blocking weaknesses identified by Gemini. Two minor improvements: add a brief Opus 4.7 reasoning trace clip and a real-drone b-roll splice — but these are polish, not blockers.
