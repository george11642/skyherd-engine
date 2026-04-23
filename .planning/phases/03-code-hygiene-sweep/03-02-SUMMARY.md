---
phase: 03-code-hygiene-sweep
plan: "02"
subsystem: sensors/server/voice-tts/edge/scenarios
tags: [silent-except, logging, observability, hygiene, tdd]
dependency_graph:
  requires: []
  provides: [HYG-01-partial]
  affects: [sensors/bus, sensors/trough_cam, server/events, voice/tts, edge/watcher, scenarios/base, scenarios/cross_ranch_coyote]
tech_stack:
  added: []
  patterns: [caplog-warning-test, BLE001-noqa-logger, percent-style-logger]
key_files:
  created: []
  modified:
    - src/skyherd/sensors/bus.py
    - src/skyherd/sensors/trough_cam.py
    - src/skyherd/server/events.py
    - src/skyherd/voice/tts.py
    - src/skyherd/edge/watcher.py
    - src/skyherd/scenarios/base.py
    - src/skyherd/scenarios/cross_ranch_coyote.py
    - tests/sensors/test_bus.py
    - tests/edge/test_watcher.py
    - tests/voice/test_tts.py
    - tests/sensors/test_trough_cam.py
decisions:
  - "WARNING for real failures operators need to see (mqtt/aiomqtt close errors); DEBUG for defensive fallbacks where safe default is already in use"
  - "No `as exc` on events.py ValueError (list.remove race) — exception payload carries no useful info beyond confirming the race"
  - "WONTFIX CancelledError catches left as-is — logging on clean shutdown creates false-positive noise"
  - "camera.py bare Exception catch noted as out-of-scope pre-existing issue — deferred to separate hygiene pass"
metrics:
  duration_minutes: ~55
  completed_date: "2026-04-23"
  tasks_completed: 2
  files_modified: 11
---

# Phase 03 Plan 02: Silent-Except Sweep (non-drone) Summary

**One-liner:** Converted 9 silent-except sites across sensors/server/voice/edge/scenarios to `logger.warning/debug` using the BLE001+logger master pattern from `rancher_mcp.py`, with 5 caplog RED/GREEN TDD tests.

## What Was Done

### HYG-01 Fix Sites (9 total)

| # | File | Line | Category | Level | Message Substring |
|---|------|------|----------|-------|-------------------|
| 1 | `sensors/bus.py` | `_close_client` | 2 - broad close | WARNING | `aiomqtt client close failed` |
| 2 | `sensors/bus.py` | `_parse_url` | 4 - parse fallback | DEBUG | `mqtt URL port unparseable` |
| 3 | `sensors/trough_cam.py` | `tick` | 3 - optional dep | DEBUG | `vision renderer unavailable` |
| 4 | `server/events.py` | `subscribe` | 6 - race | DEBUG | `sse subscriber already removed` |
| 5 | `server/events.py` | `_broadcast` | 6 - race | DEBUG | `sse queue rotation race` |
| 6 | `voice/tts.py` | `_mp3_to_wav` | 2 - broad fallback | DEBUG | `pydub mp3 decode failed` |
| 7 | `edge/watcher.py` | `_parse_mqtt_url` | 4 - parse fallback | DEBUG | `mqtt URL port unparseable in` |
| 8 | `edge/watcher.py` | `_close_mqtt_client` | 2 - broad close | WARNING | `mqtt client close failed during EdgeWatcher shutdown` |
| 9 | `edge/watcher.py` | `_install_signal_handlers` | 5 - platform variant | DEBUG | `signal handler unavailable on this platform` |
| 10 | `scenarios/base.py` | `_run_async` | 5 - OS cleanup race | DEBUG | `tmp ledger file already gone` |
| 11 | `scenarios/cross_ranch_coyote.py` | `_run_async_inner` | 5 - OS cleanup race | DEBUG | `tmp ledger file already gone` |

