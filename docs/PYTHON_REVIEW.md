# PYTHON_REVIEW.md — SkyHerd Engine

**Scope**: `src/skyherd/**/*.py` + `tests/**/*.py`
**Reviewer**: python-specialized (parallel to general code-reviewer)
**Date**: 2026-04-21
**Verdict**: Acceptable with fixes. See one-paragraph summary at bottom.

---

## Severity counts

| Severity | Count |
|----------|-------|
| CRITICAL | 2     |
| HIGH     | 9     |
| MEDIUM   | 14    |
| LOW      | 11    |

Approval: **Block** — 2 CRITICAL + 9 HIGH require fixes before demo day.

---

## CRITICAL

### C-01 — `hash()` used for session-cache identity (non-deterministic across runs)

**File**: `src/skyherd/agents/session.py:245`

```python
if session.system_prompt_cached_hash is None:
    sp_path = session.agent_spec.system_prompt_template_path
    sp_text = _load_text(sp_path)
    session.system_prompt_cached_hash = str(hash(sp_text))
```

**Issue**: Python's built-in `hash()` for strings is randomized per-process via `PYTHONHASHSEED`. Two different processes hashing the same system prompt will get different hashes. A checkpoint written by run #1 and restored in run #2 will have a "different" cached hash even when the underlying prompt text is identical — defeating the whole point of a cache fingerprint.

For an attestation-adjacent system that claims to verify "cached prompt identity," this is a **silent correctness bug**.

**Fix**:
```python
import hashlib
session.system_prompt_cached_hash = hashlib.sha256(sp_text.encode()).hexdigest()
```

---

### C-02 — `tempfile.mktemp()` deprecated and race-prone

**File**: `src/skyherd/vision/renderer.py:130,208,288`

```python
out_path = Path(tempfile.mktemp(suffix=".png"))
```

**Issue**: `tempfile.mktemp` has been deprecated since Python 2 for security reasons (TOCTOU race — another process can create the file at that path between `mktemp()` returning and you opening it). Python docs actively discourage its use. `ruff`'s `S306` would catch this if enabled.

**Fix**:
```python
import tempfile
# Use NamedTemporaryFile or mkstemp (returns an fd, no race)
fd, path_str = tempfile.mkstemp(suffix=".png")
os.close(fd)  # we only want the path; we'll re-open via PIL
out_path = Path(path_str)
```
Or better: require callers to supply `out_path` and push the temp-file concern into tests/fixtures, since renderer is usually called with a concrete path anyway.

---

## HIGH

### H-01 — Cross-module access to private attributes (`_sessions`, `_tickers`, `_tool_call_log`, `_conn`, `_value`)

**Files**:
- `src/skyherd/server/app.py:155` — `sem._value == 0`
- `src/skyherd/server/app.py:260` — `mesh._sessions.items()`
- `src/skyherd/server/events.py:352-353` — `self._mesh._sessions`, `self._mesh._session_manager._tickers`, `ticker._current_state`, `ticker._cumulative_tokens_in`, `ticker._cumulative_tokens_out`
- `src/skyherd/scenarios/base.py:139,148,280,306` — `mesh._tool_call_log`, `ledger._conn`
- `src/skyherd/scenarios/water_drop.py:108` — `mesh._tool_call_log`
- `src/skyherd/scenarios/cross_ranch_coyote.py:287,302-303` — `ledger._conn`, `cross._tool_call_log`

**Issue**:
1. `asyncio.Semaphore._value` is **undocumented CPython internals**. In Python 3.12+ semaphore internals changed, and in 3.14+ they may change again. This will silently break. Use the public API: try `sem.locked()` or a bounded semaphore pattern.
2. `_sessions`, `_tool_call_log`, `_tickers`, `_conn` are all Pythonically private. Add public properties or methods (`iter_sessions()`, `tool_calls_for(ranch)`, `close()`). Consumer modules lock producers into a specific internal shape.

