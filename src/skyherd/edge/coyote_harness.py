"""CoyoteHarness — cardboard-coyote thermal clip playback.

Emits canonical ``skyherd/{ranch}/thermal/{cam_id}`` + ``predator.thermal_hit``
payloads matching :class:`skyherd.sensors.thermal.ThermalCamSensor`, driven by a
pre-recorded thermal PNG sequence (default: ``tests/fixtures/thermal_clips/``).

Used for:

* **Hackathon demo** — a cardboard coyote cutout wrapped in thermally-reflective
  tape held in front of a camera lets the fence-line scenario play live
  without a real nocturnal predator.
* **Integration tests** — an in-process fabric drives real agent behaviour on
  deterministic thermal hits.

Deterministic: identical ``seed`` produces identical frame-index sequences.  No
wall-clock state in the frame iterator — time-dependent output (``ts``) is
sanitisable via the project-wide determinism sanitizer used by
``make demo SEED=42 SCENARIO=all``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_RANCH_ID = "ranch_a"
_DEFAULT_CAM_ID = "coyote_cam"
_DEFAULT_MQTT_URL = "mqtt://localhost:1883"
_DEFAULT_INTERVAL_S = 2.0
_DEFAULT_SPECIES = "coyote"
_DEFAULT_THERMAL_SIGNATURE = 0.78
_DEFAULT_CLIP_DIR = Path("tests/fixtures/thermal_clips")
_TOPIC_PREFIX = "thermal"


def _canonical_json(payload: dict[str, Any]) -> str:
    """Deterministic JSON wire format (matches SensorBus + EdgeWatcher)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _parse_mqtt_url(url: str) -> tuple[str, int]:
    """Parse ``mqtt://host:port`` → (host, port); defaults to port 1883."""
    without_scheme = url.split("://", 1)[-1]
    host, _, port_str = without_scheme.rpartition(":")
    if not host:
        host = without_scheme
        port_str = ""
    try:
        port = int(port_str) if port_str else 1883
    except ValueError:
        port = 1883
    return host or "localhost", port


