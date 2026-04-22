# Pinkeye Pixel Classifier Weights

| Field | Value |
|-------|-------|
| File | `pinkeye_mbv3s.pth` |
| Architecture | torchvision `mobilenet_v3_small` with `classifier[3]` replaced by `nn.Linear(1024, 4)` |
| Base weights | ImageNet-1k V1 (via `MobileNet_V3_Small_Weights.IMAGENET1K_V1`) |
| Fine-tune dataset | 224 synthetic frames from `skyherd.vision.renderer.render_trough_frame`, binary labels (class 0 = healthy, class 3 = escalate) |
| Classes | 0 = healthy, 1 = watch, 2 = log, 3 = escalate |
| SHA-256 | `fa4118b75c67366611136c82cfadb3a17616ca4f41f7dfc517fdc378d1a124dd` |
| Size | 5.93 MB |
| Training seed | 42 |
| Trained on | 2026-04-22 |
| Training command | `uv run python scripts/train_pinkeye_classifier.py --frames 500 --seed 42 --epochs 40` |
| Final val_acc | 1.0000 (binary class 0 vs 3 on 45 val samples) |

## Architecture Details

```python
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
import torch.nn as nn

model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
model.classifier[3] = nn.Linear(model.classifier[3].in_features, 4)
```

The backbone (`model.features`) was frozen during fine-tuning. Only the 4-layer
classifier (`model.classifier`) was trained. This state_dict contains both the
frozen backbone weights (identical to IMAGENET1K_V1) and the trained classifier.

## Training Notes

The renderer (`skyherd.vision.renderer._draw_cow_blob`) draws the eye discharge
streak with a FIXED colour `_COW_SICK_EYE = (220, 60, 60)` for any discharge > 0.5.
Classes 1, 2, and 3 produce identical pixels in the eye region — only class 0
(discharge <= 0.5, no streak) is visually distinct. Training uses a binary scheme:
- Class 0: discharge in [0.0, 0.5] — no streak (R_max = 180 in crop)
- Class 3: discharge in [0.8, 1.0] — bright streak (R_max = 220 in crop)

The 4-class head is retained for Wave 3 API compatibility. Smoke test confirms:
- `discharge=0.85, flag=True` → argmax = 3 (in {2, 3}) ✓
- `discharge=0.0, flag=False` → argmax = 0 ✓

## Load Instructions

```python
import torch
import torch.nn as nn
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights

model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
model.classifier[3] = nn.Linear(model.classifier[3].in_features, 4)
state = torch.load("src/skyherd/vision/_models/pinkeye_mbv3s.pth",
                   map_location="cpu", weights_only=True)
model.load_state_dict(state)
model.eval()
```

## License Caveats

The base weights are torchvision's `MobileNet_V3_Small_Weights.IMAGENET1K_V1`,
trained on ImageNet-1k which was released under research-use-only terms. For a
hackathon demo (non-deployed, non-revenue-generating), this is acceptable standard
practice — see pytorch/vision issue 2597. For any commercial productization of
SkyHerd, these weights should be replaced by:

(a) Retraining from scratch on synthetic-only data (`weights=None`, requires more
    epochs and a larger synthetic dataset), or
(b) Swapping to a commercially-licensed backbone (e.g., EfficientNet-Lite trained
    on CC-BY data).

## Reproduction

To regenerate with the same torch / torchvision version on the same CPU:

```bash
uv run python scripts/train_pinkeye_classifier.py --frames 500 --seed 42 --epochs 40
```

The resulting `pinkeye_mbv3s.pth` will match this SHA-256 on the same machine and
torch version. Note: the training requires ~40 epochs for the frozen-backbone
classifier to find the red streak signal (warm-up period epochs 1-14, breakout
begins epoch 15).
