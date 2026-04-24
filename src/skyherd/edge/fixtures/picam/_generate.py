"""Deterministic generator for PiCamSensor sample fixture frames.

Creates 4 synthetic 640x480 RGB PNGs (frame_00.png ... frame_03.png) with
varying eye-region cues so the pinkeye MobileNetV3-Small classifier exercises
different output classes during tests.

Run:
    python -m skyherd.edge.fixtures.picam._generate

Idempotent: writing twice yields byte-identical output.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

FIXTURE_DIR = Path(__file__).parent
FRAMES = 4
WIDTH = 640
HEIGHT = 480


def _render_frame(idx: int) -> np.ndarray:
    """Deterministic synthetic frame parameterised by idx in [0, 3].

    idx=0 → clean pasture (healthy eye)
    idx=1 → mild tearing (watch)
    idx=2 → opacity + staining (log)
    idx=3 → deep ulcer + swelling (escalate)
    """
    rng = np.random.RandomState(42 + idx)  # noqa: NPY002 — intentional legacy RNG for determinism
    # Base green pasture
    arr = np.full((HEIGHT, WIDTH, 3), [34, 85, 34], dtype=np.uint8)

    # Add some brown dirt patches
    for _ in range(20):
        cx = int(rng.randint(0, WIDTH))
        cy = int(rng.randint(0, HEIGHT))
        r = int(rng.randint(10, 40))
        _draw_circle(arr, cx, cy, r, (92, 72, 48))

    # Cow body — large tan rectangle in centre
    body_x0, body_y0 = WIDTH // 4, HEIGHT // 3
    body_x1, body_y1 = 3 * WIDTH // 4, 2 * HEIGHT // 3
    arr[body_y0:body_y1, body_x0:body_x1] = [200, 180, 150]

    # Head — smaller rectangle left-centre
    head_x0, head_y0 = body_x0 - 80, HEIGHT // 3 + 20
    head_x1, head_y1 = body_x0 + 20, body_y0 + 140
    head_x0 = max(0, head_x0)
    head_y0 = max(0, head_y0)
    arr[head_y0:head_y1, head_x0:head_x1] = [210, 190, 160]

    # Eye region — this is what the pinkeye classifier will attend to.
    eye_cx = head_x0 + 30
    eye_cy = head_y0 + 60
    eye_r = 18

    if idx == 0:
        # Healthy: small dark pupil on white sclera
        _draw_circle(arr, eye_cx, eye_cy, eye_r, (240, 240, 235))
        _draw_circle(arr, eye_cx, eye_cy, 6, (10, 10, 10))
    elif idx == 1:
        # Mild tearing: pinkish tint + tear streak below
        _draw_circle(arr, eye_cx, eye_cy, eye_r, (230, 200, 200))
        _draw_circle(arr, eye_cx, eye_cy, 5, (10, 10, 10))
        for dy in range(1, 30):
            arr[min(eye_cy + dy, HEIGHT - 1), eye_cx] = [170, 140, 140]
    elif idx == 2:
        # Opacity + dark staining
        _draw_circle(arr, eye_cx, eye_cy, eye_r, (180, 160, 160))
        _draw_circle(arr, eye_cx, eye_cy, 10, (80, 70, 70))
        for dy in range(1, 40):
            for dx in range(-6, 6):
                yy = min(eye_cy + dy, HEIGHT - 1)
                xx = max(0, min(WIDTH - 1, eye_cx + dx))
                arr[yy, xx] = [60, 50, 50]
    else:  # idx == 3
        # Deep ulcer + swelling
        _draw_circle(arr, eye_cx, eye_cy, eye_r + 6, (140, 110, 110))
        _draw_circle(arr, eye_cx, eye_cy, 14, (255, 210, 210))
        _draw_circle(arr, eye_cx, eye_cy, 6, (40, 20, 20))

    return arr


def _draw_circle(arr: np.ndarray, cx: int, cy: int, r: int, rgb: tuple[int, int, int]) -> None:
    """Fill a filled circle on arr in-place (clipping to bounds)."""
    h, w = arr.shape[:2]
    yy, xx = np.ogrid[:h, :w]
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    arr[mask] = rgb


def generate(out_dir: Path | None = None) -> list[Path]:
    """Write frame_00.png … frame_03.png under *out_dir* (default: fixture dir)."""
    target = out_dir or FIXTURE_DIR
    target.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for idx in range(FRAMES):
        arr = _render_frame(idx)
        out = target / f"frame_{idx:02d}.png"
        Image.fromarray(arr).save(str(out), format="PNG")
        paths.append(out)
    return paths


def hashes() -> dict[str, str]:
    """Return SHA-256 of each generated PNG — used for determinism tests."""
    result: dict[str, str] = {}
    for p in sorted(FIXTURE_DIR.glob("frame_*.png")):
        result[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


if __name__ == "__main__":
    paths = generate()
    for p in paths:
        print(p)
    print("sha256:")
    for name, h in hashes().items():
        print(f"  {name}: {h}")
