# Phase 6: SITL-CI & Determinism Gate - Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 6 (2 new scripts, 1 extended test, 1 new test, 2 config edits)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/sitl_smoke.py` | utility/script | request-response (subprocess invoke + stdout parse) | `scripts/build-replay.py` | role-match |
| `scripts/gate_check.py` | utility/script | batch (run N checks, emit table) | `scripts/build-replay.py` | role-match |
| `tests/test_determinism_e2e.py` | test | batch (N subprocess runs, hash compare) | same file (extend) | exact |
| `tests/drone/test_sitl_smoke_failure.py` | test | request-response (failure path assertion) | `tests/drone/test_sitl_e2e.py` | exact |
| `.github/workflows/ci.yml` | config | event-driven (push/PR trigger) | same file (extend) | exact |
| `Makefile` | config | batch (target orchestration) | same file (extend) | exact |

---

## Pattern Assignments

### `scripts/sitl_smoke.py` (utility/script, request-response)

**Analog:** `scripts/build-replay.py`

**Imports pattern** (`scripts/build-replay.py` lines 1-18):
```python
#!/usr/bin/env python3
"""<one-line docstring>.

Usage:
  python3 scripts/<name>.py

<extended description>
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
```

**Core subprocess-invoke pattern** (`scripts/build-replay.py` lines 33-43):
```python
def _run_demo() -> None:
    print("No seed-42 runs found — running `uv run skyherd-demo play all --seed 42` ...")
    try:
        subprocess.run(
            ["uv", "run", "skyherd-demo", "play", "all", "--seed", "42"],
            cwd=REPO_ROOT,
            check=True,
            timeout=300,
        )
    except Exception as exc:
        print(f"WARNING: demo run failed ({exc}); will use synthetic events.", file=sys.stderr)
```

**Exit-code pattern** (`scripts/build-replay.py` lines 186-194 — `render_pdf.py` variant):
```python
def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: ...", file=sys.stderr)
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
```

**Key difference for `sitl_smoke.py`:** Use `subprocess.run(..., capture_output=True, text=True)` (not `check=True`) so stdout can be inspected for evidence events before deciding exit code. Print each evidence event as it is verified. Call `sys.exit(1)` if any required event is missing from stdout. Total target: ~30 lines.

**Evidence events to assert** (from `src/skyherd/drone/e2e.py` lines 130-164):
- `CONNECTED`, `TAKEOFF OK`, `PATROL OK`, `RTL OK`, `E2E PASS`

---

### `scripts/gate_check.py` (utility/script, batch)

**Analog:** `scripts/build-replay.py`

**Imports pattern** (`scripts/build-replay.py` lines 1-18):
```python
#!/usr/bin/env python3
"""<docstring>..."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
```

**Batch-check-and-print pattern** (`scripts/build-replay.py` `main()` + loop structure, lines 165-218):
```python
def main() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    # ... setup ...

    results_out: list[dict] = []
    for item in ITEMS:
        # process
        results_out.append({...})
        print(f"  {item}: {count} events from {path.name}")

    # Summary at end
    print(f"\nWrote {OUT_FILE}")
    print(f"  count: {len(results_out)}")
```

**Subprocess capture-output pattern** (reuse `_run_demo` shape with capture):
```python
def _run_cmd(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    """Run a command and return (returncode, combined_output)."""
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout + result.stderr
```

**Gate table output format** (from RESEARCH.md Pattern 4):
```python
GATE_ITEMS = [
    ("agents_mesh",   "5 Managed Agents on shared MQTT",      _check_agents_mesh),
    ("sensors",       "7+ sim sensors emitting",              _check_sensors),
    # ... (10 total)
]
# Each _check_* returns ("GREEN" | "YELLOW" | "RED", evidence_str)
```

**Exit-code gate** — `sys.exit(0)` iff all 10 GREEN, else `sys.exit(1)`.

---

### `tests/test_determinism_e2e.py` (test, batch — EXTEND existing file)

**Analog:** same file — `tests/test_determinism_e2e.py`

