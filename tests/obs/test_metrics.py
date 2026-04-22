"""Tests for skyherd.obs.metrics."""

from __future__ import annotations

import pytest


def test_metrics_available_flag():
    """metrics_available() returns a bool regardless of whether prometheus is installed."""
    from skyherd.obs.metrics import metrics_available

    result = metrics_available()
    assert isinstance(result, bool)


def test_record_agent_wake_no_error():
    """record_agent_wake increments without raising, even if prometheus absent."""
    from skyherd.obs.metrics import record_agent_wake

    record_agent_wake("FenceLineDispatcher")
    record_agent_wake("HerdHealthWatcher")


def test_record_tool_call_no_error():
    """record_tool_call increments without raising."""
    from skyherd.obs.metrics import record_tool_call

    record_tool_call("page_rancher")
    record_tool_call("get_snapshot")


def test_record_cost_no_error():
    """record_cost sets gauge without raising."""
    from skyherd.obs.metrics import record_cost

    record_cost(0.0042)


def test_record_sensor_event_no_error():
    """record_sensor_event increments without raising."""
    from skyherd.obs.metrics import record_sensor_event

    record_sensor_event("fence", "ranch_a")


def test_record_demo_scenario_no_error():
    """record_demo_scenario increments without raising."""
    from skyherd.obs.metrics import record_demo_scenario

    record_demo_scenario("coyote_at_fence", "success")


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("prometheus_client"),
    reason="prometheus_client not installed",
)
def test_agent_wake_counter_increments():
    """When prometheus_client is available, agent wake counter actually increments."""
    from prometheus_client import REGISTRY

    from skyherd.obs.metrics import record_agent_wake

    agent = "CalvingWatch_test"
    # Get baseline
    before = 0.0
    try:
        before = REGISTRY.get_sample_value("skyherd_agent_wakes_total", {"agent": agent}) or 0.0
    except Exception:
        before = 0.0

    record_agent_wake(agent)

    after = REGISTRY.get_sample_value("skyherd_agent_wakes_total", {"agent": agent}) or 0.0
    assert after == before + 1.0


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("prometheus_client"),
    reason="prometheus_client not installed",
)
def test_tool_call_counter_increments():
    """When prometheus_client is available, tool call counter increments."""
    from prometheus_client import REGISTRY

    from skyherd.obs.metrics import record_tool_call

    tool = "test_tool_xyz"
    before = REGISTRY.get_sample_value("skyherd_tool_calls_total", {"tool": tool}) or 0.0
    record_tool_call(tool)
    after = REGISTRY.get_sample_value("skyherd_tool_calls_total", {"tool": tool}) or 0.0
    assert after == before + 1.0
