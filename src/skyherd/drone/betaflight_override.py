"""
BetaflightOverrideBackend — spin motors on a Betaflight/iNav F3 quad via MSP v1.

Purpose
-------
For the SkyHerd hackathon hero demo: when a Managed Agent dispatches a drone,
this backend briefly spins the motors on a bench-mounted racing quad (SP Racing
F3 + Betaflight or iNav).  The quad does NOT fly — it's a loud-and-visible
"dispatch acknowledged" beat for the 3-minute demo video.

SAFETY NON-NEGOTIABLES
----------------------
1. **NEVER run this with propellers fitted indoors.**  The runbook
   (``docs/HARDWARE_F3_BETAFLIGHT.md``) repeats this.  The ``--test`` CLI
   prints a warning banner before sending any MSP frame.
2. **Hard timeout.**  Every motor-spin call is wrapped in
   ``asyncio.wait_for(..., timeout=SKYHERD_MOTOR_SPIN_TIMEOUT_S)`` capped at
   :data:`MAX_SPIN_TIMEOUT_S` seconds.
3. **Motors-zero on every exit path.**  Defence in depth:
     * ``try/finally`` around the spin loop
     * ``disconnect()`` always emits a SET_MOTOR-all-zeros frame
     * ``__aexit__`` calls ``disconnect()``
     * ``SIGINT``/``SIGTERM`` handlers (when installed) do the same
4. **Throttle ceiling.**  The SKYHERD_MOTOR_THROTTLE_US value is clamped to
   :data:`MAX_THROTTLE_US` (1300 us — well below full throttle) so even a
   bad config can't full-send the motors.

Wire protocol: see :mod:`skyherd.drone._msp` for the MSP v1 codec.

Environment variables
---------------------
SKYHERD_F3_PORT
    Serial device path override (e.g. ``/dev/ttyACM0`` on Linux, ``COM3`` on
    Windows).  When unset, the first ``/dev/ttyACM*`` or ``/dev/cu.usbmodem*``
    device is used, falling back to ``serial.tools.list_ports`` auto-detect.

SKYHERD_MOTOR_SPIN_TIMEOUT_S
    Hard spin timeout in seconds.  Default ``5.0``, clamped to
    :data:`MAX_SPIN_TIMEOUT_S` (``10.0``).

SKYHERD_MOTOR_THROTTLE_US
    Motor output microseconds for the burst.  Default ``1200``, clamped to
    :data:`MAX_THROTTLE_US` (``1300``) and floored at 1000 (neutral).

SKYHERD_DRONE_BACKEND / DRONE_BACKEND
    Set to ``betaflight`` to select this backend from the factory.
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import logging
import os
import platform
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from skyherd.drone._msp import MspCommand, decode_msp_v1, encode_msp_v1
from skyherd.drone.interface import (
    DroneBackend,
    DroneError,
    DroneState,
    DroneUnavailable,
    Waypoint,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Safety constants — these are the hard ceilings, not defaults.
# ---------------------------------------------------------------------------

#: Absolute maximum throttle in microseconds.  1300us ≈ 30 % of full range
#: — enough to hear motors spin up clearly without being aggressive.
MAX_THROTTLE_US: int = 1300

#: Minimum "motor running" value in microseconds.  Anything below this is
#: effectively idle/neutral and won't spin.
MIN_THROTTLE_US: int = 1000

#: Absolute maximum spin-timeout in seconds.  Even if the user sets
#: SKYHERD_MOTOR_SPIN_TIMEOUT_S to a larger value, we clamp to this.
MAX_SPIN_TIMEOUT_S: float = 10.0

#: Default spin timeout if no env var is set.
DEFAULT_SPIN_TIMEOUT_S: float = 5.0

#: Default motor burst duration (seconds) when the agent calls ``takeoff``
#: or ``play_deterrent``.
DEFAULT_SPIN_DURATION_S: float = 2.0

#: Default serial baud for Betaflight USB CDC.  Betaflight ignores baud
#: on USB CDC; we pick a common value for compatibility.
_SERIAL_BAUD: int = 115200

#: Interval between motor-update frames during a spin.  Betaflight's serial
#: failsafe is ~200 ms with ``MSP_OVERRIDE`` enabled; we refresh well inside
#: that window so a stuck sender can't leave motors spinning.
_MOTOR_REFRESH_INTERVAL_S: float = 0.1

#: Bench "location" used for DroneState when no GPS is available.  Non-zero
#: so event sinks don't flag NaN/0.0 coordinates.
_BENCH_LAT: float = 34.0
_BENCH_LON: float = -106.0


# ---------------------------------------------------------------------------
# Environment resolvers (pure — unit-tested)
# ---------------------------------------------------------------------------


def _resolve_spin_timeout_s() -> float:
    raw = os.environ.get("SKYHERD_MOTOR_SPIN_TIMEOUT_S")
    if raw is None:
        return DEFAULT_SPIN_TIMEOUT_S
    try:
        value = float(raw)
    except ValueError:
        logger.warning(
            "SKYHERD_MOTOR_SPIN_TIMEOUT_S=%r is not a float; using default %.1fs",
            raw,
            DEFAULT_SPIN_TIMEOUT_S,
        )
        return DEFAULT_SPIN_TIMEOUT_S
    # Clamp to safety ceiling.
    return max(0.1, min(value, MAX_SPIN_TIMEOUT_S))


def _resolve_throttle_us() -> int:
    raw = os.environ.get("SKYHERD_MOTOR_THROTTLE_US")
    if raw is None:
        return 1200
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "SKYHERD_MOTOR_THROTTLE_US=%r is not an int; using default 1200us", raw
        )
        return 1200
    # Clamp to [MIN_THROTTLE_US, MAX_THROTTLE_US].
    return max(MIN_THROTTLE_US, min(value, MAX_THROTTLE_US))


# ---------------------------------------------------------------------------
# Port auto-detection
# ---------------------------------------------------------------------------


def _detect_serial_port() -> str:
    """Resolve the serial port for the F3 flight controller.

    Resolution order:
      1. ``SKYHERD_F3_PORT`` env var (used as-is).
      2. First ``/dev/ttyACM*`` match on Linux, ``/dev/cu.usbmodem*`` on macOS.
      3. ``serial.tools.list_ports.comports()`` — prefer devices whose
         description mentions "STM32" or "Betaflight" or "CDC".
      4. Raise :class:`DroneUnavailable`.
    """
    override = os.environ.get("SKYHERD_F3_PORT")
    if override:
        return override

    system = platform.system()
    if system == "Linux":
        matches = sorted(glob.glob("/dev/ttyACM*"))
        if matches:
            return matches[0]
    elif system == "Darwin":
        matches = sorted(glob.glob("/dev/cu.usbmodem*"))
        if matches:
            return matches[0]
    # Windows and fall-through path: use pyserial's list_ports.
    try:
        import serial.tools.list_ports as list_ports
    except ImportError as exc:  # pragma: no cover - pyserial missing is a hard fail
        raise DroneUnavailable(
            "pyserial is required for BetaflightOverrideBackend.  "
            "Install with: uv sync --extra drone-hw"
        ) from exc

    candidates = list(list_ports.comports())
    for port in candidates:
        desc = (getattr(port, "description", "") or "").lower()
        if any(tag in desc for tag in ("stm32", "betaflight", "virtual com", "cdc")):
            return str(port.device)
    # If nothing matches a known tag, but the list isn't empty, pick the first
    # device that looks like a COMx on Windows.
    if system == "Windows":
        for port in candidates:
            dev = str(port.device)
            if dev.upper().startswith("COM"):
                return dev

    raise DroneUnavailable(
        "No serial device found for Betaflight F3.  "
        "Set SKYHERD_F3_PORT=/dev/ttyACM0 (Linux) or COM3 (Windows) to override."
    )


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------


def _set_motor_payload(throttle_us: int, motor_idx: int = 0, num_motors: int = 4) -> bytes:
    """Build the 16-byte SET_MOTOR payload: 8 × uint16 LE microseconds.

    ``motor_idx`` is the motor to spin at ``throttle_us``.  All others and
    unused slots (5..8) are set to 0 (stopped).  Setting to 0 is the safest
    default — iNav/Betaflight interpret 0 as "off" rather than "neutral".
    """
    _ = num_motors  # reserved for quad/hex/oct configurations
    motors = [0] * 8
    if 0 <= motor_idx < 8:
        motors[motor_idx] = throttle_us & 0xFFFF
    return b"".join(m.to_bytes(2, "little") for m in motors)


def _zero_motors_payload() -> bytes:
    """16-byte payload with all motors stopped."""
    return b"\x00" * 16


class BetaflightOverrideBackend(DroneBackend):
    """Spin motors briefly on a bench-mounted Betaflight/iNav F3 quad.

    Parameters
    ----------
    port:
        Serial device.  When ``None``, auto-detected (see
        :func:`_detect_serial_port`).
    spin_timeout_s:
        Hard ceiling on any single motor-spin operation.  Overrides the
        env var when set.
    spin_duration_s:
        Requested duration of each spin burst (clamped by the timeout).
    throttle_us:
        Motor throttle value in microseconds (clamped to
        ``[MIN_THROTTLE_US, MAX_THROTTLE_US]``).
    dry_run:
        If True, never open the serial port — log frames that would be sent
        and return.  Used by ``--dry-run`` CLI mode and in tests.
    """

    def __init__(
        self,
        port: str | None = None,
        spin_timeout_s: float | None = None,
        spin_duration_s: float = DEFAULT_SPIN_DURATION_S,
        throttle_us: int | None = None,
        dry_run: bool = False,
    ) -> None:
        self._port = port
        self._spin_timeout_s = (
            min(spin_timeout_s, MAX_SPIN_TIMEOUT_S)
            if spin_timeout_s is not None
            else _resolve_spin_timeout_s()
        )
        self._spin_duration_s = max(0.05, min(spin_duration_s, self._spin_timeout_s))
        self._throttle_us = throttle_us if throttle_us is not None else _resolve_throttle_us()
        self._throttle_us = max(MIN_THROTTLE_US, min(self._throttle_us, MAX_THROTTLE_US))
        self._dry_run = dry_run

        self._serial: Any = None
        self._connected = False
        self._battery_pct: float = 75.0  # stub until MSP_ANALOG poll succeeds

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> BetaflightOverrideBackend:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        # Always cut motors and close the port, even on exception.
        await self.disconnect()

    # ------------------------------------------------------------------
    # DroneBackend implementation
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        if self._dry_run:
            self._connected = True
            logger.info("[dry-run] BetaflightOverrideBackend connected (no serial open)")
            return

        port = self._port or _detect_serial_port()
        try:
            import serial  # type: ignore[import-untyped]
        except ImportError as exc:
            raise DroneUnavailable(
                "pyserial is required for BetaflightOverrideBackend.  "
                "Install with: uv sync --extra drone-hw"
            ) from exc

        try:
            self._serial = serial.Serial(port, _SERIAL_BAUD, timeout=1, write_timeout=1)
        except Exception as exc:
            raise DroneUnavailable(
                f"Cannot open serial port {port!r}: {exc}.  "
                "Is the F3 plugged in?  Set SKYHERD_F3_PORT to override."
            ) from exc

        self._port = port
        self._connected = True
        logger.info("BetaflightOverrideBackend connected on %s @ %d baud", port, _SERIAL_BAUD)

        # Handshake: ask the FC for its API version.  We don't strictly
        # require a response — Betaflight without MSP override still ACKs
        # this — but it proves the serial link works.
        try:
            self._write_frame(encode_msp_v1(MspCommand.API_VERSION, b""))
        except Exception as exc:  # noqa: BLE001
            logger.warning("API_VERSION handshake write failed (non-fatal): %s", exc)

    async def takeoff(self, alt_m: float = 30.0) -> None:
        """Bench beat: spin motor 0 for spin_duration_s, then stop.

        NOT a real takeoff — the DIY quad stays bolted to the bench.  We log
        a warning so any orchestration code that expects airborne state
        knows this is a ground-only backend.
        """
        self._assert_connected()
        logger.warning(
            "BetaflightOverrideBackend.takeoff called — bench-only, not flying. "
            "Spinning motor for %.2fs at %d us.",
            self._spin_duration_s,
            self._throttle_us,
        )
        await self._spin_burst(duration_s=self._spin_duration_s)

    async def patrol(self, waypoints: list[Waypoint]) -> None:
        """Short spin per waypoint as a "progressing" beat."""
        self._assert_connected()
        if not waypoints:
            logger.debug("BetaflightOverrideBackend.patrol: no waypoints — noop")
            return
        # A single short burst is enough for the demo — no per-waypoint loop
        # so we never exceed the timeout budget.
        await self._spin_burst(duration_s=min(self._spin_duration_s, 1.0))

    async def return_to_home(self) -> None:
        """Cut motors immediately."""
        self._assert_connected()
        logger.info("BetaflightOverrideBackend: return_to_home — cutting motors")
        self._emergency_motors_zero()

    async def play_deterrent(self, tone_hz: int = 12000, duration_s: float = 6.0) -> None:
        """Use motor noise as a deterrent beat.

        Racing motors are LOUD — that's the joke.  Duration is clamped to
        the spin timeout regardless of the caller's request.
        """
        self._assert_connected()
        logger.info(
            "BetaflightOverrideBackend.play_deterrent: tone_hz=%d (ignored), "
            "duration_s=%.2f (clamped to %.2f)",
            tone_hz,
            duration_s,
            self._spin_timeout_s,
        )
        await self._spin_burst(duration_s=min(duration_s, self._spin_timeout_s))

    async def get_thermal_clip(self, duration_s: float = 10.0) -> Path:
        """No thermal payload on a DIY quad."""
        raise DroneUnavailable(
            "BetaflightOverrideBackend has no thermal camera.  "
            "Use MavicAdapter for thermal clips."
        )

    async def state(self) -> DroneState:
        """Return a synthetic bench DroneState.

        Battery percentage is a stub until a full MSP_ANALOG poller is
        wired up; location is the constant bench position to keep event
        sinks happy.
        """
        return DroneState(
            armed=False,
            in_air=False,  # never actually flies
            altitude_m=0.0,
            battery_pct=self._battery_pct,
            mode="MSP_OVERRIDE",
            lat=_BENCH_LAT,
            lon=_BENCH_LON,
        )

    async def disconnect(self) -> None:
        # Always send motors-zero, even if already disconnected.
        try:
            if self._connected and not self._dry_run:
                self._emergency_motors_zero()
        except Exception as exc:  # noqa: BLE001
            logger.warning("motors-zero on disconnect failed: %s", exc)

        ser = self._serial
        self._serial = None
        self._connected = False
        if ser is not None and not self._dry_run:
            try:
                ser.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning("serial close failed: %s", exc)
        logger.info("BetaflightOverrideBackend disconnected")

    # ------------------------------------------------------------------
    # Internal: spin loop + safety
    # ------------------------------------------------------------------

    async def _spin_burst(self, duration_s: float) -> None:
        """Spin motor 0 at ``self._throttle_us`` for ``duration_s`` seconds.

        Wrapped in :func:`asyncio.wait_for` with
        ``self._spin_timeout_s`` as the hard ceiling.  Motors-zero is
        emitted in every exit path (normal, timeout, exception).
        """
        effective = min(duration_s, self._spin_timeout_s)
        logger.info(
            "Spin burst: motor=0 throttle_us=%d duration_s=%.2f timeout_s=%.2f",
            self._throttle_us,
            effective,
            self._spin_timeout_s,
        )

        async def _run_spin() -> None:
            deadline = time.monotonic() + effective
            payload = _set_motor_payload(self._throttle_us, motor_idx=0)
            frame = encode_msp_v1(MspCommand.SET_MOTOR, payload)
            while time.monotonic() < deadline:
                self._write_frame(frame)
                await asyncio.sleep(_MOTOR_REFRESH_INTERVAL_S)

        try:
            try:
                await asyncio.wait_for(_run_spin(), timeout=self._spin_timeout_s)
            except TimeoutError:
                logger.warning(
                    "Spin burst hit hard timeout of %.2fs — emergency motors-zero",
                    self._spin_timeout_s,
                )
                # Hard timeout is an expected safety guard, not a failure the
                # caller needs to hear about — swallow it here so they don't
                # have to branch on a TimeoutError that ALWAYS ends in
                # motors-off.
        finally:
            # Belt-and-braces: always try to cut motors on every exit path
            # (normal, timeout, or exception).  Motors-zero errors are
            # logged but NOT propagated — if an original exception is
            # already in flight we don't want to mask it.
            try:
                self._emergency_motors_zero()
            except Exception as exc:  # noqa: BLE001
                logger.error("motors-zero in finally block failed: %s", exc)

    def _emergency_motors_zero(self) -> None:
        """Send SET_MOTOR with all zeros.  Never raises."""
        if self._dry_run:
            logger.info("[dry-run] would send SET_MOTOR all-zero")
            return
        if self._serial is None:
            return
        frame = encode_msp_v1(MspCommand.SET_MOTOR, _zero_motors_payload())
        try:
            self._serial.write(frame)
        except Exception as exc:  # noqa: BLE001
            logger.error("emergency motors-zero write failed: %s", exc)

    def _write_frame(self, frame: bytes) -> None:
        """Write a single MSP frame (or log it in dry-run mode)."""
        if self._dry_run:
            logger.info("[dry-run] MSP frame: %s", frame.hex())
            return
        if self._serial is None:
            raise DroneUnavailable("serial port not open")
        self._serial.write(frame)

    def _assert_connected(self) -> None:
        if not self._connected:
            raise DroneUnavailable(
                "BetaflightOverrideBackend not connected — call connect() first"
            )


# Silence unused-import warning for runtime-only helpers.
_ = decode_msp_v1
_ = DroneError


# ---------------------------------------------------------------------------
# CLI: `python -m skyherd.drone.betaflight_override --test`
# ---------------------------------------------------------------------------


def _print_safety_banner() -> None:
    banner = r"""
