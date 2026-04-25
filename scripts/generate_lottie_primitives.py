"""Generate 5 minimal Lottie JSON primitives for the SkyHerd video.

Phase E2 of the video-v2 plan. Rather than pulling from LottieFiles (which
would require hunting for CC0/MIT assets and recording each provenance),
we author the primitives in-repo so the licensing story is unambiguous:
**CC0 — authored by the SkyHerd project, no external source**.

Each JSON follows the Bodymovin schema that ``@remotion/lottie`` understands.
Primitives emitted:

  * ``stat-counter.json`` — number rolls up with fade-in
  * ``map-pin-drop.json`` — pin drops with bounce
  * ``hash-chip-slide.json`` — chip slides in from the right with fade
  * ``pulse-wave.json`` — concentric circles pulse outward
  * ``check-complete.json`` — checkmark draws in then settles

All primitives are 150 × 150 px, 30 fps, 60-frame (2 s) default loop.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "remotion-video" / "public" / "lottie"

FPS = 30
DURATION_FRAMES = 60  # 2 s
SIZE = 150


def _base(name: str) -> dict[str, Any]:
    """Common Bodymovin header."""
    return {
        "v": "5.9.6",
        "fr": FPS,
        "ip": 0,
        "op": DURATION_FRAMES,
        "w": SIZE,
        "h": SIZE,
        "nm": name,
        "ddd": 0,
        "assets": [],
        "layers": [],
    }


def _shape_ellipse(size: float, color: tuple[float, float, float]) -> dict[str, Any]:
    return {
        "ty": "gr",
        "it": [
            {"ty": "el", "p": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [size, size]}},
            {"ty": "fl", "c": {"a": 0, "k": list(color) + [1]}, "o": {"a": 0, "k": 100}},
            {
                "ty": "tr",
                "p": {"a": 0, "k": [0, 0]},
                "a": {"a": 0, "k": [0, 0]},
                "s": {"a": 0, "k": [100, 100]},
                "r": {"a": 0, "k": 0},
                "o": {"a": 0, "k": 100},
            },
        ],
    }


def _text_layer(text: str, frame_in: int, frame_stable: int) -> dict[str, Any]:
    return {
        "ty": 5,  # text layer
        "nm": "text",
        "ks": {
            "o": {
                "a": 1,
                "k": [
                    {"t": frame_in, "s": [0], "h": 0},
                    {"t": frame_stable, "s": [100], "h": 0},
                ],
            },
            "r": {"a": 0, "k": 0},
            "p": {"a": 0, "k": [SIZE / 2, SIZE / 2 + 20, 0]},
            "a": {"a": 0, "k": [0, 0, 0]},
            "s": {"a": 0, "k": [100, 100, 100]},
        },
        "ao": 0,
        "ip": 0,
        "op": DURATION_FRAMES,
        "st": 0,
        "bm": 0,
        "t": {
            "d": {
                "k": [
                    {
                        "t": 0,
                        "s": {
                            "s": 32,
                            "f": "Inter",
                            "t": text,
                            "j": 2,
                            "tr": 0,
                            "lh": 38,
                            "ls": 0,
                            "fc": [0.925, 0.937, 0.956],
                        },
                    }
                ]
            },
            "p": {},
            "m": {"g": 1, "a": {"a": 0, "k": [0, 0]}},
            "a": [],
        },
    }


def _solid_shape_layer(
    name: str,
    shape: dict[str, Any],
    center_offset: tuple[float, float] = (SIZE / 2, SIZE / 2),
    scale_keyframes: list[dict[str, Any]] | None = None,
    opacity_keyframes: list[dict[str, Any]] | None = None,
    position_keyframes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    scale_anim = {"a": 0, "k": [100, 100, 100]}
    if scale_keyframes:
        scale_anim = {"a": 1, "k": scale_keyframes}

    opacity_anim = {"a": 0, "k": 100}
    if opacity_keyframes:
        opacity_anim = {"a": 1, "k": opacity_keyframes}

    position_anim = {"a": 0, "k": list(center_offset) + [0]}
    if position_keyframes:
        position_anim = {"a": 1, "k": position_keyframes}

    return {
        "ty": 4,  # shape layer
        "nm": name,
        "shapes": [shape],
        "ks": {
            "o": opacity_anim,
            "r": {"a": 0, "k": 0},
            "p": position_anim,
            "a": {"a": 0, "k": [0, 0, 0]},
            "s": scale_anim,
        },
        "ao": 0,
        "ip": 0,
        "op": DURATION_FRAMES,
        "st": 0,
        "bm": 0,
    }


# --------------------------------------------------------------------------- #
# Primitive builders                                                          #
# --------------------------------------------------------------------------- #


def stat_counter() -> dict[str, Any]:
    """Fade-in numeric pill — dust-color pill with a white number on top."""
    pill = _solid_shape_layer(
        "pill",
        _shape_ellipse(110, (0.823, 0.698, 0.541)),
        opacity_keyframes=[
            {"t": 0, "s": [0], "h": 0},
            {"t": 18, "s": [100], "h": 0},
        ],
        scale_keyframes=[
            {"t": 0, "s": [60, 60, 100], "h": 0},
            {"t": 18, "s": [100, 100, 100], "h": 0},
            {"t": 45, "s": [102, 102, 100], "h": 0},
            {"t": DURATION_FRAMES, "s": [100, 100, 100], "h": 0},
        ],
    )
    label = _text_layer("$4.17", 12, 28)
    doc = _base("stat-counter")
    doc["layers"] = [label, pill]
    return doc


def map_pin_drop() -> dict[str, Any]:
    """Pin drops from the top and bounces."""
    pin = _solid_shape_layer(
        "pin",
        _shape_ellipse(38, (0.941, 0.561, 0.235)),
        position_keyframes=[
            {"t": 0, "s": [SIZE / 2, -20, 0], "h": 0},
            {"t": 20, "s": [SIZE / 2, SIZE / 2 + 30, 0], "h": 0},
            {"t": 28, "s": [SIZE / 2, SIZE / 2 + 18, 0], "h": 0},
            {"t": 36, "s": [SIZE / 2, SIZE / 2 + 30, 0], "h": 0},
        ],
    )
    ring = _solid_shape_layer(
        "ring",
        _shape_ellipse(36, (0.941, 0.561, 0.235)),
        center_offset=(SIZE / 2, SIZE / 2 + 30),
        scale_keyframes=[
            {"t": 30, "s": [100, 100, 100], "h": 0},
            {"t": DURATION_FRAMES, "s": [260, 60, 100], "h": 0},
        ],
        opacity_keyframes=[
            {"t": 30, "s": [90], "h": 0},
            {"t": DURATION_FRAMES, "s": [0], "h": 0},
        ],
    )
    doc = _base("map-pin-drop")
    doc["layers"] = [ring, pin]
    return doc


def hash_chip_slide() -> dict[str, Any]:
    """Hash chip slides in from the right with fade."""
    chip = _solid_shape_layer(
        "chip",
        _shape_ellipse(72, (0.580, 0.690, 0.533)),
        position_keyframes=[
            {"t": 0, "s": [SIZE + 100, SIZE / 2, 0], "h": 0},
            {"t": 20, "s": [SIZE / 2, SIZE / 2, 0], "h": 0},
        ],
        opacity_keyframes=[
            {"t": 0, "s": [0], "h": 0},
            {"t": 14, "s": [100], "h": 0},
        ],
    )
    text = _text_layer("0x3a9f…", 6, 22)
    doc = _base("hash-chip-slide")
    doc["layers"] = [text, chip]
    return doc


def pulse_wave() -> dict[str, Any]:
    """Three concentric circles pulse outward."""
    doc = _base("pulse-wave")
    for idx, delay in enumerate((0, 10, 20)):
        ring = _solid_shape_layer(
            f"ring-{idx}",
            _shape_ellipse(24, (0.471, 0.706, 0.863)),
            scale_keyframes=[
                {"t": delay, "s": [100, 100, 100], "h": 0},
                {"t": delay + 28, "s": [320, 320, 100], "h": 0},
            ],
            opacity_keyframes=[
                {"t": delay, "s": [80], "h": 0},
                {"t": delay + 28, "s": [0], "h": 0},
            ],
        )
        doc["layers"].append(ring)
    return doc


def check_complete() -> dict[str, Any]:
    """Simple animated checkmark done with a rotating ring + check text."""
    ring = _solid_shape_layer(
        "ring",
        _shape_ellipse(96, (0.580, 0.690, 0.533)),
        scale_keyframes=[
            {"t": 0, "s": [0, 0, 100], "h": 0},
            {"t": 22, "s": [100, 100, 100], "h": 0},
        ],
        opacity_keyframes=[
            {"t": 0, "s": [0], "h": 0},
            {"t": 22, "s": [92], "h": 0},
        ],
    )
    check = _text_layer("✓", 16, 30)
    check["t"]["d"]["k"][0]["s"]["s"] = 60
    check["t"]["d"]["k"][0]["s"]["fc"] = [1, 1, 1]
    doc = _base("check-complete")
    doc["layers"] = [check, ring]
    return doc


PRIMITIVES = {
    "stat-counter.json": stat_counter,
    "map-pin-drop.json": map_pin_drop,
    "hash-chip-slide.json": hash_chip_slide,
    "pulse-wave.json": pulse_wave,
    "check-complete.json": check_complete,
}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, builder in PRIMITIVES.items():
        path = OUT_DIR / filename
        path.write_text(json.dumps(builder(), indent=2), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
