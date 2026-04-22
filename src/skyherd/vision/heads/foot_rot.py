"""Foot rot (Interdigital Necrobacillosis) detection head.

Thresholds aligned with skills/cattle-behavior/disease/foot-rot.md §Decision rules.
"""

from __future__ import annotations

from typing import Any

from skyherd.vision.heads.base import Head
from skyherd.vision.result import DetectionResult, Severity
from skyherd.world.cattle import Cow

# Gait-score → severity mapping from foot-rot.md §Decision rules:
#   score 2  → watch  (not formally in Skill but below Tier 2 threshold)
#   score 3  → log    (interdigital swelling + gait 3 → Tier 3 call; mapped log here
#                      because a single vision head cannot confirm swelling/odor —
#                      rancher confirmation needed before escalating)
#   score 4  → escalate (Tier 3 → escalate; vet if non-ambulatory)
#   score 5  → vet_now  (Tier 4 vet call; non-ambulatory)

_SCORE_TO_SEVERITY: dict[int, Severity] = {
    2: "watch",
    3: "log",
    4: "escalate",
    5: "vet_now",
}

_SCORE_TO_CONFIDENCE: dict[int, float] = {
    2: 0.55,
    3: 0.75,
    4: 0.85,
    5: 0.95,
}

_SCORE_REASONING: dict[int, str] = {
    2: (
        "Mild gait irregularity, score 2/5 — early weight-shifting; "
        "possible interdigital irritation or pre-foot-rot maceration. "
        "Tier 1 watch: recheck footing and wet-ground exposure. "
        "Per `skills/cattle-behavior/disease/foot-rot.md` §Decision rules."
    ),
    3: (
        "Left-side weight shift, head bob on affected forelimb, score 3/5. "
        "Consistent with early foot rot (bilateral interdigital swelling + foul odor). "
        "Tier 3: rancher call; antibiotic treatment today (oxytetracycline LA IM). "
        "Per `skills/cattle-behavior/disease/foot-rot.md` §Decision rules."
    ),
    4: (
        "Severe lameness, score 4/5 — animal toe-touching only; "
        "coronary-band swelling indicated by posture. "
        "Tier 3→escalate: vet call if fever >105°F or non-ambulatory. "
        "Per `skills/cattle-behavior/disease/foot-rot.md` §Decision rules."
    ),
    5: (
        "Non-weight-bearing lameness, score 5/5 — animal recumbent or refuses to move. "
        "Consistent with advanced foot rot or septic digit. "
        "Tier 4 vet_now: vet on-site required; possible surgical digit amputation. "
        "Per `skills/cattle-behavior/disease/foot-rot.md` §Decision rules."
    ),
}


class FootRot(Head):
    """Detects foot rot via lameness score.

    Decision rules (from foot-rot.md):
    - lameness_score < 2  : no detection
    - lameness_score == 2 : watch
    - lameness_score == 3 : log
    - lameness_score == 4 : escalate
    - lameness_score == 5 : vet_now
    """

    @property
    def name(self) -> str:
        return "foot_rot"

    def should_evaluate(self, cow: Cow, frame_meta: dict[str, Any]) -> bool:  # noqa: ARG002
        """Skip cows with lameness score below threshold."""
        return cow.lameness_score >= 2

    def classify(self, cow: Cow, frame_meta: dict[str, Any]) -> DetectionResult | None:
        score = cow.lameness_score

        if score < 2:
            return None

        clamped = min(score, 5)
        severity = _SCORE_TO_SEVERITY[clamped]
        confidence = _SCORE_TO_CONFIDENCE[clamped]
        base_reasoning = _SCORE_REASONING[clamped]

        reasoning = f"Tag {cow.tag}: {base_reasoning}"

        return DetectionResult(
            head_name=self.name,
            cow_tag=cow.tag,
            confidence=confidence,
            severity=severity,
            reasoning=reasoning,
        )