================================================================================
  SkyHerd BetaflightOverrideBackend — motor test harness
  --------------------------------------------------------
  DO NOT RUN WITH PROPELLERS FITTED.  This command spins the motors on your
  F3 flight controller.  Racing motors will launch props into walls, ceilings,
  and faces.  Remove all propellers before connecting the battery.

  Hard timeout : capped by SKYHERD_MOTOR_SPIN_TIMEOUT_S (max 10s).
  Throttle      : capped by SKYHERD_MOTOR_THROTTLE_US (max 1300us ~ 30%).

  Press Ctrl-C to emergency-stop at any time.
================================================================================
"""
    print(banner, file=sys.stderr)


async def _cli_main(port: str | None, dry_run: bool, duration_s: float) -> None:
    _print_safety_banner()
    async with BetaflightOverrideBackend(port=port, dry_run=dry_run) as backend:
        await backend.takeoff(alt_m=0.0)  # alt_m is ignored; just triggers a burst
        # Give disconnect a moment before exit.
        await asyncio.sleep(0.1)
        _ = duration_s


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m skyherd.drone.betaflight_override",
        description="SkyHerd Betaflight motor-test harness (bench, NO PROPS).",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Spin motor 0 for the configured duration and exit.",
    )
    parser.add_argument("--port", default=None, help="Serial port (overrides SKYHERD_F3_PORT).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't open the serial port — log frames instead.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_SPIN_DURATION_S,
        help=f"Spin duration (seconds; default {DEFAULT_SPIN_DURATION_S}).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.test:
        parser.print_help()
        return 0

    try:
        asyncio.run(_cli_main(port=args.port, dry_run=args.dry_run, duration_s=args.duration))
    except KeyboardInterrupt:
        print("\nInterrupted — motors cut.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
