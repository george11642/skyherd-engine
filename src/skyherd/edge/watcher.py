"""EdgeWatcher — async capture/detect/publish loop for Pi H1 hardware tier."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import socket
import time
from pathlib import Path

import numpy as np

from skyherd.edge.camera import Camera, get_camera
from skyherd.edge.detector import Detection, Detector, MegaDetectorHead

logger = logging.getLogger(__name__)

_DEFAULT_CAPTURE_INTERVAL_S = 10.0
_DEFAULT_RANCH_ID = "ranch_a"
_DEFAULT_MQTT_URL = "mqtt://localhost:1883"
_MOTION_CONFIDENCE_THRESHOLD = 0.5
_FRAME_DIR = Path("runtime/edge_frames")
_TOPIC_PREFIX = "trough_cam"
_DEFAULT_HEARTBEAT_INTERVAL_S = 30.0
_DEFAULT_HEALTHZ_PORT = 8787
_THERMAL_ZONE_PATH = Path("/sys/class/thermal/thermal_zone0/temp")
_MOCK_CPU_TEMP_C = 45.0  # returned on non-Pi hosts


def _resolve_edge_id() -> str:
    """Return hostname as the default edge node identifier."""
    return socket.gethostname()


def _read_cpu_temp_c() -> float:
    """Read SoC temperature from the Linux thermal zone sysfs entry.

    Returns a mock value on non-Pi hosts where the file is absent.
    Pi 4 throttles above ~80 °C — monitor this field to catch thermal issues.
    """
    try:
        raw = _THERMAL_ZONE_PATH.read_text().strip()
        return round(int(raw) / 1000.0, 1)
    except (OSError, ValueError):
        return _MOCK_CPU_TEMP_C


def _read_mem_pct() -> float:
    """Return percentage of memory currently in use (0–100).

    Reads /proc/meminfo; falls back to 0.0 on systems where it is absent.
    """
    try:
        info: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                info[parts[0].rstrip(":")] = int(parts[1])
        total = info.get("MemTotal", 0)
        available = info.get("MemAvailable", 0)
        if total <= 0:
            return 0.0
        return round((total - available) / total * 100.0, 1)
    except (OSError, ValueError):
        return 0.0


def _make_detector(mode: str) -> Detector:
    """Construct a Detector from the EDGE_DETECTOR_MODE string.

    Supported modes
    ---------------
    rule
        RuleDetector — heuristic brightness check, ~0 ms, no model weights.
    megadetector
        MegaDetectorHead — MegaDetector V6 via PytorchWildlife (~3-5 s on Pi 4 CPU).
    coral
        CoralDetector — MegaDetector via Coral USB Edge TPU (~200 ms).
        Requires ``libedgetpu`` + ``pycoral`` installed on the host.
    """
    from skyherd.edge.detector import RuleDetector

    if mode == "rule":
        logger.info("Detector: RuleDetector (mode=rule)")
        return RuleDetector()
    if mode == "coral":
        try:
            from skyherd.edge.detector import CoralDetector  # type: ignore[attr-defined]

            logger.info("Detector: CoralDetector (mode=coral)")
            return CoralDetector()
        except (ImportError, AttributeError) as exc:
            logger.warning(
                "CoralDetector unavailable (%s) — falling back to MegaDetectorHead", exc
            )
    # megadetector (default) or coral fallback
    logger.info("Detector: MegaDetectorHead (mode=%s)", mode)
    return MegaDetectorHead()


def _parse_mqtt_url(url: str) -> tuple[str, int]:
    """Parse ``mqtt://host:port`` → (host, port).  Defaults to 1883."""
    without_scheme = url.split("://", 1)[-1]
    if ":" in without_scheme:
        host, port_str = without_scheme.rsplit(":", 1)
        try:
            return host, int(port_str)
        except ValueError:
            pass
    return without_scheme, 1883