**Full existing file to build on** (lines 1-75 — read above). Keep all shared helpers; replace or extend the test function.

**Helper functions to reuse verbatim** (lines 20-52):
```python
DETERMINISM_SANITIZE: list[tuple[str, str]] = [
    (r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.Z+-]+", ""),
    (r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", ""),
    (r"\b[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?\b", ""),
    (r"\bsession-[a-f0-9]{8}\b", "session-XXXXXXXX"),
]

def _sanitize(text: str) -> str: ...
def _md5(text: str) -> str: ...
def _run_demo(seed: int) -> str: ...
```

**Existing test to REPLACE** (lines 60-74 — 2-run variant):
```python
@pytest.mark.slow
def test_demo_seed42_is_deterministic() -> None:
    """Two back-to-back seed=42 runs ..."""
    run_a = _sanitize(_run_demo(42))
    run_b = _sanitize(_run_demo(42))
    md5_a = _md5(run_a)
    md5_b = _md5(run_b)
    assert md5_a == md5_b, ...
```

**Replacement pattern** (RESEARCH.md Pattern 3 — N=3 in-body loop):
```python
@pytest.mark.slow
def test_demo_seed42_is_deterministic_3x() -> None:
    """Three back-to-back seed=42 runs must produce identical sanitized output."""
    hashes: list[str] = []
    for i in range(3):
        sanitized = _sanitize(_run_demo(42))
        hashes.append(_md5(sanitized))

    assert len(set(hashes)) == 1, (
        f"Determinism check failed across 3 runs:\n"
        f"  run_0: {hashes[0]}\n"
        f"  run_1: {hashes[1]}\n"
        f"  run_2: {hashes[2]}\n"
        "All three sanitized md5s must match."
    )
```

**Do NOT use `pytest.mark.parametrize`** — parametrize runs 3 independent test IDs that cannot assert cross-run identity (per RESEARCH.md anti-patterns).

---

### `tests/drone/test_sitl_smoke_failure.py` (test, request-response — NEW)

**Analog:** `tests/drone/test_sitl_e2e.py`

**Skip guard pattern** (`tests/drone/test_sitl_e2e.py` lines 30-38):
```python
_ENABLED = os.environ.get("SITL_EMULATOR", "0") == "1" or os.environ.get("SITL", "0") == "1"

pytestmark = pytest.mark.skipif(
    not _ENABLED,
    reason=(
        "SITL e2e tests skipped — set SITL_EMULATOR=1 (built-in emulator) "
        "or SITL=1 (real Docker SITL)."
    ),
)
```

**Port isolation pattern** (`tests/drone/test_sitl_e2e.py` lines 44-49):
```python
_BASE_PORT = 14560  # well away from 14540 production port

def _ports(offset: int) -> tuple[int, int]:
    """Return (gcs_port, vehicle_port) for test slot *offset*."""
    return _BASE_PORT + offset * 2, _BASE_PORT + offset * 2 + 1
```

**Imports pattern** (`tests/drone/test_sitl_e2e.py` lines 18-25):
```python
from __future__ import annotations

import os
import time

import pytest

from skyherd.drone.interface import Waypoint
from skyherd.drone.pymavlink_backend import PymavlinkBackend
from skyherd.drone.sitl_emulator import MavlinkSitlEmulator
```

**Emulator lifecycle pattern** (`tests/drone/test_sitl_e2e.py` lines 59-69):
```python
@pytest.fixture(scope="module")
def shared_emulator():
    emu = MavlinkSitlEmulator(
        gcs_host="127.0.0.1",
        gcs_port=_SHARED_GCS_PORT,
        vehicle_port=_SHARED_VEHICLE_PORT,
    )
    emu.start()
    time.sleep(0.5)
    yield emu
    emu.stop()
```

