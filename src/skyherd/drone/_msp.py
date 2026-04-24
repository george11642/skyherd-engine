"""
MSP v1 — minimal encoder/decoder for Betaflight & iNav flight controllers.

Frame layout (MultiWii / Cleanflight / Betaflight / iNav — compatible)::

    $  M  <  <len:u8>  <cmd:u8>  <payload ...>  <crc:u8>
    |  |  |
    |  |  direction: '<' to FC, '>' from FC, '!' from FC = error
    |  protocol family: 'M' for v1
    preamble

The CRC is the XOR of ``len``, ``cmd``, and every payload byte — the
preamble bytes are NOT included.

This module intentionally implements only the handful of commands SkyHerd
needs on the bench: API_VERSION, STATUS, ANALOG, MOTOR, SET_MOTOR, SET_RAW_RC.
It is pure-Python, zero-dependency, and well under 150 lines so the whole
protocol surface can be reviewed at a glance.

SAFETY-CRITICAL: this module is imported by the motor-control path.  Keep
it small, pure, and side-effect-free.  No logging here.
"""

from __future__ import annotations

from enum import IntEnum

__all__ = ["MspCommand", "decode_msp_v1", "encode_msp_v1"]

_PREAMBLE = b"$M"
_DIR_TO_FC = b"<"
_DIR_FROM_FC = b">"
_DIR_ERROR = b"!"

# Minimum v1 frame: $ M <dir> <len> <cmd> <crc> == 6 bytes.
_MIN_FRAME_LEN = 6

# v1 uses a single byte for the payload length => cap at 255.
_MAX_PAYLOAD_LEN = 255


class MspCommand(IntEnum):
    """MSP v1 command IDs SkyHerd uses (canonical Betaflight/iNav values)."""

    API_VERSION = 1  # 3-byte response: protocol, api_major, api_minor
    STATUS = 101  # general flight-controller status
    MOTOR = 104  # read current motor outputs (8 × uint16 LE)
    ANALOG = 110  # voltage, amperage, rssi, mAh drawn
    SET_RAW_RC = 200  # write RC channel values (used to arm via AUX if needed)
    SET_MOTOR = 214  # write motor outputs (8 × uint16 LE microseconds)


def _xor_checksum(length: int, command: int, payload: bytes) -> int:
    """CRC is XOR of length, command, and every payload byte."""
    crc = length & 0xFF
    crc ^= command & 0xFF
    for b in payload:
        crc ^= b
    return crc & 0xFF


def encode_msp_v1(command: int, payload: bytes = b"") -> bytes:
    """Build a ``$M<`` (to-FC) MSP v1 frame.

    Parameters
    ----------
    command:
        The MSP command ID (0..255).  See :class:`MspCommand`.
    payload:
        Raw payload bytes (0..255 long).

    Returns
    -------
    bytes
        The fully-framed packet including header, length, command, payload,
        and XOR checksum.

    Raises
    ------
    ValueError
        If ``payload`` is longer than 255 bytes or ``command`` is out of
        range.
    """
    if not 0 <= command <= 0xFF:
        raise ValueError(f"MSP command out of range: {command}")
    if len(payload) > _MAX_PAYLOAD_LEN:
        raise ValueError(
            f"MSP v1 payload limited to {_MAX_PAYLOAD_LEN} bytes; got {len(payload)}"
        )

    length = len(payload)
    crc = _xor_checksum(length, command, payload)
    return _PREAMBLE + _DIR_TO_FC + bytes([length, command]) + payload + bytes([crc])


def decode_msp_v1(frame: bytes) -> tuple[int, bytes]:
    """Parse a single MSP v1 response frame.

    Accepts ``$M>`` (from FC) or ``$M!`` (from FC, error) frames.  Error
    frames surface as a :class:`ValueError` — we don't try to distinguish
    here; the caller can catch and re-raise a domain exception.

    Parameters
    ----------
    frame:
        Exactly one framed packet — caller is responsible for splitting a
        stream into frames.

    Returns
    -------
    tuple(command, payload)
        The command ID and the raw payload bytes.

    Raises
    ------
    ValueError
        If the header, length byte, or checksum is invalid.
    """
    if len(frame) < _MIN_FRAME_LEN:
        raise ValueError(f"MSP v1 frame too short: {len(frame)} < {_MIN_FRAME_LEN}")

    if frame[:2] != _PREAMBLE:
        raise ValueError(f"MSP v1 bad preamble: {frame[:2]!r}")

    direction = frame[2:3]
    if direction == _DIR_ERROR:
        raise ValueError(f"MSP v1 error response for command {frame[4]}")
    if direction != _DIR_FROM_FC:
        raise ValueError(f"MSP v1 unexpected direction byte: {direction!r}")

    length = frame[3]
    command = frame[4]
    expected_total = _MIN_FRAME_LEN + length - 1  # header(5) + payload + crc(1) = 6 + length
    # The above line is equivalent to 5 + length + 1; keep the arithmetic explicit.
    expected_total = 5 + length + 1
    if len(frame) < expected_total:
        raise ValueError(
            f"MSP v1 frame truncated: have {len(frame)} bytes, expected {expected_total}"
        )

    payload = bytes(frame[5 : 5 + length])
    crc = frame[5 + length]
    expected_crc = _xor_checksum(length, command, payload)
    if crc != expected_crc:
        raise ValueError(
            f"MSP v1 checksum mismatch: got 0x{crc:02x}, expected 0x{expected_crc:02x}"
        )

    return command, payload
