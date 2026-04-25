# Phase H — Iteration 1 Dual-Vision Baseline Comparison

**Date:** 2026-04-24
**Render method:** `pnpm exec remotion render Main-{A,B,C} --concurrency=1`, 1080p60 H.264
**Analysis:** `mcp__gemini__gemini_analyze` on each full MP4 (Gemini 3.1 Pro multimodal)

## Renders

| Variant | File | Size | Duration | Catbox (72h) |
|---------|------|------|----------|--------------|
| A — Winner-pattern | `/tmp/skyherd-iter1-A.mp4` | 49.8 MB | 180.95s | https://litter.catbox.moe/1w2rge.mp4 |
| B — Hybrid | `/tmp/skyherd-iter1-B.mp4` | 51.1 MB | 180.95s | https://litter.catbox.moe/07ys9k.mp4 |
| C — Differentiated | `/tmp/skyherd-iter1-C.mp4` | 40.6 MB | 180.05s | https://litter.catbox.moe/wavshs.mp4 |

## Scores

| Variant | Impact (30%) | Demo (25%) | Opus 4.7 (25%) | Depth (20%) | **Weighted** |
|---------|-------------:|-----------:|---------------:|------------:|-------------:|
| A | 9.0 | 7.5 | 6.0 | 10.0 | 8.07 |
| **B** | **9.5** | **9.0** | **8.5** | **10.0** | **9.23 ← LEAD** |
| C | 9.5 | 7.5 | 9.0 | 10.0 | 8.98 |

## Cross-variant analysis

### Metric-first hook wins (B & C vs A)
Both B and C (which open with "$4.17/week · 10K acres") scored Impact 9.5; A's contrarian hook scored 9.0. The metric plus scale-qualifier is a full half-point stronger than the winner-pattern identity hook for this specific problem/audience combination. **Gemini ground-truth on the top-3 4.6 winners said "no metric in <15s" — that rule breaks for our product because the metric is extraordinary, not ordinary.**

### 3-act with emphasis-only captions is the Demo sweet spot (B beats both A and C on Demo)
- A (3-act emphasis-only): Demo 7.5 — lost points on "JavaScript video game" feel, no physical grounding
- B (3-act emphasis-only, metric hook): Demo 9.0 — metric opening primes judges to value what they see
- C (5-act, dense word-level captions): Demo 7.5 — dense captions compete with dashboard UI

C's dense captions ARE the Opus-4.7-use differentiator (9.0 score), but they cost Demo score. The structural choice is a real tradeoff.

### Depth tied at 10/10 across all variants
The 1106-tests / 87%-coverage / Ed25519-attestation / deterministic-replay sequence is carrying the full 20% depth weight uniformly. No variant-specific tuning helps or hurts here.

### Opus 4.7 use is where variants diverge most (6.0 → 8.5 → 9.0)
- A keeps Opus 4.7 implicit (black box); Gemini called out the model could be "GPT-3.5 wrapped in a nice UI"
- B explicitly shows the 5-agent mesh architecture (1:58–2:10)
- C adds the meta caption-styling beat (2:05) — Opus directing its own presentation

## Universal fixes (appear across ≥2 variants)

1. **Ground abstract dashboard with concrete artifacts.** Flash vet-packet PDF, drone thermal, mobile notification mockup at the scenario beats. The 2D dots-on-grid feel hurts Demo scores on A and C.
2. **Add real-world B-roll during problem-statement / setup.** All variants have a "text + dark UI" stretch around 0:25–0:51 where real ranch B-roll would raise energy. Phase D sourced 16 Mixkit clips — not enough are in rotation yet.
3. **Explicitly name Opus 4.7.** A, B, C all leave it implicit until the final card. Change VO mentions of "Claude" at 2:08-ish to "Opus 4.7 compute."

## Variant-specific fixes

### Variant A (least pressing — runs second in line)
- Visualize an Opus 4.7 reasoning chain or JSON output during the architecture section.
- Condense middle scenarios (2/3/4) to a 10s rapid-fire montage; use saved 20s on additional depth signal.

### Variant B (LEAD — lightest touch-up)
- Intercut 2-3s real ranch footage during the problem statement (0:25–0:51).
- Flash a mock vet-packet PDF + drone thermal during the scenario sweep (1:03–1:55).
- Change "Claude" → "Opus 4.7 compute" at 2:09.

### Variant C (middle)
- Shrink kinetic text 50% and move to bottom third during UI demo (1:10–2:00) so dashboard is hero.
- Show mobile endpoint at 1:24 (vet-packet-on-phone mockup).
- Ping/glow the map when agents fire (coyote drone dispatch 1:14).

## Recommendation

**Lead: Variant B (9.23).** 1.16 points ahead of A, 0.25 ahead of C. Ship B if we need to submit today; iterate on B if we have more cycles.

Next iteration target: apply the 3 variant-B-specific fixes + the universal "concrete artifacts" fix. Estimated lift to 9.5+ with a tight B-roll pass and one mobile-mockup shot.

**Alternative:** apply C's Opus-4.7 caption-styling gimmick TO Variant B (scale down to emphasis-words only, keep the per-word semantic coloring). That combines B's structure with C's creative-track signal. Could push 9.23 → 9.5+.

## Cost summary (iter1)
- Gemini API: 3 multimodal calls, ~$0.40 estimated (Gemini 3.1 Pro)
- Opus stills: not run (sub-agent exited early; skipped in favor of Gemini-only)
- Render compute: ~45 minutes total wall-clock across 3 variants
- Catbox hosting: free, 72h retention

## Next
Orchestrator decides: ship B, iterate B (most likely), or synthesize B+C hybrid.
