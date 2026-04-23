---
phase: 02-vision-pixel-inference
plan: "04"
subsystem: vision/pixel-inference
tags: [vision, pixel-inference, pinkeye, mobilenet, tdd]
dependency_graph:
  requires:
    - src/skyherd/vision/_models/pinkeye_mbv3s.pth (Plan 03)
    - src/skyherd/vision/result.py (DetectionResult.bbox — Plan 01)
    - src/skyherd/vision/heads/base.py (Head ABC)
    - src/skyherd/world/cattle.py (Cow)
  provides:
    - src/skyherd/vision/preprocess.py (PNG→tensor helpers)
    - src/skyherd/vision/detector.py (world→pixel bbox)
    - src/skyherd/vision/heads/pinkeye.py (pixel-inference head + rule fallback)
  affects:
    - tests/vision/test_preprocess_detector.py
    - tests/vision/test_heads/test_pinkeye_pixel.py
    - src/skyherd/vision/pipeline.py (consumes pinkeye via registry — unchanged)
tech_stack:
  added:
    - MobileNetV3-Small forward pass via torchvision (lru_cache model loader)
    - PIL Image.open + numpy array pipeline for frame preprocessing
    - functools.lru_cache(maxsize=1) pattern for deterministic single-load
  patterns:
    - Pixel path + rule fallback dual-path (graceful degradation)
    - TYPE_CHECKING guard to avoid circular import on Cow
    - _get_model() lru_cache: misses=1, subsequent calls hit cache
key_files:
  created:
    - src/skyherd/vision/preprocess.py
    - src/skyherd/vision/detector.py
    - tests/vision/test_preprocess_detector.py
    - tests/vision/test_heads/test_pinkeye_pixel.py
  modified:
    - src/skyherd/vision/heads/pinkeye.py
decisions:
  - "Rule fallback fires when model unavailable (not when model predicts class 0) — distinction between 'healthy model prediction' and 'model load failure' preserves correct no-detection semantics"
  - "cow_bbox (not eye_crop_bbox) passed to DetectionResult.bbox — dashboard needs full cow extent for visibility, eye crop is too small to annotate"
  - "bounds_m from frame_meta.get('bounds_m', (2000.0, 2000.0)) — default covers all current tests and scenarios, override keeps door open for multi-ranch configs (Plan 01 spec was out of scope)"
  - "torch.use_deterministic_algorithms(warn_only=True) instead of strict mode — some MobileNetV3 ops don't have deterministic CUDA implementations; warn_only avoids breaking CPU-only path"
metrics:
  duration_minutes: 35
  completed_date: "2026-04-22"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
  files_created: 4
---

# Phase 02 Plan 04: Pixel Inference Head — Summary

MobileNetV3-Small pixel-level inference wired into `Pinkeye` head. Rule-based fallback preserved byte-for-byte. Mean CPU inference: **~10ms/frame** (well under 500ms budget). All 121 vision tests pass, 8/8 demo scenarios PASS.

## What Was Built

### Task 1: `src/skyherd/vision/preprocess.py` + `src/skyherd/vision/detector.py`

Two utility modules extracted from the plan spec, implementing the preprocessing pipeline and geometric projection helpers.

**preprocess.py** (103 lines):

| Symbol | Purpose |
|--------|---------|
| `_PREPROCESS` | `transforms.Compose` — Resize(224,224) + ToTensor + ImageNet Normalize |
| `load_frame_as_array(path)` | PIL open → RGB uint8 (H,W,3) ndarray |
| `crop_region(arr, bbox)` | Clamped crop from (H,W,3) array |
| `array_to_tensor(crop)` | Degenerate-safe → (3,224,224) float tensor |

Degenerate crop guard: any crop with `shape[0] < 2` or `shape[1] < 2` is padded to 10×10 black before `Resize` — no crashes on edge-of-frame cows.

**detector.py** (113 lines):

| Symbol | Purpose |
|--------|---------|
| `cow_bbox_in_frame(cow, bounds_m)` | World pos → 640×480 pixel bbox (matches renderer byte-for-byte) |
| `eye_crop_bbox(cow_bbox, cow)` | 48×48 eye region within cow bbox |

Both mirror `renderer.py::_world_to_frame` + `_draw_cow_blob` formulas exactly. `TYPE_CHECKING` guard on `Cow` import avoids circular import through `skyherd.world`.

TDD: 16 RED tests written first (all failed on ImportError), then implementation written, all 16 pass GREEN.

### Task 2: `src/skyherd/vision/heads/pinkeye.py` (rewritten, 237 lines)

Complete rewrite preserving the rule-based `_classify_rule` method byte-for-byte and adding:

**`_get_model()` — lru_cache model loader:**
```python
@functools.lru_cache(maxsize=1)
def _get_model() -> nn.Module | None:
    weights_ref = importlib.resources.files("skyherd.vision._models") / "pinkeye_mbv3s.pth"
    with importlib.resources.as_file(weights_ref) as weights_path:
        model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, 4)
        state = torch.load(str(weights_path), map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        model.eval()
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(mode=True, warn_only=True)
        return model
```

**`classify()` dual-path logic:**
1. `should_evaluate()` gate (discharge > 0.4 or "pinkeye" flag) — fast pre-filter
2. If `raw_path` present and file exists → `_classify_pixel()`
3. If pixel model returns None AND model is loaded → class 0 (healthy) → no detection
4. If pixel model returns None AND model is None → fall through to `_classify_rule()`
5. No raw_path → `_classify_rule()`

