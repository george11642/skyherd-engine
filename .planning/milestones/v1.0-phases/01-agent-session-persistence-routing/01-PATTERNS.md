# Phase 1: Agent Session Persistence & Routing - Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 7 (4 modified source files + 5 extended test files — counted as 7 distinct edit sites)
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/skyherd/scenarios/base.py` (`_DemoMesh.__init__` + `dispatch`) | service (session orchestrator) | event-driven | `src/skyherd/agents/mesh.py` (`AgentMesh.__init__` + `_run_handler`) | exact |
| `src/skyherd/scenarios/base.py` (`_run_async` `_registry` dict) | config / routing | event-driven | `src/skyherd/agents/mesh.py` (`_AGENT_REGISTRY`) | exact |
| `src/skyherd/scenarios/base.py` (`_route_event` routing table) | utility (dispatcher) | event-driven | `src/skyherd/agents/mesh.py` (`_mqtt_loop` topic → session routing) | role-match |
| `tests/scenarios/test_coyote.py` (new `test_creates_at_most_five_sessions`) | test | request-response | `tests/agents/test_cost.py::TestCostTicker::test_idle_after_active_stops_accrual` (advance-clock / monkeypatch pattern) | role-match |
| `tests/scenarios/test_base.py` (new `_DemoMesh` registry + routing assertions) | test | request-response | `tests/scenarios/test_base.py` existing `TestScenarioResult` class | exact |
| `tests/scenarios/test_rustling.py` (new `test_predator_pattern_learner_dispatched`) | test | event-driven | `tests/scenarios/test_rustling.py::TestRustlingScenarioIntegration::test_full_run_has_launch_drone` | exact |
| `tests/scenarios/test_run_all.py` (new `test_every_agent_dispatched_at_least_once`) | test | batch | `tests/scenarios/test_run_all.py::TestRunAll::test_run_all_each_has_tool_calls` | exact |
| `tests/agents/test_cost.py` (new idle-pause aggregator test) | test | request-response | `tests/agents/test_cost.py::TestCostTicker::test_idle_after_active_stops_accrual` | exact |
| `tests/agents/test_session.py` (new checkpoint round-trip test) | test | request-response | `tests/agents/test_session.py::TestSessionLifecycle::test_wake_appends_event` | role-match |

---

## Pattern Assignments

### `src/skyherd/scenarios/base.py` — `_DemoMesh` refactor (MA-01, MA-02, MA-03)

**Analog:** `src/skyherd/agents/mesh.py`

**Imports pattern — what `_DemoMesh` gains** (mesh.py lines 23-52):
```python
from skyherd.agents.calving_watch import CALVING_WATCH_SPEC
from skyherd.agents.calving_watch import handler as calving_handler
from skyherd.agents.cost import run_tick_loop
from skyherd.agents.fenceline_dispatcher import FENCELINE_DISPATCHER_SPEC
from skyherd.agents.fenceline_dispatcher import handler as fenceline_handler
from skyherd.agents.grazing_optimizer import GRAZING_OPTIMIZER_SPEC
from skyherd.agents.grazing_optimizer import handler as grazing_handler
from skyherd.agents.herd_health_watcher import HERD_HEALTH_WATCHER_SPEC
from skyherd.agents.herd_health_watcher import handler as herd_handler
from skyherd.agents.predator_pattern_learner import PREDATOR_PATTERN_LEARNER_SPEC
from skyherd.agents.predator_pattern_learner import handler as predator_handler
from skyherd.agents.session import Session, SessionManager
```

Note: `_run_async` currently imports specs locally inside the function body (base.py lines 213-221). After the fix, `_DemoMesh.__init__` must import them at construction time (or at module level). Mirror `mesh.py`'s top-level imports.

**Session registry init pattern — copy verbatim into `_DemoMesh.__init__`** (mesh.py lines 106-119):
```python
def __init__(
    self,
    mqtt_publish_callback: Any | None = None,
    ledger_callback: Any | None = None,
) -> None:
    self._session_manager = SessionManager(
        mqtt_publish_callback=mqtt_publish_callback,
        ledger_callback=ledger_callback,
    )
    self._sessions: dict[str, Session] = {}  # name → session
    self._handlers: dict[str, Any] = {}  # name → handler fn
