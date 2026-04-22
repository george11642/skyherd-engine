"""Tests for annotate_frame — supervision overlay on rendered frames."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from skyherd.vision.renderer import annotate_frame, render_trough_frame
from skyherd.vision.result import DetectionResult
from skyherd.world.world import World


def _make_detection(tag: str = "T001", severity: str = "watch") -> DetectionResult:
    return DetectionResult(
        head_name="pinkeye",
        cow_tag=tag,
        confidence=0.75,
        severity=severity,  # type: ignore[arg-type]
        reasoning="Test detection.",
    )


def test_annotate_frame_no_crash_with_detections(
    world_with_sick_cow: World, tmp_path: Path
) -> None:
    """annotate_frame runs without raising with one detection."""
    raw = tmp_path / "raw.png"
    render_trough_frame(world_with_sick_cow, "trough_a", out_path=raw)
    out = tmp_path / "annotated.png"
    result_path = annotate_frame(raw, [_make_detection()], out_path=out)
    assert result_path == out
    assert out.exists()


def test_annotate_frame_produces_valid_png(world_with_sick_cow: World, tmp_path: Path) -> None:
    """Output is a readable RGB PNG."""
    raw = tmp_path / "raw.png"
    render_trough_frame(world_with_sick_cow, "trough_a", out_path=raw)
    out = tmp_path / "annotated.png"
    annotate_frame(raw, [_make_detection()], out_path=out)
    img = Image.open(str(out))
    assert img.format == "PNG"
    assert img.mode == "RGB"


def test_annotate_frame_zero_detections(world_healthy: World, tmp_path: Path) -> None:
    """annotate_frame handles empty detections list without crashing."""
    raw = tmp_path / "raw.png"
    render_trough_frame(world_healthy, "trough_a", out_path=raw)
    out = tmp_path / "annotated_empty.png"
    result_path = annotate_frame(raw, [], out_path=out)
    assert result_path.exists()


def test_annotate_frame_multiple_detections(world_with_sick_cow: World, tmp_path: Path) -> None:
    """Multiple detections across all severity levels — no crash."""
    raw = tmp_path / "raw.png"
    render_trough_frame(world_with_sick_cow, "trough_a", out_path=raw)
    detections = [
        _make_detection("T001", "watch"),
        _make_detection("T002", "log"),
        _make_detection("T003", "escalate"),
        _make_detection("T004", "vet_now"),
    ]
    out = tmp_path / "multi.png"
    result_path = annotate_frame(raw, detections, out_path=out)
    assert result_path.exists()
    img = Image.open(str(out))
    assert img.size == (640, 480)


def test_annotate_frame_default_out_path(world_healthy: World, tmp_path: Path) -> None:
    """annotate_frame creates file at auto-generated temp path when out_path omitted."""
    raw = tmp_path / "raw.png"
    render_trough_frame(world_healthy, "trough_a", out_path=raw)
    result_path = annotate_frame(raw, [_make_detection()])
    assert result_path.exists()
    result_path.unlink(missing_ok=True)
