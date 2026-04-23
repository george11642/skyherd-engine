"""TroughCamSensor — counts cows near a trough and optionally renders a frame."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from skyherd.sensors.base import Sensor

if TYPE_CHECKING:
    from skyherd.attest.ledger import Ledger
    from skyherd.sensors.bus import SensorBus
    from skyherd.world.terrain import TroughConfig
    from skyherd.world.world import World

logger = logging.getLogger(__name__)

_COW_PROXIMITY_M = 50.0  # cows within this radius are "at the trough"
_FRAME_DIR = Path("runtime/frames")


def _write_placeholder_png(out_path: Path, cow_count: int) -> None:
    """Write a minimal placeholder PNG via PIL if vision renderer is absent."""
    try:
        from PIL import Image, ImageDraw  # type: ignore[import-untyped]

        img = Image.new("RGB", (320, 240), color=(34, 85, 34))  # dark green bg
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), f"TroughCam — {cow_count} cows", fill=(255, 255, 255))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(out_path), format="PNG")
    except Exception as exc:  # noqa: BLE001
        logger.debug("PIL placeholder write failed: %s", exc)


class TroughCamSensor(Sensor):
    """Emits trough camera telemetry every ``period_s`` seconds.

    Counts cows within 50 m of the trough; writes a frame (via vision renderer
    or PIL placeholder) and includes its path in the payload.
    """

    topic_prefix = "trough_cam"

    def __init__(
        self,
        world: World,
        bus: SensorBus,
        ranch_id: str,
        trough_cfg: TroughConfig,
        cam_id: str,
        period_s: float = 10.0,
        ledger: Ledger | None = None,
        ts_provider: Callable[[], float] | None = None,
    ) -> None:
        super().__init__(
            world=world,
            bus=bus,
            ranch_id=ranch_id,
            entity_id=cam_id,
            period_s=period_s,
            ledger=ledger,
            ts_provider=ts_provider,
        )
        self._trough_id = trough_cfg.id
        self._trough_pos = trough_cfg.pos

    async def tick(self) -> None:
        snap = self.world.snapshot()

        # Count cows within proximity
        nearby_ids: list[str] = []
        for cow_dict in snap.cows:
            cx, cy = cow_dict["pos"]
            tx, ty = self._trough_pos
            dist = math.sqrt((cx - tx) ** 2 + (cy - ty) ** 2)
            if dist <= _COW_PROXIMITY_M:
                nearby_ids.append(cow_dict["id"])

        ts_int = int(self._ts())
        frame_path = _FRAME_DIR / f"{self._trough_id}_{ts_int}.png"

        # Try vision renderer first; fall back to PIL placeholder
        frame_written = False
        try:
            from skyherd.vision.renderer import render_trough_frame  # type: ignore[import]

            render_trough_frame(self.world, self._trough_id, frame_path)
            frame_written = True
        except ImportError as exc:
            logger.debug("vision renderer unavailable â skipping trough frame render: %s", exc)

        if not frame_written:
            _write_placeholder_png(frame_path, len(nearby_ids))

        payload = {
            "ts": self._ts(),
            "kind": "trough_cam.reading",
            "ranch": self.ranch_id,
            "entity": self.entity_id,
            "trough_id": self._trough_id,
            "cows_present": len(nearby_ids),
            "ids": nearby_ids,
            "frame_uri": str(frame_path),
        }
        await self.bus.publish(self.topic, payload, ledger=self.ledger)