**Full e2e invocation pattern** (`tests/drone/test_sitl_e2e.py` lines 142-177):
```python
async def test_full_e2e_run_sitl_e2e(shared_emulator) -> None:
    gcs_port, vehicle_port = _ports(5)
    from skyherd.drone.e2e import run_sitl_e2e
    emu = MavlinkSitlEmulator(gcs_host="127.0.0.1", gcs_port=gcs_port, vehicle_port=vehicle_port)
    emu.start()
    time.sleep(0.5)
    try:
        result = await run_sitl_e2e(port=gcs_port, takeoff_alt_m=15.0, emulator=True)
    finally:
        emu.stop()
    assert result["success"] is True, f"E2E failed: {result}"
    assert "E2E PASS" in result["events"]
```

**Failure-path specific addition** — for `test_sitl_smoke_failure.py`, stop the emulator mid-mission and assert the CLI exits non-zero or raises. Use `emu.stop()` before the mission completes and verify `result["success"] is False` or that `run_sitl_e2e` raises.

**Noise comment to fix in `tests/drone/test_sitl_smoke.py` line 21** (dead code):
```python
pytest.mark.slow(pytestmark)  # no-op syntax error — remove or convert to @pytest.mark.slow
```

---

### `.github/workflows/ci.yml` (config — EXTEND existing file)

**Analog:** same file — `.github/workflows/ci.yml`

**Existing job structure pattern to copy** (lines 13-52 — `ci` job):
```yaml
jobs:
  ci:
    name: Python ${{ matrix.python-version }} on ${{ matrix.os }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: uv sync --all-extras
      - name: <step name>
        run: <command>
```

**Existing isolated job pattern** (lines 112-134 — `sitl-e2e` job, currently `workflow_dispatch`-only):
```yaml
sitl-e2e:
  name: SITL E2E (emulator, no Docker)
  runs-on: ubuntu-latest
  if: github.event_name == 'workflow_dispatch'    # ← THIS LINE IS REMOVED in Phase 6

  steps:
    - uses: actions/checkout@v4
    - uses: astral-sh/setup-uv@v5
      with:
        python-version: "3.12"
    - name: Install dependencies
      run: uv sync --all-extras
    - name: Run SITL E2E CLI (emulator mode)
      run: uv run skyherd-sitl-e2e --emulator
    - name: Run SITL E2E test suite
      run: SITL_EMULATOR=1 uv run pytest tests/drone/test_sitl_e2e.py ... -v --timeout=300
```

**Phase 6 change** — remove the `if: github.event_name == 'workflow_dispatch'` guard from `sitl-e2e`; add `timeout-minutes: 5`. Rename to `sitl-smoke` to match Makefile target. Keep the `docker-sitl-smoke` job as `workflow_dispatch`-only (isolated, `continue-on-error: true`). Add a `determinism` job for the 3-run test (tagged `slow`, `timeout-minutes: 15`).

**Docker job `continue-on-error` pattern** (lines 139-167 — `docker-sitl-smoke`):
```yaml
docker-sitl-smoke:
  name: Docker SITL smoke (manual)
  runs-on: ubuntu-latest
  if: github.event_name == 'workflow_dispatch'
  # NOTE: if converted to push/PR, add: continue-on-error: true
```

---

### `Makefile` (config — EXTEND existing file)

**Analog:** same file — `Makefile`

**Existing `.PHONY` pattern** (line 1):
```makefile
.PHONY: setup sim demo dashboard test lint format typecheck clean ci sitl-up sitl-down bus-up bus-down mesh-smoke one-pager hardware-demo mavic-bridge f3-bridge drone-smoke
```
Add `sitl-smoke gate-check determinism-3x` to this line.

**Existing simple target pattern** (lines 59-63):
```makefile
mesh-smoke:
	uv run skyherd-mesh mesh smoke --verbose

one-pager:
	uv run python scripts/render_pdf.py docs/ONE_PAGER.md docs/ONE_PAGER.pdf
```

**Phase 6 new targets** — match this single-command style:
```makefile
sitl-smoke:
	uv run python scripts/sitl_smoke.py

gate-check:
	uv run python scripts/gate_check.py

determinism-3x:
	uv run pytest tests/test_determinism_e2e.py -v -m slow
```

