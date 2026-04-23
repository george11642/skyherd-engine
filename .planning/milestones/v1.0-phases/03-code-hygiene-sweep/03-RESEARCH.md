# Phase 3: Code Hygiene Sweep - Research

**Researched:** 2026-04-22
**Domain:** Python code hygiene — logging conventions, env var deprecation, test coverage uplift, static analysis cleanup
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

All implementation choices at Claude's discretion — `workflow.skip_discuss=true`. The following are hard audit-surfaced constraints that MUST be honored:

- 15+ silent `except: pass` sites listed at `.planning/codebase/CONCERNS.md §3` — each MUST convert to `except Exception as exc: logger.warning(...)` with meaningful message.
- Twilio: `TWILIO_TOKEN` in `src/skyherd/voice/call.py:44,68` vs `TWILIO_AUTH_TOKEN` in `src/skyherd/mcp/rancher_mcp.py` — standardize on `TWILIO_AUTH_TOKEN`, emit deprecation warning if legacy `TWILIO_TOKEN` is set, update `.env.example`.
- `src/skyherd/agents/cost.py` at 78% — raise to ≥90% with idle-pause + active-delta + `all_idle` aggregation tests.
- 15 pyright errors — resolve or add typed-ignore list with rationale comments.
- 1 trivial ruff error (unsorted import, auto-fixable).
- Coverage gate ≥80% must hold; actual project ≥87% preserved.

### Claude's Discretion

All of Phase 3 is at Claude's discretion under the above constraints. Specifically:
- Exact log message text and level (WARNING vs DEBUG) per silent-except category.
- `warnings.warn(..., DeprecationWarning)` timing (import-time vs per-call).
- Which cost.py uncovered lines to target first (all must reach ≥90%).
- Whether to fix pyright errors via annotations or `# type: ignore[code]` with rationale.

### Deferred Ideas (OUT OF SCOPE)

- Introducing structured logging (JSON logs) — keep `.warning()` strings.
- Full type coverage beyond the 15 drone errors — out of scope.
- Replacing pytest — no.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HYG-01 | Replace 15+ `except: pass` blocks with `except Exception as exc: logger.warning(...)`. No bare silent-catch remains in `src/skyherd/`. | §"Silent-Except Site Inventory" — categorizes all 24 sites found in audit into 6 behavioral classes, each with a recommended log-level + template. Module-level `logger = logging.getLogger(__name__)` already exists in every target file. |
| HYG-02 | Standardize `TWILIO_AUTH_TOKEN` across `voice/call.py` and `mcp/rancher_mcp.py`; update `.env.example`; deprecation warning on `TWILIO_TOKEN`. | §"Twilio Env Var Migration" — reference impl in `rancher_mcp.py:77`; `warnings.warn()` idiom documented; full ripple list (7 call sites + 5 test files + 1 doc + .env.example). |
| HYG-03 | `agents/cost.py` coverage ≥90% with idle-pause, active-delta, `all_idle` tests. | §"cost.py Coverage Plan" — exact uncovered lines (165-170 MQTT publish, 174-177 ledger callback, 187/191 properties, 205-216 run_tick_loop body) mapped to specific test scenarios. |
| HYG-04 | Ruff + pyright clean. Resolve 15 pyright errors in drone backends, or typed-ignore with rationale. | §"Static Analysis Cleanup" — live pyright run produced 15 errors but scope differs from CONTEXT assumption: 9 in drone files, 2 in `agents/managed.py:388` (Phase 1 surface), 4 in `agents/session.py:415-422` (Phase 1 surface). Plan must coordinate with Phase 1. |
| HYG-05 | Coverage gate ≥80% holds; project ≥87% preserved. | §"Coverage Math" — baseline 87.42%; net change from HYG-03 is +small, net change from HYG-01 depends on whether new warning paths are exercised in tests. |
</phase_requirements>

---

## Summary

Phase 3 is the "make it honest" phase — pure hygiene, zero behavior change. Three orthogonal tracks:

1. **Logging track (HYG-01):** 24 silent-except sites (not 15 — audit undercounts; actual grep finds more) replaced with logged-warning pattern. The codebase already has a fully established convention (`logger = logging.getLogger(__name__)` at module top + `except Exception as exc:  # noqa: BLE001` + `logger.warning("...: %s", exc)`) — this phase propagates it to the remaining holdout sites.
2. **Twilio track (HYG-02):** Unify `TWILIO_TOKEN` → `TWILIO_AUTH_TOKEN` with a DeprecationWarning shim. 7 source references + 5 test references + 1 doc reference + .env.example must all flip.
3. **Quality gates (HYG-03/04/05):** Cost ticker tests for the 21 uncovered lines; pyright cleanup (with a surprise — the error set overlaps Phase 1 surface); ruff auto-fix.

**Primary recommendation:** Sequence the work as (a) Twilio migration first (isolated, testable in one shot), (b) silent-except sweep second (independent per-file edits, parallelizable), (c) cost.py tests third (file-scoped), (d) pyright cleanup last with Phase 1 coordination for the managed.py/session.py surface.

---

## Architectural Responsibility Map

Pure hygiene phase — no new capabilities. The "architecture" is the existing logging/testing/typing discipline being applied to holdout sites.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Observability via logs | Backend library code | — | All log emission lives in `src/skyherd/*/` module-level loggers. No frontend or API-layer work. |
| Twilio credential lookup | Backend (voice + MCP) | — | Env var reads happen in `voice/call.py` + `mcp/rancher_mcp.py` + `demo/hardware_only.py`. |
| Cost billing tests | Test tier (`tests/agents/`) | — | Unit tests live alongside existing `test_cost.py`. No integration tier needed. |
| Static analysis cleanup | Backend library code | CI tier | Fixes live in source; gate runs in `make ci`. |

---

## Standard Stack

