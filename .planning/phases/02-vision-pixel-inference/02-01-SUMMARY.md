---
phase: 02-vision-pixel-inference
plan: "01"
subsystem: vision
tags: [vision, licensing, interfaces, contracts, torchvision, bbox, frame_meta]
dependency_graph:
  requires: []
  provides: [DetectionResult.bbox, frame_meta.raw_path, annotate_frame.bbox_branch, _models_package, license_guard]
  affects: [src/skyherd/vision/result.py, src/skyherd/vision/pipeline.py, src/skyherd/vision/renderer.py, src/skyherd/vision/_models/__init__.py, tests/test_licenses.py, pyproject.toml]
tech_stack:
  added: [torch>=2.4<3 (direct dep), torchvision>=0.19<1 (direct dep)]
  patterns: [importlib.metadata dep-graph walk for AGPL guard, Pydantic v2 optional field with Field(default=None), annotate_frame bbox branch on det.bbox]
key_files:
  created:
    - tests/test_licenses.py
    - src/skyherd/vision/_models/__init__.py
  modified:
    - src/skyherd/vision/result.py
    - src/skyherd/vision/pipeline.py
    - src/skyherd/vision/renderer.py
    - pyproject.toml
decisions:
  - "Used importlib.metadata dep-graph walk instead of pip show (pip not in venv) to guard AGPL closure"
  - "Added torch>=2.4,<3 alongside torchvision to make both explicit direct deps (supervision pulls torch transitively but pinning is safer)"
  - "Det.bbox branch in annotate_frame uses float() cast explicitly per plan interface spec"
metrics:
  duration: "~12 minutes"
  completed: "2026-04-22"
  tasks_completed: 3
  files_changed: 6
  commits: 3
---

# Phase 02 Plan 01: Contract + License Foundation Summary

**One-liner:** Lock the vision data contract (bbox field, raw_path key, annotate_frame bbox branch) and plant the AGPL import-guard test as Wave 0 gate before any pixel inference code is written.

---

## What Landed

### 1. AGPL License Guard (`tests/test_licenses.py`)

Four tests blocking the Wave 0 gate:
- `test_no_agpl_in_base_deps` — walks the `importlib.metadata` dep graph from `skyherd-engine` (base only, no extras) and asserts `ultralytics` is absent. Skips `; extra ==` conditional deps so PytorchWildlife in the `edge` extra does not trip the guard.
- `test_no_yolov5_in_base_deps` — same pattern for `yolov5` (GPL).
- `test_torch_importable` — sanity-checks `import torch` succeeds (transitive via base deps).
- `test_torchvision_importable` — asserts `import torchvision` succeeds (now a direct dep).

All 4 PASS.

### 2. `torchvision` + `torch` promoted to direct deps (`pyproject.toml`)

```toml
"torch>=2.4,<3",
"torchvision>=0.19,<1",
```

Added under `# Vision` in `[project] dependencies`. Both were previously only available transitively. Making them direct prevents silent version drift when `supervision` or `PytorchWildlife` (edge-only) changes their transitive pins.

### 3. `DetectionResult.bbox` optional field (`src/skyherd/vision/result.py`)

```python
bbox: tuple[float, float, float, float] | None = Field(default=None)
```

Added as the final field. All 72 existing head tests pass unchanged — rule-based heads omit the argument, so `.bbox is None`. Pydantic v2 `.model_dump()` emits `"bbox": null` for rule heads (accepted tradeoff; no `ser_json_exclude_none=True` added to keep the field discoverable by downstream SSE consumers).

### 4. `src/skyherd/vision/_models/__init__.py` package marker

One-line docstring package marker. `importlib.resources.files("skyherd.vision._models")` now resolves to a directory, ready to serve `.pth` weight files when the pixel head training script deposits them.

### 5. `frame_meta["raw_path"]` injected (`src/skyherd/vision/pipeline.py`)

```python
frame_meta: dict[str, Any] = {
    "trough_id": trough_id,
    "temp_f": weather.temp_f,
    "raw_path": raw_path,  # Path to the rendered PNG — pixel heads consume this
}
```

The `raw_path` variable already existed (line 72) from the `render_trough_frame` call; this plan wires it into the dict that heads receive. `frame_meta_override` still wins (applied after, can override `raw_path` — useful in tests pointing at fixture frames).

### 6. `annotate_frame` branches on `det.bbox` (`src/skyherd/vision/renderer.py`)

