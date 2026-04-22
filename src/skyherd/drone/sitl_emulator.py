"""
Pure-Python MAVLink SITL emulator using raw UDP + pymavlink wire framing.

Architecture
------------
MAVSDK uses a "GCS perspective" model:

    mavsdk_server  ←  (udpin://0.0.0.0:<gcs_port>)  ← vehicle heartbeats
    mavsdk_server  →  (knows vehicle's return addr)  → commands

So the emulator (playing "vehicle") must:
  1. Bind its own ephemeral "vehicle" UDP socket.
  2. Proactively SEND heartbeats to mavsdk_server's *gcs_port*.
  3. Receive commands sent back to our vehicle socket.
  4. Reply with COMMAND_ACK / mission ACKs, etc.

Usage
-----
    # In-process (e.g. in pytest fixtures):
    emu = MavlinkSitlEmulator(gcs_host="127.0.0.1", gcs_port=14540)
    emu.start()
    # ... run SitlBackend tests ...
    emu.stop()

    # CLI (subprocess mode):
    python -m skyherd.drone.sitl_emulator [--gcs-port 14540]
"""

from __future__ import annotations

import logging
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MAVLink constants (ardupilotmega dialect)
# ---------------------------------------------------------------------------

MAV_TYPE_QUADROTOR = 2
MAV_AUTOPILOT_ARDUPILOTMEGA = 3
MAV_STATE_STANDBY = 3
MAV_STATE_ACTIVE = 4

MAV_MODE_FLAG_SAFETY_ARMED = 128
MAV_MODE_FLAG_GUIDED_ENABLED = 8

MAV_RESULT_ACCEPTED = 0

MAV_CMD_COMPONENT_ARM_DISARM = 400
MAV_CMD_NAV_TAKEOFF = 22
MAV_CMD_NAV_RETURN_TO_LAUNCH = 20
MAV_CMD_MISSION_START = 300

MAVLINK_MSG_ID_HEARTBEAT = 0
MAVLINK_MSG_ID_SYS_STATUS = 1
MAVLINK_MSG_ID_GPS_RAW_INT = 24
MAVLINK_MSG_ID_GLOBAL_POSITION_INT = 33
MAVLINK_MSG_ID_EKF_STATUS_REPORT = 193
MAVLINK_MSG_ID_HOME_POSITION = 242
MAVLINK_MSG_ID_AUTOPILOT_VERSION = 148
MAVLINK_MSG_ID_MISSION_COUNT = 44
MAVLINK_MSG_ID_MISSION_ITEM = 39
MAVLINK_MSG_ID_MISSION_REQUEST = 40
MAVLINK_MSG_ID_MISSION_REQUEST_INT = 51
MAVLINK_MSG_ID_MISSION_ACK = 47
MAVLINK_MSG_ID_MISSION_CURRENT = 42
MAVLINK_MSG_ID_MISSION_ITEM_REACHED = 46
MAVLINK_MSG_ID_COMMAND_LONG = 76
MAVLINK_MSG_ID_COMMAND_ACK = 77
MAVLINK_MSG_ID_BATTERY_STATUS = 147

MAV_MISSION_ACCEPTED = 0
GPS_FIX_TYPE_3D_FIX = 3
MAV_CMD_REQUEST_MESSAGE = 512  # p1 = requested message ID

COPTER_MODE_STABILIZE = 0
COPTER_MODE_GUIDED = 4
COPTER_MODE_AUTO = 3
COPTER_MODE_RTL = 6

# ---------------------------------------------------------------------------
# MAVLink v2 framing (no extra dependencies)
# ---------------------------------------------------------------------------

_MAVLINK2_STX = 0xFD

