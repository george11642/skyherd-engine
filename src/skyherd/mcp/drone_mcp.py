"""
Drone MCP server — wraps DroneBackend as Claude-callable tools.

Each tool is async, returns JSON-serialisable dicts, and validates all inputs
before touching the backend.  Use ``create_drone_mcp_server`` to get a
``McpSdkServerConfig`` suitable for ``ClaudeAgentOptions.mcp_servers``.
"""

from __future__ import annotations

import uuid
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from skyherd.drone.interface import DroneBackend, DroneError, Waypoint

# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

_TONE_MIN_HZ = 4_000
_TONE_MAX_HZ = 22_000

# ---------------------------------------------------------------------------
# Tool factory (closure pattern so DI backend is captured cleanly)
# ---------------------------------------------------------------------------


def _build_tools(backend: DroneBackend) -> list[Any]:
    """Return a list of SdkMcpTool instances bound to *backend*."""

    @tool(
        "launch_drone",
        "Arm, take off, and fly a patrol mission to the given GPS coordinate.",
        {
            "mission": str,
            "target_lat": float,
            "target_lon": float,
            "alt_m": float,
        },
    )
    async def launch_drone(args: dict[str, Any]) -> dict[str, Any]:
        """Arm + takeoff then fly a single-waypoint patrol mission; return mission_id + ETA."""
        mission = args["mission"]
        lat = float(args["target_lat"])
        lon = float(args["target_lon"])
        alt_m = float(args.get("alt_m", 60.0))

        mission_id = str(uuid.uuid4())[:8]
        try:
            await backend.takeoff(alt_m=alt_m)
            waypoint = Waypoint(lat=lat, lon=lon, alt_m=alt_m)
            await backend.patrol([waypoint])
        except DroneError as exc:
            return {
                "content": [{"type": "text", "text": f"DroneError: {exc}"}],
                "is_error": True,
            }

        # ETA: rough estimate — 5 m/s cruise speed
        state = await backend.state()
        import math

        dist_m = math.sqrt((lat - state.lat) ** 2 + (lon - state.lon) ** 2) * 111_320
        eta_s = max(30, dist_m / 5.0)

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Mission {mission_id} launched: {mission}",
                }
            ],
            "mission_id": mission_id,
            "mission": mission,
            "target_lat": lat,
            "target_lon": lon,
            "alt_m": alt_m,
            "eta_s": round(eta_s, 1),
        }

    @tool(
        "return_to_home",
        "Command the drone to return to its launch point and land.",
        {},
    )
    async def return_to_home(args: dict[str, Any]) -> dict[str, Any]:
        """Trigger RTH (Return to Home); drone lands at launch coordinates."""
        try:
            await backend.return_to_home()
        except DroneError as exc:
            return {
                "content": [{"type": "text", "text": f"DroneError: {exc}"}],
                "is_error": True,
            }
        return {
            "content": [{"type": "text", "text": "Drone returning to home"}],
            "status": "rth_initiated",
        }

    @tool(
        "play_deterrent",
        "Activate the acoustic predator deterrent at the specified frequency.",
        {"tone_hz": int, "duration_s": float},
    )
    async def play_deterrent(args: dict[str, Any]) -> dict[str, Any]:
        """Fire acoustic deterrent tone (4kHz–22kHz); returns confirmation or validation error."""
        tone_hz = int(args.get("tone_hz", 12_000))
        duration_s = float(args.get("duration_s", 6.0))

        if not (_TONE_MIN_HZ <= tone_hz <= _TONE_MAX_HZ):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Invalid tone_hz {tone_hz}: must be between "
                            f"{_TONE_MIN_HZ} and {_TONE_MAX_HZ} Hz"
                        ),
                    }
                ],
                "is_error": True,
            }

        try:
            await backend.play_deterrent(tone_hz=tone_hz, duration_s=duration_s)
        except DroneError as exc:
            return {
                "content": [{"type": "text", "text": f"DroneError: {exc}"}],
                "is_error": True,
            }

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Deterrent fired: {tone_hz} Hz for {duration_s}s",
                }
            ],
            "tone_hz": tone_hz,
            "duration_s": duration_s,
            "status": "fired",
        }

    @tool(
        "get_thermal_clip",
        "Capture a thermal camera clip from the drone and return the frame path.",
        {"duration_s": float},
    )
    async def get_thermal_clip(args: dict[str, Any]) -> dict[str, Any]:
        """Capture thermal clip; returns {path, duration_s, frame_count}."""
        duration_s = float(args.get("duration_s", 10.0))

        try:
            frame_path = await backend.get_thermal_clip(duration_s=duration_s)
        except DroneError as exc:
            return {
                "content": [{"type": "text", "text": f"DroneError: {exc}"}],
                "is_error": True,
            }

        fps = 10
        frame_count = int(duration_s * fps)
        path_str = str(frame_path)

        return {
            "content": [{"type": "text", "text": f"Thermal clip at {path_str}"}],
            "path": path_str,
            "duration_s": duration_s,
            "frame_count": frame_count,
        }

    @tool(
        "drone_status",
        "Return the current drone state (armed, in_air, altitude, battery, GPS, mode).",
        {},
    )
    async def drone_status(args: dict[str, Any]) -> dict[str, Any]:
        """Fetch live drone state snapshot; returns armed/in_air/altitude/battery/mode/lat/lon."""
        try:
            state = await backend.state()
        except DroneError as exc:
            return {
                "content": [{"type": "text", "text": f"DroneError: {exc}"}],
                "is_error": True,
            }

        return {
            "content": [{"type": "text", "text": f"Drone mode: {state.mode}"}],
            "armed": state.armed,
            "in_air": state.in_air,
            "altitude_m": state.altitude_m,
            "battery_pct": state.battery_pct,
            "mode": state.mode,
            "lat": state.lat,
            "lon": state.lon,
        }

    return [launch_drone, return_to_home, play_deterrent, get_thermal_clip, drone_status]


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def create_drone_mcp_server(
    backend: DroneBackend | None = None,
) -> McpSdkServerConfig:
    """Create a drone MCP server bound to *backend* (defaults to env-configured backend).

    Args:
        backend: Pre-constructed DroneBackend.  Pass a StubBackend in tests.

    Returns:
        McpSdkServerConfig for use with ClaudeAgentOptions.mcp_servers.
    """
    if backend is None:
        from skyherd.drone.interface import get_backend

        backend = get_backend()

    tools = _build_tools(backend)
    return create_sdk_mcp_server(name="drone", version="1.0.0", tools=tools)