Note: The plan listed 9 sites but actually 11 were converted (the plan counted `base.py` and `cross_ranch_coyote.py` as one category, and the `watcher.py` signal-handler site was listed separately). All 11 silent-pass catches in the 7 target files are converted.

### WONTFIX Sites (9 intentional — left as-is)

These are typed `asyncio.CancelledError` / `KeyboardInterrupt` catches on clean shutdown paths. Logging on every normal shutdown would generate false-positive noise with no diagnostic value.

| File | Line(s) | Pattern | Reason |
|------|---------|---------|--------|
| `sensors/acoustic.py` | 66, 71, 81 | `except asyncio.CancelledError: pass` | Clean task shutdown |
| `sensors/base.py` | 79 | `except asyncio.CancelledError: pass` | Clean task shutdown |
| `agents/mesh.py` | 162, 169 | `except asyncio.CancelledError: pass` | Tick/mqtt task cancel |
| `agents/mesh_neighbor.py` | 444 | `except asyncio.CancelledError: pass` | Clean session cancel |
| `edge/watcher.py` | 230, 237, 322 | `except asyncio.CancelledError: pass` | Run-loop/healthz cancel |

### Special Case — `fenceline_dispatcher.py:153`

Line 153 is an `if ... pass` (empty then-branch), not an `except ... pass`. This is out of HYG-01 scope (CONCERNS.md §3 framing covers bare silent-catches only). Noted, not blocked.

### Out-of-Scope Discovery — `edge/camera.py:90`

```python
except Exception:  # noqa: BLE001
    pass
```
In `PiCamera.close()`. This is a pre-existing issue not in the plan's file list. Deferred to a future hygiene pass.

## TDD Evidence

**RED commit:** `2d16deb` — 5 failing caplog tests added before any source changes.
**GREEN commit:** `09fda05` — 9 (11) source conversions; all 5 tests now pass; 328 total tests pass, 0 regressions.

### Caplog Tests Added

| Test | File | Assertion |
|------|------|-----------|
| `test_close_client_warns_on_exit_error` | `tests/sensors/test_bus.py` | `"aiomqtt client close failed"` in WARNING caplog |
| `test_parse_payload_debug_log_on_malformed_json` | `tests/sensors/test_bus.py` | `"mqtt URL port unparseable"` in DEBUG caplog |
| `test_mqtt_close_warns_on_exit_error` | `tests/edge/test_watcher.py` | `"mqtt client close failed during EdgeWatcher shutdown"` in WARNING caplog |
| `test_mp3_decode_debug_log_on_pydub_failure` | `tests/voice/test_tts.py` | `"pydub mp3 decode failed"` in DEBUG caplog |
| `test_frame_render_debug_log_on_import_error` | `tests/sensors/test_trough_cam.py` | `"vision renderer unavailable"` in DEBUG caplog |

## Verification Results

```
grep -rEn "except.*:\s*pass" [7 target files]  → CLEAN (zero matches)
ruff check [7 target files]                     → All checks passed!
pytest tests/sensors/ tests/edge/ tests/voice/test_tts.py tests/server/ tests/scenarios/
  → 328 passed, 2 skipped in 61.00s
```

## Deviations from Plan

None material — plan executed as written.

**Clarification (not a deviation):** Plan listed 9 FIX sites in the task actions, but the actual file had 11 silent-pass catches in the 7 target files (plan listed `base.py` + `cross_ranch_coyote.py` as one entry, and `watcher.py` had 3 sites not 2). All 11 were converted. The caplog test count (5) and WARNING/DEBUG level decisions match the plan exactly.

**Out-of-scope discovery logged:** `edge/camera.py:90` bare BLE001+pass — pre-existing, deferred.

## HYG-01 Closure Status

- Plan 02 closes: 11 FIX sites (sensors/server/voice/edge/scenarios subsystems)
- Plan 01 closes: voice/call.py:200 (handled separately)
- Plan 04 closes: drone subsystem sites (f3_inav, sitl_emulator)
- Remaining WONTFIX: 9 typed CancelledError catches (documented above — intentional)

## Self-Check: PASSED
