# Phase 3: Code Hygiene Sweep - Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 17 (14 modified + 3 new/extended)
**Analogs found:** 17 / 17

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/skyherd/sensors/bus.py` (lines 200, 248, 268) | utility | event-driven | `src/skyherd/sensors/bus.py:216-223` (existing reconnect catch) | exact |
| `src/skyherd/sensors/trough_cam.py` (line 93) | sensor | event-driven | `src/skyherd/mcp/rancher_mcp.py:89-91` (ImportError → debug) | exact |
| `src/skyherd/server/events.py` (lines 298, 314) | service | event-driven | `src/skyherd/agents/cost.py:169, 176` (typed-catch + debug) | exact |
| `src/skyherd/drone/f3_inav.py` (lines 369-400) | service | request-response | `src/skyherd/agents/cost.py:169` (BLE001 + debug) | exact |
| `src/skyherd/drone/sitl_emulator.py` (lines 444, 465) | service | request-response | `src/skyherd/sensors/bus.py:200` (OSError close) | role-match |
| `src/skyherd/drone/sitl_emulator.py` (line 582) | service | request-response | `src/skyherd/drone/pymavlink_backend.py:89` (nullability) | exact |
| `src/skyherd/voice/tts.py` (line 194) | utility | transform | `src/skyherd/mcp/rancher_mcp.py:92-100` (BLE001 + fallback comment) | exact |
| `src/skyherd/edge/watcher.py` (lines 111, 454, 480) | service | event-driven | `src/skyherd/sensors/bus.py:200-201` (OSError + BLE001) | exact |
| `src/skyherd/scenarios/base.py` (line 311) | utility | batch | `src/skyherd/edge/watcher.py:444-455` (OSError close pattern) | role-match |
| `src/skyherd/scenarios/cross_ranch_coyote.py` (line 306) | utility | batch | `src/skyherd/edge/watcher.py:444-455` | role-match |
| `src/skyherd/voice/call.py` (lines 44, 68) | service | request-response | `src/skyherd/mcp/rancher_mcp.py:76-77` (TWILIO_AUTH_TOKEN) | exact |
| `src/skyherd/voice/call.py` (line 200) | service | file-I/O | `src/skyherd/voice/tts.py:194-195` (BLE001 + pass) | exact |
| `src/skyherd/demo/hardware_only.py` (line 486) | utility | request-response | `src/skyherd/mcp/rancher_mcp.py:76-77` | exact |
| **NEW** `src/skyherd/voice/_twilio_env.py` | utility | request-response | `src/skyherd/agents/cost.py:1-26` (small utility module structure) | role-match |
| `src/skyherd/drone/pymavlink_backend.py` (pyright, 8 errors) | service | request-response | `pyproject.toml:155` (per-file-ignores / sitl.py F821) | exact |
| `tests/agents/test_cost.py` (extend with 4 new classes) | test | CRUD | `tests/agents/test_cost.py:145-156` (existing TestRunTickLoop) | exact |
| `tests/voice/test_call.py` (extend + conftest) | test | request-response | `tests/voice/test_call.py:97-171` (TestTryTwilioCall) | exact |

---

## Pattern Assignments

### Silent-Except → Logged Warning (HYG-01 master pattern)

**Analog:** `src/skyherd/mcp/rancher_mcp.py` lines 89-100

**The canonical BLE001 exception pattern** (copy for all Category 2 / broad-swallow sites):
```python
except Exception as exc:  # noqa: BLE001
    # <one-line comment enumerating which real exceptions land here>
    logger.warning(
        "<meaningful description> (context=%s): %s: %s",
        <context_value>,
        type(exc).__name__,
        exc,
    )
```

**The canonical ImportError → DEBUG pattern** (copy for Category 3 / optional-dep sites):
```python
except ImportError as exc:
    logger.debug("<module> unavailable — skipping <feature>: %s", exc)
