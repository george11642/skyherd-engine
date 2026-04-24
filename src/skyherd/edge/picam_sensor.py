"""PiCamSensor — Pi-side trough camera with pinkeye pixel classifier.

Differs from :class:`~skyherd.edge.watcher.EdgeWatcher` in that it focuses on
per-cow disease classification (MobileNetV3-Small from
``skyherd.vision.heads.pinkeye``) rather than broad animal detection.  The two
coexist — EdgeWatcher is the production watchdog, PiCamSensor is the
pinkeye-focused demo driver used during field trials and hackathon demos.

On the Raspberry Pi the frame source is ``picamera2``; on a dev machine it
cycles a bundled PNG fixture directory.  Both paths emit the canonical
``trough_cam.reading`` schema matching
:class:`skyherd.sensors.trough_cam.TroughCamSensor`.

Deterministic: when ``seed`` is provided the frame-index sequence is reproducible
across processes (``seed=42`` → identical sequence, always).
"""

from __future__ import annotations

import asyncio
import importlib.resources
import json
import logging
import os
import signal
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_RANCH_ID = "ranch_a"
_DEFAULT_CAM_ID = "picam_0"
_DEFAULT_MQTT_URL = "mqtt://localhost:1883"
_DEFAULT_CAPTURE_INTERVAL_S = 10.0
_FRAME_DIR = Path("runtime/picam_frames")
_TOPIC_PREFIX = "trough_cam"

# Severity labels mirror skyherd.vision.heads.pinkeye._CLASS_TO_SEVERITY so
# imports are decoupled from torch/torchvision in contexts where the pinkeye
# model weights are absent.
_CLASS_TO_SEVERITY: tuple[str | None, ...] = (None, "watch", "log", "escalate")


