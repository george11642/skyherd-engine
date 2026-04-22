"""OpenTelemetry tracing for SkyHerd.

Configuration
-------------
- ``OTEL_EXPORTER_OTLP_ENDPOINT`` — if set, exports spans to OTLP (gRPC).
  Example: ``http://localhost:4317``
- If the env var is absent, a no-op exporter is used (zero overhead).

If opentelemetry-api / opentelemetry-sdk are not installed, all calls
are silent no-ops (context manager still works — it just does nothing).
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Generator
from typing import Any

_OTEL_AVAILABLE = False
_tracer: Any = None


def configure_tracing(service_name: str = "skyherd") -> None:
    """Configure OpenTelemetry tracing.

    Exports to OTLP if OTEL_EXPORTER_OTLP_ENDPOINT is set; otherwise
    installs a no-op TracerProvider so trace_span() is always safe to call.
    """
    global _OTEL_AVAILABLE, _tracer

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource(attributes={SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)

        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import-untyped]
                    OTLPSpanExporter,
                )

                exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                provider.add_span_processor(BatchSpanProcessor(exporter))
            except ImportError:
                # OTLP exporter not installed — proceed with no-op export
                pass

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(service_name)
        _OTEL_AVAILABLE = True

    except ImportError:
        # opentelemetry not installed — _tracer stays None, trace_span is a no-op
        pass


@contextlib.contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Generator[Any, None, None]:
    """Context manager that wraps work in an OTel span.

    If OTel is not configured / not installed, yields None (no-op).

    Usage::

        with trace_span("agent.wake", {"agent": "FenceLineDispatcher"}):
            ...
    """
    if _tracer is None:
        yield None
        return

    with _tracer.start_as_current_span(name) as span:
        if attributes and span.is_recording():
            for k, v in attributes.items():
                span.set_attribute(k, v)
        yield span
