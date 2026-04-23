# Plan 02-05 — Tests + Sick-Cow Scenario Bbox Assertion + VALIDATION Fill

**Status:** Complete
**Wave:** 4 (final)
**Executor:** Sonnet (balanced profile)
**Completed:** 2026-04-22

## What Was Built

Closed out Phase 2 with three test commits that pin the pinkeye pixel-inference contract end-to-end:

- **Task 1** (`55e77eb`): Added two explicit rule-fallback preservation tests to `tests/vision/test_heads/test_pinkeye.py`. The 9 original rule-path tests are preserved byte-for-byte; new tests confirm the rule fallback fires when `frame_meta["raw_path"]` is absent or unreadable.

- **Task 2** (`aa906a7`): Added Plan-05-named tests to `tests/vision/test_heads/test_pinkeye_pixel.py` — positive-frame bbox non-None, negative-frame bbox None, inference determinism, median latency <500ms on CPU, license-clean imports assertion, lru_cache single-load.

- **Task 3** (`377bc1d`): Added pinkeye bbox scenario test in `tests/scenarios/test_sick_cow.py` — `ClassifyPipeline` on a pinkeye-positive world yields a pinkeye detection with a real bbox (0≤x0<x1≤640). Also filled `02-VALIDATION.md` Per-Task Verification Map with all 12 task rows (`status: executed`, `nyquist_compliant: true`).

## Key Outcomes

- **Median inference:** ~17.7ms CPU (28× under 500ms budget, consistent with 02-04's ~10ms measurement)
- **Test counts:** 9 original rule tests preserved + 2 new rule-fallback tests + 7 pixel-head tests + 1 scenario bbox test
- **VALIDATION.md:** Per-Task Map populated for all 12 Phase 2 tasks across 5 plans
- **Zero regressions:** `make demo SEED=42 SCENARIO=all` — 8/8 PASS
- **License clean:** AGPL guard assertion still green (no ultralytics/yolov5 in base install)

## Files Modified

- `tests/vision/test_heads/test_pinkeye.py` — 2 new tests appended (rule-fallback coverage)
- `tests/vision/test_heads/test_pinkeye_pixel.py` — 7 Plan-05-named tests added
- `tests/scenarios/test_sick_cow.py` — 1 scenario bbox test added
- `.planning/phases/02-vision-pixel-inference/02-VALIDATION.md` — Per-Task Map filled; frontmatter `status: executed`

## Note on Executor Budget

Executor returned after committing Task 3 but before writing this SUMMARY.md. Commits landed correctly on the worktree branch; SUMMARY.md written by orchestrator post-merge from the agent's final state + VALIDATION.md evidence.

## Deviations

None from plan. Task 3 execution combined the sick-cow scenario test and the VALIDATION.md fill into a single commit (`377bc1d`) because both operate on downstream artifacts with no intermediate verification point.
