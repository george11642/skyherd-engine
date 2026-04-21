"""Predators — nocturnal predator entities and spawner."""

from __future__ import annotations

import math
import random
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from skyherd.world.cattle import Herd
    from skyherd.world.clock import Clock
    from skyherd.world.terrain import Terrain

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SPAWN_NIGHT_RATE = 0.008  # Poisson rate per second during night (≈1 arrival per ~125s)
_SPAWN_DAY_RATE = 0.0002  # Much lower during day
_PREDATOR_SPEED_M_S = 1.5  # m/s toward herd
_PREDATOR_WANDER_DEG = 20.0


class PredatorState(str, Enum):
    ROAMING = "roaming"
    APPROACHING = "approaching"
    ENGAGED = "engaged"
    FLEEING = "fleeing"


class PredatorSpecies(str, Enum):
    COYOTE = "coyote"
    MOUNTAIN_LION = "mountain-lion"
    WOLF = "wolf"


_SPECIES_SIZE_KG: dict[str, float] = {
    PredatorSpecies.COYOTE: 13.0,
    PredatorSpecies.MOUNTAIN_LION: 65.0,
    PredatorSpecies.WOLF: 45.0,
}

_SPECIES_THERMAL: dict[str, float] = {
    PredatorSpecies.COYOTE: 0.4,
    PredatorSpecies.MOUNTAIN_LION: 0.7,
    PredatorSpecies.WOLF: 0.6,
}


class Predator(BaseModel):
    """Per-predator entity state."""

    id: str
    species: PredatorSpecies
    pos: tuple[float, float]
    heading_deg: float = 0.0
    state: PredatorState = PredatorState.ROAMING
    size_kg: float = 13.0
    thermal_signature: float = 0.4  # 0–1 relative to ambient

    model_config = {"use_enum_values": True}


# ---------------------------------------------------------------------------
# Spawner
# ---------------------------------------------------------------------------


class PredatorSpawner:
    """Manages nocturnal Poisson arrivals of predators at the ranch boundary.

    Randomness is entirely seeded through *rng* — no global state.
    """

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.predators: list[Predator] = []
        self._next_id = 0

    # ------------------------------------------------------------------
    # Stepping
    # ------------------------------------------------------------------

    def step(
        self,
        dt: float,
        clock: Clock,
        terrain: Terrain,
        herd: Herd,
        sim_time_s: float,
    ) -> list[dict]:
        """Advance all predators and potentially spawn new ones; return events."""
        events: list[dict] = []

        # --- Maybe spawn ---
        rate = _SPAWN_NIGHT_RATE if clock.is_night() else _SPAWN_DAY_RATE
        # Poisson arrival: P(arrival in dt) ≈ rate * dt for small dt
        if self.rng.random() < rate * dt:
            predator, spawn_event = self._spawn(terrain, sim_time_s)
            self.predators.append(predator)
            events.append(spawn_event)

        # --- Move existing predators ---
        centroid = herd.centroid()
        updated: list[Predator] = []
        for pred in self.predators:
            new_pred = self._move_predator(pred, centroid, terrain, dt)
            updated.append(new_pred)
        self.predators = updated

        return events

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _spawn(self, terrain: Terrain, sim_time_s: float) -> tuple[Predator, dict]:
        """Spawn a predator at a random boundary point."""
        w, h = terrain.config.bounds_m
        # Pick a random edge: 0=N, 1=E, 2=S, 3=W
        edge = self.rng.randint(0, 3)
        if edge == 0:  # North
            pos = (self.rng.uniform(0, w), h)
        elif edge == 1:  # East
            pos = (w, self.rng.uniform(0, h))
        elif edge == 2:  # South
            pos = (self.rng.uniform(0, w), 0.0)
        else:  # West
            pos = (0.0, self.rng.uniform(0, h))

        # Weighted species selection
        species_weights = [
            (PredatorSpecies.COYOTE, 0.7),
            (PredatorSpecies.MOUNTAIN_LION, 0.2),
            (PredatorSpecies.WOLF, 0.1),
        ]
        species_choices = [s for s, _ in species_weights]
        weights = [w_ for _, w_ in species_weights]
        species = self.rng.choices(species_choices, weights=weights, k=1)[0]

        pred_id = f"pred_{self._next_id:04d}"
        self._next_id += 1

        predator = Predator(
            id=pred_id,
            species=species,
            pos=pos,
            heading_deg=self.rng.uniform(0, 360),
            state=PredatorState.ROAMING,
            size_kg=_SPECIES_SIZE_KG[species],
            thermal_signature=_SPECIES_THERMAL[species],
        )
        event = {
            "type": "predator.spawned",
            "predator_id": pred_id,
            "species": species,
            "pos": pos,
            "sim_time_s": sim_time_s,
        }
        return predator, event

    def _move_predator(
        self,
        pred: Predator,
        herd_centroid: tuple[float, float],
        terrain: Terrain,
        dt: float,
    ) -> Predator:
        """Move predator toward herd centroid with slight random deviation."""
        data = pred.model_dump()

        dx = herd_centroid[0] - pred.pos[0]
        dy = herd_centroid[1] - pred.pos[1]
        dist_to_herd = math.sqrt(dx * dx + dy * dy)

        if dist_to_herd > 50.0:
            # Approaching mode — bias toward herd
            target_heading = math.degrees(math.atan2(dy, dx))
            noise = self.rng.uniform(-_PREDATOR_WANDER_DEG, _PREDATOR_WANDER_DEG)
            new_heading = (target_heading + noise) % 360.0
            data["state"] = PredatorState.APPROACHING.value
        else:
            # Close to herd — engaged
            new_heading = pred.heading_deg
            data["state"] = PredatorState.ENGAGED.value

        dist = _PREDATOR_SPEED_M_S * dt
        rad = math.radians(new_heading)
        new_x = pred.pos[0] + dist * math.cos(rad)
        new_y = pred.pos[1] + dist * math.sin(rad)

        # Clamp to ranch bounds
        w, h = terrain.config.bounds_m
        new_x = max(0.0, min(w, new_x))
        new_y = max(0.0, min(h, new_y))

        data["pos"] = (new_x, new_y)
        data["heading_deg"] = new_heading

        return Predator(**data)
