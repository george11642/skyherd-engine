"""
Galileo MCP server — centimetre-precision positioning via sim collar + drone state.

All position data comes from an injected ``world_snapshot_fn`` callable (tests
pass a stub; production passes ``world.snapshot``).  Haversine + ECEF helpers
live here so the module is importable standalone with no sim dependency.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

# ---------------------------------------------------------------------------
# Positioning helpers
# ---------------------------------------------------------------------------

_EARTH_R_M = 6_371_000.0  # mean Earth radius in metres


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in metres between two WGS84 points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_R_M * math.asin(math.sqrt(a))


def _ecef(lat: float, lon: float, alt_m: float = 0.0) -> tuple[float, float, float]:
    """Convert geodetic coordinates to ECEF (X, Y, Z) in metres."""
    phi = math.radians(lat)
    lam = math.radians(lon)
    # WGS84 semi-major / semi-minor axes
    a = 6_378_137.0
    b = 6_356_752.3142
    e2 = 1 - (b / a) ** 2
    n_radius = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    x = (n_radius + alt_m) * math.cos(phi) * math.cos(lam)
    y = (n_radius + alt_m) * math.cos(phi) * math.sin(lam)
    z = (n_radius * (1 - e2) + alt_m) * math.sin(phi)
    return x, y, z


def _ecef_distance_m(p1: tuple[float, float, float], p2: tuple[float, float, float]) -> float:
    """Euclidean distance between two ECEF points in metres."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2, strict=True)))


def _accuracy_cm(in_air: bool, canopy_cover: float = 0.0) -> float:
    """Return simulated Galileo accuracy.  5 cm ideal, 25 cm under heavy canopy."""
    base = 5.0
    canopy_penalty = canopy_cover * 20.0  # 0–1 → 0–20 cm penalty
    flight_penalty = 0.0 if in_air else 2.0  # slight penalty on ground
    return round(base + canopy_penalty + flight_penalty, 1)


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------


