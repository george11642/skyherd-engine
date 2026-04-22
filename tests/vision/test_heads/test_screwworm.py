"""Tests for the Screwworm detection head."""

from __future__ import annotations

from skyherd.vision.heads.screwworm import Screwworm
from skyherd.world.cattle import Cow

_HEAD = Screwworm()
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
    """No flags — no detection."""
    result = _HEAD.classify(_make_cow(), _META)
    assert result is None


def test_open_wound_alone_no_detection() -> None:
    """'open_wound' alone (without 'larvae') — no detection."""
    result = _HEAD.classify(_make_cow(disease_flags={"open_wound"}), _META)
    assert result is None


def test_larvae_alone_no_detection() -> None:
    """'larvae' alone (without 'open_wound') — no detection."""
    result = _HEAD.classify(_make_cow(disease_flags={"larvae"}), _META)
    assert result is None


# --- Positive paths ---


def test_screwworm_flag_triggers_vet_now() -> None:
    """'screwworm' flag always results in vet_now."""
    result = _HEAD.classify(_make_cow(disease_flags={"screwworm"}), _META)
    assert result is not None
    assert result.severity == "vet_now"
    assert result.head_name == "screwworm"


def test_open_wound_plus_larvae_triggers_vet_now() -> None:
    """'open_wound' + 'larvae' co-present → vet_now."""
    result = _HEAD.classify(_make_cow(disease_flags={"open_wound", "larvae"}), _META)
    assert result is not None
    assert result.severity == "vet_now"


def test_screwworm_flag_high_confidence() -> None:
    """Direct 'screwworm' flag gives higher confidence than larvae inference."""
    direct = _HEAD.classify(_make_cow(disease_flags={"screwworm"}), _META)
    inferred = _HEAD.classify(_make_cow(disease_flags={"open_wound", "larvae"}), _META)
    assert direct is not None and inferred is not None
    assert direct.confidence > inferred.confidence


def test_reasoning_cites_aphis() -> None:
    """Reasoning must mention APHIS report requirement."""
    result = _HEAD.classify(_make_cow(disease_flags={"screwworm"}), _META)
    assert result is not None
    assert "APHIS" in result.reasoning


def test_reasoning_contains_cow_tag() -> None:
    """Reasoning must contain the cow tag."""
    result = _HEAD.classify(_make_cow(tag="NM42", disease_flags={"screwworm"}), _META)
    assert result is not None
    assert "NM42" in result.reasoning