```

**The canonical parse-fallback → DEBUG pattern** (copy for Category 4 / parse sites):
```python
except (ValueError, json.JSONDecodeError, TypeError) as exc:
    logger.debug("<description of what failed> in %r — using default: %s", <context>, exc)
```

**The canonical OS-race → DEBUG pattern** (copy for Category 5 / OS cleanup sites):
```python
except OSError as exc:
    logger.debug("<resource> close/cleanup race (non-fatal): %s", exc)
```

**Log format rule (project-wide):** Always `%s`-style, never f-strings in logger calls. This is the project convention from CONVENTIONS.md:143. Any `logger.<level>(f"...")` in the diff is a bug.

---

### `src/skyherd/sensors/bus.py` (lines 200, 248, 268) — event-driven utility

**Analog:** `src/skyherd/sensors/bus.py:216-223` (existing reconnect-failure catch in same file)

**Existing logger declaration** (line 1-area):
```python
# src/skyherd/sensors/bus.py — already has:
logger = logging.getLogger(__name__)
```

**Line 200 — aiomqtt close (Category 2 → WARNING):**
```python
# BEFORE:
except Exception:  # noqa: BLE001
    pass

# AFTER:
except Exception as exc:  # noqa: BLE001
    # aiomqtt.Client.__aexit__ may raise on broker disconnect during close
    logger.warning("aiomqtt client close failed: %s", exc)
```

**Line 248 — JSON payload parse (Category 4 → DEBUG):**
```python
# BEFORE:
except (json.JSONDecodeError, TypeError): pass

# AFTER:
except (json.JSONDecodeError, TypeError) as exc:
    logger.debug("malformed mqtt payload on %s: %s", topic, exc)
```

**Line 268 — URL port parse (Category 4 → DEBUG):**
```python
# BEFORE:
except ValueError:
    pass

# AFTER:
except ValueError as exc:
    logger.debug("mqtt URL port unparseable in %r — using default %d: %s", url, _DEFAULT_BROKER_PORT, exc)
```

---

### `src/skyherd/sensors/trough_cam.py` (line 93) — optional dep ImportError

**Analog:** `src/skyherd/mcp/rancher_mcp.py:89-91`

**Line 93 — ImportError for optional vision dep (Category 3 → DEBUG):**
```python
# BEFORE:
except ImportError:
    pass

# AFTER:
except ImportError as exc:
    logger.debug("vision renderer unavailable — skipping trough frame render: %s", exc)
```

---

### `src/skyherd/server/events.py` (lines 298, 314) — queue race (Category 6)

**Analog:** `src/skyherd/agents/cost.py:169, 176` (typed catches + debug in same file)

**Line 298 — list.remove race (Category 6 → DEBUG):**
```python
# BEFORE:
except ValueError:
    pass

# AFTER:
except ValueError:
    logger.debug("sse subscriber already removed (concurrent removal race)")
```

**Lines 311-315 — queue rotation race (Category 6 → DEBUG):**
```python
# BEFORE:
except (asyncio.QueueEmpty, asyncio.QueueFull):
    pass

# AFTER:
except (asyncio.QueueEmpty, asyncio.QueueFull) as exc:
    logger.debug("sse queue rotation race on slow consumer: %s", exc)
```

---

### `src/skyherd/drone/f3_inav.py` (lines 369-400) — telemetry stream failures

**Analog:** `src/skyherd/agents/cost.py:169` (BLE001 + debug swallow)

These 5 sites are a single repeated pattern — each catch a broad `Exception` from an async telemetry iterator. Use DEBUG (not WARNING) because each field has a safe default and spamming WARNING on every lost telemetry frame drowns real signal.

**Pattern for all 5 telemetry sites (lines 369, 376, 385, 392, 399):**
```python
# BEFORE:
except Exception:
    pass

