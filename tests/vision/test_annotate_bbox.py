"""Integration tests: DetectionResult.bbox flows into annotate_frame xyxy."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

pytest.importorskip("cv2", reason="opencv-python not installed in this environment")

from skyherd.vision.renderer import annotate_frame  # noqa: E402
from skyherd.vision.result import DetectionResult  # noqa: E402
from skyherd.world.world import World  # noqa: E402


def test_bbox_flows_to_annotated_png(
    rendered_negative_frame: tuple[Path, World], tmp_path: Path
) -> None:
    """DetectionResult.bbox coords are used directly by annotate_frame (not grid fallback)."""
    raw_path, _ = rendered_negative_frame
    det = DetectionResult(
        head_name="pinkeye",
        cow_tag="T001",
        confidence=0.9,
        severity="escalate",
        reasoning="test",
        bbox=(100.0, 150.0, 200.0, 250.0),
    )
    out_path = tmp_path / "annotated_bbox.png"
    annotate_frame(raw_path, [det], out_path=out_path)
    assert out_path.exists()
    original = np.array(Image.open(str(raw_path)).convert("RGB"))
    annotated = np.array(Image.open(str(out_path)).convert("RGB"))
    # The bbox region [150:250, 100:200] must differ from original (box+label drawn).
    region_orig = original[150:250, 100:200]
    region_annot = annotated[150:250, 100:200]
    assert not np.array_equal(region_orig, region_annot), (
        "annotate_frame did not draw on the bbox region — bbox branch is broken"
    )


def test_rule_head_grid_fallback_preserved(
    rendered_negative_frame: tuple[Path, World], tmp_path: Path
) -> None:
    """When bbox is None, annotate_frame still draws via the existing grid-layout fallback."""
    raw_path, _ = rendered_negative_frame
    det = DetectionResult(
        head_name="brd",
        cow_tag="T002",
        confidence=0.7,
        severity="log",
        reasoning="test",
        # bbox omitted — defaults to None
    )
    out_path = tmp_path / "annotated_grid.png"
    annotate_frame(raw_path, [det], out_path=out_path)
    assert out_path.exists()
    original = np.array(Image.open(str(raw_path)).convert("RGB"))
    annotated = np.array(Image.open(str(out_path)).convert("RGB"))
    assert not np.array_equal(original, annotated), (
        "annotate_frame produced a byte-identical output — grid-layout annotator silently no-op'd"
    )


def test_mixed_bbox_and_none_coexist(
    rendered_negative_frame: tuple[Path, World], tmp_path: Path
) -> None:
    """A detection list with both bbox-set and bbox-None entries annotates without error."""
    raw_path, _ = rendered_negative_frame
    dets = [
        DetectionResult(
            head_name="pinkeye",
            cow_tag="T001",
            confidence=0.9,
            severity="escalate",
            reasoning="pixel",
            bbox=(10.0, 20.0, 110.0, 120.0),
        ),
        DetectionResult(
            head_name="brd",
            cow_tag="T002",
            confidence=0.7,
            severity="log",
            reasoning="rule",
        ),
    ]
    out_path = tmp_path / "annotated_mixed.png"
    annotate_frame(raw_path, dets, out_path=out_path)
    assert out_path.exists()
    img = Image.open(str(out_path))
    assert img.size == (640, 480), f"expected 640x480, got {img.size}"
