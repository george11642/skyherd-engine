"""Pinkeye (IBK — Infectious Bovine Keratoconjunctivitis) detection head.

Thresholds aligned with skills/cattle-behavior/disease/pinkeye.md §Decision rules.
"""

from __future__ import annotations

from typing import Any

from skyherd.vision.heads.base import Head
from skyherd.vision.result import DetectionResult, Severity
from skyherd.world.cattle import Cow


class Pinkeye(Head):
    """Detects ocular discharge indicative of IBK.

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
        )