```

**Eager session creation — copy into `_DemoMesh.__init__` after the `SessionManager` line** (mesh.py lines 126-132):
```python
async def start(self) -> None:
    for spec, handler_fn in _AGENT_REGISTRY:
        session = self._session_manager.create_session(spec)
        self._sessions[spec.name] = session
        self._handlers[spec.name] = handler_fn
        logger.info("AgentMesh: registered %s (session %s)", spec.name, session.id[:8])
```

Adaptation note: `_DemoMesh` is synchronous in `__init__`, so call `create_session` directly without `async`. `SessionManager.create_session()` is sync (session.py line 195). No `asyncio` needed for the registry setup.

**Wake/handle/sleep dispatch pattern — replaces the current `dispatch()` body** (mesh.py lines 241-253):
```python
async def _run_handler(
    self,
    session: Session,
    wake_event: dict[str, Any],
    handler_fn: Any,
) -> None:
    try:
        await handler_fn(session, wake_event, sdk_client=None)
    except Exception as exc:  # noqa: BLE001
        logger.error("handler error for %s: %s", session.agent_name, exc)
    finally:
        self._session_manager.sleep(session.id)  # idle-pause ticker
```

Adaptation for `_DemoMesh.dispatch()`: look up the existing session by name, call `self._session_manager.wake(session.id, wake_event)`, then `await handler_fn(session, wake_event, sdk_client=None)`, then `self._session_manager.sleep(session.id)` in a `finally` block. The old pattern created a fresh `SessionManager` on every call (base.py lines 177-183) — delete that entirely.

**Current buggy pattern to REPLACE** (base.py lines 169-196):
```python
# BEFORE (creates 241 SessionManager instances per coyote run — DELETE THIS):
async def dispatch(self, agent_name, wake_event, spec, handler_fn):
    from skyherd.agents.session import SessionManager
    manager = SessionManager()          # ← leak: new manager every call
    session = manager.create_session(spec)
    manager.wake(session.id, wake_event)
    calls = await handler_fn(session, wake_event, sdk_client=None)
    manager.sleep(session.id)
    ...
```

**Target pattern for `_DemoMesh.dispatch()`** (derives from mesh.py lines 241-253 + session.py lines 229-253):
```python
# AFTER (reuses session from registry — 5 total per scenario run):
async def dispatch(self, agent_name, wake_event, spec, handler_fn):
    session = self._sessions[agent_name]          # ← registry lookup
    self._session_manager.wake(session.id, wake_event)
    try:
        calls = await handler_fn(session, wake_event, sdk_client=None)
    except Exception as exc:                      # noqa: BLE001
        logger.error("handler error for %s: %s", agent_name, exc)
        calls = []
    finally:
        self._session_manager.sleep(session.id)  # idle-pause ticker

    if agent_name not in self._tool_call_log:
        self._tool_call_log[agent_name] = []
    self._tool_call_log[agent_name].extend(calls)
    ...
    return calls
