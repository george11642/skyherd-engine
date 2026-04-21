"""Frame renderers — synthetic scene images for vision pipeline testing and demos.

All rendering is deterministic given the same world state; no random state is
used directly — all randomness flows through the world's seeded RNG before
this module is called.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from skyherd.vision.result import DetectionResult

# ---------------------------------------------------------------------------
# Frame dimensions
# ---------------------------------------------------------------------------

_TROUGH_W, _TROUGH_H = 640, 480
_THERMAL_W, _THERMAL_H = 320, 240

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

_BG_TOP = (34, 85, 34)   # dark pasture green
_BG_BOT = (56, 120, 45)  # lighter green at horizon
_TROUGH_COLOUR = (120, 80, 40)   # brown trough rectangle
_COW_BASE = (180, 140, 100)      # fawn body colour
_COW_SICK_EYE = (220, 60, 60)   # red discharge streak
_COW_LAME_TILT = (200, 100, 40)  # darker amber when tilted


def _world_to_frame(
    pos: tuple[float, float],
    bounds_m: tuple[float, float],
    frame_w: int,
    frame_h: int,
) -> tuple[int, int]:
    """Project world coords (metres) into image pixel coords."""
    fx = int(pos[0] / bounds_m[0] * frame_w)
    fy = int((1.0 - pos[1] / bounds_m[1]) * frame_h)  # Y flipped (world SW = image bottom)
    return (
        max(0, min(frame_w - 1, fx)),
        max(0, min(frame_h - 1, fy)),
    )


def _draw_cow_blob(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    ocular_discharge: float,
    lameness_score: int,
) -> None:
    """Draw a simple cow silhouette blob centred at (cx, cy)."""
    # Body ellipse
    body_colour = _COW_LAME_TILT if lameness_score >= 3 else _COW_BASE
    r_x, r_y = 18, 12
    tilt = lameness_score  # pixels of vertical offset for tilted posture
    draw.ellipse(
        [cx - r_x, cy - r_y + tilt, cx + r_x, cy + r_y + tilt],
        fill=body_colour,
        outline=(80, 60, 30),
    )

    # Head
    hx, hy = cx + r_x - 4, cy - r_y + tilt - 6
    draw.ellipse([hx - 6, hy - 5, hx + 6, hy + 5], fill=body_colour, outline=(80, 60, 30))

    # Ears
    draw.ellipse([hx - 4, hy - 10, hx, hy - 5], fill=(160, 110, 70))
    draw.ellipse([hx + 2, hy - 10, hx + 8, hy - 5], fill=(160, 110, 70))

    # Legs (4 short lines)
    for lx_off in [-10, -4, 4, 10]:
        leg_x = cx + lx_off
        draw.line(
            [leg_x, cy + r_y + tilt, leg_x, cy + r_y + tilt + 10],
            fill=(90, 60, 30),
            width=2,
        )

    # Ocular discharge streak
    if ocular_discharge > 0.5:
        streak_alpha = int((ocular_discharge - 0.5) * 2.0 * 200)
        streak_colour = (
            min(255, _COW_SICK_EYE[0]),
            max(0, _COW_SICK_EYE[1] - streak_alpha // 4),
            max(0, _COW_SICK_EYE[2] - streak_alpha // 4),
        )
        draw.line([hx + 1, hy, hx + 3, hy + 14], fill=streak_colour, width=2)
        draw.line([hx - 1, hy + 1, hx + 1, hy + 12], fill=streak_colour, width=1)


def render_trough_frame(
    world: Any,
    trough_id: str,
    out_path: Path | None = None,
) -> Path:
    """Render a 640×480 RGB composite of the paddock trough view.

    Shows a green paddock background, trough rectangle, and up to N cow-shaped
    blobs projected from world coordinates.  Sick cows (ocular_discharge > 0.5
    or lameness_score > 2) receive visual overlays.  Deterministic given the
    same world state.

    Parameters
    ----------
    world:
        The :class:`~skyherd.world.world.World` instance (or any object with
        ``.terrain``, ``.herd``, and ``.weather_driver`` attributes).
    trough_id:
        ID of the trough to centre the view on.
    out_path:
        Destination path for the PNG.  Defaults to a temp file if omitted.

    Returns
    -------
    Path
        Absolute path to the written PNG.
    """
    if out_path is None:
        import tempfile

        out_path = Path(tempfile.mktemp(suffix=".png"))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (_TROUGH_W, _TROUGH_H), _BG_TOP)
    draw = ImageDraw.Draw(img)

    # Gradient background — draw horizontal bands top→bottom
    for y in range(_TROUGH_H):
        t = y / _TROUGH_H
        r = int(_BG_TOP[0] * (1 - t) + _BG_BOT[0] * t)
        g = int(_BG_TOP[1] * (1 - t) + _BG_BOT[1] * t)
        b = int(_BG_TOP[2] * (1 - t) + _BG_BOT[2] * t)
        draw.line([(0, y), (_TROUGH_W, y)], fill=(r, g, b))

    # Trough rectangle (centred horizontally, lower third)
    tx0, ty0 = _TROUGH_W // 4, _TROUGH_H * 2 // 3
    tx1, ty1 = _TROUGH_W * 3 // 4, _TROUGH_H * 2 // 3 + 30
    draw.rectangle([tx0, ty0, tx1, ty1], fill=_TROUGH_COLOUR, outline=(60, 40, 10), width=2)
    # Water inside trough
    draw.rectangle(
        [tx0 + 4, ty0 + 4, tx1 - 4, ty1 - 4],
        fill=(70, 130, 180),
    )

    # Find trough position in world coords
    for t in world.terrain.config.troughs:
        if t.id == trough_id:
            break

    bounds_m: tuple[float, float] = world.terrain.config.bounds_m

    # Draw cows
    for cow in world.herd.cows:
        cx, cy = _world_to_frame(cow.pos, bounds_m, _TROUGH_W, _TROUGH_H)
        _draw_cow_blob(
            draw=draw,
            cx=cx,
            cy=cy,
            ocular_discharge=cow.ocular_discharge,
            lameness_score=cow.lameness_score,
        )

    img.save(str(out_path), "PNG")
    return out_path


def render_thermal_frame(
    world: Any,
    center_pos: tuple[float, float],
    fov_deg: float = 60.0,
    out_path: Path | None = None,
) -> Path:
    """Render a 320×240 grayscale thermal image.

    Cows in the field-of-view appear as warm Gaussian blobs; predators appear
    as hotter blobs.

    Parameters
    ----------
    world:
        World instance.
    center_pos:
        Camera centre position in world metres (x, y).
    fov_deg:
        Horizontal field of view in degrees.
    out_path:
        Destination path.

    Returns
    -------
    Path
        Absolute path to the PNG.
    """
    if out_path is None:
        import tempfile

        out_path = Path(tempfile.mktemp(suffix=".png"))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    arr = np.zeros((_THERMAL_H, _THERMAL_W), dtype=np.float32)
    bounds_m: tuple[float, float] = world.terrain.config.bounds_m

    # FOV radius in world metres (approximate; no perspective distortion)
    half_fov_rad = math.radians(fov_deg / 2)
    fov_radius_m = bounds_m[0] * math.tan(half_fov_rad)

    def _add_blob(
        world_pos: tuple[float, float],
        heat: float,
        sigma_px: float,
    ) -> None:
        dx = world_pos[0] - center_pos[0]
        dy = world_pos[1] - center_pos[1]
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > fov_radius_m:
            return
        # Map world position into thermal frame
        fx = int((dx / fov_radius_m + 1.0) / 2.0 * _THERMAL_W)
        fy = int((1.0 - (dy / fov_radius_m + 1.0) / 2.0) * _THERMAL_H)
        # Gaussian splat
        for py in range(max(0, fy - 20), min(_THERMAL_H, fy + 21)):
            for px in range(max(0, fx - 20), min(_THERMAL_W, fx + 21)):
                d2 = (px - fx) ** 2 + (py - fy) ** 2
                arr[py, px] += heat * math.exp(-d2 / (2.0 * sigma_px ** 2))

    # Cows — warm blobs (heat 0.5–0.8)
    for cow in world.herd.cows:
        cow_heat = 0.5 + min(0.3, cow.health_score * 0.1)
        _add_blob(cow.pos, cow_heat, sigma_px=6.0)

    # Predators — hotter blobs (heat 0.9)
    for pred in world.predator_spawner.predators:
        _add_blob(pred.pos, 0.9, sigma_px=5.0)

    # Normalise and convert to uint8 grayscale
    max_val = arr.max()
    if max_val > 0:
        arr = arr / max_val
    gray = (arr * 255).astype(np.uint8)
    img = Image.fromarray(gray, mode="L")
    img.save(str(out_path), "PNG")
    return out_path


def annotate_frame(
    image_path: Path,
    detections: list[DetectionResult],
    out_path: Path | None = None,
) -> Path:
    """Overlay bounding-box annotations using supervision.

    Draws one box per :class:`DetectionResult` at a pseudo-position derived
    from the detection index (deterministic layout for demo use).  Uses
    ``supervision.BoxAnnotator`` and ``supervision.LabelAnnotator``.

    Parameters
    ----------
    image_path:
        Source frame (PNG).
    detections:
        List of detection results to annotate.
    out_path:
        Destination path.  Defaults to a temp file.

    Returns
    -------
    Path
        Absolute path to the annotated PNG.
    """
    import supervision as sv

    if out_path is None:
        import tempfile

        out_path = Path(tempfile.mktemp(suffix=".png"))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(str(image_path)).convert("RGB")
    frame = np.array(img)

    if not detections:
        img.save(str(out_path), "PNG")
        return out_path

    # Build supervision Detections from results
    len(detections)
    w, h = img.size
    box_w, box_h = w // 6, h // 8

    xyxy: list[list[float]] = []
    labels: list[str] = []
    class_ids: list[int] = []

    severity_to_class = {"watch": 0, "log": 1, "escalate": 2, "vet_now": 3}

    for i, det in enumerate(detections):
        # Spread boxes across the frame in a grid layout
        col = i % 4
        row = i // 4
        x0 = col * (w // 4) + 10
        y0 = row * (h // 5) + 10
        x1 = min(x0 + box_w, w - 5)
        y1 = min(y0 + box_h, h - 5)
        xyxy.append([float(x0), float(y0), float(x1), float(y1)])
        labels.append(f"{det.head_name}:{det.severity} [{det.cow_tag}]")
        class_ids.append(severity_to_class.get(det.severity, 0))

    sv_detections = sv.Detections(
        xyxy=np.array(xyxy, dtype=float),
        class_id=np.array(class_ids, dtype=int),
    )

    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()

    annotated = box_annotator.annotate(scene=frame, detections=sv_detections)
    annotated = label_annotator.annotate(
        scene=annotated, detections=sv_detections, labels=labels
    )

    Image.fromarray(annotated).save(str(out_path), "PNG")
    return out_path
