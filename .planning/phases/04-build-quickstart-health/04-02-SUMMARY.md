---
phase: 04-build-quickstart-health
plan: "02"
subsystem: server-live-mode
tags: [fastapi, dashboard, live-mode, typer, dependency-injection, bld-03]
requirements: [BLD-03]

dependency_graph:
  requires:
    - "make_world(seed=42) no-arg invocation (04-01)"
  provides:
    - "skyherd.server.live typer CLI"
    - "make dashboard -> live mode (real 50-cow world)"
    - "make dashboard-mock -> legacy SKYHERD_MOCK=1 path"
    - "skyherd-server-live entry-point"
    - "/api/snapshot returns real world data when mock=False"
  affects:
    - "src/skyherd/server/live.py"
    - "src/skyherd/server/app.py"
    - "Makefile"
    - "pyproject.toml"
    - "tests/server/test_live_app.py"

tech_stack:
  added:
    - "typer CLI for live-mode uvicorn bootstrap (mirrors cli.py pattern)"
    - "create_app(mock=False, mesh=_DemoMesh, world=make_world, ledger=Ledger) full DI path"
  patterns:
    - "TDD: write test first, confirm live path behavior, then add live.py caller"
    - "Local import in live.py for _DemoMesh (avoids circular dep)"
    - "model_dump(mode='json') for Pydantic set->list serialization"
    - "Coverage omit for uvicorn-calling CLI entry-points (same as agents/cli.py)"

key_files:
  created:
    - path: "src/skyherd/server/live.py"
      purpose: "Typer CLI that constructs real World+Ledger+_DemoMesh and starts uvicorn (64 lines)"
    - path: "tests/server/test_live_app.py"
      purpose: "BLD-03 integration test: /api/snapshot returns 50 cows in live mode"
  modified:
    - path: "Makefile"
      change: "dashboard flipped to live mode; dashboard-mock added for SKYHERD_MOCK=1 backward compat"
    - path: "pyproject.toml"
      change: "Added skyherd-server-live entry-point; added live.py to coverage omit"
    - path: "src/skyherd/server/app.py"
      change: "api_snapshot: model_dump() -> model_dump(mode='json') to fix set serialization bug"

decisions:
  - "Default host 127.0.0.1 (not 0.0.0.0) in live.py — mitigates T-04-04 info disclosure"
  - "Local import of _DemoMesh inside start() function — avoids circular import (scenarios->server)"
  - "live.py added to coverage omit — uvicorn.run() cannot be tested via TestClient; behavior tested via create_app(mock=False) path"
  - "Pre-existing 79% coverage baseline (was 78.59% at 06673d3) not fixed — out of scope for this plan"

metrics:
  duration_minutes: 20
  completed_date: "2026-04-22"
  tasks_completed: 3
  tasks_total: 3
  files_created: 2
  files_modified: 3
---

# Phase 04 Plan 02: Live-Mode Dashboard CLI Summary

**One-liner:** `make dashboard` now starts a live FastAPI server via `skyherd.server.live` that serves 50 real cows from ranch_a.yaml via full DI into `create_app(mock=False)`, replacing the always-mock `SKYHERD_MOCK=1` default.

## What Was Built

Closed BLD-03: judges typing `make dashboard` now see real sim data (50 cows, real ledger, real mesh sessions) rather than the 12-cow mock stub.

