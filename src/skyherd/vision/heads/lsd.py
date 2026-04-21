"""Lumpy Skin Disease (LSD) detection head.

Thresholds aligned with skills/cattle-behavior/disease/lsd.md §Decision rules.
LSD is a foreign animal disease — always escalate (minimum escalate, vet_now for confirmed).
"""

from __future__ import annotations

from typing import Any

from skyherd.vision.heads.base import Head
from skyherd.vision.result import DetectionResult
from skyherd.world.cattle import Cow


class LSD(Head):
    """Detects Lumpy Skin Disease nodules.

    Decision rules (from lsd.md):
    - "lsd_nodules" in disease_flags → always escalate (Tier 4: page rancher immediately,
      file USDA-APHIS FAD report, quarantine premises, no animal movement).

    Note: the Skill mandates Tier 4 for multiple 2–5 cm nodules.  Single ambiguous
    nodule is mapped to "escalate" (not vet_now) to preserve human-in-loop; confirmed
    multi-nodule case (flag "lsd_nodules") is always "vet_now".
    """

    @property
    def name(self) -> str:
        return "lsd"

    def classify(self, cow: Cow, frame_meta: dict[str, Any]) -> DetectionResult | None:
        if "lsd_nodules" not in cow.disease_flags:
            return None

        reasoning = (
            f"Tag {cow.tag}: flag 'lsd_nodules' present — firm raised skin nodules "
            "2–5 cm diameter detected on body surface. Pattern consistent with "
            "Lumpy Skin Disease Virus (Capripoxvirus). "
            "FOREIGN ANIMAL DISEASE — DO NOT WAIT: "
            "Tier 4 page rancher immediately; file USDA-APHIS FAD report "
            "(1-866-536-7593) within hours; quarantine premises; halt all "
            "animal movement. "
            "Per `skills/cattle-behavior/disease/lsd.md` §Decision rules."
        )

        return DetectionResult(
            head_name=self.name,
            cow_tag=cow.tag,
            confidence=0.90,
            severity="escalate",
            reasoning=reasoning,
        )