_CRC_EXTRA: dict[int, int] = {
    MAVLINK_MSG_ID_HEARTBEAT: 50,
    MAVLINK_MSG_ID_SYS_STATUS: 124,
    MAVLINK_MSG_ID_GPS_RAW_INT: 24,
    MAVLINK_MSG_ID_GLOBAL_POSITION_INT: 104,
    MAVLINK_MSG_ID_EKF_STATUS_REPORT: 71,
    MAVLINK_MSG_ID_HOME_POSITION: 104,
    MAVLINK_MSG_ID_AUTOPILOT_VERSION: 178,
    MAVLINK_MSG_ID_MISSION_COUNT: 221,
    MAVLINK_MSG_ID_MISSION_ITEM: 254,
    MAVLINK_MSG_ID_MISSION_REQUEST: 230,
    MAVLINK_MSG_ID_MISSION_REQUEST_INT: 196,
    MAVLINK_MSG_ID_MISSION_ACK: 153,
    MAVLINK_MSG_ID_MISSION_CURRENT: 28,
    MAVLINK_MSG_ID_MISSION_ITEM_REACHED: 11,
    MAVLINK_MSG_ID_COMMAND_ACK: 143,
    MAVLINK_MSG_ID_BATTERY_STATUS: 154,
}


def _crc_accumulate(data: bytes, crc: int = 0xFFFF) -> int:
    for byte in data:
        tmp = byte ^ (crc & 0xFF)
        tmp = (tmp ^ (tmp << 4)) & 0xFF
        crc = ((crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)) & 0xFFFF
    return crc


def _pack(
    msg_id: int,
    payload: bytes,
    seq: int,
    sys_id: int = 1,
    comp_id: int = 1,
) -> bytes:
    """Pack a MAVLink 2.0 frame.

    MAVLink2 wire layout (10-byte header, no signature):
        Byte 0:   STX  = 0xFD
        Byte 1:   LEN  = len(payload)
        Byte 2:   INC_FLAGS = 0
        Byte 3:   CMP_FLAGS = 0
        Byte 4:   SEQ
        Byte 5:   SYS_ID
        Byte 6:   COMP_ID
        Bytes 7-9: MSG_ID (3 bytes, little-endian)
        Bytes 10..: payload
        Last 2:   CRC-16/MCRF4XX over bytes[1..] + crc_extra
    """
    length = len(payload)
    # Pack header as 7 bytes (STX..COMP_ID) then 3 bytes of msg_id
    header = (
        struct.pack(
            "<BBBBBBB",
            _MAVLINK2_STX,
            length,
            0,  # incompat_flags
            0,  # compat_flags
            seq & 0xFF,
            sys_id,
            comp_id,
        )
        + struct.pack("<I", msg_id)[:3]
    )  # msg_id is 3 bytes LE (trim 4th byte)
    crc_extra = _CRC_EXTRA.get(msg_id, 0)
    crc_data = header[1:] + payload + bytes([crc_extra])
    crc = _crc_accumulate(crc_data)
    return header + payload + struct.pack("<H", crc)


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------


def _heartbeat(base_mode: int, custom_mode: int, sys_status: int) -> bytes:
    return struct.pack(
        "<IBBBBB",
        custom_mode,
        MAV_TYPE_QUADROTOR,
        MAV_AUTOPILOT_ARDUPILOTMEGA,
        base_mode,
        sys_status,
        3,
    )


def _sys_status(battery_mv: int = 12600, battery_pct: int = 85) -> bytes:
    # MAVLink SYS_STATUS: uint32 sensors_present, uint32 sensors_enabled,
    # uint32 sensors_health, uint16 load, uint16 voltage_battery,
    # int16 current_battery, int8 battery_remaining, uint16 drop_rate_comm,
    # uint16 errors_comm, uint16 errors_count[4]
    return struct.pack(
        "<IIIHHhbHHHHHH",
        0,
        0,
        0,  # sensors (all OK)
        0,  # load
        battery_mv,  # voltage_battery (mV)
        -1,  # current_battery (-1 = unknown)
        battery_pct,  # battery_remaining (0-100, -1 unknown)
        0,
        0,  # drop_rate_comm, errors_comm
        0,
        0,
        0,
        0,  # errors_count[0..3]
    )