```

---

### `src/skyherd/scenarios/base.py` — `_registry` dict in `_run_async` (ROUT-01)

**Analog:** `src/skyherd/agents/mesh.py` `_AGENT_REGISTRY` list (lines 56-62)

**Current `_registry` (missing PredatorPatternLearner)** (base.py lines 234-239):
```python
_registry = {
    "FenceLineDispatcher": (FENCELINE_DISPATCHER_SPEC, fenceline_handler),
    "HerdHealthWatcher":   (HERD_HEALTH_WATCHER_SPEC, herd_handler),
    "GrazingOptimizer":    (GRAZING_OPTIMIZER_SPEC, grazing_handler),
    "CalvingWatch":        (CALVING_WATCH_SPEC, calving_handler),
}
```

**Target `_registry` — add the missing entry** (mirror mesh.py lines 56-62):
```python
_registry = {
    "FenceLineDispatcher":    (FENCELINE_DISPATCHER_SPEC, fenceline_handler),
    "HerdHealthWatcher":      (HERD_HEALTH_WATCHER_SPEC, herd_handler),
    "PredatorPatternLearner": (PREDATOR_PATTERN_LEARNER_SPEC, predator_handler),  # ← NEW
    "GrazingOptimizer":       (GRAZING_OPTIMIZER_SPEC, grazing_handler),
    "CalvingWatch":           (CALVING_WATCH_SPEC, calving_handler),
}
```

After the `_DemoMesh` refactor, `_registry` is consumed at `_DemoMesh.__init__` time (as the registry for eager session creation) and by `_route_event` for dispatch. The `_run_async` function passes it to `_route_event`; if `_DemoMesh` holds it, thread via `mesh._sessions` keys instead.

---

### `src/skyherd/scenarios/base.py` — routing table in `_route_event` (ROUT-02)

**Analog:** `src/skyherd/agents/session.py::on_webhook` (lines 320-338) — topic pattern routing. The scenario uses a simpler event-type dict; keep the event-type style.

**Current routing table (missing 2 entries)** (base.py lines 326-337):
```python
routing: dict[str, list[str]] = {
    "fence.breach":          ["FenceLineDispatcher"],
    "predator.spawned":      ["FenceLineDispatcher"],
    "camera.motion":         ["HerdHealthWatcher"],
    "health.check":          ["HerdHealthWatcher"],
    "collar.activity_spike": ["CalvingWatch"],
    "calving.prelabor":      ["CalvingWatch"],
    "water.low":             ["FenceLineDispatcher", "GrazingOptimizer"],
    "weather.storm":         ["GrazingOptimizer"],
    "weekly.schedule":       ["GrazingOptimizer"],
    "storm.warning":         ["GrazingOptimizer"],
}
```

**Target routing table — add two entries** (ROUT-02):
```python
routing: dict[str, list[str]] = {
    # existing entries unchanged ...
    "thermal.anomaly":       ["FenceLineDispatcher", "PredatorPatternLearner"],  # ← NEW
    "nightly.analysis":      ["PredatorPatternLearner"],                          # ← NEW
}
```

Dispatch guard pattern — already present in `_route_event` (base.py line 341-346) — preserve:
```python
targets = routing.get(event_type, [])
for agent_name in targets:
    if agent_name in registry:          # ← guard: skip if not in registry
        spec, handler_fn = registry[agent_name]
        try:
            await mesh.dispatch(agent_name, event, spec, handler_fn)
        except Exception as exc:        # noqa: BLE001
            logger.warning("Handler error for %s: %s", agent_name, exc)
```

---

### `tests/scenarios/test_coyote.py` — new `test_creates_at_most_five_sessions` (MA-03)

**Analog:** `tests/agents/test_cost.py::TestCostTicker::test_idle_after_active_stops_accrual` (lines 97-107) — monkeypatch + advance internal state + assert numeric bound pattern.

**Monkeypatch counter pattern** (test_cost.py lines 97-107 — the advance-clock equivalent):
```python
async def test_idle_after_active_stops_accrual(self):
    t = self._ticker()
    t.set_state("active")
    t._last_tick_time -= 3600.0        # ← advance internal state
    await t.emit_tick()
    active_cost = t.cumulative_cost_usd
    t.set_state("idle")
    t._last_tick_time -= 3600.0
    await t.emit_tick()
    assert t.cumulative_cost_usd == pytest.approx(active_cost, rel=1e-6)  # ← bound assertion