# AFTER (repeat for each field — armed/in_air/position/battery/flight_mode):
except Exception as exc:  # noqa: BLE001
    # mavsdk telemetry stream may not be ready on first poll — safe default used
    logger.debug("mavsdk telemetry read for <field_name> failed: %s", exc)
```

Field name strings: `"armed"`, `"in_air"`, `"position"`, `"battery"`, `"flight_mode"`.

---

### `src/skyherd/drone/sitl_emulator.py` (lines 444, 465, 582)

**Analog for lines 444, 465:** `src/skyherd/edge/watcher.py:451-454` (OSError close BLE001)

**Line 444 — socket close race (Category 5 → DEBUG):**
```python
# BEFORE:
except OSError:
    pass

# AFTER:
except OSError as exc:
    logger.debug("sitl emulator socket close race (non-fatal): %s", exc)
```

**Line 465 — UDP sendto failure (Category 5 → DEBUG):**
```python
# BEFORE:
except OSError:
    pass

# AFTER:
except OSError as exc:
    logger.debug("sitl emulator sendto failed (GCS not listening): %s", exc)
```

**Line 582 — pyright: `self._sock` optional member access (HYG-04):**

**Analog:** `src/skyherd/drone/pymavlink_backend.py:89` (nullability guard pattern)

```python
# BEFORE (triggers reportOptionalMemberAccess):
data, addr = self._sock.recvfrom(1024)

# AFTER — assert before use (runtime-harmless; pyright-satisfying):
assert self._sock is not None  # bound in _start(); never None when _running is True
data, addr = self._sock.recvfrom(1024)
```

---

### `src/skyherd/voice/tts.py` (line 194) — pydub mp3 decode fallback

**Analog:** `src/skyherd/mcp/rancher_mcp.py:92-100` (BLE001 + fallback comment)

```python
# BEFORE:
except Exception:  # noqa: BLE001
    pass

# AFTER:
except Exception as exc:  # noqa: BLE001
    # pydub may fail on some mp3 encodings; raw-bytes fallback follows
    logger.debug("pydub mp3 decode failed — falling back to raw bytes write: %s", exc)
```

---

### `src/skyherd/edge/watcher.py` (lines 111, 454, 480)

**Analog:** `src/skyherd/sensors/bus.py:200` (OSError pattern) and `src/skyherd/edge/watcher.py:475-480` (existing signal handler comment)

**Line 111 — URL port parse (Category 4 → DEBUG):**
```python
# BEFORE:
except ValueError:
    pass

# AFTER:
except ValueError as exc:
    logger.debug("mqtt URL port unparseable in %r — using default 1883: %s", url, exc)
```

**Line 454 — mqtt close race (Category 2 → WARNING):**
```python
# BEFORE:
except Exception:  # noqa: BLE001
    pass

# AFTER:
except Exception as exc:  # noqa: BLE001
    # aiomqtt.Client.__aexit__ may raise on broker disconnect during watcher shutdown
    logger.warning("mqtt client close failed during EdgeWatcher shutdown: %s", exc)
```

**Lines 478-480 — signal handler unavailable (Category 5 → DEBUG):**
```python
# BEFORE:
except (NotImplementedError, RuntimeError):
    # Windows / test environments may not support add_signal_handler
    pass

# AFTER:
except (NotImplementedError, RuntimeError) as exc:
    # Windows / test environments may not support loop.add_signal_handler
    logger.debug("signal handler unavailable on this platform: %s", exc)
```

---

### `src/skyherd/scenarios/base.py` (line 311) and `scenarios/cross_ranch_coyote.py` (line 306)

**Analog:** `src/skyherd/edge/watcher.py:444-455` (OSError cleanup pattern)

**NOTE: COORDINATE WITH PHASE 1** — non-overlapping line ranges confirmed but document explicitly.

```python
# BEFORE:
except OSError:
    pass

# AFTER:
except OSError as exc:
    logger.debug("tmp ledger file already gone (cleanup race — non-fatal): %s", tmp.name)
