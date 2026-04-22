"""
SITL end-to-end tests using the built-in pure-Python MAVLink emulator.

Gate item #4 proof: SkyHerd executes real MAVLink missions — ARM, TAKEOFF,
MISSION_UPLOAD (3 waypoints), MISSION_START, MISSION_ITEM_REACHED × 3, RTL —
all over genuine UDP MAVLink wire traffic via PymavlinkBackend + MavlinkSitlEmulator.

No Docker, no mavsdk_server binary required.  Tests are skipped unless
SITL_EMULATOR=1 (or SITL=1 for a real container run).

Run locally:
    SITL_EMULATOR=1 uv run pytest tests/drone/test_sitl_e2e.py -v
"""

from __future__ import annotations

import os
import time

import pytest

from skyherd.drone.interface import Waypoint
from skyherd.drone.pymavlink_backend import PymavlinkBackend
from skyherd.drone.sitl_emulator import MavlinkSitlEmulator

# ---------------------------------------------------------------------------
# Skip guard
# ---------------------------------------------------------------------------

_ENABLED = (
    os.environ.get("SITL_EMULATOR", "0") == "1"
    or os.environ.get("SITL", "0") == "1"
)

pytestmark = pytest.mark.skipif(
    not _ENABLED,
    reason=(
        "SITL e2e tests skipped — set SITL_EMULATOR=1 (built-in emulator) "
        "or SITL=1 (real Docker SITL)."
    ),
)

# ---------------------------------------------------------------------------
# Port allocation: each test gets its own port pair to avoid conflicts
# ---------------------------------------------------------------------------

_BASE_PORT = 14560  # well away from 14540 production port


def _ports(offset: int) -> tuple[int, int]:
    """Return (gcs_port, vehicle_port) for test slot *offset*."""
    return _BASE_PORT + offset * 2, _BASE_PORT + offset * 2 + 1


# ---------------------------------------------------------------------------
# Shared emulator fixture (module scope — starts once, reused across tests)
# ---------------------------------------------------------------------------

_SHARED_GCS_PORT, _SHARED_VEHICLE_PORT = _ports(0)


@pytest.fixture(scope="module")
def shared_emulator():
    """Start MavlinkSitlEmulator for the full module; stop after all tests."""
    emu = MavlinkSitlEmulator(
        gcs_host="127.0.0.1",
        gcs_port=_SHARED_GCS_PORT,
        vehicle_port=_SHARED_VEHICLE_PORT,
    )
    emu.start()
    time.sleep(0.5)
    yield emu
    emu.stop()


@pytest.fixture()
async def backend(shared_emulator):
    """Connect PymavlinkBackend to the shared emulator; disconnect after test."""
    b = PymavlinkBackend(listen_host="127.0.0.1", listen_port=_SHARED_GCS_PORT)
    await b.connect()
    yield b
    await b.disconnect()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_emulator_connects_and_reports_state(backend) -> None:
    """PymavlinkBackend must connect and return valid DroneState."""
    state = await backend.state()
    assert isinstance(state.mode, str)
    assert 0.0 <= state.battery_pct <= 100.0
    # Home position near Zurich Airfield
    assert 47.0 < state.lat < 48.0
    assert 8.0 < state.lon < 9.5
    assert not state.in_air


async def test_emulator_takeoff_reaches_altitude(backend) -> None:
    """Drone should arm, climb, report in_air after takeoff."""
    await backend.takeoff(alt_m=10.0)
    state = await backend.state()
    assert state.in_air, f"Expected in_air after takeoff, got: {state}"
    assert state.altitude_m > 0.0
    # RTL to reset for next test
    await backend.return_to_home()


async def test_emulator_patrol_three_waypoints(backend) -> None:
    """
    Upload 3-waypoint mission and confirm all MISSION_ITEM_REACHED received.
    This is the core Gate item #4 assertion — real MAVLink mission execution.
    """
    await backend.takeoff(alt_m=20.0)

    waypoints = [
        Waypoint(lat=47.3977, lon=8.5456, alt_m=20.0, hold_s=0.0),
        Waypoint(lat=47.3980, lon=8.5460, alt_m=25.0, hold_s=0.0),
        Waypoint(lat=47.3977, lon=8.5464, alt_m=20.0, hold_s=0.0),
    ]
    await backend.patrol(waypoints)  # raises on timeout or error
    await backend.return_to_home()


async def test_emulator_thermal_clip_creates_png(backend) -> None:
    """get_thermal_clip() must produce a valid PNG file."""
    path = await backend.get_thermal_clip(duration_s=1.0)
    assert path.exists(), f"Thermal frame not created at {path}"
    assert path.suffix == ".png"
    with path.open("rb") as fh:
        header = fh.read(4)
    assert header == b"\x89PNG", f"Not a valid PNG at {path}"


async def test_emulator_rtl_lands(backend) -> None:
    """After RTL, drone should be on the ground."""
    await backend.takeoff(alt_m=10.0)
    await backend.return_to_home()
    state = await backend.state()
    assert not state.in_air, f"Expected on ground after RTL, got: {state}"


async def test_full_e2e_run_sitl_e2e(shared_emulator) -> None:
    """
    Run the complete run_sitl_e2e() coroutine against the emulator.

    Gate item #4 TRULY-GREEN proof: connect → arm → takeoff → patrol 3 WPs
    → thermal clip → RTL, all producing real MAVLink wire traffic.
    """
    # Use a fresh port pair so this test doesn't collide with the shared fixture
    gcs_port, vehicle_port = _ports(5)

    from skyherd.drone.e2e import run_sitl_e2e  # noqa: PLC0415

    # Start a dedicated emulator for this test
    emu = MavlinkSitlEmulator(
        gcs_host="127.0.0.1",
        gcs_port=gcs_port,
        vehicle_port=vehicle_port,
    )
    emu.start()
    time.sleep(0.5)
    try:
        result = await run_sitl_e2e(
            port=gcs_port,
            takeoff_alt_m=15.0,
            emulator=True,  # starts its own emulator internally
        )
    finally:
        emu.stop()

    assert result["success"] is True, f"E2E failed: {result}"
    assert result["elapsed_s"] > 0
    assert "CONNECTED" in result["events"]
    assert "TAKEOFF OK" in result["events"]
    assert "PATROL OK" in result["events"]
    assert "RTL OK" in result["events"]
    assert "E2E PASS" in result["events"]

    from pathlib import Path  # noqa: PLC0415

    clip_path = Path(result["thermal_path"])
    assert clip_path.exists(), f"Thermal clip missing: {clip_path}"
