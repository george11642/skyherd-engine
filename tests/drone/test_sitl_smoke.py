"""
SITL smoke tests — require a running ArduPilot SITL container.

These are skipped unless the ``SITL=1`` environment variable is set.
Run with: ``SITL=1 uv run pytest tests/drone/test_sitl_smoke.py -v``

Start the container first: ``make sitl-up``
"""

from __future__ import annotations

import os

import pytest

# Skip the entire module unless SITL=1 is explicitly set.
pytestmark = pytest.mark.skipif(
    os.environ.get("SITL", "0") != "1",
    reason="SITL smoke tests skipped (set SITL=1 to run; requires `make sitl-up`)",
)
pytest.mark.slow(pytestmark)


@pytest.fixture()
async def sitl_backend():
    """Connect to a live SITL and yield the backend; disconnect after test."""
    from skyherd.drone.sitl import SitlBackend

    backend = SitlBackend()
    await backend.connect()
    yield backend
    await backend.disconnect()


# ---------------------------------------------------------------------------
# Connection smoke
# ---------------------------------------------------------------------------


async def test_sitl_connects_and_reports_state(sitl_backend) -> None:
    """SITL must connect and return a sensible DroneState."""
    s = await sitl_backend.state()
    # Basic sanity: battery > 0, mode is a non-empty string.
    assert s.battery_pct > 0
    assert isinstance(s.mode, str) and s.mode != ""


# ---------------------------------------------------------------------------
# Takeoff smoke
# ---------------------------------------------------------------------------


async def test_sitl_takeoff(sitl_backend) -> None:
    """Drone arms and lifts off; state reflects in_air=True."""
    await sitl_backend.takeoff(alt_m=10.0)
    s = await sitl_backend.state()
    assert s.in_air
    assert s.armed
    assert s.altitude_m > 0

    # Land cleanly.
    await sitl_backend.return_to_home()


# ---------------------------------------------------------------------------
# Patrol smoke
# ---------------------------------------------------------------------------


async def test_sitl_patrol_two_waypoints(sitl_backend) -> None:
    """Upload a 2-waypoint mission and confirm completion without error."""
    from skyherd.drone.interface import Waypoint

    await sitl_backend.takeoff(alt_m=15.0)

    # Small local offsets near ArduPilot default SITL home (~lat 0, lon 0).
    waypoints = [
        Waypoint(lat=0.001, lon=0.001, alt_m=15.0),
        Waypoint(lat=0.002, lon=0.001, alt_m=15.0),
    ]
    await sitl_backend.patrol(waypoints)
    await sitl_backend.return_to_home()


# ---------------------------------------------------------------------------
# Thermal clip smoke
# ---------------------------------------------------------------------------


async def test_sitl_thermal_clip_creates_file(sitl_backend, tmp_path) -> None:
    """get_thermal_clip() must produce a real PNG file on disk."""
    path = await sitl_backend.get_thermal_clip(duration_s=1.0)
    assert path.exists(), f"Expected thermal frame at {path}"
    assert path.suffix == ".png"
    # Verify it's a valid PNG (starts with PNG magic bytes).
    with path.open("rb") as fh:
        header = fh.read(8)
    assert header[:4] == b"\x89PNG", f"File at {path} is not a valid PNG"


# ---------------------------------------------------------------------------
# Deterrent smoke
# ---------------------------------------------------------------------------


async def test_sitl_deterrent_logs_event(sitl_backend) -> None:
    """play_deterrent() must complete and write a row to drone_events.jsonl."""
    import json
    from pathlib import Path

    events_path = Path("runtime/drone_events.jsonl")
    size_before = events_path.stat().st_size if events_path.exists() else 0

    await sitl_backend.play_deterrent(tone_hz=12000, duration_s=1.0)

    assert events_path.exists(), "runtime/drone_events.jsonl not created"
    size_after = events_path.stat().st_size
    assert size_after > size_before, "No new event row written to drone_events.jsonl"

    # Last row must be valid JSON with event == "deterrent".
    with events_path.open() as fh:
        lines = [ln for ln in fh if ln.strip()]
    last = json.loads(lines[-1])
    assert last["event"] == "deterrent"
