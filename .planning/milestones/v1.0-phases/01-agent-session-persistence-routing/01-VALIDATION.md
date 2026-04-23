---
phase: 1
slug: agent-session-persistence-routing
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-22
updated: 2026-04-22
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. See the "Validation Architecture" section of `01-RESEARCH.md` for full test specs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8 + pytest-asyncio |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/agents/ tests/scenarios/ -x` |
| **Full suite command** | `uv run pytest --cov=src/skyherd --cov-fail-under=80` |
| **Scenario suite** | `make demo SEED=42 SCENARIO=all` |
| **Estimated runtime** | ~30-60s (quick) / ~3-5min (full) / ~3s (scenarios) |

---

## Sampling Rate

- **After every task commit:** Run the task's `<automated>` command from its `<verify>` block (< 30s typically).
- **After every plan wave:** `uv run pytest tests/scenarios/ tests/agents/ -x && make demo SEED=42 SCENARIO=all`.
- **Before `/gsd-verify-work`:** Full suite `uv run pytest --cov=src/skyherd --cov-fail-under=80` + zero-regression on 8 scenarios.
- **Max feedback latency:** ~60 seconds per task.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| P1-01-T1 | 01 | 1 | MA-01, MA-02, MA-03, ROUT-01 | T-01-02 | Test monkeypatch auto-revert via pytest fixture (no cross-test pollution) | unit + integration (RED phase) | `uv run pytest tests/scenarios/test_base.py::TestDemoMesh tests/scenarios/test_coyote.py::TestCoyoteScenario::test_creates_at_most_five_sessions --tb=no` | tests/scenarios/test_base.py ✓ tests/scenarios/test_coyote.py ✓ | planned |
| P1-01-T2 | 01 | 1 | MA-01, MA-02, MA-03, ROUT-01 | T-01-01, T-01-03, T-01-04, T-01-05 | Bounded session count; short session IDs in logs; try/finally on handler; shallow-copy accessors | unit + integration + scenario regression (GREEN phase) | `uv run pytest tests/scenarios/test_base.py::TestDemoMesh tests/scenarios/test_coyote.py::TestCoyoteScenario::test_creates_at_most_five_sessions tests/scenarios/ tests/agents/test_session.py tests/agents/test_cost.py -x` | src/skyherd/scenarios/base.py ✓ | planned |
| P1-02-T1 | 02 | 2 | ROUT-02, ROUT-03, ROUT-04 | T-01-08 | Routing-table assertions catch silent drift | unit + integration + suite (RED phase) | `uv run pytest tests/scenarios/test_base.py::TestDemoMesh::test_routing_table_thermal_anomaly tests/scenarios/test_base.py::TestDemoMesh::test_routing_table_nightly_analysis tests/scenarios/test_rustling.py::TestRustlingScenarioIntegration::test_predator_pattern_learner_dispatched tests/scenarios/test_run_all.py::TestRunAll::test_every_agent_dispatched_at_least_once_across_suite --tb=no` | tests/scenarios/test_base.py ✓ tests/scenarios/test_rustling.py ✓ tests/scenarios/test_run_all.py ✓ | planned |
| P1-02-T2 | 02 | 2 | ROUT-02, ROUT-03, ROUT-04 | T-01-06, T-01-07 | Routing fan-out documented + commented | unit + integration + scenario regression (GREEN phase) | `uv run pytest tests/scenarios/test_base.py::TestDemoMesh tests/scenarios/test_rustling.py tests/scenarios/test_run_all.py tests/scenarios/ tests/agents/ --tb=short` | src/skyherd/scenarios/base.py ✓ | planned |
| P1-03-T1 | 03 | 2 | MA-04 | T-01-11 | Aggregation contract pinned; events.py drift surfaces | unit (immediate GREEN) | `uv run pytest tests/agents/test_cost.py::TestRunTickLoop --tb=short` | tests/agents/test_cost.py ✓ | planned |
| P1-03-T2 | 03 | 2 | MA-05 | T-01-09, T-01-10 | Session-id is server-UUID; monkeypatch auto-revert; tmp_path teardown | unit + integration (immediate GREEN) | `uv run pytest tests/agents/test_session.py::TestCheckpointPersistence tests/agents/test_session.py tests/agents/test_cost.py --tb=short` | tests/agents/test_session.py ✓ | planned |
| Phase Gate | — | — | SCEN-02 | — | Zero-regression on 8-scenario suite | integration | `make demo SEED=42 SCENARIO=all && uv run pytest tests/ -x` | Makefile ✓ | planned |

---

## Wave 0 Requirements

All test scaffolds are created inside the TDD flow of each plan (RED task before GREEN task). No separate pre-wave setup is required:

- [x] `tests/scenarios/test_base.py::TestDemoMesh` — added in P1-01-T1 (RED).
- [x] `tests/scenarios/test_coyote.py::test_creates_at_most_five_sessions` — added in P1-01-T1 (RED).
- [x] `tests/scenarios/test_base.py::TestDemoMesh::test_routing_table_*` — added in P1-02-T1 (RED).
- [x] `tests/scenarios/test_rustling.py::test_predator_pattern_learner_dispatched` — added in P1-02-T1 (RED).
- [x] `tests/scenarios/test_run_all.py::test_every_agent_dispatched_at_least_once_across_suite` — added in P1-02-T1 (RED).
- [x] `tests/agents/test_cost.py::TestRunTickLoop::test_all_sessions_idle_emits_zero_rate` (+2 more) — added in P1-03-T1 (immediate GREEN — aggregation contract doc).
- [x] `tests/agents/test_session.py::TestCheckpointPersistence` — added in P1-03-T2 (immediate GREEN — MA-05 contract doc).

No dedicated `tests/agents/test_session_registry.py` file needed — assertions land inside existing `tests/scenarios/test_base.py` per the PATTERNS.md role-match.
No dedicated `tests/scenarios/test_routing.py` file needed — routing table assertions land in `tests/scenarios/test_base.py::TestDemoMesh` alongside the registry assertions.
No shared `counting_session_manager` fixture needed — `monkeypatch.setattr` per-test is cleaner for the single-use coyote counter.

---

## Manual-Only Verifications

*None — all Phase 1 behaviors have automated verification per the per-task map above.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands or explicit Wave 0 dependencies (all inline in the RED task).
- [x] Sampling continuity: every task has a dedicated automated verify; no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all MISSING references (test files exist; new classes/methods created inline in RED tasks).
- [x] No watch-mode flags (pytest runs in single-shot mode).
- [x] Feedback latency < 60s per task (coyote scenario + test_base.py completes in <10s).
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** ready for execution.