**Fix** for semaphore:
```python
# Instead of sem._value == 0, use try_acquire pattern
if sem.locked():
    return Response(content="Too many SSE connections", status_code=429, ...)
```
Or use a `Semaphore(maxsize)` where you track active counts via a separate `Counter()`.

**Fix** for private attrs: add public accessors.
```python
class AgentMesh:
    def sessions(self) -> Iterator[tuple[str, Session]]:
        yield from self._sessions.items()
```

---

### H-02 — `asyncio.create_task` without storing reference (garbage-collection risk)

**File**: `src/skyherd/agents/mesh.py:231`

```python
for session in woken:
    handler_fn = self._handlers.get(session.agent_name)
    if handler_fn:
        asyncio.create_task(
            self._run_handler(session, event, handler_fn),
            name=f"handler-{session.agent_name}",
        )
```

**Issue**: Per the Python docs and [PEP-458 / asyncio docs](https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task):

> Important: Save a reference to the result of this function, to avoid a task disappearing mid-execution. The event loop only keeps weak references to tasks.

Your task can be GC'd mid-execution. The handler may never finish, and errors inside it will be silently dropped.

**Fix**:
```python
self._inflight_handlers: set[asyncio.Task[None]] = set()
# ...
task = asyncio.create_task(
    self._run_handler(session, event, handler_fn),
    name=f"handler-{session.agent_name}",
)
self._inflight_handlers.add(task)
task.add_done_callback(self._inflight_handlers.discard)
```

---

### H-03 — `except (ImportError, AttributeError, Exception)` — redundant and misleading

**Files**:
- `src/skyherd/attest/signer.py:114` — `except (InvalidSignature, ValueError, TypeError, Exception)` in **signature verification** (security-critical)
- `src/skyherd/edge/camera.py:160` — `except (PiCameraUnavailable, Exception)`
- `src/skyherd/edge/detector.py:113` — `except (ImportError, Exception)`
- `src/skyherd/mcp/rancher_mcp.py:94` — `except (ImportError, AttributeError, Exception)`

**Issue**: `Exception` already subsumes all the specific exceptions listed. This is either (a) dead code showing the author didn't understand the class hierarchy, or (b) a failed attempt at narrow catching that actually catches everything including `KeyboardInterrupt`-adjacent issues. Importantly in `signer.py:verify`, catching `Exception` means a programming bug (e.g., `MemoryError`, `RuntimeError` from the `cryptography` lib) returns `False` rather than propagating — that's fail-closed for signatures (safe) but still hides bugs.

**Fix**:
```python
# signer.py
except (InvalidSignature, ValueError, TypeError):
    return False
# Let Exception propagate — memory errors and crypto lib bugs should crash loud.
```

---

### H-04 — Opaque callback types (`Any | None` for callables)

**Files**:
- `src/skyherd/agents/mesh.py:108-109` — `mqtt_publish_callback: Any | None`
- `src/skyherd/agents/session.py:181-182` — same
- `src/skyherd/agents/cost.py:103-104` — same (comment shows intended type)
- `src/skyherd/agents/mesh_neighbor.py:99` — `publish_callback: Any | None`

**Issue**: Using `Any` for callbacks means:
- pyright/mypy can't verify the SessionManager is invoked with the right signature
- IDE autocomplete is useless inside the callback path
- The comment `# Callable[[TickPayload], Awaitable[None]]` admits the author already knows the correct type

**Fix**:
```python
from collections.abc import Awaitable, Callable

MqttPublishCallback = Callable[[str, bytes], Awaitable[None]]
LedgerCallback = Callable[["TickPayload"], Awaitable[None]]

@dataclass
class CostTicker:
    ledger_callback: LedgerCallback | None = None
    mqtt_publish_callback: MqttPublishCallback | None = None
```

---

### H-05 — `asyncio.get_event_loop()` deprecated in running-loop context

**File**: `src/skyherd/edge/watcher.py:415`

```python
def _install_signal_handlers(self) -> None:
    loop = asyncio.get_event_loop()
    # ...
```

