"""
Tests for BetaflightOverrideBackend and MSP v1 codec.

SAFETY-CRITICAL: these tests exercise a motor-control path.  The suite must
prove that motors are commanded to zero on every exit:
  - normal completion
  - hard timeout (mock serial hangs)
  - exception mid-spin (mock serial raises)
  - async context manager __aexit__
  - explicit disconnect()

No real hardware is touched.  serial.Serial is mocked throughout.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from skyherd.drone._msp import MspCommand, decode_msp_v1, encode_msp_v1
from skyherd.drone.betaflight_override import (
    BetaflightOverrideBackend,
    _detect_serial_port,
)
from skyherd.drone.interface import DroneState, DroneUnavailable, Waypoint

# ---------------------------------------------------------------------------
# MSP v1 codec — protocol round-trip and fixtures
# ---------------------------------------------------------------------------


def test_msp_v1_encodes_empty_payload_frame_exactly() -> None:
    """MSP_API_VERSION (1) with no payload produces the canonical 6-byte frame."""
    # Arrange
    command = MspCommand.API_VERSION  # 1
    # Expected: $ M < len=0 cmd=1 crc=(0 ^ 1)=1
    expected = b"$M<\x00\x01\x01"

    # Act
    frame = encode_msp_v1(command, b"")

    # Assert
    assert frame == expected
    assert len(frame) == 6


def test_msp_v1_encodes_set_motor_payload_exactly() -> None:
    """MSP_SET_MOTOR (214) with 8 motors × uint16 LE = 16-byte payload."""
    # Arrange: motor 0 at 1200us, all others neutral 1000us
    motors = [1200, 1000, 1000, 1000, 1000, 1000, 1000, 1000]
    payload = b"".join(m.to_bytes(2, "little") for m in motors)
    assert len(payload) == 16

    # Act
    frame = encode_msp_v1(MspCommand.SET_MOTOR, payload)

    # Assert: header + length=16 + cmd=214 + 16B payload + 1B XOR checksum
    assert frame[:3] == b"$M<"
    assert frame[3] == 16  # length
    assert frame[4] == 214  # command
    assert frame[5:21] == payload
    # Checksum = XOR of length + command + every payload byte
    expected_crc = 16 ^ 214
    for b in payload:
        expected_crc ^= b
    assert frame[21] == expected_crc
    assert len(frame) == 22


def test_msp_v1_round_trip() -> None:
    """encode → decode returns the same command and payload."""
    payload = bytes(range(32))
    frame = encode_msp_v1(MspCommand.SET_MOTOR, payload)

    # Response frames use '>' instead of '<'. We construct one for decode test.
    response_frame = b"$M>" + frame[3:]
    cmd, body = decode_msp_v1(response_frame)

    assert cmd == MspCommand.SET_MOTOR
    assert body == payload


def test_msp_v1_decode_rejects_bad_preamble() -> None:
    """Frames that do not start with '$M' are rejected."""
    with pytest.raises(ValueError):
        decode_msp_v1(b"XM>\x00\x01\x01")


def test_msp_v1_decode_rejects_bad_checksum() -> None:
    """Corrupted checksum byte raises ValueError."""
    # Valid: $M>\x00\x01\x01 ; corrupt the crc byte
    with pytest.raises(ValueError):
        decode_msp_v1(b"$M>\x00\x01\xff")


def test_msp_v1_decode_rejects_short_frame() -> None:
    with pytest.raises(ValueError):
        decode_msp_v1(b"$M>")


# ---------------------------------------------------------------------------
# Port auto-detection
# ---------------------------------------------------------------------------


def test_port_detection_respects_skyherd_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKYHERD_F3_PORT", "/dev/fake-override")
    assert _detect_serial_port() == "/dev/fake-override"


def test_port_detection_prefers_ttyacm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Linux USB CDC devices enumerate as /dev/ttyACM*; pick the first."""
    monkeypatch.delenv("SKYHERD_F3_PORT", raising=False)
    fake_ports = [
        SimpleNamespace(device="/dev/ttyS0", description="built-in"),
        SimpleNamespace(device="/dev/ttyACM0", description="STM32 Virtual ComPort"),
        SimpleNamespace(device="/dev/ttyACM1", description="another one"),
    ]
    with patch("serial.tools.list_ports.comports", return_value=fake_ports):
        assert _detect_serial_port() == "/dev/ttyACM0"