def _canonical_json(payload: dict) -> str:  # type: ignore[type-arg]
    """Deterministic JSON matching SensorBus wire format."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


class EdgeWatcher:
    """Capture frames, detect animals, publish trough_cam-compatible MQTT payloads.

    Configuration via environment variables (all optional):

    ``RANCH_ID``
        Ranch identifier.  Default: ``ranch_a``.
    ``EDGE_ID``
        Node identifier (appears in topic and payload).  Default: hostname.
    ``MQTT_URL``
        Broker URL.  Default: ``mqtt://localhost:1883``.
    ``EDGE_CAPTURE_INTERVAL_S``
        Seconds between captures.  Default: ``10``.
    ``EDGE_DETECTOR_MODE``
        Detection backend: ``rule`` | ``megadetector`` | ``coral``.  Default: ``megadetector``.
    ``EDGE_HEARTBEAT_INTERVAL_S``
        Seconds between heartbeat publishes.  Default: ``30``.
    ``EDGE_HEALTHZ_PORT``
        Port for the HTTP ``/healthz`` endpoint.  ``0`` disables it.  Default: ``8787``.
    """

    def __init__(
        self,
        camera: Camera | None = None,
        detector: Detector | None = None,
        ranch_id: str | None = None,
        edge_id: str | None = None,
        mqtt_url: str | None = None,
        capture_interval_s: float | None = None,
        heartbeat_interval_s: float | None = None,
        healthz_port: int | None = None,
        detector_mode: str | None = None,
    ) -> None:
        self._ranch_id = ranch_id or os.environ.get("RANCH_ID", _DEFAULT_RANCH_ID)
        self._edge_id = edge_id or os.environ.get("EDGE_ID", _resolve_edge_id())
        self._mqtt_url = mqtt_url or os.environ.get("MQTT_URL", _DEFAULT_MQTT_URL)
        self._capture_interval_s = capture_interval_s or float(
            os.environ.get("EDGE_CAPTURE_INTERVAL_S", str(_DEFAULT_CAPTURE_INTERVAL_S))
        )
        self._heartbeat_interval_s = heartbeat_interval_s or float(
            os.environ.get("EDGE_HEARTBEAT_INTERVAL_S", str(_DEFAULT_HEARTBEAT_INTERVAL_S))
        )
        _healthz_env = int(os.environ.get("EDGE_HEALTHZ_PORT", str(_DEFAULT_HEALTHZ_PORT)))
        self._healthz_port: int = healthz_port if healthz_port is not None else _healthz_env

        # Detector: explicit injection wins; then mode env var; then megadetector default
        if detector is not None:
            self._detector: Detector = detector
        else:
            mode = detector_mode or os.environ.get("EDGE_DETECTOR_MODE", "megadetector")
            self._detector = _make_detector(mode)

        self._camera: Camera = camera if camera is not None else get_camera()

        self._mqtt_host, self._mqtt_port = _parse_mqtt_url(self._mqtt_url)
        self._topic = f"skyherd/{self._ranch_id}/{_TOPIC_PREFIX}/{self._edge_id}"
        self._status_topic = f"skyherd/{self._ranch_id}/edge_status/{self._edge_id}"
        self._running = False
        self._last_detection_ts: float | None = None
        # Published messages list — populated for testing introspection
        self._published: list[dict] = []  # type: ignore[type-arg]
        # Heartbeat payloads list — populated for testing introspection
        self._heartbeats: list[dict] = []  # type: ignore[type-arg]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_once(self) -> dict:  # type: ignore[type-arg]
        """Capture one frame, detect, publish, return payload dict."""
        frame = self._camera.capture()
        detections = self._detector.detect(frame)
        payload = self._build_payload(frame, detections)
        await self._publish(payload)
        self._annotate_and_save(frame, detections, payload["ts"])
        if detections:
            self._last_detection_ts = payload["ts"]
        if any(d["confidence"] >= _MOTION_CONFIDENCE_THRESHOLD for d in payload["detections"]):
            await self._emit_motion_event(payload)
        return payload

    async def run(self) -> None:
        """Main loop: capture every N seconds until SIGINT/SIGTERM."""
        self._running = True
        self._install_signal_handlers()
        logger.info(
            "EdgeWatcher started — ranch=%s edge=%s topic=%s interval=%.1fs heartbeat=%.1fs",
            self._ranch_id,
            self._edge_id,
            self._topic,
            self._capture_interval_s,
            self._heartbeat_interval_s,
        )
        # Start heartbeat and optional healthz concurrently with capture loop
        tasks: list[asyncio.Task] = []  # type: ignore[type-arg]
        try:
            tasks.append(asyncio.create_task(self._heartbeat_loop()))
            if self._healthz_port > 0:
                tasks.append(asyncio.create_task(self._healthz_server()))
            while self._running:
                try:
                    await self.run_once()
                except Exception as exc:  # noqa: BLE001
                    logger.error("EdgeWatcher tick error: %s", exc)
                await asyncio.sleep(self._capture_interval_s)
        except asyncio.CancelledError:
            logger.info("EdgeWatcher cancelled — shutting down")
        finally:
            for task in tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            self._camera.close()
            logger.info("EdgeWatcher stopped")

    def stop(self) -> None:
        """Request graceful shutdown (can be called from signal handlers)."""
        self._running = False

    def heartbeat_payload(self) -> dict:  # type: ignore[type-arg]
        """Build the current heartbeat dict (public for testing)."""
        return {
            "edge_id": self._edge_id,
            "ts": time.time(),
            "capture_cadence_s": self._capture_interval_s,
            "last_detection_ts": self._last_detection_ts,
            "cpu_temp_c": _read_cpu_temp_c(),
            "mem_pct": _read_mem_pct(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        """Publish a status heartbeat every ``heartbeat_interval_s`` seconds."""
        while self._running:
            await asyncio.sleep(self._heartbeat_interval_s)
            if not self._running:
                break
            payload = self.heartbeat_payload()
            raw = _canonical_json(payload)
            try:
                import aiomqtt  # type: ignore[import-untyped]

                async with aiomqtt.Client(
                    hostname=self._mqtt_host, port=self._mqtt_port
                ) as client:
                    await client.publish(self._status_topic, payload=raw.encode(), qos=0)
                logger.debug("Heartbeat → %s", self._status_topic)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Heartbeat publish failed: %s", exc)
            self._heartbeats.append(payload)

    async def _healthz_server(self) -> None:
        """Serve a minimal HTTP /healthz endpoint for LAN diagnostics.

        Returns 200 + JSON when the watcher is running, 503 when stopped.
        Intentionally dependency-free (uses asyncio streams only).
        """
        import asyncio

        async def _handle(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            try:
                await reader.read(1024)  # consume the request
                status = "ok" if self._running else "stopping"
                body = _canonical_json(
                    {
                        "status": status,
                        "edge_id": self._edge_id,
                        "ranch_id": self._ranch_id,
                        "cpu_temp_c": _read_cpu_temp_c(),
                        "mem_pct": _read_mem_pct(),
                        "ts": time.time(),
                    }
                )
                http_status = "200 OK" if self._running else "503 Service Unavailable"
                response = (
                    f"HTTP/1.1 {http_status}\r\n"
                    "Content-Type: application/json\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                    f"{body}"
                )
                writer.write(response.encode())
                await writer.drain()
            except Exception as exc:  # noqa: BLE001
                logger.debug("healthz handler error: %s", exc)
            finally:
                writer.close()

        try:
            server = await asyncio.start_server(_handle, "0.0.0.0", self._healthz_port)
            logger.info("healthz listening on port %d", self._healthz_port)
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            pass
        except OSError as exc:
            logger.warning("healthz server failed to start on port %d: %s", self._healthz_port, exc)

    def _build_payload(
        self, frame: np.ndarray, detections: list[Detection]
    ) -> dict:  # type: ignore[type-arg]
        """Build a trough_cam-compatible MQTT payload dict.

        Matches the schema emitted by TroughCamSensor so agents receive
        identical-shaped messages from sim and real hardware.
        """
        ts = time.time()
        det_dicts = [
            {
                "tag_guess": d.tag_guess,
                "bbox": d.bbox,
                "confidence": d.confidence,
                "frame_ts": d.frame_ts,
            }
            for d in detections
        ]
        return {
            "ts": ts,
            "kind": "trough_cam.reading",
            "ranch": self._ranch_id,
            "entity": self._edge_id,
            "trough_id": self._edge_id,
            "cows_present": len(detections),
            "ids": [d.tag_guess for d in detections],
            "frame_uri": str(_FRAME_DIR / f"{self._edge_id}_{int(ts)}.jpg"),
            # Edge-only extras (ignored gracefully by sim consumers)
            "source": "edge",
            "detections": det_dicts,
        }

    async def _publish(self, payload: dict) -> None:  # type: ignore[type-arg]
        """Publish *payload* to MQTT; record in ``self._published`` for tests."""
        raw = _canonical_json(payload)
        try:
            import aiomqtt  # type: ignore[import-untyped]

            async with aiomqtt.Client(
                hostname=self._mqtt_host, port=self._mqtt_port
            ) as client:
                await client.publish(self._topic, payload=raw.encode(), qos=0)
            logger.debug("Published to %s (%d bytes)", self._topic, len(raw))
        except Exception as exc:  # noqa: BLE001
            logger.warning("MQTT publish failed: %s", exc)
        self._published.append(payload)

    def _annotate_and_save(
        self, frame: np.ndarray, detections: list[Detection], ts: float
    ) -> None:
        """Write an annotated JPEG to ``runtime/edge_frames/``."""
        try:
            import supervision as sv  # type: ignore[import-untyped]
            from PIL import Image  # type: ignore[import-untyped]

            if not detections:
                img = Image.fromarray(frame)
                out_path = _FRAME_DIR / f"{self._edge_id}_{int(ts)}.jpg"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(str(out_path), format="JPEG")
                return

            import numpy as _np

            xyxy = _np.array([d.bbox for d in detections], dtype=_np.float32)
            confs = _np.array([d.confidence for d in detections], dtype=_np.float32)
            sv_det = sv.Detections(xyxy=xyxy, confidence=confs)

            annotator = sv.BoxAnnotator()
            annotated = annotator.annotate(scene=frame.copy(), detections=sv_det)

            img = Image.fromarray(annotated)
            out_path = _FRAME_DIR / f"{self._edge_id}_{int(ts)}.jpg"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(out_path), format="JPEG")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Frame annotation failed: %s", exc)

    async def _emit_motion_event(self, payload: dict) -> None:  # type: ignore[type-arg]
        """Publish a camera.motion event when confident detections appear."""
        event = {
            "ts": payload["ts"],
            "kind": "camera.motion",
            "ranch": self._ranch_id,
            "entity": self._edge_id,
            "detections": payload["detections"],
        }
        motion_topic = f"skyherd/{self._ranch_id}/events/camera.motion"
        raw = _canonical_json(event)
        try:
            import aiomqtt  # type: ignore[import-untyped]

            async with aiomqtt.Client(
                hostname=self._mqtt_host, port=self._mqtt_port
            ) as client:
                await client.publish(motion_topic, payload=raw.encode(), qos=0)
            logger.debug("camera.motion event → %s", motion_topic)
        except Exception as exc:  # noqa: BLE001
            logger.debug("camera.motion publish failed: %s", exc)

    def _install_signal_handlers(self) -> None:
        """Register SIGINT / SIGTERM for graceful shutdown."""
        loop = asyncio.get_event_loop()

        def _handle(signum: int, _: object) -> None:
            logger.info("Signal %s received — stopping EdgeWatcher", signum)
            self.stop()
            loop.stop()

        try:
            loop.add_signal_handler(signal.SIGINT, _handle, signal.SIGINT, None)
            loop.add_signal_handler(signal.SIGTERM, _handle, signal.SIGTERM, None)
        except (NotImplementedError, RuntimeError):
            # Windows / test environments may not support add_signal_handler
            pass
