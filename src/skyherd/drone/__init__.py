"""
skyherd.drone — drone backend abstraction layer.

Public API::

    from skyherd.drone import DroneBackend, DroneState, Waypoint, get_backend

    backend = get_backend("stub")   # or "sitl", or via DRONE_BACKEND env var
    await backend.connect()
    await backend.takeoff(alt_m=30)
    await backend.patrol([Waypoint(lat=34.1, lon=-106.1, alt_m=30)])
    await backend.return_to_home()
    await backend.disconnect()
"""

from skyherd.drone.interface import (
    DroneBackend,
    DroneError,
    DroneState,
    DroneUnavailable,
    Waypoint,
    get_backend,
)

__all__ = [
    "DroneBackend",
    "DroneError",
    "DroneState",
    "DroneUnavailable",
    "Waypoint",
    "get_backend",
]
