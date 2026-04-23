# Phase 2: Vision Pixel Inference - Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 10 new/modified files
**Analogs found:** 8 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/skyherd/vision/heads/pinkeye.py` | model (pixel-head) | transform (image → DetectionResult) | `src/skyherd/vision/heads/pinkeye.py` (current, rule-based) + `src/skyherd/edge/detector.py::MegaDetectorHead` | exact interface + role-match for lazy-model-load pattern |
| `src/skyherd/vision/result.py` | model | transform | `src/skyherd/vision/result.py` (current — Pydantic v2 BaseModel) | exact |
| `src/skyherd/vision/renderer.py` | utility | transform | `src/skyherd/vision/renderer.py` (current — annotate_frame) | exact (extend in-place) |
| `src/skyherd/vision/pipeline.py` | service | request-response | `src/skyherd/vision/pipeline.py` (current — ClassifyPipeline) | exact (extend in-place) |
| `src/skyherd/vision/_models/__init__.py` | config | — | `src/skyherd/vision/__init__.py` (empty package marker) | role-match |
| `src/skyherd/vision/preprocess.py` | utility | transform | `src/skyherd/edge/detector.py::RuleDetector` (numpy array ops) | partial |
| `src/skyherd/vision/detector.py` (new vision-tier) | utility | transform | `src/skyherd/edge/detector.py` (geometric bbox) | role-match |
| `scripts/train_pinkeye_classifier.py` | utility (dev-time) | batch | `scripts/build-replay.py` (standalone runnable script pattern) | role-match |
| `tests/vision/test_heads/test_pinkeye.py` | test | — | `tests/vision/test_heads/test_pinkeye.py` (current) + `tests/vision/test_heads/test_brd.py` | exact (extend) |
| `tests/test_licenses.py` | test | — | No analog — invent from `tests/test_smoke.py` structural pattern | no analog |

---

## Pattern Assignments

---

### `src/skyherd/vision/heads/pinkeye.py` (pixel head rewrite)

**Analog 1 — ABC interface:** `src/skyherd/vision/heads/pinkeye.py` (current file, lines 1-89)
**Analog 2 — lazy model-load pattern:** `src/skyherd/edge/detector.py::MegaDetectorHead` (lines 80-170)

**Imports pattern** (from current pinkeye.py, lines 1-12):
```python
from __future__ import annotations

import functools
import importlib.resources
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

from skyherd.vision.heads.base import Head
from skyherd.vision.result import DetectionResult, Severity
from skyherd.world.cattle import Cow
```

**ABC contract** (from `src/skyherd/vision/heads/base.py`, lines 27-65 — copy exactly):
```python
@property
@abstractmethod
def name(self) -> str: ...

def should_evaluate(self, cow: Cow, frame_meta: dict[str, Any]) -> bool: ...

@abstractmethod
def classify(self, cow: Cow, frame_meta: dict[str, Any]) -> DetectionResult | None: ...
```

**Lazy-singleton model-load pattern** (from `src/skyherd/edge/detector.py::MegaDetectorHead`, lines 96-115):
```python
def __init__(self) -> None:
    self._model: object | None = None
    self._fallback: RuleDetector | None = None
    self._init_attempted = False

def _ensure_model(self) -> None:
    """Lazy-initialise the MegaDetector model once."""
    if self._init_attempted:
        return
    self._init_attempted = True
    try:
        ...
        self._model = ...
        logger.info("Model loaded")
    except (ImportError, Exception) as exc:  # noqa: BLE001
        logger.warning("Model unavailable (%s) — falling back", exc)
        self._fallback = RuleDetector()