```

**Adaptation for MA-03 session-count test** — use `pytest`'s `monkeypatch` fixture (not raw assignment) to match the `scenarios_snapshot` autouse fixture pattern (conftest.py lines 14-40):
```python
def test_creates_at_most_five_sessions(monkeypatch):
    from skyherd.agents import session as session_module
    orig_init = session_module.SessionManager.__init__
    count = {"n": 0}
    def _counting(self, *a, **kw):
        count["n"] += 1
        orig_init(self, *a, **kw)
    monkeypatch.setattr(session_module.SessionManager, "__init__", _counting)
    # monkeypatch auto-reverts after the test — no try/finally needed

    from skyherd.scenarios import run
    result = run("coyote", seed=42)

    assert result.outcome_passed, f"regression: {result.outcome_error}"
    assert count["n"] <= 5, (
        f"Session leak not closed: {count['n']} SessionManager instances (target: ≤5)"
    )
```

**Class placement:** Add as a new test method in `TestCoyoteScenario` (test_coyote.py line 9). Current class has 9 methods ending at line 94; new method appends at line 95+.

---

### `tests/scenarios/test_base.py` — new `_DemoMesh` registry + routing assertions (MA-02, ROUT-01, ROUT-02)

**Analog:** `tests/scenarios/test_base.py::TestScenarioResult` (lines 17-51) — field assertion pattern.

**Existing pattern to mirror** (test_base.py lines 37-51):
```python
def test_all_expected_fields_present(self) -> None:
    field_names = {f.name for f in fields(ScenarioResult)}
    expected = {"name", "seed", "duration_s", ...}
    assert expected.issubset(field_names)
```

**Adaptation for `_DemoMesh` session registry test** (MA-02):
```python
class TestDemoMesh:
    def test_demo_mesh_holds_five_sessions_keyed_by_name(self):
        from skyherd.scenarios.base import _DemoMesh
        mesh = _DemoMesh(ledger=None)
        names = {
            "FenceLineDispatcher", "HerdHealthWatcher",
            "PredatorPatternLearner", "GrazingOptimizer", "CalvingWatch",
        }
        assert hasattr(mesh, "_sessions"), "_DemoMesh needs a sessions registry"
        assert set(mesh._sessions.keys()) == names
        assert all(s.state == "idle" for s in mesh._sessions.values())

    def test_registry_includes_predator_pattern_learner(self):
        # ROUT-01: _registry in _run_async must contain the learner
        from skyherd.scenarios.base import _DemoMesh
        mesh = _DemoMesh(ledger=None)
        assert "PredatorPatternLearner" in mesh._sessions

    def test_routing_table_thermal_anomaly(self):
        # ROUT-02: thermal.anomaly → [FenceLineDispatcher, PredatorPatternLearner]
        from skyherd.scenarios.base import _route_event, _DemoMesh
        # Build a minimal mesh and fire a thermal.anomaly event
        # Assert both agents appear in _tool_call_log after dispatch
        ...

    def test_routing_table_nightly_analysis(self):
        # ROUT-02: nightly.analysis → [PredatorPatternLearner]
        ...
```

---

### `tests/scenarios/test_rustling.py` — new `test_predator_pattern_learner_dispatched` (ROUT-03)

**Analog:** `tests/scenarios/test_rustling.py::TestRustlingScenarioIntegration::test_full_run_has_launch_drone` (lines 139-145) — `result.agent_tool_calls` dict key assertion pattern.

**Existing pattern to copy from** (test_rustling.py lines 139-145):
```python
def test_full_run_has_launch_drone(self) -> None:
    result = run("rustling", seed=42)
    all_tool_calls = [call for calls in result.agent_tool_calls.values() for call in calls]
    tool_names = {c.get("tool") for c in all_tool_calls}
    assert "launch_drone" in tool_names, (
        f"Expected launch_drone (silent observation). Got: {tool_names}"
    )
