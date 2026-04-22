"""
Sensor MCP server — exposes in-memory sensor history as Claude-callable tools.

Bus state is an optional ``dict[str, deque]`` injected at construction time so
tests can supply synthetic readings without a live sensor bus.  If the real
``skyherd.sensors.bus`` module is available it is used; otherwise a stub is
created automatically.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

# ---------------------------------------------------------------------------
# Default stub bus state
# ---------------------------------------------------------------------------

_KIND_FIELDS: dict[str, list[str]] = {
    "water_pressure": ["tank_id", "pressure_psi", "level_pct"],
    "trough_cam": ["cam_id", "frame_path", "cows_seen", "anomalies"],
    "thermal": ["cam_id", "frame_path", "hot_spots"],
    "collar_gps": ["tag", "lat", "lon", "alt_m"],
    "collar_imu": ["tag", "accel_x", "accel_y", "accel_z"],
    "acoustic": ["event", "db_level"],
    "weather": ["temp_f", "wind_kt", "conditions"],
    "fence_motion": ["fence_id", "motion_detected"],
}


def _make_default_bus_state() -> dict[str, deque]:  # type: ignore[type-arg]
    """Return an empty deque-per-kind bus state."""
    return {kind: deque(maxlen=200) for kind in _KIND_FIELDS}


def _try_load_bus() -> dict[str, deque] | None:  # type: ignore[type-arg]
    """Attempt to import the live sensor bus; return None if not yet present."""
    try:
        from skyherd.sensors.bus import get_bus_state  # type: ignore[import]

        return get_bus_state()
    except (ImportError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------


def _build_tools(bus: dict[str, deque]) -> list[Any]:  # type: ignore[type-arg]
    """Return SdkMcpTool list bound to *bus*."""

    @tool(
        "get_latest_readings",
        "Return the last N sensor readings, optionally filtered by sensor kind.",
        {
            "type": "object",
            "properties": {
                "sensor_kind": {
                    "type": "string",
                    "description": "Filter by sensor kind; omit for all kinds",
                },
                "ranch_id": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["ranch_id", "limit"],
        },
    )
    async def get_latest_readings(args: dict[str, Any]) -> dict[str, Any]:
        """Fetch last N sensor readings from the in-memory bus; returns list of reading dicts."""
        sensor_kind: str | None = args.get("sensor_kind") or None
        limit = int(args.get("limit", 20))

        readings: list[dict[str, Any]] = []

        if sensor_kind is not None:
            q = bus.get(sensor_kind)
            if q is not None:
                readings = list(q)[-limit:]
        else:
            # Mix from all kinds
            for kind, q in bus.items():
                for entry in list(q):
                    readings.append({"kind": kind, **entry})
            readings = readings[-limit:]

        return {
            "content": [{"type": "text", "text": f"Returning {len(readings)} readings"}],
            "readings": readings,
            "count": len(readings),
        }

    @tool(
        "get_camera_clip",
        "Return recent trough-cam frames with cow counts and anomaly flags.",
        {"cam_id": str, "seconds": int},
    )
    async def get_camera_clip(args: dict[str, Any]) -> dict[str, Any]:
        """Retrieve recent trough_cam frames for cam_id; returns frame_paths, cows_seen, anomalies."""
        cam_id = str(args.get("cam_id", ""))
        seconds = int(args.get("seconds", 30))

        q = bus.get("trough_cam", deque())
        frames = [r for r in q if r.get("cam_id") == cam_id][-seconds:]

        frame_paths = [r.get("frame_path", "") for r in frames]
        cows_seen = max((r.get("cows_seen", 0) for r in frames), default=0)
        anomalies: list[str] = []
        for r in frames:
            a = r.get("anomalies", [])
            if isinstance(a, list):
                anomalies.extend(a)

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Camera {cam_id}: {len(frame_paths)} frames, {cows_seen} cows",
                }
            ],
            "cam_id": cam_id,
            "frame_paths": frame_paths,
            "cows_seen": cows_seen,
            "anomalies": list(set(anomalies)),
        }

    @tool(
        "get_thermal_clip",
        "Return recent thermal camera frames with hot-spot data.",
        {"cam_id": str, "seconds": int},
    )
    async def get_thermal_clip(args: dict[str, Any]) -> dict[str, Any]:
        """Retrieve recent thermal frames for cam_id; returns frame_paths and hot_spots."""
        cam_id = str(args.get("cam_id", ""))
        seconds = int(args.get("seconds", 30))

        q = bus.get("thermal", deque())
        frames = [r for r in q if r.get("cam_id") == cam_id][-seconds:]

        frame_paths = [r.get("frame_path", "") for r in frames]
        hot_spots: list[dict[str, Any]] = []
        for r in frames:
            hs = r.get("hot_spots", [])
            if isinstance(hs, list):
                hot_spots.extend(hs)

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Thermal {cam_id}: {len(frame_paths)} frames",
                }
            ],
            "cam_id": cam_id,
            "frame_paths": frame_paths,
            "hot_spots": hot_spots,
        }

    @tool(
        "subscribe_anomalies",
        "Return recent anomaly events matching the given kind filter.",
        {"kind_filter": str},
    )
    async def subscribe_anomalies(args: dict[str, Any]) -> dict[str, Any]:
        """Fetch last N anomaly events matching kind_filter; returns list of event dicts."""
        kind_filter = str(args.get("kind_filter", ""))

        matched: list[dict[str, Any]] = []
        for kind, q in bus.items():
            if kind_filter and kind_filter not in kind:
                continue
            for entry in q:
                if entry.get("anomaly") or entry.get("anomalies"):
                    matched.append({"kind": kind, **entry})

        # Sort by sim_time_s if present
        matched.sort(key=lambda e: e.get("sim_time_s", 0))

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {len(matched)} anomaly events for filter '{kind_filter}'",
                }
            ],
            "events": matched,
            "count": len(matched),
        }

    return [get_latest_readings, get_camera_clip, get_thermal_clip, subscribe_anomalies]


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def create_sensor_mcp_server(
    bus_state: dict[str, deque] | None = None,  # type: ignore[type-arg]
) -> McpSdkServerConfig:
    """Create a sensor MCP server bound to *bus_state*.

    Args:
        bus_state: Dict of deques keyed by sensor kind.  If None, attempts to
            load the live bus; falls back to an empty stub.

    Returns:
        McpSdkServerConfig for use with ClaudeAgentOptions.mcp_servers.
    """
    if bus_state is None:
        bus_state = _try_load_bus() or _make_default_bus_state()

    tools = _build_tools(bus_state)
    return create_sdk_mcp_server(name="sensor", version="1.0.0", tools=tools)