**Issue**: Since Python 3.10, calling `asyncio.get_event_loop()` outside a running loop emits a DeprecationWarning; in 3.12+ with no running loop it raises. In 3.14 the behavior will be stricter still. Since this is called from `run()` which is async, use `get_running_loop()`.

**Fix**:
```python
def _install_signal_handlers(self) -> None:
    loop = asyncio.get_running_loop()
    # ...
```

---

### H-06 — MQTT client re-connected on every publish (performance + connection churn)

**File**: `src/skyherd/sensors/bus.py:121-135`, `src/skyherd/edge/watcher.py:266,357,407`

```python
async def publish(self, topic: str, payload: dict[str, Any], ...):
    raw = _canonical_json(payload)
    async with aiomqtt.Client(hostname=self._host, port=self._port) as client:
        await client.publish(topic, payload=raw.encode(), qos=qos)
```

**Issue**: Every single publish opens a fresh TCP + MQTT CONNECT handshake, publishes one message, and disconnects. For a 100-sensor ranch at 1 Hz cadence, that's 100 CONNECTs/sec — order of magnitude worse than pooled/long-lived connections. Some MQTT brokers will rate-limit or disconnect this. `aiomqtt.Client` is explicitly designed to be used as a long-lived async context manager.

**Fix**:
```python
class SensorBus:
    def __init__(self):
        ...
        self._client: aiomqtt.Client | None = None
        self._connect_lock = asyncio.Lock()

    async def _ensure_connected(self) -> aiomqtt.Client:
        async with self._connect_lock:
            if self._client is None:
                self._client = aiomqtt.Client(hostname=self._host, port=self._port)
                await self._client.__aenter__()
            return self._client

    async def publish(self, topic, payload, qos=0, ledger=None):
        client = await self._ensure_connected()
        raw = _canonical_json(payload)
        await client.publish(topic, payload=raw.encode(), qos=qos)
```

---

### H-07 — Quadratic per-pixel Python loops in numpy code

**File**: `src/skyherd/vision/renderer.py:139-144,234-237`

```python
# Gradient background — draw row by row
for y in range(_TROUGH_H):         # 480 iterations
    t = y / _TROUGH_H
    r = int(_BG_TOP[0] * (1 - t) + _BG_BOT[0] * t)
    ...

# Gaussian blob — per-pixel splat
for py in range(max(0, fy - 20), min(_THERMAL_H, fy + 21)):   # up to 41
    for px in range(max(0, fx - 20), min(_THERMAL_W, fx + 21)):  # up to 41
        d2 = (px - fx) ** 2 + (py - fy) ** 2
        arr[py, px] += heat * math.exp(-d2 / (2.0 * sigma_px**2))
```

**Issue**: Both patterns are classic "Python loop where numpy vectorization exists." The thermal blob is called once per cow/predator, so with 12 cows and 2 predators that's ~14 × 1681 ~= 23k Python-level iterations per frame. A vectorized version is ~100× faster.

**Fix** (thermal blob):
```python
y0, y1 = max(0, fy - 20), min(_THERMAL_H, fy + 21)
x0, x1 = max(0, fx - 20), min(_THERMAL_W, fx + 21)
yy, xx = np.mgrid[y0:y1, x0:x1]
d2 = (xx - fx) ** 2 + (yy - fy) ** 2
arr[y0:y1, x0:x1] += heat * np.exp(-d2 / (2.0 * sigma_px ** 2))
```

**Fix** (gradient background): build the array with numpy and convert to PIL once.
```python
ts = np.linspace(0, 1, _TROUGH_H)[:, None]
rows = (np.array(_BG_TOP) * (1 - ts) + np.array(_BG_BOT) * ts).astype(np.uint8)
bg = np.tile(rows[:, None, :], (1, _TROUGH_W, 1))
img = Image.fromarray(bg, mode="RGB")
```

---

### H-08 — Silent broken backend factory (`mavic` and `f3` never register)

**File**: `src/skyherd/drone/interface.py:140-153`