```python
for i, det in enumerate(detections):
    if det.bbox is not None:
        xyxy.append([float(det.bbox[0]), float(det.bbox[1]), float(det.bbox[2]), float(det.bbox[3])])
    else:
        # Grid layout fallback — unchanged behavior for rule-based heads
        col = i % 4
        row = i // 4
        x0 = col * (w // 4) + 10
        y0 = row * (h // 5) + 10
        x1 = min(x0 + box_w, w - 5)
        y1 = min(y0 + box_h, h - 5)
        xyxy.append([float(x0), float(y0), float(x1), float(y1)])
    labels.append(f"{det.head_name}:{det.severity} [{det.cow_tag}]")
    class_ids.append(severity_to_class.get(det.severity, 0))
```

Rule-head detections (all `bbox=None`) fall through to the existing grid layout — byte-identical behavior.

---

## Tests Guarding These Contracts

| Test | What It Guards |
|------|---------------|
| `tests/test_licenses.py::test_no_agpl_in_base_deps` | ultralytics absent from base dep graph |
| `tests/test_licenses.py::test_no_yolov5_in_base_deps` | yolov5 absent from base dep graph |
| `tests/test_licenses.py::test_torch_importable` | torch available in base venv |
| `tests/test_licenses.py::test_torchvision_importable` | torchvision available as direct dep |
| `tests/vision/test_heads/test_pinkeye.py` (9 tests) | Rule-based pinkeye head unaffected by bbox field |
| `tests/vision/test_renderer.py` (11 tests) | annotate_frame unchanged for rule-only detections |
| `tests/vision/test_pipeline.py` (skipped cv2) | Pipeline integration (cv2 skip = environment-only) |

---

## Zero Regression Confirmation

- **72 rule-head tests**: all PASS unchanged — bbox field defaulting to None is backwards-compatible.
- **91 vision tests total**: PASS (2 skipped = cv2/annotation tests requiring opencv, pre-existing skip condition).
- **Coverage**: 86.74% on `src/skyherd/vision/` — above the 85% threshold.

---

## Surprises / Notes

1. **pip not in venv**: The plan spec said to use `subprocess.run([sys.executable, "-m", "pip", "show", ...])` for the AGPL guard, but pip is not installed in the project's uv-managed venv. Adapted to `importlib.metadata` dep-graph walk — more correct anyway (checks declared deps, not environment state) and avoids a subprocess call.

2. **`uv sync` changed Python version context**: After `uv sync`, the system `uv run pytest` invoked Python 3.12 (system) rather than the venv's Python 3.13. All verification uses `.venv/bin/pytest` directly to ensure the correct interpreter.

3. **No Pydantic snapshot test updates needed**: Existing tests do not assert on exact `.model_dump()` key sets, so `"bbox": null` appearing in dumps caused zero breakage.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adapted AGPL guard from pip show to importlib.metadata**
- **Found during:** Task 1
- **Issue:** Plan specified `subprocess.run([sys.executable, "-m", "pip", "show", "ultralytics"])` but pip is not installed in the uv-managed venv (`No module named pip`).
- **Fix:** Used `importlib.metadata.distribution()` to walk the dep graph from `skyherd-engine`, skipping `; extra ==` conditional markers. More accurate than pip show (checks declared deps, not just installed packages).
- **Files modified:** `tests/test_licenses.py`
- **Commit:** 52a0087

---

## Known Stubs

None — all fields are wired. `bbox` defaults to `None` for rule-based heads by design (not a stub — the field is intentionally optional for backwards-compatibility). Pixel head (Wave 2, plan 02-02+) will populate it.

---

## Threat Flags

None beyond the threat model in the plan:
- T-02-01 (AGPL guard) is now mitigated by `tests/test_licenses.py`.
- T-02-02 (raw_path disclosure) remains accepted; Wave 2 pinkeye head will add `Path.resolve()` + allowed-root check.
- T-02-03 (bbox memory) remains accepted (negligible impact).

---

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `tests/test_licenses.py` exists | FOUND |
| `src/skyherd/vision/_models/__init__.py` exists | FOUND |
| `src/skyherd/vision/result.py` contains `bbox` | FOUND |
| `src/skyherd/vision/pipeline.py` contains `raw_path` | FOUND |
| `src/skyherd/vision/renderer.py` contains `det.bbox is not None` | FOUND |
| `pyproject.toml` contains `torchvision` under `[project] dependencies` | FOUND |
| Commit 52a0087 exists | FOUND |
| Commit 1de9f4f exists | FOUND |
| Commit fae2d14 exists | FOUND |
| All 95 license+vision tests PASS | CONFIRMED |
| Coverage ≥85% | CONFIRMED (86.74%) |
