"""Pinkeye (IBK — Infectious Bovine Keratoconjunctivitis) detection head.

Pixel-level inference via MobileNetV3-Small fine-tuned on synthetic frames.
Falls back to rule-based severity mapping on Cow.ocular_discharge when no
frame is available — preserves Head ABC 'tolerate missing keys' contract.

Thresholds + reasoning aligned with skills/cattle-behavior/disease/pinkeye.md.
"""

from __future__ import annotations

import functools
import importlib.resources
import logging
from pathlib import Path
from typing import Any, cast

import torch
import torch.nn as nn
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

from skyherd.vision.detector import cow_bbox_in_frame, eye_crop_bbox
from skyherd.vision.heads.base import Head
from skyherd.vision.preprocess import array_to_tensor, crop_region, load_frame_as_array
from skyherd.vision.result import DetectionResult, Severity
from skyherd.world.cattle import Cow

logger = logging.getLogger(__name__)

# Class index → Severity mapping (indices match Plan 03 label_for_cow):
# 0 → None (healthy, no detection), 1 → watch, 2 → log, 3 → escalate
_CLASS_TO_SEVERITY: tuple[Severity | None, ...] = (None, "watch", "log", "escalate")


# ---------------------------------------------------------------------------
# Model loader — loaded exactly once per process via lru_cache
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _get_model() -> nn.Module | None:
    """Build MobileNetV3-Small architecture, load fine-tuned state_dict.

    Returns ``None`` on failure (file missing, corrupt, etc.) so the caller
    can fall back to rule-based classification gracefully.

    Called at most once per process; subsequent calls return the cached object.
    """
    try:
        weights_ref = importlib.resources.files("skyherd.vision._models") / "pinkeye_mbv3s.pth"
        with importlib.resources.as_file(weights_ref) as weights_path:
            model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
            model.classifier[3] = nn.Linear(cast(int, model.classifier[3].in_features), 4)
            state = torch.load(str(weights_path), map_location="cpu", weights_only=True)
            model.load_state_dict(state)
            model.eval()
            torch.set_num_threads(1)
            torch.use_deterministic_algorithms(mode=True, warn_only=True)
            logger.info("Pinkeye pixel classifier loaded from %s", weights_path)
            return model
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Pinkeye pixel model unavailable (%s) — falling back to rule-based classification",
            exc,
        )
        return None


# ---------------------------------------------------------------------------
# Head class
# ---------------------------------------------------------------------------


