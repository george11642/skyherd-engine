"""Geometric helpers — world-to-pixel projection for the vision pixel heads.

Provides ``cow_bbox_in_frame`` and ``eye_crop_bbox`` that mirror the formulas
in ``src/skyherd/vision/renderer.py::_world_to_frame`` and
``_draw_cow_blob`` byte-for-byte, so the classifier sees the exact eye region
the renderer drew.

Uses ``TYPE_CHECKING`` for the ``Cow`` import to avoid a circular import
through ``skyherd.world`` at module load time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skyherd.world.cattle import Cow

# ---------------------------------------------------------------------------
# Frame / blob constants — must match renderer.py exactly
# ---------------------------------------------------------------------------

_FRAME_W = 640
_FRAME_H = 480

# Body ellipse radii from _draw_cow_blob
_R_X = 18
_R_Y = 12

# Padding added around the body bbox
_PAD = 4


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def cow_bbox_in_frame(cow: Cow, bounds_m: tuple[float, float]) -> tuple[int, int, int, int]:
    """Reverse-project cow world pos to a pixel bbox covering the body + head.

    Formulas match ``src/skyherd/vision/renderer.py::_world_to_frame`` and
    ``_draw_cow_blob`` (lines 39-98) byte-for-byte:

    .. code-block:: python

        fx = int(pos[0] / bounds_m[0] * frame_w)
        fy = int((1.0 - pos[1] / bounds_m[1]) * frame_h)

    Parameters
    ----------
    cow:
        Current :class:`~skyherd.world.cattle.Cow` state.
    bounds_m:
        World bounding box ``(width_m, height_m)`` — matches
        ``terrain.config.bounds_m``.

    Returns
    -------
    tuple[int, int, int, int]
        Pixel bbox ``(x0, y0, x1, y1)`` in raw 640×480 coordinates.
    """
    fx = int(cow.pos[0] / bounds_m[0] * _FRAME_W)
    fy = int((1.0 - cow.pos[1] / bounds_m[1]) * _FRAME_H)
    fx = max(0, min(_FRAME_W - 1, fx))
    fy = max(0, min(_FRAME_H - 1, fy))
    tilt = cow.lameness_score
    return (
        max(0, fx - _R_X - _PAD),
        max(0, fy - _R_Y - 16 + tilt),
        min(_FRAME_W - 1, fx + _R_X + _PAD),
        min(_FRAME_H - 1, fy + _R_Y + tilt + 2),
    )


def eye_crop_bbox(cow_bbox: tuple[int, int, int, int], cow: Cow) -> tuple[int, int, int, int]:
    """Return a 48×48-pixel bbox around the eye region within *cow_bbox*.

    Mirrors the ``_draw_cow_blob`` eye-coordinate computation:

    .. code-block:: python

        hx, hy = cx + r_x - 4, cy - r_y + tilt - 6

    Parameters
    ----------
    cow_bbox:
        Body bbox from :func:`cow_bbox_in_frame`.
    cow:
        Current :class:`~skyherd.world.cattle.Cow` state (provides
        ``lameness_score`` for the tilt offset).

    Returns
    -------
    tuple[int, int, int, int]
        Pixel bbox ``(x0, y0, x1, y1)`` in raw 640×480 coordinates.
    """
    x0, y0, x1, y1 = cow_bbox
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    hx = cx + _R_X - 4
    hy = cy - _R_Y + cow.lameness_score - 6
    half = 24
    return (
        max(0, hx - half),
        max(0, hy - half),
        min(_FRAME_W - 1, hx + half),
        min(_FRAME_H - 1, hy + half),
    )
