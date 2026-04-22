"""FenceMotionSensor — detects breaches on a single fence segment."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from skyherd.sensors.base import Sensor

if TYPE_CHECKING:
    from skyherd.attest.ledger import Ledger
    from skyherd.sensors.bus import SensorBus
    from skyherd.world.terrain import FenceLineConfig
    from skyherd.world.world import World

logger = logging.getLogger(__name__)

_DEBOUNCE_S = 5.0  # minimum seconds between consecutive breach alerts


class FenceMotionSensor(Sensor):
    """Polls world for fence breaches on a specific segment.

    Fires ``fence.breach`` with subject_kind and thermal_hint when a breach is
    detected.  Debounced to at most one alert per ``_DEBOUNCE_S`` seconds.
    """

    topic_prefix = "fence"

    def __init__(
        self,
        world: World,
        bus: SensorBus,
        ranch_id: str,
        fence_cfg: FenceLineConfig,
        period_s: float = 3.0,
        ledger: Ledger | None = None,
        ts_provider: Callable[[], float] | None = None,
    ) -> None:
        super().__init__(
            world=world,
            bus=bus,
            ranch_id=ranch_id,
            entity_id=fence_cfg.id,
            period_s=period_s,
            ledger=ledger,
            ts_provider=ts_provider,
        )
        self._segment_id = fence_cfg.id
        self._last_alert_time: float = 0.0

    async def tick(self) -> None:
        # Debounce check using monotonic clock (wall-clock independent)
        now = time.monotonic()
        if now - self._last_alert_time < _DEBOUNCE_S:
            return

        snap = self.world.snapshot()
        breach_subject: str | None = None
        thermal_hint: float = 0.0

        # Check predators first (higher priority)
        for pred_dict in snap.predators:
            pred_pos: tuple[float, float] = tuple(pred_dict["pos"])  # type: ignore[assignment]
            breached = self.world.terrain.fence_breached_by(pred_pos)
            if self._segment_id in breached:
                breach_subject = "predator"
                thermal_hint = float(pred_dict.get("thermal_signature", 0.4))
                break

        # Check cows if no predator breach
        if breach_subject is None:
            for cow_dict in snap.cows:
                cow_pos: tuple[float, float] = tuple(cow_dict["pos"])  # type: ignore[assignment]
                breached = self.world.terrain.fence_breached_by(cow_pos)
                if self._segment_id in breached:
                    breach_subject = "cow"
                    break

        if breach_subject is None:
            return

        self._last_alert_time = now

        payload = {
            "ts": self._ts(),
            "kind": "fence.breach",
            "ranch": self.ranch_id,
            "entity": self._segment_id,
            "segment_id": self._segment_id,
            "subject_kind": breach_subject,
            "thermal_hint": thermal_hint,
        }
        await self.bus.publish(self.topic, payload, ledger=self.ledger)
        logger.warning(
            "fence.breach on %s — subject=%s thermal=%.2f",
            self._segment_id,
            breach_subject,
            thermal_hint,
        )
