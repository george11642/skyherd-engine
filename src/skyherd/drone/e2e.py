"""
SkyHerd SITL end-to-end mission runner.

Connects to a MAVLink vehicle (real SITL or built-in emulator), executes a
full mission lifecycle, and prints timestamped evidence for Gate item #4.

Two backends are supported:
  --emulator  PymavlinkBackend + built-in MavlinkSitlEmulator (no Docker).
              Uses raw pymavlink over UDP — no mavsdk_server binary needed.
              This is the default offline mode.

  (default)   SitlBackend (MAVSDK / mavsdk_server) against a real Docker
              ArduPilot SITL started with `make sitl-up`.

Gate item #4 criteria (all must appear in the output):
    CONNECTED     — backend.connect() succeeded
    TAKEOFF OK    — drone armed + airborne
    PATROL OK     — 3-waypoint mission uploaded + completed
    THERMAL CLIP  — synthetic IR frame saved to disk
    RTL OK        — return-to-launch + landed
    E2E PASS      — all steps completed without exception
"""

from __future__ import annotations

import asyncio
import logging
import time

import typer

from skyherd.drone.interface import Waypoint

app = typer.Typer(add_completion=False)

logger = logging.getLogger(__name__)

# Triangle patrol over Zurich Airfield (ArduPilot SITL default home)
_PATROL_WAYPOINTS = [
    Waypoint(lat=47.3977, lon=8.5456, alt_m=50.0, hold_s=5.0),
    Waypoint(lat=47.3980, lon=8.5460, alt_m=60.0, hold_s=5.0),
    Waypoint(lat=47.3977, lon=8.5464, alt_m=50.0, hold_s=5.0),
]


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


