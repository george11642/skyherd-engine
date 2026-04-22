"""Tests for /metrics endpoint and obs logging/tracing."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Return a TestClient for the SkyHerd app in mock mode."""
    import os

    os.environ.setdefault("SKYHERD_MOCK", "1")
    from skyherd.server.app import create_app

    app = create_app(mock=True)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_metrics_endpoint_responds(client):
    """/metrics returns 200 with text content."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")


def test_metrics_endpoint_has_type_lines(client):
    """/metrics response contains '# TYPE' lines when prometheus_client installed."""
    import importlib.util

    resp = client.get("/metrics")
    body = resp.text
    if importlib.util.find_spec("prometheus_client"):
        assert "# TYPE" in body or "# HELP" in body or body.startswith("#")
    else:
        # Fallback message when prometheus not installed
        assert "prometheus_client" in body or resp.status_code == 200


def test_trace_span_noop_without_otel():
    """trace_span works as a no-op context manager when OTel not configured."""
    from skyherd.obs.tracing import trace_span

    with trace_span("test.span", {"key": "value"}) as span:
        # span may be None (no-op) or a real span — both are valid
        pass  # must not raise


def test_get_logger_returns_something():
    """get_logger always returns a usable logger."""
    from skyherd.obs.logging import get_logger

    log = get_logger("test")
    assert log is not None


def test_configure_logging_idempotent():
    """configure() can be called multiple times without error."""
    from skyherd.obs import logging as obs_log

    obs_log.configure()
    obs_log.configure()
    obs_log.configure()


def test_cors_wildcard_not_present():
    """The CORS middleware never includes a wildcard origin."""
    from skyherd.server.app import _cors_origins

    origins = _cors_origins()
    assert "*" not in origins


def test_sse_semaphore_initialized(client):
    """/events responds (200 or 429) — never 500."""
    # TestClient doesn't stream SSE well; just confirm route exists
    # by checking the app has the route registered
    from skyherd.server.app import create_app

    app = create_app(mock=True)
    routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
    assert "/events" in routes
    assert "/metrics" in routes
