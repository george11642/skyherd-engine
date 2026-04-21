"""Head registry — instantiates all detection heads and provides classify()."""

from __future__ import annotations

from typing import Any

from skyherd.vision.heads.base import Head
from skyherd.vision.heads.bcs import BCS
from skyherd.vision.heads.brd import BRD
from skyherd.vision.heads.foot_rot import FootRot
from skyherd.vision.heads.heat_stress import HeatStress
from skyherd.vision.heads.lsd import LSD
from skyherd.vision.heads.pinkeye import Pinkeye
from skyherd.vision.heads.screwworm import Screwworm
from skyherd.vision.result import DetectionResult
from skyherd.world.cattle import Cow

HEADS: list[Head] = [
    Pinkeye(),
    Screwworm(),
    FootRot(),
    BRD(),
    LSD(),
    HeatStress(),
    BCS(),
]


def classify(cow: Cow, frame_meta: dict[str, Any]) -> list[DetectionResult]:
    """Run all detection heads against *cow* and return non-None results.

    Parameters
    ----------
    cow:
        Current cow state from the world simulation.
    frame_meta:
        Ambient sensor data (temp_f, respiration_bpm, trough_id, etc.).

    Returns
    -------
    list[DetectionResult]
        All detections for this cow across all heads.  Empty list = healthy.
    """
    results: list[DetectionResult] = []
    for head in HEADS:
        result = head.classify(cow, frame_meta)
        if result is not None:
            results.append(result)
    return results