```

Note: `tmp.name` is always the context — do not log `exc` (it reveals the errno but not the path). Use `tmp.name` for operator debuggability.

---

### NEW `src/skyherd/voice/_twilio_env.py` — env var migration helper (HYG-02)

**Analog:** `src/skyherd/agents/cost.py:1-26` (small utility module: `from __future__ import annotations`, stdlib-only imports, module-level logger, single public function)

**Full module structure to copy from `cost.py` preamble pattern:**
```python
# src/skyherd/agents/cost.py lines 1-26 (module preamble pattern):
"""CostTicker — per-session cost metering..."""

from __future__ import annotations

import asyncio
import json
import logging
import time
# ...

logger = logging.getLogger(__name__)
```

**New module content pattern:**
```python
"""_twilio_env — single source of truth for Twilio auth token lookup.

Prefers TWILIO_AUTH_TOKEN. Falls back to legacy TWILIO_TOKEN with a
one-shot DeprecationWarning so operators can migrate .env files without
a hard break. TWILIO_TOKEN will be removed in a future release.
"""

from __future__ import annotations

import os
import warnings

_DEPRECATION_EMITTED: set[str] = set()


def _get_twilio_auth_token() -> str:
    """Return Twilio auth token from env, preferring TWILIO_AUTH_TOKEN."""
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

**Key points:**
- No `logger` import — uses `warnings.warn` not `logger.warning` for DeprecationWarning (pytest captures it; respects `PYTHONWARNINGS` filter).
- `_DEPRECATION_EMITTED: set[str]` is module-level state — tests must clear it between runs (see conftest fixture below).
- `stacklevel=2` attributes the warning to the caller, not the helper itself.

---

### `src/skyherd/voice/call.py` (lines 5, 44, 68) — TWILIO_TOKEN → TWILIO_AUTH_TOKEN

**Analog for token reads:** `src/skyherd/mcp/rancher_mcp.py:76-77`

```python
# mcp/rancher_mcp.py:76-77 — already correct (reference, no change needed):
token = os.environ.get("TWILIO_AUTH_TOKEN", "")
```

**Line 44 `_twilio_available()`:**
```python
# BEFORE:
def _twilio_available() -> bool:
    return bool(
        os.environ.get("TWILIO_SID")
        and os.environ.get("TWILIO_TOKEN")
        and os.environ.get("TWILIO_FROM")
    )

# AFTER:
from skyherd.voice._twilio_env import _get_twilio_auth_token

def _twilio_available() -> bool:
    return bool(
        os.environ.get("TWILIO_SID")
        and _get_twilio_auth_token()
        and os.environ.get("TWILIO_FROM")
    )
```

**Line 68 `_try_twilio_call()`:**
```python
# BEFORE:
token = os.environ.get("TWILIO_TOKEN", "")

# AFTER:
token = _get_twilio_auth_token()
```

**Line 200 `_maybe_emit_sse()` (Category 5 → DEBUG):**
```python
# BEFORE:
except OSError:
    pass  # non-fatal

# AFTER:
except OSError as exc:
    logger.debug("sse events.jsonl write failed (non-fatal): %s", exc)
```

---

### `src/skyherd/demo/hardware_only.py` (line 486, docstring line 25)

**Analog:** `src/skyherd/voice/call.py:44` (post-migration call pattern)

```python
# BEFORE:
twilio_token = os.environ.get("TWILIO_TOKEN", "")

# AFTER:
from skyherd.voice._twilio_env import _get_twilio_auth_token
twilio_token = _get_twilio_auth_token()
```

Update docstring mention on line 25 from `TWILIO_TOKEN` to `TWILIO_AUTH_TOKEN`.

---

### `src/skyherd/drone/pymavlink_backend.py` — pyright cleanup (HYG-04, Pass A)

