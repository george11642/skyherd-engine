"""Abstract base class for disease-detection heads."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from skyherd.vision.result import DetectionResult
from skyherd.world.cattle import Cow


class Head(ABC):
    """A single disease-detection head.

    Each head inspects one :class:`~skyherd.world.cattle.Cow` and returns
    a :class:`~skyherd.vision.result.DetectionResult` if a condition is
    detected, or ``None`` if the cow is clear.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this head (used in DetectionResult.head_name)."""

    @abstractmethod
    def classify(self, cow: Cow, frame_meta: dict[str, Any]) -> DetectionResult | None:
        """Classify a single cow.

        Parameters
        ----------
        cow:
            Current cow state from the world simulation.
        frame_meta:
            Ambient sensor data associated with the frame (e.g. temp_f,
            respiration_bpm, trough_id).  Heads must tolerate missing keys.

        Returns
        -------
        DetectionResult | None
            A result if the condition is detected, else ``None``.
        """
