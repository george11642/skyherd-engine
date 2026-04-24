"""Deterministic generator for cardboard-coyote thermal clip fixture frames.

Creates 6 grayscale PNGs simulating a coyote's thermal signature drifting
across a 160x120 FLIR-style viewport.

Run:
    python -m tests.fixtures.thermal_clips._generate

Idempotent: produces byte-identical output per run.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

FIXTURE_DIR = Path(__file__).parent
FRAMES = 6
WIDTH = 160
HEIGHT = 120


def _render_thermal(idx: int) -> np.ndarray:
    """Produce a grayscale thermal frame parameterised by idx in [0, 5].

    Simulates a coyote (warm blob) drifting left-to-right across the frame.
    Background mimics a cold pasture at night (dark gray).
    """
    # Background: cold ground with low-level noise
    rng = np.random.RandomState(42 + idx)  # noqa: NPY002 — intentional for determinism
    bg = rng.randint(20, 50, size=(HEIGHT, WIDTH), dtype=np.uint8)

    # Warm blob: Gaussian at a drifting centre
    # idx 0 → left edge, idx 5 → right edge
    cx = int(20 + (WIDTH - 40) * (idx / (FRAMES - 1)))
    cy = HEIGHT // 2 + (idx - 2) * 3  # slight vertical drift

    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    # Anisotropic Gaussian — slightly wider than tall (coyote body)
    sigma_x = 18.0
    sigma_y = 10.0
    gauss = np.exp(
        -(((xx - cx) ** 2) / (2 * sigma_x**2) + ((yy - cy) ** 2) / (2 * sigma_y**2))
    )
    # Scale to [0, 200] and add to background
    blob = (gauss * 210).astype(np.int16)
    arr = np.clip(bg.astype(np.int16) + blob, 0, 255).astype(np.uint8)
    return arr


def generate(out_dir: Path | None = None) -> list[Path]:
    target = out_dir or FIXTURE_DIR
    target.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for idx in range(FRAMES):
        arr = _render_thermal(idx)
        out = target / f"frame_{idx:02d}.png"
        Image.fromarray(arr).save(str(out), format="PNG")
        paths.append(out)
    return paths


def hashes() -> dict[str, str]:
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
