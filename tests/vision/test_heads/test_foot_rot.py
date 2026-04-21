"""Tests for the FootRot detection head."""

from __future__ import annotations

from skyherd.vision.heads.foot_rot import FootRot
from skyherd.world.cattle import Cow

_HEAD = FootRot()
_META: dict = {}


def _make_cow(tag: str = "T001", lameness_score: int = 0) -> Cow:
    return Cow(
        id=f"cow_{tag}",
        tag=tag,
        pos=(100.0, 100.0),
        lameness_score=lameness_score,
    )


# --- Negative paths ---

def test_no_lameness_no_detection() -> None:
    """lameness_score=0 → no detection."""
    assert _HEAD.classify(_make_cow(lameness_score=0), _META) is None


def test_score_1_no_detection() -> None:
    """lameness_score=1 is below threshold — no detection."""
    assert _HEAD.classify(_make_cow(lameness_score=1), _META) is None


# --- Positive paths ---

def test_score_2_watch() -> None:
    """lameness_score=2 → watch severity."""
    result = _HEAD.classify(_make_cow(lameness_score=2), _META)
    assert result is not None
    assert result.severity == "watch"
    assert result.head_name == "foot_rot"


def test_score_3_log() -> None:
    """lameness_score=3 → log severity (Tier 3: rancher call)."""
    result = _HEAD.classify(_make_cow(lameness_score=3), _META)
    assert result is not None
    assert result.severity == "log"


def test_score_4_escalate() -> None:
    """lameness_score=4 → escalate severity (Tier 3 escalate + vet if non-ambulatory)."""
    result = _HEAD.classify(_make_cow(lameness_score=4), _META)
    assert result is not None
    assert result.severity == "escalate"


def test_score_5_vet_now() -> None:
    """lameness_score=5 → vet_now severity (non-weight-bearing, Tier 4)."""
    result = _HEAD.classify(_make_cow(lameness_score=5), _META)
    assert result is not None
    assert result.severity == "vet_now"


def test_confidence_increases_with_score() -> None:
    """Higher lameness scores should yield higher confidence."""
    results = [
        _HEAD.classify(_make_cow(lameness_score=s), _META)
        for s in range(2, 6)
    ]
    confidences = [r.confidence for r in results if r is not None]
    assert confidences == sorted(confidences), "Confidence should increase with lameness score"


def test_reasoning_mentions_score() -> None:
    """Reasoning must include gait score."""
    result = _HEAD.classify(_make_cow(lameness_score=3), _META)
    assert result is not None
    assert "3/5" in result.reasoning


def test_reasoning_cites_skill() -> None:
    """Reasoning must reference the foot-rot skill."""
    result = _HEAD.classify(_make_cow(lameness_score=4), _META)
    assert result is not None
    assert "foot-rot.md" in result.reasoning


def test_reasoning_contains_cow_tag() -> None:
    result = _HEAD.classify(_make_cow(tag="LAME77", lameness_score=3), _META)
    assert result is not None
    assert "LAME77" in result.reasoning
