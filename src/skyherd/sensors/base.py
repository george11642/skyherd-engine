"""Sensor abstract base — all emitters inherit from this."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skyherd.attest.ledger import Ledger
    from skyherd.sensors.bus import SensorBus
    from skyherd.world.world import World

logger = logging.getLogger(__name__)


class Sensor(ABC):
    """Abstract base for all sensor emitters.

    Subclasses must define:
      - ``topic_prefix`` class variable (e.g. ``"skyherd/{ranch_id}/water"``)
      - ``tick()`` — emit one reading per call

    The ``run()`` loop calls ``tick()`` every ``period_s`` seconds until
    the task is cancelled.
    """

    topic_prefix: str = ""

    def __init__(
        self,
        world: World,
        bus: SensorBus,
        ranch_id: str,
        entity_id: str,
        period_s: float,
        ledger: Ledger | None = None,
    ) -> None:
        self.world = world
        self.bus = bus
        self.ranch_id = ranch_id
        self.entity_id = entity_id
        self.period_s = period_s
        self.ledger = ledger
        self.topic = f"skyherd/{ranch_id}/{self.topic_prefix}/{entity_id}"

    @abstractmethod
    async def tick(self) -> None:
        """Emit one sensor reading.  Called every ``period_s`` seconds."""

    async def run(self) -> None:
        """Loop: sleep period_s then tick, until cancelled."""
        logger.debug("Sensor %s starting (period=%.1fs)", self.topic, self.period_s)
        try:
            while True:
                await asyncio.sleep(self.period_s)
                await self.tick()
        except asyncio.CancelledError:
            logger.debug("Sensor %s cancelled", self.topic)
            raise
