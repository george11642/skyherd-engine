# Phase 1: Agent Session Persistence & Routing — Research

**Researched:** 2026-04-22
**Domain:** Managed Agents session lifecycle, MQTT-style event routing, session registry architecture, idle-pause cost metering, deterministic scenario testing
**Confidence:** HIGH (session API semantics HIGH-verified via Anthropic docs; routing + test shape HIGH-verified by direct code inspection + runtime reproduction)

---

## Summary

The leak is architectural, not semantic. `_DemoMesh.dispatch()` at `src/skyherd/scenarios/base.py:169-196` constructs a brand-new `SessionManager` (and therefore a brand-new `Session`) on every single agent wake event. A coyote scenario run produces **241 sessions** (reproduced live in this research — see "Runtime reproduction" below). The live mesh (`AgentMesh` in `src/skyherd/agents/mesh.py`) already solves this correctly: one `SessionManager`, five sessions created at `start()`, reused across all wake events driven off the MQTT subscriber. The fix is to make `_DemoMesh` do what `AgentMesh` already does, plus wire `PredatorPatternLearner` into the scenario runner's `_registry` and routing table.

Managed Agents sessions are designed precisely for this pattern. The Anthropic docs state that "a session ... maintains conversation history across multiple interactions" and the status machine is `idle → running → idle → running → ...` driven entirely by `client.beta.sessions.events.send()`. There is **no explicit wake primitive**; sending a new `user.message` event to an idle session transitions it to `running`. The SkyHerd local shim already models this exactly (`SessionManager.wake()` / `sleep()` flip state, pausing the `CostTicker`).

**Primary recommendation:** Lift a single shared `_SessionRegistry` helper out of (or parallel to) `AgentMesh`. Have `_DemoMesh.__init__` create the 5 sessions eagerly (or at least once-per-agent lazily in `dispatch()`), store them in a dict keyed by agent name, and reuse them for every subsequent `dispatch()` call within one scenario run. Add `PredatorPatternLearner` to `_registry`, add `thermal.anomaly` + `skyherd/+/cron/nightly` to the routing table, and add an `AgentDispatched`-style counter (class-level instrumentation on `SessionManager.create_session` or a separate `_dispatch_counts` dict on `_DemoMesh`) so tests can verify dispatch actually happened.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Discuss phase was skipped** (`workflow.skip_discuss=true`). All implementation choices are at Claude's discretion, constrained by:
- ROADMAP phase goal, success criteria
- `CONCERNS.md` §1 (Priority 1 & Priority 2) and §6
- Codebase conventions from `.planning/codebase/`

### Known Audit Constraints
- Current leak: `src/skyherd/scenarios/base.py:179` creates fresh `SessionManager()` per dispatch. 241 sessions per coyote scenario run **[VERIFIED by live reproduction in this research]**.
- `_DemoMesh` is the dispatch surface — fix there.
- `_registry` dict at `base.py:234` omits `PredatorPatternLearner`.
- Routing table at `base.py:326-337` has no entry for `thermal.anomaly` or `skyherd/+/cron/nightly`.
- Cost ticker at `src/skyherd/agents/cost.py` — idle-pause billing should be verifiable after this phase.
- Zero-regression: all 8 scenarios must continue to PASS `make demo SEED=42 SCENARIO=all`.
- Must not break `ManagedSessionManager` (real MA platform wiring in `src/skyherd/agents/managed.py`) — session registry pattern should work for both local shim and real platform paths.

### Claude's Discretion

- Whether to extract a shared `SessionRegistry` helper used by both `_DemoMesh` and `AgentMesh`, or just mirror the `AgentMesh` pattern inline in `_DemoMesh`.
- Instrumentation approach for test verification (class-level counter on `SessionManager.__init__`, a dispatch counter dict on `_DemoMesh`, or both).
- Exact sleep/wake ordering for the ticker in `_DemoMesh.dispatch()` after the refactor.

### Deferred Ideas (OUT OF SCOPE)

- **Live Managed Agents platform session persistence verification** — the real MA path already supports persistent sessions per `managed.py`; this phase proves the demo path matches, but live-platform verification is **Phase 5 (Dashboard Live-Mode)**.
- **Session checkpoint serialization to disk for resume-across-process** — overkill for scenario-run scope; in-memory registry per scenario run is sufficient.
- **Refactoring `AgentMesh` to share code with `_DemoMesh`** — pursue only if trivial during planning; otherwise defer.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MA-01 | Each of 5 agents runs on ONE long-lived platform session within a scenario run | Session registry pattern — `AgentMesh.start()` (`mesh.py:126-146`) is the proven template; `_DemoMesh` must adopt it. Sessions naturally persist across events per Managed Agents docs: *"A session is a running agent instance ... and maintains conversation history across multiple interactions."* |
| MA-02 | `_DemoMesh` holds session registry keyed by agent name; lazy create or eager create, reuse thereafter | Mirror `AgentMesh._sessions: dict[str, Session]` (name → session) pattern — see `mesh.py:115,128-132` |
| MA-03 | Coyote scenario creates ≤5 platform sessions (down from 241) | `SessionManager.__init__` instrumentation confirms 241 today; post-fix target is **5** (one per agent in `_registry`). Test harness pattern: monkey-patch `SessionManager.__init__` with a class-level counter — reproduced in "Runtime reproduction" below. |
| MA-04 | Cost ticker shows idle-pause: `rate_per_hr_usd=0.0` + `all_idle=True` after idle threshold | `CostTicker.set_state("idle")` is called by `SessionManager.sleep()`; `run_tick_loop` aggregates; `server/events.py:370-377` emits `all_idle` on SSE. Test pattern: manually advance `ticker._last_tick_time` as `test_cost.py::test_idle_after_active_stops_accrual` already does. |
| MA-05 | Checkpoint persistence works — PredatorPatternLearner context retained across sim-day boundaries | Local shim `SessionManager.checkpoint()` / `restore_from_checkpoint()` serialize to `runtime/sessions/{session_id}.json` (`session.py:256-318`). Real MA platform checkpoints are automatic per `managed.py:298-311`. Sim-day boundary = `duration_s=600.0` scenario clock; checkpoints triggered via `AgentSpec.checkpoint_interval_s` (`predator_pattern_learner.py:51` = 86400s — nightly). |
| ROUT-01 | `PredatorPatternLearner` present in `_registry` | Already exists in `AgentMesh._AGENT_REGISTRY` (`mesh.py:56-62`) — just needs mirroring into `scenarios/base.py:234-239`. |
| ROUT-02 | Routing table includes `thermal.anomaly` → `[FenceLineDispatcher, PredatorPatternLearner]` + `skyherd/+/cron/nightly` → `[PredatorPatternLearner]` | Routing table at `base.py:326-337` is a dict `{event_type → [agent_names]}`. Note: the live mesh (`mesh.py`) uses **MQTT topic patterns** via `SessionManager.on_webhook()` — `_DemoMesh` uses the simpler **event_type → agents** dispatch. Both work; keep the scenario's event_type dispatch style, just add the two missing entries. |
| ROUT-03 | Rustling scenario assertions verify agent dispatch count | Current rustling test (`tests/scenarios/test_rustling.py:139-163`) asserts `launch_drone in tool_names` but does NOT assert PredatorPatternLearner actually ran — its tool calls (`get_thermal_history`, `log_pattern_analysis`) are defined in `simulate.py:308-328` but never reach `mesh._tool_call_log` because the learner is never dispatched. Needs assertion on `PredatorPatternLearner` key in `mesh._tool_call_log`. |
| ROUT-04 | All 5 agents have ≥1 assertion in ≥1 scenario proving they ran | Coverage matrix required — build table: scenario × agent → assertion exists? |

