"""Laptop-as-drone-controller smoke tests (Phase 7.1 LDC-01).

Proves the MAVSDK-over-USB-C path is wired end-to-end without touching a
real drone. All MAVLink socket calls are mocked at the
``pymavlink.mavutil.mavlink_connection`` boundary so the test is fast, runs
offline, and stays deterministic.

The real USB-C verification happens Friday per
``docs/LAPTOP_DRONE_CONTROL.md``. This file is the pre-flight guarantee
that the wiring is sound before George plugs anything in.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from skyherd.drone.interface import DroneBackend, DroneError, DroneState, Waypoint
from skyherd.server.app import create_app
from skyherd.server.drone_control import TOKEN_HEADER


TEST_TOKEN = "laptop-drone-token-xyz"


# ---------------------------------------------------------------------------
# Fake backend for ESTOP fallback coverage
# ---------------------------------------------------------------------------


class _RtlFailingBackend(DroneBackend):
    """Backend whose RTL raises DroneError, disconnect succeeds — ESTOP chain."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def connect(self) -> None:
        self.calls.append("connect")

    async def takeoff(self, alt_m: float = 30.0) -> None:  # pragma: no cover
        self.calls.append("takeoff")

    async def patrol(self, waypoints: list[Waypoint]) -> None:  # pragma: no cover
        self.calls.append("patrol")

    async def return_to_home(self) -> None:
        self.calls.append("return_to_home")
        raise DroneError("RTL lost signal (mocked USB-C pull)")

    async def play_deterrent(
        self, tone_hz: int = 12000, duration_s: float = 6.0
    ) -> None:  # pragma: no cover
        self.calls.append("play_deterrent")

    async def get_thermal_clip(
        self, duration_s: float = 10.0
    ) -> Any:  # pragma: no cover
        self.calls.append("get_thermal_clip")
        return None

    async def state(self) -> DroneState:  # pragma: no cover
        return DroneState()

    async def disconnect(self) -> None:
        self.calls.append("disconnect")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class _FakeMavlinkMessage:
    """Minimal stand-in for a pymavlink message object."""

    def __init__(
        self,
        *,
        type_name: str,
        command: int = 0,
        relative_alt: int = 0,
        base_mode: int = 0,
        seq: int = 0,
    ) -> None:
        self._type = type_name
        self.command = command
        self.result = 0  # MAV_RESULT_ACCEPTED
        self.relative_alt = relative_alt
        self.base_mode = base_mode
        self.seq = seq

    def get_type(self) -> str:
        return self._type


def _build_mock_connection(*, climb_alt_mm: int = 25000) -> MagicMock:
    """Return a MagicMock shaped like a live pymavlink.mavfile connection.

    The mock feeds HEARTBEAT + GLOBAL_POSITION_INT messages back so the
    blocking loops in :class:`PymavlinkBackend` terminate instead of
    timing out.
    """
    conn = MagicMock()
    conn.target_system = 1
    conn.target_component = 1

    # Sequence of messages fed to recv_match — heartbeat first (connect),
    # then ACKs for ARM / TAKEOFF, then a GPI indicating airborne.
    scripted = [
        _FakeMavlinkMessage(type_name="HEARTBEAT", base_mode=0x80),
        _FakeMavlinkMessage(type_name="COMMAND_ACK", command=400),
        _FakeMavlinkMessage(type_name="COMMAND_ACK", command=22),
        _FakeMavlinkMessage(
            type_name="GLOBAL_POSITION_INT", relative_alt=climb_alt_mm
        ),
    ]

    def _recv_match(**_kwargs: Any) -> Any:
        if scripted:
            return scripted.pop(0)
        return _FakeMavlinkMessage(type_name="HEARTBEAT", base_mode=0x80)

    conn.recv_match = MagicMock(side_effect=_recv_match)
    conn.wait_heartbeat = MagicMock(return_value=None)
    conn.mav.command_long_send = MagicMock(return_value=None)
    conn.close = MagicMock(return_value=None)
    return conn


def test_mavsdk_over_usb_c_smoke_mocked() -> None:
    """PymavlinkBackend (MAVSDK leg of MavicAdapter) wires ARM + TAKEOFF.

    Directly instantiates :class:`PymavlinkBackend` — the USB-C MAVLink path
    that Friday's laptop-as-controller relies on. ``mavic_direct`` in the
    interface factory points at :class:`MavicBackend` (WebSocket to DJI
    companion app); the laptop path uses the pymavlink leg instead.
    """
    from skyherd.drone.pymavlink_backend import PymavlinkBackend

    conn = _build_mock_connection()

    # Patch the underlying mavlink_connection constructor used by
    # PymavlinkBackend._blocking_connect.
    with patch(
        "skyherd.drone.pymavlink_backend.mavutil.mavlink_connection",
        return_value=conn,
    ):
        backend = PymavlinkBackend(listen_host="127.0.0.1", listen_port=14552)
        assert backend.__class__.__name__ == "PymavlinkBackend"

        import asyncio

        async def _drive() -> None:
            await backend.connect()
            await backend.takeoff(alt_m=20.0)

        asyncio.run(_drive())

    # Command assertions: ARM (cmd 400) and TAKEOFF (cmd 22) both sent via
    # command_long_send. The exact arg order differs between pymavlink
    # versions so we only check the command id positions.
    calls = conn.mav.command_long_send.call_args_list
    assert len(calls) >= 2
    commands = [c.args[2] for c in calls]
    assert 400 in commands, f"expected ARM (400), got {commands}"
    assert 22 in commands, f"expected TAKEOFF (22), got {commands}"


@pytest_asyncio.fixture
async def client_for_backend():
    """Yields a factory that wraps an injected backend in a live app."""
    created: list[AsyncClient] = []

    async def _factory(backend: DroneBackend) -> AsyncClient:
        app = create_app(
            mock=True,
            drone_backend=backend,
            manual_override_token=TEST_TOKEN,
        )
        client = AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=True),
            base_url="http://test",
        )
        created.append(client)
        return client

    try:
        yield _factory
    finally:
        for c in created:
            await c.aclose()


@pytest.mark.asyncio
async def test_estop_http_chain_rtl_then_disconnect_fallback(
    client_for_backend,
) -> None:
    """POST /api/drone/estop falls back from RTL to disconnect when RTL fails."""
    backend = _RtlFailingBackend()
    client = await client_for_backend(backend)

    resp = await client.post(
        "/api/drone/estop", headers={TOKEN_HEADER: TEST_TOKEN}
    )
    # Best-effort path: HTTP 200 with best_effort flag even though RTL failed.
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["action"] == "estop"
    assert body["best_effort"] is True
    assert body["ok"] is True  # disconnect succeeded

    # Verify call order: RTL attempted, then disconnect as fallback.
    assert "return_to_home" in backend.calls
    assert "disconnect" in backend.calls
    assert backend.calls.index("return_to_home") < backend.calls.index(
        "disconnect"
    )


@pytest.mark.asyncio
async def test_arm_http_chain_reaches_backend(client_for_backend) -> None:
    """POST /api/drone/arm reaches a live-style backend through the HTTP path.

    Uses the same _RtlFailingBackend (connect succeeds) to cover the
    HTTP → drone_control → backend wiring without requiring MAVLink.
    """
    backend = _RtlFailingBackend()
    client = await client_for_backend(backend)

    resp = await client.post("/api/drone/arm", headers={TOKEN_HEADER: TEST_TOKEN})
    assert resp.status_code == 200
    assert backend.calls == ["connect"]
