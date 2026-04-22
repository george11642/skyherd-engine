"""
Shared safety guards for all drone backends.

Three independent guards that both MavicBackend and F3InavBackend invoke
before any actuator call:

  - GeofenceChecker  — validates waypoints against a ranch polygon loaded
                       from ``worlds/<ranch>.yaml``.
  - BatteryGuard     — triggers RTH at 25 % per battery-economics.md.
  - WindGuard        — vetoes takeoff above a platform-specific ceiling.

All guards raise :class:`~skyherd.drone.interface.DroneError` subclasses
so backends can surface informative messages without boilerplate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from skyherd.drone.interface import DroneError, Waypoint

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GeofenceViolation(DroneError):
    """Raised when a waypoint falls outside the ranch geofence polygon."""


class BatteryTooLow(DroneError):
    """Raised when battery is below the minimum threshold for the operation."""


class WindTooHigh(DroneError):
    """Raised when measured wind speed exceeds the platform's ceiling."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# RTH trigger from battery-economics.md
_BATTERY_RTH_THRESHOLD_PCT: float = 25.0
# Minimum for takeoff — slightly higher than RTH so we don't take off then RTH
_BATTERY_MIN_TAKEOFF_PCT: float = 30.0

# Default wind ceilings (knots) per platform
WIND_CEILING_MAVIC_KT: float = 21.0
WIND_CEILING_F3_KT: float = 18.0


# ---------------------------------------------------------------------------
# Geofence
# ---------------------------------------------------------------------------


def _point_in_polygon(lat: float, lon: float, polygon: list[tuple[float, float]]) -> bool:
    """
    Ray-casting point-in-polygon test using (lat, lon) geographic coordinates.

    ``polygon`` is a list of (lat, lon) tuples forming a closed ring.
    Returns True if the point is inside (or on the boundary of) the polygon.
    """
    n = len(polygon)
    inside = False
    px, py = lat, lon
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


class GeofenceChecker:
    """
    Validates waypoints against a geofence polygon loaded from a YAML world
    file.

    The YAML file must contain a top-level ``geofence`` key with a list of
    ``[lat, lon]`` pairs::

        geofence:
          - [34.05, -106.10]
          - [34.10, -106.10]
          - [34.10, -106.05]
          - [34.05, -106.05]

    If no ``geofence`` key is present the checker is a no-op (all waypoints
    pass).  This lets existing world files that only define local-metre
    coordinates operate without changes.

    Parameters
    ----------
    world_name:
        Base name of the YAML file under ``worlds/`` (e.g. ``"ranch_a"``).
    worlds_dir:
        Override for the worlds directory (defaults to ``<repo-root>/worlds``).
    """

    def __init__(
        self,
        world_name: str = "ranch_a",
        worlds_dir: Path | None = None,
    ) -> None:
        self._world_name = world_name
        self._polygon: list[tuple[float, float]] | None = None
        self._loaded = False

        if worlds_dir is None:
            # Resolve relative to this file: src/skyherd/drone/safety.py
            # → repo root is 4 levels up
            worlds_dir = Path(__file__).parent.parent.parent.parent / "worlds"

        self._worlds_dir = worlds_dir

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        yaml_path = self._worlds_dir / f"{self._world_name}.yaml"
        if not yaml_path.exists():
            logger.warning(
                "GeofenceChecker: world file %s not found — geofence disabled",
                yaml_path,
            )
            self._polygon = None
            self._loaded = True
            return

        with yaml_path.open() as fh:
            data: dict[str, Any] = yaml.safe_load(fh)

        raw = data.get("geofence")
        if raw is None:
            logger.info(
                "GeofenceChecker: no 'geofence' key in %s — geofence disabled",
                yaml_path,
            )
            self._polygon = None
            self._loaded = True
            return

        # raw is a list of [lat, lon] pairs
        self._polygon = [(float(pt[0]), float(pt[1])) for pt in raw]
        logger.info(
            "GeofenceChecker: loaded %d-point polygon from %s",
            len(self._polygon),
            yaml_path,
        )
        self._loaded = True

    def check_waypoint(self, waypoint: Waypoint) -> None:
        """
        Raise :class:`GeofenceViolation` if the waypoint is outside the
        polygon.  A no-op if no geofence polygon is configured.
        """
        self._ensure_loaded()
        if self._polygon is None:
            return

        if not _point_in_polygon(waypoint.lat, waypoint.lon, self._polygon):
            raise GeofenceViolation(
                f"Waypoint ({waypoint.lat:.6f}, {waypoint.lon:.6f}) is outside "
                f"the geofence for ranch '{self._world_name}'. "
                "Correct the mission or update the world YAML."
            )

    def check_waypoints(self, waypoints: list[Waypoint]) -> None:
        """Check every waypoint in the list; raises on the first violation."""
        for wp in waypoints:
            self.check_waypoint(wp)


# ---------------------------------------------------------------------------
# Battery guard
# ---------------------------------------------------------------------------


class BatteryGuard:
    """
    Checks battery level before operations and signals RTH when low.

    Parameters
    ----------
    rth_threshold_pct:
        Battery percentage at which RTH should be triggered (default 25 %).
    min_takeoff_pct:
        Minimum battery to allow takeoff (default 30 %).
    """

    def __init__(
        self,
        rth_threshold_pct: float = _BATTERY_RTH_THRESHOLD_PCT,
        min_takeoff_pct: float = _BATTERY_MIN_TAKEOFF_PCT,
    ) -> None:
        self.rth_threshold_pct = rth_threshold_pct
        self.min_takeoff_pct = min_takeoff_pct

    def check_takeoff(self, battery_pct: float) -> None:
        """
        Raise :class:`BatteryTooLow` if ``battery_pct`` is below the takeoff
        minimum.
        """
        if battery_pct < self.min_takeoff_pct:
            raise BatteryTooLow(
                f"Battery at {battery_pct:.1f} % — minimum for takeoff is "
                f"{self.min_takeoff_pct:.0f} %. Swap battery before launching."
            )

    def should_rth(self, battery_pct: float) -> bool:
        """
        Return True if the battery level warrants an immediate return-to-home.
        """
        return battery_pct <= self.rth_threshold_pct

    def check_in_flight(self, battery_pct: float) -> None:
        """
        Raise :class:`BatteryTooLow` if the in-flight battery has reached the
        RTH threshold.  Call periodically from the backend's state-monitoring
        loop.
        """
        if self.should_rth(battery_pct):
            raise BatteryTooLow(
                f"Battery at {battery_pct:.1f} % — RTH threshold "
                f"({self.rth_threshold_pct:.0f} %) reached. Returning to home."
            )


# ---------------------------------------------------------------------------
# Wind guard
# ---------------------------------------------------------------------------


@dataclass
class WindGuard:
    """
    Prevents takeoff when measured wind speed exceeds a platform ceiling.

    Parameters
    ----------
    ceiling_kt:
        Maximum wind speed in knots.  Use :py:data:`WIND_CEILING_MAVIC_KT`
        (21 kt) for the Mavic Air 2 or :py:data:`WIND_CEILING_F3_KT` (18 kt)
        for F3 quads.
    """

    ceiling_kt: float = WIND_CEILING_MAVIC_KT

    def check(self, wind_speed_kt: float) -> None:
        """
        Raise :class:`WindTooHigh` if ``wind_speed_kt`` exceeds the ceiling.
        """
        if wind_speed_kt > self.ceiling_kt:
            raise WindTooHigh(
                f"Wind at {wind_speed_kt:.1f} kt exceeds platform ceiling of "
                f"{self.ceiling_kt:.0f} kt. Takeoff vetoed until wind subsides."
            )