def _build_tools(
    world_snapshot_fn: Callable[[], Any],
    drone_state_fn: Callable[[], Any] | None,
) -> list[Any]:
    """Return SdkMcpTool list bound to the snapshot callables."""

    @tool(
        "get_drone_position",
        "Return the drone's current GPS position with Galileo accuracy estimate.",
        {},
    )
    async def get_drone_position(args: dict[str, Any]) -> dict[str, Any]:
        """Fetch drone lat/lon/alt from backend state; returns accuracy_cm from sim model."""
        if drone_state_fn is not None:
            try:
                state = await drone_state_fn()
                lat = float(state.lat)
                lon = float(state.lon)
                alt_m = float(state.altitude_m)
                in_air = bool(state.in_air)
            except Exception:  # noqa: BLE001
                lat, lon, alt_m, in_air = 34.0, -106.0, 0.0, False
        else:
            lat, lon, alt_m, in_air = 34.0, -106.0, 0.0, False

        acc_cm = _accuracy_cm(in_air)

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Drone @ ({lat:.6f}, {lon:.6f}) alt={alt_m:.1f}m acc={acc_cm}cm",
                }
            ],
            "lat": lat,
            "lon": lon,
            "alt_m": alt_m,
            "accuracy_cm": acc_cm,
        }

    @tool(
        "get_cattle_positions",
        "Return GPS positions for all (or specified) cattle based on collar data.",
        {
            "type": "object",
            "properties": {
                "tags": {"anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}], "description": "Tag IDs to filter; omit or null for all"},
            },
            "required": [],
        },
    )
    async def get_cattle_positions(args: dict[str, Any]) -> dict[str, Any]:
        """Retrieve collar positions for named cattle tags (or all cows if tags is None)."""
        tags_filter: list[str] | None = args.get("tags") or None

        snap = world_snapshot_fn()
        cows: list[dict[str, Any]] = snap.cows if hasattr(snap, "cows") else snap.get("cows", [])

        results: list[dict[str, Any]] = []
        for cow in cows:
            tag = cow.get("tag", "")
            if tags_filter is not None and tag not in tags_filter:
                continue

            pos = cow.get("pos", (0.0, 0.0))
            lat = float(pos[0]) if isinstance(pos, (list, tuple)) else float(pos.get("lat", 0.0))
            lon = float(pos[1]) if isinstance(pos, (list, tuple)) else float(pos.get("lon", 0.0))

            # Sim collar positions are in ranch-local metres; treat them as
            # lat/lon offsets from a reference origin (ranch SW corner at 34°N, 106°W).
            # Scale: 1 degree lat ≈ 111 320 m
            ref_lat, ref_lon = 34.0, -106.0
            lat_deg = ref_lat + lat / 111_320.0
            lon_deg = ref_lon + lon / (111_320.0 * math.cos(math.radians(ref_lat)))

            acc_cm = _accuracy_cm(in_air=False, canopy_cover=0.1)

            results.append(
                {
                    "tag": tag,
                    "lat": round(lat_deg, 8),
                    "lon": round(lon_deg, 8),
                    "alt_m": 0.0,
                    "accuracy_cm": acc_cm,
                    "paddock_id": cow.get("paddock_id", ""),
                }
            )

        return {
            "content": [
                {"type": "text", "text": f"Returned {len(results)} cattle positions"}
            ],
            "positions": results,
            "count": len(results),
        }

    @tool(
        "distance_between",
        "Calculate haversine + ECEF distance in metres between two collar-tagged cattle.",
        {"tag_a": str, "tag_b": str},
    )
    async def distance_between(args: dict[str, Any]) -> dict[str, Any]:
        """Compute haversine and ECEF 3-D distance between two tagged cattle; returns metres."""
        tag_a = str(args.get("tag_a", ""))
        tag_b = str(args.get("tag_b", ""))

        snap = world_snapshot_fn()
        cows: list[dict[str, Any]] = snap.cows if hasattr(snap, "cows") else snap.get("cows", [])

        ref_lat, ref_lon = 34.0, -106.0

        def _find(tag: str) -> dict[str, Any] | None:
            for c in cows:
                if c.get("tag") == tag:
                    return c
            return None

        cow_a = _find(tag_a)
        cow_b = _find(tag_b)

        if cow_a is None or cow_b is None:
            missing = tag_a if cow_a is None else tag_b
            return {
                "content": [
                    {"type": "text", "text": f"Tag not found: {missing}"}
                ],
                "is_error": True,
            }

        def _to_latlon(c: dict[str, Any]) -> tuple[float, float]:
            pos = c.get("pos", (0.0, 0.0))
            x = float(pos[0]) if isinstance(pos, (list, tuple)) else 0.0
            y = float(pos[1]) if isinstance(pos, (list, tuple)) else 0.0
            lat = ref_lat + x / 111_320.0
            lon = ref_lon + y / (111_320.0 * math.cos(math.radians(ref_lat)))
            return lat, lon

        la, loa = _to_latlon(cow_a)
        lb, lob = _to_latlon(cow_b)

        hav_m = _haversine_m(la, loa, lb, lob)
        ecef_m = _ecef_distance_m(_ecef(la, loa), _ecef(lb, lob))

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Distance {tag_a}↔{tag_b}: "
                        f"haversine={hav_m:.2f}m ECEF={ecef_m:.2f}m"
                    ),
                }
            ],
            "tag_a": tag_a,
            "tag_b": tag_b,
            "haversine_m": round(hav_m, 4),
            "ecef_m": round(ecef_m, 4),
        }

    return [get_drone_position, get_cattle_positions, distance_between]


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def create_galileo_mcp_server(
    world_snapshot_fn: Callable[[], Any] | None = None,
    drone_state_fn: Callable[[], Any] | None = None,
) -> McpSdkServerConfig:
    """Create a Galileo positioning MCP server.

    Args:
        world_snapshot_fn: Zero-arg callable returning a WorldSnapshot or compatible
            dict.  Defaults to importing the global World singleton if None.
        drone_state_fn: Async callable returning DroneState.  Defaults to None
            (uses static fallback coords).

    Returns:
        McpSdkServerConfig for use with ClaudeAgentOptions.mcp_servers.
    """
    if world_snapshot_fn is None:
        # Attempt to get a lazy reference — avoids import-time world construction.
        def _default_snapshot() -> Any:
            try:
                from pathlib import Path  # noqa: PLC0415

                from skyherd.world.world import make_world  # noqa: PLC0415

                _w = make_world(seed=42, config_path=Path("config/ranch.yaml"))
                return _w.snapshot()
            except Exception:  # noqa: BLE001
                # Return a minimal stub snapshot dict
                return {"cows": [], "predators": []}

        world_snapshot_fn = _default_snapshot

    tools = _build_tools(world_snapshot_fn, drone_state_fn)
    return create_sdk_mcp_server(name="galileo", version="1.0.0", tools=tools)
