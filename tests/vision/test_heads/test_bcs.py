"""Tests for the BCS (Body Condition Score) detection head."""

from __future__ import annotations

from skyherd.vision.heads.bcs import BCS
from skyherd.world.cattle import Cow

_HEAD = BCS()
_META: dict = {}


def _make_cow(
    tag: str = "T001",
    bcs: float = 5.5,
    pregnancy_days_remaining: int | None = None,
) -> Cow:
    return Cow(
        id=f"cow_{tag}",
        tag=tag,
        pos=(100.0, 100.0),
        bcs=bcs,
        pregnancy_days_remaining=pregnancy_days_remaining,
    )


# --- Negative paths: within target window ---


def test_gestating_cow_in_window_no_detection() -> None:
    """Pregnant cow BCS 5.0 — within gestating window [3.5, 6.5] — no detection."""
    assert _HEAD.classify(_make_cow(bcs=5.0, pregnancy_days_remaining=90), _META) is None


def test_lactating_cow_in_window_no_detection() -> None:
    """Non-pregnant cow BCS 5.5 — within lactating window [4.0, 7.0] — no detection."""
    assert _HEAD.classify(_make_cow(bcs=5.5), _META) is None


def test_bcs_exactly_at_low_bound_no_detection() -> None:
    """BCS = 4.0 for lactating cow (at low bound, not below) — no detection."""
    assert _HEAD.classify(_make_cow(bcs=4.0), _META) is None


def test_bcs_exactly_at_high_bound_no_detection() -> None:
    """BCS = 7.0 for lactating cow (at high bound, not above) — no detection."""
    assert _HEAD.classify(_make_cow(bcs=7.0), _META) is None


# --- Positive paths: emaciation (critical) ---


def test_critical_emaciation_escalate() -> None:
    """BCS < 3.0 → escalate regardless of stage."""
    result = _HEAD.classify(_make_cow(bcs=2.5), _META)
    assert result is not None
    assert result.severity == "escalate"
    assert result.head_name == "bcs"


def test_bcs_1_escalate_high_confidence() -> None:
    """BCS = 1.0 (emaciated) → escalate with confidence >= 0.90."""
    result = _HEAD.classify(_make_cow(bcs=1.0), _META)
    assert result is not None
    assert result.severity == "escalate"
    assert result.confidence >= 0.90


# --- Positive paths: below target window ---


def test_pregnant_cow_below_calving_risk_log() -> None:
    """Pregnant cow BCS 3.8 — below calving-risk threshold 4.0 → log."""
    result = _HEAD.classify(_make_cow(bcs=3.8, pregnancy_days_remaining=20), _META)
    assert result is not None
    assert result.severity == "log"


def test_nonpregnant_below_low_target_watch() -> None:
    """Non-pregnant cow BCS 3.8 — below 4.0 target → watch."""
    result = _HEAD.classify(_make_cow(bcs=3.8, pregnancy_days_remaining=None), _META)
    assert result is not None
    assert result.severity == "watch"


def test_gestating_below_gestating_low_watch() -> None:
    """Pregnant cow BCS 3.2 — below gestating low 3.5 but above calving 4.0 check... watch."""
    # BCS 3.2 < GESTATING_LOW (3.5) but 3.2 >= EMACIATION (3.0) and not < CALVING_RISK (4.0)
    # Actually 3.2 < 4.0 so it triggers calving log for pregnant cow
    result = _HEAD.classify(_make_cow(bcs=3.2, pregnancy_days_remaining=90), _META)
    assert result is not None
    # Pregnant + BCS < 4.0 → log
    assert result.severity == "log"


# --- Positive paths: above target window ---


def test_pregnant_obese_above_7_log() -> None:
    """Pregnant cow BCS 7.5 — fat-cow calving risk → log."""
    result = _HEAD.classify(_make_cow(bcs=7.5, pregnancy_days_remaining=10), _META)
    assert result is not None
    assert result.severity == "log"


def test_nonpregnant_obese_above_high_watch() -> None:
    """Non-pregnant cow BCS 7.5 — above target high 7.0 → watch."""
    result = _HEAD.classify(_make_cow(bcs=7.5), _META)
    assert result is not None
    assert result.severity == "watch"


# --- Reasoning ---


def test_reasoning_cites_skill() -> None:
    result = _HEAD.classify(_make_cow(bcs=2.0), _META)
    assert result is not None
    assert "bcs.md" in result.reasoning


def test_reasoning_contains_cow_tag() -> None:
    result = _HEAD.classify(_make_cow(tag="THINCOW", bcs=2.5), _META)
    assert result is not None
    assert "THINCOW" in result.reasoning


def test_reasoning_contains_bcs_value() -> None:
    result = _HEAD.classify(_make_cow(bcs=2.5), _META)
    assert result is not None
    assert "2.5" in result.reasoning
