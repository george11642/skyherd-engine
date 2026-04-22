"""Shared PNG → tensor preprocessing helpers for vision pixel heads.

Provides deterministic transforms (ImageNet normalization) shared by all
pixel-level disease detection heads in ``skyherd.vision.heads``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

# ---------------------------------------------------------------------------
# ImageNet normalization transform
# ---------------------------------------------------------------------------

_PREPROCESS = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ]
)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def load_frame_as_array(path: Path) -> np.ndarray:
    """Load PNG at *path* as an RGB uint8 (H, W, 3) numpy array.

    Parameters
    ----------
    path:
        Filesystem path to the PNG file.

    Returns
    -------
    np.ndarray
        Shape ``(H, W, 3)``, dtype ``uint8``.
    """
    with Image.open(str(path)) as img:
        return np.array(img.convert("RGB"))


def crop_region(arr: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    """Crop a (H, W, 3) array to *bbox* (x0, y0, x1, y1).

    Coordinates are clamped to the array bounds so callers do not need to
    guard against out-of-frame crop requests.

    Parameters
    ----------
    arr:
        Source image as ``(H, W, 3)`` uint8 array.
    bbox:
        ``(x0, y0, x1, y1)`` crop window in pixel space.

    Returns
    -------
    np.ndarray
        Cropped sub-array; always at least 1 pixel in each dimension.
    """
    h, w = arr.shape[:2]
    x0, y0, x1, y1 = bbox
    x0 = max(0, min(w - 1, x0))
    x1 = max(x0 + 1, min(w, x1))
    y0 = max(0, min(h - 1, y0))
    y1 = max(y0 + 1, min(h, y1))
    return arr[y0:y1, x0:x1]


def array_to_tensor(crop: np.ndarray) -> torch.Tensor:
    """Convert a (H, W, 3) uint8 crop to a (3, 224, 224) preprocessed tensor.

    Applies :data:`_PREPROCESS` (Resize + ToTensor + ImageNet Normalize).
    Handles degenerate crops (shape < 2 in any spatial dimension) by padding
    with a black 10×10 frame so :class:`~torchvision.transforms.Resize` always
    has valid input.

    Parameters
    ----------
    crop:
        ``(H, W, 3)`` uint8 numpy array.

    Returns
    -------
    torch.Tensor
        Float tensor of shape ``(3, 224, 224)``.
    """
    if crop.size == 0 or crop.shape[0] < 2 or crop.shape[1] < 2:
        # Degenerate crop — pad to 10x10 black so Resize has something to consume
        crop = np.zeros((10, 10, 3), dtype=np.uint8)
    img = Image.fromarray(crop)
    return _PREPROCESS(img)  # type: ignore[return-value]
