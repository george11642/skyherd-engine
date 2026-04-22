"""WeatherSensor — wraps world.weather and emits readings; fires weather.storm alert."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from skyherd.sensors.base import Sensor

if TYPE_CHECKING:
    from skyherd.attest.ledger import Ledger
    from skyherd.sensors.bus import SensorBus
    from skyherd.world.world import World

logger = logging.getLogger(__name__)

_STORM_CONDITION = "storm"


class WeatherSensor(Sensor):
    """Reads ``world.weather_driver.current`` and publishes a weather reading.

    Fires a ``weather.storm`` event whenever ``conditions == "storm"``.
    """

    topic_prefix = "weather"

    def __init__(
        self,
        world: World,
        bus: SensorBus,
        ranch_id: str,
        station_id: str = "station_1",
        period_s: float = 30.0,
        ledger: Ledger | None = None,
        ts_provider: Callable[[], float] | None = None,
    ) -> None:
        super().__init__(
            world=world,
            bus=bus,
            ranch_id=ranch_id,
            entity_id=station_id,
            period_s=period_s,
            ledger=ledger,
            ts_provider=ts_provider,
        )
        self._storm_active: bool = False  # track storm state for edge-fire

    async def tick(self) -> None:
        w = self.world.weather_driver.current

        payload = {
            "ts": self._ts(),
            "kind": "weather.reading",
            "ranch": self.ranch_id,
            "entity": self.entity_id,
            "wind_kt": round(w.wind_kt, 2),
            "wind_dir_deg": round(w.wind_dir_deg, 1),
            "temp_f": round(w.temp_f, 1),
            "conditions": str(w.conditions),
        }
        await self.bus.publish(self.topic, payload, ledger=self.ledger)

        # Storm alert
        is_storm = str(w.conditions) == _STORM_CONDITION
        if is_storm:
            alert = {
                "ts": self._ts(),
                "kind": "weather.storm",
                "ranch": self.ranch_id,
                "entity": self.entity_id,
                "wind_kt": round(w.wind_kt, 2),
                "temp_f": round(w.temp_f, 1),
                "conditions": str(w.conditions),
            }
            await self.bus.publish(
                f"skyherd/{self.ranch_id}/alert/weather_storm",
                alert,
                ledger=self.ledger,
            )
            if not self._storm_active:
                logger.warning("weather.storm alert fired for ranch %s", self.ranch_id)
                self._storm_active = True
        else:
            self._storm_active = False