```python
if backend_name not in _REGISTRY:
    if backend_name == "sitl":
        from skyherd.drone.sitl import SitlBackend
        _register("sitl", SitlBackend)
    elif backend_name == "stub":
        from skyherd.drone.stub import StubBackend
        _register("stub", StubBackend)
    else:
        raise DroneError(...)
```

**Issue**: `MavicBackend` and `F3InavBackend` exist in the package but the factory only knows about `"sitl"` and `"stub"`. Setting `DRONE_BACKEND=mavic` raises `DroneError("Unknown drone backend 'mavic'...")`. In `hardware_only.py:_launch_drone`, this exception is caught and the code silently falls through to SITL — so the "Mavic hardware demo" actually runs on SITL and nobody notices.

**Fix**:
```python
elif backend_name == "mavic":
    from skyherd.drone.mavic import MavicBackend
    _register("mavic", MavicBackend)
elif backend_name == "f3" or backend_name == "f3_inav":
    from skyherd.drone.f3_inav import F3InavBackend
    _register(backend_name, F3InavBackend)
```

---

### H-09 — Dead code in AgentSpec (the `if False` Easter egg + immediate override)

**File**: `src/skyherd/agents/herd_health_watcher.py:39-60`

```python
HERD_HEALTH_WATCHER_SPEC = AgentSpec(
    name="HerdHealthWatcher",
    ...
    skills=[
        ...,
        _skill("cattle-behavior/disease/pinkeye.md") if False else "",  # loaded if exists
        _skill("ranch-ops/human-in-loop-etiquette.md"),
    ],
    ...
)

# Override skills with all that actually exist
HERD_HEALTH_WATCHER_SPEC.skills = [
    _skill("cattle-behavior/feeding-patterns.md"),
    ...
]
```

**Issue**: The `if False else ""` conditional always evaluates to `""`, adding an empty string to the skills list. Then three lines later the whole `.skills` list is *re-assigned*, throwing away everything in the dataclass constructor. This is two layers of dead code stacked on top of each other — both the ternary and the initial `skills=[...]` payload.

**Fix**: delete the `if False` branch and the initial `skills=[...]`. Build the list once, correctly, with actual disk-existence checks.
```python
SKILL_CANDIDATES = [
    "cattle-behavior/feeding-patterns.md",
    ...,
]
SKILLS = [_skill(s) for s in SKILL_CANDIDATES if Path(_skill(s)).exists()]
HERD_HEALTH_WATCHER_SPEC = AgentSpec(..., skills=SKILLS, ...)
```

---

## MEDIUM

### M-01 — `print()` in non-CLI library code

**Files**:
- `src/skyherd/vision/pipeline.py:35` — `print(result.detections)` inside an example/docstring demo function but still executable.
- `src/skyherd/world/cli.py:48,52` — CLI, acceptable.

**Fix** for pipeline.py:35: wrap in `if __name__ == "__main__":` or remove — library code shouldn't print to stdout.

---

### M-02 — Dead expression statement

**File**: `src/skyherd/vision/renderer.py:301`

```python
# Build supervision Detections from results
len(detections)
w, h = img.size
```

The `len(detections)` call has no effect — result is discarded. Remove the line or add `_ = len(detections)` with an intent comment (but really, just remove).

---

### M-03 — Empty `if TYPE_CHECKING: pass`

**File**: `src/skyherd/agents/session.py:40-41`

```python
if TYPE_CHECKING:
    pass
```

Dead code — imports were presumably removed. Delete the whole block.

---

### M-04 — Function-local imports where module-level would work

**Files**: 47+ instances. Notable offenders:
- `src/skyherd/mcp/drone_mcp.py:63` — `import math` inside an async tool handler (hot path)
- `src/skyherd/demo/hardware_only.py` — 16 in-function imports
- `src/skyherd/drone/sitl.py`, `drone/f3_inav.py`, `drone/mavic.py` — some are justified (lazy-loading heavy SDKs like `mavsdk`, `websockets`, `supervision`, `PytorchWildlife`), others aren't.

