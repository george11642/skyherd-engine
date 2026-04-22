"""Tests for the Pinkeye detection head."""

from __future__ import annotations

from pathlib import Path

from skyherd.vision.heads.pinkeye import Pinkeye
from skyherd.world.cattle import Cow

_HEAD = Pinkeye()
_META: dict = {}


def _make_cow(
    tag: str = "T001", ocular_discharge: float = 0.0, disease_flags: set[str] | None = None
) -> Cow:
    return Cow(
        id=f"cow_{tag}",
        tag=tag,
        pos=(100.0, 100.0),
        ocular_discharge=ocular_discharge,
        disease_flags=disease_flags or set(),
    )


# --- Negative path ---


def test_healthy_cow_no_detection() -> None:
    """Cow with zero discharge and no flag — no detection."""
    result = _HEAD.classify(_make_cow(ocular_discharge=0.0), _META)
    assert result is None


def test_below_threshold_no_detection() -> None:
    """discharge=0.4 exactly is below threshold (> 0.4 required)."""
    result = _HEAD.classify(_make_cow(ocular_discharge=0.4), _META)
    assert result is None


# --- Positive paths ---


def test_watch_at_low_discharge() -> None:
    """discharge=0.45 (above 0.4) → watch severity."""
    result = _HEAD.classify(_make_cow(ocular_discharge=0.45), _META)
    assert result is not None
    assert result.severity == "watch"
    assert result.head_name == "pinkeye"
    assert result.cow_tag == "T001"
    assert 0.0 < result.confidence <= 1.0


def test_log_at_mid_discharge() -> None:
    """discharge=0.65 → log severity (corneal opacity range)."""
    result = _HEAD.classify(_make_cow(ocular_discharge=0.65), _META)
    assert result is not None
    assert result.severity == "log"


def test_escalate_at_high_discharge() -> None:
    """discharge=0.85 → escalate (bilateral / deep ulcer)."""
    result = _HEAD.classify(_make_cow(ocular_discharge=0.85), _META)
    assert result is not None
    assert result.severity == "escalate"


def test_escalate_at_max_discharge() -> None:
    """discharge=1.0 → escalate with high confidence."""
    result = _HEAD.classify(_make_cow(ocular_discharge=1.0), _META)
    assert result is not None
    assert result.severity == "escalate"
    assert result.confidence >= 0.80


def test_flag_overrides_low_discharge() -> None:
    """Flag 'pinkeye' present → at least log even when discharge <= 0.4."""
    result = _HEAD.classify(_make_cow(ocular_discharge=0.1, disease_flags={"pinkeye"}), _META)
    assert result is not None
    assert result.severity == "log"


def test_reasoning_contains_skill_reference() -> None:
    """Reasoning must cite the skill file."""
    result = _HEAD.classify(_make_cow(ocular_discharge=0.9), _META)
    assert result is not None
    assert "pinkeye.md" in result.reasoning


def test_reasoning_contains_cow_tag() -> None:
    """Reasoning must mention the cow tag."""
    cow = _make_cow(tag="REDTAG", ocular_discharge=0.7)
    result = _HEAD.classify(cow, _META)
    assert result is not None
    assert "REDTAG" in result.reasoning


# --- Rule fallback explicit tests (Plan 05) ---


def test_rule_fallback_fires_when_raw_path_missing() -> None:
    """frame_meta without raw_path -> rule path -> bbox is None."""
    cow = _make_cow(ocular_discharge=0.75)
    result = _HEAD.classify(cow, {"raw_path": None})
    assert result is not None
    assert result.severity == "log"
    assert result.bbox is None
    assert "pinkeye.md" in result.reasoning


def test_rule_fallback_fires_when_raw_path_nonexistent() -> None:
    """frame_meta with a raw_path that doesn't exist on disk -> rule fallback -> bbox is None."""
    cow = _make_cow(ocular_discharge=0.85)
    result = _HEAD.classify(cow, {"raw_path": Path("/nonexistent/xxx.png")})
    assert result is not None
    assert result.severity == "escalate"
    assert result.bbox is None
