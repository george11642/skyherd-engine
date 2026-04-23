---
phase: 03-code-hygiene-sweep
plan: "04"
subsystem: drone
tags: [drone, pyright, ruff, static-analysis, silent-except, telemetry, tdd]
dependency_graph:
  requires: []
  provides: [HYG-01-drone, HYG-04, HYG-05]
  affects: [src/skyherd/drone/f3_inav.py, src/skyherd/drone/sitl_emulator.py, src/skyherd/drone/pymavlink_backend.py, src/skyherd/server/app.py]
tech_stack:
  added: []
  patterns: [DEBUG-log-on-exception, type-ignore-with-rationale, assert-runtime-guard]
key_files:
  created: []
  modified:
    - src/skyherd/drone/f3_inav.py
    - src/skyherd/drone/sitl_emulator.py
    - src/skyherd/drone/pymavlink_backend.py
    - src/skyherd/server/app.py
    - tests/drone/test_f3_inav.py
decisions:
  - "WONTFIX: sitl_emulator.py KeyboardInterrupt catch is intentional CLI signal handler — documented with comment, not converted"
  - "assert self._sock is not None preferred over type: ignore for sitl_emulator nullability (runtime invariant is real)"
  - "6 pyright errors in agents/managed.py + agents/session.py explicitly deferred to Phase 1 — no throwaway type-ignores added"
  - "Pre-existing ruff errors in tests/vision/ (8 errors) are out-of-scope; logged to deferred-items"
metrics:
  duration: "~20 min"
  completed: "2026-04-22"
  tasks_completed: 2
  files_modified: 5
  commits: 2
---

# Phase 3 Plan 04: Drone Silent-Except Sweep + Pyright Clean Summary

**One-liner:** Converted 7 drone silent-except sites to `logger.debug`, resolved 9 pyright errors on Phase-3-owned files via typed-ignores with rationale + an assert guard, and auto-fixed 1 ruff import sort — leaving the codebase fully clean on the Phase 3 surface.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Convert 7 drone silent-except sites + RED/GREEN caplog test | c7b4009 | f3_inav.py, sitl_emulator.py, test_f3_inav.py |
| 2 | Fix 9 pyright errors + ruff auto-fix server/app.py | e740f6f | pymavlink_backend.py, server/app.py, test_f3_inav.py |

## Silent-Except Conversions (HYG-01 — Drone Subsystem)

### f3_inav.py — 5 FIX sites

| Line (approx) | Field | Category | Action |
|---------------|-------|----------|--------|
| 369 | `armed` | Category 5 — transient stream | `logger.debug("mavsdk telemetry read for armed failed: %s", exc)` |
| 377 | `in_air` | Category 5 — transient stream | `logger.debug("mavsdk telemetry read for in_air failed: %s", exc)` |
| 386 | `position` | Category 5 — transient stream | `logger.debug("mavsdk telemetry read for position failed: %s", exc)` |
| 393 | `battery` | Category 5 — transient stream | `logger.debug("mavsdk telemetry read for battery failed: %s", exc)` |
| 400 | `flight_mode` | Category 5 — transient stream | `logger.debug("mavsdk telemetry read for flight_mode failed: %s", exc)` |

All 5 sites use `except Exception as exc:  # noqa: BLE001` with a consistent message format: `"mavsdk telemetry read for <field> failed: %s"`.

### sitl_emulator.py — 2 FIX + 1 WONTFIX

| Line (approx) | Site | Action |
|---------------|------|--------|
| 444 | Socket close race on stop() | `logger.debug("sitl emulator socket close race (non-fatal): %s", exc)` |
| 466 | UDP sendto failure in _send() | `logger.debug("sitl emulator sendto failed (GCS not listening): %s", exc)` |
| 742 | `except KeyboardInterrupt: pass` | **WONTFIX** — CLI main-loop signal handler (Ctrl-C graceful shutdown). Added rationale comment above. |

## Pyright Errors Resolved (HYG-04)

### pymavlink_backend.py — 8 errors → 0

All 8 errors stem from pymavlink's missing stubs for `mavfile` subclasses returned by `mavutil.mavlink_connection()`. The runtime objects (`mavtcp`, `mavudp`, etc.) have `target_system`, `wait_heartbeat`, `recv_match(timeout=...)` at runtime but the stub union type doesn't include them.

One rationale comment block added per method group; specific suppression codes per error:

| Error | Suppression | Rationale |
|-------|-------------|-----------|
| `recv_match(timeout=...)` call-arg mismatch | `# type: ignore[call-arg]` | pymavlink stubs lack `timeout` kwarg on `recv_match` |
| `conn.target_system` attr-access | `# type: ignore[attr-defined]` | runtime UDP objects have this; stubs don't |
| `conn.wait_heartbeat(timeout=...)` attr-access | `# type: ignore[attr-defined]` | runtime method; not in stubs |
| `return conn` return-value mismatch | `# type: ignore[return-value]` | union includes non-`mavfile` log-file readers; UDP conn is always `mavfile`-compatible |

