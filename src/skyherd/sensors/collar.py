"""CollarSensor — GPS+IMU collar on a single cow, emits position and activity."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from skyherd.sensors.base import Sensor

if TYPE_CHECKING:
    from skyherd.attest.ledger import Ledger
    from skyherd.sensors.bus import SensorBus
    from skyherd.world.world import World

logger = logging.getLogger(__name__)

_BATTERY_DRAIN_PER_TICK = 0.05  # % per tick (synthetic; real LoRa is ~0.01%/hr)
_LOW_BATTERY_THRESHOLD_PCT = 15.0
_WALKING_SPEED_THRESHOLD_M_S = 0.3  # cow speed above which activity = "walking"
_GRAZING_SPEED_THRESHOLD_M_S = 0.05  # between 0.05–0.3 = "grazing", below = "resting"


def _classify_activity(speed_m_s: float) -> str:
    if speed_m_s >= _WALKING_SPEED_THRESHOLD_M_S:
        return "walking"
    if speed_m_s >= _GRAZING_SPEED_THRESHOLD_M_S:
        return "grazing"
    return "resting"


class CollarSensor(Sensor):
    """GPS+IMU collar emitter for one cow.

    Emits position, heading, activity classification, and battery % every
    ``period_s`` seconds.  Fires ``collar.low_battery`` alert below 15%.
    """

    topic_prefix = "collar"

    def __init__(
        self,
        world: World,
        bus: SensorBus,
        ranch_id: str,
        cow_id: str,
        period_s: float = 60.0,
        ledger: Ledger | None = None,
        initial_battery_pct: float = 100.0,
    ) -> None:
        super().__init__(
            world=world,
            bus=bus,
            ranch_id=ranch_id,
            entity_id=cow_id,
            period_s=period_s,
            ledger=ledger,
        )
        self._cow_id = cow_id
        self._battery_pct: float = initial_battery_pct
        self._low_battery_fired = False
        self._prev_pos: tuple[float, float] | None = None

    async def tick(self) -> None:
        cow = self._find_cow()
        if cow is None:
            logger.warning("CollarSensor: cow %s not found in world", self._cow_id)
            return

        # Drain battery
        self._battery_pct = max(0.0, self._battery_pct - _BATTERY_DRAIN_PER_TICK)

        # Estimate speed from position delta
        pos: tuple[float, float] = tuple(cow["pos"])  # type: ignore[assignment]
        if self._prev_pos is not None:
            import math

            dx = pos[0] - self._prev_pos[0]
            dy = pos[1] - self._prev_pos[1]
            dist = math.sqrt(dx * dx + dy * dy)
            speed_m_s = dist / self.period_s
        else:
            speed_m_s = 0.0
        self._prev_pos = pos

        activity = _classify_activity(speed_m_s)

        payload = {
            "ts": time.time(),
            "kind": "collar.reading",
            "ranch": self.ranch_id,
            "entity": self._cow_id,
            "pos": list(pos),
            "heading_deg": float(cow.get("heading_deg", 0.0)),
            "activity": activity,
            "battery_pct": round(self._battery_pct, 2),
        }
        await self.bus.publish(self.topic, payload, ledger=self.ledger)

        # Low battery alert (once per episode)
        if self._battery_pct < _LOW_BATTERY_THRESHOLD_PCT and not self._low_battery_fired:
            self._low_battery_fired = True
            alert = {
                "ts": time.time(),
                "kind": "collar.low_battery",
                "ranch": self.ranch_id,
                "entity": self._cow_id,
                "battery_pct": round(self._battery_pct, 2),
            }
            await self.bus.publish(
                f"skyherd/{self.ranch_id}/alert/collar_low_battery",
                alert,
                ledger=self.ledger,
            )
            logger.warning("collar.low_battery for %s (%.1f%%)", self._cow_id, self._battery_pct)
        elif self._battery_pct >= _LOW_BATTERY_THRESHOLD_PCT:
            self._low_battery_fired = False

    def _find_cow(self) -> dict | None:
        snap = self.world.snapshot()
        for cow_dict in snap.cows:
            if cow_dict["id"] == self._cow_id:
                return cow_dict
        return None
