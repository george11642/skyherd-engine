"""Body Condition Score (BCS) detection head.

Thresholds aligned with skills/cattle-behavior/disease/bcs.md §Decision rules.
"""

from __future__ import annotations

from typing import Any

from skyherd.vision.heads.base import Head
from skyherd.vision.result import DetectionResult, Severity
from skyherd.world.cattle import Cow

# Target BCS windows from bcs.md:
#   Gestating (pregnant): 3.5–6.5   (mid-gestation 4–5.5 acceptable; approach calving 5–6)
#   Lactating (non-pregnant): 4.0–7.0
#
# Decision rules from bcs.md:
#   BCS < 4 approaching calving (within 30 days) → Tier 2 log
#   BCS < 3                                       → Tier 3 escalate
#   BCS > 7 in late-gestation cow                 → Tier 2 log (fat-cow risk)
#   Rapid drop >0.5 in 2-week window              → flag (not modelled here; no history)

_GESTATING_LOW = 3.5
_GESTATING_HIGH = 6.5
_LACTATING_LOW = 4.0
_LACTATING_HIGH = 7.0

# Critical thresholds (apply regardless of stage)
_EMACIATION_THRESHOLD = 3.0  # → escalate (Tier 3)
_CALVING_RISK_LOW = 4.0  # → log when pregnant (Tier 2)
_OBESITY_RISK_HIGH = 7.0  # → log when pregnant (Tier 2)


def _target_window(cow: Cow) -> tuple[float, float]:
    """Return (low, high) BCS target for this cow's production stage."""
    if cow.pregnancy_days_remaining is not None:
        return (_GESTATING_LOW, _GESTATING_HIGH)
    return (_LACTATING_LOW, _LACTATING_HIGH)


def _classify_bcs(cow: Cow) -> tuple[Severity, float, str] | None:
    """Return (severity, confidence, reasoning) or None if BCS is within target."""
    bcs = cow.bcs
    is_pregnant = cow.pregnancy_days_remaining is not None
    low, high = _target_window(cow)

    # Critical emaciation — applies to all cows (Tier 3)
    if bcs < _EMACIATION_THRESHOLD:
        deficit = _EMACIATION_THRESHOLD - bcs
        confidence = round(min(1.0, 0.75 + deficit * 0.2), 2)
        reasoning = (
            f"BCS {bcs:.1f}/9 — below critical emaciation threshold {_EMACIATION_THRESHOLD}. "
            "Ribs individually visible with no fat cover; spine prominent. "
            "Tier 3: emergency nutritional support + vet evaluation for underlying disease. "
            "Per `skills/cattle-behavior/disease/bcs.md` §Decision rules."
        )
        return "escalate", confidence, reasoning

    # Pregnant cow below calving-risk threshold — check independently of stage window.
    # bcs.md: "BCS < 4 approaching calving → Tier 2 log".  This threshold applies even
    # when BCS is still above the gestating window low (3.5), because 3.5–4.0 is in-window
    # but still carries calving risk.
    if is_pregnant and bcs < _CALVING_RISK_LOW:
        deficit = _CALVING_RISK_LOW - bcs
        confidence = round(min(1.0, 0.65 + deficit * 0.25), 2)
        reasoning = (
            f"BCS {bcs:.1f}/9 — below calving-risk threshold {_CALVING_RISK_LOW} "
            f"(pregnancy_days_remaining={cow.pregnancy_days_remaining}). "
            "Dystocia and rebreeding-failure risk elevated. "
            "Tier 2: supplemental feeding needed. "
            "Per `skills/cattle-behavior/disease/bcs.md` §Decision rules."
        )
        return "log", confidence, reasoning

    # Thin below stage-appropriate low target (for non-pregnant or gestating below 3.5)
    if bcs < low:
        deficit = low - bcs
        severity: Severity = "watch"
        confidence = round(min(1.0, 0.55 + deficit * 0.3), 2)
        reasoning = (
            f"BCS {bcs:.1f}/9 — below target window low of {low} for this stage. "
            "Nutritional supplementation review recommended. "
            "Tier 1 watch: cross-reference paddock-rotation.md for forage quality. "
            "Per `skills/cattle-behavior/disease/bcs.md` §Decision rules."
        )
        return severity, confidence, reasoning

    # Obese above stage-appropriate high target
    if bcs > high:
        excess = bcs - high
        if is_pregnant and bcs > _OBESITY_RISK_HIGH:
            severity = "log"
            confidence = round(min(1.0, 0.65 + excess * 0.2), 2)
            reasoning = (
                f"BCS {bcs:.1f}/9 — above fat-cow risk threshold {_OBESITY_RISK_HIGH} "
                f"(pregnancy_days_remaining={cow.pregnancy_days_remaining}). "
                "Difficult calving risk elevated in late-gestation obese cow. "
                "Tier 2 note: monitor closely in calving-signs. "
                "Per `skills/cattle-behavior/disease/bcs.md` §Decision rules."
            )
            return severity, confidence, reasoning
        else:
            severity = "watch"
            confidence = round(min(1.0, 0.50 + excess * 0.2), 2)
            reasoning = (
                f"BCS {bcs:.1f}/9 — above target window high of {high} for this stage. "
                "Overconditioning may reduce reproductive efficiency. "
                "Tier 1 watch: adjust feed ration. "
                "Per `skills/cattle-behavior/disease/bcs.md` §Decision rules."
            )
            return severity, confidence, reasoning

    return None


class BCS(Head):
    """Detects body condition score outside target window.

    Decision rules (from bcs.md):
    - BCS within target range : no detection
    - BCS below target low    : watch (general) or log (pregnant approaching calving)
    - BCS < 3.0               : escalate (Tier 3 — emergency nutritional support)
    - BCS > target high       : watch (general) or log (pregnant late-gestation fat cow)
    """

    @property
    def name(self) -> str:
        return "bcs"

    def should_evaluate(self, cow: Cow, frame_meta: dict[str, Any]) -> bool:  # noqa: ARG002
        """Skip cows whose BCS is clearly within all target windows."""
        bcs = cow.bcs
        # Fast reject: clearly healthy range (4.0–6.5 covers all stage windows)
        if 4.0 <= bcs <= 6.5:
            return False
        return True

    def classify(self, cow: Cow, frame_meta: dict[str, Any]) -> DetectionResult | None:
        result = _classify_bcs(cow)
        if result is None:
            return None

        severity, confidence, reasoning = result
        full_reasoning = f"Tag {cow.tag}: {reasoning}"

        return DetectionResult(
            head_name=self.name,
            cow_tag=cow.tag,
            confidence=confidence,
            severity=severity,
            reasoning=full_reasoning,
        )
