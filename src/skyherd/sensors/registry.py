"""Sensor registry — EMITTERS dict and run_all factory.

``run_all`` spawns one asyncio task per sensor entity and returns a list of
tasks so the caller can cancel the whole group.

Hardware-override support
-------------------------
Pass ``overrides`` to ``run_all`` (or set the ``HARDWARE_OVERRIDES`` env var)
to suppress specific sim emitters when a real Pi takes over that MQTT topic.

Override dict format::

    {
        "trough_cam": {"trough_1": "edge-fence", "trough_2": "edge-barn"},
        "fence":      {"fence_sw": "edge-fence"},
        "thermal":    {"therm_1": "edge-fence"},
    }

Env-var format (comma-separated ``sensor_type:entity_id:edge_node`` triples)::

    HARDWARE_OVERRIDES=trough_cam:trough_1:edge-fence,trough_cam:trough_2:edge-barn

When an entry is present the sim emitter for that ``(sensor_type, entity_id)``
pair is **not** spawned.  Every other emitter and all agents are unaffected.
"""

from __future__ import annotations

import asyncio
import logging
import os
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

# ---------------------------------------------------------------------------
# Override support
# ---------------------------------------------------------------------------

_HW_OVERRIDES_ENV = "HARDWARE_OVERRIDES"

# Sensor types that can be taken over by hardware nodes.
OVERRIDEABLE_SENSOR_TYPES: frozenset[str] = frozenset({"trough_cam", "fence", "thermal"})


def parse_overrides(raw: str) -> dict[str, dict[str, str]]:
    """Parse ``HARDWARE_OVERRIDES`` env-var string into a nested dict.

    Input format: ``sensor_type:entity_id:edge_node[,...]``

    Example::

        "trough_cam:trough_1:edge-fence,trough_cam:trough_2:edge-barn"

    Returns::

        {"trough_cam": {"trough_1": "edge-fence", "trough_2": "edge-barn"}}
    """
    result: dict[str, dict[str, str]] = {}
    for triple in raw.split(","):
        triple = triple.strip()
        if not triple:
            continue
        parts = triple.split(":", 2)
        if len(parts) != 3:
            logger.warning("HARDWARE_OVERRIDES: skipping malformed triple %r", triple)
            continue
        sensor_type, entity_id, edge_node = parts
        result.setdefault(sensor_type, {})[entity_id] = edge_node
    return result


def _load_overrides(
    overrides: dict[str, dict[str, str]] | None,
) -> dict[str, dict[str, str]]:
    """Resolve overrides from kwarg or env var.

    Priority: kwarg > env var > empty dict (no overrides).
    """
    if overrides is not None:
        return overrides
    raw = os.environ.get(_HW_OVERRIDES_ENV, "").strip()
    if raw:
        parsed = parse_overrides(raw)
        if parsed:
            logger.info(
                "HARDWARE_OVERRIDES loaded from env: %s",
                {k: list(v) for k, v in parsed.items()},
            )
        return parsed
    return {}


def _is_overridden(
    sensor_type: str,
    entity_id: str,
    hw_overrides: dict[str, dict[str, str]],
) -> bool:
    """Return True if this (sensor_type, entity_id) pair is taken over by hardware."""
    return entity_id in hw_overrides.get(sensor_type, {})


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

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
    hw_overrides: dict[str, dict[str, str]] | None = None,
) -> list[Sensor]:
    """Instantiate one sensor per entity derived from world terrain + herd.

    Parameters
    ----------
    hw_overrides:
        Nested dict ``{sensor_type: {entity_id: edge_node}}``.  Any sensor
        whose ``(sensor_type, entity_id)`` pair appears here is **skipped** —
        the real Pi node owns that topic.
    """
    if hw_overrides is None:
        hw_overrides = {}

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
        if _is_overridden("trough_cam", trough.id, hw_overrides):
            edge_node = hw_overrides["trough_cam"][trough.id]
            logger.info(
                "trough_cam/%s suppressed — hardware override by %s",
                trough.id,
                edge_node,
            )
            continue
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
    if _is_overridden("thermal", "therm_1", hw_overrides):
        edge_node = hw_overrides["thermal"]["therm_1"]
        logger.info("thermal/therm_1 suppressed — hardware override by %s", edge_node)
    else:
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
        if _is_overridden("fence", fence.id, hw_overrides):
            edge_node = hw_overrides["fence"][fence.id]
            logger.info(
                "fence/%s suppressed — hardware override by %s",
                fence.id,
                edge_node,
            )
            continue
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
    overrides: dict[str, dict[str, str]] | None = None,
) -> list[asyncio.Task[Any]]:
    """Spawn all sensor tasks and return the task list.

    Parameters
    ----------
    overrides:
        Hardware override dict ``{sensor_type: {entity_id: edge_node}}``.
        When provided (or when ``HARDWARE_OVERRIDES`` env var is set), any
        sensor whose ``(sensor_type, entity_id)`` pair is listed is **not**
        spawned — the real Pi node publishes to that topic instead.

        Env-var format: ``sensor_type:entity_id:edge_node[,...]``
        Example::

            HARDWARE_OVERRIDES=trough_cam:trough_1:edge-fence,trough_cam:trough_2:edge-barn

    The caller is responsible for cancelling the tasks when done::

        tasks = await run_all(world, bus, "ranch_a")
        try:
            await asyncio.sleep(60)
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    """
    hw_overrides = _load_overrides(overrides)
    sensors = _build_sensors(world, bus, ranch_id, ledger, hw_overrides)
    tasks: list[asyncio.Task[Any]] = []
    for sensor in sensors:
        task = asyncio.create_task(sensor.run(), name=sensor.topic)
        tasks.append(task)

    suppressed = sum(len(v) for v in hw_overrides.values())
    logger.info(
        "run_all: spawned %d sensor tasks for ranch %s (%d suppressed by hardware overrides)",
        len(tasks),
        ranch_id,
        suppressed,
    )
    return tasks
