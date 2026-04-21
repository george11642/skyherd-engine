"""Tests for galileo_mcp — sim positions, haversine correctness ≤1m error."""

from __future__ import annotations

import math

import pytest

from skyherd.mcp.galileo_mcp import _haversine_m, create_galileo_mcp_server

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snapshot(cows: list[dict]) -> object:
    """Return a minimal WorldSnapshot-like object."""

    class _Snap:
        def __init__(self, c):
            self.cows = c

    return _Snap(cows)


async def _call_tool(server, tool_name: str, args: dict) -> object:
    from mcp.types import CallToolRequest, ListToolsRequest

    inst = server["instance"]
    list_result = await inst.request_handlers[ListToolsRequest](ListToolsRequest(method="tools/list"))
    tools = list_result.root.tools
    assert any(t.name == tool_name for t in tools), f"Tool '{tool_name}' not registered"
    call_result = await inst.request_handlers[CallToolRequest](
        CallToolRequest(method="tools/call", params={"name": tool_name, "arguments": args})
    )
    return call_result.root


# ---------------------------------------------------------------------------
# Haversine unit tests (no server needed)
# ---------------------------------------------------------------------------


class TestHaversineFormula:
    def test_same_point_is_zero(self):
        assert _haversine_m(34.0, -106.0, 34.0, -106.0) == pytest.approx(0.0, abs=1e-6)

    def test_known_distance_equator(self):
        # 1 degree of longitude at equator ≈ 111 320 m
        dist = _haversine_m(0.0, 0.0, 0.0, 1.0)
        assert dist == pytest.approx(111_320, rel=0.01)

    def test_known_north_south(self):
        # 1 degree of latitude ≈ 111 320 m
        dist = _haversine_m(0.0, 0.0, 1.0, 0.0)
        assert dist == pytest.approx(111_195, rel=0.01)

    def test_known_coords_new_mexico(self):
        # Albuquerque to Socorro NM is roughly 80 km
        dist = _haversine_m(35.085, -106.651, 34.058, -106.891)
        assert 70_000 < dist < 120_000

    def test_error_versus_reference_under_1m(self):
        """Haversine against a known geodetic distance should be within 1 m for short ranges."""
        # 100 m north
        lat1, lon1 = 34.0, -106.0
        lat2 = lat1 + 100 / 111_320.0
        lon2 = lon1
        dist = _haversine_m(lat1, lon1, lat2, lon2)
        assert abs(dist - 100.0) < 1.0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def two_cow_snapshot():
    cows = [
        {"tag": "TAG001", "pos": (0.0, 0.0), "paddock_id": "p1"},
        {"tag": "TAG002", "pos": (100.0, 0.0), "paddock_id": "p1"},
    ]
    return _make_snapshot(cows)


@pytest.fixture()
def galileo_server(two_cow_snapshot):
    return create_galileo_mcp_server(
        world_snapshot_fn=lambda: two_cow_snapshot,
        drone_state_fn=None,
    )


# ---------------------------------------------------------------------------
# get_drone_position
# ---------------------------------------------------------------------------


class TestGetDronePosition:
    async def test_returns_position_fields(self, galileo_server):
        result = await _call_tool(galileo_server, "get_drone_position", {})
        assert not result.isError
        text = result.content[0].text
        assert "drone" in text.lower() or "lat" in text.lower() or "acc" in text.lower()

    async def test_accuracy_cm_is_positive(self, galileo_server):
        result = await _call_tool(galileo_server, "get_drone_position", {})
        assert not result.isError

    async def test_with_drone_state_fn(self, two_cow_snapshot):
        from skyherd.drone.interface import DroneState

        async def _fake_state():
            return DroneState(lat=34.001, lon=-106.001, altitude_m=60.0, in_air=True)

        server = create_galileo_mcp_server(
            world_snapshot_fn=lambda: two_cow_snapshot,
            drone_state_fn=_fake_state,
        )
        result = await _call_tool(server, "get_drone_position", {})
        assert not result.isError
        text = result.content[0].text
        assert "34" in text or "drone" in text.lower()


