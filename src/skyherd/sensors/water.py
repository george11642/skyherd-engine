"""WaterTankSensor — monitors a single water tank and emits level/pressure readings."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from skyherd.sensors.base import Sensor

if TYPE_CHECKING:
    from skyherd.attest.ledger import Ledger
    from skyherd.sensors.bus import SensorBus
    from skyherd.world.terrain import WaterTankConfig
    from skyherd.world.world import World

logger = logging.getLogger(__name__)

_WATER_LOW_THRESHOLD_PCT = 20.0
_FLOW_LPM_PER_PSI = 0.5  # synthetic: flow_lpm ≈ pressure_psi * factor


class WaterTankSensor(Sensor):
    """Emits water tank telemetry every ``period_s`` seconds.

    Fires a ``water.low`` event (once, debounced) when level < 20%.
    """

    topic_prefix = "water"

    def __init__(
        self,
        world: World,
        bus: SensorBus,
        ranch_id: str,
        tank_cfg: WaterTankConfig,
        period_s: float = 5.0,
        ledger: Ledger | None = None,
    ) -> None:
        super().__init__(
            world=world,
            bus=bus,
            ranch_id=ranch_id,
            entity_id=tank_cfg.id,
            period_s=period_s,
            ledger=ledger,
        )
        self._tank_id = tank_cfg.id
        self._low_event_fired = False  # debounce: fire once per low episode

    async def tick(self) -> None:
        # Find current tank state from world terrain config
        tank = self._find_tank()
        if tank is None:
            logger.warning("WaterTankSensor: tank %s not found in world", self._tank_id)
            return

        flow_lpm = round(tank.pressure_psi * _FLOW_LPM_PER_PSI, 2)
        payload = {
            "ts": time.time(),
            "kind": "water.reading",
            "ranch": self.ranch_id,
            "entity": self._tank_id,
            "level_pct": round(tank.level_pct, 2),
            "pressure_psi": round(tank.pressure_psi, 2),
            "flow_lpm": flow_lpm,
            "temp_f": 55.0,  # synthetic ground-temp for buried tanks
        }
        await self.bus.publish(self.topic, payload, ledger=self.ledger)

        # Debounced water.low alert
        if tank.level_pct < _WATER_LOW_THRESHOLD_PCT and not self._low_event_fired:
            self._low_event_fired = True
            alert = {
                "ts": time.time(),
                "kind": "water.low",
                "ranch": self.ranch_id,
                "entity": self._tank_id,
                "level_pct": round(tank.level_pct, 2),
            }
            await self.bus.publish(
                f"skyherd/{self.ranch_id}/alert/water_low",
                alert,
                ledger=self.ledger,
            )
            logger.warning(
                "water.low fired for %s (%.1f%%)", self._tank_id, tank.level_pct
            )
        elif tank.level_pct >= _WATER_LOW_THRESHOLD_PCT:
            # Reset debounce when level recovers
            self._low_event_fired = False

    def _find_tank(self) -> WaterTankConfig | None:
        for t in self.world.terrain.config.water_tanks:
            if t.id == self._tank_id:
                return t
        return None
