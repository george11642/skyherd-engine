"""World facade — assembles all sim subsystems and drives them forward."""

from __future__ import annotations

import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from skyherd.world.cattle import Cow, Herd
from skyherd.world.clock import Clock
from skyherd.world.predators import PredatorSpawner
from skyherd.world.terrain import Terrain, TerrainConfig
from skyherd.world.weather import Weather, WeatherDriver

# ---------------------------------------------------------------------------
# Snapshot model
# ---------------------------------------------------------------------------


class WorldSnapshot(BaseModel):
    """Serialisable point-in-time snapshot of the entire ranch world."""

    sim_time_s: float
    clock_iso: str
    is_night: bool
    weather: Weather
    cows: list[dict[str, Any]]
    predators: list[dict[str, Any]]
    event_count: int

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# World
# ---------------------------------------------------------------------------


class World:
    """Top-level simulation object.

    All randomness is seeded; same seed + same inputs = identical event stream.
    """

    def __init__(
        self,
        clock: Clock,
        terrain: Terrain,
        herd: Herd,
        predator_spawner: PredatorSpawner,
        weather_driver: WeatherDriver,
    ) -> None:
        self.clock = clock
        self.terrain = terrain
        self.herd = herd
        self.predator_spawner = predator_spawner
        self.weather_driver = weather_driver
        self.events: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(self, dt: float) -> list[dict[str, Any]]:
        """Advance the world by *dt* sim-seconds; return newly emitted events."""
        self.clock.advance(dt)
        sim_time_s = self.clock.sim_time_s

        # 1. Weather
        weather = self.weather_driver.step(dt, sim_time_s)

        # 2. Herd
        herd_events = self.herd.step(dt, self.terrain, weather, sim_time_s)

        # 3. Predators
        pred_events = self.predator_spawner.step(
            dt, self.clock, self.terrain, self.herd, sim_time_s
        )

        # 4. Fence breach check for predators
        fence_events: list[dict] = []
        for pred in self.predator_spawner.predators:
            breached = self.terrain.fence_breached_by(pred.pos)
            for fence_id in breached:
                fence_events.append(
                    {
                        "type": "fence.breach",
                        "source": "predator",
                        "predator_id": pred.id,
                        "fence_id": fence_id,
                        "sim_time_s": sim_time_s,
                    }
                )

        # 5. Water level check
        water_events: list[dict] = []
        for tank in self.terrain.config.water_tanks:
            if tank.level_pct < 20.0:
                water_events.append(
                    {
                        "type": "water.low",
                        "tank_id": tank.id,
                        "level_pct": tank.level_pct,
                        "sim_time_s": sim_time_s,
                    }
                )

        # 6. Storm events
        storm_events: list[dict] = []
        if weather.conditions == "storm":
            storm_events.append(
                {
                    "type": "weather.storm",
                    "wind_kt": weather.wind_kt,
                    "temp_f": weather.temp_f,
                    "sim_time_s": sim_time_s,
                }
            )

        step_events = herd_events + pred_events + fence_events + water_events + storm_events
        self.events.extend(step_events)
        return step_events

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> WorldSnapshot:
        """Return a serialisable snapshot of the current world state."""
        return WorldSnapshot(
            sim_time_s=self.clock.sim_time_s,
            clock_iso=self.clock.iso(),
            is_night=self.clock.is_night(),
            weather=self.weather_driver.current,
            cows=[c.model_dump() for c in self.herd.cows],
            predators=[p.model_dump() for p in self.predator_spawner.predators],
            event_count=len(self.events),
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def make_world(seed: int, config_path: Path) -> World:
    """Build a fully-seeded :class:`World` from a YAML ranch config.

    Same *seed* + same *config_path* content = identical world evolution.
    """
    rng = random.Random(seed)

    # --- Terrain ---
    terrain_config = TerrainConfig.from_yaml(config_path)
    terrain = Terrain(terrain_config)

    # --- Clock (2026-04-21 06:00 MT = 13:00 UTC) ---
    start_utc = datetime(2026, 4, 21, 13, 0, 0, tzinfo=UTC)
    clock = Clock(sim_start_utc=start_utc, rate=1.0)

    # --- Herd from cattle_spawn block ---
    cows: list[Cow] = []
    for i, entry in enumerate(terrain_config.cattle_spawn):
        cow = Cow(
            id=f"cow_{i:03d}",
            tag=entry.tag,
            pos=entry.pos,
            paddock_id=entry.paddock,
            bcs=entry.bcs,
            thirst=rng.uniform(0.1, 0.4),
            hunger=rng.uniform(0.1, 0.3),
            pregnancy_days_remaining=entry.pregnancy_days_remaining if entry.pregnant else None,
        )
        cows.append(cow)

    herd_rng = random.Random(rng.randint(0, 2**31))
    herd = Herd(cows=cows, rng=herd_rng)

    # --- Predator spawner ---
    pred_rng = random.Random(rng.randint(0, 2**31))
    predator_spawner = PredatorSpawner(rng=pred_rng)

    # --- Weather ---
    weather_driver = WeatherDriver()

    return World(
        clock=clock,
        terrain=terrain,
        herd=herd,
        predator_spawner=predator_spawner,
        weather_driver=weather_driver,
    )