- `src/skyherd/server/live.py` (64 lines): typer CLI that constructs `make_world(seed=42)`, fresh `Ledger` in `/tmp`, `_DemoMesh(ledger=ledger)`, and passes all three to `create_app(mock=False, mesh=..., world=..., ledger=...)`, then calls `uvicorn.run()`. Binds to `127.0.0.1` by default (T-04-04 threat mitigation).
- `make dashboard` → `uv run python -m skyherd.server.live --port 8000 --host 127.0.0.1 --seed 42`
- `make dashboard-mock` → `SKYHERD_MOCK=1 uv run uvicorn skyherd.server.app:app --port 8000` (backward-compat)
- `skyherd-server-live` registered in `[project.scripts]` — `uv run skyherd-server-live --help` works
- 2 integration tests in `tests/server/test_live_app.py`: both pass (2/2 green)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 4ef89da | test | add BLD-03 integration test for live dashboard snapshot |
| 8647a8e | feat | add skyherd.server.live typer CLI for live-mode dashboard (BLD-03) |
| c6cbaf7 | build | flip make dashboard to live; add dashboard-mock for legacy path (BLD-03) |
| dac4112 | build | omit live.py from coverage (CLI entry-point, same pattern as agents/cli.py) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `api_snapshot` crashed on live path due to non-JSON-serializable `set`**
- **Found during:** Task 1 (first test run)
- **Issue:** `world.snapshot().model_dump()` returns `disease_flags` as `set[str]`, which `json.dumps()` cannot serialize. The live `/api/snapshot` path raised `TypeError: Object of type set is not JSON serializable`. This was the 73%-covered-but-never-invoked-from-Makefile latent bug the plan mentioned.
- **Fix:** Changed `world.snapshot().model_dump()` to `world.snapshot().model_dump(mode="json")` in `src/skyherd/server/app.py:141`. Pydantic v2's `mode="json"` converts sets to lists and tuples to lists automatically.
- **Files modified:** `src/skyherd/server/app.py`
- **Commit:** 4ef89da (bundled with test commit)

**2. [Rule 2 - Missing critical functionality] live.py not excluded from coverage**
- **Found during:** Post-Task 3 full coverage run
- **Issue:** `live.py` calls `uvicorn.run()` which blocks forever — cannot be exercised by pytest/TestClient. Adding it without exclusion dropped server module coverage. Same pattern as `src/skyherd/agents/cli.py` which is already omitted.
- **Fix:** Added `"src/skyherd/server/live.py"` to `[tool.coverage.run] omit` in `pyproject.toml`.
- **Files modified:** `pyproject.toml`
- **Commit:** dac4112

### Pre-existing Issue (Out of Scope)

**Coverage gate was already failing before this plan:** Baseline at commit 06673d3 measured 78.59% total against `fail_under=80`. After this plan (with live.py omitted), coverage is 79.01% — actually improved by +0.42pp vs baseline, still below threshold. The gap is in voice/vision/sensors modules not covered in the standard pytest run (they require torch, hardware devices, or MQTT broker). Tracked in deferred-items.md as pre-existing.

## Known Stubs

None. All data paths serve real content:
- `/api/snapshot` in live mode returns actual `world.snapshot().model_dump(mode="json")` — 50 cows from ranch_a.yaml
- `/api/agents` in live mode returns `_DemoMesh._sessions` (real session objects, idle at boot)
- `/api/attest` in live mode reads from real SQLite ledger (empty at boot, entries accumulate as scenarios run)

The CLI echoes "Agent lanes will populate once 'make demo' runs in another terminal" — this is intentional documentation of the Pitfall 3 behavior (agents are idle at dashboard boot), not a stub.

## Threat Flags

None. T-04-04 mitigated: `--host 127.0.0.1` hardcoded in both `live.py` default and Makefile invocation. The CORS policy in `app.py` remains locked (unchanged).

## Self-Check

### Files exist:
- [x] `src/skyherd/server/live.py` — FOUND (64 lines)
- [x] `tests/server/test_live_app.py` — FOUND
- [x] `Makefile` contains `dashboard-mock` — FOUND
- [x] `pyproject.toml` contains `skyherd-server-live` — FOUND

### Commits exist:
- [x] 4ef89da — FOUND
- [x] 8647a8e — FOUND
- [x] c6cbaf7 — FOUND
- [x] dac4112 — FOUND

### Test results:
- [x] `test_live_snapshot_returns_real_world_data` — PASS (50 cows)
- [x] `test_live_health_ok` — PASS
- [x] Full suite (excl. vision/voice/sensors): 885 passed, 13 skipped, 0 failures
- [x] `make -n dashboard` shows `python -m skyherd.server.live --port 8000`
- [x] `make -n dashboard-mock` shows `SKYHERD_MOCK=1 uv run uvicorn`
- [x] `uv run skyherd-server-live --help` succeeds
- [x] Live smoke test: server starts, `/api/snapshot` returns cows=50

## Self-Check: PASSED
