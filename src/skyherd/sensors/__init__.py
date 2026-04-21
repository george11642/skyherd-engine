"""skyherd.sensors — MQTT sensor bus and emitter registry."""

from skyherd.sensors.base import Sensor
from skyherd.sensors.bus import SensorBus
from skyherd.sensors.registry import EMITTERS, run_all

__all__ = [
    "Sensor",
    "SensorBus",
    "EMITTERS",
    "run_all",
    "publish",
]


async def publish(
    topic: str,
    payload: dict,
    *,
    bus: SensorBus | None = None,
) -> None:
    """Convenience wrapper: publish a single payload via a one-shot SensorBus.

    If *bus* is provided, it is used directly (caller manages lifecycle).
    Otherwise a temporary bus is created (no embedded broker — expects external).
    """
    if bus is not None:
        await bus.publish(topic, payload)
        return

    import os

    os.environ.setdefault("MQTT_URL", "mqtt://localhost:1883")
    temp_bus = SensorBus()
    await temp_bus.publish(topic, payload)
