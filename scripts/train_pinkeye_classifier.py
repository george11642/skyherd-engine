#!/usr/bin/env python3
"""One-off training script for the pinkeye pixel classifier head.

NOT run in CI or at runtime. Generates synthetic frames from renderer.py,
fine-tunes MobileNetV3-Small's classifier head, runs a smoke test, and saves
the trained weights to src/skyherd/vision/_models/pinkeye_mbv3s.pth.

Usage:
    uv run python scripts/train_pinkeye_classifier.py --frames 500 --seed 42
"""

from __future__ import annotations

import argparse
import hashlib
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from torch.utils.data import DataLoader, TensorDataset
from torchvision import transforms
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
WEIGHTS_PATH = REPO_ROOT / "src" / "skyherd" / "vision" / "_models" / "pinkeye_mbv3s.pth"

_FRAME_W, _FRAME_H = 640, 480
_R_X, _R_Y = 18, 12

_PREPROCESS = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)

# Ocular-discharge sweep values — main grid + class-boundary jitter (RESEARCH.md A8 mitigation)
_DISCHARGE_SWEEP = [
    round(v, 2)
    for v in [i * 0.05 for i in range(21)]  # 0.0, 0.05, 0.1, ..., 1.0
] + [0.41, 0.45, 0.55, 0.59, 0.61, 0.65, 0.75, 0.79, 0.81, 0.85, 0.95]


# ---------------------------------------------------------------------------
# Label oracle (must match src/skyherd/vision/heads/pinkeye.py rule tiers)
# ---------------------------------------------------------------------------


def label_for_cow(ocular_discharge: float, has_pinkeye_flag: bool) -> int:
    """Map ocular_discharge + flag to 4-class label index.

    0 = healthy, 1 = watch, 2 = log, 3 = escalate.
    Order and thresholds must match the rule head's severity tiers.
    """
    if ocular_discharge <= 0.4 and not has_pinkeye_flag:
        return 0  # healthy
    if has_pinkeye_flag and ocular_discharge <= 0.4:
        return 2  # log (flag override)
    if ocular_discharge < 0.6:
        return 1  # watch
    if ocular_discharge < 0.8:
        return 2  # log
    return 3  # escalate


# ---------------------------------------------------------------------------
# Eye-crop helper
# ---------------------------------------------------------------------------


def eye_crop(
    frame_arr: np.ndarray,
    cow_pos: tuple[float, float],
    bounds_m: tuple[float, float],
    tilt: int = 0,
) -> np.ndarray:
    """Crop the 48×48 eye region from a rendered frame array.

    Applies the same reverse-projection formula as renderer._draw_cow_blob so
    that the crop window is centred on the rendered head position.

    Parameters
    ----------
    frame_arr:
        HxWx3 uint8 numpy array (e.g. from ``np.array(Image.open(...))``)
    cow_pos:
        (px, py) world position in metres.
    bounds_m:
        (bx, by) world bounds in metres.
    tilt:
        Lameness tilt offset (matches lameness_score used in renderer).
    """
    px, py = cow_pos
    bx, by = bounds_m

    # World → frame projection (mirrors renderer._world_to_frame)
    fx = int(px / bx * _FRAME_W)
    fy = int((1.0 - py / by) * _FRAME_H)

    # Head centre (mirrors renderer._draw_cow_blob head calculation)
    hx = fx + _R_X - 4
    hy = fy - _R_Y + tilt - 6

    # 48×48 window centred on head
    half = 24
    x0 = max(0, hx - half)
    y0 = max(0, hy - half)
    x1 = min(_FRAME_W - 1, hx + half)
    y1 = min(_FRAME_H - 1, hy + half)

    return frame_arr[y0:y1, x0:x1]


# ---------------------------------------------------------------------------
# World builder (mirrors tests/vision/conftest.py without importing from tests)
# ---------------------------------------------------------------------------