class Pinkeye(Head):
    """Pixel-level pinkeye detector; rule-based fallback when no frame available.

    Decision rules (from pinkeye.md):
    - discharge 0.0–0.4 : below threshold — no detection
    - discharge 0.4–0.6 : Tier 1 watch — unilateral tearing, recheck in 48 hrs
    - discharge 0.6–0.8 : Tier 2 log — central corneal opacity; antibiotic within 24 hrs
    - discharge 0.8–1.0 : Tier 3 escalate — bilateral or deep ulcer; blindness risk
    - disease_flag "pinkeye" present : override to minimum "log" regardless of score
    """

    @property
    def name(self) -> str:
        return "pinkeye"

    def should_evaluate(self, cow: Cow, frame_meta: dict[str, Any]) -> bool:  # noqa: ARG002
        """Skip cows with no ocular discharge and no disease flag."""
        return cow.ocular_discharge > 0.4 or "pinkeye" in cow.disease_flags

    def classify(self, cow: Cow, frame_meta: dict[str, Any]) -> DetectionResult | None:
        """Classify a single cow for pinkeye.

        Attempts pixel inference when ``frame_meta['raw_path']`` is present and
        readable. Falls back to rule-based severity mapping when the frame is
        unavailable or the model failed to load.
        """
        if not self.should_evaluate(cow, frame_meta):
            return None

        raw_path = frame_meta.get("raw_path")
        bounds_m: tuple[float, float] = frame_meta.get("bounds_m", (2000.0, 2000.0))

        # Attempt pixel path
        if raw_path is not None:
            raw_path = Path(raw_path)
            if raw_path.exists():
                pixel_result = self._classify_pixel(cow, raw_path, bounds_m)
                if pixel_result is not None:
                    # Model returned a severity — use it
                    return pixel_result
                # _classify_pixel returned None for one of two reasons:
                #   a) Model predicted class 0 (healthy) — genuine no-detection
                #   b) Model unavailable — fall through to rule fallback
                if _get_model() is not None:
                    # Case (a): model is loaded and healthy → class 0 → no detection
                    return None
                # Case (b): model unavailable → fall through to rule

        # Rule fallback (no frame OR model unavailable)
        return self._classify_rule(cow)

    # ------------------------------------------------------------------
    # Pixel path
    # ------------------------------------------------------------------

    def _classify_pixel(
        self, cow: Cow, raw_path: Path, bounds_m: tuple[float, float]
    ) -> DetectionResult | None:
        """Run MobileNetV3-Small forward pass; return None on healthy or error."""
        model = _get_model()
        if model is None:
            return None
        try:
            arr = load_frame_as_array(raw_path)
            cow_bbox = cow_bbox_in_frame(cow, bounds_m)
            eye_bbox = eye_crop_bbox(cow_bbox, cow)
            crop = crop_region(arr, eye_bbox)
            tensor = array_to_tensor(crop).unsqueeze(0)
            with torch.no_grad():
                logits = model(tensor)
                probs = torch.softmax(logits, dim=1)[0]
                severity_idx = int(probs.argmax().item())
                confidence = float(probs[severity_idx].item())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pinkeye pixel inference failed on %s: %s", cow.tag, exc)
            return None

        severity = _CLASS_TO_SEVERITY[severity_idx]
        if severity is None:
            # Model predicts healthy (class 0) — caller decides whether to rule-fall-back
            return None

        class_names = ("healthy", "watch", "log", "escalate")
        reasoning = (
            f"Pixel classifier (MobileNetV3-Small) on tag {cow.tag}: "
            f"{class_names[severity_idx]} (p={confidence:.2f}). "
            "Per `skills/cattle-behavior/disease/pinkeye.md` §Decision rules."
        )
        return DetectionResult(
            head_name=self.name,
            cow_tag=cow.tag,
            confidence=round(confidence, 2),
            severity=severity,
            reasoning=reasoning,
            bbox=(
                float(cow_bbox[0]),
                float(cow_bbox[1]),
                float(cow_bbox[2]),
                float(cow_bbox[3]),
            ),
        )

    # ------------------------------------------------------------------
    # Rule fallback — preserved byte-for-byte from pre-Phase-2
    # ------------------------------------------------------------------

    def _classify_rule(self, cow: Cow) -> DetectionResult | None:
        """Original rule-based severity mapping — preserved byte-for-byte from pre-Phase-2."""
        discharge = cow.ocular_discharge
        has_flag = "pinkeye" in cow.disease_flags

        if discharge <= 0.4 and not has_flag:
            return None

        severity: Severity
        confidence: float
        reasoning: str

        if has_flag and discharge <= 0.4:
            # Flag present but discharge below visual threshold — early/flag-only detection
            severity = "log"
            confidence = 0.70
            reasoning = (
                f"Disease flag 'pinkeye' set on tag {cow.tag}; ocular discharge score "
                f"{discharge:.2f} is below visual threshold but flag overrides to Tier 2 log. "
                "Recommend antibiotic evaluation per "
                "`skills/cattle-behavior/disease/pinkeye.md` §Decision rules."
            )
        elif discharge < 0.6:
            severity = "watch"
            confidence = round(0.5 + (discharge - 0.4) * 2.5, 2)
            reasoning = (
                f"Ocular discharge score {discharge:.2f}/1.0 on tag {cow.tag} — consistent "
                "with unilateral tearing (epiphora) without confirmed opacity. "
                "Tier 1 watch: recheck in 48 hrs per "
                "`skills/cattle-behavior/disease/pinkeye.md` §Decision rules."
            )
        elif discharge < 0.8:
            severity = "log"
            confidence = round(0.65 + (discharge - 0.6) * 1.5, 2)
            reasoning = (
                f"Ocular discharge score {discharge:.2f}/1.0 on tag {cow.tag} — "
                "central corneal opacity likely; dark facial staining and blepharospasm "
                "visible. Tier 2: antibiotic treatment within 24 hrs and UV shade per "
                "`skills/cattle-behavior/disease/pinkeye.md` §Decision rules."
            )
        else:
            severity = "escalate"
            confidence = round(min(1.0, 0.80 + (discharge - 0.8) * 1.0), 2)
            reasoning = (
                f"Ocular discharge score {discharge:.2f}/1.0 on tag {cow.tag} — "
                "bilateral opacity or deep corneal ulcer suspected; blindness risk. "
                "Tier 3: rancher call and vet evaluation recommended per "
                "`skills/cattle-behavior/disease/pinkeye.md` §Decision rules."
            )

        return DetectionResult(
            head_name=self.name,
            cow_tag=cow.tag,
            confidence=confidence,
            severity=severity,
            reasoning=reasoning,
            # bbox left as None — rule fallback has no pixel information
        )
