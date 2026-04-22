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

    Performance gate
    ----------------
    :meth:`should_evaluate` is called **before** :meth:`classify` and must be
    cheap (no model inference).  Return ``False`` to skip the full classify
    pass for cows that cannot possibly trigger this head.  The default
    implementation returns ``True`` (evaluate all cows) so existing heads
    work unchanged until they opt in.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this head (used in DetectionResult.head_name)."""

    def should_evaluate(self, cow: Cow, frame_meta: dict[str, Any]) -> bool:  # noqa: ARG002
        """Return True if this cow warrants a full classify() call.

        Override in subclasses to gate expensive classification on cheap
        pre-conditions (e.g. lameness score threshold, disease flags present).
        The default returns True — always evaluate.

        Parameters
        ----------
        cow:
            Current cow state.
        frame_meta:
            Ambient sensor data for this frame.
        """
        return True

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