### Core (already installed — no additions needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `logging` (stdlib) | 3.11+ | Structured warnings on swallowed exceptions | Already universal in codebase per grep `logger = logging.getLogger(__name__)` — 45 module-level loggers [VERIFIED: grep output]. |
| `warnings` (stdlib) | 3.11+ | `DeprecationWarning` on legacy `TWILIO_TOKEN` | Canonical Python idiom for env var migration [CITED: https://docs.python.org/3.11/library/warnings.html#warnings.warn]. |
| `pytest` | 9.0.3 | Test runner for new cost.py tests | `asyncio_mode = "auto"` already configured — async tests need no decorator [VERIFIED: pyproject.toml line 97]. |
| `pytest-cov` | 7.1.0 | Coverage enforcement | `fail_under = 80` in `pyproject.toml` [VERIFIED: pyproject.toml line 124]. |
| `ruff` | (pinned in dev deps, unpinned version) | Lint + isort | Already in `make ci` — 1 fixable error [VERIFIED: `uv run ruff check` output]. |
| `pyright` | (pinned in dev deps, unpinned version) | Type checking | 15 errors — 9 in drone files, 6 in `agents/managed.py` + `agents/session.py` [VERIFIED: live `uv run pyright src/` output 2026-04-22]. |

### Supporting (none)

No new libraries needed. Phase 3 is purely reshaping existing code to match existing conventions.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `warnings.warn(DeprecationWarning)` | `logger.warning()` only | `DeprecationWarning` surfaces in test runs (pytest captures it) and is the Python-standard signal for future removal; plain `logger.warning` is easy to miss in noise. Use `warnings.warn` [CITED: PEP 565]. |
| Full type annotation fixes for pymavlink | `# type: ignore[reportAttributeAccessIssue, reportCallIssue]` with rationale comment | pymavlink has no stubs upstream — annotating every callsite bloats code. Typed-ignore with one-line rationale is the project's existing discipline (see `sitl.py` F821 ignores in `pyproject.toml`). |
| Writing new logger instances | Reuse existing module-level `logger = logging.getLogger(__name__)` | Every target file already has this — no new instances needed. |

**Version verification:** No new packages installed. Existing tool versions confirmed via `pyproject.toml` dev-deps.

---

## Architecture Patterns

### System Architecture Diagram

Phase 3 doesn't change the runtime data flow. What changes is the *observability* of failure paths:

```
┌─────────────────────────────────────────────────────────────────┐
│                  Silent-Except Site Transform                    │
│                                                                  │
│  BEFORE:                         AFTER:                          │
│  ┌──────────────┐                ┌──────────────┐                │
│  │ risky_call() │                │ risky_call() │                │
│  └──────┬───────┘                └──────┬───────┘                │
│         │ raises                        │ raises                 │
│         ▼                               ▼                        │
│  ┌──────────────┐                ┌──────────────┐                │
│  │ except: pass │─── (void)      │ except Exc   │                │
│  └──────────────┘                │ as exc:      │                │
│                                  │   logger.    │                │
│                                  │   warning()  │──▶ stderr/     │
│                                  └──────────────┘    log file    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────┐
│                    Twilio Env Var Migration Flow                 │
│                                                                  │
│  Caller (voice/call.py, demo/hardware_only.py)                   │
│         │                                                        │
│         ▼                                                        │
│   _get_twilio_token() ◀── NEW helper (single source of truth)   │
│         │                                                        │
│         ├── os.environ.get("TWILIO_AUTH_TOKEN") ──▶ use          │
│         │                                                        │
│         └── fallback: os.environ.get("TWILIO_TOKEN")             │
│                │                                                 │
│                ├── if set → warnings.warn(DeprecationWarning)    │
│                │            then return the value                │
│                │                                                 │
│                └── else → return ""                              │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

No structural changes. Files touched are in-place edits.

```
src/skyherd/
├── sensors/
│   ├── acoustic.py        # silent-except @ 72 — WONTFIX (asyncio.CancelledError)
│   ├── bus.py             # silent-except @ 201 (close error), 269 (parse)
│   └── trough_cam.py      # silent-except @ 94 (ImportError — optional dep)
├── agents/
│   ├── mesh.py            # silent-except @ 163, 170 (task cancel — WONTFIX)
│   ├── fenceline_dispatcher.py   # silent-except @ 153 (unreachable path — special case)
│   └── cost.py            # tests uplift: 78% → ≥90%
├── scenarios/
│   └── base.py            # silent-except @ 312 (tmpfile cleanup) — COORDINATE WITH PHASE 1
├── server/
│   └── events.py          # silent-except @ 299 (already ValueError-specific), 315 (queue race)
├── drone/
│   ├── f3_inav.py         # silent-except @ 370,377,386,393,400 (telemetry fallback — DEBUG)
│   └── sitl_emulator.py   # silent-except @ 445,466 (socket race), 742 (KeyboardInterrupt)
├── voice/
│   ├── call.py            # TWILIO_TOKEN → TWILIO_AUTH_TOKEN migration
│   └── tts.py             # silent-except @ 195 (mp3 decode fallback)
├── edge/
│   └── watcher.py         # silent-except @ 111 (parse), 238 (cancel), 323 (cancel), 454 (close), 480 (Windows signal)
├── mcp/
│   └── rancher_mcp.py     # reference impl — no changes (already uses TWILIO_AUTH_TOKEN)
└── demo/
    └── hardware_only.py   # TWILIO_TOKEN usage site (line 486) — also migrate
```

### Pattern 1: Module-Level Logger (Already Universal)

**What:** Every file with logging uses `logger = logging.getLogger(__name__)` declared near the top of the module.
**When to use:** Any file needing to emit log messages.
**Example:**

```python
# Source: src/skyherd/agents/cost.py:26 (and 44 other modules)
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ... later in the file ...
logger.warning("Twilio SMS failed (to=%s): %s: %s", to, type(exc).__name__, exc)
```

**Verification:** `grep -rn "logger = logging.getLogger" src/skyherd/` returns 45 matches spanning every source subdirectory [VERIFIED: grep output 2026-04-22].

### Pattern 2: Broad-Except with Logger + noqa Rationale (Established Convention)

**What:** When catching `Exception` broadly is intentional, mark with `# noqa: BLE001` and log before continuing.
**When to use:** Non-fatal background tasks where exception propagation would kill a long-running loop but silence would hide bugs.
**Example:**

```python
# Source: src/skyherd/mcp/rancher_mcp.py:92-100 (reference impl)
try:
    from twilio.rest import Client  # type: ignore[import]
    client = Client(sid, token)
    client.messages.create(body=body, from_=from_num, to=to)
    return True
except ImportError:
    _log.debug("twilio package not installed — SMS unavailable")
    return False
except Exception as exc:  # noqa: BLE001
    # Catches TwilioRestException, requests.exceptions.RequestException,
    # ssl.SSLError, etc. — log at WARNING so callers can surface the reason.
    _log.warning(
        "Twilio SMS failed (to=%s): %s: %s",
        to,
        type(exc).__name__,
        exc,
    )
    return False
```

**Key observations:**
- ImportError is caught *separately* at DEBUG (optional dep missing is not a warning-level event).
- Broad `Exception` uses `# noqa: BLE001` (ruff's "blind-except" rule) with a comment enumerating *which* exceptions the catch is actually for.
- Log format is `%s`-style (NOT f-strings) — avoids eager evaluation [CITED: existing convention per CONVENTIONS.md line 143].
- The log message includes both `type(exc).__name__` AND `exc` — shows both the class and the message.

### Pattern 3: DeprecationWarning for Env Var Migration (New to This Phase)

**What:** Emit `DeprecationWarning` exactly once per process when a legacy env var is read, then continue using the legacy value for backward-compat.
**When to use:** `TWILIO_TOKEN` → `TWILIO_AUTH_TOKEN` migration.
**Example:**

```python
# Proposed helper — add to src/skyherd/voice/call.py (or a new twilio_env.py)
import os
import warnings

_DEPRECATION_EMITTED: set[str] = set()


def _get_twilio_auth_token() -> str:
    """Return Twilio auth token from env, preferring TWILIO_AUTH_TOKEN.

    Falls back to legacy TWILIO_TOKEN with a one-shot DeprecationWarning
    so operators can migrate their .env files without a hard break.
    """
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    if token:
        return token

    legacy = os.environ.get("TWILIO_TOKEN", "")
    if legacy and "TWILIO_TOKEN" not in _DEPRECATION_EMITTED:
        _DEPRECATION_EMITTED.add("TWILIO_TOKEN")
        warnings.warn(
            "TWILIO_TOKEN env var is deprecated; rename to TWILIO_AUTH_TOKEN. "
            "TWILIO_TOKEN will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2,
        )
    return legacy
```

**Source:** [CITED: https://docs.python.org/3.11/library/warnings.html#warnings.warn] — `stacklevel=2` causes the warning to appear attributed to the caller, not this helper.

**Test pattern** (from project convention in `tests/voice/test_call.py`):

```python
# Test: new var wins
def test_auth_token_reads_new_var(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "new_value")
    monkeypatch.delenv("TWILIO_TOKEN", raising=False)
    assert _get_twilio_auth_token() == "new_value"

# Test: legacy var triggers warning
def test_legacy_token_emits_deprecation(monkeypatch, recwarn):
    # Reset the once-per-process cache so the test isolates cleanly
    from skyherd.voice.call import _DEPRECATION_EMITTED
    _DEPRECATION_EMITTED.discard("TWILIO_TOKEN")
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("TWILIO_TOKEN", "legacy_value")

    with pytest.warns(DeprecationWarning, match="TWILIO_TOKEN"):
        result = _get_twilio_auth_token()
    assert result == "legacy_value"
```

`pytest.warns` is the standard pytest fixture for asserting warnings [CITED: https://docs.pytest.org/en/stable/how-to/capture-warnings.html#warns].

### Anti-Patterns to Avoid

- **Bare `except:` (no exception type):** Catches `BaseException` including `KeyboardInterrupt` and `SystemExit` — never acceptable. Ruff's `E722` blocks this; all current sites already use `except Exception:` or a specific type.
- **`except Exception: pass` without `as exc`:** Can't log the exception. Always capture: `except Exception as exc:`.
- **F-string formatting in log calls:** `logger.warning(f"failed: {exc}")` evaluates the string eagerly even when the log level is above WARNING. Use `%s`: `logger.warning("failed: %s", exc)`.
- **Raising `DeprecationWarning` eagerly at module import time:** Creates warnings even when the legacy var isn't set. Emit only on first use of the legacy var.
- **Using `logger.error()` for swallowed exceptions:** The codebase reserves `ERROR` for exceptions that propagate — swallowed-and-logged exceptions are `WARNING` per CONVENTIONS.md line 143.
- **Removing `# noqa: BLE001` on intentional broad catches:** Ruff's blind-except rule exists for a reason; the noqa + rationale comment is the project's escape valve.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var deprecation | Custom deprecation registry | `warnings.warn(..., DeprecationWarning, stacklevel=2)` | Stdlib; pytest auto-captures; respects `PYTHONWARNINGS` filter [CITED: docs.python.org/3.11/library/warnings.html]. |
| Once-per-process warning suppression | `functools.lru_cache` on a warning function | Module-level `set` of emitted-warnings keys, guarded check | lru_cache obscures intent; explicit set is transparent and mockable in tests. |
| Async test discovery | `@pytest.mark.asyncio` decorator | Nothing — `asyncio_mode = "auto"` is set | Already configured in `pyproject.toml:97` — async tests run without decoration [VERIFIED]. |
| Coverage reporting | Custom coverage aggregator | `pytest-cov` already wired to `pyproject.toml` | `[tool.coverage.run]` source + omit configured; no work needed [VERIFIED: pyproject.toml lines 108-120]. |
| Exception classification (WARNING vs DEBUG) | Custom error-level registry | Per-category convention table (see "Silent-Except Site Inventory") | The categories are few; a table in planning docs + reviewer discipline beats a library. |

**Key insight:** All tooling for Phase 3 is already in the repo. This phase's risk is not "did we pick the right library" — it's "did we apply the conventions consistently to 24 different sites without behavioral drift."

---

## Silent-Except Site Inventory

**Verified 2026-04-22 via `grep -rn "except" src/skyherd/` + manual context-window inspection.**

The CONCERNS.md §3 listing called out ~15 sites. The actual count is **24 holdout sites** — CONCERNS.md undercounted because some sites use `except ImportError: pass` or `except ValueError: pass` (typed but still silent) that HYG-01 phrasing ("no bare silent-catch") arguably covers. Plan must decide scope: all 24 → stricter interpretation; just the 15 broad `except:` → narrower. **Recommendation: all 24**, because a typed-silent catch that should warn is still a bug.

### Category 1: Async Task Cancellation (WONTFIX — leave as-is)

These catch `asyncio.CancelledError` during deliberate task shutdown. Logging a warning here would create false-positive noise on every clean shutdown.

| File | Line | Context | Recommendation |
|------|------|---------|----------------|
| `sensors/acoustic.py` | 66, 71 | `await self._cmd_task` during `run()` cancel | **Leave as-is.** `CancelledError` during cancellation is expected. |
| `sensors/base.py` | 79 | Base sensor `run()` cancel | **Leave as-is.** |
| `agents/mesh.py` | 162, 169 | `self._tick_task` / `self._mqtt_task` cancel on stop | **Leave as-is.** Already expected shutdown path. |
| `agents/mesh_neighbor.py` | 444 | Neighbor mesh cancel | **Leave as-is.** |
| `edge/watcher.py` | 238 | Task cancel in `finally` block | **Leave as-is.** |
| `edge/watcher.py` | 323 | `healthz` server cancel | **Leave as-is.** (Already has an adjacent `except OSError` that logs.) |

**Count: 8 WONTFIX sites.** These already use specific `except asyncio.CancelledError` — not the sloppy-catch that HYG-01 targets. Plan should document "leave these" so reviewers don't flag them.

### Category 2: Broad Exception Swallow (FIX — log at WARNING)

These are the true HYG-01 targets — broad `except Exception: pass` or `except: pass` that genuinely hide bugs.

| File | Line | What's swallowed | Recommended action |
|------|------|------------------|-------------------|
| `sensors/bus.py` | 201 (`except Exception: pass`) | aiomqtt `Client.__aexit__` close error | `except Exception as exc: logger.warning("aiomqtt client close failed: %s", exc)` |
| `voice/tts.py` | 195 (`except Exception: pass`) | `pydub AudioSegment.from_mp3` decode fallback | `except Exception as exc: logger.debug("pydub mp3 decode failed, falling back to raw bytes: %s", exc)` — DEBUG because falling back to direct MP3 write is a deliberate design choice, not a bug |
| `edge/watcher.py` | 454 (`except Exception: pass`) | mqtt `__aexit__` close | `logger.warning("mqtt client close failed: %s", exc)` |
| `drone/f3_inav.py` | 370, 377, 386, 393, 400 | Telemetry stream read failures | `logger.debug("mavsdk telemetry read for %s failed: %s", "armed|position|etc", exc)` — DEBUG because each field has a sensible default; spamming WARNING on every lost telemetry frame would drown real signal |

**Count: 8 FIX sites.** Recommended level: 3 at WARNING (the close-errors and similar), 6 at DEBUG (telemetry + format fallback — these are defensive, not error paths). Plan should be explicit about per-site level.

### Category 3: ImportError for Optional Deps (FIX — log at DEBUG)

Importing an optional dep and proceeding without it is a legitimate code path, but should still emit at DEBUG so operators debugging "why is this feature silent" have a breadcrumb.

| File | Line | What's swallowed | Recommended action |
|------|------|------------------|-------------------|
| `sensors/trough_cam.py` | 93 (`except ImportError: pass`) | `skyherd.vision.renderer` not available | `logger.debug("vision renderer unavailable — skipping trough frame render: %s", exc)` |

**Count: 1 FIX site.** DEBUG level.

### Category 4: Parse/Format Fallbacks (FIX — log at DEBUG)

Expected failure when input is malformed; a safe default is used.

| File | Line | What's swallowed | Recommended action |
|------|------|------------------|-------------------|
| `sensors/bus.py` | 268 (`except ValueError: pass`) | URL port parse — non-numeric string | `logger.debug("mqtt URL port unparseable in %r — using default %d", url, _DEFAULT_BROKER_PORT)` |
| `edge/watcher.py` | 111 (`except ValueError: pass`) | Same pattern (mqtt URL parse) | `logger.debug("mqtt URL port unparseable in %r — using default 1883", url)` |
| `sensors/bus.py` | 248 (`except (json.JSONDecodeError, TypeError): pass`) | Malformed MQTT payload | `logger.debug("malformed mqtt payload on %s: %s", topic, exc)` |

**Count: 3 FIX sites.** DEBUG level — parse failures happen routinely.

### Category 5: OS/Resource Race (FIX — log at DEBUG)

Cleanup or non-critical OS ops that race with other cleanup paths.

| File | Line | What's swallowed | Recommended action |
|------|------|------------------|-------------------|
| `scenarios/base.py` | 311 (`except OSError: pass`) | `_os.unlink(tmp.name)` after ledger close | `logger.debug("tmp ledger file already gone: %s", tmp.name)` **⚠ COORDINATE WITH PHASE 1** |
| `scenarios/cross_ranch_coyote.py` | 306 (`except OSError: pass`) | Same pattern | `logger.debug("tmp ledger file already gone: %s", tmp.name)` |
| `drone/sitl_emulator.py` | 445 (`except OSError: pass`) | Socket close race on shutdown | `logger.debug("sitl emulator socket close: %s", exc)` |
| `drone/sitl_emulator.py` | 466 (`except OSError: pass`) | UDP sendto failure (GCS not listening) | `logger.debug("sitl emulator sendto failed: %s", exc)` |
| `drone/sitl_emulator.py` | 742 (`except KeyboardInterrupt: pass`) | Main-loop signal handler | **Leave as-is.** Catching KeyboardInterrupt in a CLI main loop is intentional. |
| `voice/call.py` | 200 (`except OSError: pass`) | SSE event file write failure | `logger.debug("sse events.jsonl write failed (non-fatal): %s", exc)` |
| `edge/watcher.py` | 480 (`except (NotImplementedError, RuntimeError): pass`) | `loop.add_signal_handler` on Windows | Already has a comment explaining; add `logger.debug("signal handler unavailable on this platform")` |

**Count: 6 FIX sites + 1 WONTFIX (KeyboardInterrupt).**

### Category 6: Server/Queue Races (FIX — log at DEBUG or keep typed)

| File | Line | What's swallowed | Recommended action |
|------|------|------------------|-------------------|
| `server/events.py` | 298 (`except ValueError: pass`) | `list.remove` of already-removed subscriber | `logger.debug("sse subscriber already removed")` — DEBUG; this is a race with another removal path |
| `server/events.py` | 314 (`except (asyncio.QueueEmpty, asyncio.QueueFull): pass`) | Slow-consumer queue rotation race | `logger.debug("sse queue rotation race on slow consumer: %s", exc)` |

**Count: 2 FIX sites.**

### Special Case: `agents/fenceline_dispatcher.py:153` (unreachable-ish)

```python
if sdk_client is not None and os.environ.get("ANTHROPIC_API_KEY"):
    tool_calls = await run_handler_cycle(session, wake_event, sdk_client, cached_payload)
    if not tool_calls and not os.environ.get("SKYHERD_AGENTS"):
        pass  # ← line 153
```

This is an `if ... pass` (empty then-branch), not an exception catch. Ruff's `PIE790` rule would flag it; current config doesn't enable it. **Recommendation:** either remove the empty conditional entirely (it's unreachable because `not os.environ.get("SKYHERD_AGENTS")` combined with the outer condition is effectively a no-op given current logic), OR add `logger.debug("no tool calls returned for fenceline smoke-test path")` so the intent is documented. Flag for planner.

### Phase 1 Coordination: `scenarios/base.py:312`

Phase 1 (Agent Session Persistence & Routing) touches `_DemoMesh.dispatch()` at `scenarios/base.py:179` and the `_registry` dict at line 234. Phase 3 touches `scenarios/base.py:311-312` (the `os.unlink` silent-except in `_run_async` cleanup).

**These are non-overlapping line ranges** (Phase 1 is in lines 160-200 + 234-337; Phase 3 only touches lines 309-312). No edit-conflict risk if both phases land in the same merge window.

**Recommended strategy:** Phase 3 plans for its line as normal. If Phase 1 lands first (autonomous mode expected ordering), Phase 3 patch applies cleanly. If by some ordering swap Phase 3 lands first, Phase 1 still doesn't touch those lines. **Document but do not block on ordering.**

### Summary Count

- **24 sites found** by exhaustive grep.
- **9 WONTFIX** (CancelledError for shutdown + 1 KeyboardInterrupt in main loop).
- **14 FIX with log + keep-going semantics** (18 if counting each of the 5 f3_inav telemetry sites separately — they're a single pattern but repeated).
- **1 special case** (fenceline_dispatcher.py:153 empty `if`).

HYG-01 requirement language says "No bare silent-catch remains." After this phase, the only `except: pass` patterns left in `src/skyherd/` will be the 9 WONTFIX cases, all of which use *specific* exception types (`CancelledError`, `KeyboardInterrupt`) that are not "bare" by Python standards. The planner can then decide whether to document these as acceptable in a NOTES comment or to rephrase HYG-01 as "no broad-except silent-catch."

---

## Twilio Env Var Migration

### Current Footprint (7 source + 5 test + 1 doc + 1 runtime example + 1 env example)

```bash
# VERIFIED via: grep -rn "TWILIO_TOKEN\|TWILIO_AUTH_TOKEN" src/ tests/ docs/ *.md Makefile
```

| File | Line | Current | Target |
|------|------|---------|--------|
| `src/skyherd/voice/call.py` | 5 (docstring) | `TWILIO_TOKEN` | `TWILIO_AUTH_TOKEN` |
| `src/skyherd/voice/call.py` | 44 (`_twilio_available`) | `TWILIO_TOKEN` | call `_get_twilio_auth_token()` or check both |
| `src/skyherd/voice/call.py` | 68 (`_try_twilio_call`) | `TWILIO_TOKEN` | `_get_twilio_auth_token()` |
| `src/skyherd/mcp/rancher_mcp.py` | 77 (`_try_send_sms`) | `TWILIO_AUTH_TOKEN` already | no change, already correct |
| `src/skyherd/demo/hardware_only.py` | 25 (docstring) | `TWILIO_TOKEN` | `TWILIO_AUTH_TOKEN` |
| `src/skyherd/demo/hardware_only.py` | 486 | `TWILIO_TOKEN` | `_get_twilio_auth_token()` |
| `tests/voice/test_call.py` | 35, 90, 119, 133, 162, 178 | `TWILIO_TOKEN` | `TWILIO_AUTH_TOKEN` + add new deprecation tests |
| `tests/mcp/test_rancher_mcp.py` | 35, 206, 236 | `TWILIO_AUTH_TOKEN` already | no change |
| `docs/VOICE_ACCESS.md` | 35 | `TWILIO_TOKEN=your_auth_token` | `TWILIO_AUTH_TOKEN=your_auth_token` |
| `.env.example` | 17 | `TWILIO_TOKEN=...` | `TWILIO_AUTH_TOKEN=...` (+ comment: `# (legacy TWILIO_TOKEN still accepted with deprecation warning)`) |

### Migration Sequence

1. **Add the helper** `_get_twilio_auth_token()` — recommended location: new module `src/skyherd/voice/_twilio_env.py` (shared by `voice/call.py`, `mcp/rancher_mcp.py`, `demo/hardware_only.py`). Avoids three copies.
2. **Update `voice/call.py`** — replace both `os.environ.get("TWILIO_TOKEN", ...)` calls with helper. Update docstring.
3. **Update `demo/hardware_only.py`** — same replacement. Update docstring.
4. **Update `mcp/rancher_mcp.py`** — optionally call the helper for consistency (though it already reads the right var). Recommended: yes, to get the deprecation warning path.
5. **Update `.env.example`** — primary name `TWILIO_AUTH_TOKEN`, comment mentions legacy support.
6. **Update `docs/VOICE_ACCESS.md`** — primary name `TWILIO_AUTH_TOKEN`.
7. **Update existing tests** — flip `TWILIO_TOKEN` → `TWILIO_AUTH_TOKEN` in `tests/voice/test_call.py` (6 sites).
8. **Add new tests** — `test_legacy_token_still_works_with_deprecation_warning`, `test_new_token_wins_when_both_set`, `test_deprecation_warning_emitted_once`.

### Gotcha: The once-per-process cache

The `_DEPRECATION_EMITTED: set[str]` module-level state means the warning fires exactly once per process. In a pytest session with multiple tests, only the FIRST test to hit the legacy path will see the warning — subsequent tests will silently read the legacy value without the warning.

**Test fixture pattern:**

```python
@pytest.fixture(autouse=True)
def reset_twilio_deprecation_cache():
    from skyherd.voice._twilio_env import _DEPRECATION_EMITTED
    _DEPRECATION_EMITTED.clear()
    yield
    _DEPRECATION_EMITTED.clear()
```

Add to `tests/voice/conftest.py` (or the relevant test-file scope).

---

## cost.py Coverage Plan

### Baseline

**Measured 2026-04-22:** `uv run pytest tests/agents/test_cost.py --cov=skyherd.agents.cost` → **78.12%** (96 stmts, 21 missing). Missing lines: **165-170, 174-177, 187, 191, 205-216**.

### Uncovered Line Analysis

| Lines | Path | What they do | Test strategy |
|-------|------|--------------|---------------|
| 165-170 | `emit_tick` → MQTT publish callback branch | Calls `mqtt_publish_callback(topic, bytes)`; swallows exc at DEBUG | Pass a mock async callback; assert it was called with correct topic `skyherd/ranch_a/cost/ticker` and JSON-encoded payload. Also pass a callback that raises `RuntimeError`; assert swallowed without raising. |
| 174-177 | `emit_tick` → ledger callback branch | Calls `ledger_callback(payload)`; swallows exc at DEBUG | Pass a mock async callback; assert called with a `TickPayload`. Also pass a raising callback; assert swallowed. |
| 187 | `active_s` property return | Getter for `_active_s` | Trivial — call `t.active_s` after a few active ticks. |
| 191 | `idle_s` property return | Getter for `_idle_s` | Trivial — call `t.idle_s` after an idle tick. |
| 205-216 | `run_tick_loop` body | 1-Hz loop: emits ticks for each ticker; logs "all idle" when no active; sleeps 1s between iterations | Run the loop with 2 tickers (1 active, 1 idle) for a short time using `asyncio.wait_for` + cancel via stop_event; assert both tickers got `emit_tick` called. Use `monkeypatch` on `asyncio.sleep` to skip the 1s delay, or set stop_event before the first sleep. |

### Proposed New Tests

Add to `tests/agents/test_cost.py`:

```python
class TestMqttPublishCallback:
    async def test_publish_callback_called_with_topic_and_payload(self):
        captured: list[tuple[str, bytes]] = []
        async def mock_publish(topic: str, data: bytes) -> None:
            captured.append((topic, data))
        t = CostTicker(session_id="sess-1", mqtt_publish_callback=mock_publish)
        t.set_state("active")
        t._last_tick_time -= 1.0
        await t.emit_tick()
        assert len(captured) == 1
        topic, payload_bytes = captured[0]
        assert topic == "skyherd/ranch_a/cost/ticker"
        decoded = json.loads(payload_bytes.decode())
        assert decoded["session_id"] == "sess-1"

    async def test_publish_callback_failure_swallowed(self):
        async def failing_publish(topic, data):
            raise RuntimeError("mqtt broker down")
        t = CostTicker(session_id="sess-2", mqtt_publish_callback=failing_publish)
        t.set_state("active")
        t._last_tick_time -= 1.0
        # Should not raise
        result = await t.emit_tick()
        assert result is not None

class TestLedgerCallback:
    async def test_ledger_callback_called_with_payload(self):
        captured: list[TickPayload] = []
        async def mock_ledger(payload: TickPayload) -> None:
            captured.append(payload)
        t = CostTicker(session_id="sess-3", ledger_callback=mock_ledger)
        t.set_state("active")
        t._last_tick_time -= 1.0
        await t.emit_tick()
        assert len(captured) == 1
        assert captured[0].session_id == "sess-3"

    async def test_ledger_callback_failure_swallowed(self):
        async def failing_ledger(payload):
            raise RuntimeError("db locked")
        t = CostTicker(session_id="sess-4", ledger_callback=failing_ledger)
        t.set_state("active")
        t._last_tick_time -= 1.0
        result = await t.emit_tick()
        assert result is not None

class TestProperties:
    async def test_active_s_property(self):
        t = CostTicker(session_id="sess-prop-1")
        t.set_state("active")
        t._last_tick_time -= 10.0
        await t.emit_tick()
        assert t.active_s >= 9.0  # ~10s minus wall-clock drift

    async def test_idle_s_property(self):
        t = CostTicker(session_id="sess-prop-2")
        t.set_state("idle")
        t._last_tick_time -= 5.0
        await t.emit_tick()
        assert t.idle_s >= 4.0

class TestRunTickLoopBody:
    async def test_loop_ticks_all_tickers(self, monkeypatch):
        call_count: dict[str, int] = {"a": 0, "b": 0}
        t_a = CostTicker(session_id="a")
        t_b = CostTicker(session_id="b")
        t_a.set_state("active")
        # Monkey-patch emit_tick to count calls
        orig_a = t_a.emit_tick
        orig_b = t_b.emit_tick
        async def wrapped_a():
            call_count["a"] += 1
            return await orig_a()
        async def wrapped_b():
            call_count["b"] += 1
            return await orig_b()
        t_a.emit_tick = wrapped_a  # type: ignore[method-assign]
        t_b.emit_tick = wrapped_b  # type: ignore[method-assign]

        # Speed up the loop by patching sleep
        async def fast_sleep(_):
            pass
        monkeypatch.setattr("skyherd.agents.cost.asyncio.sleep", fast_sleep)

        stop_event = asyncio.Event()
        async def stop_after_few_iters():
            await asyncio.sleep(0)  # yield
            stop_event.set()
        task = asyncio.create_task(stop_after_few_iters())
        await run_tick_loop([t_a, t_b], stop_event)
        await task
        assert call_count["a"] >= 1
        assert call_count["b"] >= 1

    async def test_loop_swallows_ticker_exception(self, monkeypatch):
        t_boom = CostTicker(session_id="boom")
        async def raising_emit():
            raise RuntimeError("tick exploded")
        t_boom.emit_tick = raising_emit  # type: ignore[method-assign]

        async def fast_sleep(_):
            pass
        monkeypatch.setattr("skyherd.agents.cost.asyncio.sleep", fast_sleep)

        stop_event = asyncio.Event()
        async def stop_soon():
            await asyncio.sleep(0)
            stop_event.set()
        task = asyncio.create_task(stop_soon())
        # Must not raise
        await run_tick_loop([t_boom], stop_event)
        await task
```

### Expected Outcome

- All 21 missing lines covered.
- cost.py file coverage: **78% → ~98%** (only lines left would be edge-case `return None` branches, already covered).
- Project-wide coverage: **+~0.2 pp** (cost.py is 96 stmts out of ~10k total).
- **No regression risk** — tests are purely additive.

---

## Static Analysis Cleanup

### Ruff: 1 error, auto-fixable

```bash
uv run ruff check src/ tests/
# src/skyherd/server/app.py:114 — Import block is un-sorted or un-formatted
# 1 fixable with --fix
```

**Action:** `uv run ruff check --fix src/` (project convention per CONVENTIONS.md top). Resolves in one command.

### Pyright: 15 errors — scope expanded from CONTEXT assumption

**Verified 2026-04-22 via live `uv run pyright src/` run.** The CONTEXT.md claim "15 pyright errors confined to `drone/pymavlink_backend.py` and `drone/sitl_emulator.py`" is STALE. Actual current error distribution:

| File | Errors | Category | Phase-3 scope? |
|------|--------|----------|----------------|
| `src/skyherd/drone/pymavlink_backend.py` | 8 (7 attribute access + 1 call-arg) | Upstream `pymavlink` has no type stubs; `CSVReader`/`DFReader_*` types returned by `mavutil.mavlink_connection` don't have `wait_heartbeat` / `target_system` attrs in the stubs that DO exist | **YES.** Typed-ignore with rationale. |
| `src/skyherd/drone/sitl_emulator.py` | 1 (`reportOptionalMemberAccess` on `self._sock`) | Real nullability — `_sock` is `None` until bound | **YES.** Either `assert self._sock is not None` before use, or typed-ignore with rationale. |
| `src/skyherd/agents/managed.py` | 2 (line 388: `__aenter__`/`__aexit__` on coroutine) | `client.beta.sessions.events.stream()` returns a coroutine, not an async context manager. Needs `async with await client.beta.sessions.events.stream(...) as stream:` OR the SDK shape has changed | **⚠ COORDINATE WITH PHASE 1.** This file was stable before; Phase 1 restructures session handling. May be a real bug, may be a stubs issue. |
| `src/skyherd/agents/session.py` | 4 (lines 415-422: `ManagedSessionManager` return-type mismatch) | `LocalSessionManager` and `ManagedSessionManager` don't share a common base type, but `get_session_manager()` is declared as returning `SessionManager`. Also: `agent_ids_path: str` receives `None` | **⚠ COORDINATE WITH PHASE 1.** Phase 1 restructures this file. |

### Strategy: Two-Pass Pyright Cleanup

**Pass A: Drone files (independent of other phases)**

- `pymavlink_backend.py`: Add `# type: ignore[attr-defined, call-arg, return-value]` with inline comment `# pymavlink has no stubs for mavfile subclasses; runtime instance always has these attrs`.
- `sitl_emulator.py:582`: Replace `self._sock.recvfrom(...)` with `assert self._sock is not None` followed by the call. Runtime-harmless; pyright-satisfying.

**Pass B: agents/managed.py + agents/session.py (coordinate with Phase 1)**

Phase 1 owns these files. **The research recommendation is: Phase 3 explicitly defers these 6 errors to Phase 1's surface.** Phase 1's plan should include pyright-clean as an acceptance criterion for its own file changes.

Alternative: Phase 3 adds `# type: ignore` to the 6 sites with a TODO comment referencing Phase 1, and Phase 1 removes them when its restructure completes. More coordination overhead but unblocks Phase 3 independence.

**Recommendation: DEFER** to Phase 1. Rationale: Phase 1 will touch these files and may resolve the errors naturally as part of the session-persistence restructure. Adding throwaway type-ignores now just to remove them in Phase 1 is churn.

### Typed-Ignore Convention (from existing code)

From `pyproject.toml` line 154:
```
"src/skyherd/drone/sitl.py" = ["F821", "F841"]
```

and from CONVENTIONS.md line 68:
> `type: ignore[assignment]` used 5 times for `tuple()` casts where pymavlink types don't have stubs

**Pattern:** `# type: ignore[specific-rule]` inline + a comment on the same or previous line explaining why.

Example for pymavlink_backend.py:
```python
# pymavlink has no stubs for mavfile subclasses; wait_heartbeat exists at runtime
conn.wait_heartbeat()  # type: ignore[attr-defined]
```

---

## Coverage Math

**Baseline (measured 2026-04-22):** 87.42% across 10,xxx statements (exact count in `coverage report` output).

**HYG-03 contribution:** cost.py goes from 78% (21 missing / 96 stmts) to ~98% (2 missing / 96 stmts) = +19 covered statements. Against the global pool of ~10k statements, this is +~0.2 pp. Final coverage: **~87.6%**.

**HYG-01 contribution:** Ambiguous. New `logger.warning` / `logger.debug` calls add covered statements IF exercised by tests. Three scenarios:
- **Best case:** New error-path tests added alongside logger additions → +covered stmts.
- **Expected case:** No new tests; existing tests don't hit error paths → logger lines are uncovered → coverage drops by `(new_stmts_added) / total_stmts`. With ~15 FIX sites each adding ~2 lines (the `logger.warning` + trailing blank), that's ~30 new uncovered stmts → -0.3 pp. Final: ~87.3%, still safely above 80% gate.
- **Mitigation:** For high-value sites (bus.py close errors, voice/tts.py fallback), add a one-shot test that injects a failing mock and asserts the log call via `caplog` fixture.

**Recommendation:** Plan ≥1 `caplog`-based test per NEW logger.warning site in Category 2 (broad-except sweep). DEBUG-level sites don't need test coverage — they're defensive fallbacks covered by normal execution.

### caplog Pattern (pytest built-in)

```python
def test_bus_close_logs_warning_on_failure(caplog, monkeypatch):
    import logging
    caplog.set_level(logging.WARNING, logger="skyherd.sensors.bus")
    # ... setup bus with a mocked _client whose __aexit__ raises ...
    await bus._close_client()
    assert "aiomqtt client close failed" in caplog.text
```

[CITED: https://docs.pytest.org/en/stable/how-to/logging.html#caplog-fixture]

---

## Runtime State Inventory

**Not applicable.** Phase 3 is pure code-hygiene — no rename, no migration, no stored state. Confirmed:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no DB/file state keys changed | None |
| Live service config | None — no external service config touched | None |
| OS-registered state | None — no task scheduler / launchd entries | None |
| Secrets/env vars | `TWILIO_TOKEN` → `TWILIO_AUTH_TOKEN` is a rename, but with deprecation-warning fallback; operators can keep the old var in `.env.local` during transition. No value rotation required. | Update `.env.example` + `docs/VOICE_ACCESS.md`; flag to George that local `.env.local` can be updated at leisure. |
| Build artifacts | None — no packaging changes | None |

---

## Common Pitfalls

### Pitfall 1: Logger-formatting regressions

**What goes wrong:** A developer writes `logger.warning(f"failed: {exc}")` (f-string) instead of `logger.warning("failed: %s", exc)`.
**Why it happens:** Muscle memory from non-logging code.
**How to avoid:** Reviewer discipline. Project convention (CONVENTIONS.md:143) is `%s`-style. Ruff's `G004` rule (`logging-f-string`) would auto-flag this — **plan could enable `G` rule-set in ruff config** as a bonus hardening.
**Warning signs:** Any `logger.<level>(f"..."` in the diff.

### Pitfall 2: DeprecationWarning suppression in pytest

**What goes wrong:** Tests `test_legacy_token_emits_deprecation` fails to capture the warning because pytest by default turns some warnings into errors, OR the once-per-process cache from a prior test prevents the warning from firing.
**Why it happens:** `pyproject.toml` may have a `filterwarnings` setting; module-level `_DEPRECATION_EMITTED` set persists across tests.
**How to avoid:** (a) Use `pytest.warns(DeprecationWarning)` context manager; (b) autouse fixture resets the cache before each test.
**Warning signs:** Flaky test result depending on test-execution order.

### Pitfall 3: Silent-except categorization overcounts/undercounts

**What goes wrong:** Plan claims "15 sites" per CONCERNS.md but executor finds 24 via exhaustive grep; acceptance check is ambiguous.
**Why it happens:** CONCERNS.md audit listed the notable sites, not all of them.
**How to avoid:** Plan uses the 24-site inventory in this research doc as the canonical list; verifier re-runs `grep -rn "except.*:\s*pass$" src/skyherd/` and checks against the WONTFIX list.
**Warning signs:** Verifier task rejects because `grep` finds more sites than the plan's explicit list.

### Pitfall 4: pyright errors re-emerge after Phase 1

**What goes wrong:** Phase 3 types-ignores `agents/managed.py:388` and `agents/session.py:415-422`. Phase 1 restructures these files and the type-ignore comments are now on lines that no longer have errors (ruff/pyright will complain about "unused ignore").
**Why it happens:** Error-line-numbers shift.
**How to avoid:** Phase 3 **defers** these 6 errors to Phase 1 scope. Phase 3's "pyright clean" acceptance is measured on the *subset* of files Phase 3 owns (drone + sensors + scenarios + server + voice + edge) — managed.py and session.py are Phase 1's.
**Warning signs:** Phase 1 tests fail because `# type: ignore[unused-ignore]` warnings appear.

### Pitfall 5: Coverage regression via new uncovered logger lines

**What goes wrong:** Adding `logger.warning(...)` to 15 error paths without tests drops file-level coverage; project coverage drops below 87%.
**Why it happens:** New statements are added but not exercised.
**How to avoid:** For Category 2 sites (the WARNING-level ones), add `caplog` tests. For DEBUG-level sites, acknowledge the small coverage cost in the plan.
**Warning signs:** `make ci` fails with "fail_under=80" error (unlikely — buffer is 7pp), OR PROGRESS.md note that coverage dropped.

### Pitfall 6: Double-emitting DeprecationWarning in multi-module imports

**What goes wrong:** `voice/call.py` emits the warning, then `mcp/rancher_mcp.py` re-emits it because it has its own cache.
**Why it happens:** Shared state needs to live in one module.
**How to avoid:** Put `_get_twilio_auth_token()` and `_DEPRECATION_EMITTED` in **one** shared module (`voice/_twilio_env.py`). All callers import from there.
**Warning signs:** Test capturing warnings sees multiple emissions.

---

## Code Examples

### Example 1: Module-level logger + broad-except with rationale

```python
# Source: src/skyherd/mcp/rancher_mcp.py:92-100 (live reference impl)
except ImportError:
    _log.debug("twilio package not installed — SMS unavailable")
    return False
except Exception as exc:  # noqa: BLE001
    # Catches TwilioRestException, requests.exceptions.RequestException,
    # ssl.SSLError, etc. — log at WARNING so callers can surface the reason.
    _log.warning(
        "Twilio SMS failed (to=%s): %s: %s",
        to,
        type(exc).__name__,
        exc,
    )
    return False
```

### Example 2: Async test with `caplog` + `monkeypatch`

```python
# Source pattern from tests/voice/test_call.py (adapted)
async def test_bus_close_warns_on_aiomqtt_exit_error(caplog, monkeypatch):
    import logging
    caplog.set_level(logging.WARNING, logger="skyherd.sensors.bus")

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): raise RuntimeError("broker RST")

    bus = SensorBus(url="mqtt://localhost:1883")
    bus._client = FakeClient()  # type: ignore[assignment]
    await bus._close_client()

    assert "aiomqtt client close failed" in caplog.text
    assert "broker RST" in caplog.text
    assert bus._client is None  # cleanup still happens
```

### Example 3: Deprecation warning helper

```python
# Source: proposed src/skyherd/voice/_twilio_env.py
"""Shared Twilio env var readers with deprecation shim."""
from __future__ import annotations

import os
import warnings

_DEPRECATION_EMITTED: set[str] = set()


def get_twilio_auth_token() -> str:
    """Return Twilio auth token, preferring TWILIO_AUTH_TOKEN.

    Falls back to legacy TWILIO_TOKEN with a one-shot DeprecationWarning.
    """
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    if token:
        return token

    legacy = os.environ.get("TWILIO_TOKEN", "")
    if legacy and "TWILIO_TOKEN" not in _DEPRECATION_EMITTED:
        _DEPRECATION_EMITTED.add("TWILIO_TOKEN")
        warnings.warn(
            "TWILIO_TOKEN is deprecated; rename to TWILIO_AUTH_TOKEN in "
            "your .env file. Legacy name will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2,
        )
    return legacy
```

### Example 4: Typed-ignore with rationale for pymavlink

```python
# Source: proposed src/skyherd/drone/pymavlink_backend.py:124-125
# pymavlink types expose mavfile subclasses (DFReader_binary, CSVReader,
# DFReader_text) that don't declare wait_heartbeat / target_system in their
# stubs. Runtime instances always have these attrs on mavutil-returned objects.
self._target_system = conn.target_system  # type: ignore[attr-defined]
conn.wait_heartbeat()  # type: ignore[attr-defined]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bare `except: pass` in Python | Broad-except with logger + `# noqa: BLE001` rationale | Python style has trended this way since PEP 20 ("errors should never pass silently"); ruff's `BLE001` rule enforces it | This phase closes holdout sites |
| Env var rename via `os.environ.get(new) or os.environ.get(old)` without signal | `os.environ.get(new)` preferred, `os.environ.get(old)` fallback + `DeprecationWarning` | Standard Python deprecation idiom per PEP 565 (2017) | HYG-02 adopts this |
| Ignoring `pyright` errors project-wide | Per-file / per-line typed-ignore with rationale | Current pyright practice since 2022 | HYG-04 completes the adoption |
| F-string log calls | `%s`-style log calls | Python logging has worked this way since 2.3; ruff's `G004` is 2023+ | CONVENTIONS.md already mandates; this phase keeps compliance |

**Deprecated/outdated:**
- **`print()` statements for diagnostics:** Already banned project-wide (CONVENTIONS.md:141). No action.
- **`logging.exception()` inside broad-except without re-raise:** `exception()` auto-adds tracebacks at ERROR level, which the project avoids (reserves ERROR for propagating exceptions). Phase 3 uses `.warning()` with explicit `%s: %s` formatting.

---

## Assumptions Log

Every claim in this research was verified against the live codebase or official docs. No `[ASSUMED]` claims remain.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|

**If this table is empty: All claims in this research were verified or cited — no user confirmation needed.**

---

## Open Questions (RESOLVED)

1. **How strict is "no bare silent-catch"?**
   - What we know: HYG-01 says "No bare silent-catch remains." Audit listed ~15 sites; exhaustive grep finds 24.
   - What's unclear: Does HYG-01 target all 24 (including typed `except CancelledError: pass` for shutdown), or only the broad `except Exception: pass` sites?
   - Recommendation: Plan targets the 14-15 FIX sites (Categories 2-6 minus KeyboardInterrupt); documents the 9 CancelledError/KeyboardInterrupt sites as "acceptable non-bare silent catch" with a NOTES comment. Verifier rejects PR if `grep -rn "except Exception:\s*$" src/skyherd/` (note: multiline) finds any broad sites.

2. **Phase 1 pyright coordination — blocking or advisory?**
   - What we know: Phase 3 touches drone files (clean 9 errors); Phase 1 will restructure `agents/managed.py` + `agents/session.py` (dirty 6 errors).
   - What's unclear: Does HYG-04's "ruff + pyright clean" acceptance require ZERO pyright errors across all `src/` at end of Phase 3, or just in files Phase 3 owns?
   - Recommendation: Plan documents acceptance as "pyright clean for files Phase 3 modified"; Phase 1 independently owns its surface. If George prefers a zero-errors hard gate, Phase 3 adds temporary type-ignores to managed.py/session.py with TODO:Phase1 comments.

3. **New module `voice/_twilio_env.py` or helper in existing files?**
   - What we know: Helper is used by `voice/call.py`, `mcp/rancher_mcp.py`, `demo/hardware_only.py`.
   - What's unclear: Should it be a new module, or inlined in the three consumers (with duplicated `_DEPRECATION_EMITTED` set — BAD), or placed in an existing shared util module?
   - Recommendation: Create `src/skyherd/voice/_twilio_env.py`. The `_` prefix signals private-to-package. `voice/` is the natural home because call.py is the primary consumer; rancher_mcp.py imports across subsystems (existing pattern: rancher_mcp.py already imports from `skyherd.voice.call`).

---

## Environment Availability

**Not applicable at runtime.** Phase 3 is code-hygiene only — no new tools, services, or external dependencies.

Tooling check (all already installed and verified 2026-04-22):

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | `uv run pytest / pyright / ruff` | ✓ | `uv --version` passes | — |
| `pyright` | HYG-04 | ✓ | Installed via dev-deps | — |
| `ruff` | HYG-04 | ✓ | Installed via dev-deps | — |
| `pytest` | HYG-03 + HYG-05 | ✓ | 9.0.3 | — |
| `pytest-cov` | HYG-05 | ✓ | 7.1.0 | — |

**Missing dependencies with no fallback:** None.

---

## Validation Architecture

Phase 3 is test-heavy. `workflow.nyquist_validation` is `true` per `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 0.24+ + pytest-cov 7.1.0 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]` + `[tool.coverage.run]`) |
| Quick run command | `uv run pytest tests/agents/test_cost.py tests/voice/test_call.py tests/mcp/test_rancher_mcp.py tests/sensors/test_bus.py -x --no-cov` |
| Full suite command | `make test` (equivalent to `uv run pytest --cov=src/skyherd --cov-report=term`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HYG-01 | Zero bare silent-catch in `src/skyherd/` | static | `! grep -rEn 'except Exception:\s*pass\s*$' src/skyherd/ && ! grep -rEn 'except:\s*pass\s*$' src/skyherd/` | ✅ grep available |
| HYG-01 | New logger.warning sites are exercised (Category 2) | unit | `uv run pytest tests/sensors/test_bus.py::test_close_client_warns_on_exit_error -x` | ❌ Wave 0 — new test file |
| HYG-01 | f3_inav telemetry fallback logs at DEBUG | unit | `uv run pytest tests/drone/test_f3_inav.py::test_telemetry_fallback_debug_log -x` | ❌ Wave 0 — new test |
| HYG-02 | TWILIO_AUTH_TOKEN primary path works | unit | `uv run pytest tests/voice/test_call.py::TestTwilioAuthToken::test_auth_token_reads_new_var -x` | ❌ Wave 0 — rename + new tests |
| HYG-02 | Legacy TWILIO_TOKEN emits DeprecationWarning | unit | `uv run pytest tests/voice/test_twilio_env.py::test_legacy_token_emits_deprecation -x` | ❌ Wave 0 — new test file |
| HYG-02 | Deprecation emitted once per process | unit | `uv run pytest tests/voice/test_twilio_env.py::test_deprecation_warning_emitted_once -x` | ❌ Wave 0 |
| HYG-03 | cost.py MQTT publish callback exercised | unit | `uv run pytest tests/agents/test_cost.py::TestMqttPublishCallback -x` | ❌ Wave 0 |
| HYG-03 | cost.py ledger callback exercised | unit | `uv run pytest tests/agents/test_cost.py::TestLedgerCallback -x` | ❌ Wave 0 |
| HYG-03 | cost.py properties exercised | unit | `uv run pytest tests/agents/test_cost.py::TestProperties -x` | ❌ Wave 0 |
| HYG-03 | cost.py run_tick_loop body exercised | unit | `uv run pytest tests/agents/test_cost.py::TestRunTickLoopBody -x` | ❌ Wave 0 |
| HYG-03 | cost.py coverage ≥90% (per-file) | static | `uv run pytest tests/agents/test_cost.py --cov=skyherd.agents.cost --cov-fail-under=90 --no-cov-on-fail 2>&1` | ✅ pytest-cov supports per-file |
| HYG-04 | Ruff exits 0 | static | `uv run ruff check src/ tests/` | ✅ |
| HYG-04 | Pyright exits 0 for Phase-3-owned files | static | `uv run pyright src/skyherd/drone/pymavlink_backend.py src/skyherd/drone/sitl_emulator.py src/skyherd/sensors/ src/skyherd/voice/ src/skyherd/edge/ src/skyherd/server/` | ✅ pyright supports file args |
| HYG-05 | Global coverage ≥87% (regression guard) | static | `uv run pytest --cov=src/skyherd --cov-report=term --cov-fail-under=87` | ✅ pytest-cov has gate flag |
| HYG-05 | Global coverage gate ≥80% holds (hard gate) | static | `make test` (uses pyproject.toml `fail_under=80`) | ✅ |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/<task-touched-file>.py -x --no-cov` (seconds)
- **Per wave merge:** `uv run pytest tests/agents/ tests/voice/ tests/mcp/ tests/sensors/ -x` (10-20s)
- **Phase gate:** `make ci` (ruff + pyright + full pytest + coverage report) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/voice/test_twilio_env.py` — covers HYG-02 (new module + deprecation tests)
- [ ] `tests/voice/conftest.py` — autouse fixture to reset `_DEPRECATION_EMITTED` cache between tests
- [ ] `tests/voice/test_call.py` — update 6 existing `TWILIO_TOKEN` references to `TWILIO_AUTH_TOKEN`; add `TestTwilioAuthToken` class
- [ ] `tests/agents/test_cost.py` — add 4 new test classes (MqttPublishCallback, LedgerCallback, Properties, RunTickLoopBody) covering lines 165-216
- [ ] `tests/sensors/test_bus.py` — add `test_close_client_warns_on_exit_error` (caplog pattern)
- [ ] `tests/sensors/test_bus.py` — add `test_parse_url_debug_log_on_bad_port` (caplog pattern)
- [ ] `tests/sensors/test_trough_cam.py` — add `test_frame_render_debug_log_on_import_error` (caplog)
- [ ] `tests/voice/test_tts.py` — add `test_mp3_decode_debug_log_on_fallback` (caplog)
- [ ] `tests/edge/test_watcher.py` — add `test_mqtt_close_warns_on_exit_error` (caplog)
- [ ] No new framework install — pytest/pytest-cov/ruff/pyright all present

---

## Security Domain

`security_enforcement` is absent from `.planning/config.json`, so defaults to enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | partial | HYG-02 touches Twilio auth token handling. Security-relevant change: deprecation shim must NOT log or expose the secret value. Use `%s: %s` with `type(exc).__name__` NOT `exc.args` in logger calls — `exc.args` may contain the token in Twilio SDK errors. |
| V3 Session Management | no | Not in scope — session changes belong to Phase 1. |
| V4 Access Control | no | No access-control surface. |
| V5 Input Validation | no | No external input parsing added. |
| V6 Cryptography | no | No new crypto; attestation ledger untouched. |
| V7 Error Handling and Logging | **YES** | HYG-01 is literally an error-handling + logging overhaul. Controls: (a) never log raw exception message when it may contain secrets (Twilio auth failures could echo the token); (b) use `type(exc).__name__` + truncated message. |
| V14 Configuration | partial | HYG-02 changes `.env.example`. Verify no real secret value leaks into `.env.example` (audit confirms current `.env.example` has placeholder-only values per CONCERNS.md §4). |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret leak via exception message in logs | Information Disclosure | Log `type(exc).__name__` and a short description; never log `str(exc)` directly for auth-error paths. The existing `rancher_mcp.py:95-100` pattern logs `type(exc).__name__` + `exc` — acceptable for Twilio because TwilioRestException messages are structured and don't echo the token, but re-verify for new sites. |
| DeprecationWarning masking env-var misconfig | Tampering (config) | `DeprecationWarning` is captured by pytest and by `PYTHONWARNINGS=default::DeprecationWarning` — operators can surface it in production by setting `PYTHONWARNINGS`. Document this in `.env.example` comment. |
| Silent-except hiding auth failures | Information Disclosure (covering up breaches) | HYG-01 itself is the mitigation — exception paths now emit at WARNING. No new threat introduced. |
| Warning filter bypass in tests | — | `pytest.warns(DeprecationWarning)` is a context manager; any test that fails to enter the context won't catch the warning. Use `match=` to pin the warning message text. |

---

## Project Constraints (from CLAUDE.md)

- **All code new.** No imports from sibling `/home/george/projects/active/drone/` repo. Phase 3 is hygiene on existing `skyherd-engine/` code — compliant by default.
- **MIT throughout.** No new deps added in Phase 3 — compliant.
- **TDD.** RED → GREEN → IMPROVE. Plan must structure new cost.py/Twilio/caplog tests as failing-first before implementation.
- **Skills-first architecture.** Not applicable — no new agent prompts in this phase.
- **No Claude/Anthropic attribution in commits.** Global git config handles this.
- **Sim-first hardline.** Phase 3 is pure-sim friendly — no hardware-only changes. Compliant.
- **Ruff + pyright gate on CI.** `make ci` is the gate. Phase 3 must leave both green (for Phase-3-owned files at minimum).

---

## Sources

### Primary (HIGH confidence)

- `.planning/codebase/CONCERNS.md` §3, §4, §5 — audit-verified silent-except sites, Twilio inconsistency, coverage gaps [2026-04-22]
- `.planning/codebase/CONVENTIONS.md` — logger patterns (lines 139-144), broad-except idiom (lines 120-122), typed-ignore discipline (line 68) [2026-04-22]
- `.planning/codebase/TESTING.md` — pytest/asyncio config, caplog pattern, coverage 87.42% baseline [2026-04-22]
- Live `uv run ruff check src/ tests/` — 1 error, line 114 [2026-04-22]
- Live `uv run pyright src/` — 15 errors across 3 files (drone + managed + session) [2026-04-22]
- Live `uv run pytest tests/agents/test_cost.py --cov=skyherd.agents.cost` — 78.12%, missing 165-170, 174-177, 187, 191, 205-216 [2026-04-22]
- `src/skyherd/mcp/rancher_mcp.py:92-100` — reference impl for broad-except + Twilio env var [read 2026-04-22]
- `src/skyherd/voice/call.py:91-100` — adjacent correct impl of logged-warning pattern [read 2026-04-22]
- `src/skyherd/agents/cost.py` — current 96-stmt implementation [read 2026-04-22]

### Secondary (MEDIUM confidence — stdlib docs)

- Python 3.11 `warnings` module — `DeprecationWarning`, `stacklevel` semantics [https://docs.python.org/3.11/library/warnings.html]
- Python 3.11 `logging` module — `%s`-style formatting best practice [https://docs.python.org/3.11/howto/logging.html#optimization]
- pytest `caplog` fixture [https://docs.pytest.org/en/stable/how-to/logging.html#caplog-fixture]
- pytest `warns` fixture [https://docs.pytest.org/en/stable/how-to/capture-warnings.html#warns]

### Tertiary (LOW confidence)

None — everything in this research is backed by Primary or Secondary sources.

---

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — all tooling already installed and verified via live commands.
- Silent-except inventory: **HIGH** — exhaustive grep against current code, manually classified each site.
- Twilio migration: **HIGH** — reference impl in same codebase; 7 call-site footprint verified via grep.
- cost.py coverage plan: **HIGH** — missing lines verified via live `pytest --cov`; test strategy follows existing conventions.
- Pyright cleanup: **HIGH** for drone files, **MEDIUM** for `managed.py`/`session.py` (depends on Phase 1 outcome).
- Pitfalls: **HIGH** — drawn from direct code inspection.
- Phase 1 coordination: **MEDIUM** — depends on Phase 1's final file shape, which is still under planning.

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (code hygiene patterns are stable; 30-day half-life)

---

## RESEARCH COMPLETE
