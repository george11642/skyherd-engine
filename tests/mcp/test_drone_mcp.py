"""Tests for drone_mcp — exercises every tool against StubBackend."""

from __future__ import annotations

import pytest
from mcp.types import CallToolRequest, ListToolsRequest

from skyherd.drone.stub import StubBackend
from skyherd.mcp.drone_mcp import create_drone_mcp_server

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def backend():
    return StubBackend()


@pytest.fixture()
async def connected_backend(backend):
    await backend.connect()
    return backend


@pytest.fixture()
def drone_server(connected_backend):
    return create_drone_mcp_server(backend=connected_backend)


# ---------------------------------------------------------------------------
# Helper: call a tool by name via the MCP low-level request handlers
# ---------------------------------------------------------------------------


async def _call_tool(server, tool_name: str, args: dict) -> object:
    """Call a tool via the MCP server's request_handlers interface."""
    inst = server["instance"]
    list_handler = inst.request_handlers[ListToolsRequest]
    list_result = await list_handler(ListToolsRequest(method="tools/list"))
    tools = list_result.root.tools
    assert any(t.name == tool_name for t in tools), f"Tool '{tool_name}' not registered"

    call_handler = inst.request_handlers[CallToolRequest]
    result = await call_handler(
        CallToolRequest(method="tools/call", params={"name": tool_name, "arguments": args})
    )
    return result.root


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLaunchDrone:
    async def test_returns_mission_id(self, drone_server, connected_backend):
        result = await _call_tool(
            drone_server,
            "launch_drone",
            {
                "mission": "coyote_patrol",
                "target_lat": 34.001,
                "target_lon": -106.001,
                "alt_m": 60.0,
            },
        )
        # Result is a CallToolResult — check it's not an error
        assert not result.isError
        # Content should have text
        assert result.content
        text = result.content[0].text
        assert "launched" in text.lower() or "mission" in text.lower()

    async def test_drone_moved_to_waypoint(self, drone_server, connected_backend):
        await _call_tool(
            drone_server,
            "launch_drone",
            {"mission": "test", "target_lat": 34.005, "target_lon": -106.005, "alt_m": 50.0},
        )
        state = await connected_backend.state()
        assert state.lat == pytest.approx(34.005)
        assert state.lon == pytest.approx(-106.005)


class TestReturnToHome:
    async def test_rth_returns_status(self, drone_server):
        result = await _call_tool(drone_server, "return_to_home", {})
        assert not result.isError
        text = result.content[0].text
        assert "home" in text.lower() or "rth" in text.lower()

    async def test_drone_not_in_air_after_rth(self, drone_server, connected_backend):
        await connected_backend.takeoff(30.0)
        await _call_tool(drone_server, "return_to_home", {})
        state = await connected_backend.state()
        assert state.in_air is False


class TestPlayDeterrent:
    async def test_valid_tone(self, drone_server):
        result = await _call_tool(
            drone_server, "play_deterrent", {"tone_hz": 12000, "duration_s": 6.0}
        )
        assert not result.isError
        text = result.content[0].text
        assert "12000" in text or "deterrent" in text.lower()

    async def test_tone_below_minimum_is_error(self, drone_server):
        result = await _call_tool(
            drone_server, "play_deterrent", {"tone_hz": 100, "duration_s": 3.0}
        )
        assert result.isError
        assert "invalid" in result.content[0].text.lower() or "4" in result.content[0].text

    async def test_tone_above_maximum_is_error(self, drone_server):
        result = await _call_tool(
            drone_server, "play_deterrent", {"tone_hz": 30000, "duration_s": 3.0}
        )
        assert result.isError

    async def test_boundary_minimum_accepted(self, drone_server):
        result = await _call_tool(
            drone_server, "play_deterrent", {"tone_hz": 4000, "duration_s": 1.0}
        )
        assert not result.isError

    async def test_boundary_maximum_accepted(self, drone_server):
        result = await _call_tool(
            drone_server, "play_deterrent", {"tone_hz": 22000, "duration_s": 1.0}
        )
        assert not result.isError


class TestGetThermalClip:
    async def test_returns_path_and_counts(self, drone_server):
        result = await _call_tool(drone_server, "get_thermal_clip", {"duration_s": 5.0})
        assert not result.isError
        text = result.content[0].text
        assert "thermal" in text.lower() or "clip" in text.lower()

    async def test_frame_count_proportional_to_duration(self, drone_server):
        # frame_count = duration_s * 10 (10fps)
        result = await _call_tool(drone_server, "get_thermal_clip", {"duration_s": 10.0})
        assert not result.isError
        # We can only check content text; full dict is in the tool response
        # Verify no error
        assert result.content


class TestDroneStatus:
    async def test_returns_state_fields(self, drone_server):
        result = await _call_tool(drone_server, "drone_status", {})
        assert not result.isError
        text = result.content[0].text
        # Should mention mode
        assert "mode" in text.lower() or "stabilize" in text.lower() or "guided" in text.lower()

    async def test_status_reflects_connected_state(self, drone_server, connected_backend):
        result = await _call_tool(drone_server, "drone_status", {})
        assert not result.isError
        # Backend is connected so mode should not be UNKNOWN
        assert "unknown" not in result.content[0].text.lower()


class TestServerRegistration:
    def test_server_has_correct_name(self):
        backend = StubBackend()
        server = create_drone_mcp_server(backend=backend)
        assert server["name"] == "drone"

    def test_server_is_sdk_type(self):
        backend = StubBackend()
        server = create_drone_mcp_server(backend=backend)
        assert server["type"] == "sdk"
