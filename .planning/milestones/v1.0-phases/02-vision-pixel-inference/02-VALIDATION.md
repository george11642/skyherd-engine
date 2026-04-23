---
phase: 2
slug: vision-pixel-inference
status: executed
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-22
---

# Phase 2 — Validation Strategy

> Per-phase validation contract. See "Validation Architecture" section of `02-RESEARCH.md` for full test specs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + time.perf_counter (for latency — no pytest-benchmark dep added) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/vision/ -x` |
| **Full suite command** | `uv run pytest --cov=src/skyherd/vision --cov-fail-under=85` |
| **Estimated runtime** | ~20-40s (quick, excluding training) / ~2-3min (full) |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/vision/test_heads/test_pinkeye.py tests/test_licenses.py -x`
- **After every plan wave:** Full vision suite + license-clean assertion
- **Before `/gsd-verify-work`:** Full suite + `make demo SCENARIO=sick_cow` green
- **Max feedback latency:** ~40 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-T1 | 02-01 | 1 | VIS-02 | T-02-01 | AGPL packages absent from base dep graph; torch+torchvision importable | license | `uv run pytest tests/test_licenses.py -v` | yes | executed |
| 02-01-T2 | 02-01 | 1 | VIS-01 | T-02-03 | DetectionResult.bbox optional field present; rule heads return bbox=None | unit | `uv run pytest tests/vision/test_heads/ -v` | yes | executed |
| 02-01-T3 | 02-01 | 1 | VIS-05 | T-02-02 | raw_path injected into frame_meta; annotate_frame branches on det.bbox | integration | `uv run pytest tests/vision/test_pipeline.py tests/vision/test_renderer.py -v` | yes | executed |
| 02-02-T1 | 02-02 | 1 | VIS-01 | - | sick_pinkeye_world + rendered_positive_frame + rendered_negative_frame fixtures present | unit | `uv run pytest tests/vision/ --fixtures 2>&1 \| grep -c "sick_pinkeye_world"` | yes | executed |
| 02-02-T2 | 02-02 | 1 | VIS-05 | - | bbox data flows from DetectionResult through annotate_frame to annotated PNG pixels | integration | `uv run pytest tests/vision/test_annotate_bbox.py -v` | yes | executed |
| 02-03-T1 | 02-03 | 2 | VIS-03 | T-02-06 | train_pinkeye_classifier.py generates pinkeye_mbv3s.pth with val_acc >= 0.70 | unit | `uv run pytest tests/vision/ -k "model" -v` | yes | executed |
| 02-03-T2 | 02-03 | 2 | VIS-03 | T-02-07 | pinkeye_mbv3s.pth loads without key mismatch; smoke: discharge=0.85 → class in {2,3} | unit | `uv run python -c "from skyherd.vision.heads.pinkeye import _get_model; m=_get_model(); assert m is not None"` | yes | executed |
| 02-04-T1 | 02-04 | 3 | VIS-04 | T-02-09 | preprocess.py + detector.py: load_frame_as_array + cow_bbox_in_frame correct geometry | unit | `uv run pytest tests/vision/test_preprocess_detector.py -v` | yes | executed |
| 02-04-T2 | 02-04 | 3 | VIS-01, VIS-04 | T-02-08, T-02-12 | pixel path fires on raw_path present; weights_only=True in torch.load; lru_cache hit | unit | `uv run pytest tests/vision/test_heads/test_pinkeye_pixel.py -v` | yes | executed |
| 02-05-T1 | 02-05 | 4 | VIS-01 | - | 9 original rule-path tests preserved byte-for-byte; 2 explicit rule-fallback tests pass | unit | `uv run pytest tests/vision/test_heads/test_pinkeye.py -v` | yes | executed |
| 02-05-T2 | 02-05 | 4 | VIS-01, VIS-02, VIS-04 | T-02-13, T-02-14, T-02-15 | positive frame bbox; negative None; determinism; median<500ms; no AGPL imports; lru_cache | unit + perf + license | `uv run pytest tests/vision/test_heads/test_pinkeye_pixel.py -v` | yes | executed |
| 02-05-T3 | 02-05 | 4 | VIS-05 | - | ClassifyPipeline on pinkeye-positive world yields pinkeye detection with real bbox | scenario | `uv run pytest tests/scenarios/test_sick_cow.py -v && uv run pytest tests/vision/ tests/scenarios/test_sick_cow.py tests/test_licenses.py -x` | yes | executed |

---

## Wave 0 Requirements

- [x] `tests/vision/conftest.py` — synthetic-frame fixture generator (positive / negative pinkeye frames)
- [x] `tests/test_licenses.py` — AGPL import-guard test; asserts no `ultralytics` / `yolov5` in base install
- [x] `src/skyherd/vision/_models/` — scaffold directory for weights (`.gitignore` weights, ship download script)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sick-cow scenario dashboard panel shows real bbox overlay | VIS-05 | Visual — hard to assert pixel-perfect in CI | Run `make dashboard` live mode, play sick_cow scenario, verify bbox renders on rendered PNG |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 40s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
