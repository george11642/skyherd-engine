---
phase: 02-vision-pixel-inference
plan: "02"
subsystem: vision/testing
tags: [vision, testing, fixtures, bbox, pinkeye]
dependency_graph:
  requires: []
  provides:
    - tests/vision/conftest.py::sick_pinkeye_world
    - tests/vision/conftest.py::rendered_positive_frame
    - tests/vision/conftest.py::rendered_negative_frame
    - tests/vision/test_annotate_bbox.py (3 integration tests)
  affects:
    - tests/vision/test_heads/test_pinkeye.py (Wave 3 consumer)
    - src/skyherd/vision/renderer.py::annotate_frame (integration guard)
tech_stack:
  added: []
  patterns:
    - pytest fixtures for synthetic rendered frames (seed-driven, deterministic)
    - pytest.importorskip("cv2") guard on supervision-dependent tests
key_files:
  created:
    - tests/vision/test_annotate_bbox.py
  modified:
    - tests/vision/conftest.py
decisions:
  - "Fixtures added additively at bottom of conftest.py — zero existing lines modified"
  - "test_annotate_bbox.py left RED in Wave 0 worktree (supervision not installed + Plan 01 bbox field not yet merged); this is expected TDD RED state"
  - "Pydantic silently ignores unknown bbox kwarg pre-Plan-01 — tests reach annotate_frame before failing on supervision import"
metrics:
  duration_minutes: 8
  completed_date: "2026-04-22"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 02 Plan 02: Vision Test Fixtures + bbox Integration Guard — Summary

Wave 0 test scaffolding for Phase 02 vision pixel inference. Provides deterministic synthetic-frame fixtures and guards the `DetectionResult.bbox → annotate_frame` data flow before any pixel inference code exists.

## What Was Built

### New Fixtures in `tests/vision/conftest.py`

Three fixtures added additively at the bottom of the file — zero existing lines changed:

| Fixture | Contract |
|---------|----------|
| `sick_pinkeye_world` | `World` with one cow: tag=`SICK01`, pos=(300,300), `ocular_discharge=0.85`, `disease_flags={"pinkeye"}`. Deterministic (seed=42). |
| `rendered_positive_frame` | Renders `sick_pinkeye_world` trough_a frame to `tmp_path/raw_positive.png`. Returns `(Path, World)`. |
| `rendered_negative_frame` | Renders `world_healthy` trough_a frame to `tmp_path/raw_negative.png`. Returns `(Path, World)`. |

All three fixtures are discoverable via `pytest --fixtures tests/vision/conftest.py`.

**Determinism guarantee:** `render_trough_frame` is deterministic given identical `World` state (verified by pre-existing `test_render_trough_frame_deterministic` test in `test_renderer.py`). The fixtures use fixed random seeds (42, 99, etc.) to ensure byte-identical PNG output across replays.

### New Integration Tests in `tests/vision/test_annotate_bbox.py`

Three tests guarding the bbox data flow at the integration boundary:

| Test | What It Guards |
|------|---------------|
| `test_bbox_flows_to_annotated_png` | `DetectionResult(bbox=(100,150,200,250))` causes pixels in that region to differ from source — proves bbox branch in `annotate_frame` is active |
| `test_rule_head_grid_fallback_preserved` | `bbox=None` still causes grid-layout annotation (regression sentinel for existing behavior) |
| `test_mixed_bbox_and_none_coexist` | Mixed bbox/None detection list completes without error; output is valid 640×480 PNG |

## cv2 / supervision Environment Notes

**Important for CI/WSL2:** The tests use `pytest.importorskip("cv2")` as the skip guard (per the plan's `<cv2_guard_pattern>`). In this worktree's environment, `cv2` IS installed, so tests run — but `supervision` is not installed, causing failures at `annotate_frame()`. This is a **pre-existing environment issue** (same failure occurs in `test_annotate.py` and `test_pipeline.py` from before this plan).

The tests are intentionally **RED in this Wave 0 worktree** for two reasons:
1. `DetectionResult.bbox` field does not yet exist (Plan 01 adds it; Plan 01 runs in a parallel worktree)
2. `supervision` package is not installed in this worktree's Python environment

After Plan 01 merges and `supervision` is installed, all three tests will go GREEN.

## Deviations from Plan

None — plan executed exactly as written. The RED test state is explicitly expected per the `<parallel_safety>` note in the plan.

## Self-Check

### Created files exist:
- `tests/vision/conftest.py` — FOUND (modified, additive)
- `tests/vision/test_annotate_bbox.py` — FOUND (created, 93 lines)

### Commits exist:
- `eabd8b7` — `test(02-02): add sick_pinkeye_world + rendered_positive/negative_frame fixtures`
- `671dee6` — `test(02-02): write test_annotate_bbox.py — integration test of bbox data flow`

### Done criteria verification:
- `grep -c "def sick_pinkeye_world" tests/vision/conftest.py` → 1 ✓
- `grep -c "def rendered_positive_frame" tests/vision/conftest.py` → 1 ✓
- `grep -c "def rendered_negative_frame" tests/vision/conftest.py` → 1 ✓
- `pytest --fixtures tests/vision/conftest.py` lists all 3 new fixtures ✓
- `grep -c "pytest.importorskip" tests/vision/test_annotate_bbox.py` → 1 ✓
- `grep -c "DetectionResult" tests/vision/test_annotate_bbox.py` → 5+ hits ✓
- `tests/vision/test_annotate_bbox.py` has 3 test functions ✓
- 93 lines (above min 40) ✓
- Renderer and registry tests (`test_renderer.py`, `test_registry.py`) still pass — 19 passed ✓
- Zero existing fixtures modified ✓

## Self-Check: PASSED
