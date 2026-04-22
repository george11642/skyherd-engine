"""Detector abstraction — MegaDetectorHead (hardware) or RuleDetector (offline/CI)."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Detection(BaseModel):
    """Single detection emitted by a Detector."""

    tag_guess: str
    """Best-guess animal category (e.g. 'animal', 'cattle', 'person')."""
    bbox: list[float]
    """Bounding box as [x1, y1, x2, y2] in pixel coordinates."""
    confidence: float = Field(ge=0.0, le=1.0)
    """Detection confidence in [0, 1]."""
    frame_ts: float = Field(default_factory=time.time)
    """Unix timestamp when the frame was captured."""


class Detector(ABC):
    """Abstract detector — takes a raw frame, returns a list of Detections."""

    @abstractmethod
    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Run detection on *frame* (RGB HxWx3 uint8) and return results."""


# ---------------------------------------------------------------------------
# Rule-based detector — runs entirely offline, no model weights required
# ---------------------------------------------------------------------------

# These thresholds mirror the cattle-behavior skill files so the offline
# detector stays consistent with the sim vision heads.
_RULE_CONFIDENCE = 0.72
_OCCUPANCY_THRESHOLD = 0.05  # mean brightness fraction that implies "something present"


class RuleDetector(Detector):
    """Lightweight heuristic detector — compatible with CI and non-GPU hosts.

    Uses simple image statistics (brightness, contrast) to decide whether
    anything resembling a large animal is present in the frame.  Returns at
    most one synthetic detection per call so downstream tests can validate
    the full publish pipeline without real model weights.
    """

    def detect(self, frame: np.ndarray) -> list[Detection]:
        h, w = frame.shape[:2]
        # Normalise to [0,1]
        norm = frame.astype(np.float32) / 255.0
        mean_brightness = float(norm.mean())

        if mean_brightness > _OCCUPANCY_THRESHOLD:
            # Synthetic bounding box covering the centre third of the frame
            x1, y1 = w // 3, h // 3
            x2, y2 = 2 * w // 3, 2 * h // 3
            return [
                Detection(
                    tag_guess="animal",
                    bbox=[float(x1), float(y1), float(x2), float(y2)],
                    confidence=_RULE_CONFIDENCE,
                )
            ]
        return []


# ---------------------------------------------------------------------------
# MegaDetector V6 head — requires PytorchWildlife installed
# ---------------------------------------------------------------------------


class MegaDetectorHead(Detector):
    """Animal detector backed by MegaDetector V6 via PytorchWildlife (MIT).

    Lazy-imports ``PytorchWildlife`` so the module loads on any host.  Falls
    back transparently to :class:`RuleDetector` when weights are missing or
    the package is not installed.

    Usage::

        detector = MegaDetectorHead()
        detections = detector.detect(frame)
    """

    # Category labels from MegaDetector V6 (index → label)
    _CATEGORIES = {1: "animal", 2: "person", 3: "vehicle"}

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
            from PytorchWildlife.models import (  # type: ignore[import-untyped,import-not-found]
                detection as pw_detection,
            )

            self._model = pw_detection.MegaDetectorV6()
            logger.info("MegaDetectorV6 loaded via PytorchWildlife")
        except (ImportError, Exception) as exc:  # noqa: BLE001
            logger.warning("MegaDetectorV6 unavailable (%s) — falling back to RuleDetector", exc)
            self._fallback = RuleDetector()

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Detect animals in *frame*.

        Uses MegaDetector V6 when available; otherwise delegates to
        :class:`RuleDetector` for CI-safe offline operation.
        """
        self._ensure_model()

        if self._fallback is not None:
            return self._fallback.detect(frame)

        ts = time.time()
        detections: list[Detection] = []
        try:
            # PytorchWildlife returns a dict with 'detections' key
            result = self._model.single_image_detection(  # type: ignore[union-attr]
                frame, img_path=None
            )
            raw = result.get("detections", [])
            for det in raw:
                # det is a supervision Detection or dict depending on pw version
                if hasattr(det, "xyxy"):
                    # supervision Detection object
                    for i in range(len(det.xyxy)):
                        bbox = det.xyxy[i].tolist()
                        conf = float(det.confidence[i]) if det.confidence is not None else 0.0
                        cls_id = int(det.class_id[i]) if det.class_id is not None else 1
                        detections.append(
                            Detection(
                                tag_guess=self._CATEGORIES.get(cls_id, "animal"),
                                bbox=bbox,
                                confidence=conf,
                                frame_ts=ts,
                            )
                        )
                else:
                    # dict-style fallback
                    bbox = det.get("bbox", [0.0, 0.0, 1.0, 1.0])
                    conf = float(det.get("conf", 0.0))
                    cls_id = int(det.get("category_id", 1))
                    detections.append(
                        Detection(
                            tag_guess=self._CATEGORIES.get(cls_id, "animal"),
                            bbox=bbox,
                            confidence=conf,
                            frame_ts=ts,
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            logger.error("MegaDetector inference error: %s — falling back to rules", exc)
            self._fallback = RuleDetector()
            return self._fallback.detect(frame)

        return detections