**Analog:** `pyproject.toml:155` (`"src/skyherd/drone/sitl.py" = ["F821", "F841"]`) and existing `# type: ignore[import]` in same file line 84 (rancher_mcp.py)

**Pattern for all 8 pymavlink attribute/call errors:**
```python
# pymavlink has no stubs for mavfile subclasses; wait_heartbeat/target_system/
# target_component exist at runtime on all mavfile subclass instances.
conn.wait_heartbeat(timeout=2.0)  # type: ignore[attr-defined]
```

Apply `# type: ignore[attr-defined]` inline with a preceding comment on the same block:
- One comment block per method/attribute group (not per line)
- Comment text: `# pymavlink has no stubs for mavfile subclasses; <attr> exists at runtime`

---

### `tests/agents/test_cost.py` — extend with 4 new test classes (HYG-03)

**Analog:** `tests/agents/test_cost.py:145-156` (existing `TestRunTickLoop` class structure)

**Import pattern to add** (copy from existing lines 1-18):
```python
# Already imported — add only what's missing:
import json  # add this line (needed by TestMqttPublishCallback)
# CostTicker, TickPayload, run_tick_loop — already imported
```

**Test class structure pattern** (from `TestRunTickLoop` lines 145-156):
```python
class TestRunTickLoop:
    async def test_tick_loop_stops_on_event(self):
        t = CostTicker(session_id="loop-test-session")
        stop_event = asyncio.Event()
        stop_event.set()
        await run_tick_loop([t], stop_event)
```

All 4 new classes follow the same pattern: `class TestXxx:` with `async def test_*(self)` methods using `asyncio.Event`, direct ticker manipulation (`_last_tick_time -= N`), and mock callables via `captured: list[...]`. No `@pytest.mark.asyncio` needed (`asyncio_mode = "auto"` in pyproject.toml:97).

**4 new classes to append at end of file:**

1. `TestMqttPublishCallback` — covers lines 165-170 (MQTT callback path + failure swallow)
2. `TestLedgerCallback` — covers lines 174-177 (ledger callback path + failure swallow)
3. `TestProperties` — covers lines 187, 191 (`active_s` and `idle_s` properties)
4. `TestRunTickLoopBody` — covers lines 205-216 (loop iteration + all-idle + exception swallow)

See RESEARCH.md `cost.py Coverage Plan` section for exact test bodies — these are concrete and ready to paste.

---

### `tests/voice/test_call.py` — extend with deprecation tests (HYG-02)

**Analog:** `tests/voice/test_call.py:97-171` (`TestTryTwilioCall` class — monkeypatch + fake module injection pattern)

**Key patterns from existing tests:**
```python
# Pattern: monkeypatch env vars (from test_call.py:32-38)
def test_no_twilio_env_gives_dashboard_ring(self, tmp_path, monkeypatch):
    monkeypatch.delenv("TWILIO_SID", raising=False)
    monkeypatch.delenv("TWILIO_TOKEN", raising=False)

# Pattern: pytest.warns for DeprecationWarning (NEW — not yet in codebase)
with pytest.warns(DeprecationWarning, match="TWILIO_TOKEN"):
    result = _get_twilio_auth_token()
```

**Existing TWILIO_TOKEN refs to update in test_call.py** (lines 90, 119, 133, 162, 178):
```python
# BEFORE:
monkeypatch.setenv("TWILIO_TOKEN", "fake_token")
# AFTER:
monkeypatch.setenv("TWILIO_AUTH_TOKEN", "fake_token")
```

**3 new tests to add** (new class `TestTwilioEnvMigration`):
1. `test_auth_token_reads_new_var` — `TWILIO_AUTH_TOKEN` wins, no warning
2. `test_legacy_token_emits_deprecation` — `TWILIO_TOKEN` triggers `DeprecationWarning`
3. `test_deprecation_warning_emitted_once` — second call does not re-emit

---

### NEW `tests/voice/conftest.py` — deprecation cache reset fixture