def _gps_raw(lat_1e7: int, lon_1e7: int, alt_mm: int) -> bytes:
    return struct.pack(
        "<QiiiHHHHBB",
        int(time.time() * 1e6),
        lat_1e7,
        lon_1e7,
        alt_mm,
        100,
        100,
        0,
        0,
        GPS_FIX_TYPE_3D_FIX,
        10,
    )


def _global_pos(lat_1e7: int, lon_1e7: int, alt_mm: int, rel_alt_mm: int) -> bytes:
    t_ms = int(time.monotonic() * 1000) & 0xFFFFFFFF
    return struct.pack("<IiiiihhhH", t_ms, lat_1e7, lon_1e7, alt_mm, rel_alt_mm, 0, 0, 0, 18000)


def _home_position(lat_1e7: int, lon_1e7: int, alt_mm: int) -> bytes:
    """HOME_POSITION (msg 242): tells mavsdk_server the home position is set.

    Layout (MAVLink common spec):
        int32  latitude, longitude, altitude (×1e7 / mm)
        float  x, y, z          (local NED, 0 = unknown)
        float  q[4]              (attitude quaternion, identity)
        float  approach_x/y/z   (approach vector, 0)
        uint64 time_usec
    Total: 3×int32 + 10×float + 1×uint64 = 12 + 40 + 8 = 60 bytes
    """
    return struct.pack(
        "<3i10fQ",
        lat_1e7,
        lon_1e7,
        alt_mm,  # 3 ints
        0.0,
        0.0,
        0.0,  # x, y, z
        1.0,
        0.0,
        0.0,
        0.0,  # q[4] identity
        0.0,
        0.0,
        0.0,  # approach_x/y/z
        int(time.time() * 1e6),  # time_usec
    )


def _ekf_status_report() -> bytes:
    """EKF_STATUS_REPORT (msg 193) — all health flags set = healthy.

    flags bits (ardupilotmega):
      1=ATTITUDE, 2=VEL_HORIZ, 4=VEL_VERT, 8=POS_HORIZ_REL,
      16=POS_HORIZ_ABS, 32=POS_VERT_ABS, 64=POS_VERT_AGL,
      128=CONST_POS_MODE, 256=PRED_POS_HORIZ_REL, 512=PRED_POS_HORIZ_ABS
    Set 0x1FF (all except CONST_POS_MODE) = healthy GPS + EKF.
    """
    flags = 0x1FF  # all healthy flags
    # float velocity_variance, pos_horiz_variance, pos_vert_variance,
    # compass_variance, terrain_alt_variance; uint16 flags; float airspeed_variance
    return struct.pack("<fffffHf", 0.01, 0.01, 0.01, 0.01, 0.01, flags, 0.01)


def _autopilot_version() -> bytes:
    """AUTOPILOT_VERSION (msg 148) — minimal valid response.

    uint64 capabilities, uint64 uid,
    uint32 flight_sw_version, middleware_sw_version, os_sw_version, board_version,
    uint16 vendor_id, product_id,
    uint8[8] flight_custom_version, middleware_custom_version, os_custom_version
    """
    capabilities = (1 << 0) | (1 << 1)  # MAV_PROTOCOL_CAPABILITY_MISSION_FLOAT + INT
    return struct.pack(
        "<QQIIIIHHxxxxxxxx8s8s8s",
        capabilities,
        0,  # uid
        0x04050700,  # flight_sw_version (ArduCopter 4.5.7)
        0,  # middleware
        0,  # os
        0,  # board
        0x026D,  # vendor_id (3DR = 0x3DR → use ArduPilot 0x026D)
        0x0011,  # product_id
        b"SkyHerd\x00",  # flight_custom_version
        b"\x00" * 8,
        b"\x00" * 8,
    )