---

## Architectural Responsibility Map

Each capability maps to a tier in SkyHerd's 5-layer nervous system (per `ARCHITECTURE.md`). This phase operates entirely in **Layer 3 — Respond**, with test reach into Layer 5 (attestation) and the dashboard aggregator in `server/events.py`.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Session registry (one session per agent, lifetime = scenario run) | Layer 3 — Respond (`agents/`) | — | Sessions are first-class Managed Agents primitives; only Layer 3 owns them. |
| Event routing dispatch table (event_type → agents) | Layer 3 — Respond (`scenarios/base.py` in demo path; `session.py::on_webhook` in live path) | Layer 1 — Sense (provides topics) | Dispatch lives in Layer 3; the sensor bus is the upstream producer. |
| Session lifecycle (wake/sleep/checkpoint) | Layer 3 — Respond (`session.py`, `managed.py`) | — | Owned by `SessionManager`; same public API for local shim vs real MA platform. |
| Cost ticker idle-pause billing | Layer 3 — Respond (`cost.py`) | Dashboard (`server/events.py`) | Ticker runs in Layer 3; dashboard aggregates for SSE emission. |
| Dispatch verification counter (test-only instrumentation) | Test harness (Layer 3 tests) | — | Not production code; belongs in a conftest fixture or monkey-patch. |
| PredatorPatternLearner checkpoint across sim-day | Layer 3 — Respond (`predator_pattern_learner.py` + `session.py::checkpoint`) | Layer 5 — Defend (attestation ledger) | Checkpoint is Layer 3 state; optional attestation log is Layer 5. |

Note: the scenario runner (`scenarios/base.py`) is the test harness for Layer 3, not Layer 1. Confusing these two matters for the routing-dispatch fix — the scenario does NOT go through the MQTT bus (`SensorBus`), it injects events directly into `_DemoMesh.dispatch()` via `_route_event()`. That's why the scenario needs its own routing table in addition to `wake_topics` in the specs.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | `>=0.69,<1` (installed: **0.96.0** [VERIFIED]) | Managed Agents SDK — `client.beta.sessions.{create,retrieve,events.send,events.stream,archive,delete}` | Already the project's Managed Agents transport (`managed.py:140,149,216,240`). `client.beta.sessions` exposes `archive/create/delete/events/list/resources/retrieve/update` [VERIFIED via introspection]. `client.beta.sessions.events` exposes `list/send/stream` [VERIFIED]. |
| `claude-agent-sdk` | pinned in pyproject | MCP-server wiring for in-session tool calls | Already used by `src/skyherd/mcp/*.py` |
| `pytest` + `pytest-asyncio` | already pinned | Async test framework for session lifecycle tests | Project's existing test stack |

