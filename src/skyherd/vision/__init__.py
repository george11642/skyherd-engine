"""SkyHerd vision layer — synthetic frame rendering and disease-detection heads."""

from skyherd.vision.pipeline import ClassifyPipeline, PipelineResult
from skyherd.vision.registry import HEADS, classify
from skyherd.vision.renderer import annotate_frame, render_thermal_frame, render_trough_frame
from skyherd.vision.result import DetectionResult

__all__ = [
    "render_trough_frame",
    "render_thermal_frame",
    "annotate_frame",
    "classify",
    "HEADS",
    "DetectionResult",
    "ClassifyPipeline",
    "PipelineResult",
]
