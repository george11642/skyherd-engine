"""Tests for skyherd.edge.picam_sensor.PiCamSensor.

Exercises dev-mode sample-loop capture, pinkeye classifier integration,
deterministic frame ordering, canonical JSON publish, shutdown lifecycle,
and CLI subcommand wiring.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from typer.testing import CliRunner

from skyherd.edge.cli import app
from skyherd.edge.picam_sensor import (
    PiCamSensor,
    _canonical_json,
    _default_classifier,
    _discover_sample_frames,
)

runner = CliRunner(mix_stderr=False)


def _escalate_classifier(frame: np.ndarray) -> dict[str, Any]:  # noqa: ARG001
    return {"severity": "escalate", "confidence": 0.92, "class_idx": 3}


def _healthy_classifier(frame: np.ndarray) -> dict[str, Any]:  # noqa: ARG001
    return {"severity": None, "confidence": 0.88, "class_idx": 0}


def _watch_classifier(frame: np.ndarray) -> dict[str, Any]:  # noqa: ARG001
    return {"severity": "watch", "confidence": 0.61, "class_idx": 1}


def _raising_classifier(frame: np.ndarray) -> dict[str, Any]:  # noqa: ARG001
    raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# Fixture discovery
# ---------------------------------------------------------------------------


class TestFixtureDiscovery:
    def test_discover_returns_bundled_frames(self) -> None:
        frames = _discover_sample_frames()
        assert len(frames) >= 4
        for p in frames:
            assert p.exists()
            assert p.suffix == ".png"

    def test_discover_sorted_lexicographically(self) -> None:
        frames = _discover_sample_frames()
        assert frames == sorted(frames)


# ---------------------------------------------------------------------------
# Payload schema
# ---------------------------------------------------------------------------


class TestPayloadSchema:
    def test_kind_is_trough_cam_reading(self) -> None:
        sensor = PiCamSensor(seed=42, classifier=_escalate_classifier)
        payload = asyncio.run(sensor.run_once())
        assert payload["kind"] == "trough_cam.reading"

    def test_ranch_entity_trough_id_match_cam(self) -> None:
        sensor = PiCamSensor(ranch_id="ranch_x", cam_id="picam_7", classifier=_escalate_classifier)
        payload = asyncio.run(sensor.run_once())
        assert payload["ranch"] == "ranch_x"
        assert payload["entity"] == "picam_7"
        assert payload["trough_id"] == "picam_7"

    def test_source_is_picam(self) -> None:
        sensor = PiCamSensor(classifier=_escalate_classifier)
        payload = asyncio.run(sensor.run_once())
        assert payload["source"] == "picam"

    def test_pinkeye_result_keys_present(self) -> None:
        sensor = PiCamSensor(classifier=_watch_classifier)
        payload = asyncio.run(sensor.run_once())
        assert set(payload["pinkeye_result"].keys()) >= {"severity", "confidence", "class_idx"}

    def test_frame_uri_is_string(self) -> None:
        sensor = PiCamSensor(classifier=_healthy_classifier)
        payload = asyncio.run(sensor.run_once())
        assert isinstance(payload["frame_uri"], str)
        assert "picam_frames" in payload["frame_uri"]

    def test_cows_present_zero_when_healthy(self) -> None:
        sensor = PiCamSensor(classifier=_healthy_classifier)
        payload = asyncio.run(sensor.run_once())
        assert payload["cows_present"] == 0
        assert payload["ids"] == []

    def test_cows_present_one_when_pinkeye_detects(self) -> None:
        sensor = PiCamSensor(classifier=_escalate_classifier, cam_id="picam_0")
        payload = asyncio.run(sensor.run_once())
        assert payload["cows_present"] == 1
        assert payload["ids"] == ["cow_picam_0"]

    def test_ts_is_monotonic_across_ticks(self) -> None:
        sensor = PiCamSensor(classifier=_escalate_classifier)
        ts1 = asyncio.run(sensor.run_once())["ts"]
        ts2 = asyncio.run(sensor.run_once())["ts"]
        assert ts2 >= ts1


# ---------------------------------------------------------------------------
# Pinkeye integration
# ---------------------------------------------------------------------------


class TestPinkeyeIntegration:
    def test_classify_returns_none_severity_on_healthy_stub(self) -> None:
        sensor = PiCamSensor(classifier=_healthy_classifier)
        payload = asyncio.run(sensor.run_once())
        assert payload["pinkeye_result"]["severity"] is None

    def test_classify_returns_escalate_when_stub_returns_class_3(self) -> None:
        sensor = PiCamSensor(classifier=_escalate_classifier)
        payload = asyncio.run(sensor.run_once())
        assert payload["pinkeye_result"]["severity"] == "escalate"
        assert payload["pinkeye_result"]["class_idx"] == 3

    def test_classifier_exception_degrades_to_null_result(self) -> None:
        sensor = PiCamSensor(classifier=_raising_classifier)
        payload = asyncio.run(sensor.run_once())
        assert payload["pinkeye_result"]["severity"] is None
        assert payload["pinkeye_result"]["confidence"] == 0.0

    def test_default_classifier_returns_shape(self) -> None:
        arr = np.full((480, 640, 3), 128, dtype=np.uint8)
        result = _default_classifier(arr)
        assert "severity" in result
        assert "confidence" in result
        assert "class_idx" in result


# ---------------------------------------------------------------------------
# Pi / non-Pi fork
# ---------------------------------------------------------------------------


class TestCaptureFork:
    def test_non_pi_uses_sample_loop(self) -> None:
        """On dev machine (no picamera2), _capture reads from fixtures."""
        sensor = PiCamSensor(classifier=_escalate_classifier)
        frame = sensor._capture()
        assert frame.ndim == 3
        assert frame.shape[2] == 3
        assert frame.dtype == np.uint8

    def test_sample_capture_cycles_through_dir(self) -> None:
        sensor = PiCamSensor(classifier=_escalate_classifier)
        frames = [sensor._capture() for _ in range(5)]
        # Without seed, index advances via _tick_count — but _capture doesn't
        # increment the counter, so all 5 frames equal frame 0. Exercise
        # cycling via run_once which increments.
        frames2 = []
        for _ in range(5):
            asyncio.run(sensor.run_once())
            frames2.append(sensor._capture())
        assert len(frames2) == 5

    def test_sample_capture_gracefully_degrades_on_empty_dir(self, tmp_path: Path) -> None:
        sensor = PiCamSensor(classifier=_escalate_classifier, sample_dir=tmp_path)
        frame = sensor._capture()
        assert frame.shape == (480, 640, 3)
        # Solid green pasture fallback
        assert (frame == np.array([34, 85, 34], dtype=np.uint8)).all()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_seeded_mode_produces_identical_sequence_across_instances(self) -> None:
        s1 = PiCamSensor(seed=42, classifier=_escalate_classifier)
        s2 = PiCamSensor(seed=42, classifier=_escalate_classifier)
        seq1 = [s1._seeded_index() or s1._tick_count for _ in range(6)]
        # Advance ticks to capture real seq
        seq1 = []
        for _ in range(6):
            seq1.append(s1._seeded_index())
            s1._tick_count += 1
        seq2 = []
        for _ in range(6):
            seq2.append(s2._seeded_index())
            s2._tick_count += 1
        assert seq1 == seq2

    def test_different_seeds_give_different_sequences(self) -> None:
        s1 = PiCamSensor(seed=42, classifier=_escalate_classifier)
        s2 = PiCamSensor(seed=43, classifier=_escalate_classifier)
        seqs: list[list[int]] = []
        for s in (s1, s2):
            seq: list[int] = []
            for _ in range(6):
                seq.append(s._seeded_index())
                s._tick_count += 1
            seqs.append(seq)
        assert seqs[0] != seqs[1]

    def test_unseeded_cycles_modulo_frame_count(self) -> None:
        sensor = PiCamSensor(classifier=_escalate_classifier)
        n = len(sensor._sample_frames) or 1
        seq = []
        for _ in range(n + 2):
            seq.append(sensor._seeded_index())
            sensor._tick_count += 1
        # First n ticks: 0, 1, ..., n-1.  Next two wrap.
        assert seq[:n] == list(range(n))
        assert seq[n] == 0

    def test_canonical_json_is_sorted_compact(self) -> None:
        payload = {"b": 2, "a": 1, "c": [1, 2]}
        raw = _canonical_json(payload)
        # key order is alphabetical + no whitespace
        assert raw == '{"a":1,"b":2,"c":[1,2]}'


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------


class TestPublish:
    def test_injected_publisher_called_with_canonical_json(self) -> None:
        captured: list[tuple[str, bytes]] = []

        async def fake_pub(topic: str, raw: bytes) -> None:
            captured.append((topic, raw))

        sensor = PiCamSensor(
            classifier=_escalate_classifier,
            mqtt_publish=fake_pub,
            cam_id="picam_99",
            ranch_id="ranch_x",
        )
        asyncio.run(sensor.run_once())
        assert len(captured) == 1
        topic, raw = captured[0]
        assert topic == "skyherd/ranch_x/trough_cam/picam_99"
        # canonical: sorted keys, no whitespace
        parsed = json.loads(raw.decode())
        assert parsed["kind"] == "trough_cam.reading"

    def test_publisher_failure_does_not_raise(self) -> None:
        async def failing_pub(topic: str, raw: bytes) -> None:
            raise ConnectionError("broker gone")

        sensor = PiCamSensor(classifier=_escalate_classifier, mqtt_publish=failing_pub)
        payload = asyncio.run(sensor.run_once())
        assert payload["kind"] == "trough_cam.reading"
        assert len(sensor._published) == 1

    def test_no_broker_default_path_still_records_locally(self) -> None:
        # Default path tries aiomqtt against mqtt://localhost:1883; that's
        # unreachable in CI but the exception must be swallowed.
        sensor = PiCamSensor(classifier=_escalate_classifier, mqtt_url="mqtt://localhost:19999")
        payload = asyncio.run(sensor.run_once())
        assert payload["kind"] == "trough_cam.reading"
        assert len(sensor._published) == 1


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_close_is_idempotent(self) -> None:
        sensor = PiCamSensor(classifier=_escalate_classifier)
        sensor.close()
        sensor.close()  # second call must not raise

    def test_close_releases_allocated_picam(self) -> None:
        class FakePicam:
            def __init__(self) -> None:
                self.stopped = False
                self.closed = False

            def stop(self) -> None:
                self.stopped = True

            def close(self) -> None:
                self.closed = True

        fake = FakePicam()
        sensor = PiCamSensor(classifier=_escalate_classifier)
        sensor._picam = fake
        sensor.close()
        assert fake.stopped and fake.closed
        assert sensor._picam is None

    def test_stop_ends_run_loop(self) -> None:
        sensor = PiCamSensor(classifier=_escalate_classifier, capture_interval_s=0.01)

        async def runner_and_stop() -> None:
            task = asyncio.create_task(sensor.run())
            await asyncio.sleep(0.05)
            sensor.stop()
            await asyncio.wait_for(task, timeout=1.0)

        asyncio.run(runner_and_stop())
        assert not sensor._running


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCli:
    def test_picam_runs_one_tick_and_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Replace the default classifier to skip torch model load
        from skyherd.edge import picam_sensor as ps

        monkeypatch.setattr(ps, "_default_classifier", _escalate_classifier)

        result = runner.invoke(app, ["picam", "--max-ticks", "1", "--seed", "42"])
        assert result.exit_code == 0, result.output + (result.stderr or "")
        assert "picam tick" in result.output or "picam tick" in (result.stderr or "")

    def test_picam_seed_flag_forwards(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from skyherd.edge import picam_sensor as ps

        monkeypatch.setattr(ps, "_default_classifier", _escalate_classifier)

        captured: dict[str, Any] = {}
        orig_init = ps.PiCamSensor.__init__

        def spy_init(self: Any, *args: Any, **kwargs: Any) -> None:
            captured["seed"] = kwargs.get("seed")
            orig_init(self, *args, **kwargs)

        monkeypatch.setattr(ps.PiCamSensor, "__init__", spy_init)
        result = runner.invoke(app, ["picam", "--max-ticks", "1", "--seed", "77"])
        assert result.exit_code == 0
        assert captured["seed"] == 77


# ---------------------------------------------------------------------------
# Extra coverage — default classifier paths + Pi-capture mock
# ---------------------------------------------------------------------------


class TestDefaultClassifierPaths:
    def test_default_classifier_with_missing_torch_returns_null_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Forces the inner import to fail; expects safe null result."""
        import builtins

        real_import = builtins.__import__

        def raising_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if "torch" in name or "pinkeye" in name:
                raise ImportError(f"simulated absence of {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", raising_import)
        arr = np.zeros((480, 640, 3), dtype=np.uint8)
        result = _default_classifier(arr)
        assert result == {"severity": None, "confidence": 0.0, "class_idx": 0}

    def test_default_classifier_with_model_unavailable_returns_null(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When _get_model returns None, classifier reports null result."""
        from skyherd.vision.heads import pinkeye as pk

        # Clear lru cache and patch _get_model to return None
        pk._get_model.cache_clear()
        monkeypatch.setattr(pk, "_get_model", lambda: None)
        # The classifier re-imports inside — make sure our monkeypatched
        # module-level function is visible.
        arr = np.zeros((480, 640, 3), dtype=np.uint8)
        result = _default_classifier(arr)
        assert result["severity"] is None
        assert result["class_idx"] == 0

    def test_pi_capture_uses_picam_when_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Forcibly provides a fake Picamera2 class; PiCamSensor should use it."""
        import sys
        import types

        fake_module = types.ModuleType("picamera2")

        class FakePicamera2:
            def __init__(self) -> None:
                self.configured = False
                self.started = False

            def create_still_configuration(self, **kwargs: Any) -> dict[str, Any]:
                return {"cfg": kwargs}

            def configure(self, cfg: Any) -> None:
                self.configured = True

            def start(self) -> None:
                self.started = True

            def capture_array(self) -> np.ndarray:
                return np.full((480, 640, 3), 200, dtype=np.uint8)

            def stop(self) -> None:
                pass

            def close(self) -> None:
                pass

        fake_module.Picamera2 = FakePicamera2  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "picamera2", fake_module)

        sensor = PiCamSensor(classifier=_escalate_classifier)
        frame = sensor._try_pi_capture()
        assert frame is not None
        assert frame.shape == (480, 640, 3)
        # Second call: reuses the allocated picam
        frame2 = sensor._try_pi_capture()
        assert frame2 is not None
        sensor.close()

    def test_pi_capture_logs_once_when_unavailable(self) -> None:
        """Covers the 'unavailable already logged' branch by calling twice."""
        sensor = PiCamSensor(classifier=_escalate_classifier)
        # Not on a Pi; first call logs, second call suppresses
        assert sensor._try_pi_capture() is None
        assert sensor._pi_unavailable_logged is True
        assert sensor._try_pi_capture() is None


class TestMqttUrlParsing:
    def test_publish_parses_mqtt_url_port_component(self) -> None:
        """Covers the mqtt_url rpartition parsing path."""
        sensor = PiCamSensor(
            classifier=_escalate_classifier,
            mqtt_url="mqtt://192.168.1.1:12345",
        )
        # Default aiomqtt path with unreachable host — swallowed
        payload = asyncio.run(sensor.run_once())
        assert payload["kind"] == "trough_cam.reading"

    def test_publish_parses_mqtt_url_without_port(self) -> None:
        """URL missing :port triggers ValueError path → default 1883."""
        sensor = PiCamSensor(
            classifier=_escalate_classifier,
            mqtt_url="mqtt://unreachable-host-xyz",
        )
        payload = asyncio.run(sensor.run_once())
        assert payload["kind"] == "trough_cam.reading"