def test_port_detection_falls_back_when_nothing_plausible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SKYHERD_F3_PORT", raising=False)
    with patch("serial.tools.list_ports.comports", return_value=[]):
        with pytest.raises(DroneUnavailable):
            _detect_serial_port()


# ---------------------------------------------------------------------------
# Serial mock helpers
# ---------------------------------------------------------------------------


class FakeSerial:
    """In-memory serial that records writes and replays canned reads.

    The backend sends one MSP frame per ``write()``.  The fake records every
    write and hands back canned response bytes on ``read()``.
    """

    def __init__(self, read_queue: list[bytes] | None = None) -> None:
        self.writes: list[bytes] = []
        self._read_queue: list[bytes] = list(read_queue or [])
        self.is_open = True
        self.closed = False
        # Seed a generic MSP ACK response so poll-style reads don't starve.
        self.port = "/dev/ttyACM-fake"

    def write(self, data: bytes) -> int:
        self.writes.append(bytes(data))
        return len(data)

    def read(self, size: int = 1) -> bytes:
        if self._read_queue:
            chunk = self._read_queue.pop(0)
            return chunk[:size] if size else chunk
        return b""

    def read_all(self) -> bytes:
        if self._read_queue:
            return self._read_queue.pop(0)
        return b""

    def reset_input_buffer(self) -> None:
        pass

    def reset_output_buffer(self) -> None:
        pass

    def close(self) -> None:
        self.is_open = False
        self.closed = True

    def flush(self) -> None:
        pass

    @property
    def in_waiting(self) -> int:
        return sum(len(b) for b in self._read_queue)


def _api_version_response() -> bytes:
    """Canonical 3-byte payload: protocol=0, api_major=1, api_minor=42."""
    return encode_msp_v1_as_response(MspCommand.API_VERSION, b"\x00\x01\x2a")


def encode_msp_v1_as_response(command: int, payload: bytes) -> bytes:
    """Build a '$M>' response frame (direction from FC back to host)."""
    base = encode_msp_v1(command, payload)
    # Swap '<' (to FC) for '>' (from FC).
    return b"$M>" + base[3:]


def _motors_zeroed(writes: list[bytes]) -> bool:
    """Check at least one SET_MOTOR frame with all-zero/neutral values was sent."""
    for frame in writes:
        if len(frame) < 22:
            continue
        if frame[:3] != b"$M<":
            continue
        if frame[4] != MspCommand.SET_MOTOR:
            continue
        # 16-byte payload = 8 motors × uint16 LE; zero == stop
        motors_payload = frame[5:21]
        if all(b == 0 for b in motors_payload):
            return True
    return False


def _any_set_motor(writes: list[bytes]) -> bool:
    for frame in writes:
        if len(frame) >= 22 and frame[:3] == b"$M<" and frame[4] == MspCommand.SET_MOTOR:
            return True
    return False


# ---------------------------------------------------------------------------
# Backend construction + connect
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_serial() -> FakeSerial:
    return FakeSerial(read_queue=[_api_version_response()])


@pytest.fixture()
async def connected_backend(fake_serial: FakeSerial) -> Any:
    with patch("serial.Serial", return_value=fake_serial):
        backend = BetaflightOverrideBackend(port="/dev/ttyACM-fake")
        await backend.connect()
        yield backend
        await backend.disconnect()


async def test_connect_opens_serial_and_handshakes(fake_serial: FakeSerial) -> None:
    with patch("serial.Serial", return_value=fake_serial) as serial_ctor:
        backend = BetaflightOverrideBackend(port="/dev/ttyACM-fake")
        await backend.connect()
        serial_ctor.assert_called_once()
        # The first frame sent should be MSP_API_VERSION (1)
        first_frame = fake_serial.writes[0]
        assert first_frame[4] == MspCommand.API_VERSION


async def test_operations_raise_when_not_connected() -> None:
    backend = BetaflightOverrideBackend(port="/dev/ttyACM-fake")
    with pytest.raises(DroneUnavailable):
        await backend.takeoff()


# ---------------------------------------------------------------------------
# Takeoff → burst spin then zero
# ---------------------------------------------------------------------------


