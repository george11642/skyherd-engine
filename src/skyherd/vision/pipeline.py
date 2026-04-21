"""ClassifyPipeline — end-to-end world-snapshot → annotated frame + detections."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skyherd.vision.registry import classify
from skyherd.vision.renderer import annotate_frame, render_trough_frame
from skyherd.vision.result import DetectionResult
from skyherd.world.world import World


@dataclass
class PipelineResult:
    """Output of a single :class:`ClassifyPipeline` run."""

    annotated_frame_path: Path
    detections: list[DetectionResult] = field(default_factory=list)

    @property
    def detection_count(self) -> int:
        return len(self.detections)


class ClassifyPipeline:
    """Given a World and a trough_id, enumerates cows in frame and classifies each.

    Usage::

        pipeline = ClassifyPipeline()
        result = pipeline.run(world, trough_id="trough_a")
        print(result.detections)

    This is the entry-point consumed by the HerdHealthWatcher agent in Wave 3.
    """

    def run(
        self,
        world: World,
        trough_id: str,
        frame_meta_override: dict[str, Any] | None = None,
        out_dir: Path | None = None,
    ) -> PipelineResult:
        """Render frame, classify every cow, annotate and return results.

        Parameters
        ----------
        world:
            Live (or replayed) world instance.
        trough_id:
            Which trough view to render.
        frame_meta_override:
            Optional sensor overrides (e.g. ``{"respiration_bpm": 70}``).
            If not provided, defaults are derived from current weather.
        out_dir:
            Directory to write PNGs.  Defaults to a temp directory.

        Returns
        -------
        PipelineResult
            Annotated frame path + all detections across all cows.
        """
        if out_dir is None:
            out_dir = Path(tempfile.mkdtemp())
        else:
            out_dir = Path(out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

        raw_path = out_dir / f"raw_{trough_id}.png"
        render_trough_frame(world, trough_id, out_path=raw_path)

        # Build frame_meta from world weather + any overrides
        weather = world.weather_driver.current
        frame_meta: dict[str, Any] = {
            "trough_id": trough_id,
            "temp_f": weather.temp_f,
        }
        if frame_meta_override:
            frame_meta.update(frame_meta_override)

        # Classify every cow in the herd (all are "in frame" for sim purposes)
        all_detections: list[DetectionResult] = []
        for cow in world.herd.cows:
            cow_results = classify(cow, frame_meta)
            all_detections.extend(cow_results)

        annotated_path = out_dir / f"annotated_{trough_id}.png"
        annotate_frame(raw_path, all_detections, out_path=annotated_path)

        return PipelineResult(
            annotated_frame_path=annotated_path,
            detections=all_detections,
        )