```

**Adapt for pinkeye.py** — use `@functools.lru_cache(maxsize=1)` instead of instance flag:
```python
@functools.lru_cache(maxsize=1)
def _get_model() -> nn.Module:
    model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, 4)
    weight_path = importlib.resources.files("skyherd.vision._models") / "pinkeye_mbv3s.pth"
    state = torch.load(str(weight_path), map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(mode=True, warn_only=True)
    return model
```

**should_evaluate gate** (from current pinkeye.py, line 30-32 — preserve exactly):
```python
def should_evaluate(self, cow: Cow, frame_meta: dict[str, Any]) -> bool:  # noqa: ARG002
    """Skip cows with no ocular discharge and no disease flag."""
    return cow.ocular_discharge > 0.4 or "pinkeye" in cow.disease_flags
```

**Core classify pattern** (from current pinkeye.py, lines 34-89 — severity mapping preserved; mechanism becomes pixel inference):
```python
def classify(self, cow: Cow, frame_meta: dict[str, Any]) -> DetectionResult | None:
    # Gate check (redundant safety)
    if not self.should_evaluate(cow, frame_meta):
        return None

    raw_path: Path | None = frame_meta.get("raw_path")
    if raw_path is None:
        # Fallback to rule-based if no frame available (e.g. rule-only tests)
        return self._rule_fallback(cow)

    # Load frame + locate cow bbox via geometric projection
    bbox = _cow_bbox_in_frame(cow, ...)  # see detector.py pattern
    eye_crop = _crop_eye_region(raw_path, bbox)

    model = _get_model()
    with torch.no_grad():
        logits = model(eye_crop.unsqueeze(0))
        probs = torch.softmax(logits, dim=1)[0]
        severity_idx = int(probs.argmax())
        confidence = float(probs[severity_idx])

    _CLASSES = ["healthy", "watch", "log", "escalate"]
    if _CLASSES[severity_idx] == "healthy":
        return None

    severity: Severity = _CLASSES[severity_idx]  # type: ignore[assignment]
    return DetectionResult(
        head_name=self.name,
        cow_tag=cow.tag,
        confidence=round(confidence, 2),
        severity=severity,
        reasoning=(
            f"Pixel classifier (MobileNetV3-Small) on cow {cow.tag}: "
            f"{_CLASSES[severity_idx]} (p={confidence:.2f}). "
            "Per `skills/cattle-behavior/disease/pinkeye.md` §Decision rules."
        ),
        bbox=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
    )
```

**Reasoning must cite skill** (from existing test `test_reasoning_contains_skill_reference`, pinkeye.py line 53):
```python
# Pattern: reasoning string MUST contain "pinkeye.md"
"Per `skills/cattle-behavior/disease/pinkeye.md` §Decision rules."
```

---

### `src/skyherd/vision/result.py` (add `bbox` field)

**Analog:** `src/skyherd/vision/result.py` (current, lines 1-22)

**Existing Pydantic v2 BaseModel pattern** (lines 1-22 — full file, copy and extend):
```python
"""DetectionResult — output of a single disease-detection head."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["watch", "log", "escalate", "vet_now"]


class DetectionResult(BaseModel):
    """Pydantic model returned by each disease-detection head."""

    head_name: str
    cow_tag: str
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Severity
    reasoning: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    # NEW: real pixel bbox from pixel head; None for rule-based heads (backwards-compatible)
    bbox: tuple[float, float, float, float] | None = Field(default=None)
```

**Backwards-compatibility note:** Pydantic v2 `.model_dump()` emits `bbox: null` for rule heads. Downstream SSE serializers or snapshot tests that assert on exact dict keys must be updated. Use `model_config = ConfigDict(ser_json_exclude_none=True)` or update assertions.

---

### `src/skyherd/vision/renderer.py` (extend `annotate_frame`)

**Analog:** `src/skyherd/vision/renderer.py::annotate_frame` (lines 262-341 — full function)

**Current grid-layout bbox construction** (lines 316-327 — replace this section):
```python
for i, det in enumerate(detections):
    # Spread boxes across the frame in a grid layout
    col = i % 4
    row = i // 4
    x0 = col * (w // 4) + 10
    y0 = row * (h // 5) + 10
    x1 = min(x0 + box_w, w - 5)
    y1 = min(y0 + box_h, h - 5)
    xyxy.append([float(x0), float(y0), float(x1), float(y1)])
```

**New pattern — branch on `det.bbox`:**
```python
for i, det in enumerate(detections):
    if det.bbox is not None:
        # Real pixel bbox from pixel head — use directly
        xyxy.append(list(det.bbox))
    else:
        # Grid layout fallback for rule-based heads (preserves existing behavior)
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

**supervision Detections + annotators** (lines 329-340 — copy exactly, unchanged):
```python
sv_detections = sv.Detections(
    xyxy=np.array(xyxy, dtype=float),
    class_id=np.array(class_ids, dtype=int),
)
box_annotator = sv.BoxAnnotator()
label_annotator = sv.LabelAnnotator()
annotated = box_annotator.annotate(scene=frame, detections=sv_detections)
annotated = label_annotator.annotate(scene=annotated, detections=sv_detections, labels=labels)
Image.fromarray(annotated).save(str(out_path), "PNG")
```

---

### `src/skyherd/vision/pipeline.py` (add `raw_path` to `frame_meta`)

**Analog:** `src/skyherd/vision/pipeline.py::ClassifyPipeline.run` (lines 65-96)

**Current `frame_meta` construction** (lines 76-82 — extend this block):
```python
weather = world.weather_driver.current
frame_meta: dict[str, Any] = {
    "trough_id": trough_id,
    "temp_f": weather.temp_f,
}
if frame_meta_override:
    frame_meta.update(frame_meta_override)
```

**New pattern — inject `raw_path` after rendering:**
```python
raw_path = out_dir / f"raw_{trough_id}.png"
render_trough_frame(world, trough_id, out_path=raw_path)

weather = world.weather_driver.current
frame_meta: dict[str, Any] = {
    "trough_id": trough_id,
    "temp_f": weather.temp_f,
    "raw_path": raw_path,  # NEW — pixel head reads this key
}
if frame_meta_override:
    frame_meta.update(frame_meta_override)
```

**Note:** The `raw_path` key is new but safe — `Head.classify` docstring already states "Heads must tolerate missing keys." All 6 rule heads ignore unknown keys.

---

### `src/skyherd/vision/preprocess.py` (new — PNG→tensor helpers)

**Analog:** `src/skyherd/edge/detector.py::RuleDetector.detect` (lines 55-72) for numpy array ops pattern + `src/skyherd/vision/renderer.py::_world_to_frame` (lines 39-51) for coordinate math pattern

**Imports pattern** (mirroring edge/detector.py numpy + PIL style):
```python
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms
```

**Core preprocessing transform** (from RESEARCH.md Pattern 2):
```python
_PREPROCESS = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


def load_frame_as_array(path: Path) -> np.ndarray:
    """Load PNG at path as RGB uint8 HxWx3 numpy array."""
    return np.array(Image.open(str(path)).convert("RGB"))


def crop_region(arr: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    """Crop arr to bbox (x0, y0, x1, y1). Returns HxWx3 uint8."""
    x0, y0, x1, y1 = bbox
    return arr[y0:y1, x0:x1]


def array_to_tensor(crop: np.ndarray) -> torch.Tensor:
    """Convert HxWx3 uint8 numpy crop to preprocessed (1,3,224,224) tensor."""
    img = Image.fromarray(crop)
    return _PREPROCESS(img)
```

---

### `src/skyherd/vision/detector.py` (new vision-tier — geometric cow bbox)

**Analog:** `src/skyherd/vision/renderer.py::_world_to_frame` + `_draw_cow_blob` (lines 39-98) — the renderer is the oracle for cow positions

**Key: read `renderer._world_to_frame` semantics exactly** (lines 39-51):
```python
def _world_to_frame(
    pos: tuple[float, float],
    bounds_m: tuple[float, float],
    frame_w: int,
    frame_h: int,
) -> tuple[int, int]:
    fx = int(pos[0] / bounds_m[0] * frame_w)
    fy = int((1.0 - pos[1] / bounds_m[1]) * frame_h)  # Y flipped
    return (
        max(0, min(frame_w - 1, fx)),
        max(0, min(frame_h - 1, fy)),
    )
```

**Cow blob dimensions** (from `renderer._draw_cow_blob`, lines 54-98):
```python
# r_x, r_y = 18, 12 (body ellipse half-axes)
# hx = cx + r_x - 4  (head x)
# hy = cy - r_y + tilt - 6  (head y, includes tilt = cow.lameness_score)
# eye streak at (hx+1, hy) to (hx+3, hy+14)
```

**cow_bbox_in_frame pattern** (from RESEARCH.md Pattern 1):
```python
_FRAME_W, _FRAME_H = 640, 480
_R_X, _R_Y = 18, 12
_PAD = 4


def cow_bbox_in_frame(
    cow: "Cow",
    bounds_m: tuple[float, float],
) -> tuple[int, int, int, int]:
    """Return (x0, y0, x1, y1) pixel bbox for cow body+head in the trough frame."""
    fx = int(cow.pos[0] / bounds_m[0] * _FRAME_W)
    fy = int((1.0 - cow.pos[1] / bounds_m[1]) * _FRAME_H)
    fx = max(0, min(_FRAME_W - 1, fx))
    fy = max(0, min(_FRAME_H - 1, fy))
    tilt = cow.lameness_score
    return (
        max(0, fx - _R_X - _PAD),
        max(0, fy - _R_Y - 16 + tilt),  # include head+eye region above body
        min(_FRAME_W - 1, fx + _R_X + _PAD),
        min(_FRAME_H - 1, fy + _R_Y + tilt + 2),
    )


def eye_crop_bbox(
    cow_bbox: tuple[int, int, int, int],
    cow: "Cow",
) -> tuple[int, int, int, int]:
    """Return 48×48 pixel window around the eye region within cow_bbox."""
    # Eye position mirrors _draw_cow_blob: hx = cx + r_x - 4, hy = cy - r_y + tilt - 6
    # Compute cx/cy from cow_bbox midpoint
    x0, y0, x1, y1 = cow_bbox
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    hx = cx + _R_X - 4
    hy = cy - _R_Y + cow.lameness_score - 6
    half = 24
    return (
        max(0, hx - half),
        max(0, hy - half),
        min(_FRAME_W - 1, hx + half),
        min(_FRAME_H - 1, hy + half),
    )
```

---

### `src/skyherd/vision/_models/__init__.py` (new package marker)

**Analog:** `src/skyherd/vision/__init__.py` (empty package marker — 0 bytes or docstring only)

**Pattern:**
```python
"""Pre-trained weights package — accessed via importlib.resources."""
```

**pyproject.toml extension** (from current `[tool.hatch.build.targets.wheel]`, line 91):
```toml
# Current:
packages = ["src/skyherd"]

# No change needed — hatchling includes all files under src/skyherd by default.
# Verify .pth file is not .gitignored and weights_only=True is used in torch.load.
```

---

### `scripts/train_pinkeye_classifier.py` (dev-time only)

**Analog:** `scripts/build-replay.py` (lines 1-222) — standalone runnable script

**Script skeleton pattern** (from build-replay.py lines 1-15, 165-222):
```python
#!/usr/bin/env python3
"""One-off training script: generates synthetic pinkeye frames and fine-tunes
MobileNetV3-Small head. Run once at phase-plan time; output .pth is checked
into src/skyherd/vision/_models/.

Usage:
  uv run python scripts/train_pinkeye_classifier.py [--frames 500] [--seed 42]

NOT run in CI or at runtime.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    ...


if __name__ == "__main__":
    main()
```

**sys.path pattern from build-replay.py** (implicit — script imports from `skyherd.*`):
```python
# pyproject.toml has pythonpath=["src"] for pytest; scripts rely on uv run
# which activates the venv. No sys.path manipulation needed.
```

---

### `tests/vision/test_heads/test_pinkeye.py` (rewrite / extend)

**Primary analog:** `tests/vision/test_heads/test_pinkeye.py` (current, lines 1-94 — preserve all existing test names; update mechanism)
**Secondary analog:** `tests/vision/test_heads/test_brd.py` (lines 1-111 — additional test naming and structure patterns)
**Tertiary analog for pixel tests:** `tests/vision/test_pipeline.py` (lines 1-67 — `pytest.importorskip("cv2", ...)` guard + `tmp_path` fixture + world fixtures)

**Module-level head instantiation** (from current test_pinkeye.py, lines 8-9):
```python
_HEAD = Pinkeye()
_META: dict = {}
```

**`_make_cow` helper** (from current test_pinkeye.py, lines 12-21 — add `pos` param for pixel tests):
```python
def _make_cow(
    tag: str = "T001",
    ocular_discharge: float = 0.0,
    disease_flags: set[str] | None = None,
    pos: tuple[float, float] = (300.0, 300.0),
    lameness_score: int = 0,
) -> Cow:
    return Cow(
        id=f"cow_{tag}",
        tag=tag,
        pos=pos,
        ocular_discharge=ocular_discharge,
        disease_flags=disease_flags or set(),
        lameness_score=lameness_score,
    )
```

**Rule-path tests** (from current test_pinkeye.py, lines 27-94 — keep ALL of these; they run against `frame_meta={}` i.e. `raw_path` absent → rule fallback):
```python
def test_healthy_cow_no_detection() -> None: ...
def test_below_threshold_no_detection() -> None: ...
def test_watch_at_low_discharge() -> None: ...
def test_log_at_mid_discharge() -> None: ...
def test_escalate_at_high_discharge() -> None: ...
def test_escalate_at_max_discharge() -> None: ...
def test_flag_overrides_low_discharge() -> None: ...
def test_reasoning_contains_skill_reference() -> None: ...
def test_reasoning_contains_cow_tag() -> None: ...
```

**cv2 guard pattern for pixel tests** (from test_pipeline.py, lines 9-13 and test_annotate.py lines 9-13):
```python
# At module top — pixel tests require torch + PIL (no cv2 needed for inference only)
# No importorskip needed for the inference path — only annotation path needs cv2.
# Split: inference tests (no guard) vs annotation integration tests (cv2 guard).
```

**Pixel-path test pattern** (new, adapting `test_pipeline.py` fixture + `world_with_sick_cow`):
```python
def test_pixel_head_returns_bbox_for_sick_cow(
    world_with_sick_cow: World, tmp_path: Path
) -> None:
    """Pixel head sets DetectionResult.bbox when raw_path present."""
    raw = tmp_path / "raw_trough_a.png"
    render_trough_frame(world_with_sick_cow, "trough_a", out_path=raw)
    frame_meta = {"raw_path": raw, "trough_id": "trough_a"}
    sick_cow = world_with_sick_cow.herd.cows[0]
    result = _HEAD.classify(sick_cow, frame_meta)
    assert result is not None
    assert result.bbox is not None
    x0, y0, x1, y1 = result.bbox
    assert x0 < x1 and y0 < y1  # valid box
    assert 0 <= x0 <= 639 and 0 <= x1 <= 639
    assert 0 <= y0 <= 479 and 0 <= y1 <= 479
```

**Determinism test pattern** (from `tests/vision/test_renderer.py::test_render_trough_frame_deterministic`, lines 39-45):
```python
def test_pixel_head_is_deterministic(world_with_sick_cow: World, tmp_path: Path) -> None:
    """Same world + same frame → identical DetectionResult twice."""
    raw = tmp_path / "raw.png"
    render_trough_frame(world_with_sick_cow, "trough_a", out_path=raw)
    frame_meta = {"raw_path": raw}
    sick = world_with_sick_cow.herd.cows[0]
    r1 = _HEAD.classify(sick, frame_meta)
    r2 = _HEAD.classify(sick, frame_meta)
    assert r1 == r2  # bit-identical via model.eval() + torch.set_num_threads(1)
```

**Skill-reference test** (preserve from current, line 81-84):
```python
def test_reasoning_contains_skill_reference() -> None:
    """Reasoning must cite the skill file — preserved from rule-head tests."""
    result = _HEAD.classify(_make_cow(ocular_discharge=0.9), _META)
    assert result is not None
    assert "pinkeye.md" in result.reasoning
```

---

### `tests/test_licenses.py` (new — no close analog)

**Closest analog:** `tests/test_smoke.py` (structural: simple import + assert at module level, no fixtures)

**Pattern — subprocess-based license guard:**
```python
"""License guard: assert no AGPL/GPL packages in the base dep closure."""

from __future__ import annotations

import subprocess
import sys


def test_no_agpl_in_base_deps() -> None:
    """uv tree must not contain ultralytics or yolov5 in base (non-extra) deps."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "show", "ultralytics"],
        capture_output=True,
        text=True,
    )
    # ultralytics must NOT be importable from the base venv
    assert result.returncode != 0, (
        "ultralytics (AGPL-3.0) is installed in the base dep closure. "
        "Remove PytorchWildlife from base deps immediately."
    )


def test_torch_importable() -> None:
    """torch must be importable (base dep via transitive)."""
    import torch  # noqa: F401
```

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** Every existing Python file in `src/skyherd/`
**Apply to:** All new `.py` files — mandatory project convention.

### Pydantic v2 BaseModel field definition
**Source:** `src/skyherd/vision/result.py` (lines 13-22) + `src/skyherd/edge/detector.py` (lines 15-25)
```python
from pydantic import BaseModel, Field

class MyModel(BaseModel):
    field: str
    optional_field: float | None = Field(default=None)
    bounded: float = Field(ge=0.0, le=1.0)
```
**Apply to:** `result.py` (bbox field addition), any new data models.

### `pytest.importorskip("cv2", ...)` guard
**Source:** `tests/vision/test_pipeline.py` (lines 9-13), `tests/vision/test_annotate.py` (lines 9-13)
```python
pytest.importorskip("cv2", reason="opencv-python not installed in this environment")
```
**Apply to:** Any test file that calls `annotate_frame()` or uses `supervision.BoxAnnotator`. Do NOT apply to pure inference tests (pixel head classify, preprocess, detector) — those don't need cv2.

### Module-level logger
**Source:** `src/skyherd/edge/detector.py` (line 12)
```python
import logging
logger = logging.getLogger(__name__)
```
**Apply to:** `src/skyherd/vision/heads/pinkeye.py`, `src/skyherd/vision/preprocess.py`, `src/skyherd/vision/detector.py`

### `from __future__ import annotations` + type-only `Cow` import
**Source:** `src/skyherd/vision/heads/base.py` (lines 1-9)
```python
from __future__ import annotations
from typing import Any
from skyherd.vision.result import DetectionResult
from skyherd.world.cattle import Cow
```
**Apply to:** All head files and the new `detector.py`.

### `tmp_path` + world fixture pattern for integration tests
**Source:** `tests/vision/test_pipeline.py` (lines 17-23), `tests/vision/conftest.py` (lines 69-122)
```python
def test_something(world_with_sick_cow: World, tmp_path: Path) -> None:
    pipeline = ClassifyPipeline()
    result = pipeline.run(world_with_sick_cow, "trough_a", out_dir=tmp_path)
    assert result.detection_count >= 1
```
**Apply to:** All new vision integration tests in `tests/vision/test_heads/test_pinkeye.py` that need a rendered frame.

### Standalone script skeleton
**Source:** `scripts/build-replay.py` (lines 1-15, 165-222)
```python
#!/usr/bin/env python3
"""Docstring with Usage: block."""
from __future__ import annotations
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

def main() -> None:
    ...

if __name__ == "__main__":
    main()
```
**Apply to:** `scripts/train_pinkeye_classifier.py`

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `tests/test_licenses.py` | test | — | No license-guard test exists in the codebase; invent from structural pattern of simple no-fixture tests like `tests/test_smoke.py` |
| `src/skyherd/vision/_models/pinkeye_mbv3s.pth` | binary asset | — | Not a code file; produced by `scripts/train_pinkeye_classifier.py` at phase-plan time; no pattern to extract |

---

## Metadata

**Analog search scope:** `src/skyherd/vision/`, `src/skyherd/edge/`, `scripts/`, `tests/vision/`, `tests/`
**Files scanned:** 15 source files, 10 test files
**Pattern extraction date:** 2026-04-22