### sitl_emulator.py — 1 error → 0

| Line | Error | Fix |
|------|-------|-----|
| 582 | `reportOptionalMemberAccess` on `self._sock.recvfrom(4096)` | Added `assert self._sock is not None  # bound in start(); never None when _running is True` — runtime invariant is real, assert preferred over type-ignore |

### Phase-3-Owned Pyright Gate Result

```
uv run pyright src/skyherd/drone/ src/skyherd/sensors/ src/skyherd/voice/ src/skyherd/edge/ src/skyherd/server/ src/skyherd/scenarios/ src/skyherd/agents/cost.py
→ 0 errors, 5 warnings (missing stubs for mavsdk/pymavlink — informational only)
```

## Ruff Fix (HYG-04)

| File | Error | Fix |
|------|-------|-----|
| `src/skyherd/server/app.py:114` | `I001` unsorted import block | `ruff check --fix src/` auto-fixed |

`src/` ruff gate: **0 errors**.

## Phase-1 Handoff — Explicitly Deferred Pyright Errors

6 pyright errors remain open in agent files. These are **NOT Phase 3 scope** — Phase 1 restructures both files:

| File | Lines | Error Count | Error Type |
|------|-------|-------------|------------|
| `src/skyherd/agents/managed.py` | 388 | 2 | `__aenter__`/`__aexit__` on coroutine |
| `src/skyherd/agents/session.py` | 415–422 | 4 | return-type mismatch + None→str |

**Phase 1 acceptance criterion (mandatory):**
> `uv run pyright src/skyherd/agents/managed.py src/skyherd/agents/session.py` must exit 0 as part of Phase 1 verification. No throwaway type-ignores were added in Phase 3 — churn not justified per 03-RESEARCH.md:669.

## TDD: Caplog Test

Added `test_telemetry_debug_log_on_transient_failure` to `tests/drone/test_f3_inav.py`:
- RED: confirmed `caplog.text` did not contain the message before source changes
- GREEN: confirmed `caplog.text` contains `"mavsdk telemetry read for armed"` after conversion
- Monkeypatches `telemetry.armed()` to raise `RuntimeError("stream not ready")` on first iteration

## Verification Results

| Gate | Result |
|------|--------|
| `grep -rEn "except Exception:\s*pass\s*$" src/skyherd/drone/` | ZERO matches |
| `grep -rEn "except OSError:\s*pass\s*$" src/skyherd/drone/` | ZERO matches |
| `grep -rEn "except KeyboardInterrupt:" src/skyherd/drone/sitl_emulator.py` | 1 match (WONTFIX, intentional) |
| `uv run pyright src/skyherd/drone/ ...` (Phase-3-owned scope) | 0 errors, 5 warnings |
| `uv run ruff check src/` | 0 errors |
| `pytest tests/drone/ -x --no-cov` | 87 passed, 11 skipped |
| `pytest --cov=src/skyherd --cov-fail-under=80` | 1168 passed, 87.38% coverage |

## Overall Phase 3 Gate Status

| Requirement | Status | Closed By |
|-------------|--------|-----------|
| HYG-01 — Zero silent-except in all Phase-3-owned files | CLOSED | Plans 01, 02, 03, 04 |
| HYG-02 — Twilio env var standardised | CLOSED | Plan 01 |
| HYG-03 — agents/cost.py coverage ≥90% | CLOSED | Plan 03 |
| HYG-04 — pyright clean on Phase-3-owned files | CLOSED | Plan 04 (6 agents/ errors deferred to Phase 1 with explicit handoff) |
| HYG-05 — project coverage ≥80% gate held | CLOSED | Plan 04 (87.38% confirmed) |

## Deviations from Plan

### Pre-existing ruff errors in tests/vision/ (out of scope — documented)

**Found during:** Task 2 verification
**Issue:** `tests/vision/test_heads/test_pinkeye_pixel.py` and `tests/vision/test_preprocess_detector.py` had 8 ruff errors (unused imports, E402, F811, I001). These existed on the base commit before this plan.
**Action:** Confirmed pre-existing via `git stash` check. Not fixed — out of scope per Phase 3 scope boundary. Logged here for Phase 5 (vision) cleanup.
**Scope:** Phase 5 / separate cleanup plan

### Invalid `# noqa` directive in test (Rule 1 — auto-fixed)

**Found during:** Task 2 ruff check
**Issue:** Added `# noqa: unreachable` in test helper — not a valid ruff code, triggered a ruff warning.
**Fix:** Replaced with `# noqa: RET505` (valid suppression for unreachable after raise in async generator).
**Commit:** e740f6f

## Known Stubs

None — all data flows wired; no placeholder text or empty stubs in modified files.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| src/skyherd/drone/f3_inav.py | FOUND |
| src/skyherd/drone/sitl_emulator.py | FOUND |
| src/skyherd/drone/pymavlink_backend.py | FOUND |
| src/skyherd/server/app.py | FOUND |
| tests/drone/test_f3_inav.py | FOUND |
| commit c7b4009 | FOUND |
| commit e740f6f | FOUND |
