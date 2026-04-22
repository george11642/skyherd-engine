"""Tests for the pixel-inference path of the Pinkeye detection head.

These tests exercise the new MobileNetV3-Small pixel path added in Plan 04.
All existing rule-based tests remain in ``test_pinkeye.py`` unchanged.

TDD RED phase: these tests fail until pinkeye.py is rewritten with
pixel-path + model loader.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from skyherd.vision.renderer import render_trough_frame
from skyherd.world.cattle import Cow


def _make_sick_cow(
    tag: str = "SICK01",
    pos: tuple[float, float] = (300.0, 300.0),
    ocular_discharge: float = 0.85,
    disease_flags: set[str] | None = None,
) -> Cow:
    return Cow(
        id=f"cow_{tag}",
        tag=tag,
        pos=pos,
        ocular_discharge=ocular_discharge,
        disease_flags=disease_flags or {"pinkeye"},
        lameness_score=0,
    )


def _make_healthy_cow(
    tag: str = "OK01", pos: tuple[float, float] = (300.0, 300.0)
) -> Cow:
    return Cow(
        id=f"cow_{tag}",
        tag=tag,
        pos=pos,
        ocular_discharge=0.0,
        disease_flags=set(),
        lameness_score=0,
    )


# ---------------------------------------------------------------------------
# Model loader tests
# ---------------------------------------------------------------------------


def test_get_model_returns_nn_module() -> None:
    """_get_model() must return a non-None nn.Module (weights loaded from Plan 03)."""
    from skyherd.vision.heads.pinkeye import _get_model

    model = _get_model()
    assert model is not None, "_get_model() returned None — weights missing or corrupt"


def test_get_model_is_cached() -> None:
    """Calling _get_model() twice returns the identical object (lru_cache hit)."""
    from skyherd.vision.heads.pinkeye import _get_model

    m1 = _get_model()
    m2 = _get_model()
    assert m1 is m2, "lru_cache must return same object on second call"


def test_get_model_has_4_output_classes() -> None:
    """Model final linear layer must have out_features == 4."""
    import torch.nn as nn

    from skyherd.vision.heads.pinkeye import _get_model

    model = _get_model()
    assert model is not None
    # classifier[3] is the final Linear layer
    final_layer = model.classifier[3]  # type: ignore[index]
    assert isinstance(final_layer, nn.Linear)
    assert final_layer.out_features == 4, f"Expected 4 classes, got {final_layer.out_features}"


# ---------------------------------------------------------------------------
# Pixel path: integration with rendered frame
# ---------------------------------------------------------------------------


def test_pixel_path_fires_when_raw_path_present(
    rendered_positive_frame: tuple[Path, object],
) -> None:
    """Pixel path fires and returns a DetectionResult when raw_path is present."""
    from skyherd.vision.heads.pinkeye import Pinkeye

    png_path, world = rendered_positive_frame  # type: ignore[misc]
    # Get the sick cow from the world
    sick_cow = world.herd.cows[0]  # type: ignore[attr-defined]
    frame_meta = {
        "raw_path": png_path,
        "bounds_m": (2000.0, 2000.0),
    }
    head = Pinkeye()
    result = head.classify(sick_cow, frame_meta)
    # Model trained binary: discharge=0.85 → class 3 (escalate). Must be non-None.
    assert result is not None, "Pixel path should detect sick cow with discharge=0.85"


def test_pixel_path_bbox_populated(
    rendered_positive_frame: tuple[Path, object],
) -> None:
    """Pixel path populates DetectionResult.bbox as (x0, y0, x1, y1) float tuple."""
    from skyherd.vision.heads.pinkeye import Pinkeye

    png_path, world = rendered_positive_frame  # type: ignore[misc]
    sick_cow = world.herd.cows[0]  # type: ignore[attr-defined]
    frame_meta = {"raw_path": png_path, "bounds_m": (2000.0, 2000.0)}
    head = Pinkeye()
    result = head.classify(sick_cow, frame_meta)
    assert result is not None
    assert result.bbox is not None, "Pixel path must populate bbox"
    assert len(result.bbox) == 4
    x0, y0, x1, y1 = result.bbox
    assert x0 < x1, f"bbox x0={x0} must be < x1={x1}"
    assert y0 < y1, f"bbox y0={y0} must be < y1={y1}"


def test_pixel_path_reasoning_contains_skill_and_tag(
    rendered_positive_frame: tuple[Path, object],
) -> None:
    """Pixel path reasoning must cite pinkeye.md AND the cow tag."""
    from skyherd.vision.heads.pinkeye import Pinkeye

    png_path, world = rendered_positive_frame  # type: ignore[misc]
    sick_cow = world.herd.cows[0]  # type: ignore[attr-defined]
    frame_meta = {"raw_path": png_path, "bounds_m": (2000.0, 2000.0)}
    head = Pinkeye()
    result = head.classify(sick_cow, frame_meta)
    assert result is not None
    assert "pinkeye.md" in result.reasoning, "Pixel reasoning must cite pinkeye.md"
    assert sick_cow.tag in result.reasoning, "Pixel reasoning must contain cow tag"


def test_pixel_path_mobilenet_string_in_module() -> None:
    """pinkeye.py source must reference mobilenet_v3_small (not just imported, but used)."""
    import inspect

    from skyherd.vision.heads import pinkeye

    src = inspect.getsource(pinkeye)
    assert "mobilenet_v3_small" in src, "pinkeye.py must reference mobilenet_v3_small"


# ---------------------------------------------------------------------------
# Rule fallback: no raw_path
# ---------------------------------------------------------------------------


def test_rule_fallback_fires_without_raw_path() -> None:
    """Rule fallback fires when frame_meta has no raw_path (preserves existing tests)."""
    from skyherd.vision.heads.pinkeye import Pinkeye

    cow = _make_sick_cow()
    head = Pinkeye()
    result = head.classify(cow, {})  # empty frame_meta — no raw_path
    assert result is not None
    assert result.bbox is None, "Rule fallback must not set bbox"
    assert "pinkeye.md" in result.reasoning


def test_rule_fallback_fires_when_raw_path_is_none() -> None:
    """Rule fallback fires when raw_path is explicitly None."""
    from skyherd.vision.heads.pinkeye import Pinkeye

    cow = _make_sick_cow()
    head = Pinkeye()
    result = head.classify(cow, {"raw_path": None})
    assert result is not None
    assert result.bbox is None


def test_rule_fallback_fires_when_raw_path_missing_file(tmp_path: Path) -> None:
    """Rule fallback fires when raw_path points to a non-existent file."""
    from skyherd.vision.heads.pinkeye import Pinkeye

    cow = _make_sick_cow()
    head = Pinkeye()
    missing = tmp_path / "does_not_exist.png"
    result = head.classify(cow, {"raw_path": missing})
    assert result is not None
    assert result.bbox is None


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_pixel_path_deterministic(
    rendered_positive_frame: tuple[Path, object],
) -> None:
    """Two consecutive classify() calls on same cow + frame return equal model_dump() (ex timestamp)."""
    from skyherd.vision.heads.pinkeye import Pinkeye

    png_path, world = rendered_positive_frame  # type: ignore[misc]
    sick_cow = world.herd.cows[0]  # type: ignore[attr-defined]
    frame_meta = {"raw_path": png_path, "bounds_m": (2000.0, 2000.0)}
    head = Pinkeye()
    r1 = head.classify(sick_cow, frame_meta)
    r2 = head.classify(sick_cow, frame_meta)
    assert r1 is not None and r2 is not None
    d1 = r1.model_dump()
    d2 = r2.model_dump()
    # Exclude timestamp (wall-clock dependent)
    d1.pop("timestamp")
    d2.pop("timestamp")
    assert d1 == d2, f"Non-deterministic pixel classification: {d1} != {d2}"


# ---------------------------------------------------------------------------
# Inference latency (soft gate — <500ms)
# ---------------------------------------------------------------------------


def test_pixel_path_under_500ms(
    rendered_positive_frame: tuple[Path, object],
) -> None:
    """Pixel classification should complete in <500ms on CPU (soft gate for demo)."""
    from skyherd.vision.heads.pinkeye import Pinkeye

    png_path, world = rendered_positive_frame  # type: ignore[misc]
    sick_cow = world.herd.cows[0]  # type: ignore[attr-defined]
    frame_meta = {"raw_path": png_path, "bounds_m": (2000.0, 2000.0)}
    head = Pinkeye()
    # Warm-up call (model is cached after first)
    head.classify(sick_cow, frame_meta)

    start = time.perf_counter()
    head.classify(sick_cow, frame_meta)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 500, f"Pixel inference took {elapsed_ms:.1f}ms > 500ms budget"


# ---------------------------------------------------------------------------
# Healthy cow classification (model says class 0 → no detection)
# ---------------------------------------------------------------------------


def test_healthy_cow_no_detection_with_frame(
    rendered_negative_frame: tuple[Path, object],
) -> None:
    """Healthy cow (discharge=0.0, no flag) returns None even when frame is present."""
    from skyherd.vision.heads.pinkeye import Pinkeye

    png_path, world = rendered_negative_frame  # type: ignore[misc]
    healthy_cow = world.herd.cows[0]  # type: ignore[attr-defined]
    frame_meta = {"raw_path": png_path, "bounds_m": (2000.0, 2000.0)}
    head = Pinkeye()
    # should_evaluate gate fires first — discharge=0 → False → None regardless
    result = head.classify(healthy_cow, frame_meta)
    assert result is None


# ---------------------------------------------------------------------------
# bounds_m override via frame_meta
# ---------------------------------------------------------------------------


def test_bounds_m_override_accepted(
    rendered_positive_frame: tuple[Path, object],
) -> None:
    """frame_meta['bounds_m'] override is accepted (non-default bounds_m)."""
    from skyherd.vision.heads.pinkeye import Pinkeye

    png_path, world = rendered_positive_frame  # type: ignore[misc]
    sick_cow = world.herd.cows[0]  # type: ignore[attr-defined]
    # Override with different bounds — should not crash
    frame_meta = {"raw_path": png_path, "bounds_m": (1000.0, 1000.0)}
    head = Pinkeye()
    # Should not raise
    head.classify(sick_cow, frame_meta)
