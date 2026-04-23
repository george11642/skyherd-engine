#!/usr/bin/env python3
"""SITL smoke wrapper — runs skyherd-sitl-e2e --emulator and asserts evidence events.

Usage:
  python3 scripts/sitl_smoke.py

Exits 0 iff all 5 required evidence events appear in the subprocess stdout:
  CONNECTED, TAKEOFF OK, PATROL OK, RTL OK, E2E PASS

Consumed by: Makefile `sitl-smoke` target (Plan 03) and the `sitl-smoke`
CI job in `.github/workflows/ci.yml` (this plan).

BLD-04 proof: real MAVLink mission over UDP via the in-process pymavlink emulator.
No Docker, no `ardupilot/ardupilot-sitl` image — that image does not exist on
Docker Hub (verified 2026-04-22).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

REQUIRED_EVENTS: tuple[str, ...] = (
    "CONNECTED",
    "TAKEOFF OK",
    "PATROL OK",
    "RTL OK",
    "E2E PASS",
)


def main() -> None:
    try:
        result = subprocess.run(
            ["uv", "run", "skyherd-sitl-e2e", "--emulator", "--takeoff-alt", "15.0"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        print("SITL smoke FAIL — skyherd-sitl-e2e timed out after 180s", file=sys.stderr)
        sys.exit(1)

    output = result.stdout + result.stderr
    missing = [evt for evt in REQUIRED_EVENTS if evt not in output]

    if result.returncode != 0:
        print(
            f"SITL smoke FAIL — skyherd-sitl-e2e exited {result.returncode}",
            file=sys.stderr,
        )
        print(f"  missing events: {missing}", file=sys.stderr)
        print(f"  last output lines:\n{output[-600:]}", file=sys.stderr)
        sys.exit(1)

    if missing:
        print(
            f"SITL smoke FAIL — {len(missing)} required evidence event(s) missing: {missing}",
            file=sys.stderr,
        )
        print(f"  full output tail:\n{output[-600:]}", file=sys.stderr)
        sys.exit(1)

    print(f"SITL smoke OK — all {len(REQUIRED_EVENTS)} evidence events verified.")
    for evt in REQUIRED_EVENTS:
        print(f"  [OK] {evt}")
    sys.exit(0)


if __name__ == "__main__":
    main()
