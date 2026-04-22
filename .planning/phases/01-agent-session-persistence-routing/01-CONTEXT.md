# Phase 1: Agent Session Persistence & Routing - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Each of the 5 agents runs on ONE long-lived Managed Agents session reused across all events in a scenario run, and every agent (including PredatorPatternLearner) is actually dispatched by the routing table.

Requirements: MA-01, MA-02, MA-03, MA-04, MA-05, ROUT-01, ROUT-02, ROUT-03, ROUT-04.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per workflow.skip_discuss=true (George invoked /gsd-autonomous "do full milestone one fully autonomously").

Use ROADMAP phase goal, success criteria, CONCERNS.md §1 (Priority 1 & Priority 2) and §6, and codebase conventions from `.planning/codebase/` to guide decisions.

### Known Constraints from Audit
- Current leak: `src/skyherd/scenarios/base.py:179` creates fresh `SessionManager()` per dispatch. 241 sessions per coyote scenario run.
- `_DemoMesh` is the dispatch surface — fix there.
- `_registry` dict at `base.py:234` omits `PredatorPatternLearner`.
- Routing table at `base.py:326-337` has no entry for `thermal.anomaly` or `skyherd/+/cron/nightly`.
- Cost ticker at `src/skyherd/agents/cost.py` — idle-pause billing should be verifiable after this phase.
- Zero-regression: all 8 scenarios must continue to PASS `make demo SEED=42 SCENARIO=all`.
- Must not break `ManagedSessionManager` (real MA platform wiring in `src/skyherd/agents/managed.py`) — session registry pattern should work for both local shim and real platform paths.

</decisions>

<code_context>
## Existing Code Insights

Codebase context gathered during `/gsd-map-codebase` (see `.planning/codebase/ARCHITECTURE.md`, `CONCERNS.md`, `STRUCTURE.md`).

Key integration points:
- `src/skyherd/scenarios/base.py` — `_DemoMesh.dispatch()` (the leak site), `_registry` dict, routing table
- `src/skyherd/agents/session.py` — `SessionManager` (local shim)
- `src/skyherd/agents/managed.py` — `ManagedSessionManager` (real MA platform; preserve API parity)
- `src/skyherd/agents/_handler_base.py` — `run_handler_cycle()` selects managed vs local vs simulation paths
- `src/skyherd/agents/mesh.py` — `AgentMesh.start()` and `_mqtt_loop()` — the "real" mesh, already persistent-session-capable; the scenario demo bypasses this
- `src/skyherd/agents/cost.py` — cost ticker emits `rate_per_hr_usd` + `all_idle` on SSE; needs verifiable idle-pause behavior
- `tests/scenarios/` — scenario test harness to add `AgentDispatched` counter assertions
- `src/skyherd/agents/predator_pattern_learner.py` — exists; just not wired into `_registry` + routing

</code_context>

<specifics>
## Specific Ideas

- Session registry keyed by agent name, stored on `_DemoMesh` instance; lazy creation on first wake; reuse thereafter.
- Consider extracting a `SessionRegistry` helper so both `_DemoMesh` (scenarios) and `AgentMesh` (live) can share it.
- For verification: add a `SessionManager.__init__` counter (module-level or class-level) the test harness can assert on.
- For idle-pause: add a cost ticker test that advances the clock past the idle threshold and asserts `all_idle: True` + `rate_per_hr_usd: 0.0`.
- For PredatorPatternLearner: rustling scenario should inject a `thermal.anomaly` event and assert the learner's handler got called (via `AgentDispatched` counter or mock).
- Checkpoint persistence (MA-05): the learner running across sim-day boundaries should see its session state retained — use session checkpoint/resume semantics in `SessionManager.checkpoint()`.

</specifics>

<deferred>
## Deferred Ideas

- Live Managed Agents platform session persistence (vs local shim session persistence) — the real MA path already supports persistent sessions per `managed.py`; this phase proves the demo path matches, but live-platform verification is a separate concern for Phase 5 (Dashboard Live-Mode).
- Session checkpoint serialization to disk for resume-across-process — overkill for scenario-run scope; in-memory registry per scenario run is enough.
- Refactoring `AgentMesh` to share code with `_DemoMesh` — pursue only if trivial during planning; otherwise defer.

</deferred>
