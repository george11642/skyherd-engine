"""Terrain — static ranch geometry loaded from a YAML config."""

from __future__ import annotations

import math
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Config models (Pydantic v2)
# ---------------------------------------------------------------------------


class WaterTankConfig(BaseModel):
    id: str
    pos: tuple[float, float]
    capacity_l: float
    level_pct: float = 100.0
    pressure_psi: float = 45.0


class TroughConfig(BaseModel):
    id: str
    pos: tuple[float, float]
    paddock: str


class FenceLineConfig(BaseModel):
    id: str
    segment: list[tuple[float, float]]  # exactly 2 points: [(x0,y0),(x1,y1)]
    tag: str = ""


class PaddockConfig(BaseModel):
    id: str
    polygon: list[tuple[float, float]]


class BarnConfig(BaseModel):
    pos: tuple[float, float]


class CattleSpawnEntry(BaseModel):
    tag: str
    pos: tuple[float, float]
    paddock: str
    bcs: float = 5.0
    pregnant: bool = False
    pregnancy_days_remaining: int | None = None


class NeighborRef(BaseModel):
    """Reference to a neighbouring ranch and the shared fence segment IDs."""

    id: str  # e.g. "ranch_a"
    shared_fence: str  # cardinal direction of the shared boundary ("west", "east", …)
    shared_fence_segment_ids: list[str] = Field(default_factory=list)
    # e.g. ["ranch_a:fence_east", "ranch_b:fence_west"]


class TerrainConfig(BaseModel):
    name: str
    bounds_m: tuple[float, float]  # (width, height)
    paddocks: list[PaddockConfig] = Field(default_factory=list)
    water_tanks: list[WaterTankConfig] = Field(default_factory=list)
    troughs: list[TroughConfig] = Field(default_factory=list)
    fence_lines: list[FenceLineConfig] = Field(default_factory=list)
    barn: BarnConfig
    cattle_spawn: list[CattleSpawnEntry] = Field(default_factory=list)
    neighbors: list[NeighborRef] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> TerrainConfig:
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    """Ray-casting polygon containment test."""
    x, y = point
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _point_to_segment_dist(
    p: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> float:
    """Minimum distance from point *p* to segment *ab*."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0:
        return _dist(p, a)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len_sq))
    proj = (ax + t * dx, ay + t * dy)
    return _dist(p, proj)


# ---------------------------------------------------------------------------
# Terrain facade
# ---------------------------------------------------------------------------

_FENCE_BREACH_THRESHOLD_M = 2.0  # meters — cow this close to fence is flagged


class Terrain:
    """Wraps a :class:`TerrainConfig` and exposes spatial queries."""

    def __init__(self, config: TerrainConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Spatial queries
    # ------------------------------------------------------------------

    def in_paddock(self, pos: tuple[float, float]) -> str | None:
        """Return the paddock id that contains *pos*, or None if outside all."""
        for paddock in self.config.paddocks:
            if _point_in_polygon(pos, paddock.polygon):
                return paddock.id
        return None

    def nearest_trough(self, pos: tuple[float, float]) -> TroughConfig | None:
        """Return the nearest trough to *pos*, or None if no troughs exist."""
        best: TroughConfig | None = None
        best_d = float("inf")
        for trough in self.config.troughs:
            d = _dist(pos, trough.pos)
            if d < best_d:
                best_d = d
                best = trough
        return best

    def fence_breached_by(self, pos: tuple[float, float]) -> list[str]:
        """Return ids of fence lines whose segment is within breach threshold of *pos*."""
        breached: list[str] = []
        for fence in self.config.fence_lines:
            if len(fence.segment) < 2:
                continue
            a, b = fence.segment[0], fence.segment[1]
            d = _point_to_segment_dist(pos, a, b)
            if d <= _FENCE_BREACH_THRESHOLD_M:
                breached.append(fence.id)
        return breached

    def nearest_water_tank(self, pos: tuple[float, float]) -> WaterTankConfig | None:
        """Return the nearest water tank to *pos*."""
        best: WaterTankConfig | None = None
        best_d = float("inf")
        for tank in self.config.water_tanks:
            d = _dist(pos, tank.pos)
            if d < best_d:
                best_d = d
                best = tank
        return best