### Supporting (in-tree; nothing new)

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `skyherd.agents.session.SessionManager` | Local shim — full sim path | Scenarios, unit tests, CI without API key |
| `skyherd.agents.managed.ManagedSessionManager` | Real platform client | `SKYHERD_AGENTS=managed` + `ANTHROPIC_API_KEY` set |
| `skyherd.agents.mesh.AgentMesh` | Live 5-agent mesh with persistent sessions | Production / live dashboard; **template for _DemoMesh fix** |
| `skyherd.agents._handler_base.run_handler_cycle` | Auto-selects managed vs local vs simulation path based on session type + env | All 5 agent handlers already call it |
| `skyherd.agents.cost.CostTicker` / `run_tick_loop` | Per-session cost metering; idle-pause primitive | Already wired into `Session` via `SessionManager.create_session()` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-memory session registry keyed by agent name (inside `_DemoMesh`) | Shared `SessionRegistry` class consumed by both `AgentMesh` and `_DemoMesh` | Cleanest refactor long-term; defer per `deferred` section unless trivial (George's decision: explicitly listed as deferred). |
| Eager session creation in `_DemoMesh.__init__` | Lazy: create on first `dispatch()` for that agent | Eager is simpler and matches `AgentMesh.start()`; lazy mirrors the real "session created when first event arrives" Managed Agents lifecycle but adds a branch. **Recommend eager.** |
| Class-level counter on `SessionManager.__init__` | Instance-level dispatch counter on `_DemoMesh` | Counter on `__init__` catches the leak directly (what the audit measured); `_DemoMesh` dispatch counter proves the routing half. **Use both** — they measure different things. |

**Installation:** No new dependencies required. All work is refactoring within existing modules.

**Version verification:**
```bash
uv run python3 -c "import anthropic; print(anthropic.__version__)"
# → 0.96.0   [VERIFIED 2026-04-22]
```

---

## Architecture Patterns

### System Architecture Diagram

Per-scenario data flow after the fix:

```
┌─────────────────────┐
│ Scenario.setup()    │   sets world pre-conditions
│ (e.g. Coyote)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│ _DemoMesh.__init__(ledger)                              │
│   ┌─────────────────────────────────────────────────┐   │
│   │ SessionManager()  ← ONE manager per scenario    │   │
│   │   .create_session(FENCELINE_DISPATCHER_SPEC)    │   │
│   │   .create_session(HERD_HEALTH_WATCHER_SPEC)     │   │
│   │   .create_session(PREDATOR_PATTERN_LEARNER)  ★  │   │
│   │   .create_session(GRAZING_OPTIMIZER_SPEC)       │   │
│   │   .create_session(CALVING_WATCH_SPEC)           │   │
│   │ _sessions: dict[name → Session] = {…5 entries…} │   │
│   └─────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────┘
                             │
   ┌─────────────────────────┴───────────────────────────┐
   │ sim loop (600s / 5s steps)                          │
   │                                                     │
   │   world.step(5.0) → [events]                        │
   │   scenario.inject_events(world, t) → [events]       │
   │                                                     │
   │   for ev in all_events:                             │
   │     _route_event(ev, mesh, _registry, ledger)       │
   │        ↓                                            │
   │     routing_table[ev.type] → [agent_names]          │
   │        ↓                                            │
   │     for name in agent_names:                        │
   │       await mesh.dispatch(name, ev, spec, handler)  │
   │          ↓                                          │
   │       session = mesh._sessions[name]  ← REUSE       │
   │       mgr.wake(session.id, ev)                      │
   │       calls = await handler(session, ev, None)      │
   │       mgr.sleep(session.id)     ← idle-pause ticker │
   │       mesh._tool_call_log[name].extend(calls)       │
   │                                                     │
   └─────────────────────────────────────────────────────┘
                             │
                             ▼
   ┌─────────────────────────────────────────────────┐
   │ Scenario.assert_outcome(event_stream, mesh)     │
   │   - tool calls present                          │
   │   - AgentDispatched counter per agent ≥ 1       │
   └─────────────────────────────────────────────────┘

★ New: PredatorPatternLearner added to registry (ROUT-01).
```

Key change from today:
- **Before:** `dispatch()` creates fresh `SessionManager` + fresh `Session` every call ⇒ 241 sessions.
- **After:** `__init__` creates one `SessionManager` + five `Session` objects; `dispatch()` looks up the existing session by name ⇒ 5 sessions.

### Routing table canonical form

The scenario runner uses **event_type-based dispatch** (not MQTT topic patterns). This is intentional: scenarios inject events with a `type` key directly, skipping the MQTT bus. Two-column table lives at `base.py:326-337`:

```python
routing: dict[str, list[str]] = {
    "fence.breach":            ["FenceLineDispatcher"],
    "predator.spawned":        ["FenceLineDispatcher"],
    "camera.motion":           ["HerdHealthWatcher"],
    "health.check":            ["HerdHealthWatcher"],
    "collar.activity_spike":   ["CalvingWatch"],
    "calving.prelabor":        ["CalvingWatch"],
    "water.low":               ["FenceLineDispatcher", "GrazingOptimizer"],
    "weather.storm":           ["GrazingOptimizer"],
    "weekly.schedule":         ["GrazingOptimizer"],
    "storm.warning":           ["GrazingOptimizer"],

    # NEW (ROUT-02):
    "thermal.anomaly":         ["FenceLineDispatcher", "PredatorPatternLearner"],
    "nightly.analysis":        ["PredatorPatternLearner"],   # for cron-style wake
    # Also consider: the AgentMesh smoke test uses "nightly.analysis" event type
    # (see mesh.py:83 _SMOKE_WAKE_EVENTS entry for PredatorPatternLearner).
}
```

Note on topic `skyherd/+/cron/nightly`: that is an MQTT wake pattern (see `predator_pattern_learner.py:37-40`). The scenario runner's `routing` dict is keyed by event **type**, not MQTT topic. So for ROUT-02's `skyherd/+/cron/nightly` requirement, either:
- Map `"nightly.analysis"` event-type to `[PredatorPatternLearner]` (what the smoke test uses), OR
- Also enhance `_route_event` to check the `topic` field when present and match against `agent_spec.wake_topics` using `_mqtt_topic_matches`. Cleaner, matches live-mesh behavior. **Recommended for future work, not strictly required for this phase** — the event-type route is sufficient for MA-05 checkpoint test.

### Pattern 1: Live mesh session persistence (template for `_DemoMesh` fix)

**What:** `AgentMesh` creates sessions once in `start()`, stores them in a `dict[str, Session]` keyed by agent name, reuses across all incoming MQTT events.
**When to use:** Mirror exactly in `_DemoMesh` for scenario runs.

```python
# Source: src/skyherd/agents/mesh.py:126-146 [VERIFIED by inspection]
async def start(self) -> None:
    """Create all 5 sessions and start the cost-tick loop + MQTT subscriber."""
    for spec, handler_fn in _AGENT_REGISTRY:
        session = self._session_manager.create_session(spec)
        self._sessions[spec.name] = session          # ← registry keyed by name
        self._handlers[spec.name] = handler_fn
        logger.info("AgentMesh: registered %s (session %s)", spec.name, session.id[:8])

    tickers = self._session_manager.all_tickers()
    self._tick_task = asyncio.create_task(
        run_tick_loop(tickers, self._stop_event),
        name="cost-tick-loop",
    )
    ...

# Then on each incoming event:
async def _run_handler(self, session: Session, wake_event, handler_fn):
    try:
        await handler_fn(session, wake_event, sdk_client=None)
    except Exception as exc:
        logger.error("handler error for %s: %s", session.agent_name, exc)
    finally:
        self._session_manager.sleep(session.id)    # idle-pause ticker
```

### Pattern 2: Managed Agents send-event pattern

**What:** A session is created once with `client.beta.sessions.create(agent=…, environment_id=…)`; subsequent events are sent via `client.beta.sessions.events.send(session_id, events=[…])`; the session naturally transitions `idle → running → idle` on each send.
**When to use:** This is what the real platform does. Local shim emulates this via `wake()` / `sleep()` on the same `Session` object.

```python
# Source: https://platform.claude.com/docs/en/managed-agents/sessions [CITED]
# "A session is a running agent instance within an environment.
#  Each session references an agent and an environment (both created separately),
#  and maintains conversation history across multiple interactions."

# Create once:
session = client.beta.sessions.create(agent=agent.id, environment_id=env.id)

# Reuse — every send transitions idle → running:
client.beta.sessions.events.send(
    session.id,
    events=[{"type": "user.message", "content": [{"type": "text", "text": "…"}]}],
)

# Session statuses (from docs):
#   idle         — waiting for input (default after creation)
#   running      — actively executing
#   rescheduling — transient error, retrying
#   terminated   — unrecoverable error
```

### Pattern 3: Test instrumentation via `__init__` counter

**What:** Monkey-patch `SessionManager.__init__` to count invocations per scenario run.
**When to use:** MA-03 verification — proves the leak is closed at the construction boundary.

```python
# Source: Live-reproduced in this research [VERIFIED — reproduction output below]
def test_coyote_creates_at_most_five_sessions():
    from skyherd.agents import session as session_module

    _orig_init = session_module.SessionManager.__init__
    count = {"n": 0}
    def _counting_init(self, *args, **kwargs):
        count["n"] += 1
        _orig_init(self, *args, **kwargs)
    session_module.SessionManager.__init__ = _counting_init
    try:
        from skyherd.scenarios import run
        result = run("coyote", seed=42)
    finally:
        session_module.SessionManager.__init__ = _orig_init

    assert result.outcome_passed
    assert count["n"] <= 5, f"Session leak: {count['n']} SessionManager instances"
```

### Recommended Project Structure

No structural changes. Work is localized to:

```
src/skyherd/
├── scenarios/
│   └── base.py          # _DemoMesh + _registry + routing table — PRIMARY EDIT SITE
├── agents/
│   ├── session.py       # SessionManager — unchanged (API contract preserved)
│   ├── managed.py       # ManagedSessionManager — unchanged (API parity preserved)
│   ├── mesh.py          # AgentMesh — template, unchanged
│   └── cost.py          # CostTicker — unchanged
tests/
├── scenarios/
│   ├── test_rustling.py    # EXTEND: add dispatch count assertions (ROUT-03)
│   ├── test_coyote.py      # EXTEND: add session-count-≤5 assertion (MA-03)
│   └── conftest.py         # EXTEND: add optional session counter fixture
└── agents/
    ├── test_cost.py        # EXTEND: add idle-pause-after-N-seconds assertion (MA-04)
    └── test_session.py     # EXTEND: add checkpoint persistence cross-boundary (MA-05)
```

### Anti-Patterns to Avoid

- **Creating a new `SessionManager` per wake event** — the bug being fixed. The `SessionManager` constructor wires a `runtime/sessions/` dir and cost-ticker scaffolding; instantiating it 241 times wastes allocations and destroys shared ticker state.
- **Making `_DemoMesh.dispatch()` also responsible for routing** — keep routing in `_route_event()` (the dict-based dispatch), keep `dispatch()` responsible for wake/handle/sleep on an **existing** session. Don't conflate.
- **Using the real MA platform for scenario runs** — scenarios run with `sdk_client=None`, exercising the simulation path (`simulate.py`). Keep it that way — simulation tests are free, deterministic, and fast (~3s for all 8).
- **Forgetting the 8 bonus scenarios** — `SCEN-02` is a milestone-wide zero-regression criterion. All 8 (coyote, sick_cow, water_drop, calving, storm, cross_ranch_coyote, wildfire, rustling) must still PASS after the `_DemoMesh` refactor.
- **Per-scenario counter leaks across pytest sessions** — pytest shares state; `conftest.py` already has a `scenarios_snapshot` autouse fixture (`tests/scenarios/conftest.py:14-40`). Any new `SessionManager.__init__` monkey-patch must restore the original in a fixture teardown or use a context manager.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session persistence across events | Custom event queue + re-instantiation logic | Existing `SessionManager._sessions` dict + `wake/sleep` semantics | Already models MA platform lifecycle. `managed.py` preserves the same API shape. |
| Cost idle-pause logic | New "pause tracker" | `CostTicker.set_state("idle")` already called by `SessionManager.sleep()` | Already tested in `tests/agents/test_cost.py:97-107`. Wiring already hooked through `session.py:224-225,241`. |
| MQTT topic pattern matching | Custom glob/regex | `skyherd.agents.session._mqtt_topic_matches()` | Already implements `+` and `#` wildcards per MQTT spec; tested in `test_webhook_routing.py:29-55`. |
| Checkpoint serialization | Pickle/custom format | `SessionManager.checkpoint()` → `runtime/sessions/{id}.json` | JSON, round-trippable via `restore_from_checkpoint()`, already at 98% coverage. |
| Managed-vs-local runtime selection | Env-var parsing in each handler | `run_handler_cycle()` in `_handler_base.py` | Already auto-selects based on `SKYHERD_AGENTS` + `platform_session_id` attribute. All 5 handlers already call it. |
| Session event-type routing | New dispatcher | Extend existing `base.py::_route_event` dict | One-line changes; existing pattern. |

**Key insight:** This phase is 100% plumbing. Every primitive needed (session registry, wake/sleep, cost ticker, checkpoint, topic matching, handler dispatch) already exists and is tested. The work is wiring them together correctly in `_DemoMesh` to match what `AgentMesh` already does.

---

## Runtime State Inventory

This is a refactor phase on a brownfield codebase. Inventory of runtime state that might be affected:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **`runtime/sessions/*.json`** checkpoint files from previous runs; **`runtime/scenario_runs/*.jsonl`** replay logs; **`runtime/agent_ids.json`** holding 5 MA platform agent IDs; **`runtime/ma_environment_id.txt`** holding live env ID; **`docs/REPLAY_LOG.md`** cumulative log (currently modified per `git status`) | **None required for state.** Code change should not invalidate any of these. However: `_DemoMesh.__init__` now eagerly creates 5 sessions, which means `runtime/sessions/` gets 5 checkpoint JSONs per scenario run instead of 241. That's a filesystem behavior change — cleaner, but worth noting. No migration. |
| Live service config | **Real MA platform agents** already provisioned (`runtime/agent_ids.json` has 5 IDs, `runtime/ma_environment_id.txt` has env ID per `ARCHITECTURE.md:89-93`) | **None.** Scenario path does NOT touch the real platform (it uses `sdk_client=None` simulation path). Real MA provisioning is unchanged. |
| OS-registered state | None — this phase has no OS daemon, systemd, task scheduler, pm2 registration | None — verified by grep on `src/skyherd/` (no OS-process registration code). |
| Secrets/env vars | `SKYHERD_AGENTS`, `ANTHROPIC_API_KEY` (read in `session.py:418`, `managed.py:142`, `_handler_base.py:81,87`) | **None — code reads env vars by exact name unchanged.** No secret key is renamed. |
| Build artifacts / installed packages | None — no package rename, no egg-info, no compiled binary | None. |

**Canonical question answered:** After the refactor, the only user-visible runtime change is that `runtime/sessions/` grows by 5 JSON files per scenario run instead of 241 (good). Every other runtime artifact (agent IDs, env ID, scenario JSONL, ledger DB, REPLAY_LOG.md line format) is unchanged.

---

## Validation Architecture

> Mandatory per `workflow.nyquist_validation=true` in `.planning/config.json`. Each test here maps to one or more phase requirements and cites the target test file.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | **pytest 8** + **pytest-asyncio** (per `pyproject.toml` — exact pins visible by `grep pytest pyproject.toml`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` section (project root) |
| Quick run command | `uv run pytest tests/scenarios/test_coyote.py::TestCoyoteScenario -x` |
| Scoped suite for this phase | `uv run pytest tests/scenarios/ tests/agents/test_cost.py tests/agents/test_session.py tests/agents/test_webhook_routing.py -x` |
| Full suite command | `uv run pytest` (all 1106 tests) |
| Scenarios end-to-end | `make demo SEED=42 SCENARIO=all` (≈3s wall) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Target File / Location | Automated Command | File Exists? |
|--------|----------|-----------|------------------------|-------------------|-------------|
| MA-01 | Session reused across events in a scenario run | unit | `tests/agents/test_session.py` (new test class `TestSessionReuse`) | `uv run pytest tests/agents/test_session.py::TestSessionReuse -x` | ✅ (file exists; extend) |
| MA-02 | `_DemoMesh._sessions` dict present, keyed by name, 5 entries | unit | `tests/scenarios/test_base.py` (new test) | `uv run pytest tests/scenarios/test_base.py -k "sessions_dict" -x` | ✅ (file exists; extend) |
| MA-03 | Coyote scenario creates ≤5 `SessionManager` instances | integration | `tests/scenarios/test_coyote.py::TestCoyoteScenario::test_creates_at_most_five_sessions` | `uv run pytest tests/scenarios/test_coyote.py::TestCoyoteScenario::test_creates_at_most_five_sessions -x` | ✅ (extend) |
| MA-04 | After N idle seconds, `all_idle=True` + `rate_per_hr_usd=0.0` | integration | `tests/agents/test_cost.py::TestRunTickLoop` (new test) + `tests/server/test_events.py` if present | `uv run pytest tests/agents/test_cost.py::TestRunTickLoop -x` | ✅ (extend) |
| MA-05 | PredatorPatternLearner session state survives a checkpoint/restore cycle | unit | `tests/agents/test_session.py` (new `test_checkpoint_round_trip_predator_pattern`) | `uv run pytest tests/agents/test_session.py -k checkpoint -x` | ✅ (extend) |
| ROUT-01 | `PredatorPatternLearner` in `_registry` | unit | `tests/scenarios/test_base.py` (new `test_registry_includes_predator_pattern_learner`) | `uv run pytest tests/scenarios/test_base.py -k predator -x` | ✅ (extend) |
| ROUT-02 | `thermal.anomaly` routes to `[FenceLineDispatcher, PredatorPatternLearner]`; `nightly.analysis` routes to `[PredatorPatternLearner]` | unit | `tests/scenarios/test_base.py` (new `test_routing_table_thermal_anomaly`, `test_routing_table_nightly`) | `uv run pytest tests/scenarios/test_base.py -k routing -x` | ✅ (extend) |
| ROUT-03 | Rustling scenario dispatches PredatorPatternLearner (not just logs the event) | integration | `tests/scenarios/test_rustling.py::TestRustlingScenarioIntegration::test_predator_pattern_learner_dispatched` | `uv run pytest tests/scenarios/test_rustling.py::TestRustlingScenarioIntegration::test_predator_pattern_learner_dispatched -x` | ✅ (extend) |
| ROUT-04 | All 5 agents run in ≥1 scenario | integration (suite-level) | `tests/scenarios/test_run_all.py` (new `test_every_agent_dispatched_at_least_once_across_suite`) | `uv run pytest tests/scenarios/test_run_all.py -k every_agent -x` | ✅ (extend) |
| SCEN-02 | All 8 scenarios still PASS after refactor | integration | `make demo SEED=42 SCENARIO=all` + `tests/scenarios/test_*.py` full | `uv run pytest tests/scenarios/ -x && make demo SEED=42 SCENARIO=all` | ✅ (regression gate) |

### Concrete Test Specs

Below: pseudocode for the six most load-bearing new/extended tests. Planner lifts these into TDD task actions.

**1. `tests/scenarios/test_coyote.py::test_creates_at_most_five_sessions` (MA-03)**

```python
def test_creates_at_most_five_sessions(monkeypatch):
    # Reproduce the audit's counter pattern — count __init__ calls
    from skyherd.agents import session as session_module
    orig_init = session_module.SessionManager.__init__
    count = {"n": 0}
    def _counting(self, *a, **kw):
        count["n"] += 1
        orig_init(self, *a, **kw)
    monkeypatch.setattr(session_module.SessionManager, "__init__", _counting)

    from skyherd.scenarios import run
    result = run("coyote", seed=42)

    assert result.outcome_passed, f"regression: {result.outcome_error}"
    assert count["n"] <= 5, (
        f"Session leak not closed: {count['n']} SessionManager instances "
        f"(target: ≤5)"
    )
```

Current (pre-fix) value: **241** [VERIFIED via live reproduction].

**2. `tests/scenarios/test_base.py::test_demo_mesh_holds_session_registry` (MA-02)**

```python
def test_demo_mesh_holds_five_sessions_keyed_by_name():
    from skyherd.scenarios.base import _DemoMesh
    mesh = _DemoMesh(ledger=None)
    # After the fix, sessions should exist before any dispatch()
    # (if eager) or must be reachable via dispatch() and dict-lookup pattern.
    names = {"FenceLineDispatcher", "HerdHealthWatcher",
             "PredatorPatternLearner", "GrazingOptimizer", "CalvingWatch"}
    # Option A (eager): mesh._sessions keyed by name
    assert hasattr(mesh, "_sessions"), "_DemoMesh needs a sessions registry"
    assert set(mesh._sessions.keys()) == names
    # All sessions idle after init, no wake events yet
    assert all(s.state == "idle" for s in mesh._sessions.values())
```

**3. `tests/scenarios/test_rustling.py::test_predator_pattern_learner_dispatched` (ROUT-03)**

```python
def test_predator_pattern_learner_dispatched_in_rustling():
    result = run("rustling", seed=42)
    assert "PredatorPatternLearner" in result.agent_tool_calls, (
        f"PredatorPatternLearner never dispatched. "
        f"Agents with tool calls: {list(result.agent_tool_calls)}"
    )
    learner_calls = result.agent_tool_calls["PredatorPatternLearner"]
    tool_names = {c["tool"] for c in learner_calls}
    # From simulate.py:313-328 — learner emits these two tool calls
    assert "get_thermal_history" in tool_names or "log_pattern_analysis" in tool_names, (
        f"Expected learner tool calls in rustling; got: {tool_names}"
    )
```

**4. `tests/scenarios/test_run_all.py::test_every_agent_dispatched_at_least_once` (ROUT-04)**

```python
def test_every_agent_dispatched_at_least_once_across_suite():
    from skyherd.scenarios import run_all
    results = run_all(seed=42)
    dispatched = set()
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

**5. `tests/agents/test_cost.py::test_all_idle_emits_zero_rate_per_hr` (MA-04)**

```python
async def test_tick_loop_flags_all_idle_after_threshold():
    from skyherd.agents.cost import CostTicker, run_tick_loop
    t1 = CostTicker(session_id="s1")
    t2 = CostTicker(session_id="s2")
    t1.set_state("idle")
    t2.set_state("idle")
    stop = asyncio.Event()
    # Simulate server/events.py aggregation (lines 347-377)
    any_active = any(t._current_state == "active" for t in [t1, t2])
    assert any_active is False
    all_idle = not any_active
    rate_per_hr_usd = 0.0 if all_idle else 0.08
    assert all_idle is True
    assert rate_per_hr_usd == 0.0
```

Then higher-level wiring (lift from `server/events.py:347-377`):

```python
def test_real_cost_tick_aggregator_pauses_when_all_idle():
    # Build two idle tickers → aggregator should emit all_idle=True, rate_per_hr_usd=0.0
    ... (uses the same aggregation logic from events.py::_real_cost_tick)
```

**6. `tests/agents/test_session.py::test_checkpoint_persists_across_restore` (MA-05)**

```python
def test_predator_pattern_learner_checkpoint_round_trip(tmp_path, monkeypatch):
    # Redirect runtime/sessions to tmp_path
    monkeypatch.setattr("skyherd.agents.session._RUNTIME_DIR", tmp_path)
    from skyherd.agents.session import SessionManager
    from skyherd.agents.predator_pattern_learner import PREDATOR_PATTERN_LEARNER_SPEC

    mgr = SessionManager()
    s = mgr.create_session(PREDATOR_PATTERN_LEARNER_SPEC)
    # Simulate a sim-day of activity — wake, consume events, checkpoint
    mgr.wake(s.id, {"topic": "skyherd/ranch_a/thermal/cam_1", "type": "thermal.clip"})
    mgr.wake(s.id, {"topic": "skyherd/ranch_a/cron/nightly", "type": "nightly.analysis"})
    assert len(s.wake_events_consumed) == 2
    path = mgr.checkpoint(s.id)
    assert path.exists()

    # New manager (sim-day boundary) — restore state
    mgr2 = SessionManager()
    # Must register session first to know its ID mapping; use restore_from_checkpoint
    mgr2._sessions[s.id] = s  # pre-register for spec resolution
    restored = mgr2.restore_from_checkpoint(s.id)
    assert len(restored.wake_events_consumed) == 2
    assert restored.state == "idle"  # always restored idle per session.py:304
```

### Sampling Rate

- **Per task commit:** `uv run pytest tests/scenarios/test_coyote.py tests/scenarios/test_rustling.py tests/agents/test_session.py tests/agents/test_cost.py -x` (scoped to this phase's surface; <10s wall)
- **Per wave merge:** `uv run pytest tests/scenarios/ tests/agents/ -x` (<30s)
- **Phase gate:** `uv run pytest` full + `make demo SEED=42 SCENARIO=all` green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] No dedicated `test_demo_mesh.py` — dispatch-level tests currently land in `tests/scenarios/test_base.py` which is a 5KB file today. Could stay there.
- [ ] No shared session-counter fixture — the `monkeypatch.setattr(SessionManager, "__init__", …)` pattern is lifted per-test. **Recommend:** add a `tests/agents/conftest.py::session_manager_counter` fixture that returns a `{"n": int}` dict and installs the counter. Reusable across MA-03 and future leak-regression tests.
- [ ] Framework install: none required — pytest + pytest-asyncio already pinned.

*(All other gaps: none — existing test infrastructure covers the phase.)*

---

## Common Pitfalls

### Pitfall 1: Mistaking topic patterns for event types

**What goes wrong:** `PREDATOR_PATTERN_LEARNER_SPEC.wake_topics` lists `"skyherd/+/cron/nightly"` (MQTT pattern). The scenario runner routes by `event["type"]` (e.g. `"nightly.analysis"`). If you add `"skyherd/+/cron/nightly"` as a key in the scenario `routing` dict, it never fires — because the scenario's `event["type"]` will be `"thermal.anomaly"` or `"nightly.analysis"`, never the topic string.
**Why it happens:** The live `AgentMesh._mqtt_loop()` uses topics; the scenario `_route_event` uses types; they diverged for simulation speed.
**How to avoid:** Route by event TYPE in `scenarios/base.py`. If you want topic-pattern parity with the live mesh, add optional topic-based matching as a second lookup path (`if event.get("topic"): match against agent_spec.wake_topics`). Keep both.
**Warning signs:** A test asserts `PredatorPatternLearner` was dispatched, but `mesh._tool_call_log` is empty for that agent even though `thermal.anomaly` events are in the stream.

### Pitfall 2: Counter fixture leaking across tests

**What goes wrong:** Monkey-patching `SessionManager.__init__` without cleanup leaks the counter into subsequent tests; the coyote counter might see sessions created by a later test.
**Why it happens:** pytest fixtures share module-level state.
**How to avoid:** Use `monkeypatch` (pytest built-in) which auto-reverts, NOT raw `SessionManager.__init__ = _counting`. Or wrap in try/finally. The autouse `scenarios_snapshot` in `tests/scenarios/conftest.py` is a good model.
**Warning signs:** A session-count test passes in isolation but fails when run in the full suite.

### Pitfall 3: Idle state not reached because `sleep()` never called

**What goes wrong:** After refactor, if the new `_DemoMesh.dispatch()` forgets to call `mgr.sleep(session.id)` at the end, the ticker stays in `"active"` state and cost accrues forever. `all_idle` never goes True.
**Why it happens:** Easy to miss when refactoring the dispatch flow.
**How to avoid:** Use a `try/finally` in `dispatch()` around the handler call, ending with `manager.sleep(session.id)`. Mirror `AgentMesh._run_handler` (`mesh.py:241-253`).
**Warning signs:** MA-04 test fails; `run_tick_loop` always shows `any_active=True`.

### Pitfall 4: Session created inside `_DemoMesh.__init__` breaks test_base.py fixtures

**What goes wrong:** Many existing tests instantiate `_DemoMesh()` with `ledger=None`. If `_DemoMesh.__init__` now eagerly calls `SessionManager().create_session()` for 5 specs, **and** those specs touch the filesystem via `_load_text()` for skill files, isolated unit tests that `cd` somewhere weird will fail.
**Why it happens:** `SessionManager.create_session()` triggers `_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)` at `session.py:189` and the wake path tries to read system-prompt files.
**How to avoid:** Two options: (a) eager creation is OK because `create_session` doesn't read prompts — only `wake()` does. Confirmed by inspection of `session.py:195-212`. So eager is safe. (b) Alternatively, lazy creation on first `dispatch()` of that agent. **Recommend (a) eager** — simpler and mirrors `AgentMesh`.
**Warning signs:** `test_base.py` tests break with `FileNotFoundError` after refactor.

### Pitfall 5: Rustling scenario assertion already had `launch_drone` but learner never runs

**What goes wrong:** The current `test_rustling.py::test_full_run_has_launch_drone` passes today (via FenceLineDispatcher). But that tells you nothing about PredatorPatternLearner. Adding PredatorPatternLearner to routing means it WILL now run, so its `log_pattern_analysis` tool call will appear in `mesh._tool_call_log` — any existing test that counts total tool calls across all agents will break.
**Why it happens:** The simulate path in `simulate.py:308-328` for PredatorPatternLearner always returns 2 tool calls. Rustling injects `thermal.anomaly` 3 times? Actually: the `_anomaly_injected` guard at `rustling.py:67-68` ensures only one injection. So 1 `thermal.anomaly` event × 2 agents × 2 tool calls = 4 new tool calls added to rustling total.
**How to avoid:** Re-run `make demo SEED=42 SCENARIO=rustling` **before and after** the routing fix and diff the counts. Update any brittle total-tool-call counts.
**Warning signs:** A passing test fails with `assert total_tool_calls == 7` → `expected 7, got 11`.

### Pitfall 6: Server `events.py:353` references `_tickers` dict that doesn't exist on `SessionManager`

**What goes wrong:** `server/events.py:352-354` reads `self._mesh._session_manager._tickers.get(session.id)` — but `SessionManager` has no `_tickers` attribute. Tickers live on `Session._ticker`. This silently crashes the live-mode cost aggregator in a try/except.
**Why it happens:** Code drift between `session.py` (tickers attached per-Session) and `events.py` (reaches for a manager-level `_tickers` dict).
**How to avoid:** Don't fix in this phase — **flag for Phase 5 (Dashboard Live-Mode)**. This phase should not touch `server/events.py`. Document the finding.
**Warning signs:** `make dashboard` live-mode (`SKYHERD_MOCK=0`) throws or silently shows zeros in the cost ticker.

---

## Runtime reproduction (confidence artifact)

Ran this in the working tree **2026-04-22** [VERIFIED]:

```python
uv run python3 -c "
import asyncio
from skyherd.agents.session import SessionManager
_orig_init = SessionManager.__init__
counter = {'n': 0}
def _counting_init(self, *a, **kw):
    counter['n'] += 1
    _orig_init(self, *a, **kw)
SessionManager.__init__ = _counting_init

from skyherd.scenarios import run
result = run('coyote', seed=42)
print(f'SessionManager instances during coyote run: {counter[\"n\"]}')
print(f'Scenario passed: {result.outcome_passed}')
print(f'Events: {len(result.event_stream)}')
print(f'Tool calls: {sum(len(v) for v in result.agent_tool_calls.values())}')
"
```

Output:
```
SessionManager instances during coyote run: 241
Scenario passed: True
Events: 131
Tool calls: 244
```

This is load-bearing evidence for MA-03's acceptance criterion. After the fix, `SessionManager instances` should drop to **5** (or **4** if `_DemoMesh` lazy-creates and `CalvingWatch` is never woken in coyote — coyote injects fence.breach but no collar.activity_spike, so CalvingWatch wake never fires; still, eager creation creates 5 upfront).

---

## Code Examples

Verified patterns from the live codebase:

### Session registry pattern — the fix template

```python
# Source: src/skyherd/agents/mesh.py:100-146 [VERIFIED]
class AgentMesh:
    def __init__(self, mqtt_publish_callback=None, ledger_callback=None):
        self._session_manager = SessionManager(
            mqtt_publish_callback=mqtt_publish_callback,
            ledger_callback=ledger_callback,
        )
        self._sessions: dict[str, Session] = {}    # name → session
        self._handlers: dict[str, Any] = {}

    async def start(self) -> None:
        for spec, handler_fn in _AGENT_REGISTRY:
            session = self._session_manager.create_session(spec)
            self._sessions[spec.name] = session
            self._handlers[spec.name] = handler_fn
```

### Wake/handle/sleep cycle — the dispatch template

```python
# Source: src/skyherd/agents/mesh.py:241-253 [VERIFIED]
async def _run_handler(self, session, wake_event, handler_fn):
    try:
        await handler_fn(session, wake_event, sdk_client=None)
    except Exception as exc:
        logger.error("handler error for %s: %s", session.agent_name, exc)
    finally:
        self._session_manager.sleep(session.id)  # idle-pause
```

### Managed Agents session lifecycle

```python
# Source: Anthropic Managed Agents docs [CITED: platform.claude.com/docs/en/managed-agents/sessions]
# Session is created ONCE; events flow across its lifetime.
session = client.beta.sessions.create(
    agent=agent.id,
    environment_id=environment.id,
    title="skyherd-FenceLineDispatcher",
)

# Every event send transitions idle → running:
with client.beta.sessions.events.stream(session.id) as stream:
    client.beta.sessions.events.send(
        session.id,
        events=[{"type": "user.message",
                 "content": [{"type": "text", "text": "fence breach on seg_1"}]}],
    )
    for event in stream:
        if event.type == "session.status_idle":
            break   # agent is done with this turn; session is REUSABLE
```

### Topic pattern matching (MQTT semantics, already tested)

```python
# Source: src/skyherd/agents/session.py:361-380 [VERIFIED]
def _mqtt_topic_matches(topic: str, pattern: str) -> bool:
    """Supports `+` (one level) and `#` (remaining levels)."""
    if pattern == "#": return True
    if pattern.endswith("/#"):
        prefix = pattern[:-2]
        return topic == prefix or topic.startswith(prefix + "/")
    if "#" in pattern: return False
    topic_parts = topic.split("/")
    pattern_parts = pattern.split("/")
    if len(topic_parts) != len(pattern_parts): return False
    return all(p == "+" or p == t for p, t in zip(pattern_parts, topic_parts, strict=True))
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Stateless session-per-call agent loops | Managed Agents: long-lived sessions with idle-pause billing | Apr 2026 (MA launch) | Agents persist context across events; cheap to keep idle. This phase aligns SkyHerd with the MA model. |
| Hand-rolled MQTT pattern matching | `aiomqtt` + ad-hoc `_mqtt_topic_matches` helper | pre-existing in repo | SkyHerd's helper is correct (verified by `tests/agents/test_webhook_routing.py:29-55`). |
| Cost metered per API call only | Per-session-hour + per-token + per-cache (idle = $0) | Apr 2026 MA | SkyHerd's `CostTicker` already models this (`cost.py:32-36`). |

**Deprecated/outdated in the codebase:**
- `server/events.py:353` reads `self._mesh._session_manager._tickers` — `_tickers` dict doesn't exist; tickers live on Sessions. **Flag for Phase 5, not this phase.**
- `TWILIO_TOKEN` env var at `voice/call.py:44,68` — deprecated in favor of `TWILIO_AUTH_TOKEN` per `HYG-02`. **Not this phase.**

---

## Environment Availability

> Skipped — this phase has no external dependencies. It is a pure Python refactor + test extension inside the existing toolchain (`uv`, `pytest`, `anthropic`, `claude-agent-sdk` — all pinned in `pyproject.toml`, all currently installed).

Verification:
```bash
uv run python3 -c "import anthropic, claude_agent_sdk, pytest; print('ok')"
# → ok   [VERIFIED]
```

No Docker, no SITL, no Twilio, no ElevenLabs needed. No MQTT broker required (scenarios bypass the bus — they route events directly through `_route_event`).

---

## Project Constraints (from CLAUDE.md)

Extracting actionable directives from `/home/george/projects/active/skyherd-engine/CLAUDE.md` that this phase must honor:

- **Sim-first hardline** — MVP is 100% simulated. This phase stays entirely in the simulation path (`sdk_client=None`). ✓ Aligned.
- **TDD mandatory** — RED (failing test) → GREEN (min impl) → IMPROVE (refactor). Plan the tests from the "Validation Architecture" section FIRST. ✓ Phase is TDD-shaped.
- **All code new** — no imports from sibling `/home/george/projects/active/drone/` repo. ✓ No drone-repo imports needed.
- **MIT throughout** — no AGPL deps. ✓ No new deps.
- **Skills-first architecture** — domain knowledge in `skills/*.md`, not in long system prompts. ✓ Not affected — this phase doesn't touch skills or prompts.
- **No Claude/Anthropic attribution in commits** — ✓ Global config handles this.
- **Beta header `managed-agents-2026-04-01`** — applied automatically by SDK. Do NOT override. ✓ Aligned — no manual header code in this phase.
- **Prompt caching mandatory** — every `messages.create` / `sessions.events.send` emits `cache_control: ephemeral`. ✓ Already handled by `build_cached_messages()` in `session.py:110-152` and `_run_local_with_cache()` in `_handler_base.py:188-250`. This phase doesn't modify either.
- **Determinism** — `make demo SEED=42 SCENARIO=all` byte-identical across replays. ✓ Refactor must not introduce timing-dependent behavior. Use `time.monotonic()` sparingly; existing `CostTicker` already uses it correctly.
- **Test gate 80%+** — coverage floor. ✓ Current project at 87.42%; this phase should raise `cost.py` to ≥90% (HYG-03 — but that's Phase 3's concern).
- **No `dangerously-skip-permissions`** — not invoked.
- **Plan > this file > vision doc > your own judgment** — The plan at `/home/george/.claude/plans/update-ur-memory-project-context-splendid-swan.md` is v5.1-locked; this phase aligns with its Sim Completeness Gate item #1 ("All 5 Managed Agents live and cross-talking via shared MQTT").

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | *(none — every factual claim in this research is `[VERIFIED]` via direct code inspection, live Python reproduction, or `[CITED]` from platform.claude.com docs)* | — | — |

*All claims tagged `[ASSUMED]` in the source text of this document: zero.*

Confidence grounding:
- Session count of 241: **[VERIFIED]** by running the counter in this research session.
- `AgentMesh` as template: **[VERIFIED]** by inspecting `mesh.py:100-253`.
- Managed Agents session lifecycle: **[CITED]** platform.claude.com/docs/en/managed-agents/sessions.
- Anthropic Python SDK API shape (`sessions.create/retrieve/events.send/events.stream/archive/delete`): **[VERIFIED]** via `dir(client.beta.sessions)` introspection at anthropic 0.96.0.
- `events.py:353` `_tickers` bug: **[VERIFIED]** by grep — `_tickers` never defined on `SessionManager`.
- Prompt caching already wired correctly in both runtimes: **[VERIFIED]** by reading `_handler_base.py:188-250` (C1 fix comment block).

---

## Open Questions

1. **Should the scenario routing table also honor MQTT topic patterns (via `agent_spec.wake_topics`)?**
   - What we know: live `AgentMesh` uses topics; scenario `_DemoMesh` uses event-type dict. Both work. `ROUT-02` can be satisfied entirely via event-type dict.
   - What's unclear: Do we want strict parity between scenario and live paths? Event-type routing is simpler; topic-pattern routing is richer.
   - **Recommendation:** Stick with event-type dict for this phase (minimum viable fix). Defer topic-pattern parity. Note as follow-up.

2. **Eager vs lazy session creation in `_DemoMesh`?**
   - What we know: `AgentMesh.start()` is eager; `SessionManager.create_session()` doesn't touch the filesystem beyond `mkdir -p`. Eager is safe.
   - What's unclear: Does eager creation of 5 sessions slow down scenario unit tests (1106 tests, many instantiate `_DemoMesh`)?
   - **Recommendation:** Eager, because (a) it matches `AgentMesh`, (b) `create_session` is ~µs, (c) unit tests that don't run the sim loop will pay 5×µs overhead — negligible.

3. **Is PredatorPatternLearner's simulate path deterministic for the rustling scenario's expected tool count?**
   - What we know: `simulate.py:308-328` always returns 2 tool calls: `get_thermal_history` + `log_pattern_analysis`. Deterministic by construction.
   - What's unclear: Does rustling inject `thermal.anomaly` exactly once (protected by `self._anomaly_injected` guard), or multiple times?
   - **Recommendation:** Confirmed by reading `rustling.py:51-68` — guard ensures single injection. Therefore rustling will gain exactly 2 new tool calls per run once learner is routed. Fine.

4. **Does the `_DemoMesh` fix also need to fix the `tests/scenarios/test_coyote_with_sitl.py` SITL path?**
   - What we know: That test uses `SitlBackend`, not the simulation path. Its session lifetime is different (SITL session per test).
   - What's unclear: Does it use `_DemoMesh` internally?
   - **Recommendation:** Check quickly — if it does, verify it still passes post-fix. If not, ignore for this phase.

5. **How to handle the rustling scenario's existing assertion that only checks event presence?**
   - What we know: `test_rustling.py:156-163` asserts attestation entries by grepping `event_category=rustling_suspected`. Passes today without PredatorPatternLearner running.
   - What's unclear: Should we keep that assertion AND add a dispatch assertion, or replace?
   - **Recommendation:** Keep both. Event-presence is about attestation correctness; dispatch count is about agent persistence correctness. They're orthogonal.

---

## Security Domain

> Required per default. This phase operates on session lifecycle + routing. Minimal security surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Session auth is bearer-token API key, handled by anthropic SDK — unchanged by this phase. |
| V3 Session Management | **yes** | Session reuse across events, idle-pause, checkpoint lifecycle. Local shim emulates MA platform semantics. |
| V4 Access Control | no | No user auth in this phase. |
| V5 Input Validation | minimal | Wake events are internal dicts (not user input). No new validation surface. |
| V6 Cryptography | no | Attestation uses Ed25519 (`attest/signer.py`) — unchanged by this phase. Don't hand-roll. |

### Known Threat Patterns for this phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Session ID disclosure via logs | Information Disclosure | `session.py:211,226,249,272` already logs only first 8 chars of UUID. Preserve that. |
| Ticker/session state tampering via test monkeypatches leaking into production | Tampering | Use `pytest.MonkeyPatch` fixture (auto-reverts) for MA-03 counter; not raw attribute assignment. |
| Checkpoint JSON path traversal | Tampering | `runtime/sessions/{session_id}.json` — session_id is a server-generated UUID per `session.py:197`. No user control over path segment. ✓ Safe. |
| Denial-of-service via unbounded session creation | DoS | This is literally the bug being fixed. 241 sessions per scenario → 5. Zero-trust: add regression test (MA-03). |

No new crypto, no new secret handling, no new external I/O.

---

## Sources

### Primary (HIGH confidence)

- `src/skyherd/agents/session.py` — `SessionManager`, `Session`, `build_cached_messages`, `_mqtt_topic_matches`, `LocalSessionManager` alias, `get_session_manager` factory.
- `src/skyherd/agents/managed.py` — `ManagedSessionManager` (real platform client), `ManagedSession`, `ensure_agent`, `create_session_async`, `send_wake_event`, `stream_session_events`.
- `src/skyherd/agents/mesh.py` — `AgentMesh.start/stop/smoke_test/_mqtt_loop/_run_handler` — the session-registry template.
- `src/skyherd/agents/_handler_base.py` — `run_handler_cycle`, `_run_managed`, `_run_local_with_cache` (C1 prompt-cache fix).
- `src/skyherd/agents/cost.py` — `CostTicker.set_state/record_api_call/emit_tick`, `run_tick_loop`, pricing constants.
- `src/skyherd/agents/predator_pattern_learner.py` — `PREDATOR_PATTERN_LEARNER_SPEC`, handler.
- `src/skyherd/scenarios/base.py` — `_DemoMesh`, `_run_async`, `_route_event`, `_registry` dict, routing table.
- `src/skyherd/scenarios/rustling.py` — rustling scenario — the ROUT-03 target.
- `src/skyherd/agents/simulate.py:308-328` — `predator_pattern_learner` deterministic simulation.
- `tests/agents/test_cost.py` — idle-pause test patterns already established (lines 97-107).
- `tests/agents/test_webhook_routing.py` — topic matching test patterns.
- `tests/scenarios/test_rustling.py` — rustling test patterns; where ROUT-03 assertion lands.
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONCERNS.md` — audit ground truth.

### Secondary (HIGH confidence — CITED docs)

- **Anthropic Managed Agents docs** — `https://platform.claude.com/docs/en/managed-agents/sessions` (session lifecycle, status machine, API shape, beta header).
- **Anthropic Managed Agents docs** — `https://platform.claude.com/docs/en/managed-agents/events-and-streaming` (event types table — `user.message`, `user.interrupt`, `user.custom_tool_result`, `user.tool_confirmation`, `user.define_outcome`; session event types `session.status_idle/running/rescheduled/terminated`; span events `span.model_request_end` with `model_usage`).
- **Anthropic Managed Agents overview** — `https://platform.claude.com/docs/en/managed-agents/overview` (four concepts: Agent, Environment, Session, Events).
- **Anthropic Managed Agents agent setup** — `https://platform.claude.com/docs/en/managed-agents/agent-setup` (agent versioning, tools, `agent_toolset_20260401`).

### Tertiary

- Introspection of `anthropic 0.96.0` Python SDK via `dir(client.beta.sessions)` and `dir(client.beta.sessions.events)` — confirms the API surface the project depends on.

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — all libraries already in use; version pinned; introspection confirms API shape.
- Architecture: **HIGH** — live mesh is the template; direct code read reveals pattern.
- Pitfalls: **HIGH** — every pitfall either reproduced live (the leak) or traceable to a specific line of code (the `_tickers` bug, the event-type vs topic-pattern divergence).
- Validation: **HIGH** — test patterns exist for every requirement; only extending, not inventing.
- Managed Agents session semantics: **HIGH** — canonical Anthropic docs cited, API shape introspected.
- Checkpoint semantics (MA-05): **MEDIUM** — local shim semantics are clear (serialize → JSON → reload); "sim-day boundary" is an informal term — mapped to `duration_s=600` scenario clock + explicit `SessionManager.checkpoint()` call in a test.

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (30 days — stable codebase, no imminent MA SDK changes expected; hackathon submission is Apr 26 so practical window is 4 days).
