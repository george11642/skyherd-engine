"""Tests for the BRD (Bovine Respiratory Disease) detection head."""

from __future__ import annotations

from skyherd.vision.heads.brd import _RESP_BPM_THRESHOLD, BRD
from skyherd.world.cattle import Cow

_HEAD = BRD()
_META_NORMAL: dict = {"respiration_bpm": 25}
_META_HIGH_BPM: dict = {"respiration_bpm": 70}
_META_NO_BPM: dict = {}


def _make_cow(
    tag: str = "T001",
    health_score: float = 1.0,
    disease_flags: set[str] | None = None,
) -> Cow:
    return Cow(
        id=f"cow_{tag}",
        tag=tag,
        pos=(100.0, 100.0),
        health_score=health_score,
        disease_flags=disease_flags or set(),
    )


# --- Negative paths ---

def test_healthy_cow_no_detection() -> None:
    """health_score >= 0.6 → no detection regardless of bpm."""
    assert _HEAD.classify(_make_cow(health_score=1.0), _META_HIGH_BPM) is None


def test_unhealthy_without_respiratory_no_detection() -> None:
    """health_score < 0.6 but no respiratory signal → no detection."""
    assert _HEAD.classify(_make_cow(health_score=0.5), _META_NORMAL) is None


def test_high_bpm_without_health_threshold_no_detection() -> None:
    """High bpm alone (health >= 0.6) → no detection."""
    assert _HEAD.classify(_make_cow(health_score=0.7), _META_HIGH_BPM) is None


# --- Positive paths: respiratory flag ---

def test_respiratory_flag_triggers() -> None:
    """'respiratory' flag + health < 0.6 → detection."""
    cow = _make_cow(health_score=0.55, disease_flags={"respiratory"})
    result = _HEAD.classify(cow, _META_NO_BPM)
    assert result is not None
    assert result.head_name == "brd"


def test_log_near_threshold() -> None:
    """health 0.5–0.6 with respiratory signal → log (Tier 3 antibiotic)."""
    cow = _make_cow(health_score=0.55, disease_flags={"respiratory"})
    result = _HEAD.classify(cow, _META_NO_BPM)
    assert result is not None
    assert result.severity == "log"


def test_escalate_at_low_health() -> None:
    """health 0.3–0.5 → escalate (second-line antibiotic + vet)."""
    cow = _make_cow(health_score=0.4, disease_flags={"respiratory"})
    result = _HEAD.classify(cow, _META_NO_BPM)
    assert result is not None
    assert result.severity == "escalate"


def test_vet_now_at_critical_health() -> None:
    """health < 0.3 → vet_now (recumbent, Tier 4)."""
    cow = _make_cow(health_score=0.2, disease_flags={"respiratory"})
    result = _HEAD.classify(cow, _META_NO_BPM)
    assert result is not None
    assert result.severity == "vet_now"


# --- Positive paths: high respiration bpm ---

def test_high_bpm_triggers_with_low_health() -> None:
    """bpm > threshold + health < 0.6 → detection via bpm signal."""
    cow = _make_cow(health_score=0.55)
    result = _HEAD.classify(cow, {"respiration_bpm": _RESP_BPM_THRESHOLD + 1})
    assert result is not None


def test_reasoning_mentions_bpm_when_provided() -> None:
    """Reasoning includes bpm value when frame_meta has it."""
    cow = _make_cow(health_score=0.5)
    result = _HEAD.classify(cow, {"respiration_bpm": 75})
    assert result is not None
    assert "75" in result.reasoning


def test_reasoning_cites_skill() -> None:
    cow = _make_cow(health_score=0.4, disease_flags={"respiratory"})
    result = _HEAD.classify(cow, _META_NO_BPM)
    assert result is not None
    assert "brd.md" in result.reasoning


def test_reasoning_contains_cow_tag() -> None:
    cow = _make_cow(tag="WHEEZE01", health_score=0.4, disease_flags={"respiratory"})
    result = _HEAD.classify(cow, _META_NO_BPM)
    assert result is not None
    assert "WHEEZE01" in result.reasoning