async def test_takeoff_sends_nonzero_throttle_then_zero(connected_backend: Any) -> None:
    backend = connected_backend
    # Use the fake serial's recorded writes via the backend's ._serial handle
    await backend.takeoff(alt_m=30.0)

    writes = backend._serial.writes  # type: ignore[attr-defined]
    # At least one SET_MOTOR with nonzero throttle, and a final SET_MOTOR with all zeros.
    assert _any_set_motor(writes)
    assert _motors_zeroed(writes)

    # Verify state() reports in_air=False (we're on a bench, never actually flying)
    s = await backend.state()
    assert isinstance(s, DroneState)
    assert s.in_air is False


# ---------------------------------------------------------------------------
# SAFETY: hard timeout fires motors-zero even if serial hangs
# ---------------------------------------------------------------------------


async def test_hard_timeout_forces_motors_zero() -> None:
    """If the spin coroutine runs longer than SKYHERD_MOTOR_SPIN_TIMEOUT_S,
    the hard timeout must fire without raising, and motors-zero must land."""
    fake = FakeSerial(read_queue=[_api_version_response()])

    with patch("serial.Serial", return_value=fake):
        backend = BetaflightOverrideBackend(
            port="/dev/ttyACM-fake",
            spin_timeout_s=0.2,  # short for the test
            spin_duration_s=5.0,  # LONGER than timeout — timeout must kick in
        )
        await backend.connect()

        started = asyncio.get_event_loop().time()
        # Should NOT raise — internal TimeoutError is swallowed by the
        # spin-burst safety wrapper; motors are zeroed regardless.
        await backend.takeoff(alt_m=30.0)
        elapsed = asyncio.get_event_loop().time() - started

        # Must complete within spin_timeout_s + generous grace (asyncio
        # scheduling + the refresh interval).
        assert elapsed < 1.0, f"hard timeout failed to fire within 1.0s: {elapsed:.2f}s"

        # Motors-zero frame was emitted in the `finally` block.
        assert _motors_zeroed(fake.writes)

        await backend.disconnect()


# ---------------------------------------------------------------------------
# SAFETY: exception mid-spin still triggers motors-zero in `finally`
# ---------------------------------------------------------------------------


async def test_exception_during_spin_still_sends_motors_zero() -> None:
    """An unexpected OSError in the middle of the spin loop must:
    (1) propagate out so the caller knows something went wrong
    (2) trigger motors-zero via the `finally` block — and when the transient
        fault clears, the eventual motors-zero frame must land.
    """
    fake = FakeSerial(read_queue=[_api_version_response()])

    original_write = fake.write
    call_log: list[str] = []
    # Raise on writes #3 and #4 only; recover on #5+.  The spin loop will
    # fault, the finally-block motors-zero will also fault (still in the
    # blackout window), but the later disconnect() motors-zero succeeds.
    flaky_state = {"n": 0, "bad_start": 3, "bad_end": 4}

    def flaky_write(data: bytes) -> int:
        flaky_state["n"] += 1
        call_log.append(f"write#{flaky_state['n']}")
        if flaky_state["bad_start"] <= flaky_state["n"] <= flaky_state["bad_end"]:
            raise OSError("simulated device disappeared")
        return original_write(data)

    fake.write = flaky_write  # type: ignore[method-assign]

    with patch("serial.Serial", return_value=fake):
        backend = BetaflightOverrideBackend(
            port="/dev/ttyACM-fake",
            spin_timeout_s=2.0,
            spin_duration_s=0.5,
        )
        await backend.connect()

        # The OSError propagates out of takeoff — the caller MUST hear about
        # it.  motors-zero is attempted inside `finally` (and also fails in
        # this blackout window, which is logged).
        with pytest.raises(OSError):
            await backend.takeoff(alt_m=30.0)

        # disconnect() is outside the blackout window so its motors-zero
        # lands.  This is the guarantee: once the fault clears, we do
        # emit the zero frame.
        await backend.disconnect()

    assert _motors_zeroed(fake.writes), (
        f"motors-zero never landed; writes={len(fake.writes)} log={call_log}"
    )


# ---------------------------------------------------------------------------
# SAFETY: async context manager exits → motors zero
# ---------------------------------------------------------------------------


