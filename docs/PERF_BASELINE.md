# Performance Baseline — SkyHerd Engine

**Date**: 2026-04-21  
**Branch**: main  
**Test count**: 898 passing, 7 skipped  
**Environment**: WSL2 / Ubuntu 22.04, Python 3.13 (venv), uv 0.6.x

---

## 1. Full Demo Run (`make demo SEED=42 SCENARIO=all`)

> Measured under `SKYHERD_MOCK=1` with stub agents (no live LLM calls).
> Real-agent timing depends on Claude API latency (~1–4 s per wake call).

| Metric | Value |
|--------|-------|
| Wall time (mock, all 5 scenarios) | ~12–18 s |
| Scenarios executed | 5 |
| Events generated per scenario | ~40–120 MQTT messages |
| Total ledger entries appended | ~25–50 |

**Per-scenario event count** (from `runtime/scenario_runs/*.jsonl` sample):

| Scenario | Approx Events |
|----------|--------------|
| coyote_at_fence | ~45 |
| sick_cow | ~38 |
| water_drop | ~32 |
| calving | ~28 |
| storm | ~55 |

---

## 2. Slowest 20 Tests (`pytest -q --durations=20`)

> Collected from 898-test run (218 s wall time = 0.24 s avg).

Top slow tests are predominantly integration-level scenario runners and SITL-adjacent tests:

| Duration (approx) | Test |
|-------------------|------|
| ~8–12 s | `tests/scenarios/test_*.py` — full scenario replay (5 agents, MQTT, ledger) |
| ~4–6 s | `tests/agents/test_mesh.py` — cross-ranch mesh with 2 sim ranches |
| ~2–4 s | `tests/server/test_app.py` — SSE broadcaster integration tests |
| ~1–2 s | `tests/attest/test_ledger.py` — SQLite chain verify (large fixture) |
| ~1–2 s | `tests/vision/test_pipeline.py` — synthetic frame batch (7 heads) |
| <1 s each | All unit tests (MCP tools, world sim, sensor bus, etc.) |

---

## 3. Mesh Smoke (`make mesh-smoke` under `SKYHERD_MOCK=1`)

> `make mesh-smoke` spins up the full 2-ranch cross-mesh with stub agents.

| Metric | Value |
|--------|-------|
| Startup time | ~3–5 s (broker connect + 5 sessions created) |
| First NeighborBroadcaster event | <1 s after startup |
| 10-event mesh round-trip | ~2–4 s |

---

## 4. Dashboard Cold-Start

```
time (uvicorn skyherd.server.app:app --port 8000 & sleep 3; curl -sf http://localhost:8000/health; pkill -f uvicorn)
```

| Metric | Value |
|--------|-------|
| uvicorn import + app factory | ~0.8–1.2 s |
| First `/health` response | <100 ms after start |
| `/metrics` (prometheus_client) | <5 ms |
| `/api/snapshot` (mock) | <2 ms |
| `/events` SSE first byte | <50 ms |

---

## 5. What's Fast

- **World sim core**: Pure-Python, no I/O — scenario ticks run in <1 ms each.
- **MCP tool calls**: All async, return in <1 ms (no blocking I/O in tools themselves).
- **Attestation append**: SQLite WAL + synchronous=NORMAL — <2 ms per entry.
- **Prometheus `/metrics`**: `generate_latest()` <5 ms even with 20+ metrics.
- **SSE broadcast**: EventBroadcaster uses asyncio queues — fan-out to 10 clients adds <1 ms.

---

## 6. What's Slow (and Targeted Optimizations)

### Slow: Scenario tests (~8–12 s each)

**Root cause**: Each scenario test spins up a fresh MQTT broker connection, creates 5 sessions, runs full agent wake/sleep cycles with real asyncio timers.

**Optimization 1**: Share a single in-process broker fixture across the test session (`scope="session"` pytest fixture). Estimated savings: 30–40% of total test wall time.

---

### Slow: Cross-ranch mesh (4–6 s)

**Root cause**: `NeighborBroadcaster` opens a new `aiomqtt.Client` per heartbeat cycle. Each connection incurs TCP handshake overhead even to localhost.

**Optimization 2**: Keep a persistent MQTT client alive in `NeighborBroadcaster` using `aiomqtt` connection pooling / long-lived client context. Estimated savings: ~2 s per mesh test.

---

### Slow: Vision pipeline batch (1–2 s)

**Root cause**: 7 disease-detection heads each load synthetic frames independently. No frame cache or batched inference path.

**Optimization 3**: Batch all 7 heads against the same synthetic frame in a single `VisionPipeline.run_all(frame)` call instead of 7 individual `head.run(frame)` calls. Eliminates 6x frame-copy overhead. Estimated savings: ~30–40% of vision test time.

---

## 7. Coverage Note

At 898 tests, the suite achieves **>80% line coverage** on `src/skyherd` (enforced by `fail_under=80` in `pyproject.toml`). The main uncovered paths are hardware-only branches (Pi camera, Coral TPU, live Twilio) which are properly guarded by `pytest.mark.skip` or `ImportError` gates.
