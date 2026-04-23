"""SITL failure-path test — emulator broken mid-mission MUST produce loud failure.

Complements tests/drone/test_sitl_e2e.py by asserting the INVERSE:
if the MAVLink stream drops during an active mission, run_sitl_e2e must
raise or return success=False.  This locks the BLD-04 CI job's loud-failure
behavior per RESEARCH.md Pitfall 6: continue-on-error must NOT hide real
SITL regressions on the emulator path.
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest

from skyherd.drone.sitl_emulator import MavlinkSitlEmulator

_ENABLED = os.environ.get("SITL_EMULATOR", "0") == "1" or os.environ.get("SITL", "0") == "1"

pytestmark = pytest.mark.skipif(
    not _ENABLED,
    reason=(
        "SITL failure-path test skipped — set SITL_EMULATOR=1 (built-in emulator) "
        "or SITL=1 (real Docker SITL)."
    ),
)

_BASE_PORT = 14560  # matches test_sitl_e2e.py convention
_OFFSET = 9  # sits clear of existing offsets (0..5) used by happy-path tests


def _ports(offset: int) -> tuple[int, int]:
    """Return (gcs_port, vehicle_port) for test slot *offset*."""
    return _BASE_PORT + offset * 2, _BASE_PORT + offset * 2 + 1


async def test_sitl_smoke_handshake_break_produces_failure() -> None:
    """Breaking the MAVLink stream mid-mission must raise or return success=False.

    BLD-04 loud-failure discipline: the emulator-mode CI job has no
    continue-on-error, so a genuine SITL regression must fail CI.
    """
    from skyherd.drone.e2e import run_sitl_e2e

    gcs_port, vehicle_port = _ports(_OFFSET)

    emu = MavlinkSitlEmulator(
        gcs_host="127.0.0.1",
        gcs_port=gcs_port,
        vehicle_port=vehicle_port,
    )
    emu.start()
    time.sleep(0.5)

    async def _break_stream_soon() -> None:
        await asyncio.sleep(0.8)  # let handshake begin, then yank the rug
        emu.stop()

    breaker = asyncio.create_task(_break_stream_soon())

    caught_exception: Exception | None = None
    result: dict | None = None
    try:
        result = await run_sitl_e2e(
            port=gcs_port,
            takeoff_alt_m=15.0,
            emulator=False,  # do NOT let run_sitl_e2e spin up its own; use ours
        )
    except Exception as exc:
        caught_exception = exc
    finally:
        try:
            emu.stop()
        except Exception:
            pass
        if not breaker.done():
            breaker.cancel()
            try:
                await breaker
            except (asyncio.CancelledError, Exception):
                pass

    # Failure MUST surface — either as an exception or as success=False.
    if caught_exception is not None:
        assert True, f"run_sitl_e2e raised as expected: {caught_exception!r}"
    else:
        assert result is not None, "no result and no exception — impossible"
        assert result.get("success") is False, (
            f"expected success=False after mid-mission emulator kill, got {result}"
        )
