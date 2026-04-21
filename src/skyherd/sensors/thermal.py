"""ThermalCamSensor — drone-mounted thermal camera detecting predators in camera cone."""

from __future__ import annotations

import logging
import math
import time
from typing import TYPE_CHECKING

from skyherd.sensors.base import Sensor

if TYPE_CHECKING:
    from skyherd.attest.ledger import Ledger
    from skyherd.sensors.bus import SensorBus
    from skyherd.world.world import World

logger = logging.getLogger(__name__)

# Camera cone: 60° half-angle, 300 m range
_CAM_HALF_ANGLE_DEG = 30.0
_CAM_RANGE_M = 300.0


def _in_cone(
    cam_pos: tuple[float, float],
    cam_heading_deg: float,
    target_pos: tuple[float, float],
) -> bool:
    """Return True if *target_pos* is within the camera cone."""
    dx = target_pos[0] - cam_pos[0]
    dy = target_pos[1] - cam_pos[1]
    dist = math.sqrt(dx * dx + dy * dy)
    if dist > _CAM_RANGE_M:
        return False
    if dist == 0:
        return True
    bearing_deg = math.degrees(math.atan2(dy, dx)) % 360.0
    diff = abs((bearing_deg - cam_heading_deg + 180.0) % 360.0 - 180.0)
    return diff <= _CAM_HALF_ANGLE_DEG


class ThermalCamSensor(Sensor):
    """Thermal camera mounted on the drone (or barn when drone is idle).

    Emits a reading every ``period_s`` seconds; fires ``predator.thermal_hit``
    when a predator enters the camera cone.
    """

    topic_prefix = "thermal"

    def __init__(
        self,
        world: World,
        bus: SensorBus,
        ranch_id: str,
        cam_id: str,
        period_s: float = 15.0,
        ledger: Ledger | None = None,
    ) -> None:
        super().__init__(
            world=world,
            bus=bus,
            ranch_id=ranch_id,
            entity_id=cam_id,
            period_s=period_s,
            ledger=ledger,
        )

    def _cam_pose(self) -> tuple[tuple[float, float], float]:
        """Return (position, heading_deg) of the camera.

        Uses drone snapshot if available; falls back to barn position.
        """
        # No drone world integration yet — use barn as default mount
        barn_pos: tuple[float, float] = self.world.terrain.config.barn.pos
        # No drone world integration yet — use barn as default mount
        return barn_pos, 0.0  # heading north by default

    async def tick(self) -> None:
        cam_pos, cam_heading = self._cam_pose()
        snap = self.world.snapshot()

        hits: list[dict] = []
        for pred_dict in snap.predators:
            pred_pos: tuple[float, float] = tuple(pred_dict["pos"])  # type: ignore[assignment]
            if _in_cone(cam_pos, cam_heading, pred_pos):
                hits.append(
                    {
                        "predator_id": pred_dict["id"],
                        "species": pred_dict.get("species", "unknown"),
                        "thermal_signature": pred_dict.get("thermal_signature", 0.0),
                    }
                )

        payload = {
            "ts": time.time(),
            "kind": "thermal.reading",
            "ranch": self.ranch_id,
            "entity": self.entity_id,
            "cam_pos": list(cam_pos),
            "cam_heading_deg": cam_heading,
            "predators_detected": len(hits),
            "hits": hits,
        }
        await self.bus.publish(self.topic, payload, ledger=self.ledger)

        # Fire alert for each detected predator
        for hit in hits:
            alert = {
                "ts": time.time(),
                "kind": "predator.thermal_hit",
                "ranch": self.ranch_id,
                "entity": self.entity_id,
                **hit,
            }
            await self.bus.publish(
                f"skyherd/{self.ranch_id}/alert/thermal_hit",
                alert,
                ledger=self.ledger,
            )
            logger.warning(
                "predator.thermal_hit: %s (%s)",
                hit["predator_id"],
                hit.get("species"),
            )
