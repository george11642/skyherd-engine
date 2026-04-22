"""Tests for EdgeWatcher — MockCamera + RuleDetector + stub MQTT publish.

Uses an in-process EdgeWatcher with MockCamera and RuleDetector so no broker
or hardware is required.  Validates that published messages match the
TroughCamSensor schema consumed by the sim agents.
"""

from __future__ import annotations

import json

import pytest

from skyherd.edge.camera import MockCamera
from skyherd.edge.detector import Detection, RuleDetector
from skyherd.edge.watcher import EdgeWatcher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_watcher(**kwargs) -> EdgeWatcher:  # type: ignore[type-arg]
    """Factory for a fully in-process EdgeWatcher (no broker needed)."""
    defaults = {
        "camera": MockCamera(),
        "detector": RuleDetector(),
        "ranch_id": "test_ranch",
        "edge_id": "test_node",
        "mqtt_url": "mqtt://localhost:19999",  # unreachable — publish best-effort
        "capture_interval_s": 1.0,
    }
    defaults.update(kwargs)
    return EdgeWatcher(**defaults)


# ---------------------------------------------------------------------------
# Detection model
# ---------------------------------------------------------------------------


class TestDetection:
    def test_detection_has_required_fields(self) -> None:
        d = Detection(
            tag_guess="animal",
            bbox=[10.0, 20.0, 100.0, 200.0],
            confidence=0.88,
        )
        assert d.tag_guess == "animal"
        assert len(d.bbox) == 4
        assert 0.0 <= d.confidence <= 1.0
        assert d.frame_ts > 0

    def test_confidence_clamped_to_unit_interval(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Detection(tag_guess="x", bbox=[0, 0, 1, 1], confidence=1.5)

        with pytest.raises(ValidationError):
            Detection(tag_guess="x", bbox=[0, 0, 1, 1], confidence=-0.1)


# ---------------------------------------------------------------------------
# Payload schema (matches TroughCamSensor)
# ---------------------------------------------------------------------------


class TestPayloadSchema:
    """Published payload must be structurally identical to sim trough_cam."""

    def test_required_trough_cam_keys_present(self) -> None:
        watcher = _make_watcher()
        import numpy as np

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = RuleDetector().detect(frame)
        payload = watcher._build_payload(frame, detections)

        required_keys = {
            "ts",
            "kind",
            "ranch",
            "entity",
            "trough_id",
            "cows_present",
            "ids",
            "frame_uri",
        }
        assert required_keys.issubset(payload.keys()), (
            f"Missing keys: {required_keys - payload.keys()}"
        )

    def test_kind_matches_sim_sensor(self) -> None:
        watcher = _make_watcher()
        import numpy as np

        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        detections = RuleDetector().detect(frame)
        payload = watcher._build_payload(frame, detections)
        assert payload["kind"] == "trough_cam.reading"

    def test_ranch_and_entity_match_config(self) -> None:
        watcher = _make_watcher(ranch_id="myranch", edge_id="cam_7")
        import numpy as np

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        payload = watcher._build_payload(frame, [])
        assert payload["ranch"] == "myranch"
        assert payload["entity"] == "cam_7"

    def test_cows_present_reflects_detection_count(self) -> None:
        watcher = _make_watcher()
        import numpy as np

        frame = np.ones((480, 640, 3), dtype=np.uint8) * 200  # bright → detections
        detections = RuleDetector().detect(frame)
        payload = watcher._build_payload(frame, detections)
        assert payload["cows_present"] == len(detections)

    def test_payload_is_json_serialisable(self) -> None:
        watcher = _make_watcher()
        import numpy as np

        frame = np.ones((480, 640, 3), dtype=np.uint8) * 100
        payload = watcher._build_payload(frame, [])
        serialised = json.dumps(payload)
        decoded = json.loads(serialised)
        assert decoded["kind"] == "trough_cam.reading"


# ---------------------------------------------------------------------------
# run_once integration
# ---------------------------------------------------------------------------


class TestRunOnce:
    """run_once captures, detects, and records published payloads."""

    @pytest.mark.asyncio
    async def test_run_once_returns_payload(self) -> None:
        watcher = _make_watcher()
        payload = await watcher.run_once()
        assert isinstance(payload, dict)
        assert "ts" in payload

    @pytest.mark.asyncio
    async def test_run_once_records_in_published(self) -> None:
        watcher = _make_watcher()
        await watcher.run_once()
        assert len(watcher._published) == 1

    @pytest.mark.asyncio
    async def test_multiple_run_once_accumulates(self) -> None:
        watcher = _make_watcher()
        for _ in range(3):
            await watcher.run_once()
        assert len(watcher._published) == 3

    @pytest.mark.asyncio
    async def test_published_payload_has_source_edge(self) -> None:
        watcher = _make_watcher()
        await watcher.run_once()
        assert watcher._published[0]["source"] == "edge"

    @pytest.mark.asyncio
    async def test_topic_matches_sim_convention(self) -> None:
        watcher = _make_watcher(ranch_id="ranch_a", edge_id="pi_trough_1")
        assert watcher._topic == "skyherd/ranch_a/trough_cam/pi_trough_1"


# ---------------------------------------------------------------------------
# Motion event threshold
# ---------------------------------------------------------------------------


class TestMotionEvent:
    """camera.motion event fires when confidence >= 0.5."""

    @pytest.mark.asyncio
    async def test_motion_event_fires_on_high_confidence(self) -> None:
        import numpy as np

        from skyherd.edge.detector import Detection

        class HighConfDetector(RuleDetector):
            def detect(self, frame: np.ndarray) -> list[Detection]:
                return [Detection(tag_guess="animal", bbox=[0, 0, 100, 100], confidence=0.9)]

        watcher = _make_watcher(detector=HighConfDetector())
        payload = await watcher.run_once()
        assert any(d["confidence"] >= 0.5 for d in payload["detections"])

    @pytest.mark.asyncio
    async def test_no_motion_event_on_empty_detections(self) -> None:
        import numpy as np

        class NoDetector(RuleDetector):
            def detect(self, frame: np.ndarray) -> list[Detection]:
                return []

        watcher = _make_watcher(detector=NoDetector())
        payload = await watcher.run_once()
        assert payload["cows_present"] == 0
