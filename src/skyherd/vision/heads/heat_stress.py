"""Heat stress (pathological) detection head.

Thresholds aligned with skills/cattle-behavior/disease/heat-stress-disease.md §Decision rules.
"""

from __future__ import annotations

from typing import Any

from skyherd.vision.heads.base import Head
from skyherd.vision.result import DetectionResult, Severity
from skyherd.world.cattle import Cow

# From heat-stress-disease.md:
#   temp_f > 95°F AND health_score < 0.8 → at-risk window
#   "panting" flag alone (any temp)      → watch
#   panting score 3 / not recovering     → Tier 3 (log→escalate)
#   panting score 4 / recumbency         → Tier 4 vet_now

_TEMP_THRESHOLD_F = 95.0
_HEALTH_THRESHOLD = 0.8


def _severity_from_signals(
    has_panting: bool,
    health_score: float,
    temp_f: float,
) -> Severity:
    """Derive severity from combined panting + health + temperature signals.

    heat-stress-disease.md decision rules:
    - panting + high temp + health 0.7–0.8 : watch
    - panting + high temp + health 0.5–0.7 : log (heat exhaustion developing)
    - panting + high temp + health 0.3–0.5 : escalate (heat exhaustion not resolving)
    - panting + high temp + health < 0.3   : vet_now (heat stroke)
    """
    if health_score >= 0.7:
        return "watch"
    if health_score >= 0.5:
        return "log"
    if health_score >= 0.3:
        return "escalate"
    return "vet_now"


class HeatStress(Head):
    """Detects pathological heat stress in cattle.

    Decision rules (from heat-stress-disease.md):
    - temp_f > 95 AND health_score < 0.8 : at-risk; severity by health depth
    - "panting" in disease_flags          : at minimum watch, regardless of temp
    """

    @property
    def name(self) -> str:
        return "heat_stress"

    def should_evaluate(self, cow: Cow, frame_meta: dict[str, Any]) -> bool:
        """Skip cows where neither the ambient nor panting trigger can fire."""
        temp_f: float = frame_meta.get("temp_f", 72.0)
        ambient_possible = temp_f > _TEMP_THRESHOLD_F and cow.health_score < _HEALTH_THRESHOLD
        return ambient_possible or "panting" in cow.disease_flags

    def classify(self, cow: Cow, frame_meta: dict[str, Any]) -> DetectionResult | None:
        temp_f: float = frame_meta.get("temp_f", 72.0)
        has_panting = "panting" in cow.disease_flags

        ambient_trigger = temp_f > _TEMP_THRESHOLD_F and cow.health_score < _HEALTH_THRESHOLD

        if not ambient_trigger and not has_panting:
            return None

        severity = _severity_from_signals(has_panting, cow.health_score, temp_f)
        confidence = round(
            min(
                1.0,
                0.60
                + (max(temp_f - _TEMP_THRESHOLD_F, 0) / 20.0)
                + ((_HEALTH_THRESHOLD - cow.health_score) * 0.5),
            ),
            2,
        )

        panting_detail = " + 'panting' flag set" if has_panting else ""
        reasoning = (
            f"Tag {cow.tag}: ambient temp {temp_f:.1f}°F (threshold >{_TEMP_THRESHOLD_F}°F)"
            f"{panting_detail}; health score {cow.health_score:.2f}. "
        )

        if severity == "watch":
            reasoning += (
                "Panting score 1–2 range; shade and water accessible — "
                "normal heat response boundary. Tier 1 watch: monitor for progression. "
            )
        elif severity == "log":
            reasoning += (
                "Heat exhaustion developing — reduced feed intake, elevated panting. "
                "Tier 2: move to shade, increase water access checks. "
            )
        elif severity == "escalate":
            reasoning += (
                "Panting score 3 equivalent; not recovering after shade access — "
                "heat exhaustion. Tier 3: wet animal down, call rancher. "
            )
        else:
            reasoning += (
                "Recumbency or panting score 4 — heat stroke. "
                "Tier 4: vet call now; cold-water cooling starting immediately. "
            )

        reasoning += "Per `skills/cattle-behavior/disease/heat-stress-disease.md` §Decision rules."

        return DetectionResult(
            head_name=self.name,
            cow_tag=cow.tag,
            confidence=confidence,
            severity=severity,
            reasoning=reasoning,
        )
