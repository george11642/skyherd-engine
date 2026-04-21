"""AcousticEmitterSensor — publishes emitter state and listens for activation commands."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from skyherd.sensors.base import Sensor

if TYPE_CHECKING:
    from skyherd.attest.ledger import Ledger
    from skyherd.sensors.bus import SensorBus
    from skyherd.world.world import World

logger = logging.getLogger(__name__)

_CMD_TOPIC_SUFFIX = "cmd"  # listens on skyherd/{ranch_id}/acoustic/cmd


class AcousticEmitterSensor(Sensor):
    """Acoustic deterrent emitter sensor.

    Publishes emitter state every ``period_s`` seconds.
    Listens on the command topic for activation/deactivation payloads.
    """

    topic_prefix = "acoustic"

    def __init__(
        self,
        world: World,
        bus: SensorBus,
        ranch_id: str,
        emitter_id: str = "emit_1",
        period_s: float = 30.0,
        ledger: Ledger | None = None,
    ) -> None:
        super().__init__(
            world=world,
            bus=bus,
            ranch_id=ranch_id,
            entity_id=emitter_id,
            period_s=period_s,
            ledger=ledger,
        )
        self._active: bool = False
        self._frequency_hz: float = 15000.0  # ultrasonic default
        self._pattern: str = "burst"
        self._conditioning_phase: str = "idle"
        self._cmd_topic = f"skyherd/{ranch_id}/acoustic/{_CMD_TOPIC_SUFFIX}"
        self._cmd_task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # Lifecycle override — also start command listener
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Run emitter loop and command listener concurrently."""
        self._cmd_task = asyncio.create_task(self._listen_commands())
        try:
            await super().run()
        except asyncio.CancelledError:
            if self._cmd_task is not None:
                self._cmd_task.cancel()
                try:
                    await self._cmd_task
                except asyncio.CancelledError:
                    pass
            raise

    async def _listen_commands(self) -> None:
        """Subscribe to command topic and update emitter state."""
        try:
            async with self.bus.subscribe(self._cmd_topic) as messages:
                async for _topic, cmd_payload in messages:
                    self._apply_command(cmd_payload)
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("AcousticEmitter command listener error: %s", exc)

    def _apply_command(self, cmd: dict[str, Any]) -> None:
        if "active" in cmd:
            self._active = bool(cmd["active"])
        if "frequency_hz" in cmd:
            self._frequency_hz = float(cmd["frequency_hz"])
        if "pattern" in cmd:
            self._pattern = str(cmd["pattern"])
        if "conditioning_phase" in cmd:
            self._conditioning_phase = str(cmd["conditioning_phase"])
        logger.info(
            "AcousticEmitter %s: active=%s freq=%.0fHz pattern=%s phase=%s",
            self.entity_id,
            self._active,
            self._frequency_hz,
            self._pattern,
            self._conditioning_phase,
        )

    async def tick(self) -> None:
        payload = {
            "ts": time.time(),
            "kind": "acoustic.reading",
            "ranch": self.ranch_id,
            "entity": self.entity_id,
            "active": self._active,
            "frequency_hz": self._frequency_hz,
            "pattern": self._pattern,
            "target_conditioning_phase": self._conditioning_phase,
        }
        await self.bus.publish(self.topic, payload, ledger=self.ledger)
