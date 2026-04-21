"""Tests for the HeatStress detection head."""

from __future__ import annotations

from skyherd.vision.heads.heat_stress import HeatStress
from skyherd.world.cattle import Cow

_HEAD = HeatStress()


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


def _meta(temp_f: float = 72.0) -> dict:
    return {"temp_f": temp_f}


# --- Negative paths ---

def test_cool_healthy_no_detection() -> None:
    """Cool weather + healthy cow → no detection."""
    assert _HEAD.classify(_make_cow(), _meta(70.0)) is None


def test_hot_but_healthy_no_detection() -> None:
    """Temp > 95 but health >= 0.8 → no detection (no panting flag either)."""
    assert _HEAD.classify(_make_cow(health_score=0.85), _meta(100.0)) is None


def test_unhealthy_but_cool_no_detection() -> None:
    """health < 0.8 but temp <= 95 and no panting → no detection."""
    assert _HEAD.classify(_make_cow(health_score=0.5), _meta(90.0)) is None


# --- Positive paths: ambient trigger ---

def test_hot_and_unhealthy_triggers() -> None:
    """Temp > 95 + health < 0.8 → detection."""
    result = _HEAD.classify(_make_cow(health_score=0.75), _meta(96.0))
    assert result is not None
    assert result.head_name == "heat_stress"


def test_watch_at_mild_heat_and_health() -> None:
    """health 0.7–0.8 + mild heat → watch."""
    result = _HEAD.classify(_make_cow(health_score=0.75), _meta(96.0))
    assert result is not None
    assert result.severity == "watch"


def test_log_at_moderate_degradation() -> None:
    """health 0.5–0.7 + high temp → log."""
    result = _HEAD.classify(_make_cow(health_score=0.6), _meta(100.0))
    assert result is not None
    assert result.severity == "log"


def test_escalate_at_severe_degradation() -> None:
    """health 0.3–0.5 + high temp → escalate."""
    result = _HEAD.classify(_make_cow(health_score=0.4), _meta(105.0))
    assert result is not None
    assert result.severity == "escalate"


def test_vet_now_at_critical() -> None:
    """health < 0.3 + extreme heat → vet_now."""
    result = _HEAD.classify(_make_cow(health_score=0.2), _meta(110.0))
    assert result is not None
    assert result.severity == "vet_now"


# --- Positive paths: panting flag ---

def test_panting_flag_triggers_at_any_temp() -> None:
    """'panting' flag triggers even in cool weather."""
    result = _HEAD.classify(_make_cow(health_score=1.0, disease_flags={"panting"}), _meta(70.0))
    assert result is not None


def test_panting_flag_with_cool_temp_is_watch() -> None:
    """'panting' in cool weather + full health → watch."""
    result = _HEAD.classify(_make_cow(health_score=0.95, disease_flags={"panting"}), _meta(70.0))
    assert result is not None
    assert result.severity == "watch"


def test_reasoning_cites_skill() -> None:
    result = _HEAD.classify(_make_cow(health_score=0.4), _meta(105.0))
    assert result is not None
    assert "heat-stress-disease.md" in result.reasoning


def test_reasoning_contains_cow_tag() -> None:
    result = _HEAD.classify(_make_cow(tag="HOTCOW", health_score=0.5), _meta(100.0))
    assert result is not None
    assert "HOTCOW" in result.reasoning