**Rule of thumb**: in-function import is correct when (a) optional heavy dep is gated by env/config, or (b) breaking a genuine circular. Otherwise move to module level.

---

### M-05 — `UUID` truncation to 8 hex chars

**Files**: `src/skyherd/mcp/drone_mcp.py:50`, `src/skyherd/mcp/rancher_mcp.py:134,210`, `src/skyherd/voice/call.py:112`

```python
mission_id = str(uuid.uuid4())[:8]
```

With 8 hex chars (32 bits of randomness) and birthday-collision math, you'll see a collision at ~65k IDs. For attestation-anchored records across multiple ranches, prefer full UUIDs or at least 12-16 chars. Also `str(uuid.uuid4())` includes hyphens — `str(uuid.uuid4())[:8]` will sometimes chop part of a hyphen. Use `uuid.uuid4().hex[:12]` instead.

---

### M-06 — Ambiguous `Exception` swallowing (16 files, 57 total occurrences)

Every `# noqa: BLE001` marker is a "we know this is bad but it's a demo" flag. That's fine for a hackathon, but for production hardening:
- Distinguish "network call that may fail" (catch `OSError, aiomqtt.MqttError`) from "logic path that should never fail" (let it propagate).
- Log the full traceback with `logger.exception()` rather than `logger.warning("%s", exc)` — you lose the stack otherwise.

**Current worst offenders**:
- `src/skyherd/demo/hardware_only.py` — 11 occurrences
- `src/skyherd/drone/f3_inav.py` — 8
- `src/skyherd/drone/sitl.py` — 8

---

### M-07 — `logger.error("%s: %s", exc)` without `exc_info`

**Files**: `src/skyherd/demo/hardware_only.py` uses `exc_info=True` correctly once (line 134), but most other `logger.error` / `logger.warning` calls drop the traceback. For a system that claims attestation-grade logs, stacks matter.

**Fix**: prefer `logger.exception("...")` inside `except` blocks.

---

### M-08 — Missing `pytest.raises(match=...)` (44 of 46 usages)

**Files**: `tests/drone/test_safety.py`, `tests/drone/test_mavic.py`, `tests/attest/test_ledger.py`, etc.

```python
with pytest.raises(GeofenceViolation):  # what message?
    checker.check_waypoint(wp)
```

Without `match=`, the test passes for *any* `GeofenceViolation` — including one raised for a different reason than you intended. For 10 loc of test setup, adding `match=r"outside the geofence"` catches the regression where the error message drifts.

---

### M-09 — Weak test assertions ("no error" pattern)

**File**: `tests/obs/test_metrics.py:16-50`

```python
def test_record_agent_wake_no_error():
    record_agent_wake("FenceLineDispatcher")
    record_agent_wake("HerdHealthWatcher")
```

No assertion — the test passes as long as the function doesn't raise. Should call `metrics_available()` + fetch the counter value.

---

### M-10 — Inconsistent `model_config = {...}` vs Pydantic `ConfigDict`

**Files**: `src/skyherd/world/world.py:34`, `src/skyherd/world/cattle.py:51`, `src/skyherd/world/predators.py:64`

```python
class WorldSnapshot(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
```

Pydantic v2 idiomatic form:
```python
from pydantic import ConfigDict
model_config = ConfigDict(arbitrary_types_allowed=True)
```

`ConfigDict` is a `TypedDict` so mypy/pyright verify the keys. The dict-literal form does not.

---

### M-11 — `re.Pattern` used without generic parameter

**File**: `src/skyherd/voice/wes.py:138`

```python
_JARGON_SUBS: list[tuple[re.Pattern, str]] = [...]
```

In 3.11+, `re.Pattern[str]` is the fully-specified form. `list[tuple[re.Pattern[str], str]]` gives you index-hint information.

---

### M-12 — `asyncio.Queue` consumers without explicit `task_done()`

**File**: `src/skyherd/agents/mesh_neighbor.py:456-463`

