---
phase: 02-vision-pixel-inference
plan: "03"
subsystem: vision/ml-training
tags: [vision, ml-training, weights, mobilenetv3]
dependency_graph:
  requires:
    - scripts/train_pinkeye_classifier.py
    - src/skyherd/vision/renderer.py::render_trough_frame
    - src/skyherd/world/ (World, Herd, Cow, Terrain)
  provides:
    - src/skyherd/vision/_models/pinkeye_mbv3s.pth (Wave 3 consumer)
    - src/skyherd/vision/_models/WEIGHTS.md
  affects:
    - src/skyherd/vision/heads/pinkeye.py (Wave 3 -- loads weights via importlib.resources)
tech_stack:
  added:
    - MobileNetV3-Small (torchvision) with frozen ImageNet V1 backbone
  patterns:
    - Frozen-backbone fine-tuning: freeze model.features, train only classifier
    - Binary training scheme for visually indistinguishable intermediate classes
    - State_dict saved with torch.save; loaded with torch.load(..., weights_only=True)
key_files:
  created:
    - src/skyherd/vision/_models/pinkeye_mbv3s.pth
    - src/skyherd/vision/_models/WEIGHTS.md
  modified:
    - scripts/train_pinkeye_classifier.py
decisions:
  - "Binary training (class 0 vs class 3 only): renderer _COW_SICK_EYE is a fixed
     constant (220,60,60) so classes 1,2,3 produce identical pixels in the eye region.
     Binary training achieves 100% val_acc; 4-class head retained for Wave 3 API compat"
  - "40 epochs required: frozen ImageNet backbone needs 14-22 epoch warm-up before
     the classifier discovers the red streak signal (val_acc jumps from 0.49 to 1.00
     between epochs 14-23). Default epochs bumped to 40 to reliably clear threshold"
  - "ImageNet V1 weights + frozen backbone (plan spec): weights=None + full-network
     training was attempted first but failed (loss→0 in 2 epochs, val_acc stuck at
     0.49 = predict-all-one-class collapse). ImageNet priors essential for signal detection"
metrics:
  duration_minutes: 45
  completed_date: "2026-04-22"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 02 Plan 03: Pinkeye Classifier Weights -- Summary

MobileNetV3-Small with frozen ImageNet V1 backbone fine-tuned on 224 synthetic frames. Final val_acc = 1.0000, smoke test passes (positive discharge=0.85 → class 3, negative discharge=0.0 → class 0). SHA-256: `fa4118b75c67366611136c82cfadb3a17616ca4f41f7dfc517fdc378d1a124dd`.

## What Was Built

### Task 1: `scripts/train_pinkeye_classifier.py`

One-off deterministic training script (excluded from coverage + pyright). Key design:

| Section | Detail |
|---------|--------|
| Determinism block | `random.seed(42)` + `np.random.seed(42)` + `torch.manual_seed(42)` + `torch.set_num_threads(1)` + `torch.use_deterministic_algorithms(warn_only=True)` |
| Dataset | 14 healthy discharges x 8 cow positions + 14 sick discharges x 8 positions = 224 total; 80/20 train/val split |
| Crop | `eye_crop()` -- 48x48 window centred on rendered head (hx = fx+R_X-4, hy = fy-R_Y+tilt-6, half=24) |
| Model | `mobilenet_v3_small(weights=IMAGENET1K_V1)`, features frozen, `classifier[3] = Linear(1024, 4)` |
| Optimizer | `Adam(classifier.parameters(), lr=1e-3)` + `ReduceLROnPlateau(patience=3, factor=0.5)` |
| Smoke gate | Positive (discharge=0.85) → argmax in {2,3}; negative (discharge=0.0) → argmax == 0 |
| Save guard | Only saves if `best_val_acc >= 0.70` AND smoke test passes |

### Task 2: Training run + `pinkeye_mbv3s.pth` + `WEIGHTS.md`

Training output:

| Metric | Value |
|--------|-------|
| Epochs | 40 |
| Final val_acc | 1.0000 (epochs 23-40 all perfect) |
| Smoke positive | 3 (in {2, 3}) ✓ |
| Smoke negative | 0 ✓ |
| SHA-256 | `fa4118b75c67366611136c82cfadb3a17616ca4f41f7dfc517fdc378d1a124dd` |
| File size | 5.93 MB (under 20 MB cap) |