def _build_world(ocular_discharge: float, has_flag: bool, seed: int) -> object:
    """Construct a minimal single-cow World for a given disease state."""
    # Import here to allow the module to be imported without the full package
    # on the PATH (the script is dev-time only).
    from skyherd.world.cattle import Cow, Herd
    from skyherd.world.clock import Clock
    from skyherd.world.predators import PredatorSpawner
    from skyherd.world.terrain import (
        BarnConfig,
        FenceLineConfig,
        PaddockConfig,
        Terrain,
        TerrainConfig,
        TroughConfig,
        WaterTankConfig,
    )
    from skyherd.world.weather import WeatherDriver
    from skyherd.world.world import World

    # Terrain — identical to conftest._make_terrain()
    config = TerrainConfig(
        name="train_synthetic",
        bounds_m=(2000.0, 2000.0),
        paddocks=[
            PaddockConfig(
                id="p_main",
                polygon=[(0.0, 0.0), (2000.0, 0.0), (2000.0, 2000.0), (0.0, 2000.0)],
            )
        ],
        water_tanks=[WaterTankConfig(id="wt1", pos=(200.0, 200.0), capacity_l=5000.0)],
        troughs=[TroughConfig(id="trough_a", pos=(200.0, 200.0), paddock="p_main")],
        fence_lines=[
            FenceLineConfig(id="fence_s", segment=[(0.0, 0.0), (2000.0, 0.0)], tag="perimeter")
        ],
        barn=BarnConfig(pos=(1900.0, 1900.0)),
    )
    terrain = Terrain(config)

    cow = Cow(
        id="cow_TRAIN01",
        tag="TRAIN01",
        pos=(300.0, 300.0),
        health_score=0.6,
        lameness_score=0,
        ocular_discharge=ocular_discharge,
        bcs=5.5,
        disease_flags={"pinkeye"} if has_flag else set(),
    )

    rng = random.Random(seed)
    herd = Herd(cows=[cow], rng=rng)
    clock = Clock(sim_start_utc=datetime(2026, 4, 21, 13, 0, tzinfo=UTC))
    weather_driver = WeatherDriver()
    pred_spawner = PredatorSpawner(rng=random.Random(seed + 1))

    return World(
        clock=clock,
        terrain=terrain,
        herd=herd,
        predator_spawner=pred_spawner,
        weather_driver=weather_driver,
    )


# ---------------------------------------------------------------------------
# Dataset generation
# ---------------------------------------------------------------------------