def _command_ack(command: int, result: int = MAV_RESULT_ACCEPTED) -> bytes:
    return struct.pack("<HBBiBB", command, result, 0, 0, 255, 0)


def _mission_request(seq: int) -> bytes:
    return struct.pack("<HBB", seq, 255, 0)


def _mission_ack() -> bytes:
    return struct.pack("<BBB", 255, 0, MAV_MISSION_ACCEPTED)


def _mission_current(seq: int, total: int) -> bytes:
    return struct.pack("<HH", seq, total)


def _mission_item_reached(seq: int) -> bytes:
    return struct.pack("<H", seq)


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class _Phase(IntEnum):
    DISARMED = 0
    ARMING = 1
    ARMED = 2
    TAKING_OFF = 3
    IN_AIR = 4
    ON_MISSION = 5
    RETURNING = 6
    LANDED = 7


@dataclass
class _State:
    phase: _Phase = _Phase.DISARMED
    lat_deg: float = 47.3977
    lon_deg: float = 8.5456
    home_alt_m: float = 488.0
    rel_alt_m: float = 0.0
    target_alt_m: float = 30.0
    battery_pct: int = 85
    flight_mode: int = COPTER_MODE_STABILIZE
    seq: int = 0
    mission_total: int = 0
    mission_current: int = 0
    mission_items_rx: int = 0
    _entered_at: float = field(default_factory=time.monotonic)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def next_seq(self) -> int:
        with self._lock:
            s = self.seq
            self.seq = (self.seq + 1) & 0xFF
            return s

    def enter(self, phase: _Phase) -> None:
        self.phase = phase
        self._entered_at = time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self._entered_at

    @property
    def armed(self) -> bool:
        return self.phase in (
            _Phase.ARMING,
            _Phase.ARMED,
            _Phase.TAKING_OFF,
            _Phase.IN_AIR,
            _Phase.ON_MISSION,
            _Phase.RETURNING,
        )


# ---------------------------------------------------------------------------
# Emulator
# ---------------------------------------------------------------------------


