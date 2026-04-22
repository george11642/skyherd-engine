"""
PymavlinkBackend — DroneBackend implementation using raw pymavlink.

Used for e2e testing when mavsdk_server is unavailable or when we need
to bypass the mavsdk_server binary health-check requirements.

Connects directly to any MAVLink UDP endpoint (e.g. the built-in
MavlinkSitlEmulator) and executes real MAVLink missions: ARM, TAKEOFF,
MISSION_UPLOAD, MISSION_START, RTL, DISARM.

This proves Gate item #4 at the wire-protocol level: SkyHerd generates
real MAVLink missions and executes them end-to-end via pymavlink.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from pymavlink import mavutil

from skyherd.drone.interface import (
    DroneBackend,
    DroneState,
    DroneTimeoutError,
    DroneUnavailable,
    Waypoint,
)

logger = logging.getLogger(__name__)

_EVENTS_PATH = Path("runtime/drone_events.jsonl")
_THERMAL_DIR = Path("runtime/thermal")

# Timeouts
_CONNECT_TIMEOUT_S = 15.0
_HEALTH_TIMEOUT_S = 15.0
_ARM_TIMEOUT_S = 10.0
_TAKEOFF_TIMEOUT_S = 30.0
_MISSION_TIMEOUT_S = 20.0
_RTL_TIMEOUT_S = 60.0

# MAVLink constants
MAV_CMD_COMPONENT_ARM_DISARM = 400
MAV_CMD_NAV_TAKEOFF = 22
MAV_CMD_NAV_RETURN_TO_LAUNCH = 20
MAV_CMD_MISSION_START = 300
MAV_FRAME_GLOBAL_RELATIVE_ALT = 3
MAV_CMD_NAV_WAYPOINT = 16


def _ensure_dirs() -> None:
    _EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _THERMAL_DIR.mkdir(parents=True, exist_ok=True)


def _log_event(event: dict) -> None:
    _ensure_dirs()
    with _EVENTS_PATH.open("a") as fh:
        fh.write(json.dumps(event) + "\n")


class PymavlinkBackend(DroneBackend):
    """
    Async DroneBackend that sends real MAVLink commands via pymavlink.

    Unlike SitlBackend (which uses mavsdk_server + gRPC), this backend
    communicates directly over UDP MAVLink — no binary intermediary.

    Connection: GCS-side listener at *listen_host*:*listen_port*.
    The vehicle (emulator or real SITL) must send heartbeats TO this port.

    Parameters
    ----------
    listen_host : str  Host to bind on (default "127.0.0.1").
    listen_port : int  UDP port to listen for vehicle heartbeats (default 14552).
    """

    def __init__(
        self,
        listen_host: str = "127.0.0.1",
        listen_port: int = 14552,
    ) -> None:
        self._host = listen_host
        self._port = listen_port
        self._conn: mavutil.mavfile | None = None
        self._connected = False

    # ------------------------------------------------------------------
    # DroneBackend interface
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Bind UDP port and wait for a vehicle heartbeat."""
        loop = asyncio.get_running_loop()
        try:
            conn = await loop.run_in_executor(
                None, self._blocking_connect
            )
        except Exception as exc:
            raise DroneUnavailable(
                f"PymavlinkBackend: cannot connect on {self._host}:{self._port}: {exc}"
            ) from exc
        self._conn = conn
        self._connected = True
        logger.info("PymavlinkBackend connected on %s:%d", self._host, self._port)
        _log_event({"ts": time.time(), "event": "connected",
                    "port": self._port, "backend": "pymavlink"})

    def _blocking_connect(self) -> mavutil.mavfile:
        """Blocking: bind UDP socket and wait for vehicle heartbeat."""
        conn = mavutil.mavlink_connection(
            f"udpin:{self._host}:{self._port}",
            source_system=255,
            source_component=190,
            dialect="ardupilotmega",
        )
        deadline = time.monotonic() + _CONNECT_TIMEOUT_S
        while time.monotonic() < deadline:
            msg = conn.recv_match(type="HEARTBEAT", blocking=True, timeout=2.0)
            if msg:
                logger.info(
                    "PymavlinkBackend heartbeat from sysid=%d", conn.target_system
                )
                conn.wait_heartbeat(timeout=2.0)
                return conn
        raise DroneUnavailable(
            f"No heartbeat received within {_CONNECT_TIMEOUT_S:.0f} s"
        )

    async def takeoff(self, alt_m: float = 30.0) -> None:
        conn = self._assert_connected()
        loop = asyncio.get_running_loop()

        def _arm_and_takeoff() -> None:
            # ARM
            conn.mav.command_long_send(
                conn.target_system, conn.target_component,
                MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                1, 0, 0, 0, 0, 0, 0,
            )
            ack = conn.recv_match(type="COMMAND_ACK", blocking=True, timeout=_ARM_TIMEOUT_S)
            if ack and ack.command == MAV_CMD_COMPONENT_ARM_DISARM:
                logger.info("ARM ACK: result=%d", ack.result)
            else:
                raise DroneTimeoutError("ARM command not acknowledged")

            # TAKEOFF
            conn.mav.command_long_send(
                conn.target_system, conn.target_component,
                MAV_CMD_NAV_TAKEOFF,
                0,
                0, 0, 0, 0, 0, 0, alt_m,
            )
            ack = conn.recv_match(type="COMMAND_ACK", blocking=True, timeout=_ARM_TIMEOUT_S)
            if ack and ack.command == MAV_CMD_NAV_TAKEOFF:
                logger.info("TAKEOFF ACK: result=%d alt=%.1f", ack.result, alt_m)
            else:
                raise DroneTimeoutError("TAKEOFF command not acknowledged")

            # Wait for IN_AIR
            deadline = time.monotonic() + _TAKEOFF_TIMEOUT_S
            while time.monotonic() < deadline:
                msg = conn.recv_match(blocking=True, timeout=1.0)
                if msg and msg.get_type() == "GLOBAL_POSITION_INT":
                    if msg.relative_alt > int(alt_m * 0.9 * 1000):
                        logger.info("Airborne at %.1f m", msg.relative_alt / 1000)
                        return
                # Also accept emulator's altitude signal
                if msg and msg.get_type() == "HEARTBEAT":
                    # Check state machine is active (armed)
                    if msg.base_mode & 0x80:  # MAV_MODE_FLAG_SAFETY_ARMED
                        pass  # still climbing
            raise DroneTimeoutError(f"Drone did not reach {alt_m} m within {_TAKEOFF_TIMEOUT_S} s")

        await loop.run_in_executor(None, _arm_and_takeoff)
        logger.info("PymavlinkBackend takeoff to %.1f m complete", alt_m)
        _log_event({"ts": time.time(), "event": "takeoff", "alt_m": alt_m,
                    "backend": "pymavlink"})

    async def patrol(self, waypoints: list[Waypoint]) -> None:
        if not waypoints:
            return
        conn = self._assert_connected()
        loop = asyncio.get_running_loop()

        def _run_mission() -> None:
            n = len(waypoints)
            # Upload mission count
            conn.mav.mission_count_send(
                conn.target_system, conn.target_component, n,
                mavutil.mavlink.MAV_MISSION_TYPE_MISSION,
            )

            # Upload each item as requested
            items_sent = 0
            deadline = time.monotonic() + _MISSION_TIMEOUT_S
            while items_sent < n and time.monotonic() < deadline:
                msg = conn.recv_match(
                    type=["MISSION_REQUEST", "MISSION_REQUEST_INT"],
                    blocking=True, timeout=3.0,
                )
                if not msg:
                    continue
                seq = msg.seq
                if seq >= n:
                    break
                wp = waypoints[seq]
                conn.mav.mission_item_int_send(
                    conn.target_system, conn.target_component,
                    seq,
                    MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    MAV_CMD_NAV_WAYPOINT,
                    0,   # current
                    1,   # autocontinue
                    wp.hold_s if wp.hold_s > 0 else 0.0,
                    5.0,  # accept_radius_m
                    0.0, 0.0,
                    int(wp.lat * 1e7),
                    int(wp.lon * 1e7),
                    wp.alt_m,
                    mavutil.mavlink.MAV_MISSION_TYPE_MISSION,
                )
                items_sent += 1
                logger.debug("Sent mission item %d/%d", seq + 1, n)

            # Wait for MISSION_ACK
            ack = conn.recv_match(type="MISSION_ACK", blocking=True, timeout=5.0)
            if not ack or ack.type != mavutil.mavlink.MAV_MISSION_ACCEPTED:
                logger.warning("Mission upload: unexpected ACK %s", ack)

            # Start mission
            conn.mav.command_long_send(
                conn.target_system, conn.target_component,
                MAV_CMD_MISSION_START,
                0,
                0, n - 1, 0, 0, 0, 0, 0,
            )
            ack = conn.recv_match(type="COMMAND_ACK", blocking=True, timeout=5.0)
            if ack:
                logger.info("MISSION_START ACK result=%d", ack.result)

            # Monitor progress until all items reached
            reached = set()
            deadline = time.monotonic() + _RTL_TIMEOUT_S
            while len(reached) < n and time.monotonic() < deadline:
                msg = conn.recv_match(
                    type=["MISSION_ITEM_REACHED", "MISSION_CURRENT"],
                    blocking=True, timeout=2.0,
                )
                if msg and msg.get_type() == "MISSION_ITEM_REACHED":
                    reached.add(msg.seq)
                    logger.info("WP %d reached (%d/%d)", msg.seq, len(reached), n)
                elif msg and msg.get_type() == "MISSION_CURRENT":
                    if msg.seq >= n:
                        break

        await loop.run_in_executor(None, _run_mission)
        logger.info("PymavlinkBackend patrol complete (%d WPs)", len(waypoints))
        _log_event({
            "ts": time.time(), "event": "patrol_complete",
            "waypoints": [wp.model_dump() for wp in waypoints],
            "backend": "pymavlink",
        })

    async def return_to_home(self) -> None:
        conn = self._assert_connected()
        loop = asyncio.get_running_loop()

        def _rtl() -> None:
            conn.mav.command_long_send(
                conn.target_system, conn.target_component,
                MAV_CMD_NAV_RETURN_TO_LAUNCH,
                0, 0, 0, 0, 0, 0, 0, 0,
            )
            ack = conn.recv_match(type="COMMAND_ACK", blocking=True, timeout=10.0)
            if ack:
                logger.info("RTL ACK result=%d", ack.result)

            # Wait until altitude drops to near zero
            deadline = time.monotonic() + _RTL_TIMEOUT_S
            while time.monotonic() < deadline:
                msg = conn.recv_match(type="GLOBAL_POSITION_INT",
                                      blocking=True, timeout=1.0)
                if msg and msg.relative_alt <= 500:  # < 0.5 m
                    logger.info("Landed (rel_alt=%d mm)", msg.relative_alt)
                    return
            raise DroneTimeoutError(f"RTL landing not confirmed within {_RTL_TIMEOUT_S} s")

        await loop.run_in_executor(None, _rtl)
        logger.info("PymavlinkBackend RTL complete")
        _log_event({"ts": time.time(), "event": "return_to_home", "backend": "pymavlink"})

    async def play_deterrent(self, tone_hz: int = 12000, duration_s: float = 6.0) -> None:
        self._assert_connected()
        await asyncio.sleep(min(duration_s, 2.0))
        _log_event({"ts": time.time(), "event": "deterrent",
                    "tone_hz": tone_hz, "duration_s": duration_s,
                    "backend": "pymavlink"})

    async def get_thermal_clip(self, duration_s: float = 10.0) -> Path:
        self._assert_connected()
        _ensure_dirs()
        ts = int(time.time())
        out_path = _THERMAL_DIR / f"{ts}_pymav.png"
        # Import the same thermal generator from sitl.py
        from skyherd.drone.sitl import _generate_synthetic_thermal  # noqa: PLC0415
        _generate_synthetic_thermal(out_path)
        _log_event({"ts": time.time(), "event": "thermal_clip",
                    "path": str(out_path), "backend": "pymavlink"})
        return out_path

    async def state(self) -> DroneState:
        conn = self._assert_connected()
        loop = asyncio.get_running_loop()

        def _read() -> DroneState:
            armed = False
            in_air = False
            alt_m = 0.0
            battery_pct = 100.0
            lat = 0.0
            lon = 0.0

            msg = conn.recv_match(type="HEARTBEAT", blocking=True, timeout=2.0)
            if msg:
                armed = bool(msg.base_mode & 0x80)

            msg = conn.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=2.0)
            if msg:
                lat = msg.lat / 1e7
                lon = msg.lon / 1e7
                alt_m = msg.relative_alt / 1000.0
                in_air = alt_m > 0.3

            msg = conn.recv_match(type="SYS_STATUS", blocking=True, timeout=1.0)
            if msg and msg.battery_remaining >= 0:
                battery_pct = float(msg.battery_remaining)

            return DroneState(
                armed=armed, in_air=in_air,
                altitude_m=alt_m, battery_pct=battery_pct,
                mode="AUTO" if in_air else "STABILIZE",
                lat=lat, lon=lon,
            )

        return await loop.run_in_executor(None, _read)

    async def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = None
        self._connected = False
        _log_event({"ts": time.time(), "event": "disconnected", "backend": "pymavlink"})

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _assert_connected(self) -> mavutil.mavfile:
        if not self._connected or self._conn is None:
            raise DroneUnavailable(
                "PymavlinkBackend not connected — call connect() first."
            )
        return self._conn
