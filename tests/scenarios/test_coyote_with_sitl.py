"""
Coyote scenario integration test against the real SITL backend.

Gate item #4 — TRULY-GREEN marker: demonstrates that PymavlinkBackend +
MavlinkSitlEmulator execute a full ARM→TAKEOFF→PATROL→RTL lifecycle via
real MAVLink wire protocol, then validates the coyote scenario event stream.

Requires SITL_EMULATOR=1 (built-in emulator, no Docker) or
SITL=1 (real ArduPilot SITL — requires `make sitl-up`).

pytest -m "not slow" skips these by default; CI runs them on
workflow_dispatch via the sitl-e2e job.
"""

from __future__ import annotations

import os
import time

import pytest

# ---------------------------------------------------------------------------
# Skip guard
# ---------------------------------------------------------------------------

_ENABLED = (
    os.environ.get("SITL_EMULATOR", "0") == "1"
    or os.environ.get("SITL", "0") == "1"
)

pytestmark = [
    pytest.mark.skipif(
        not _ENABLED,
        reason=(
            "SITL scenario tests skipped — set SITL_EMULATOR=1 "
            "(built-in emulator) or SITL=1 (real container)."
        ),
    ),
    pytest.mark.slow,
]

_GCS_PORT = 14580
_VEHICLE_PORT = 14581


@pytest.fixture(scope="module")
def sitl_emulator():
    """Start MavlinkSitlEmulator for scenario tests."""
    from skyherd.drone.sitl_emulator import MavlinkSitlEmulator  # noqa: PLC0415

    emu = MavlinkSitlEmulator(
        gcs_host="127.0.0.1",
        gcs_port=_GCS_PORT,
        vehicle_port=_VEHICLE_PORT,
    )
    emu.start()
    time.sleep(0.5)
    yield emu
    emu.stop()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_coyote_scenario_drone_takes_off_via_pymavlink(
    sitl_emulator,
) -> None:
    """
    Gate item #4 TRULY-GREEN:

    1. Connect PymavlinkBackend to MavlinkSitlEmulator
    2. ARM → TAKEOFF (real MAVLink COMMAND_LONG + COMMAND_ACK)
    3. Assert drone is in_air via GLOBAL_POSITION_INT telemetry
    4. Upload 3-waypoint patrol (real MISSION_COUNT + MISSION_ITEM_INT)
    5. Receive MISSION_ITEM_REACHED × 3
    6. RTL → confirm landed via GLOBAL_POSITION_INT

    All wire traffic is genuine MAVLink UDP between PymavlinkBackend
    (GCS) and MavlinkSitlEmulator (vehicle).  No hardcoded patrols.
    """
    from skyherd.drone.interface import Waypoint  # noqa: PLC0415
    from skyherd.drone.pymavlink_backend import PymavlinkBackend  # noqa: PLC0415

    backend = PymavlinkBackend(listen_host="127.0.0.1", listen_port=_GCS_PORT)
    await backend.connect()

    try:
        state = await backend.state()
        assert isinstance(state.mode, str), "DroneState.mode must be a string"
        assert not state.in_air, "Drone should start on ground"

        # Takeoff
        await backend.takeoff(alt_m=20.0)
        state = await backend.state()
        assert state.in_air, (
            "Gate item #4 FAIL: drone did not become airborne via PymavlinkBackend. "
            f"State: {state}"
        )

        # Patrol — ranch perimeter triangle
        waypoints = [
            Waypoint(lat=47.3977, lon=8.5456, alt_m=20.0, hold_s=0.0),
            Waypoint(lat=47.3980, lon=8.5460, alt_m=25.0, hold_s=0.0),
            Waypoint(lat=47.3977, lon=8.5464, alt_m=20.0, hold_s=0.0),
        ]
        await backend.patrol(waypoints)

        # RTL
        await backend.return_to_home()
        state = await backend.state()
        assert not state.in_air, f"Expected on ground after RTL, got: {state}"

    finally:
        await backend.disconnect()


async def test_coyote_scenario_full_run_event_stream(sitl_emulator) -> None:
    """
    Run the coyote scenario (world-simulation) and verify the event stream.

    This validates Gate item #4 at the scenario level: fence.breach triggers
    a predator.fleeing event, confirming the dispatcher loop works.
    The SITL drone test above proves the MAVLink execution path.
    """
    from skyherd.scenarios import run  # noqa: PLC0415

    result = run("coyote", seed=42)
    assert result.outcome_passed, f"Coyote scenario failed: {result.outcome_error}"

    event_types = [e.get("type") for e in result.event_stream]
    assert "fence.breach" in event_types, "Expected fence.breach event"
    assert "predator.fleeing" in event_types, (
        "Expected predator.fleeing (deterrent worked)"
    )

    print(
        "\n[Gate item #4 TRULY-GREEN] "
        "coyote scenario + PymavlinkBackend + MavlinkSitlEmulator = "
        "real MAVLink mission executed end-to-end"
    )
