"""Sensor registry — EMITTERS dict and run_all factory.

``run_all`` spawns one asyncio task per sensor entity and returns a list of
tasks so the caller can cancel the whole group.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from skyherd.sensors.acoustic import AcousticEmitterSensor
from skyherd.sensors.collar import CollarSensor
from skyherd.sensors.fence import FenceMotionSensor
from skyherd.sensors.thermal import ThermalCamSensor
from skyherd.sensors.trough_cam import TroughCamSensor
from skyherd.sensors.water import WaterTankSensor
from skyherd.sensors.weather import WeatherSensor

if TYPE_CHECKING:
    from skyherd.attest.ledger import Ledger
    from skyherd.sensors.base import Sensor
    from skyherd.sensors.bus import SensorBus
    from skyherd.world.world import World

logger = logging.getLogger(__name__)

# Registry of sensor class names → class objects (for introspection / docs)
EMITTERS: dict[str, type[Sensor]] = {
    "water": WaterTankSensor,
    "trough_cam": TroughCamSensor,
    "thermal": ThermalCamSensor,
    "fence": FenceMotionSensor,
    "collar": CollarSensor,
    "acoustic": AcousticEmitterSensor,
    "weather": WeatherSensor,
}


def _build_sensors(
    world: World,
    bus: SensorBus,
    ranch_id: str,
    ledger: Ledger | None,
) -> list[Sensor]:
    """Instantiate one sensor per entity derived from world terrain + herd."""
    sensors: list[Sensor] = []
    cfg = world.terrain.config

    # --- Water tanks ---
    for tank in cfg.water_tanks:
        sensors.append(
            WaterTankSensor(
                world=world,
                bus=bus,
                ranch_id=ranch_id,
                tank_cfg=tank,
                period_s=5.0,
                ledger=ledger,
            )
        )

    # --- Trough cameras (one per trough) ---
    for i, trough in enumerate(cfg.troughs):
        sensors.append(
            TroughCamSensor(
                world=world,
                bus=bus,
                ranch_id=ranch_id,
                trough_cfg=trough,
                cam_id=f"cam_{i + 1}",
                period_s=10.0,
                ledger=ledger,
            )
        )

    # --- Thermal camera (one, drone-mounted) ---
    sensors.append(
        ThermalCamSensor(
            world=world,
            bus=bus,
            ranch_id=ranch_id,
            cam_id="therm_1",
            period_s=15.0,
            ledger=ledger,
        )
    )

    # --- Fence motion sensors (one per fence segment) ---
    for fence in cfg.fence_lines:
        sensors.append(
            FenceMotionSensor(
                world=world,
                bus=bus,
                ranch_id=ranch_id,
                fence_cfg=fence,
                period_s=3.0,
                ledger=ledger,
            )
        )

    # --- Collar sensors (one per cow) ---
    for cow in world.herd.cows:
        sensors.append(
            CollarSensor(
                world=world,
                bus=bus,
                ranch_id=ranch_id,
                cow_id=cow.id,
                period_s=60.0,
                ledger=ledger,
            )
        )

    # --- Acoustic emitter (one per ranch) ---
    sensors.append(
        AcousticEmitterSensor(
            world=world,
            bus=bus,
            ranch_id=ranch_id,
            emitter_id="emit_1",
            period_s=30.0,
            ledger=ledger,
        )
    )

    # --- Weather station (one per ranch) ---
    sensors.append(
        WeatherSensor(
            world=world,
            bus=bus,
            ranch_id=ranch_id,
            station_id="station_1",
            period_s=30.0,
            ledger=ledger,
        )
    )

    return sensors


async def run_all(
    world: World,
    bus: SensorBus,
    ranch_id: str,
    ledger: Ledger | None = None,
) -> list[asyncio.Task[Any]]:
    """Spawn all sensor tasks and return the task list.

    The caller is responsible for cancelling the tasks when done::

        tasks = await run_all(world, bus, "ranch_a")
        try:
            await asyncio.sleep(60)
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    """
    sensors = _build_sensors(world, bus, ranch_id, ledger)
    tasks: list[asyncio.Task[Any]] = []
    for sensor in sensors:
        task = asyncio.create_task(sensor.run(), name=sensor.topic)
        tasks.append(task)

    logger.info(
        "run_all: spawned %d sensor tasks for ranch %s",
        len(tasks),
        ranch_id,
    )
    return tasks
