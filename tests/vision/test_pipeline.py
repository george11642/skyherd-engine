"""Tests for ClassifyPipeline — end-to-end world snapshot → detections."""

from __future__ import annotations

from pathlib import Path

import pytest

# supervision requires opencv-python (cv2) which is not installed in the base
# WSL2 / CI environment.  Skip cleanly rather than failing with ImportError.
pytest.importorskip("cv2", reason="opencv-python not installed in this environment")

from skyherd.vision.pipeline import ClassifyPipeline  # noqa: E402
from skyherd.world.world import World


def test_pipeline_returns_detections_for_sick_cow(
    world_with_sick_cow: World, tmp_path: Path
) -> None:
    """Pipeline returns at least 1 detection when a sick cow is present."""
    pipeline = ClassifyPipeline()
    result = pipeline.run(world_with_sick_cow, "trough_a", out_dir=tmp_path)
    assert result.detection_count >= 1


def test_pipeline_returns_zero_detections_for_healthy_herd(
    world_healthy: World, tmp_path: Path
) -> None:
    """Pipeline returns 0 detections for a herd of fully healthy cows."""
    pipeline = ClassifyPipeline()
    result = pipeline.run(world_healthy, "trough_a", out_dir=tmp_path)
    assert result.detection_count == 0


def test_pipeline_writes_annotated_frame(world_with_sick_cow: World, tmp_path: Path) -> None:
    """Pipeline produces an annotated PNG file."""
    pipeline = ClassifyPipeline()
    result = pipeline.run(world_with_sick_cow, "trough_a", out_dir=tmp_path)
    assert result.annotated_frame_path.exists()
    assert result.annotated_frame_path.suffix == ".png"


def test_pipeline_result_has_cow_tags(world_with_sick_cow: World, tmp_path: Path) -> None:
    """Every DetectionResult has a non-empty cow_tag."""
    pipeline = ClassifyPipeline()
    result = pipeline.run(world_with_sick_cow, "trough_a", out_dir=tmp_path)
    for det in result.detections:
        assert det.cow_tag, "cow_tag must not be empty"


def test_pipeline_frame_meta_override(world_with_sick_cow: World, tmp_path: Path) -> None:
    """frame_meta_override is accepted without crashing."""
    pipeline = ClassifyPipeline()
    result = pipeline.run(
        world_with_sick_cow,
        "trough_a",
        frame_meta_override={"respiration_bpm": 75},
        out_dir=tmp_path,
    )
    assert result is not None


def test_pipeline_default_out_dir(world_healthy: World) -> None:
    """Pipeline works without providing out_dir (uses temp dir)."""
    pipeline = ClassifyPipeline()
    result = pipeline.run(world_healthy, "trough_a")
    assert result.annotated_frame_path.exists()
