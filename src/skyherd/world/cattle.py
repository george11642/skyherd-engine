"""Cattle — Cow dataclass and Herd stepping logic."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from skyherd.world.terrain import Terrain
    from skyherd.world.weather import Weather

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_THIRST_RATE_PER_S = 1.0 / (6 * 3600)  # full thirst in ~6 hours
_HUNGER_RATE_PER_S = 1.0 / (12 * 3600)  # full hunger in ~12 hours
_BCS_DECAY_RATE = 0.001 / 3600  # BCS drops 0.001 per hour when not fed
_DRINK_RESTORE = 0.9  # thirst restored to this level after drinking
_DRINK_THRESHOLD = 0.7  # cow seeks water above this thirst level
_DRINK_PROXIMITY_M = 10.0  # how close a cow must be to trough to drink
_WALK_SPEED_M_S = 0.5  # typical walking speed (m/s)
_WANDER_ANGLE_DEG = 30.0  # max random heading deviation per step


class Cow(BaseModel):
    """Per-animal state.  All fields are immutable-style (produce new copies on mutation).

    Positions are in metres relative to ranch origin (SW corner).
    """

    id: str
    tag: str
    pos: tuple[float, float]
    heading_deg: float = 0.0
    paddock_id: str = ""
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    thirst: float = Field(default=0.2, ge=0.0, le=1.0)
    hunger: float = Field(default=0.1, ge=0.0, le=1.0)
    bcs: float = Field(default=5.0, ge=1.0, le=9.0)
    pregnancy_days_remaining: int | None = None
    lameness_score: int = Field(default=0, ge=0, le=5)
    ocular_discharge: float = Field(default=0.0, ge=0.0, le=1.0)
    disease_flags: set[str] = Field(default_factory=set)
    last_drink_ts: float = 0.0  # sim_time_s when last drank
    last_feed_ts: float = 0.0  # sim_time_s when last fed

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Herd
# ---------------------------------------------------------------------------


class Herd:
    """Collection of cows with a deterministic step function.

    All randomness flows through *rng*; no global random state is used.
    """

    def __init__(self, cows: list[Cow], rng: random.Random) -> None:
        self.cows: list[Cow] = list(cows)
        self.rng = rng

    # ------------------------------------------------------------------
    # Stepping
    # ------------------------------------------------------------------

    def step(
        self,
        dt: float,
        terrain: Terrain,
        weather: Weather,
        sim_time_s: float,
    ) -> list[dict]:
        """Advance all cows by *dt* sim-seconds; return list of emitted event dicts."""
        events: list[dict] = []
        updated: list[Cow] = []

        for cow in self.cows:
            new_cow, cow_events = self._step_cow(cow, dt, terrain, weather, sim_time_s)
            updated.append(new_cow)
            events.extend(cow_events)

        self.cows = updated
        return events

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _step_cow(
        self,
        cow: Cow,
        dt: float,
        terrain: Terrain,
        weather: Weather,
        sim_time_s: float,
    ) -> tuple[Cow, list[dict]]:
        events: list[dict] = []
        data = cow.model_dump()

        # --- Physiological decay ---
        new_thirst = min(1.0, data["thirst"] + _THIRST_RATE_PER_S * dt)
        new_hunger = min(1.0, data["hunger"] + _HUNGER_RATE_PER_S * dt)

        # BCS decays if not fed recently (more than 24h without feed)
        hours_without_feed = (sim_time_s - data["last_feed_ts"]) / 3600.0
        if hours_without_feed > 24.0:
            new_bcs = max(1.0, data["bcs"] - _BCS_DECAY_RATE * dt)
        else:
            new_bcs = data["bcs"]

        data["thirst"] = new_thirst
        data["hunger"] = new_hunger
        data["bcs"] = new_bcs

        # --- Movement ---
        new_pos, new_heading = self._move_cow(
            pos=data["pos"],
            heading_deg=data["heading_deg"],
            thirst=new_thirst,
            terrain=terrain,
            dt=dt,
        )
        data["pos"] = new_pos
        data["heading_deg"] = new_heading

        # --- Update paddock_id ---
        pid = terrain.in_paddock(new_pos)
        if pid is not None:
            data["paddock_id"] = pid

        # --- Drinking ---
        trough = terrain.nearest_trough(new_pos)
        if trough is not None:
            dist_to_trough = math.sqrt(
                (new_pos[0] - trough.pos[0]) ** 2 + (new_pos[1] - trough.pos[1]) ** 2
            )
            if dist_to_trough <= _DRINK_PROXIMITY_M and new_thirst > 0.3:
                data["thirst"] = max(0.0, 1.0 - _DRINK_RESTORE)  # → ~0.1
                data["last_drink_ts"] = sim_time_s
                events.append(
                    {
                        "type": "cow.drank",
                        "cow_id": cow.id,
                        "tag": cow.tag,
                        "trough_id": trough.id,
                        "sim_time_s": sim_time_s,
                    }
                )

        # --- Lameness check ---
        if data["lameness_score"] >= 3:
            events.append(
                {
                    "type": "cow.lame",
                    "cow_id": cow.id,
                    "tag": cow.tag,
                    "lameness_score": data["lameness_score"],
                    "sim_time_s": sim_time_s,
                }
            )

        return Cow(**data), events

    def _move_cow(
        self,
        pos: tuple[float, float],
        heading_deg: float,
        thirst: float,
        terrain: Terrain,
        dt: float,
    ) -> tuple[tuple[float, float], float]:
        """Compute new position using random-walk-with-drift toward trough when thirsty."""
        if thirst >= _DRINK_THRESHOLD:
            # Biased walk: aim toward nearest trough
            trough = terrain.nearest_trough(pos)
            if trough is not None:
                dx = trough.pos[0] - pos[0]
                dy = trough.pos[1] - pos[1]
                target_heading = math.degrees(math.atan2(dy, dx))
                # Blend current heading toward target with small random noise
                noise = self.rng.uniform(-_WANDER_ANGLE_DEG, _WANDER_ANGLE_DEG)
                new_heading = target_heading + noise * 0.3
            else:
                new_heading = heading_deg + self.rng.uniform(-_WANDER_ANGLE_DEG, _WANDER_ANGLE_DEG)
        else:
            # Pure random wander
            new_heading = heading_deg + self.rng.uniform(-_WANDER_ANGLE_DEG, _WANDER_ANGLE_DEG)

        # Clamp heading to [0, 360)
        new_heading = new_heading % 360.0

        # Apply speed (lameness could reduce this, but keep simple)
        speed = _WALK_SPEED_M_S
        dist = speed * dt
        rad = math.radians(new_heading)
        new_x = pos[0] + dist * math.cos(rad)
        new_y = pos[1] + dist * math.sin(rad)

        # Clamp to ranch bounds
        w, h = terrain.config.bounds_m
        new_x = max(0.0, min(w, new_x))
        new_y = max(0.0, min(h, new_y))

        return (new_x, new_y), new_heading

    def centroid(self) -> tuple[float, float]:
        """Return the mean position of the herd."""
        if not self.cows:
            return (0.0, 0.0)
        xs = [c.pos[0] for c in self.cows]
        ys = [c.pos[1] for c in self.cows]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