def generate_dataset(
    n_frames: int, seed: int, tmp_dir: Path
) -> tuple[torch.Tensor, torch.Tensor]:
    """Generate up to n_frames synthetic (crop, label) pairs.

    Sweeps ocular_discharge values including boundary-jitter values to ensure
    all four severity classes are well-represented.

    Returns
    -------
    (X, y) where X has shape (N, 3, 224, 224) and y has shape (N,).
    """
    from skyherd.vision.renderer import render_trough_frame

    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Build the sweep: (discharge, has_pinkeye_flag, label)
    # Cycle through flag=True/False for each discharge value
    samples: list[tuple[float, bool]] = []
    for d in _DISCHARGE_SWEEP:
        samples.append((d, False))
        samples.append((d, True))

    # If n_frames > len(samples), repeat with slight pos variation via seed offset
    sample_cycle: list[tuple[float, bool]] = []
    repetitions = (n_frames // len(samples)) + 1
    for rep in range(repetitions):
        for s in samples:
            sample_cycle.append(s)
    sample_cycle = sample_cycle[:n_frames]

    rng_seq = random.Random(seed)
    X_list: list[torch.Tensor] = []
    y_list: list[int] = []

    for i, (discharge, has_flag) in enumerate(sample_cycle):
        # Small jitter to discharge so repeated rounds aren't identical
        jitter = rng_seq.uniform(-0.02, 0.02) if i >= len(_DISCHARGE_SWEEP) * 2 else 0.0
        d_val = float(np.clip(discharge + jitter, 0.0, 1.0))
        label = label_for_cow(d_val, has_flag)

        frame_seed = seed + i
        world = _build_world(d_val, has_flag, frame_seed)

        frame_path = tmp_dir / f"frame_{i:05d}.png"
        render_trough_frame(world, "trough_a", out_path=frame_path)

        img_arr = np.array(Image.open(frame_path).convert("RGB"))

        # Extract cow from world to get position
        cow = world.herd.cows[0]
        crop_arr = eye_crop(img_arr, cow.pos, (2000.0, 2000.0), tilt=0)

        # Guard: if crop is too small (edge clamp), resize from full frame region
        if crop_arr.size == 0 or crop_arr.shape[0] < 4 or crop_arr.shape[1] < 4:
            crop_arr = img_arr[:48, :48]  # fallback — top-left corner

        crop_img = Image.fromarray(crop_arr.astype(np.uint8))
        tensor = _PREPROCESS(crop_img)  # (3, 224, 224)
        X_list.append(tensor)
        y_list.append(label)

        if (i + 1) % 50 == 0:
            print(f"  Generated {i + 1}/{len(sample_cycle)} frames ...", flush=True)

    return torch.stack(X_list), torch.tensor(y_list, dtype=torch.long)


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------


def smoke_test(model: nn.Module, tmp_dir: Path) -> None:
    """Verify that the trained model classifies correctly before saving.

    - Positive frame (discharge=0.85, flag=True) must yield argmax in {2, 3}.
    - Negative frame (discharge=0.0, flag=False) must yield argmax == 0.

    Raises RuntimeError on mismatch.
    """
    from skyherd.vision.renderer import render_trough_frame

    model.eval()

    def _classify_world(discharge: float, has_flag: bool, frame_name: str) -> int:
        world = _build_world(discharge, has_flag, seed=999)
        frame_path = tmp_dir / f"smoke_{frame_name}.png"
        render_trough_frame(world, "trough_a", out_path=frame_path)
        img_arr = np.array(Image.open(frame_path).convert("RGB"))
        cow = world.herd.cows[0]
        crop_arr = eye_crop(img_arr, cow.pos, (2000.0, 2000.0), tilt=0)
        if crop_arr.size == 0 or crop_arr.shape[0] < 4 or crop_arr.shape[1] < 4:
            crop_arr = img_arr[:48, :48]
        crop_img = Image.fromarray(crop_arr.astype(np.uint8))
        tensor = _PREPROCESS(crop_img).unsqueeze(0)  # (1, 3, 224, 224)
        with torch.no_grad():
            logits = model(tensor)
        return int(logits.argmax(dim=1).item())

    pos_pred = _classify_world(0.85, True, "positive")
    neg_pred = _classify_world(0.0, False, "negative")

    print(f"  Smoke test: positive_pred={pos_pred} (want {{2,3}}), negative_pred={neg_pred} (want 0)")

    if pos_pred not in {2, 3}:
        raise RuntimeError(
            f"Smoke test FAILED: positive frame predicted class {pos_pred}, expected {{2, 3}}. "
            f"Negative frame predicted class {neg_pred}. Weights NOT saved."
        )
    if neg_pred != 0:
        raise RuntimeError(
            f"Smoke test FAILED: negative frame predicted class {neg_pred}, expected 0. "
            f"Positive frame predicted class {pos_pred}. Weights NOT saved."
        )

    print("  Smoke test PASSED.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point: parse args, train, smoke-test, save weights."""
    parser = argparse.ArgumentParser(
        description=(
            "Train the pinkeye MobileNetV3-Small pixel classifier on synthetic frames. "
            "Saves weights to src/skyherd/vision/_models/pinkeye_mbv3s.pth."
        )
    )
    parser.add_argument("--frames", type=int, default=500, help="Number of synthetic frames")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for determinism")
    parser.add_argument("--epochs", type=int, default=10, help="Training epochs")
    parser.add_argument(
        "--tmp-dir",
        type=Path,
        default=None,
        help="Temp directory for rendered frames (default: REPO_ROOT/runtime/train_tmp)",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Determinism block — must be first
    # ------------------------------------------------------------------
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(mode=True, warn_only=True)

    tmp_dir = args.tmp_dir or (REPO_ROOT / "runtime" / "train_tmp")
    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print(f"[train] seed={args.seed}, frames={args.frames}, epochs={args.epochs}")
    print(f"[train] tmp_dir={tmp_dir}")
    print(f"[train] weights will be saved to: {WEIGHTS_PATH}")
    print()

    # ------------------------------------------------------------------
    # Dataset
    # ------------------------------------------------------------------
    print("[train] Generating dataset ...")
    X, y = generate_dataset(args.frames, args.seed, tmp_dir)
    print(f"[train] Dataset shape: X={X.shape}, y={y.shape}, classes={y.unique().tolist()}")
    print()

    # 80/20 train/val split (seeded)
    n_total = len(X)
    n_train = int(n_total * 0.8)
    g = torch.Generator().manual_seed(args.seed)
    perm = torch.randperm(n_total, generator=g)
    train_idx = perm[:n_train]
    val_idx = perm[n_train:]

    train_ds = TensorDataset(X[train_idx], y[train_idx])
    val_ds = TensorDataset(X[val_idx], y[val_idx])
    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True, generator=g)
    val_loader = DataLoader(val_ds, batch_size=32, shuffle=False)

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------
    print("[train] Loading MobileNetV3-Small with ImageNet V1 weights ...")
    model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    # Freeze backbone
    for param in model.features.parameters():
        param.requires_grad = False
    # Replace head
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, 4)
    print(f"[train] Trainable params: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")
    print()

    # ------------------------------------------------------------------
    # Training loop
    # ------------------------------------------------------------------
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.classifier.parameters(), lr=1e-3)

    best_val_acc = 0.0
    best_state_dict = None

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        n_batches = 0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            logits = model(X_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            n_batches += 1
        train_loss /= max(n_batches, 1)

        # Validation
        model.eval()
        n_correct = 0
        n_val = 0
        with torch.no_grad():
            for X_val, y_val in val_loader:
                preds = model(X_val).argmax(dim=1)
                n_correct += (preds == y_val).sum().item()
                n_val += len(y_val)
        val_acc = n_correct / max(n_val, 1)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state_dict = {k: v.clone() for k, v in model.state_dict().items()}

        print(f"  Epoch {epoch:02d}/{args.epochs} — train_loss={train_loss:.4f}, val_acc={val_acc:.4f}")

    print(f"\n[train] Best val_acc: {best_val_acc:.4f}")

    if best_val_acc < 0.70:
        print(
            f"ERROR: val_acc={best_val_acc:.4f} is below the 0.70 minimum threshold.",
            file=sys.stderr,
        )
        print("Weights NOT saved. Consider increasing --epochs or --frames.", file=sys.stderr)
        sys.exit(1)

    # Restore best weights
    assert best_state_dict is not None
    model.load_state_dict(best_state_dict)
    model.eval()

    # ------------------------------------------------------------------
    # Smoke test
    # ------------------------------------------------------------------
    print("\n[train] Running smoke test ...")
    smoke_test(model, tmp_dir)

    # ------------------------------------------------------------------
    # Save weights
    # ------------------------------------------------------------------
    WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), str(WEIGHTS_PATH))

    # SHA-256 + filesize
    raw_bytes = WEIGHTS_PATH.read_bytes()
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    size_bytes = len(raw_bytes)
    size_mb = size_bytes / (1024 * 1024)

    print(f"\n[train] Weights saved to: {WEIGHTS_PATH}")
    print(f"[train] SHA-256 : {sha256}")
    print(f"[train] Size    : {size_bytes} bytes ({size_mb:.2f} MB)")

    if size_mb > 20.0:
        print(
            f"WARNING: weights file is {size_mb:.2f} MB, exceeding the 20 MB soft cap.",
            file=sys.stderr,
        )

    print("\n[train] Done. Wave 3 can now load the weights via:")
    print("  torch.load('src/skyherd/vision/_models/pinkeye_mbv3s.pth', weights_only=True)")


if __name__ == "__main__":
    main()
