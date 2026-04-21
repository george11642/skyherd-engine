"""Wiring test — spin up all 4 MCP servers and assert every tool is registered."""

from __future__ import annotations

from collections import deque

from skyherd.drone.stub import StubBackend
from skyherd.mcp import (
    create_drone_mcp_server,
    create_galileo_mcp_server,
    create_rancher_mcp_server,
    create_sensor_mcp_server,
)

# ---------------------------------------------------------------------------
# Expected tool names per server
# ---------------------------------------------------------------------------

_DRONE_TOOLS = {"launch_drone", "return_to_home", "play_deterrent", "get_thermal_clip", "drone_status"}
_SENSOR_TOOLS = {"get_latest_readings", "get_camera_clip", "get_thermal_clip", "subscribe_anomalies"}
_RANCHER_TOOLS = {"page_rancher", "page_vet", "get_rancher_preferences"}
_GALILEO_TOOLS = {"get_drone_position", "get_cattle_positions", "distance_between"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snapshot(cows=None):
    class _Snap:
        def __init__(self, c):
            self.cows = c or []

    return _Snap(cows or [])


async def _list_tools_for(server) -> set[str]:
    from mcp.types import ListToolsRequest

    inst = server["instance"]
    result = await inst.request_handlers[ListToolsRequest](ListToolsRequest(method="tools/list"))
    return {t.name for t in result.root.tools}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAllServersRegisterCorrectTools:
    async def test_drone_tools(self):
        backend = StubBackend()
        server = create_drone_mcp_server(backend=backend)
        registered = await _list_tools_for(server)
        assert _DRONE_TOOLS == registered

    async def test_sensor_tools(self):
        bus: dict = {k: deque() for k in ["trough_cam", "thermal", "water_pressure", "collar_gps"]}
        server = create_sensor_mcp_server(bus_state=bus)
        registered = await _list_tools_for(server)
        assert _SENSOR_TOOLS == registered

    async def test_rancher_tools(self):
        server = create_rancher_mcp_server()
        registered = await _list_tools_for(server)
        assert _RANCHER_TOOLS == registered

    async def test_galileo_tools(self):
        server = create_galileo_mcp_server(world_snapshot_fn=lambda: _make_snapshot())
        registered = await _list_tools_for(server)
        assert _GALILEO_TOOLS == registered


class TestServerNamesAndTypes:
    def test_drone_server_name(self):
        assert create_drone_mcp_server(backend=StubBackend())["name"] == "drone"

    def test_sensor_server_name(self):
        assert create_sensor_mcp_server(bus_state={})["name"] == "sensor"

    def test_rancher_server_name(self):
        assert create_rancher_mcp_server()["name"] == "rancher"

    def test_galileo_server_name(self):
        assert create_galileo_mcp_server(world_snapshot_fn=lambda: _make_snapshot())["name"] == "galileo"

    def test_all_types_are_sdk(self):
        servers = [
            create_drone_mcp_server(backend=StubBackend()),
            create_sensor_mcp_server(bus_state={}),
            create_rancher_mcp_server(),
            create_galileo_mcp_server(world_snapshot_fn=lambda: _make_snapshot()),
        ]
        for s in servers:
            assert s["type"] == "sdk", f"{s['name']} has type {s['type']!r}, expected 'sdk'"


class TestAllToolsRegisteredAcrossAllServers:
    async def test_combined_tool_count(self):
        backend = StubBackend()
        bus: dict = {}
        drone = create_drone_mcp_server(backend=backend)
        sensor = create_sensor_mcp_server(bus_state=bus)
        rancher = create_rancher_mcp_server()
        galileo = create_galileo_mcp_server(world_snapshot_fn=lambda: _make_snapshot())

        all_tools: set[str] = set()
        for srv in [drone, sensor, rancher, galileo]:
            all_tools |= await _list_tools_for(srv)

        expected = _DRONE_TOOLS | _SENSOR_TOOLS | _RANCHER_TOOLS | _GALILEO_TOOLS
        # All expected tools should be present (sensor + drone both have get_thermal_clip)
        assert expected == all_tools

    async def test_server_instances_are_independent(self):
        """Two drone server instances should have independent state."""
        b1, b2 = StubBackend(), StubBackend()
        s1 = create_drone_mcp_server(backend=b1)
        s2 = create_drone_mcp_server(backend=b2)
        tools1 = await _list_tools_for(s1)
        tools2 = await _list_tools_for(s2)
        assert tools1 == tools2  # Same tool names
        assert s1["instance"] is not s2["instance"]  # Different instances