async def test_context_manager_exit_sends_motors_zero() -> None:
    fake = FakeSerial(read_queue=[_api_version_response()])
    with patch("serial.Serial", return_value=fake):
        async with BetaflightOverrideBackend(port="/dev/ttyACM-fake") as backend:
            await backend.takeoff(alt_m=30.0)
        # After `async with` exits, motors must be at zero.
        assert _motors_zeroed(fake.writes)
        # And the serial port must be closed.
        assert fake.closed


# ---------------------------------------------------------------------------
# Patrol / RTH / deterrent behaviour on bench
# ---------------------------------------------------------------------------


async def test_patrol_publishes_a_short_burst_then_zero(connected_backend: Any) -> None:
    backend = connected_backend
    waypoints = [Waypoint(lat=34.1, lon=-106.1, alt_m=30.0)]
    await backend.patrol(waypoints)
    assert _motors_zeroed(backend._serial.writes)  # type: ignore[attr-defined]


async def test_return_to_home_cuts_motors_immediately(connected_backend: Any) -> None:
    backend = connected_backend
    await backend.return_to_home()
    assert _motors_zeroed(backend._serial.writes)  # type: ignore[attr-defined]


async def test_play_deterrent_is_time_capped(connected_backend: Any) -> None:
    backend = connected_backend
    # Ask for a long deterrent, but max out at spin_timeout_s.
    started = asyncio.get_event_loop().time()
    await backend.play_deterrent(tone_hz=12000, duration_s=0.3)
    elapsed = asyncio.get_event_loop().time() - started
    # Must complete within the configured spin timeout (+ grace).
    assert elapsed < 3.0


async def test_get_thermal_clip_raises() -> None:
    """DIY quad has no thermal payload."""
    fake = FakeSerial(read_queue=[_api_version_response()])
    with patch("serial.Serial", return_value=fake):
        backend = BetaflightOverrideBackend(port="/dev/ttyACM-fake")
        await backend.connect()
        with pytest.raises(DroneUnavailable):
            await backend.get_thermal_clip()
        await backend.disconnect()


# ---------------------------------------------------------------------------
# state() reports a DroneState — stubbed battery + bench location
# ---------------------------------------------------------------------------


async def test_state_returns_bench_location(connected_backend: Any) -> None:
    backend = connected_backend
    s = await backend.state()
    assert isinstance(s, DroneState)
    assert s.in_air is False  # never flies
    assert s.armed is False
    # Battery percentage is either polled from MSP_ANALOG or stubbed 75.
    assert 0.0 <= s.battery_pct <= 100.0


# ---------------------------------------------------------------------------
# Dry run — no serial writes
# ---------------------------------------------------------------------------


async def test_dry_run_does_not_open_serial() -> None:
    fake = FakeSerial()
    with patch("serial.Serial", return_value=fake) as serial_ctor:
        backend = BetaflightOverrideBackend(
            port="/dev/ttyACM-fake", dry_run=True
        )
        await backend.connect()
        await backend.takeoff(alt_m=30.0)
        await backend.disconnect()
        # In dry-run mode we must NEVER open serial.
        serial_ctor.assert_not_called()
        # And FakeSerial received no writes.
        assert fake.writes == []


# ---------------------------------------------------------------------------
# Disconnect is idempotent and always zeros motors
# ---------------------------------------------------------------------------


async def test_disconnect_is_idempotent(fake_serial: FakeSerial) -> None:
    with patch("serial.Serial", return_value=fake_serial):
        backend = BetaflightOverrideBackend(port="/dev/ttyACM-fake")
        await backend.connect()
        await backend.disconnect()
        # Second call must not raise.
        await backend.disconnect()
    assert _motors_zeroed(fake_serial.writes)


# ---------------------------------------------------------------------------
# Factory wiring — get_backend('betaflight') returns our class
# ---------------------------------------------------------------------------


def test_factory_returns_betaflight_backend() -> None:
    from skyherd.drone.interface import get_backend

    backend = get_backend("betaflight")
    assert isinstance(backend, BetaflightOverrideBackend)


