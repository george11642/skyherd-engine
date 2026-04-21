"""
Drone abstraction layer — interface, data types, and backend factory.

All drone operations are async. Concrete backends implement DroneBackend;
``get_backend()`` reads DRONE_BACKEND env var and dispatches to the right impl.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class Waypoint(BaseModel):
    """A single geographic waypoint for a patrol or goto operation."""

    lat: float
    lon: float
    alt_m: float
    hold_s: float = 0.0


@dataclass
class DroneState:
    """Snapshot of current drone state, returned by :py:meth:`DroneBackend.state`."""

    armed: bool = False
    in_air: bool = False
    altitude_m: float = 0.0
    battery_pct: float = 100.0
    mode: str = "UNKNOWN"
    lat: float = 0.0
    lon: float = 0.0


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DroneError(Exception):
    """Base exception for all drone errors."""


class DroneUnavailable(DroneError):
    """Raised when the drone (or SITL) cannot be reached."""


# ---------------------------------------------------------------------------
# Abstract backend
# ---------------------------------------------------------------------------


class DroneBackend(ABC):
    """
    Abstract async drone backend.

    Every public method must be awaited.  Implementations must be safe
    to construct without side effects; side effects happen only in
    ``connect()``.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the drone or simulator."""

    @abstractmethod
    async def takeoff(self, alt_m: float = 30.0) -> None:
        """Arm and take off to *alt_m* metres AGL."""

    @abstractmethod
    async def patrol(self, waypoints: list[Waypoint]) -> None:
        """Upload and execute a mission visiting each waypoint in order."""

    @abstractmethod
    async def return_to_home(self) -> None:
        """Command return-to-launch and wait for landing."""

    @abstractmethod
    async def play_deterrent(self, tone_hz: int = 12000, duration_s: float = 6.0) -> None:
        """
        Activate acoustic deterrent.

        On the ground: plays a .wav via system audio (stubbed in sim).
        In the air: logs to event bus; simulates an 8-s hold at current position.
        """

    @abstractmethod
    async def get_thermal_clip(self, duration_s: float = 10.0) -> Path:
        """
        Capture or synthesise a thermal image sequence.

        Returns the path to the first frame (PNG) of the clip.
        Real hardware returns an actual thermal frame; sim composites a
        synthetic IR frame via PIL.
        """

    @abstractmethod
    async def state(self) -> DroneState:
        """Return a fresh :class:`DroneState` snapshot."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanly disconnect from the drone or simulator."""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, type[DroneBackend]] = {}


def _register(name: str, cls: type[DroneBackend]) -> None:
    _REGISTRY[name] = cls


def get_backend(name: str | None = None) -> DroneBackend:
    """
    Return an uninitialised :class:`DroneBackend` instance.

    Resolution order:
    1. *name* argument (if provided)
    2. ``DRONE_BACKEND`` environment variable
    3. Defaults to ``"sitl"``

    Call :py:meth:`DroneBackend.connect` to open the connection.
    """
    backend_name = name or os.environ.get("DRONE_BACKEND", "sitl")

    # Lazy imports so callers that only use StubBackend never pull mavsdk.
    if backend_name not in _REGISTRY:
        if backend_name == "sitl":
            from skyherd.drone.sitl import SitlBackend  # noqa: PLC0415

            _register("sitl", SitlBackend)
        elif backend_name == "stub":
            from skyherd.drone.stub import StubBackend  # noqa: PLC0415

            _register("stub", StubBackend)
        else:
            raise DroneError(
                f"Unknown drone backend {backend_name!r}. "
                f"Available: {sorted(_REGISTRY) or ['sitl', 'stub']}"
            )

    cls = _REGISTRY[backend_name]
    return cls()