`WEIGHTS.md` documents architecture, load instructions, training command, binary-training rationale, and ImageNet non-commercial license caveat.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Binary training scheme -- classes 1/2/3 are pixel-identical**

- **Found during:** Task 2 first training run (val_acc stuck at 0.49)
- **Issue:** The renderer's `_COW_SICK_EYE = (220, 60, 60)` is a fixed constant. Any discharge > 0.5 produces R=220 in the streak region. Classes 1, 2, and 3 produce bit-for-bit identical eye crops. A 4-class classifier cannot distinguish them from pixels.
- **Fix:** Binary training (class 0 vs class 3 only). Class 0: discharge <= 0.5 (no streak, R_max=180). Class 3: discharge >= 0.8 (bright streak, R_max=220). The 4-class head is retained so Wave 3's `load_state_dict` works without modification.
- **Smoke test alignment:** discharge=0.85 → class 3 in {2, 3} ✓; discharge=0.0 → class 0 ✓
- **Files modified:** `scripts/train_pinkeye_classifier.py`

**2. [Rule 1 - Bug] 40 epochs required instead of plan's default 10**

- **Found during:** Multiple training runs
- **Issue:** With a frozen ImageNet backbone, the linear classifier needs 14-22 epochs of warm-up before it discovers the red-streak signal. At epoch 14 val_acc is still 0.49 (predict-all-class-0); at epoch 15 it jumps to 0.51, then climbs to 1.00 by epoch 23.
- **Fix:** Training command bumped to `--epochs 40`. The plan's retry condition covers this; documented here for clarity.
- **Files modified:** Training command in WEIGHTS.md

**3. [Rule 1 - Bug] weights=None from-scratch training failed -- reverted to ImageNet V1**

- **Found during:** Task 2 intermediate attempts
- **Issue:** MobileNetV3-Small trained from scratch on 179 samples collapsed: loss reaches ~0.0006 by epoch 2 (perfect memorization) but val_acc stays at 0.489 (model predicts all-class-0). Batch norm with only 32-sample batches is too unstable; the gradient doesn't generalize.
- **Fix:** Reverted to plan-spec approach: `MobileNet_V3_Small_Weights.IMAGENET1K_V1` + frozen backbone. ImageNet features already respond to color/texture; a single linear layer on top detects the red streak reliably.
- **Files modified:** `scripts/train_pinkeye_classifier.py`

## Wave 3 Load Contract Verification

```python
# Wave 3 pinkeye.py will use:
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
import torch.nn as nn

model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
model.classifier[3] = nn.Linear(model.classifier[3].in_features, 4)
state = torch.load("src/skyherd/vision/_models/pinkeye_mbv3s.pth",
                   map_location="cpu", weights_only=True)
model.load_state_dict(state)  # verified: no key mismatches
```

## Self-Check

### Files exist:
- `scripts/train_pinkeye_classifier.py` -- FOUND (rewritten, 302 lines)
- `src/skyherd/vision/_models/pinkeye_mbv3s.pth` -- FOUND (5.93 MB)
- `src/skyherd/vision/_models/WEIGHTS.md` -- FOUND (SHA-256 present, License Caveats present)

### Commits exist:
- `77c6265` -- `feat(02-03): add train_pinkeye_classifier.py + exclude scripts from coverage`
- `04ea988` -- `chore(02-03): rewrite training to ImageNet V1 frozen backbone + 40 epochs`
- `7304a10` -- `feat(02-03): add trained pinkeye_mbv3s.pth weights + WEIGHTS.md provenance`

### Test regressions:
- 93 vision + renderer + registry + head tests PASS (zero regressions)
- 2 pre-existing failures in `test_licenses.py` (torch/torchvision not on system Python -- pre-existing before this plan)
- 3 pre-existing failures in `test_annotate.py` + `test_annotate_bbox.py` (supervision not installed -- documented in Plan 02-02 SUMMARY)

## Self-Check: PASSED