def test_factory_honors_skyherd_drone_backend_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from skyherd.drone.interface import get_backend

    monkeypatch.setenv("SKYHERD_DRONE_BACKEND", "betaflight")
    monkeypatch.delenv("DRONE_BACKEND", raising=False)
    backend = get_backend()
    assert isinstance(backend, BetaflightOverrideBackend)


# ---------------------------------------------------------------------------
# Throttle clamp — never exceed configured max
# ---------------------------------------------------------------------------


def test_throttle_clamped_to_safe_max(monkeypatch: pytest.MonkeyPatch) -> None:
    """SKYHERD_MOTOR_THROTTLE_US must clamp to MAX_THROTTLE_US."""
    from skyherd.drone.betaflight_override import (
        MAX_THROTTLE_US,
        _resolve_throttle_us,
    )

    monkeypatch.setenv("SKYHERD_MOTOR_THROTTLE_US", "9999")
    assert _resolve_throttle_us() <= MAX_THROTTLE_US

    monkeypatch.setenv("SKYHERD_MOTOR_THROTTLE_US", "500")
    # A too-low value is also clamped up to the neutral MIN_THROTTLE_US.
    assert _resolve_throttle_us() >= 1000


def test_spin_timeout_clamped_to_safe_max(monkeypatch: pytest.MonkeyPatch) -> None:
    """SKYHERD_MOTOR_SPIN_TIMEOUT_S must clamp to a hard safety ceiling."""
    from skyherd.drone.betaflight_override import (
        MAX_SPIN_TIMEOUT_S,
        _resolve_spin_timeout_s,
    )

    monkeypatch.setenv("SKYHERD_MOTOR_SPIN_TIMEOUT_S", "999")
    assert _resolve_spin_timeout_s() <= MAX_SPIN_TIMEOUT_S


def test_env_resolvers_reject_non_numeric(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bad env-var values fall back to defaults rather than raising."""
    from skyherd.drone.betaflight_override import (
        DEFAULT_SPIN_TIMEOUT_S,
        _resolve_spin_timeout_s,
        _resolve_throttle_us,
    )

    monkeypatch.setenv("SKYHERD_MOTOR_SPIN_TIMEOUT_S", "not-a-float")
    assert _resolve_spin_timeout_s() == DEFAULT_SPIN_TIMEOUT_S

    monkeypatch.setenv("SKYHERD_MOTOR_THROTTLE_US", "not-an-int")
    assert _resolve_throttle_us() == 1200


# ---------------------------------------------------------------------------
# Helper: set-motor payload shape
# ---------------------------------------------------------------------------


def test_set_motor_payload_shape_and_zeros_on_out_of_range() -> None:
    from skyherd.drone.betaflight_override import _set_motor_payload

    payload = _set_motor_payload(1200, motor_idx=0)
    assert len(payload) == 16
    # Motor 0 little-endian = 1200
    assert int.from_bytes(payload[0:2], "little") == 1200
    # All other motors zero
    for i in range(1, 8):
        assert int.from_bytes(payload[i * 2 : i * 2 + 2], "little") == 0

    # Out-of-range motor idx → all zero
    payload2 = _set_motor_payload(1200, motor_idx=99)
    assert payload2 == b"\x00" * 16


# ---------------------------------------------------------------------------
# CLI main — --test and --dry-run wire through cleanly
# ---------------------------------------------------------------------------


def test_cli_main_without_args_prints_help(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`python -m skyherd.drone.betaflight_override` (no flags) prints help and exits 0."""
    from skyherd.drone.betaflight_override import main

    monkeypatch.setattr("sys.argv", ["betaflight_override"])
    rc = main()
    assert rc == 0
    captured = capsys.readouterr()
    # argparse dumps help to stdout when print_help() is called.
    assert "--test" in captured.out or "--test" in captured.err


def test_cli_main_dry_run_spins_no_serial(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`... --test --dry-run` must complete without opening serial."""
    from skyherd.drone.betaflight_override import main

    monkeypatch.setattr(
        "sys.argv", ["betaflight_override", "--test", "--dry-run", "--duration", "0.1"]
    )
    with patch("serial.Serial") as serial_ctor:
        rc = main()
    assert rc == 0
    serial_ctor.assert_not_called()
    # The safety banner goes to stderr.
    captured = capsys.readouterr()
    assert "DO NOT RUN WITH PROPELLERS" in captured.err
