"""SkyHerd observability — structlog + Prometheus + OpenTelemetry.

Usage
-----
Import is lazy: the obs package is only wired when SKYHERD_OBS=1 or the
caller imports explicitly.  Main deps stay slim.

    from skyherd.obs import get_logger, record_agent_wake, record_tool_call
    from skyherd.obs import record_cost, trace_span

Quick start
-----------
    import skyherd.obs.logging as obs_log
    import skyherd.obs.metrics as obs_metrics
    import skyherd.obs.tracing as obs_trace

    obs_log.configure()
    obs_metrics.configure()
    obs_trace.configure_tracing()
"""

from __future__ import annotations

from skyherd.obs.logging import configure as _configure_logging
from skyherd.obs.logging import get_logger
from skyherd.obs.metrics import record_agent_wake, record_cost, record_tool_call
from skyherd.obs.tracing import trace_span

__all__ = [
    "get_logger",
    "record_agent_wake",
    "record_tool_call",
    "record_cost",
    "trace_span",
    "_configure_logging",
]