**Env-var doc pattern** — existing targets like `sitl-up` (line 46) show inline `docker compose` invocation. Document `SITL_EMULATOR` and `SITL_IMAGE` env vars in a comment above `sitl-smoke`.

---

## Shared Patterns

### Script structure (shebang + docstring + `main()` + `__name__` guard)
**Source:** `scripts/build-replay.py` lines 1-12, 165, 220-222
**Apply to:** `scripts/sitl_smoke.py`, `scripts/gate_check.py`
```python
#!/usr/bin/env python3
"""<Short description>.

Usage:
  python3 scripts/<name>.py

<Extended description>
"""
from __future__ import annotations
...
def main() -> None: ...
if __name__ == "__main__":
    main()
```

### subprocess run + check return code
**Source:** `scripts/build-replay.py` lines 33-44; `tests/test_determinism_e2e.py` lines 43-52
**Apply to:** `scripts/sitl_smoke.py`, `scripts/gate_check.py`
```python
result = subprocess.run(
    ["uv", "run", ...],
    cwd=REPO_ROOT,
    capture_output=True,
    text=True,
    timeout=120,
)
output = result.stdout + result.stderr
# inspect output before deciding exit
```

### SITL skip guard
**Source:** `tests/drone/test_sitl_e2e.py` lines 30-38
**Apply to:** `tests/drone/test_sitl_smoke_failure.py`
```python
_ENABLED = os.environ.get("SITL_EMULATOR", "0") == "1" or os.environ.get("SITL", "0") == "1"
pytestmark = pytest.mark.skipif(not _ENABLED, reason="Set SITL_EMULATOR=1 to run.")
```

### Port isolation
**Source:** `tests/drone/test_sitl_e2e.py` lines 44-49
**Apply to:** `tests/drone/test_sitl_smoke_failure.py`
```python
_BASE_PORT = 14560
def _ports(offset: int) -> tuple[int, int]:
    return _BASE_PORT + offset * 2, _BASE_PORT + offset * 2 + 1
```

### `@pytest.mark.slow`
**Source:** `tests/test_determinism_e2e.py` line 60; `pyproject.toml` lines 101-103
**Apply to:** `tests/test_determinism_e2e.py` (extended), any multi-minute gate test
```python
@pytest.mark.slow
def test_...: ...
```
Run with: `uv run pytest -m slow`; deselect with: `uv run pytest -m "not slow"`

### CI job skeleton (uv-based)
**Source:** `.github/workflows/ci.yml` lines 93-108 (`pip-audit` job — cleanest minimal example)
**Apply to:** new `determinism` CI job
```yaml
job-name:
  name: <Human label>
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: astral-sh/setup-uv@v5
      with:
        python-version: "3.12"
    - name: Install dependencies
      run: uv sync --all-extras
    - name: <Step>
      run: <command>
```

---

## No Analog Found

All Phase 6 files have close analogs in the repo. No files require falling back to RESEARCH.md patterns alone.

| File | Reason analog is partial |
|---|---|
| `scripts/gate_check.py` | `build-replay.py` is the closest analog but gate_check has structured pass/fail table output and calls multiple sub-processes; planner must merge the batch-loop pattern with the `_check_*` dispatcher design from RESEARCH.md Pattern 4 |
| `tests/drone/test_sitl_smoke_failure.py` | analog is the happy-path `test_sitl_e2e.py`; failure-path test pattern (stop emulator mid-mission, assert exception or non-zero result) has no existing example in the repo |

---

## Metadata

**Analog search scope:** `scripts/`, `tests/`, `.github/workflows/`, `Makefile`, `src/skyherd/drone/`
**Files read:** `scripts/build-replay.py`, `scripts/render_pdf.py`, `tests/test_determinism_e2e.py`, `tests/drone/test_sitl_e2e.py`, `tests/drone/test_sitl_smoke.py`, `.github/workflows/ci.yml`, `Makefile`, `src/skyherd/drone/e2e.py` (partial), `pyproject.toml` (partial)
**Pattern extraction date:** 2026-04-22
