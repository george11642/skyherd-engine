"""Tests for the manual drone-control HTTP surface (Phase 7.1 LDC-03).

Covers the five token-gated endpoints that let a human operator drive the
Mavic from the laptop. Uses ``httpx.AsyncClient`` against the app factory in
mock mode with a ``FakeDroneBackend`` injected so no real drone, no network,
and no asyncio-heavy MAVLink stack is touched.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from skyherd.drone.interface import (
    DroneBackend,
    DroneError,
    DroneState,
    Waypoint,
)
from skyherd.server.app import create_app
from skyherd.server.drone_control import TOKEN_HEADER


class FakeBroadcaster:
    """Minimal broadcaster stand-in that records every _broadcast call."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def _broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, dict(payload)))

    # The real EventBroadcaster has no-op start/stop at the module level;
    # lifespan only touches broadcaster.start/stop when we use the live one.


class FakeDroneBackend(DroneBackend):
    """Records every method invocation plus programmable failure hooks."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail_on: set[str] = set()
        self.connected: bool = False

    def _record(self, name: str, **kwargs: Any) -> None:
        self.calls.append((name, dict(kwargs)))

    def _maybe_fail(self, name: str) -> None:
        if name in self.fail_on:
            # Use DroneError so the endpoint maps to 502; DroneUnavailable
            # tests cover the 503 path separately via the "no backend" route.
            raise DroneError(f"simulated failure on {name}")

    async def connect(self) -> None:
        self._record("connect")
        self._maybe_fail("connect")
        self.connected = True

    async def takeoff(self, alt_m: float = 30.0) -> None:
        self._record("takeoff", alt_m=alt_m)
        self._maybe_fail("takeoff")

    async def patrol(self, waypoints: list[Waypoint]) -> None:  # pragma: no cover
        self._record("patrol", waypoints=list(waypoints))

    async def return_to_home(self) -> None:
        self._record("return_to_home")
        self._maybe_fail("return_to_home")

    async def play_deterrent(
        self, tone_hz: int = 12000, duration_s: float = 6.0
    ) -> None:  # pragma: no cover
        self._record("play_deterrent", tone_hz=tone_hz, duration_s=duration_s)

    async def get_thermal_clip(
        self, duration_s: float = 10.0
    ) -> Path:  # pragma: no cover
        self._record("get_thermal_clip", duration_s=duration_s)
        return Path("runtime/thermal/fake.png")

    async def state(self) -> DroneState:  # pragma: no cover
        self._record("state")
        return DroneState()

    async def disconnect(self) -> None:
        self._record("disconnect")
        self._maybe_fail("disconnect")
        self.connected = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


TEST_TOKEN = "testtoken-abc123"


def _build_app(
    *,
    backend: DroneBackend | None,
    token: str = TEST_TOKEN,
    broadcaster: FakeBroadcaster | None = None,
) -> Any:
    """Build a fresh app and (for the broadcaster swap) reach past create_app.

    We need to inject a ``FakeBroadcaster`` because the live
    :class:`EventBroadcaster` spins up asyncio tasks on lifespan startup. Our
    tests check the SSE emit list directly, so we monkey-patch the
    ``attach_drone_control`` call site by rebuilding with a throwaway app.
    """
    app = create_app(
        mock=True,
        drone_backend=backend,
        manual_override_token=token,
    )
    if broadcaster is not None:
        # Replace the closure's broadcaster by re-mounting drone-control onto
        # a fresh FakeBroadcaster. FastAPI route collisions are OK here — the
        # new routes are appended and take precedence in matching order.
        from skyherd.server.drone_control import attach_drone_control

        # Strip the previous /api/drone/* routes first so the FakeBroadcaster
        # version is the one exercised by the test.
        app.router.routes = [
            r
            for r in app.router.routes
            if not (getattr(r, "path", "").startswith("/api/drone"))
        ]
        attach_drone_control(
            app,
            get_backend=lambda: backend,
            broadcaster=broadcaster,
            token=token,
        )
    return app


@pytest_asyncio.fixture
async def client_factory():
    """Yields a factory that builds an AsyncClient around a configured app."""
    clients: list[AsyncClient] = []

    async def _factory(
        *,
        backend: DroneBackend | None,
        token: str = TEST_TOKEN,
        broadcaster: FakeBroadcaster | None = None,
    ) -> AsyncClient:
        app = _build_app(backend=backend, token=token, broadcaster=broadcaster)
        client = AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=True),
            base_url="http://test",
        )
        clients.append(client)
        return client

    try:
        yield _factory
    finally:
        for c in clients:
            await c.aclose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arm_without_token_returns_401(client_factory):
    backend = FakeDroneBackend()
    client = await client_factory(backend=backend)
    resp = await client.post("/api/drone/arm")
    assert resp.status_code == 401
    assert "missing" in resp.json()["detail"].lower()
    assert backend.calls == []


@pytest.mark.asyncio
async def test_arm_with_wrong_token_returns_403(client_factory):
    backend = FakeDroneBackend()
    client = await client_factory(backend=backend)
    resp = await client.post(
        "/api/drone/arm", headers={TOKEN_HEADER: "not-the-right-token"}
    )
    assert resp.status_code == 403
    assert backend.calls == []


@pytest.mark.asyncio
async def test_arm_without_backend_returns_503(client_factory):
    client = await client_factory(backend=None)
    resp = await client.post("/api/drone/arm", headers={TOKEN_HEADER: TEST_TOKEN})
    assert resp.status_code == 503
    assert "backend" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_arm_with_backend_calls_backend_and_broadcasts(client_factory):
    backend = FakeDroneBackend()
    bc = FakeBroadcaster()
    client = await client_factory(backend=backend, broadcaster=bc)

    resp = await client.post("/api/drone/arm", headers={TOKEN_HEADER: TEST_TOKEN})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["action"] == "arm"
    assert "latency_ms" in body

    # Backend was invoked.
    assert any(name == "connect" for name, _ in backend.calls)
    # SSE event emitted.
    assert len(bc.events) == 1
    event_type, payload = bc.events[0]
    assert event_type == "drone.manual_override"
    assert payload["action"] == "arm"
    assert payload["actor"] == "laptop"
    assert payload["success"] is True
    assert payload["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_double_arm_is_idempotent(client_factory):
    backend = FakeDroneBackend()
    bc = FakeBroadcaster()
    client = await client_factory(backend=backend, broadcaster=bc)

    for _ in range(2):
        resp = await client.post("/api/drone/arm", headers={TOKEN_HEADER: TEST_TOKEN})
        assert resp.status_code == 200

    # Connect was called twice (each invocation is cheap on real backends)
    # but both returned 200 and backend state is connected.
    connect_calls = [c for c in backend.calls if c[0] == "connect"]
    assert len(connect_calls) == 2
    assert backend.connected is True
    # Two SSE events emitted.
    arm_events = [p for t, p in bc.events if t == "drone.manual_override"]
    assert len(arm_events) == 2
    assert all(p["action"] == "arm" for p in arm_events)


@pytest.mark.asyncio
async def test_estop_calls_rtl_then_disarm_on_failure(client_factory):
    backend = FakeDroneBackend()
    backend.fail_on.add("return_to_home")
    bc = FakeBroadcaster()
    client = await client_factory(backend=backend, broadcaster=bc)

    resp = await client.post("/api/drone/estop", headers={TOKEN_HEADER: TEST_TOKEN})
    # ESTOP always returns 200 (best-effort); payload carries the truth.
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "estop"
    assert body["best_effort"] is True
    assert body["ok"] is True  # disconnect succeeded as the fallback.

    # Verify call order: RTL attempted first, disconnect as fallback.
    names = [c[0] for c in backend.calls]
    assert "return_to_home" in names
    assert "disconnect" in names
    assert names.index("return_to_home") < names.index("disconnect")

    # SSE carries best_effort flag.
    assert len(bc.events) == 1
    _, payload = bc.events[0]
    assert payload.get("best_effort") is True
    assert "simulated failure" in (payload.get("error") or "")


@pytest.mark.asyncio
async def test_takeoff_rejects_out_of_range_alt(client_factory):
    backend = FakeDroneBackend()
    client = await client_factory(backend=backend)
    resp = await client.post(
        "/api/drone/takeoff",
        headers={TOKEN_HEADER: TEST_TOKEN},
        json={"alt_m": 500.0},
    )
    assert resp.status_code == 422
    # Backend never invoked for out-of-range input.
    assert not any(c[0] == "takeoff" for c in backend.calls)


@pytest.mark.asyncio
async def test_takeoff_accepts_valid_alt_and_passes_to_backend(client_factory):
    backend = FakeDroneBackend()
    client = await client_factory(backend=backend)
    resp = await client.post(
        "/api/drone/takeoff",
        headers={TOKEN_HEADER: TEST_TOKEN},
        json={"alt_m": 15.5},
    )
    assert resp.status_code == 200
    takeoff_calls = [c for c in backend.calls if c[0] == "takeoff"]
    assert len(takeoff_calls) == 1
    assert takeoff_calls[0][1]["alt_m"] == 15.5


@pytest.mark.asyncio
async def test_manual_override_token_disabled_returns_503(client_factory):
    """When token is empty, every endpoint is disabled regardless of input."""
    backend = FakeDroneBackend()
    client = await client_factory(backend=backend, token="")

    resp = await client.post("/api/drone/arm", headers={TOKEN_HEADER: "anything"})
    assert resp.status_code == 503
    assert "disabled" in resp.json()["detail"].lower()
    assert backend.calls == []


@pytest.mark.asyncio
async def test_rtl_land_and_disarm_all_succeed(client_factory):
    """RTL, LAND, DISARM all call the right backend method with token."""
    backend = FakeDroneBackend()
    bc = FakeBroadcaster()
    client = await client_factory(backend=backend, broadcaster=bc)

    for action in ("rtl", "land", "disarm"):
        resp = await client.post(
            f"/api/drone/{action}", headers={TOKEN_HEADER: TEST_TOKEN}
        )
        assert resp.status_code == 200, f"{action} failed: {resp.text}"
        assert resp.json()["action"] == action

    # RTL and LAND both call return_to_home; DISARM calls disconnect.
    names = [c[0] for c in backend.calls]
    assert names.count("return_to_home") == 2  # rtl + land
    assert names.count("disconnect") == 1

    actions = [p["action"] for _, p in bc.events]
    assert actions == ["rtl", "land", "disarm"]


@pytest.mark.asyncio
async def test_backend_drone_error_maps_to_502(client_factory):
    """A non-ESTOP action whose backend raises DroneError returns 502."""
    backend = FakeDroneBackend()
    backend.fail_on.add("connect")
    bc = FakeBroadcaster()
    client = await client_factory(backend=backend, broadcaster=bc)

    resp = await client.post("/api/drone/arm", headers={TOKEN_HEADER: TEST_TOKEN})
    assert resp.status_code == 502
    # Failure path also emits an SSE event so the panel can show it.
    assert len(bc.events) == 1
    _, payload = bc.events[0]
    assert payload["success"] is False
    assert "simulated failure" in payload["error"]