**Analog:** `tests/sensors/conftest.py:71-112` (autouse fixture pattern using `pytest.fixture()`)

```python
"""Shared fixtures for voice tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_twilio_deprecation_cache():
    """Clear the once-per-process DeprecationWarning cache before each test.

    Without this, the first test that hits the legacy TWILIO_TOKEN path
    sets _DEPRECATION_EMITTED and all subsequent tests in the session skip
    the warning — making deprecation tests order-dependent.
    """
    from skyherd.voice._twilio_env import _DEPRECATION_EMITTED
    _DEPRECATION_EMITTED.clear()
    yield
    _DEPRECATION_EMITTED.clear()
```

---

## Shared Patterns

### Module-Level Logger (universal — all target files already have it)

**Source:** `src/skyherd/agents/cost.py:26` (representative; 45 modules share this pattern)

```python
import logging

logger = logging.getLogger(__name__)
```

**Apply to:** All files in the silent-except sweep. Verify with `grep "logger = logging.getLogger" <file>` before editing — every target file already has this. No new logger instances needed.

### BLE001 noqa Comment with Rationale

**Source:** `src/skyherd/mcp/rancher_mcp.py:92-94`

```python
except Exception as exc:  # noqa: BLE001
    # <one sentence enumerating real exception types expected here>
    logger.warning("...")
```

**Apply to:** Every broad-`Exception` catch (Category 2 sites). The `# noqa: BLE001` comment is the project's documented escape valve for intentional broad catches — do not remove it.

### caplog Pattern for Testing New Warning Sites

**Source:** pytest built-in; project usage pattern from `tests/sensors/` suite.

```python
def test_bus_close_logs_warning_on_failure(caplog, monkeypatch):
    import logging
    caplog.set_level(logging.WARNING, logger="skyherd.sensors.bus")
    # ... mock the failing resource ...
    await bus._close_client()
    assert "aiomqtt client close failed" in caplog.text
```

**Apply to:** Every Category 2 (broad-except → WARNING) new site. One caplog test per WARNING-level logger.warning addition to prevent the coverage regression described in RESEARCH.md `Coverage Math`.

### pytest.warns Pattern for DeprecationWarning

**Source:** pytest docs; new to this phase.

```python
with pytest.warns(DeprecationWarning, match="TWILIO_TOKEN"):
    result = _get_twilio_auth_token()
```

**Apply to:** `tests/voice/test_call.py::TestTwilioEnvMigration` new tests.

---

## No Analog Found

All files have a close analog. No new-pattern files without codebase precedent.

| File | Reason Covered |
|------|----------------|
| `src/skyherd/voice/_twilio_env.py` | Structurally mirrors `cost.py` (small utility module); `warnings.warn` pattern is stdlib-documented in RESEARCH.md |
| `tests/voice/conftest.py` | Mirrors `tests/sensors/conftest.py` autouse fixture pattern exactly |

---

## Phase 1 Coordination Notes

The following files are shared surface between Phase 1 and Phase 3:

| File | Phase 1 lines | Phase 3 lines | Conflict risk |
|------|---------------|---------------|---------------|
| `src/skyherd/scenarios/base.py` | ~160-200, 234-337 | 309-312 | None — non-overlapping |
| `src/skyherd/agents/managed.py` | restructures file | pyright errors 388 | **DEFER Phase 3 pyright fixes here to Phase 1** |
| `src/skyherd/agents/session.py` | restructures file | pyright errors 415-422 | **DEFER Phase 3 pyright fixes here to Phase 1** |

Phase 3 planner must explicitly scope HYG-04 as "drone files only" (Pass A) and defer `managed.py` + `session.py` pyright errors to Phase 1's acceptance criteria.

---

## Metadata

**Analog search scope:** `src/skyherd/`, `tests/`
**Files scanned:** 18 (all target files + their existing test counterparts)
**Pattern extraction date:** 2026-04-22