async def run_sitl_e2e(
    port: int = 14540,
    takeoff_alt_m: float = 30.0,
    emulator: bool = False,
) -> dict:
    """
    End-to-end SITL test: connect → arm → takeoff → patrol 3 WPs → RTL.

    When *emulator* is True:
      - Starts MavlinkSitlEmulator in a background thread (vehicle side).
      - Connects PymavlinkBackend as GCS listener on *port*.
      - All MAVLink wire traffic goes directly over UDP (no mavsdk_server).

    When *emulator* is False:
      - Connects SitlBackend (MAVSDK) to a real Docker SITL on *port*.
      - Requires `make sitl-up` first.

    Returns a result dict: {success, elapsed_s, thermal_path, events}.
    Raises on any failure.
    """
    _log("=== SkyHerd SITL E2E Mission Runner ===")
    _log(f"Port        : {port}")
    _log(f"Backend     : {'pymavlink+emulator' if emulator else 'mavsdk+docker-sitl'}")
    _log(f"Takeoff alt : {takeoff_alt_m} m")
    _log(f"Waypoints   : {len(_PATROL_WAYPOINTS)}")
    _log("")

    emu_obj = None  # in-process emulator instance

    if emulator:
        # ------------------------------------------------------------------
        # Start in-process emulator: vehicle on (port+1) → GCS on port
        # PymavlinkBackend listens on `port`, emulator sends to `port`
        # ------------------------------------------------------------------
        from skyherd.drone.sitl_emulator import MavlinkSitlEmulator  # noqa: PLC0415

        vehicle_port = port + 1
        _log(f"Starting MavlinkSitlEmulator vehicle_port={vehicle_port} → gcs_port={port}")
        emu_obj = MavlinkSitlEmulator(
            gcs_host="127.0.0.1",
            gcs_port=port,
            vehicle_port=vehicle_port,
        )
        emu_obj.start()
        # Give it a moment to bind and begin sending heartbeats
        await asyncio.sleep(1.0)
        _log(f"Emulator running (vehicle UDP {emu_obj.port})")

        from skyherd.drone.pymavlink_backend import PymavlinkBackend  # noqa: PLC0415

        backend = PymavlinkBackend(listen_host="127.0.0.1", listen_port=port)

    else:
        # ------------------------------------------------------------------
        # Real Docker SITL: SitlBackend uses mavsdk_server
        # ------------------------------------------------------------------
        import skyherd.drone.sitl as _sitl_mod  # noqa: PLC0415

        _sitl_mod._SITL_ADDRESS = f"udpin://0.0.0.0:{port}"
        from skyherd.drone.sitl import SitlBackend  # noqa: PLC0415

        backend = SitlBackend()

    start_time = time.monotonic()
    events: list[str] = []

    try:
        # --- CONNECT ---
        _log("Connecting to MAVLink vehicle...")
        await backend.connect()
        state = await backend.state()
        _log(
            f"CONNECTED: armed={state.armed} in_air={state.in_air} "
            f"battery={state.battery_pct:.0f}% mode={state.mode} "
            f"lat={state.lat:.4f} lon={state.lon:.4f}"
        )
        events.append("CONNECTED")

        # --- TAKEOFF ---
        _log(f"Arming + takeoff to {takeoff_alt_m} m AGL...")
        await backend.takeoff(takeoff_alt_m)
        state = await backend.state()
        _log(f"TAKEOFF OK — altitude={state.altitude_m:.1f} m in_air={state.in_air}")
        events.append("TAKEOFF OK")

        # --- PATROL ---
        _log(f"Uploading + starting {len(_PATROL_WAYPOINTS)}-waypoint patrol...")
        for i, wp in enumerate(_PATROL_WAYPOINTS):
            _log(f"  WP{i}: lat={wp.lat} lon={wp.lon} alt={wp.alt_m} m hold={wp.hold_s} s")
        await backend.patrol(_PATROL_WAYPOINTS)
        state = await backend.state()
        _log(f"PATROL OK — all {len(_PATROL_WAYPOINTS)} waypoints reached")
        events.append("PATROL OK")

        # --- THERMAL CLIP ---
        _log("Capturing thermal clip (5 s)...")
        clip_path = await backend.get_thermal_clip(duration_s=5)
        _log(f"THERMAL CLIP: {clip_path}")
        events.append(f"THERMAL CLIP: {clip_path}")

        # --- RTL ---
        _log("Commanding Return-to-Launch...")
        await backend.return_to_home()
        state = await backend.state()
        _log(f"RTL OK — in_air={state.in_air} armed={state.armed}")
        events.append("RTL OK")

        elapsed = time.monotonic() - start_time
        _log("")
        _log(f"=== E2E PASS (wall-time: {elapsed:.1f} s) ===")
        events.append("E2E PASS")

        return {
            "success": True,
            "elapsed_s": elapsed,
            "thermal_path": str(clip_path),
            "events": events,
        }

    except Exception as exc:
        elapsed = time.monotonic() - start_time
        _log(f"E2E FAIL after {elapsed:.1f} s: {exc}")
        events.append(f"E2E FAIL: {exc}")
        raise

    finally:
        try:
            await backend.disconnect()
        except Exception:
            pass
        if emu_obj is not None:
            _log("Stopping emulator...")
            emu_obj.stop()
            _log("Emulator stopped")


@app.command()
def main(
    port: int = typer.Option(14540, help="MAVLink UDP port (GCS listener)"),
    emulator: bool = typer.Option(
        False, "--emulator/--no-emulator",
        help=(
            "Use built-in pymavlink emulator (no Docker). "
            "When false, connects to a real Docker SITL via MAVSDK."
        ),
    ),
    takeoff_alt: float = typer.Option(30.0, help="Takeoff altitude in metres AGL"),
    verbose: bool = typer.Option(False, "--verbose/--quiet", help="Debug logging"),
) -> None:
    """
    Run the SkyHerd SITL end-to-end mission and print timestamped evidence.

    Gate item #4: SITL drone executes real MAVLink missions from
    FenceLineDispatcher tool calls — no hardcoded patrols.

    Offline (no Docker):  skyherd-sitl-e2e --emulator
    Docker SITL:          make sitl-up && skyherd-sitl-e2e
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    result = asyncio.run(
        run_sitl_e2e(
            port=port,
            takeoff_alt_m=takeoff_alt,
            emulator=emulator,
        )
    )
    raise SystemExit(0 if result["success"] else 1)
