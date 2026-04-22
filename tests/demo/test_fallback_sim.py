"""Tests for the 180-second fallback-to-sim path.

Verifies:
- When no Pi detection arrives within timeout, fallback_used=True is set.
- fallback_reason is PROP_NOT_DETECTED.
- The sim coyote scenario is invoked as substitute.
- The JSONL output is still written (demo ends cleanly).
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skyherd.demo.hardware_only import HardwareOnlyDemo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _EmptyBus:
    """Bus that never publishes anything — forces timeout path."""

    async def start(self):
        pass

    async def stop(self):
        pass

    def subscribe(self, _topic):
        return _EmptyContextManager()


class _EmptyContextManager:
    async def __aenter__(self):
        return self._iter()

    async def __aexit__(self, *args):
        pass

    async def _iter(self):
        # Yield nothing — caller will time out
        return
        yield  # make it a generator


# ---------------------------------------------------------------------------
# Fallback triggered by timeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_triggered_on_timeout(tmp_path, monkeypatch):
    """No Pi detection within timeout → fallback_used=True, reason=PROP_NOT_DETECTED."""
    monkeypatch.setenv("DRONE_BACKEND", "stub")
    monkeypatch.delenv("TWILIO_SID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("skyherd.demo.hardware_only._RUNS_DIR", tmp_path)

    # Very short timeout so test runs fast
    demo = HardwareOnlyDemo(prop="coyote", timeout_s=0.05)

    # Patch the bus to return nothing
    with (
        patch("skyherd.demo.hardware_only.SensorBus", return_value=_EmptyBus()),
        patch.object(demo, "_boot_background_sim", AsyncMock(return_value=[])),
        # Patch sim fallback to avoid full scenario overhead
        patch.object(
            demo,
            "_fallback_coyote_sim",
            AsyncMock(side_effect=_set_fallback_flag(demo)),
        ),
    ):
        result = await demo.run()

    assert result.fallback_used is True
    assert result.fallback_reason == "PROP_NOT_DETECTED"
    assert result.hardware_detection_received is False


def _set_fallback_flag(demo: HardwareOnlyDemo):
    """Returns a coroutine that sets fallback fields on the demo result."""

    async def _inner(_world=None):
        demo._result.fallback_used = True
        demo._result.fallback_reason = "PROP_NOT_DETECTED"
        demo._record_event(
            {
                "type": "fallback_triggered",
                "reason": "PROP_NOT_DETECTED",
                "ts": time.time(),
            }
        )

    return _inner


@pytest.mark.asyncio
async def test_fallback_writes_jsonl(tmp_path, monkeypatch):
    """Fallback path still writes JSONL output — demo ends cleanly."""
    monkeypatch.setenv("DRONE_BACKEND", "stub")
    monkeypatch.delenv("TWILIO_SID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("skyherd.demo.hardware_only._RUNS_DIR", tmp_path)

    demo = HardwareOnlyDemo(prop="coyote", timeout_s=0.05)

    with (
        patch("skyherd.demo.hardware_only.SensorBus", return_value=_EmptyBus()),
        patch.object(demo, "_boot_background_sim", AsyncMock(return_value=[])),
        patch.object(
            demo,
            "_fallback_coyote_sim",
            AsyncMock(side_effect=_set_fallback_flag(demo)),
        ),
    ):
        result = await demo.run()

    assert result.jsonl_path is not None
    assert result.jsonl_path.exists(), "JSONL should be written even on fallback"

    # Verify it contains a header record
    import json

    lines = result.jsonl_path.read_text().splitlines()
    header = json.loads(lines[0])
    assert header["record"] == "hardware_demo_header"
    assert header["fallback_used"] is True


# ---------------------------------------------------------------------------
# Fallback sim scenario invokes coyote path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_coyote_sim_fires_scenario(tmp_path, monkeypatch):
    """_fallback_coyote_sim calls _run_async for CoyoteScenario."""
    monkeypatch.setattr("skyherd.demo.hardware_only._RUNS_DIR", tmp_path)

    demo = HardwareOnlyDemo(prop="coyote", timeout_s=0.05)

    # Build a minimal ScenarioResult-like mock
    mock_result = MagicMock()
    mock_result.outcome_passed = True
    mock_result.agent_tool_calls = {
        "FenceLineDispatcher": [
            {"tool": "launch_drone", "input": {"target_lat": 34.123}},
            {"tool": "page_rancher", "input": {"urgency": "call"}},
        ]
    }

    with patch("skyherd.demo.hardware_only._run_async", AsyncMock(return_value=mock_result)):
        await demo._fallback_coyote_sim(world=MagicMock())

    assert demo._result.fallback_used is True
    assert demo._result.fallback_reason == "PROP_NOT_DETECTED"
    assert demo._result.drone_launched is True  # launch_drone was in tool_calls


# ---------------------------------------------------------------------------
# Fallback does not crash on scenario error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_coyote_sim_tolerates_error(tmp_path, monkeypatch):
    """If the sim fallback itself errors, it logs and does not raise."""
    monkeypatch.setattr("skyherd.demo.hardware_only._RUNS_DIR", tmp_path)

    demo = HardwareOnlyDemo(prop="coyote", timeout_s=0.05)

    with patch(
        "skyherd.demo.hardware_only._run_async",
        AsyncMock(side_effect=RuntimeError("sim exploded")),
    ):
        # Should not raise
        await demo._fallback_coyote_sim(world=MagicMock())

    # fallback_used and reason should have been set before the error
    assert demo._result.fallback_used is True


# ---------------------------------------------------------------------------
# combo prop: sick-cow still runs after coyote fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_combo_sick_cow_runs_after_coyote_fallback(tmp_path, monkeypatch):
    """In combo mode, sick-cow prop runs even when coyote used fallback."""
    monkeypatch.setenv("DRONE_BACKEND", "stub")
    monkeypatch.delenv("TWILIO_SID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("skyherd.demo.hardware_only._RUNS_DIR", tmp_path)

    sick_cow_called = []

    async def _mock_sick_cow(world):
        sick_cow_called.append(True)

    demo = HardwareOnlyDemo(prop="combo", timeout_s=0.05)

    with (
        patch("skyherd.demo.hardware_only.SensorBus", return_value=_EmptyBus()),
        patch.object(demo, "_boot_background_sim", AsyncMock(return_value=[])),
        patch.object(
            demo,
            "_fallback_coyote_sim",
            AsyncMock(side_effect=_set_fallback_flag(demo)),
        ),
        patch.object(demo, "_run_sick_cow_prop", AsyncMock(side_effect=_mock_sick_cow)),
    ):
        result = await demo.run()

    assert result.fallback_used is True
    assert len(sick_cow_called) == 1, "sick-cow prop must run after coyote fallback in combo mode"


# ---------------------------------------------------------------------------
# Timeout value is respected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_180s_timeout_constant_is_default():
    """Default HardwareOnlyDemo timeout is 180 seconds."""
    from skyherd.demo.hardware_only import _DETECTION_TIMEOUT_S

    assert _DETECTION_TIMEOUT_S == 180.0
    demo = HardwareOnlyDemo(prop="coyote")
    assert demo.timeout_s == 180.0
