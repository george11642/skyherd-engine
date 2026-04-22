"""Bovine Respiratory Disease (BRD) detection head.

Thresholds aligned with skills/cattle-behavior/disease/brd.md §Decision rules.
"""

from __future__ import annotations

from typing import Any

from skyherd.vision.heads.base import Head
from skyherd.vision.result import DetectionResult, Severity
from skyherd.world.cattle import Cow

# BRD triggers when health_score < 0.6 AND respiratory signal present.
# Respiratory signal = disease_flag "respiratory" OR frame_meta["respiration_bpm"] > 60.
# (Normal cattle: 20–30 breaths/min; >50 is labored; 60+ is confirmed BRD threshold.)

_HEALTH_THRESHOLD = 0.6
_RESP_BPM_THRESHOLD = 60


def _has_respiratory_signal(cow: Cow, frame_meta: dict[str, Any]) -> bool:
    if "respiratory" in cow.disease_flags:
        return True
    bpm = frame_meta.get("respiration_bpm")
    return bpm is not None and bpm > _RESP_BPM_THRESHOLD


def _severity_from_health(health: float) -> Severity:
    """Map health_score to severity following brd.md decision rules.

    health 0.5–0.6  → log   (DART ≥2 or elevated temp — Tier 3 call, mapped log)
    health 0.3–0.5  → escalate (rapid breathing + no improvement — Tier 3 escalate)
    health < 0.3    → vet_now  (recumbent with labored breathing — Tier 4)
    """
    if health >= 0.5:
        return "log"
    if health >= 0.3:
        return "escalate"
    return "vet_now"


def _confidence_from_health(health: float) -> float:
    """Higher confidence when health score is further below threshold."""
    return round(min(1.0, 0.65 + (0.6 - health) * 1.1), 2)


class BRD(Head):
    """Detects Bovine Respiratory Disease.

    Decision rules (from brd.md):
    - health_score ≥ 0.6 : no detection (insufficient signal)
    - health_score < 0.6 + respiratory flag or high bpm:
        - 0.5–0.6 → log (Tier 3: antibiotic treatment today)
        - 0.3–0.5 → escalate (Tier 3: second-line antibiotic + vet)
        - < 0.3   → vet_now (Tier 4: recumbent, IV fluids)
    """

    @property
    def name(self) -> str:
        return "brd"

    def classify(self, cow: Cow, frame_meta: dict[str, Any]) -> DetectionResult | None:
        if cow.health_score >= _HEALTH_THRESHOLD:
            return None

        if not _has_respiratory_signal(cow, frame_meta):
            return None

        severity = _severity_from_health(cow.health_score)
        confidence = _confidence_from_health(cow.health_score)

        bpm = frame_meta.get("respiration_bpm")
        resp_detail = (
            f"respiration {bpm:.0f} bpm (threshold >{_RESP_BPM_THRESHOLD})"
            if bpm is not None
            else "flag 'respiratory' set"
        )

        reasoning = (
            f"Tag {cow.tag}: health score {cow.health_score:.2f} < {_HEALTH_THRESHOLD} "
            f"with {resp_detail}. "
            "DART indicators: droopy posture, abnormal breathing, separation from herd. "
            f"Severity {severity}: "
        )

        if severity == "log":
            reasoning += "DART ≥2; antibiotic treatment today (tulathromycin 2.5 mg/kg). "
        elif severity == "escalate":
            reasoning += (
                "Rapid shallow breathing, no improvement in 24 hrs; "
                "second-line antibiotic + vet consultation. "
            )
        else:
            reasoning += (
                "Recumbent with labored breathing — septicemia risk; "
                "vet call now, NSAID + IV fluid support. "
            )

        reasoning += "Per `skills/cattle-behavior/disease/brd.md` §Decision rules."

        return DetectionResult(
            head_name=self.name,
            cow_tag=cow.tag,
            confidence=confidence,
            severity=severity,
            reasoning=reasoning,
        )