```

**Adaptation for PredatorPatternLearner dispatch assertion** (ROUT-03):
```python
def test_predator_pattern_learner_dispatched_in_rustling(self) -> None:
    result = run("rustling", seed=42)
    assert "PredatorPatternLearner" in result.agent_tool_calls, (
        f"PredatorPatternLearner never dispatched. "
        f"Agents with tool calls: {list(result.agent_tool_calls)}"
    )
    learner_calls = result.agent_tool_calls["PredatorPatternLearner"]
    tool_names = {c.get("tool") for c in learner_calls}
    assert "get_thermal_history" in tool_names or "log_pattern_analysis" in tool_names, (
        f"Expected learner tool calls; got: {tool_names}"
    )
```

**Class placement:** Add inside `TestRustlingScenarioIntegration` (test_rustling.py line 123). Append after line 170.

**Pitfall (from RESEARCH.md §Pitfall 5):** Adding PredatorPatternLearner to the routing table adds 2 new tool calls to the rustling total. Any existing assertion checking a hardcoded total tool-call count will break. Audit `test_rustling.py` for such assertions before adding the routing entry — current tests check tool NAME presence, not total count, so this is safe for now.

---

### `tests/scenarios/test_run_all.py` — new `test_every_agent_dispatched_at_least_once` (ROUT-04)

**Analog:** `tests/scenarios/test_run_all.py::TestRunAll::test_run_all_each_has_tool_calls` (lines 30-34) — batch result iteration + set comprehension pattern.

**Existing pattern to extend** (test_run_all.py lines 30-34):
```python
def test_run_all_each_has_tool_calls(self) -> None:
    results = run_all(seed=42)
    for result in results:
        total_tools = sum(len(v) for v in result.agent_tool_calls.values())
        assert total_tools > 0, f"Scenario {result.name!r} produced no tool calls"
```

**Adaptation for per-agent coverage assertion** (ROUT-04):
```python
def test_every_agent_dispatched_at_least_once_across_suite(self) -> None:
    results = run_all(seed=42)
    dispatched: set[str] = set()
    for r in results:
        dispatched.update(r.agent_tool_calls.keys())
    required = {
        "FenceLineDispatcher", "HerdHealthWatcher",
        "PredatorPatternLearner", "GrazingOptimizer", "CalvingWatch",
    }
    missing = required - dispatched
    assert not missing, (
        f"Agents never dispatched anywhere in the 8-scenario suite: {missing}"
    )
```

**Class placement:** Add inside `TestRunAll` (test_run_all.py line 8). Append after line 57.

---

### `tests/agents/test_cost.py` — new idle-pause aggregator test (MA-04)

**Analog:** `tests/agents/test_cost.py::TestCostTicker::test_idle_after_active_stops_accrual` (lines 97-107) — the canonical advance-clock + assert-zero-delta pattern.

**Primary pattern to copy** (test_cost.py lines 97-107):
```python
async def test_idle_after_active_stops_accrual(self):
    t = self._ticker()
    t.set_state("active")
    t._last_tick_time -= 3600.0   # advance internal clock
    await t.emit_tick()
    active_cost = t.cumulative_cost_usd
    t.set_state("idle")
    t._last_tick_time -= 3600.0
    await t.emit_tick()
    assert t.cumulative_cost_usd == pytest.approx(active_cost, rel=1e-6)
```

**Adaptation for MA-04 multi-ticker all-idle test**:
```python
class TestRunTickLoop:
    # (existing tests at lines 145-156)
    async def test_all_sessions_idle_emits_zero_rate(self):
        # Build two tickers both in idle state
        t1 = CostTicker(session_id="s1")
        t2 = CostTicker(session_id="s2")
        t1.set_state("idle")
        t2.set_state("idle")
        # Aggregation logic mirrors server/events.py lines 347-377
        any_active = any(t._current_state == "active" for t in [t1, t2])
        all_idle = not any_active
        rate_per_hr_usd = 0.0 if all_idle else _SESSION_HOUR_RATE_USD
        assert all_idle is True
        assert rate_per_hr_usd == pytest.approx(0.0)
