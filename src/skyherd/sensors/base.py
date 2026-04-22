"""Sensor abstract base — all emitters inherit from this."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skyherd.attest.ledger import Ledger
    from skyherd.sensors.bus import SensorBus
    from skyherd.world.world import World

logger = logging.getLogger(__name__)

# Default wall-clock ts_provider — replaced with world.clock.sim_time_s in sim
_WALL_CLOCK_TS: Callable[[], float] = time.time


class Sensor(ABC):
    """Abstract base for all sensor emitters.

    Subclasses must define:
      - ``topic_prefix`` class variable (e.g. ``"skyherd/{ranch_id}/water"``)
      - ``tick()`` — emit one reading per call

    The ``run()`` loop calls ``tick()`` every ``period_s`` seconds until
    the task is cancelled.

    Parameters
    ----------
    ts_provider:
        Callable returning the current timestamp as a float (Unix seconds).
        Defaults to ``time.time`` (wall-clock).  In deterministic sim runs,
        pass ``world.clock.sim_time_s`` or a lambda wrapping the world clock.
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
        ts_provider: Callable[[], float] | None = None,
    ) -> None:
        self.world = world
        self.bus = bus
        self.ranch_id = ranch_id
        self.entity_id = entity_id
        self.period_s = period_s
        self.ledger = ledger
        self.topic = f"skyherd/{ranch_id}/{self.topic_prefix}/{entity_id}"
        self._ts: Callable[[], float] = ts_provider if ts_provider is not None else _WALL_CLOCK_TS

    def _iso(self) -> str:
        """Return current timestamp as ISO-8601 string via ts_provider."""
        ts = self._ts()
        return datetime.fromtimestamp(ts, tz=UTC).isoformat()

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