class MavlinkSitlEmulator:
    """
    Pure-Python ArduCopter SITL emulator.

    Acts as the "vehicle" side: sends heartbeats + telemetry to *gcs_port*
    (where mavsdk_server is listening), receives commands, replies with ACKs.

    Parameters
    ----------
    gcs_host : str
        IP address of the GCS / mavsdk_server host (default ``127.0.0.1``).
    gcs_port : int
        UDP port mavsdk_server is listening on (default ``14540``).
    vehicle_port : int
        UDP port this emulator binds as the "vehicle" (default ``14541``).
        Use 0 for an OS-assigned ephemeral port.
    """

    def __init__(
        self,
        gcs_host: str = "127.0.0.1",
        gcs_port: int = 14540,
        vehicle_port: int = 14541,
    ) -> None:
        self._gcs_addr = (gcs_host, gcs_port)
        self._vehicle_port = vehicle_port
        self._sock: socket.socket | None = None
        self._state = _State()
        self._running = False
        self._threads: list[threading.Thread] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Bind vehicle socket, start background threads."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", self._vehicle_port))
        self._sock.settimeout(0.3)
        # Resolve actual port if 0 was requested
        self._vehicle_port = self._sock.getsockname()[1]
        self._running = True

        for target, name in (
            (self._heartbeat_loop, "sitl-hb"),
            (self._telemetry_loop, "sitl-telem"),
            (self._state_machine_loop, "sitl-sm"),
            (self._recv_loop, "sitl-recv"),
        ):
            t = threading.Thread(target=target, daemon=True, name=name)
            t.start()
            self._threads.append(t)

        logger.info(
            "MavlinkSitlEmulator vehicle_port=%d → gcs %s:%d",
            self._vehicle_port,
            *self._gcs_addr,
        )

    def stop(self) -> None:
        """Shut down threads and socket."""
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        for t in self._threads:
            t.join(timeout=2.0)
        self._threads.clear()
        logger.info("MavlinkSitlEmulator stopped")

    @property
    def port(self) -> int:
        return self._vehicle_port

    # ------------------------------------------------------------------
    # Internal — wire send
    # ------------------------------------------------------------------

    def _send(self, msg_id: int, payload: bytes) -> None:
        if not self._sock:
            return
        try:
            frame = _pack(msg_id, payload, self._state.next_seq())
            self._sock.sendto(frame, self._gcs_addr)
        except OSError:
            pass

    def _ack(self, command: int, result: int = MAV_RESULT_ACCEPTED) -> None:
        logger.debug("ACK cmd=%d result=%d", command, result)
        self._send(MAVLINK_MSG_ID_COMMAND_ACK, _command_ack(command, result))

    # ------------------------------------------------------------------
    # Thread: HEARTBEAT at 1 Hz
    # ------------------------------------------------------------------

    def _heartbeat_loop(self) -> None:
        while self._running:
            s = self._state
            base_mode = MAV_MODE_FLAG_GUIDED_ENABLED
            if s.armed:
                base_mode |= MAV_MODE_FLAG_SAFETY_ARMED
            sys_status = MAV_STATE_ACTIVE if s.armed else MAV_STATE_STANDBY
            self._send(
                MAVLINK_MSG_ID_HEARTBEAT,
                _heartbeat(base_mode, s.flight_mode, sys_status),
            )
            time.sleep(1.0)

    # ------------------------------------------------------------------
    # Thread: telemetry at 4 Hz
    # ------------------------------------------------------------------

    def _telemetry_loop(self) -> None:
        _telem_tick = 0
        while self._running:
            s = self._state
            lat_1e7 = int(s.lat_deg * 1e7)
            lon_1e7 = int(s.lon_deg * 1e7)
            home_alt_mm = int(s.home_alt_m * 1000)
            alt_mm = int((s.home_alt_m + s.rel_alt_m) * 1000)
            rel_mm = int(s.rel_alt_m * 1000)
            self._send(MAVLINK_MSG_ID_GPS_RAW_INT, _gps_raw(lat_1e7, lon_1e7, alt_mm))
            self._send(
                MAVLINK_MSG_ID_GLOBAL_POSITION_INT, _global_pos(lat_1e7, lon_1e7, alt_mm, rel_mm)
            )
            self._send(
                MAVLINK_MSG_ID_SYS_STATUS,
                _sys_status(battery_mv=int(12600 * s.battery_pct / 100), battery_pct=s.battery_pct),
            )
            # Every 1 s: send EKF_STATUS_REPORT + HOME_POSITION so
            # mavsdk_server sets is_global_position_ok + is_home_position_ok
            if _telem_tick % 4 == 0:
                try:
                    self._send(MAVLINK_MSG_ID_EKF_STATUS_REPORT, _ekf_status_report())
                    self._send(
                        MAVLINK_MSG_ID_HOME_POSITION, _home_position(lat_1e7, lon_1e7, home_alt_mm)
                    )
                except Exception:
                    pass  # non-critical; skip on pack error
            _telem_tick += 1
            time.sleep(0.25)

    # ------------------------------------------------------------------
    # Thread: state machine
    # ------------------------------------------------------------------

    def _state_machine_loop(self) -> None:
        while self._running:
            s = self._state
            elapsed = s.elapsed()

            if s.phase == _Phase.ARMING and elapsed >= 0.3:
                s.enter(_Phase.ARMED)

            elif s.phase == _Phase.TAKING_OFF:
                # Climb 5 m/s
                s.rel_alt_m = min(s.rel_alt_m + 5.0 * 0.1, s.target_alt_m)
                if s.rel_alt_m >= s.target_alt_m * 0.95:
                    logger.info("Emulator airborne at %.1f m", s.rel_alt_m)
                    s.enter(_Phase.IN_AIR)

            elif s.phase == _Phase.ON_MISSION:
                # Advance one mission item every 2 s
                if s.mission_current < s.mission_total and elapsed >= 2.0:
                    logger.info(
                        "Emulator mission item %d/%d",
                        s.mission_current,
                        s.mission_total,
                    )
                    self._send(
                        MAVLINK_MSG_ID_MISSION_ITEM_REACHED,
                        _mission_item_reached(s.mission_current),
                    )
                    s.mission_current += 1
                    self._send(
                        MAVLINK_MSG_ID_MISSION_CURRENT,
                        _mission_current(s.mission_current, s.mission_total),
                    )
                    s.enter(_Phase.ON_MISSION)  # reset timer
                elif s.mission_current >= s.mission_total and s.mission_total > 0:
                    logger.info("Emulator mission complete")
                    s.enter(_Phase.IN_AIR)

            elif s.phase == _Phase.RETURNING:
                # Descend 2 m/s
                s.rel_alt_m = max(0.0, s.rel_alt_m - 2.0 * 0.1)
                if s.rel_alt_m <= 0.05:
                    s.rel_alt_m = 0.0
                    logger.info("Emulator landed")
                    s.enter(_Phase.LANDED)

            time.sleep(0.1)

    # ------------------------------------------------------------------
    # Thread: receive + dispatch
    # ------------------------------------------------------------------

    def _recv_loop(self) -> None:
        buf = b""
        while self._running:
            try:
                data, _addr = self._sock.recvfrom(4096)
            except OSError:
                continue
            buf += data
            # Parse complete MAVLink 2 frames
            while True:
                idx = buf.find(bytes([_MAVLINK2_STX]))
                if idx < 0:
                    buf = b""
                    break
                buf = buf[idx:]
                if len(buf) < 10:
                    break
                length = buf[1]
                frame_len = 10 + length + 2
                if len(buf) < frame_len:
                    break
                self._dispatch(buf[:frame_len])
                buf = buf[frame_len:]

    def _dispatch(self, frame: bytes) -> None:
        try:
            # MAVLink2: msg_id is 3 bytes at offset 7 (little-endian)
            msg_id = frame[7] | (frame[8] << 8) | (frame[9] << 16)
            payload = frame[10:-2]
        except (IndexError, struct.error):
            return

        if msg_id == MAVLINK_MSG_ID_COMMAND_LONG:
            self._on_command_long(payload)
        elif msg_id == MAVLINK_MSG_ID_MISSION_COUNT:
            self._on_mission_count(payload)
        elif msg_id in (MAVLINK_MSG_ID_MISSION_ITEM, MAVLINK_MSG_ID_MISSION_REQUEST_INT):
            self._on_mission_item(payload, msg_id)

    def _on_command_long(self, payload: bytes) -> None:
        if len(payload) < 30:
            return
        try:
            params = struct.unpack_from("<fffffff", payload, 0)
            command = struct.unpack_from("<H", payload, 28)[0]
        except struct.error:
            return

        logger.info("Emulator COMMAND_LONG cmd=%d p1=%.1f", command, params[0])

        if command == MAV_CMD_REQUEST_MESSAGE:
            # mavsdk_server requests specific messages on demand (p1 = msg_id)
            requested_id = int(params[0])
            self._ack(command)
            s = self._state
            lat_1e7 = int(s.lat_deg * 1e7)
            lon_1e7 = int(s.lon_deg * 1e7)
            home_alt_mm = int(s.home_alt_m * 1000)
            if requested_id == MAVLINK_MSG_ID_HOME_POSITION:
                self._send(
                    MAVLINK_MSG_ID_HOME_POSITION, _home_position(lat_1e7, lon_1e7, home_alt_mm)
                )
            elif requested_id == MAVLINK_MSG_ID_AUTOPILOT_VERSION:
                try:
                    self._send(MAVLINK_MSG_ID_AUTOPILOT_VERSION, _autopilot_version())
                except Exception as exc:
                    logger.debug("autopilot_version pack error: %s", exc)
            elif requested_id == MAVLINK_MSG_ID_EKF_STATUS_REPORT:
                self._send(MAVLINK_MSG_ID_EKF_STATUS_REPORT, _ekf_status_report())
            # Other requested messages: silently ignore (GCS will retry)

        elif command == MAV_CMD_COMPONENT_ARM_DISARM:
            if params[0] > 0.5:
                self._state.enter(_Phase.ARMING)
                self._state.flight_mode = COPTER_MODE_GUIDED
            else:
                self._state.enter(_Phase.LANDED)
                self._state.flight_mode = COPTER_MODE_STABILIZE
            self._ack(command)

        elif command == MAV_CMD_NAV_TAKEOFF:
            alt = params[6] if params[6] > 0 else 30.0
            self._state.target_alt_m = alt
            self._state.enter(_Phase.TAKING_OFF)
            self._state.flight_mode = COPTER_MODE_GUIDED
            self._ack(command)

        elif command == MAV_CMD_NAV_RETURN_TO_LAUNCH:
            self._state.enter(_Phase.RETURNING)
            self._state.flight_mode = COPTER_MODE_RTL
            self._ack(command)

        elif command == MAV_CMD_MISSION_START:
            self._state.mission_current = 0
            self._state.enter(_Phase.ON_MISSION)
            self._state.flight_mode = COPTER_MODE_AUTO
            self._ack(command)
            self._send(
                MAVLINK_MSG_ID_MISSION_CURRENT, _mission_current(0, self._state.mission_total)
            )

        else:
            self._ack(command)

    def _on_mission_count(self, payload: bytes) -> None:
        if len(payload) < 2:
            return
        count = struct.unpack_from("<H", payload, 0)[0]
        logger.info("Emulator MISSION_COUNT=%d", count)
        self._state.mission_total = count
        self._state.mission_items_rx = 0
        if count > 0:
            self._send(MAVLINK_MSG_ID_MISSION_REQUEST, _mission_request(0))

    def _on_mission_item(self, payload: bytes, msg_id: int) -> None:
        # Both MISSION_ITEM and MISSION_REQUEST_INT land here for seq extraction
        if len(payload) < 2:
            return
        # seq is at different offsets depending on message type
        if msg_id == MAVLINK_MSG_ID_MISSION_ITEM:
            # MISSION_ITEM: float(x,y,z)=12B, int16(seq)=2B at offset 28
            if len(payload) >= 30:
                seq_val = struct.unpack_from("<H", payload, 28)[0]
            else:
                return
        else:
            seq_val = struct.unpack_from("<H", payload, 0)[0]

        logger.debug("Emulator MISSION_ITEM seq=%d", seq_val)
        self._state.mission_items_rx += 1
        next_seq = seq_val + 1

        if next_seq < self._state.mission_total:
            self._send(MAVLINK_MSG_ID_MISSION_REQUEST, _mission_request(next_seq))
        else:
            # All items received
            self._send(MAVLINK_MSG_ID_MISSION_ACK, _mission_ack())
            logger.info("Emulator mission upload ACKed (%d items)", self._state.mission_total)


# ---------------------------------------------------------------------------
# CLI entry point (subprocess mode)
# ---------------------------------------------------------------------------


def main() -> None:
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    gcs_port = int(sys.argv[1]) if len(sys.argv) > 1 else 14540
    vehicle_port = int(sys.argv[2]) if len(sys.argv) > 2 else 14541
    emu = MavlinkSitlEmulator(gcs_port=gcs_port, vehicle_port=vehicle_port)
    emu.start()
    print(
        f"[sitl_emulator] vehicle_port={emu.port} → mavsdk_server :{gcs_port}",
        flush=True,
    )
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        emu.stop()


if __name__ == "__main__":
    main()