```

**Class placement:** Add inside `TestRunTickLoop` (test_cost.py line 145). Append after line 156.

---

### `tests/agents/test_session.py` — new checkpoint round-trip test (MA-05)

**Analog:** `tests/agents/test_session.py::TestSessionLifecycle::test_wake_appends_event` (lines 55-61) — create session → mutate → assert state pattern.

**Existing wake-append pattern to mirror** (test_session.py lines 55-61):
```python
def test_wake_appends_event(self):
    mgr = SessionManager()
    spec = _make_spec()
    session = mgr.create_session(spec)
    event = {"type": "fence.breach", "ranch_id": "ranch_a"}
    mgr.wake(session.id, event)
    assert event in session.wake_events_consumed
```

**`_make_spec` helper to reuse** (test_session.py lines 12-22):
```python
def _make_spec(name: str = "TestAgent", wake_topics: list[str] | None = None) -> AgentSpec:
    return AgentSpec(
        name=name,
        system_prompt_template_path="src/skyherd/agents/prompts/fenceline_dispatcher.md",
        wake_topics=wake_topics or ["skyherd/+/fence/+"],
        mcp_servers=["sensor_mcp"],
        skills=[],
        checkpoint_interval_s=3600,
        max_idle_s_before_checkpoint=600,
        model="claude-opus-4-7",
    )
```

**Adaptation for MA-05 checkpoint round-trip**:
```python
class TestCheckpointPersistence:
    def test_predator_pattern_learner_checkpoint_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setattr("skyherd.agents.session._RUNTIME_DIR", tmp_path)
        from skyherd.agents.session import SessionManager
        from skyherd.agents.predator_pattern_learner import PREDATOR_PATTERN_LEARNER_SPEC

        mgr = SessionManager()
        s = mgr.create_session(PREDATOR_PATTERN_LEARNER_SPEC)

        # Simulate two wake events (nightly analysis across sim-day boundary)
        mgr.wake(s.id, {"topic": "skyherd/ranch_a/thermal/cam_1", "type": "thermal.clip"})
        mgr.sleep(s.id)
        mgr.wake(s.id, {"topic": "skyherd/ranch_a/cron/nightly", "type": "nightly.analysis"})
        mgr.sleep(s.id)
        assert len(s.wake_events_consumed) == 2

        path = mgr.checkpoint(s.id)
        assert path.exists()

        # Restore into a new manager (sim-day boundary simulation)
        mgr2 = SessionManager()
        mgr2._sessions[s.id] = s   # pre-register so spec is resolvable
        restored = mgr2.restore_from_checkpoint(s.id)
        assert len(restored.wake_events_consumed) == 2
        assert restored.state == "idle"   # session.py:304 — always restore idle
```

**Class placement:** Add as a new class `TestCheckpointPersistence` in `tests/agents/test_session.py` after the existing class hierarchy.

---

## Shared Patterns

### SessionManager.wake/sleep cycle (idle-pause primitive)
**Source:** `src/skyherd/agents/session.py` lines 214-253
**Apply to:** `_DemoMesh.dispatch()` refactor (MA-01, MA-04)
```python
# sleep() — transitions to idle, pauses cost ticker
def sleep(self, session_id: str) -> Session:
    session = self._get(session_id)
    if session.state == "active":
        elapsed = time.monotonic() - session._active_start_ts
        session.run_time_active_s += elapsed
    session.state = "idle"
    if session._ticker:
        session._ticker.set_state("idle")   # ← idle-pause money shot
    return session

# wake() — transitions to active, resumes cost ticker
def wake(self, session_id: str, wake_event: dict[str, Any]) -> Session:
    session = self._get(session_id)
    session.state = "active"
    session._active_start_ts = time.monotonic()
    session.wake_events_consumed.append(wake_event)
    if session._ticker:
        session._ticker.set_state("active")
    return session
