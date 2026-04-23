---
phase: 03-code-hygiene-sweep
plan: 01
subsystem: voice
tags: [twilio, deprecation, env-vars, voice, mcp, tdd]
dependency_graph:
  requires: []
  provides: [HYG-02]
  affects: [voice/call.py, mcp/rancher_mcp.py, demo/hardware_only.py]
tech_stack:
  added: [src/skyherd/voice/_twilio_env.py]
  patterns: [once-per-process DeprecationWarning cache, stacklevel=2 attribution]
key_files:
  created:
    - src/skyherd/voice/_twilio_env.py
    - tests/voice/_twilio_env/__init__.py
    - tests/voice/_twilio_env/test_twilio_env.py
    - tests/voice/conftest.py
  modified:
    - src/skyherd/voice/call.py
    - src/skyherd/demo/hardware_only.py
    - src/skyherd/mcp/rancher_mcp.py
    - .env.example
    - docs/VOICE_ACCESS.md
    - tests/voice/test_call.py
decisions:
  - "Lazy import in conftest.py autouse fixture so RED-phase collection succeeds before helper exists"
  - "stacklevel=2 in warnings.warn so DeprecationWarning points at caller, not _twilio_env.py"
  - "ruff auto-fix applied to rancher_mcp.py import sort (I001) after adding helper import"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-22"
  tasks_completed: 2
  files_created: 4
  files_modified: 6
---

# Phase 03 Plan 01: Twilio env-var migration (HYG-02) Summary

**One-liner:** Centralized `_get_twilio_auth_token()` helper standardizes `TWILIO_AUTH_TOKEN` as canonical across all 3 consumers with once-per-process `DeprecationWarning` for legacy `TWILIO_TOKEN`.

## What Was Built

### New helper module: `src/skyherd/voice/_twilio_env.py`

Single source of truth for Twilio auth-token lookup (51 lines):
- Prefers `TWILIO_AUTH_TOKEN`; falls back to `TWILIO_TOKEN` with `DeprecationWarning`
- `_DEPRECATION_EMITTED: set[str]` module-level cache ensures warning fires once per process
- `stacklevel=2` attributes warning to caller, not helper internals
- No logger — warning message is a static constant string (security: token value never logged)

### Source migrations (3 consumers)

| File | Site | Before | After |
|------|------|--------|-------|
| `voice/call.py` | `_twilio_available()` | `os.environ.get("TWILIO_TOKEN")` | `_get_twilio_auth_token()` |
| `voice/call.py` | `_try_twilio_call()` | `os.environ.get("TWILIO_TOKEN", "")` | `_get_twilio_auth_token()` |
| `voice/call.py` | line-200 silent-except | `except OSError: pass` | `except OSError as exc: logger.debug(...)` |
| `demo/hardware_only.py` | line 486 | `os.environ.get("TWILIO_TOKEN", "")` | `_get_twilio_auth_token()` |
| `mcp/rancher_mcp.py` | `_try_send_sms()` | `os.environ.get("TWILIO_AUTH_TOKEN", "")` | `_get_twilio_auth_token()` |

### Documentation updates

- `.env.example`: `TWILIO_TOKEN` → `TWILIO_AUTH_TOKEN` + legacy deprecation comment
- `docs/VOICE_ACCESS.md`: setup instructions updated to `TWILIO_AUTH_TOKEN`

### Tests

**New (7 total):**
- `tests/voice/_twilio_env/test_twilio_env.py` — 4 helper unit tests (new var wins, legacy emits warning, once-per-process cache, neither→empty)
- `tests/voice/test_call.py::TestTwilioAuthTokenMigration` — 3 migration tests (prefers auth token, accepts legacy with warning, SSE OSError logs DEBUG)

**Flipped (6 existing refs):** All `TWILIO_TOKEN` setenv/delenv in `TestTryTwilioCall` and `TestRenderUrgencyCall` updated to `TWILIO_AUTH_TOKEN`.

**New fixture:** `tests/voice/conftest.py` autouse fixture clears `_DEPRECATION_EMITTED` between tests to prevent order-dependent flakes.

**Final test run:** 125 passed, 0 failed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test had setenv/delenv ordering error**
- **Found during:** Task 2 GREEN phase (first test run)
- **Issue:** `test_twilio_available_prefers_auth_token` set `TWILIO_AUTH_TOKEN` on line 245 then immediately `delenv`'d it on line 247 (copy-paste error from legacy test pattern), causing `_twilio_available()` to return False
- **Fix:** Changed `monkeypatch.delenv("TWILIO_AUTH_TOKEN", ...)` to `monkeypatch.delenv("TWILIO_TOKEN", ...)` — the intent was to ensure no legacy var is present
- **Files modified:** `tests/voice/test_call.py`
- **Commit:** 2736d67

**2. [Rule 1 - Lint] Import sort in rancher_mcp.py**
- **Found during:** Task 2 ruff check post-migration
- **Issue:** `ruff I001` — new `from skyherd.voice._twilio_env import _get_twilio_auth_token` needed blank line separation from `claude_agent_sdk` import block
- **Fix:** `ruff check --fix` auto-corrected the import block
- **Files modified:** `src/skyherd/mcp/rancher_mcp.py`
- **Commit:** 2736d67 (already included)

## Security Verification (Threat Model)

| Threat ID | Status | Notes |
|-----------|--------|-------|
| T-03-01 | Mitigated | `_twilio_env.py` has no logger; `warnings.warn` message is a static constant — token value never exposed |
| T-03-02 | Mitigated | line-200 DEBUG log uses `%s` on OSError — no Twilio credentials in SSE write errors |
| T-03-03 | Mitigated | `.env.example` uses `...` placeholder only; deprecation note in comment |
| T-03-04 | Accepted | `_DEPRECATION_EMITTED` cache is legitimate; test fixture restores isolation |

## Known Stubs

None — all wired to real env vars; no placeholder data flows to UI.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 (RED + GREEN) | 88bd931 | Add `_twilio_env` helper + 4 unit tests + conftest autouse fixture |
| Task 2 (migration) | 2736d67 | Migrate all TWILIO_TOKEN sites + 3 migration tests + docs update |

## Self-Check: PASSED

All 11 files verified present. Both task commits (88bd931, 2736d67) confirmed in git log.
