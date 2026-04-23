"""Tests for src/skyherd/vision/preprocess.py and src/skyherd/vision/detector.py.

TDD RED phase: these tests should fail before the modules exist.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from skyherd.world.cattle import Cow

# ---------------------------------------------------------------------------
# preprocess tests
# ---------------------------------------------------------------------------


def test_preprocess_import() -> None:
    """preprocess module exports required symbols."""
    from skyherd.vision import preprocess as pp  # noqa: F401

    assert hasattr(pp, "load_frame_as_array")
    assert hasattr(pp, "crop_region")
    assert hasattr(pp, "array_to_tensor")
    assert hasattr(pp, "_PREPROCESS")


def test_crop_region_normal() -> None:
    """crop_region returns correct slice from array."""
    from skyherd.vision.preprocess import crop_region

    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    arr[20:120, 10:110] = 100  # fill known region
    cropped = crop_region(arr, (10, 20, 110, 120))
    assert cropped.shape == (100, 100, 3)
    assert cropped[0, 0, 0] == 100


def test_crop_region_clamp_to_bounds() -> None:
    """crop_region clamps coordinates that exceed array bounds."""
    from skyherd.vision.preprocess import crop_region

    arr = np.ones((480, 640, 3), dtype=np.uint8)
    # Request a crop extending outside array bounds
    cropped = crop_region(arr, (-10, -5, 700, 500))
    # Should be clamped to valid range — non-empty
    assert cropped.shape[0] > 0
    assert cropped.shape[1] > 0
    assert cropped.ndim == 3


def test_array_to_tensor_normal() -> None:
    """array_to_tensor produces (3, 224, 224) float tensor."""
    from skyherd.vision.preprocess import array_to_tensor

    crop = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    t = array_to_tensor(crop)
    assert isinstance(t, torch.Tensor)
    assert t.shape == (3, 224, 224)
    assert t.dtype == torch.float32


def test_array_to_tensor_degenerate_crop() -> None:
    """array_to_tensor handles 1x1 degenerate crop without crashing."""
    from skyherd.vision.preprocess import array_to_tensor

    tiny = np.zeros((1, 1, 3), dtype=np.uint8)
    t = array_to_tensor(tiny)
    assert t.shape == (3, 224, 224)


def test_array_to_tensor_empty_crop() -> None:
    """array_to_tensor handles 0-element crop without crashing."""
    from skyherd.vision.preprocess import array_to_tensor

    empty = np.zeros((0, 0, 3), dtype=np.uint8)
    t = array_to_tensor(empty)
    assert t.shape == (3, 224, 224)


def test_load_frame_as_array(tmp_path: Path) -> None:
    """load_frame_as_array loads a PNG file and returns (H, W, 3) uint8 array."""
    from PIL import Image

    from skyherd.vision.preprocess import load_frame_as_array

    # Create a test PNG
    img = Image.fromarray(np.zeros((480, 640, 3), dtype=np.uint8), mode="RGB")
    png_path = tmp_path / "test_frame.png"
    img.save(str(png_path))

    arr = load_frame_as_array(png_path)
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (480, 640, 3)
    assert arr.dtype == np.uint8


def test_preprocess_normalizes_to_imagenet() -> None:
    """_PREPROCESS pipeline normalizes to ImageNet stats (mean ~0.449 for 128-gray input)."""
    from PIL import Image

    from skyherd.vision.preprocess import _PREPROCESS

    # 128/255 grey image
    gray_img = Image.fromarray(np.full((224, 224, 3), 128, dtype=np.uint8))
    t = _PREPROCESS(gray_img)
    # After (128/255 - 0.485) / 0.229 ≈ -0.04, value should be near 0, not raw pixel value
    assert t.max().item() < 5.0  # definitely normalized (not 0-255)


# ---------------------------------------------------------------------------
# detector tests
# ---------------------------------------------------------------------------


def test_detector_import() -> None:
    """detector module exports required symbols."""
    from skyherd.vision import detector as det  # noqa: F401

    assert hasattr(det, "cow_bbox_in_frame")
    assert hasattr(det, "eye_crop_bbox")


def _make_cow(
    pos: tuple[float, float] = (300.0, 300.0), lameness_score: int = 0
) -> Cow:
    return Cow(
        id="c1",
        tag="T001",
        pos=pos,
        lameness_score=lameness_score,
    )


def test_cow_bbox_returns_4_tuple() -> None:
    """cow_bbox_in_frame returns a 4-element tuple of ints."""
    from skyherd.vision.detector import cow_bbox_in_frame

    cow = _make_cow()
    bb = cow_bbox_in_frame(cow, (2000.0, 2000.0))
    assert len(bb) == 4
    assert all(isinstance(v, int) for v in bb)


def test_cow_bbox_x0_lt_x1_y0_lt_y1() -> None:
    """Bbox coordinates are ordered: x0 < x1 and y0 < y1."""
    from skyherd.vision.detector import cow_bbox_in_frame

    cow = _make_cow()
    x0, y0, x1, y1 = cow_bbox_in_frame(cow, (2000.0, 2000.0))
    assert x0 < x1, f"x0={x0} must be < x1={x1}"
    assert y0 < y1, f"y0={y0} must be < y1={y1}"


def test_cow_bbox_clamped_to_frame() -> None:
    """Bbox does not exceed 640x480 frame dimensions."""
    from skyherd.vision.detector import cow_bbox_in_frame

    # Cow near edge of world
    cow = _make_cow(pos=(1990.0, 1990.0))
    x0, y0, x1, y1 = cow_bbox_in_frame(cow, (2000.0, 2000.0))
    assert 0 <= x0 < 640
    assert 0 <= y0 < 480
    assert x1 <= 639
    assert y1 <= 479


def test_eye_crop_bbox_returns_4_tuple() -> None:
    """eye_crop_bbox returns a 4-element tuple."""
    from skyherd.vision.detector import cow_bbox_in_frame, eye_crop_bbox

    cow = _make_cow()
    bb = cow_bbox_in_frame(cow, (2000.0, 2000.0))
    eb = eye_crop_bbox(bb, cow)
    assert len(eb) == 4


def test_eye_crop_bbox_ordered_and_clamped() -> None:
    """Eye crop bbox is ordered and within frame."""
    from skyherd.vision.detector import cow_bbox_in_frame, eye_crop_bbox

    cow = _make_cow()
    bb = cow_bbox_in_frame(cow, (2000.0, 2000.0))
    ex0, ey0, ex1, ey1 = eye_crop_bbox(bb, cow)
    assert ex0 < ex1, f"eye x0={ex0} must be < x1={ex1}"
    assert ey0 < ey1, f"eye y0={ey0} must be < y1={ey1}"
    assert 0 <= ex0
    assert 0 <= ey0
    assert ex1 <= 639
    assert ey1 <= 479


def test_cow_bbox_reflects_world_projection() -> None:
    """Cow near world origin projects near top-left of frame (Y-flipped)."""
    from skyherd.vision.detector import cow_bbox_in_frame

    # Cow at lower-left of world (0, near 0) should appear near top of frame
    # because world Y is flipped: py = (1 - y/bounds) * H
    cow = _make_cow(pos=(100.0, 1950.0))  # top of world → small py
    x0, y0, x1, y1 = cow_bbox_in_frame(cow, (2000.0, 2000.0))
    # Small world y → py near 0 (small fy), centered near top of frame
    assert y0 < 100, f"Cow at top of world should have small y0, got {y0}"


def test_detector_no_circular_import() -> None:
    """detector module can be imported without triggering a circular import."""
    import importlib

    # This should succeed without ImportError
    mod = importlib.import_module("skyherd.vision.detector")
    assert mod is not None
