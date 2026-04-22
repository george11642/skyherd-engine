"""Tests for the LSD (Lumpy Skin Disease) detection head."""

from __future__ import annotations

from skyherd.vision.heads.lsd import LSD
from skyherd.world.cattle import Cow

_HEAD = LSD()
_META: dict = {}


def _make_cow(tag: str = "T001", disease_flags: set[str] | None = None) -> Cow:
    return Cow(
        id=f"cow_{tag}",
        tag=tag,
        pos=(100.0, 100.0),
        disease_flags=disease_flags or set(),
    )


# --- Negative paths ---


def test_healthy_cow_no_detection() -> None:
    """No flags → no detection."""
    assert _HEAD.classify(_make_cow(), _META) is None


def test_unrelated_flags_no_detection() -> None:
    """Other disease flags present but not 'lsd_nodules' → no detection."""
    assert _HEAD.classify(_make_cow(disease_flags={"respiratory", "pinkeye"}), _META) is None


# --- Positive paths ---


def test_lsd_nodules_flag_triggers() -> None:
    """'lsd_nodules' flag → detection with escalate severity."""
    result = _HEAD.classify(_make_cow(disease_flags={"lsd_nodules"}), _META)
    assert result is not None
    assert result.head_name == "lsd"


def test_lsd_severity_is_escalate() -> None:
    """LSD always returns 'escalate' (FAD protocol — page rancher immediately)."""
    result = _HEAD.classify(_make_cow(disease_flags={"lsd_nodules"}), _META)
    assert result is not None
    assert result.severity == "escalate"


def test_lsd_high_confidence() -> None:
    """LSD detection confidence is at least 0.85."""
    result = _HEAD.classify(_make_cow(disease_flags={"lsd_nodules"}), _META)
    assert result is not None
    assert result.confidence >= 0.85


def test_reasoning_mentions_aphis_hotline() -> None:
    """Reasoning must cite the USDA-APHIS FAD hotline."""
    result = _HEAD.classify(_make_cow(disease_flags={"lsd_nodules"}), _META)
    assert result is not None
    assert "APHIS" in result.reasoning


def test_reasoning_cites_skill() -> None:
    result = _HEAD.classify(_make_cow(disease_flags={"lsd_nodules"}), _META)
    assert result is not None
    assert "lsd.md" in result.reasoning


def test_reasoning_contains_cow_tag() -> None:
    result = _HEAD.classify(_make_cow(tag="LUMPY99", disease_flags={"lsd_nodules"}), _META)
    assert result is not None
    assert "LUMPY99" in result.reasoning