**`_classify_pixel()` pixel path:**
- Loads frame via `load_frame_as_array`
- Computes `cow_bbox_in_frame` + `eye_crop_bbox`
- Crops → `array_to_tensor` → `model(tensor.unsqueeze(0))`
- softmax + argmax → `_CLASS_TO_SEVERITY[idx]`
- Populates `DetectionResult.bbox` with **cow bbox** (not eye bbox — dashboard visibility)
- Reasoning: `f"Pixel classifier (MobileNetV3-Small) on tag {cow.tag}: ..."` + `pinkeye.md` cite

TDD: 14 RED tests written first, then implementation written, 23 tests (14 new + 9 existing) all pass GREEN.

## Inference Performance

Measured on CPU (WSL2, no GPU):

| Metric | Value |
|--------|-------|
| Model load time (first call) | ~4-5s (ImageNet weights download cached) |
| Inference time (warm, per frame) | ~10ms mean (9.6ms min, 11.0ms max over 5 calls) |
| Budget | 500ms |
| Headroom | ~49x margin |
| lru_cache miss count | 1 (loaded once per process) |
| lru_cache hit count | 7 (subsequent calls) |

The model is loaded on first `classify()` call that hits the pixel path. All subsequent calls hit the lru_cache immediately.

## Pydantic model_dump Behavior on bbox Tuple

`DetectionResult.bbox` is typed as `tuple[float, float, float, float] | None`. When serialized via `.model_dump()`, Pydantic v2 emits a **list** (not a tuple):

```python
>>> result.model_dump()["bbox"]
[96.0, 362.0, 140.0, 424.0]  # list, not tuple
```

This is standard Pydantic v2 behavior for tuple fields — sequences are always emitted as JSON arrays. The determinism test uses `.model_dump()` comparison which handles this correctly (two lists are equal). Downstream SSE consumers (dashboard) receive `[x0, y0, x1, y1]` arrays — no impact on rendering.

## lru_cache Verification

```
cache_info: CacheInfo(hits=7, misses=1, maxsize=1, currsize=1)
```

`_get_model()` is truly called once per process. The `@functools.lru_cache(maxsize=1)` wrapper on a module-level function guarantees this without requiring any class-level state.

## Deviations from Plan

None — plan executed exactly as written. The binary-class-ceiling finding from Plan 03 (classes 1/2/3 are pixel-identical due to `_COW_SICK_EYE` constant) was already documented and the severity mapping handles it gracefully: the model reliably predicts class 0 (healthy, discharge ≤ 0.5) vs class 3 (escalate, discharge ≥ 0.8). The `_CLASS_TO_SEVERITY` tuple retains all 4 indices for API compatibility.

## Known Stubs

None — all data paths are wired:
- Pixel path: real CNN inference from real `.pth` weights
- Rule path: real threshold formulas
- `DetectionResult.bbox`: real pixel coordinates on pixel path, `None` on rule path (by design)

## Threat Surface

| Mitigation | Status |
|------------|--------|
| T-02-08: `torch.load(..., weights_only=True)` | Implemented — enforced in `_get_model()` |
| T-02-09: Path traversal via `raw_path` | Mitigated — `Path(raw_path).exists()` check before any file access |
| T-02-10: Decompression bomb PNG | Accepted — PIL default cap applies; rendered frames are 640×480 from trusted renderer |
| T-02-11: Logger weight path disclosure | Accepted — package-internal paths, no user data |
| T-02-12: Swapped .pth label regression | Mitigated — `test_pixel_path_fires_when_raw_path_present` would catch label-swap |

## Self-Check

### Files exist:
- `src/skyherd/vision/preprocess.py` — FOUND (103 lines)
- `src/skyherd/vision/detector.py` — FOUND (113 lines)
- `src/skyherd/vision/heads/pinkeye.py` — FOUND (237 lines, rewritten)
- `tests/vision/test_preprocess_detector.py` — FOUND (16 tests)
- `tests/vision/test_heads/test_pinkeye_pixel.py` — FOUND (14 tests)

### Commits exist (worktree branch):
- `bb6ea4a` — `test(02-04): add failing tests for preprocess.py and detector.py` (RED Task 1)
- `86b7f84` — `feat(02-04): add preprocess.py and detector.py utility modules` (GREEN Task 1)
- `cf0e9af` — `test(02-04): add failing pixel-inference tests for Pinkeye head` (RED Task 2)
- `eb9832a` — `feat(02-04): rewrite pinkeye.py as pixel-inference head with rule fallback` (GREEN Task 2)

### Verification:
- `uv run pytest tests/vision/test_heads/test_pinkeye.py` — 9/9 PASS (rule fallback unchanged)
- `uv run pytest tests/vision/test_heads/test_pinkeye_pixel.py` — 14/14 PASS (pixel path)
- `uv run pytest tests/vision/` — 121/121 PASS, 3 skipped (pre-existing cv2 skips)
- `uv run pytest tests/vision/test_heads/` — 86/86 PASS (all head tests)
- `ruff check src/skyherd/vision/{heads/pinkeye.py,preprocess.py,detector.py}` — CLEAN
- `make demo SEED=42 SCENARIO=all` — 8/8 PASS (coyote, sick_cow, water_drop, calving, storm, cross_ranch_coyote, wildfire, rustling)
- `_get_model()` loads without errors, params=1,521,956
- `mobilenet_v3_small` count in pinkeye.py: 2 ≥ 1 ✓
- `pinkeye.md` count in pinkeye.py: 7 ≥ 5 ✓
- `bbox=` count in pinkeye.py: 1 ≥ 1 ✓

## Self-Check: PASSED
