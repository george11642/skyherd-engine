"""Tests for iOS-required endpoints: GET /api/scenarios and GET /api/status.

TDD: tests written before implementation.
Mirrors conventions from tests/server/test_app.py.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from skyherd.server.app import create_app


@pytest.fixture
def mock_app():
    return create_app(mock=True)


@pytest_asyncio.fixture
async def client(mock_app):
    async with AsyncClient(
        transport=ASGITransport(app=mock_app, raise_app_exceptions=True),
        base_url="http://test",
    ) as c:
        yield c


# ------------------------------------------------------------------
# GET /api/scenarios
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenarios_returns_200(client):
    resp = await client.get("/api/scenarios")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_scenarios_response_has_scenarios_list(client):
    resp = await client.get("/api/scenarios")
    data = resp.json()
    assert "scenarios" in data
    assert isinstance(data["scenarios"], list)


@pytest.mark.asyncio
async def test_scenarios_list_is_non_empty(client):
    resp = await client.get("/api/scenarios")
    data = resp.json()
    assert len(data["scenarios"]) > 0


@pytest.mark.asyncio
async def test_scenarios_each_entry_has_required_fields(client):
    resp = await client.get("/api/scenarios")
    data = resp.json()
    for scenario in data["scenarios"]:
        assert "id" in scenario, f"Missing 'id' in {scenario}"
        assert "name" in scenario, f"Missing 'name' in {scenario}"
        assert "description" in scenario, f"Missing 'description' in {scenario}"
        assert "agents" in scenario, f"Missing 'agents' in {scenario}"
        assert "expected_duration_s" in scenario, f"Missing 'expected_duration_s' in {scenario}"


@pytest.mark.asyncio
async def test_scenarios_agents_is_list(client):
    resp = await client.get("/api/scenarios")
    data = resp.json()
    for scenario in data["scenarios"]:
        assert isinstance(scenario["agents"], list), (
            f"'agents' should be a list, got {type(scenario['agents'])} in {scenario['id']}"
        )


@pytest.mark.asyncio
async def test_scenarios_expected_duration_is_number(client):
    resp = await client.get("/api/scenarios")
    data = resp.json()
    for scenario in data["scenarios"]:
        assert isinstance(scenario["expected_duration_s"], (int, float)), (
            f"'expected_duration_s' should be numeric in {scenario['id']}"
        )


@pytest.mark.asyncio
async def test_scenarios_contains_known_scenario_ids(client):
    resp = await client.get("/api/scenarios")
    data = resp.json()
    ids = {s["id"] for s in data["scenarios"]}
    # The 5 hero scenarios documented in CLAUDE.md must be present
    expected = {"coyote", "sick_cow", "water_drop", "calving", "storm"}
    assert expected.issubset(ids), f"Missing hero scenarios. Got: {ids}"


@pytest.mark.asyncio
async def test_scenarios_id_matches_name_or_key(client):
    """The 'id' field should be the machine-readable scenario key."""
    resp = await client.get("/api/scenarios")
    data = resp.json()
    for scenario in data["scenarios"]:
        assert isinstance(scenario["id"], str)
        assert scenario["id"]  # non-empty


# ------------------------------------------------------------------
# GET /api/status
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_returns_200_when_no_driver_attached(client):
    """Must return 200 even when no ambient driver is attached."""
    resp = await client.get("/api/status")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_status_response_has_required_fields(client):
    resp = await client.get("/api/status")
    data = resp.json()
    assert "attached" in data
    assert "running" in data
    assert "active_scenario" in data
    assert "speed" in data
    assert "seed" in data
    assert "world_tick" in data


@pytest.mark.asyncio
async def test_status_attached_is_false_when_no_driver(client):
    """With no ambient driver, attached must be False."""
    resp = await client.get("/api/status")
    data = resp.json()
    assert data["attached"] is False


@pytest.mark.asyncio
async def test_status_active_scenario_is_none_when_no_driver(client):
    resp = await client.get("/api/status")
    data = resp.json()
    assert data["active_scenario"] is None


@pytest.mark.asyncio
async def test_status_speed_defaults_to_one_when_no_driver(client):
    resp = await client.get("/api/status")
    data = resp.json()
    assert data["speed"] == 1.0


@pytest.mark.asyncio
async def test_status_seed_is_none_when_no_driver(client):
    resp = await client.get("/api/status")
    data = resp.json()
    assert data["seed"] is None


@pytest.mark.asyncio
async def test_status_world_tick_is_none_when_no_driver(client):
    resp = await client.get("/api/status")
    data = resp.json()
    assert data["world_tick"] is None


@pytest.mark.asyncio
async def test_status_running_is_false_when_no_driver(client):
    resp = await client.get("/api/status")
    data = resp.json()
    assert data["running"] is False


@pytest.mark.asyncio
async def test_status_with_attached_driver(mock_app):
    """When an ambient driver is attached, attached=True and fields reflect driver state."""

    class _FakeDriver:
        active_scenario = "coyote"
        speed = 2.5
        seed = 42
        world_tick = 120
        running = True

    mock_app.state.ambient_driver = _FakeDriver()
    async with AsyncClient(
        transport=ASGITransport(app=mock_app, raise_app_exceptions=True),
        base_url="http://test",
    ) as c:
        resp = await c.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["attached"] is True
    assert data["active_scenario"] == "coyote"
    assert data["speed"] == 2.5
    assert data["seed"] == 42
    assert data["world_tick"] == 120
    assert data["running"] is True