```python
async def _event_router_loop(self) -> None:
    while True:
        topic, payload = await self._event_bus.get()
        to_ranch = payload.get("to_ranch", "")
        listener = self._listeners.get(to_ranch)
        if listener is not None:
            await listener.on_neighbor_event(topic, payload)
        # missing: self._event_bus.task_done()
```

Without `task_done()`, `queue.join()` never returns. Fine for now (no `.join()` caller), but tests that want to drain the bus deterministically will have no clean way.

---

### M-13 — Test file imports inside test functions

**File**: `tests/obs/test_metrics.py` (every test), `tests/server/test_events.py` (mostly module-level)

```python
def test_metrics_available_flag():
    from skyherd.obs.metrics import metrics_available   # imported here
    result = metrics_available()
```

Acceptable if you're testing import side effects. Otherwise noisy and slows down collection. Prefer module-level.

---

### M-14 — Pydantic `WesMessage.context: dict[str, Any] = {}`  — mutable default

**File**: `src/skyherd/voice/wes.py:31`

```python
class WesMessage(BaseModel):
    context: dict[str, Any] = {}
```

Pydantic v2 deep-copies default model values, so this is safe at runtime — but it still violates the usual Python idiom and confuses readers. Prefer `Field(default_factory=dict)` for consistency.

---

## LOW

### L-01 — `_DEFAULT_SKILLS_DIR = Path(__file__).resolve().parents[4]` (brittle path arithmetic)

**Files**: `src/skyherd/voice/wes.py:23`, `src/skyherd/scenarios/base.py:36`, `src/skyherd/demo/hardware_only.py:55`, `src/skyherd/drone/safety.py:123`, `src/skyherd/server/app.py:52`

Counting parent directories is brittle — if someone moves the file one level deeper the whole stack breaks silently. Prefer `importlib.resources` for package data or an env var / config.

### L-02 — `datetime.now(tz=UTC)` vs `datetime.now(UTC)`

Both work; mixing them (`datetime.now(tz=UTC)` in `scenarios/base.py` vs `datetime.now(UTC)` in `voice/call.py`) is stylistic inconsistency. Pick one.

### L-03 — `int(ts)` for file naming loses sub-second resolution

**Files**: `src/skyherd/drone/mavic.py:369`, `drone/f3_inav.py:334`, `drone/sitl.py:*`, `edge/watcher.py:*`

Two events in the same second collide. Use `int(ts * 1000)` or an ISO timestamp.

### L-04 — Docstring/raise misalignment

**File**: `src/skyherd/attest/signer.py:103-115` — docstring says "Never raises" but the catch-all `except (..., Exception)` proves the author isn't sure. Trim the claim or narrow the catch.

### L-05 — `ClassVar` missing on registry dicts

**File**: `src/skyherd/edge/detector.py:94`

```python
class MegaDetectorHead(Detector):
    _CATEGORIES = {1: "animal", 2: "person", 3: "vehicle"}
```

Should be `_CATEGORIES: ClassVar[dict[int, str]] = {...}` so pyright doesn't flag it as an instance-default.

### L-06 — `Optional[X]` vs `X | None` — pick one

Project uses `X | None` (modern, good), but some edge cases mix. Grep reveals consistent `| None` which is correct — no action needed, just confirming the pattern is held.

### L-07 — `try: subprocess.run(...); except CalledProcessError as exc: raise RuntimeError(f"...{exc.stderr.decode()[:200]}")`

**Files**: `src/skyherd/voice/tts.py:118,140`

Truncating stderr to 200 chars loses diagnostic info. Consider logging the full stderr and only user-facing-truncating.

### L-08 — `asyncio.Event` + `while not self._stop_event.is_set(): await asyncio.sleep(INTERVAL)`

**Files**: `src/skyherd/server/events.py`, `src/skyherd/edge/watcher.py`, `src/skyherd/agents/cost.py`

Pattern: "sleep then check cancel" means shutdown waits up to `INTERVAL` seconds. Prefer `asyncio.wait_for(self._stop_event.wait(), timeout=INTERVAL)` so shutdown is instant:

```python
try:
    await asyncio.wait_for(self._stop_event.wait(), timeout=INTERVAL)
    break  # stop_event was set
except asyncio.TimeoutError:
    pass  # interval elapsed; continue loop
```

### L-09 — `list[tuple[re.Pattern, str]]` — type could use `TypeAlias`

```python
JargonRule: TypeAlias = tuple[re.Pattern[str], str]
_JARGON_SUBS: list[JargonRule] = [...]
```

### L-10 — `str(message.topic)` (aiomqtt topics are `Topic` objects)

**File**: `src/skyherd/sensors/bus.py:168`

Works but `message.topic.value` is the documented aiomqtt API. Minor — would surface in pyright strict.

### L-11 — Commented-out / inline comments with dashes that could be docstring promotion

**Files**: Multiple — `src/skyherd/obs/metrics.py`, `src/skyherd/voice/tts.py`, etc. have section dividers like `# -----`. Harmless; personal preference. Flagged because some are 80 chars and PEP 8 prefers 79 at most unless `line-length=100` is explicit (which it is for this project).

---

## Top 10 Findings (Triage Order)

| # | Severity | ID | Headline | File |
|---|----------|-----|----------|------|
| 1 | CRITICAL | C-01 | `hash()` non-deterministic for session cache fingerprint | `agents/session.py:245` |
| 2 | CRITICAL | C-02 | `tempfile.mktemp` deprecated + TOCTOU-prone | `vision/renderer.py:130,208,288` |
| 3 | HIGH     | H-08 | Silent broken backend factory — `mavic`/`f3` never register | `drone/interface.py:140-153` |
| 4 | HIGH     | H-01 | Cross-module private-attribute access (incl. `asyncio.Semaphore._value`) | `server/app.py`, `server/events.py`, `scenarios/*` |
| 5 | HIGH     | H-02 | `asyncio.create_task` without reference → GC risk | `agents/mesh.py:231` |
| 6 | HIGH     | H-06 | `aiomqtt.Client` reconnected per-publish | `sensors/bus.py`, `edge/watcher.py` |
| 7 | HIGH     | H-03 | `except (..., Exception)` redundant catch chains | `attest/signer.py:114` + 3 others |
| 8 | HIGH     | H-09 | Dead-code `if False` skill + immediate override | `agents/herd_health_watcher.py:39-60` |
| 9 | HIGH     | H-04 | Callbacks typed as `Any` where `Callable[...]` fits | `agents/mesh.py`, `cost.py`, `session.py`, `mesh_neighbor.py` |
| 10 | HIGH    | H-07 | Pure-Python per-pixel loops in numpy rendering hot path | `vision/renderer.py:139-144,234-237` |

---

## Verdict

**Acceptable, not idiomatic.** The code reads as a well-organized hackathon codebase hardening into production: consistent use of `Pathlib`, `from __future__ import annotations`, async/await patterns, Pydantic v2 models, parameterized SQL, `hmac.compare_digest` for attestation equality, `yaml.safe_load` everywhere, no `pickle` on untrusted input — the security foundation is solid. Where it falls short is in the seams: callbacks typed as `Any`, cross-module reaches into private attributes (including undocumented CPython internals like `Semaphore._value`), a silently broken drone-backend factory, `hash()` used for a fingerprint that ought to be SHA-256, and three independent `tempfile.mktemp` TOCTOU bugs. Async discipline is mostly right (no `time.sleep`, proper `CancelledError` handling, `TaskGroup`-compatible shutdown) but one `create_task` leak and one `get_event_loop()` call risk silent failures on Python 3.12+. Tests cover the safety-critical guard classes thoroughly but rely on weak `pytest.raises(X)` without `match=` and several "no error" assertions. None of this blocks the demo, but before the next funding milestone the CRITICAL and HIGH items need sweeping — especially C-01 and H-08, which silently degrade production behavior without any test signal.
