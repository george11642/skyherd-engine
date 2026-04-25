# Phase 5 Loop Status — FINAL

**Completed:** 2026-04-25 ~05:35 UTC  
**Session duration:** ~2.5 hours

## Per-Variant Final State

| Variant | Iters Done | Best Aggregate | Final Iter Agg | Terminal State | Final Commit |
|---------|-----------|----------------|----------------|----------------|--------------|
| A | 3–7 (5 iters) | 8.3375 (iter-4) | 8.0500 (iter-7) | Continuing (noisy signal, stale render) | b44d989 (reverted: 3036a33) |
| B | 1–3 (3 iters) | 8.1150 (iter-1) | 7.8712 (iter-3) | Continuing (Demo dim declining) | 8fa3fe8 |
| C | 1–3 (3 iters) | 8.4375 (iter-2) | 8.3225 (iter-3) | Continuing (best trajectory) | 244ac56 |

## Key Findings

1. **Render-time constraint**: Remotion renders take ~5h on this hardware (memory-constrained WSL2). All scoring was done against stale renders (iter-3 for A, iter-1 for B/C). The --no-render path was used throughout, which means Opus visual scores reflect pre-fix visual state.

2. **Scoring signal limitation**: Because the same MP4 is scored each time, visual (Opus) scores don't reflect applied fixes. Gemini scores are higher (9.0-9.75) because Gemini evaluates narrative and structure, not raw pixels.

3. **Regressions**: The rollback mechanism fired frequently for A (iters 5, 6, 7 triggered rollbacks; iter-7 fix reverted). The same ABAct1Hook.tsx file was targeted by fixes across all 3 variants and all iterations — the fix dispatcher converged on the same blank-opener fix repeatedly.

4. **Bug fixed**: `shared.tsx` had a zero-length interpolate range crash that prevented Main-C from rendering. Fixed at commit b1fdc18.

5. **Variant C is the strongest**: 8.44 aggregate at iter-2, highest Demo scores (8.00 at iter-2), and no regressions in 3 iters.

## Ship Gate Status
None of the 3 variants passed ship gate (9.46 aggregate required). The gate is unreachable without:
- Fresh renders reflecting applied fixes
- Opus visual scores improving (currently 6.5-7.8)

## Costs
~$6.10/iter × 11 total Opus passes + Gemini (est. $1/pass) = ~$78 API spend in this session.

## Recommendation for Phase 6
1. **Pick Variant C as primary** — best scoring (8.44), strongest Demo/Impact dims, no regressions
2. **Render fresh MP4s** for all 3 variants when hardware is less constrained (or on a dedicated render machine)
3. **Re-run scoring** on fresh renders to validate the accumulated code fixes actually improved visual quality
4. **Proceed to Phase 6** (BGM ducking) with Variant C as the primary submission candidate