class CoyoteHarness:
    """Plays a pre-recorded thermal clip over MQTT.

    Parameters
    ----------
    cam_id:
        Thermal camera identifier.
    ranch_id:
        Ranch identifier (topic prefix).
    mqtt_url:
        Broker URL.
    interval_s:
        Seconds between frames when ``run()`` is used.
    clip_dir:
        Override the default PNG clip directory.
    species:
        Reported predator species (defaults to ``coyote``).
    thermal_signature:
        Fixed thermal signature emitted in payloads (0.0 – 1.0).
    seed:
        Deterministic seed for frame-index cycling.
    ts_provider:
        Callable returning float timestamps — test injection.
    mqtt_publish:
        Async callable ``(topic, raw_bytes) -> None`` — test injection.
    """

    def __init__(
        self,
        cam_id: str | None = None,
        ranch_id: str | None = None,
        mqtt_url: str | None = None,
        interval_s: float | None = None,
        clip_dir: Path | None = None,
        species: str = _DEFAULT_SPECIES,
        thermal_signature: float = _DEFAULT_THERMAL_SIGNATURE,
        seed: int | None = None,
        ts_provider: Callable[[], float] | None = None,
        mqtt_publish: Callable[[str, bytes], Awaitable[None]] | None = None,
    ) -> None:
        self._cam_id = cam_id or os.environ.get("COYOTE_CAM_ID", _DEFAULT_CAM_ID)
        self._ranch_id = ranch_id or os.environ.get("RANCH_ID", _DEFAULT_RANCH_ID)
        self._mqtt_url = mqtt_url or os.environ.get("MQTT_URL", _DEFAULT_MQTT_URL)
        self._interval_s = float(
            interval_s
            if interval_s is not None
            else os.environ.get("COYOTE_INTERVAL_S", _DEFAULT_INTERVAL_S)
        )
        self._species = species
        self._thermal_signature = float(thermal_signature)
        self._seed = seed
        self._ts_provider: Callable[[], float] = ts_provider or time.time
        self._mqtt_publish = mqtt_publish
        self._tick_count = 0
        self._running = False

        self._topic_reading = f"skyherd/{self._ranch_id}/{_TOPIC_PREFIX}/{self._cam_id}"
        self._topic_alert = f"skyherd/{self._ranch_id}/alert/thermal_hit"

        # Load clip
        clip = clip_dir if clip_dir is not None else _DEFAULT_CLIP_DIR
        self._clip_dir = Path(clip)
        self._clip_frames: list[Path] = self._load_clip(self._clip_dir)

        # Introspection: test hooks populate these
        self._published_readings: list[dict[str, Any]] = []
        self._published_alerts: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Clip loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_clip(clip_dir: Path) -> list[Path]:
        """Return PNGs in *clip_dir* sorted lexicographically.

        Raises
        ------
        FileNotFoundError
            If *clip_dir* does not exist.
        ValueError
            If *clip_dir* exists but contains no PNG frames.
        """
        if not clip_dir.exists():
            raise FileNotFoundError(
                f"thermal clip dir not found: {clip_dir} — run "
                "'python -m tests.fixtures.thermal_clips._generate' to create fixtures."
            )
        frames = sorted(p for p in clip_dir.iterdir() if p.suffix.lower() == ".png")
        if not frames:
            raise ValueError(
                f"thermal clip dir {clip_dir} contains no PNG frames — "
                "run 'python -m tests.fixtures.thermal_clips._generate'."
            )
        return frames

    # ------------------------------------------------------------------
    # Deterministic frame selection
    # ------------------------------------------------------------------

    def _frame_index(self) -> int:
        """Return the frame index for the current tick."""
        n = len(self._clip_frames)
        if self._seed is None:
            return self._tick_count % n
        # Knuth multiplicative hash — stateless, spreads consecutive ticks.
        return (self._seed * 2654435761 + self._tick_count) % n

    # ------------------------------------------------------------------
    # Payload builders
    # ------------------------------------------------------------------

    def _build_hit(self, frame_idx: int) -> dict[str, Any]:
        return {
            "predator_id": f"cardboard_{self._species}_{frame_idx}",
            "species": self._species,
            "thermal_signature": self._thermal_signature,
        }

    def _build_reading(self, ts: float, frame_path: Path, frame_idx: int) -> dict[str, Any]:
        """Matches ThermalCamSensor schema + harness extras (ignored by consumers)."""
        hit = self._build_hit(frame_idx)
        return {
            "ts": ts,
            "kind": "thermal.reading",
            "ranch": self._ranch_id,
            "entity": self._cam_id,
            "cam_pos": [0.0, 0.0],
            "cam_heading_deg": 0.0,
            "predators_detected": 1,
            "hits": [hit],
            # Harness extras
            "source": "cardboard_coyote",
            "frame_path": str(frame_path),
            "frame_idx": frame_idx,
            "seeded": self._seed is not None,
        }

    def _build_thermal_hit_alert(self, ts: float, frame_idx: int) -> dict[str, Any]:
        hit = self._build_hit(frame_idx)
        return {
            "ts": ts,
            "kind": "predator.thermal_hit",
            "ranch": self._ranch_id,
            "entity": self._cam_id,
            **hit,
        }

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    async def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish *payload* to *topic*; inject-friendly + best-effort."""
        raw = _canonical_json(payload).encode()

        if self._mqtt_publish is not None:
            try:
                await self._mqtt_publish(topic, raw)
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "injected mqtt_publish raised on %s (%s) — swallowed", topic, exc
                )
            return

        # Default: aiomqtt best-effort
        try:
            import aiomqtt  # type: ignore[import-untyped]

            host, port = _parse_mqtt_url(self._mqtt_url)
            async with aiomqtt.Client(hostname=host, port=port, timeout=2.0) as client:
                await client.publish(topic, payload=raw, qos=0)
        except Exception as exc:  # noqa: BLE001
            logger.debug("CoyoteHarness publish best-effort failed on %s: %s", topic, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_once(self) -> dict[str, Any]:
        """Emit one thermal.reading + predator.thermal_hit pair.  Returns the reading."""
        frame_idx = self._frame_index()
        frame_path = self._clip_frames[frame_idx]
        ts = self._ts_provider()

        reading = self._build_reading(ts, frame_path, frame_idx)
        alert = self._build_thermal_hit_alert(ts, frame_idx)

        await self._publish(self._topic_reading, reading)
        await self._publish(self._topic_alert, alert)

        self._published_readings.append(reading)
        self._published_alerts.append(alert)

        self._tick_count += 1
        return reading

    async def run(self) -> None:
        """Loop frames until ``stop()`` is called or SIGINT/SIGTERM arrive."""
        self._running = True
        self._install_signal_handlers()
        logger.info(
            "CoyoteHarness started — ranch=%s cam=%s seed=%s frames=%d interval=%.1fs",
            self._ranch_id,
            self._cam_id,
            self._seed,
            len(self._clip_frames),
            self._interval_s,
        )
        try:
            while self._running:
                try:
                    await self.run_once()
                except Exception as exc:  # noqa: BLE001
                    logger.error("CoyoteHarness tick failed: %s", exc)
                await asyncio.sleep(self._interval_s)
        except asyncio.CancelledError:
            logger.info("CoyoteHarness cancelled — shutting down")
        finally:
            self._running = False

    def stop(self) -> None:
        """Request graceful shutdown."""
        self._running = False

    def _install_signal_handlers(self) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGINT, self.stop)
            loop.add_signal_handler(signal.SIGTERM, self.stop)
        except (NotImplementedError, RuntimeError) as exc:
            logger.debug("signal handler unavailable: %s", exc)