def _canonical_json(payload: dict[str, Any]) -> str:
    """Deterministic JSON matching the EdgeWatcher wire format."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _discover_sample_frames() -> list[Path]:
    """Return the bundled PiCamSensor sample frames in sorted order.

    Falls back to an empty list if the fixture package is unavailable (e.g.
    custom install) — callers must handle the empty case.
    """
    try:
        ref = importlib.resources.files("skyherd.edge.fixtures.picam")
        with importlib.resources.as_file(ref) as fixture_dir:
            return sorted(Path(fixture_dir).glob("frame_*.png"))
    except (ModuleNotFoundError, FileNotFoundError) as exc:
        logger.warning("PiCamSensor fixture frames unavailable (%s)", exc)
        return []


# ---------------------------------------------------------------------------
# Pinkeye classification dispatch
# ---------------------------------------------------------------------------


def _default_classifier(frame: np.ndarray) -> dict[str, Any]:
    """Run MobileNetV3-Small pinkeye head on *frame*, return severity dict.

    Returns a well-shaped result even when the model is unavailable — the
    fallback severity is ``None`` (no detection) with confidence 0.
    """
    try:
        import torch

        from skyherd.vision.heads.pinkeye import _get_model
        from skyherd.vision.preprocess import array_to_tensor
    except Exception as exc:  # noqa: BLE001
        logger.warning("pinkeye classifier unavailable (%s)", exc)
        return {"severity": None, "confidence": 0.0, "class_idx": 0}

    model = _get_model()
    if model is None:
        return {"severity": None, "confidence": 0.0, "class_idx": 0}

    try:
        # Crop the eye region out of a synthetic cow head — use the centre-left
        # quadrant since that's where _render_frame places the eye.
        h, w = frame.shape[:2]
        eye_x0 = int(w * 0.15)
        eye_y0 = int(h * 0.35)
        eye_x1 = int(w * 0.35)
        eye_y1 = int(h * 0.55)
        crop = frame[eye_y0:eye_y1, eye_x0:eye_x1]
        if crop.size == 0:
            crop = frame
        tensor = array_to_tensor(crop).unsqueeze(0)
        with torch.no_grad():
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1)[0]
            idx = int(probs.argmax().item())
            conf = float(probs[idx].item())
    except Exception as exc:  # noqa: BLE001
        logger.warning("pinkeye inference failed (%s)", exc)
        return {"severity": None, "confidence": 0.0, "class_idx": 0}

    severity = _CLASS_TO_SEVERITY[idx] if 0 <= idx < len(_CLASS_TO_SEVERITY) else None
    return {
        "severity": severity,
        "confidence": round(conf, 3),
        "class_idx": idx,
    }


# ---------------------------------------------------------------------------
# PiCamSensor
# ---------------------------------------------------------------------------


class PiCamSensor:
    """Captures frames, classifies pinkeye, publishes trough_cam payloads.

    On the Pi: uses ``picamera2.Picamera2`` for real frame capture.
    On dev machines: cycles through bundled sample frames (deterministic).

    Parameters
    ----------
    ranch_id:
        Ranch identifier (topic prefix).
    cam_id:
        Camera identifier — also used as ``trough_id`` + payload entity.
    mqtt_url:
        Broker URL.
    capture_interval_s:
        Seconds between captures.
    sample_dir:
        Override the dev-mode fixture directory (useful for tests).
    seed:
        Deterministic frame-order seed.  When set, ``seed=42`` → identical
        frame sequence across processes.
    classifier:
        Test injection: callable ``(frame: np.ndarray) -> {severity, confidence,
        class_idx}`` replacing the default pinkeye head.
    mqtt_publish:
        Test injection: async callable ``(topic, raw_bytes) -> None`` replacing
        the default aiomqtt publish.  When unset the sensor tries aiomqtt
        best-effort and silently skips on connection failure.
    """

    def __init__(
        self,
        ranch_id: str | None = None,
        cam_id: str | None = None,
        mqtt_url: str | None = None,
        capture_interval_s: float | None = None,
        sample_dir: Path | None = None,
        seed: int | None = None,
        classifier: Callable[[np.ndarray], dict[str, Any]] | None = None,
        mqtt_publish: Callable[[str, bytes], Awaitable[None]] | None = None,
    ) -> None:
        self._ranch_id = ranch_id or os.environ.get("RANCH_ID", _DEFAULT_RANCH_ID)
        self._cam_id = cam_id or os.environ.get("EDGE_ID", _DEFAULT_CAM_ID)
        self._mqtt_url = mqtt_url or os.environ.get("MQTT_URL", _DEFAULT_MQTT_URL)
        self._capture_interval_s = capture_interval_s or float(
            os.environ.get("EDGE_CAPTURE_INTERVAL_S", str(_DEFAULT_CAPTURE_INTERVAL_S))
        )
        self._seed = seed
        self._tick_count = 0
        self._running = False
        self._published: list[dict[str, Any]] = []
        self._picam: Any = None
        self._pi_unavailable_logged = False
        self._classifier = classifier or _default_classifier
        self._mqtt_publish = mqtt_publish
        self._topic = f"skyherd/{self._ranch_id}/{_TOPIC_PREFIX}/{self._cam_id}"

        # Dev-mode sample frame source
        if sample_dir is not None:
            self._sample_frames: list[Path] = sorted(Path(sample_dir).glob("frame_*.png"))
        else:
            self._sample_frames = _discover_sample_frames()

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------

    def _capture(self) -> np.ndarray:
        """Return one RGB frame as (H, W, 3) uint8."""
        pi_frame = self._try_pi_capture()
        if pi_frame is not None:
            return pi_frame
        return self._sample_capture()

    def _try_pi_capture(self) -> np.ndarray | None:
        """Return a Pi frame if picamera2 is available; else None."""
        try:
            from picamera2 import Picamera2  # type: ignore[import-untyped,import-not-found]
        except ImportError:
            if not self._pi_unavailable_logged:
                logger.info("picamera2 unavailable — using sample-loop fixture frames")
                self._pi_unavailable_logged = True
            return None

        if self._picam is None:
            self._picam = Picamera2()
            cfg = self._picam.create_still_configuration(
                main={"size": (640, 480), "format": "RGB888"}
            )
            self._picam.configure(cfg)
            self._picam.start()
            logger.info("Picamera2 started for PiCamSensor")
        frame: np.ndarray = self._picam.capture_array()
        return frame

    def _sample_capture(self) -> np.ndarray:
        """Return one fixture frame as uint8 RGB array."""
        if not self._sample_frames:
            # Graceful degradation: return a solid green synthetic frame.
            return np.full((480, 640, 3), [34, 85, 34], dtype=np.uint8)

        idx = self._seeded_index()
        path = self._sample_frames[idx]
        from PIL import Image

        with Image.open(str(path)) as img:
            return np.array(img.convert("RGB"), dtype=np.uint8)

    def _seeded_index(self) -> int:
        """Deterministic cycling over sample frames.

        When ``seed`` is None this is simply the tick count modulo the frame
        count.  When ``seed`` is set, a Knuth hash is applied so different seeds
        produce clearly-distinct sequences in short replays.
        """
        n = len(self._sample_frames) or 1
        if self._seed is None:
            return self._tick_count % n
        # Knuth multiplicative hash over (seed, tick_count).
        return (self._seed * 2654435761 + self._tick_count) % n

    # ------------------------------------------------------------------
    # Classify + build payload
    # ------------------------------------------------------------------

    def _classify(self, frame: np.ndarray) -> dict[str, Any]:
        try:
            result = self._classifier(frame)
        except Exception as exc:  # noqa: BLE001
            logger.warning("classifier raised (%s) — emitting null result", exc)
            result = {"severity": None, "confidence": 0.0, "class_idx": 0}
        # Normalise: ensure required keys present
        severity = result.get("severity")
        confidence = float(result.get("confidence", 0.0))
        class_idx = int(result.get("class_idx", 0))
        return {
            "severity": severity,
            "confidence": round(confidence, 3),
            "class_idx": class_idx,
        }

    def _build_payload(
        self, frame: np.ndarray, pinkeye_result: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a canonical trough_cam.reading payload."""
        ts = time.time()
        has_detection = pinkeye_result["severity"] is not None
        cows_present = 1 if has_detection else 0
        ids = [f"cow_{self._cam_id}"] if has_detection else []
        frame_uri = str(_FRAME_DIR / f"{self._cam_id}_{int(ts)}.jpg")

        return {
            "ts": ts,
            "kind": "trough_cam.reading",
            "ranch": self._ranch_id,
            "entity": self._cam_id,
            "trough_id": self._cam_id,
            "cows_present": cows_present,
            "ids": ids,
            "frame_uri": frame_uri,
            # Edge extras (ignored gracefully by sim consumers)
            "source": "picam",
            "pinkeye_result": pinkeye_result,
            "seed": self._seed,
            "tick": self._tick_count,
        }

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    async def _publish(self, payload: dict[str, Any]) -> None:
        """Publish *payload* to MQTT; best-effort (swallow publish errors)."""
        raw = _canonical_json(payload).encode()
        self._published.append(payload)

        if self._mqtt_publish is not None:
            try:
                await self._mqtt_publish(self._topic, raw)
            except Exception as exc:  # noqa: BLE001
                logger.debug("injected mqtt_publish raised (%s) — swallowed", exc)
            return

        # Default: best-effort aiomqtt publish
        try:
            import aiomqtt  # type: ignore[import-untyped]

            host, _, port_str = self._mqtt_url.split("://", 1)[-1].rpartition(":")
            try:
                port = int(port_str)
            except ValueError:
                port = 1883
            host = host or "localhost"
            async with aiomqtt.Client(hostname=host, port=port, timeout=2.0) as client:
                await client.publish(self._topic, payload=raw, qos=0)
        except Exception as exc:  # noqa: BLE001
            logger.debug("PiCamSensor MQTT publish best-effort failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_once(self) -> dict[str, Any]:
        """Capture one frame, classify, publish, return payload dict."""
        frame = self._capture()
        pinkeye_result = self._classify(frame)
        payload = self._build_payload(frame, pinkeye_result)
        await self._publish(payload)
        self._tick_count += 1
        return payload

    async def run(self) -> None:
        """Main loop — captures every ``capture_interval_s`` until stopped."""
        self._running = True
        self._install_signal_handlers()
        logger.info(
            "PiCamSensor started — ranch=%s cam=%s topic=%s interval=%.1fs seed=%s",
            self._ranch_id,
            self._cam_id,
            self._topic,
            self._capture_interval_s,
            self._seed,
        )
        try:
            while self._running:
                try:
                    await self.run_once()
                except Exception as exc:  # noqa: BLE001
                    logger.error("PiCamSensor tick failed: %s", exc)
                await asyncio.sleep(self._capture_interval_s)
        except asyncio.CancelledError:
            logger.info("PiCamSensor cancelled — shutting down")
        finally:
            self.close()

    def stop(self) -> None:
        """Request graceful shutdown from a signal handler."""
        self._running = False

    def close(self) -> None:
        """Release the Pi camera handle if allocated.  Idempotent."""
        if self._picam is not None:
            try:
                self._picam.stop()
                self._picam.close()
            except Exception:  # noqa: BLE001
                pass
            self._picam = None

    def _install_signal_handlers(self) -> None:
        """Install SIGINT / SIGTERM → stop(), tolerating non-main-thread."""
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGINT, self.stop)
            loop.add_signal_handler(signal.SIGTERM, self.stop)
        except (NotImplementedError, RuntimeError) as exc:
            logger.debug("signal handler unavailable on this platform: %s", exc)
