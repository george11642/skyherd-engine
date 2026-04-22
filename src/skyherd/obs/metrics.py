"""Prometheus metrics for SkyHerd.

Metrics
-------
- skyherd_agent_wakes_total{agent}          Counter
- skyherd_tool_calls_total{tool}            Counter
- skyherd_cost_usd_cumulative               Gauge
- skyherd_sensor_events_total{sensor,ranch} Counter
- skyherd_demo_scenarios_total{scenario,outcome} Counter

If prometheus_client is not installed, all calls are silent no-ops.
"""

from __future__ import annotations

_METRICS_AVAILABLE = False

try:
    from prometheus_client import Counter, Gauge

    _agent_wakes = Counter(
        "skyherd_agent_wakes_total",
        "Total number of agent wake events",
        ["agent"],
    )
    _tool_calls = Counter(
        "skyherd_tool_calls_total",
        "Total number of MCP tool calls",
        ["tool"],
    )
    _cost_cumulative = Gauge(
        "skyherd_cost_usd_cumulative",
        "Cumulative LLM cost in USD across all sessions",
    )
    _sensor_events = Counter(
        "skyherd_sensor_events_total",
        "Total sensor events published",
        ["sensor", "ranch"],
    )
    _demo_scenarios = Counter(
        "skyherd_demo_scenarios_total",
        "Total demo scenario runs",
        ["scenario", "outcome"],
    )
    _METRICS_AVAILABLE = True

except ImportError:
    _agent_wakes = None  # type: ignore[assignment]
    _tool_calls = None  # type: ignore[assignment]
    _cost_cumulative = None  # type: ignore[assignment]
    _sensor_events = None  # type: ignore[assignment]
    _demo_scenarios = None  # type: ignore[assignment]


def configure() -> None:
    """No-op — metrics are registered at import time. Kept for API symmetry."""
    pass


def record_agent_wake(agent: str) -> None:
    """Increment the agent wake counter for *agent*."""
    if _agent_wakes is not None:
        _agent_wakes.labels(agent=agent).inc()


def record_tool_call(tool: str) -> None:
    """Increment the tool call counter for *tool*."""
    if _tool_calls is not None:
        _tool_calls.labels(tool=tool).inc()


def record_cost(total_usd: float) -> None:
    """Set the cumulative cost gauge to *total_usd*."""
    if _cost_cumulative is not None:
        _cost_cumulative.set(total_usd)


def record_sensor_event(sensor: str, ranch: str) -> None:
    """Increment the sensor event counter for *sensor* on *ranch*."""
    if _sensor_events is not None:
        _sensor_events.labels(sensor=sensor, ranch=ranch).inc()


def record_demo_scenario(scenario: str, outcome: str) -> None:
    """Increment the demo scenario counter for *scenario* with *outcome*."""
    if _demo_scenarios is not None:
        _demo_scenarios.labels(scenario=scenario, outcome=outcome).inc()


def metrics_available() -> bool:
    """Return True if prometheus_client is installed."""
    return _METRICS_AVAILABLE