```

**Critical:** always call `sleep()` in a `finally` block so idle-pause fires even if the handler raises. This is the pattern in `mesh.py::_run_handler` lines 241-253.

### monkeypatch auto-revert fixture pattern
**Source:** `tests/scenarios/conftest.py` lines 14-40
**Apply to:** MA-03 SessionManager counter test, MA-05 `_RUNTIME_DIR` redirect
```python
@pytest.fixture(autouse=True)
def scenarios_snapshot():
    # snapshot → yield → restore
    original_values = dict(SCENARIOS)
    yield
    for k, v in original_values.items():
        SCENARIOS[k] = v
```

Use `monkeypatch.setattr(...)` (not raw attribute assignment) so pytest handles teardown automatically — mirrors the isolation discipline in `conftest.py`.

### Scenario integration test structure
**Source:** `tests/scenarios/test_rustling.py::TestRustlingScenarioIntegration` lines 123-170
**Apply to:** All new integration-level scenario test methods
```python
class TestRustlingScenarioIntegration:
    def test_full_run_passes(self) -> None:
        result = run("rustling", seed=42)
        assert result.outcome_passed, f"Rustling scenario failed: {result.outcome_error}"

    def test_full_run_has_launch_drone(self) -> None:
        result = run("rustling", seed=42)
        all_tool_calls = [call for calls in result.agent_tool_calls.values() for call in calls]
        tool_names = {c.get("tool") for c in all_tool_calls}
        assert "launch_drone" in tool_names, ...
```

Pattern: `run(name, seed=42)` → inspect `result.agent_tool_calls[agent_name]` → assert tool name presence. Never assert on total count — count changes when new agents are routed.

### `try/finally` dispatch guard
**Source:** `src/skyherd/agents/mesh.py` lines 241-253
**Apply to:** `_DemoMesh.dispatch()` refactor
```python
async def _run_handler(self, session, wake_event, handler_fn):
    try:
        await handler_fn(session, wake_event, sdk_client=None)
    except Exception as exc:      # noqa: BLE001
        logger.error("handler error for %s: %s", session.agent_name, exc)
    finally:
        self._session_manager.sleep(session.id)   # MUST be in finally
```

The `finally` guarantees `sleep()` fires even on handler exception, keeping the cost ticker paused correctly. This is the anti-pattern guard for Pitfall 3 (RESEARCH.md §Pitfall 3).

---

## No Analog Found

All files in scope have close analogs. No entries in this section.

---

## Key Pitfalls (from RESEARCH.md — concrete file references)

| Pitfall | Source to Read | Guard |
|---------|---------------|-------|
| Event type vs MQTT topic in routing dict | `src/skyherd/agents/predator_pattern_learner.py` lines 37-40 (`wake_topics` uses MQTT format) vs `base.py` lines 326-337 (uses event type strings) | Route by `event["type"]` in scenario, not topic pattern |
| `_tickers` dict bug in server/events.py line 353 | `src/skyherd/agents/session.py` — no `_tickers` attr on `SessionManager`; tickers live on `Session._ticker` | Flag for Phase 5; do NOT touch `server/events.py` in this phase |
| Counter fixture cross-test pollution | `tests/scenarios/conftest.py` lines 14-40 | Use `monkeypatch.setattr`, not raw `SessionManager.__init__ = ...` |
| `sleep()` missing after handler | `src/skyherd/agents/mesh.py` lines 248-253 | Always use `try/finally` in `dispatch()` |

---

## Metadata

**Analog search scope:** `src/skyherd/agents/`, `src/skyherd/scenarios/`, `tests/scenarios/`, `tests/agents/`
**Files scanned:** 14 (mesh.py, session.py, cost.py, base.py, predator_pattern_learner.py, test_cost.py, test_session.py, test_rustling.py, test_coyote.py, test_base.py, test_run_all.py, conftest.py, managed.py, predator_pattern_learner.py)
**Pattern extraction date:** 2026-04-22