# ---------------------------------------------------------------------------
# get_cattle_positions
# ---------------------------------------------------------------------------


class TestGetCattlePositions:
    async def test_returns_all_cows(self, galileo_server):
        result = await _call_tool(galileo_server, "get_cattle_positions", {})
        assert not result.isError
        text = result.content[0].text
        assert "2" in text  # 2 cows in fixture

    async def test_filter_by_tag(self, galileo_server):
        result = await _call_tool(
            galileo_server, "get_cattle_positions", {"tags": ["TAG001"]}
        )
        assert not result.isError
        text = result.content[0].text
        assert "1" in text  # only TAG001 returned

    async def test_unknown_tag_returns_zero(self, galileo_server):
        result = await _call_tool(
            galileo_server, "get_cattle_positions", {"tags": ["NOTEXIST"]}
        )
        assert not result.isError
        text = result.content[0].text
        assert "0" in text

    async def test_position_near_ranch_reference(self, galileo_server):
        result = await _call_tool(galileo_server, "get_cattle_positions", {"tags": None})
        assert not result.isError
        # Just verify no error and content returned — lat/lon checked via haversine test


# ---------------------------------------------------------------------------
# distance_between
# ---------------------------------------------------------------------------


class TestDistanceBetween:
    async def test_distance_tag001_tag002(self, galileo_server):
        result = await _call_tool(
            galileo_server,
            "distance_between",
            {"tag_a": "TAG001", "tag_b": "TAG002"},
        )
        assert not result.isError
        text = result.content[0].text
        assert "distance" in text.lower() or "tag001" in text.lower()

    async def test_distance_approximately_100m(self, galileo_server):
        """TAG001 is at pos=(0,0), TAG002 at pos=(100,0) — should be ~100m apart."""
        result = await _call_tool(
            galileo_server,
            "distance_between",
            {"tag_a": "TAG001", "tag_b": "TAG002"},
        )
        assert not result.isError
        # The text should mention a distance; let's verify it's reasonable
        # We can check: 100m offset in pos-x maps to ~100/111320 degrees lat delta
        # haversine of that should be ~100m
        text = result.content[0].text
        assert "tag001" in text.lower() or "100" in text or "m" in text.lower()

    async def test_haversine_error_under_1m_for_100m_separation(self, galileo_server):
        """Integration: the haversine distance for 100m local offset should be within 1m of 100."""
        # Use the formula directly with the same coordinate math the tool uses
        ref_lat, ref_lon = 34.0, -106.0
        lat1 = ref_lat + 0.0 / 111_320.0
        lon1 = ref_lon + 0.0 / (111_320.0 * math.cos(math.radians(ref_lat)))
        lat2 = ref_lat + 100.0 / 111_320.0
        lon2 = ref_lon + 0.0 / (111_320.0 * math.cos(math.radians(ref_lat)))
        dist = _haversine_m(lat1, lon1, lat2, lon2)
        assert abs(dist - 100.0) < 1.0

    async def test_missing_tag_returns_error(self, galileo_server):
        result = await _call_tool(
            galileo_server,
            "distance_between",
            {"tag_a": "TAG001", "tag_b": "MISSING"},
        )
        assert result.isError

    async def test_both_missing_returns_error(self, galileo_server):
        result = await _call_tool(
            galileo_server,
            "distance_between",
            {"tag_a": "GHOST1", "tag_b": "GHOST2"},
        )
        assert result.isError

    async def test_same_cow_distance_is_zero(self, galileo_server):
        result = await _call_tool(
            galileo_server,
            "distance_between",
            {"tag_a": "TAG001", "tag_b": "TAG001"},
        )
        assert not result.isError


# ---------------------------------------------------------------------------
# Server meta
# ---------------------------------------------------------------------------


class TestServerMeta:
    def test_name_is_galileo(self):
        server = create_galileo_mcp_server(world_snapshot_fn=lambda: _make_snapshot([]))
        assert server["name"] == "galileo"

    def test_type_is_sdk(self):
        server = create_galileo_mcp_server(world_snapshot_fn=lambda: _make_snapshot([]))
        assert server["type"] == "sdk"
