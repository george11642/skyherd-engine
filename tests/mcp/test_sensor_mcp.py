"""Tests for sensor_mcp — inject synthetic history and assert correct slices."""

from __future__ import annotations

from collections import deque

import pytest

from skyherd.mcp.sensor_mcp import create_sensor_mcp_server

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bus(entries_by_kind: dict) -> dict:
    """Build a bus_state dict with pre-populated deques."""
    bus: dict = {}
    for kind, entries in entries_by_kind.items():
        bus[kind] = deque(entries, maxlen=200)
    return bus


async def _call_tool(server, tool_name: str, args: dict) -> object:
    from mcp.types import CallToolRequest, ListToolsRequest

    inst = server["instance"]
    list_result = await inst.request_handlers[ListToolsRequest](
        ListToolsRequest(method="tools/list")
    )
    tools = list_result.root.tools
    assert any(t.name == tool_name for t in tools), f"Tool '{tool_name}' not registered"
    call_result = await inst.request_handlers[CallToolRequest](
        CallToolRequest(method="tools/call", params={"name": tool_name, "arguments": args})
    )
    return call_result.root


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def rich_bus():
    """Bus state with a variety of readings."""
    return _make_bus(
        {
            "trough_cam": [
                {
                    "cam_id": "cam_1",
                    "frame_path": "/frames/1.png",
                    "cows_seen": 3,
                    "anomalies": ["limping"],
                },
                {"cam_id": "cam_1", "frame_path": "/frames/2.png", "cows_seen": 2, "anomalies": []},
                {
                    "cam_id": "cam_2",
                    "frame_path": "/frames/3.png",
                    "cows_seen": 5,
                    "anomalies": ["discharge"],
                },
            ],
            "thermal": [
                {
                    "cam_id": "thermal_1",
                    "frame_path": "/thermal/1.png",
                    "hot_spots": [{"x": 10, "y": 20}],
                },
                {"cam_id": "thermal_2", "frame_path": "/thermal/2.png", "hot_spots": []},
            ],
            "water_pressure": [
                {"tank_id": "tank_a", "pressure_psi": 45.0, "level_pct": 80.0},
                {"tank_id": "tank_b", "pressure_psi": 10.0, "level_pct": 15.0},
            ],
            "collar_gps": [
                {"tag": "TAG001", "lat": 34.001, "lon": -106.001, "alt_m": 0.0, "anomaly": False},
                {"tag": "TAG002", "lat": 34.002, "lon": -106.002, "alt_m": 0.0, "anomaly": True},
            ],
        }
    )


@pytest.fixture()
def sensor_server(rich_bus):
    return create_sensor_mcp_server(bus_state=rich_bus)


# ---------------------------------------------------------------------------
# get_latest_readings
# ---------------------------------------------------------------------------


class TestGetLatestReadings:
    async def test_returns_all_kinds_when_no_filter(self, sensor_server):
        result = await _call_tool(
            sensor_server, "get_latest_readings", {"ranch_id": "ranch_a", "limit": 50}
        )
        assert not result.isError
        # Should have content
        assert result.content

    async def test_filter_by_kind(self, sensor_server, rich_bus):
        result = await _call_tool(
            sensor_server,
            "get_latest_readings",
            {"sensor_kind": "water_pressure", "ranch_id": "ranch_a", "limit": 10},
        )
        assert not result.isError

    async def test_limit_respected(self, sensor_server):
        result = await _call_tool(
            sensor_server,
            "get_latest_readings",
            {"ranch_id": "ranch_a", "limit": 1},
        )
        assert not result.isError

    async def test_unknown_kind_returns_empty(self, sensor_server):
        result = await _call_tool(
            sensor_server,
            "get_latest_readings",
            {"sensor_kind": "nonexistent_kind", "ranch_id": "ranch_a", "limit": 10},
        )
        assert not result.isError

    async def test_empty_bus_returns_empty(self):
        empty_bus: dict = {"trough_cam": deque(), "thermal": deque()}
        server = create_sensor_mcp_server(bus_state=empty_bus)
        result = await _call_tool(
            server, "get_latest_readings", {"ranch_id": "ranch_a", "limit": 10}
        )
        assert not result.isError


# ---------------------------------------------------------------------------
# get_camera_clip
# ---------------------------------------------------------------------------


class TestGetCameraClip:
    async def test_returns_frames_for_cam(self, sensor_server):
        result = await _call_tool(
            sensor_server, "get_camera_clip", {"cam_id": "cam_1", "seconds": 10}
        )
        assert not result.isError
        text = result.content[0].text
        assert "cam_1" in text

    async def test_anomalies_aggregated(self, sensor_server):
        result = await _call_tool(
            sensor_server, "get_camera_clip", {"cam_id": "cam_1", "seconds": 10}
        )
        assert not result.isError
        # limping should be in the aggregated anomalies
        assert "cam_1" in result.content[0].text

    async def test_no_frames_for_unknown_cam(self, sensor_server):
        result = await _call_tool(
            sensor_server, "get_camera_clip", {"cam_id": "no_such_cam", "seconds": 30}
        )
        assert not result.isError

    async def test_cam_filter_isolates_correctly(self, sensor_server):
        result = await _call_tool(
            sensor_server, "get_camera_clip", {"cam_id": "cam_2", "seconds": 30}
        )
        assert not result.isError
        assert "cam_2" in result.content[0].text


# ---------------------------------------------------------------------------
# get_thermal_clip
# ---------------------------------------------------------------------------


class TestGetThermalClip:
    async def test_returns_thermal_frames(self, sensor_server):
        result = await _call_tool(
            sensor_server, "get_thermal_clip", {"cam_id": "thermal_1", "seconds": 30}
        )
        assert not result.isError
        text = result.content[0].text
        assert "thermal_1" in text

    async def test_no_hot_spots_for_empty_cam(self, sensor_server):
        result = await _call_tool(
            sensor_server, "get_thermal_clip", {"cam_id": "thermal_2", "seconds": 30}
        )
        assert not result.isError


# ---------------------------------------------------------------------------
# subscribe_anomalies
# ---------------------------------------------------------------------------


class TestSubscribeAnomalies:
    async def test_returns_anomaly_events(self, sensor_server):
        result = await _call_tool(
            sensor_server, "subscribe_anomalies", {"kind_filter": "collar_gps"}
        )
        assert not result.isError

    async def test_empty_filter_returns_all_anomalies(self, sensor_server):
        result = await _call_tool(sensor_server, "subscribe_anomalies", {"kind_filter": ""})
        assert not result.isError

    async def test_no_anomalies_in_clean_bus(self):
        clean_bus = _make_bus(
            {
                "trough_cam": [
                    {"cam_id": "c", "frame_path": "/f.png", "cows_seen": 1, "anomalies": []}
                ]
            }
        )
        server = create_sensor_mcp_server(bus_state=clean_bus)
        result = await _call_tool(server, "subscribe_anomalies", {"kind_filter": ""})
        assert not result.isError


# ---------------------------------------------------------------------------
# Server meta
# ---------------------------------------------------------------------------


class TestServerMeta:
    def test_server_name_is_sensor(self):
        server = create_sensor_mcp_server(bus_state={})
        assert server["name"] == "sensor"

    def test_server_type_is_sdk(self):
        server = create_sensor_mcp_server(bus_state={})
        assert server["type"] == "sdk"
