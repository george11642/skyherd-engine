"""New World Screwworm (Cochliomyia hominivorax) detection head.

Thresholds aligned with skills/cattle-behavior/disease/screwworm.md §Decision rules.
Always vet_now — federally reportable pest (2026 APHIS emergency order).
"""

from __future__ import annotations

from typing import Any

from skyherd.vision.heads.base import Head
from skyherd.vision.result import DetectionResult
from skyherd.world.cattle import Cow


class Screwworm(Head):
    """Detects New World Screwworm larvae in open wounds.

    Decision rules (from screwworm.md):
    - disease_flag "screwworm" : always vet_now (Tier 4 page rancher immediately +
      APHIS report within 24 hrs)
    - disease_flags containing both "open_wound" and "larvae" : same vet_now response
    """

    @property
    def name(self) -> str:
        return "screwworm"

    def classify(self, cow: Cow, frame_meta: dict[str, Any]) -> DetectionResult | None:
        has_screwworm = "screwworm" in cow.disease_flags
        has_larvae_in_wound = "open_wound" in cow.disease_flags and "larvae" in cow.disease_flags

        if not has_screwworm and not has_larvae_in_wound:
            return None

        if has_screwworm:
            trigger = "disease flag 'screwworm' confirmed"
            confidence = 0.95
        else:
            trigger = "flags 'open_wound' + 'larvae' co-present"
            confidence = 0.85

        reasoning = (
            f"Tag {cow.tag}: {trigger}. Larvae visible in wound tissue — obligate "
            "living-tissue parasite consistent with Cochliomyia hominivorax. "
            "Tier 4 mandatory: page rancher immediately, file APHIS Form VS 9-3 "
            "within 24 hrs, isolate animal, contact NM Livestock Board (505-841-6161). "
            "Per `skills/cattle-behavior/disease/screwworm.md` §Decision rules — "
            "do NOT wait for lab confirmation."
        )

        return DetectionResult(
            head_name=self.name,
            cow_tag=cow.tag,
            confidence=confidence,
            severity="vet_now",
            reasoning=reasoning,
        )
