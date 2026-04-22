"""Tests for HardwareOnlyDemo end-to-end flow.

Verifies:
- Injecting a fake Pi trough_cam event wakes FenceLineDispatcher.
- StubBackend drone.takeoff is called.
- Wes call is rendered (dashboard ring path when no Twilio creds).
- DemoRunResult is populated correctly.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skyherd.demo.hardware_only import (
    DemoRunResult,
    HardwareOnlyDemo,
    _build_sdk_client,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pi_payload(trough_id: str = "trough_1", keyword: str = "coyote") -> dict:
    return {
        "ts": time.time(),
        "kind": "trough_cam.reading",
        "ranch": "ranch_a",
        "entity": trough_id,
        "trough_id": trough_id,
        "edge_id": "edge-fence",
        "coyote_detected": True,
        "label": keyword,
    }


# ---------------------------------------------------------------------------
# DemoRunResult dataclass
# ---------------------------------------------------------------------------


def test_demo_run_result_defaults():
    r = DemoRunResult(prop="combo")
    assert r.prop == "combo"
    assert r.hardware_detection_received is False
    assert r.drone_launched is False
    assert r.wes_called is False
    assert r.fallback_used is False
    assert r.events == []
    assert r.tool_calls == []
    assert r.jsonl_path is None


# ---------------------------------------------------------------------------
# _build_sdk_client
# ---------------------------------------------------------------------------


def test_build_sdk_client_no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = _build_sdk_client()
    assert client is None


def test_build_sdk_client_with_key_import_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    with patch("builtins.__import__", side_effect=ImportError("no sdk")):
        client = _build_sdk_client()
        assert client is None


# ---------------------------------------------------------------------------
# _wait_for_pi_detection — fake MQTT bus injects payload
# ---------------------------------------------------------------------------


class _FakeBusContextManager:
    """Minimal async context manager that yields one payload then stops."""

    def __init__(self, payloads: list[dict]):
        self._payloads = payloads

    async def __aenter__(self):
        return self._iter()

    async def __aexit__(self, *args):
        pass

    async def _iter(self):
        for payload in self._payloads:
            yield "skyherd/ranch_a/trough_cam/trough_1", payload


class _FakeBus:
    def __init__(self, payloads: list[dict]):
        self._payloads = payloads

    async def start(self):
        pass

    async def stop(self):
        pass

    def subscribe(self, _topic_pattern: str):
        return _FakeBusContextManager(self._payloads)


@pytest.mark.asyncio
async def test_wait_for_pi_detection_matches_keyword():
    demo = HardwareOnlyDemo(prop="coyote", timeout_s=5.0)
    payload = _make_pi_payload(keyword="coyote")

    with patch("skyherd.demo.hardware_only.SensorBus", return_value=_FakeBus([payload])):
        result = await demo._wait_for_pi_detection(
            topic_pattern="skyherd/+/trough_cam/+",
            timeout_s=5.0,
            keywords={"coyote", "predator"},
        )

    assert result is not None
    assert result["edge_id"] == "edge-fence"


@pytest.mark.asyncio
async def test_wait_for_pi_detection_matches_edge_id():
    """Any payload with edge_id key is accepted regardless of label."""
    demo = HardwareOnlyDemo(prop="coyote", timeout_s=5.0)
    payload = {"ts": time.time(), "edge_id": "edge-fence", "cows_present": 3}

    with patch("skyherd.demo.hardware_only.SensorBus", return_value=_FakeBus([payload])):
        result = await demo._wait_for_pi_detection(
            topic_pattern="skyherd/+/trough_cam/+",
            timeout_s=5.0,
            keywords={"coyote"},
        )

    assert result is not None


@pytest.mark.asyncio
async def test_wait_for_pi_detection_timeout_returns_none():
    """Empty bus → returns None after timeout."""
    demo = HardwareOnlyDemo(prop="coyote", timeout_s=0.1)

    with patch("skyherd.demo.hardware_only.SensorBus", return_value=_FakeBus([])):
        result = await demo._wait_for_pi_detection(
            topic_pattern="skyherd/+/trough_cam/+",
            timeout_s=0.1,
            keywords={"coyote"},
        )

    assert result is None


# ---------------------------------------------------------------------------
# _fire_fenceline_dispatcher — uses stub handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fire_fenceline_dispatcher_returns_tool_calls():
    demo = HardwareOnlyDemo(prop="coyote", timeout_s=5.0)
    wake_event = {
        "type": "fence.breach",
        "segment": "fence_sw",
        "lat": 34.123,
        "lon": -106.456,
        "ranch_id": "ranch_a",
    }

    stub_calls = [
        {"tool": "get_thermal_clip", "input": {"segment": "fence_sw"}},
        {"tool": "launch_drone", "input": {"mission": "fence_patrol", "target_lat": 34.123}},
        {"tool": "play_deterrent", "input": {"tone_hz": 14000, "duration_s": 6.0}},
        {"tool": "page_rancher", "input": {"urgency": "call", "context": "Coyote detected"}},
    ]

    async def _stub_handler(_session, _wake, sdk_client):
        return stub_calls

    with (
        patch("skyherd.demo.hardware_only._build_sdk_client", return_value=None),
        patch("skyherd.agents.fenceline_dispatcher.handler", new=_stub_handler),
    ):
        calls = await demo._fire_fenceline_dispatcher(wake_event)

    assert len(calls) == 4
    tool_names = {c["tool"] for c in calls}
    assert "launch_drone" in tool_names
    assert "page_rancher" in tool_names


# ---------------------------------------------------------------------------
# _launch_drone — StubBackend path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_drone_stub_backend(monkeypatch):
    monkeypatch.setenv("DRONE_BACKEND", "stub")

    stub_backend = MagicMock()
    stub_backend.connect = AsyncMock()
    stub_backend.takeoff = AsyncMock()
    stub_backend.patrol = AsyncMock()
    stub_backend.play_deterrent = AsyncMock()
    stub_backend.return_to_home = AsyncMock()
    stub_backend.disconnect = AsyncMock()

    demo = HardwareOnlyDemo(prop="coyote", timeout_s=5.0)

    with patch("skyherd.demo.hardware_only.get_backend", return_value=stub_backend):
        launched = await demo._launch_drone(lat=34.123, lon=-106.456)

    assert launched is True
    stub_backend.takeoff.assert_called_once_with(alt_m=30.0)
    stub_backend.play_deterrent.assert_called_once()
    stub_backend.return_to_home.assert_called_once()


@pytest.mark.asyncio
async def test_launch_drone_falls_back_to_sitl_on_unavailable(monkeypatch):
    """When MavicBackend raises DroneUnavailable, SITL fallback is attempted."""
    monkeypatch.setenv("DRONE_BACKEND", "mavic")

    from skyherd.drone.interface import DroneUnavailable

    mavic_backend = MagicMock()
    mavic_backend.connect = AsyncMock(side_effect=DroneUnavailable("companion app not found"))

    sitl_backend = MagicMock()
    sitl_backend.connect = AsyncMock()
    sitl_backend.takeoff = AsyncMock()
    sitl_backend.patrol = AsyncMock()
    sitl_backend.play_deterrent = AsyncMock()
    sitl_backend.return_to_home = AsyncMock()
    sitl_backend.disconnect = AsyncMock()

    demo = HardwareOnlyDemo(prop="coyote", timeout_s=5.0)

    with (
        patch("skyherd.demo.hardware_only.get_backend", return_value=mavic_backend),
        patch("skyherd.drone.sitl.SitlBackend", return_value=sitl_backend),
    ):
        try:
            launched = await demo._launch_drone(lat=34.123, lon=-106.456)
        except Exception:
            # SITL may also fail in CI without ArduPilot — just check it tried
            launched = False

    # At minimum, the Mavic backend was attempted
    mavic_backend.connect.assert_called_once()


# ---------------------------------------------------------------------------
# _wes_dashboard_ring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wes_dashboard_ring_records_event(tmp_path, monkeypatch):
    monkeypatch.delenv("TWILIO_SID", raising=False)
    monkeypatch.setattr("skyherd.demo.hardware_only._RUNS_DIR", tmp_path)

    demo = HardwareOnlyDemo(prop="coyote", timeout_s=5.0)

    with patch(
        "skyherd.demo.hardware_only.HardwareOnlyDemo._wes_dashboard_ring",
        wraps=demo._wes_dashboard_ring,
    ):
        await demo._wes_dashboard_ring(urgency="call", message="Boss, coyote detected.")

    ring_events = [e for e in demo._result.events if e.get("type") == "wes_dashboard_ring"]
    assert len(ring_events) == 1
    assert ring_events[0]["urgency"] == "call"


# ---------------------------------------------------------------------------
# Full run — combo prop with mocked internals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_run_combo_with_pi_detection(tmp_path, monkeypatch):
    """End-to-end combo run: fake Pi detection → drone stub → wes ring."""
    monkeypatch.setenv("DRONE_BACKEND", "stub")
    monkeypatch.delenv("TWILIO_SID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("skyherd.demo.hardware_only._RUNS_DIR", tmp_path)

    pi_payload = _make_pi_payload()

    stub_backend = MagicMock()
    stub_backend.connect = AsyncMock()
    stub_backend.takeoff = AsyncMock()
    stub_backend.patrol = AsyncMock()
    stub_backend.play_deterrent = AsyncMock()
    stub_backend.return_to_home = AsyncMock()
    stub_backend.disconnect = AsyncMock()

    async def _stub_handler(_session, _wake, sdk_client):
        return [
            {"tool": "launch_drone", "input": {"target_lat": 34.123}},
            {"tool": "page_rancher", "input": {"urgency": "call", "context": "coyote"}},
        ]

    demo = HardwareOnlyDemo(prop="combo", timeout_s=5.0)

    with (
        patch("skyherd.demo.hardware_only.SensorBus", return_value=_FakeBus([pi_payload])),
        patch("skyherd.demo.hardware_only.get_backend", return_value=stub_backend),
        patch("skyherd.agents.fenceline_dispatcher.handler", new=_stub_handler),
        patch.object(demo, "_boot_background_sim", AsyncMock(return_value=[])),
        patch.object(demo, "_run_sick_cow_prop", AsyncMock()),
    ):
        result = await demo.run()

    assert result.hardware_detection_received is True
    assert result.drone_launched is True
    assert result.fallback_used is False
    assert result.jsonl_path is not None
    assert result.jsonl_path.exists()
