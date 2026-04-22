# Testing Patterns

**Analysis Date:** 2026-04-22

## Test Framework

**Runner:** pytest 9.0.3 (Python 3.13.11 runtime)
- Config: `pyproject.toml` — `[tool.pytest.ini_options]`
- `asyncio_mode = "auto"` — all async test functions run automatically, no decorator needed
- `testpaths = ["tests"]`
- `pythonpath = ["src"]`
- `--tb=short` added to all runs
- Slow tests marked with `@pytest.mark.slow` (1 test uses it: `tests/test_determinism_e2e.py:60`)

**Async Plugin:** pytest-asyncio 0.24+

**Coverage:** pytest-cov with `fail_under = 80`

**Frontend Runner:** Vitest 3.2.3 + jsdom
- Config: `web/vite.config.ts` `[test]` section
- Setup: `web/src/test-setup.ts` (just `import "@testing-library/jest-dom"`)
- Testing Library: `@testing-library/react` 16.x + `@testing-library/user-event` 14.x

**Run Commands:**
```bash
uv run pytest                                    # all tests, no coverage
uv run pytest --cov=src/skyherd --cov-report=term  # with coverage
uv run pytest -m "not slow"                      # skip slow E2E
make test                                        # full pytest suite with coverage
make ci                                          # lint + typecheck + test
cd web && pnpm test:run                          # frontend vitest (one-shot)
cd web && pnpm test                              # frontend vitest (watch)
```

## Actual Test Count

**Claimed in CLAUDE.md:** "880+ tests"
**Actual collected:** 1119 tests (as of 2026-04-22)
**Actual passing:** 1106 passed, 13 skipped, 0 failed, 2 warnings
- Skipped tests: `tests/drone/test_sitl_e2e.py` (6 skipped), `tests/drone/test_sitl_smoke.py` (5 skipped), `tests/scenarios/test_coyote_with_sitl.py` (2 skipped) — all require real SITL or ANTHROPIC_API_KEY
- **Frontend:** 38 tests across 5 test files, all passing

**Total test functions (grep count):** 404 `def test_` / `async def test_` functions — the remainder comes from class-based test grouping (pytest collects methods).

## Actual Coverage

**Claimed:** 80%+ target
**Actual measured:** **87.42%** total — target is met

Coverage was run as: `uv run pytest --cov=src/skyherd --cov-report=term`

### Files at 100% coverage
- `src/skyherd/scenarios/calving.py`, `coyote.py`, `rustling.py`, `sick_cow.py`, `storm.py`, `water_drop.py`, `wildfire.py`
- `src/skyherd/vision/pipeline.py`, `registry.py`, `result.py`
- All 7 vision heads: `bcs.py`, `brd.py`, `foot_rot.py`, `heat_stress.py`, `lsd.py`, `pinkeye.py`, `screwworm.py`
- `src/skyherd/voice/tts.py`
- `src/skyherd/world/clock.py`, `predators.py`, `world.py`, `weather.py`
- `src/skyherd/sensors/registry.py`, `thermal.py`, `weather.py`

### Files with notable coverage gaps (below 85%)
| File | Coverage | Missing lines |
|------|----------|---------------|
| `src/skyherd/drone/e2e.py` | **0%** | 24–225 (all) |
| `src/skyherd/edge/cli.py` | **0%** | 11–79 (all) |
| `src/skyherd/agents/cost.py` | 78% | 165-170, 174-177, 187, 191, 205-216 |
| `src/skyherd/agents/mesh.py` | 78% | 155-156, 198-200, 224-253 |
| `src/skyherd/sensors/__init__.py` | 67% | 31-35 |
| `src/skyherd/obs/tracing.py` | 34% | 32-60, 78-82 |
| `src/skyherd/server/events.py` | 76% | 293-402 (SSE event dispatch paths) |

### Coverage omissions (configured in pyproject.toml)
These files are excluded from the coverage report entirely:
- `src/skyherd/drone/pymavlink_backend.py` — requires physical drone/SITL
- `src/skyherd/drone/sitl.py` — requires running ArduPilot SITL
- `src/skyherd/drone/sitl_emulator.py` — hardware-only
- `src/skyherd/demo/hardware_only.py` — requires physical sensors
- `src/skyherd/agents/cli.py` — CLI entry-point tested via subprocess

## Test Directory Structure

Tests mirror source exactly — every source subdirectory has a corresponding `tests/` subdirectory:

```
tests/
├── agents/           # agent session, mesh, fenceline, herd-health, cost, webhook
├── attest/           # ledger, signer, CLI
├── demo/             # demo CLI, fallback sim, hardware demo flow, overrides
├── drone/            # interface, safety, stub, mavic, F3/iNav, SITL e2e (skipped)
├── edge/             # camera, fleet, heartbeat, watcher
├── hardware/         # decode_payload, mavic_protocol
├── mcp/              # drone_mcp, galileo_mcp, rancher_mcp, sensor_mcp, wiring
├── obs/              # metrics, server_metrics
├── scenarios/        # one test file per scenario + base, CLI, determinism, run_all
├── sensors/          # per-sensor + bus_persistent (integration)
├── server/           # app, app_coverage, CLI, events
├── vision/           # pipeline, registry, renderer, annotate, all 7 heads
├── voice/            # call, CLI, get_backend, humanize, tts, wes
├── world/            # cattle/herd, clock, determinism, predators, weather, CLI
├── conftest.py files # obs, sensors, scenarios, vision — shared fixtures
├── test_smoke.py     # top-level smoke test
└── test_determinism_e2e.py  # slow E2E determinism test
```

Frontend tests are co-located:
```
web/src/components/
├── AgentLane.test.tsx
├── AttestationPanel.test.tsx
├── CostTicker.test.tsx
├── CrossRanchView.test.tsx
└── RanchMap.test.tsx
```

## Test Structure Patterns

**Python — class-based grouping:**
```python
# tests/agents/test_fenceline.py
class TestFencelineDispatcherSpec:
    def test_name(self):
        assert FENCELINE_DISPATCHER_SPEC.name == "FenceLineDispatcher"

class TestFencelineSimulateHandler:
    def _fence_event(self) -> dict:  # private helper method
        return {"topic": "skyherd/ranch_a/fence/seg_1", "type": "fence.breach", ...}

    def test_returns_list(self):
        session = _make_session()
        calls = _simulate_handler(self._fence_event(), session)
        assert isinstance(calls, list)
```

**Python — async tests (no decorator needed with asyncio_mode=auto):**
```python
# tests/agents/test_fenceline.py:96-109
class TestFencelineHandlerAsync:
    async def test_handler_no_api_key_uses_simulation(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        session = _make_session()
        calls = await handler(session, event, sdk_client=None)
        assert isinstance(calls, list)
```

**Python — module-level factory functions:**
```python
# tests/agents/test_fenceline.py:13-15
def _make_session() -> Session:
    mgr = SessionManager()
    return mgr.create_session(FENCELINE_DISPATCHER_SPEC)
```

**Python — direct assertions without AAA comments (no enforce):**
```python
# tests/world/test_weather.py
class TestScheduledStorm:
    def test_storm_fires_at_exact_tick(self):
        # arrange inline, no label
        w = WeatherDriver(scheduled_storm=ScheduledStorm(...))
        result = w.step(tick=0, dt=5.0)
        assert result.active is True
```

## Fixtures and Conftest

**`tests/sensors/conftest.py`** — most complete fixture set:
- `MockBus` class: in-memory MQTT bus replacement; captures all published payloads by topic
- `world` fixture: deterministic `World` from `ranch_a.yaml` with seed=42, 50 cows
- `mock_bus` fixture: fresh `MockBus` instance

**`tests/scenarios/conftest.py`:**
- `scenarios_snapshot` autouse fixture: snapshots/restores `SCENARIOS` dict to prevent cross-test pollution

**`tests/obs/conftest.py`** and **`tests/vision/conftest.py`**: minimal per-subsystem fixtures

**No shared top-level conftest** — each subsystem has its own, preventing implicit global dependencies.

## Mocking Patterns

**Python — monkeypatch for env vars:**
```python
monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
monkeypatch.setenv("SKYHERD_AGENTS", "managed")
```

**Python — MockBus (in-memory):**
```python
# tests/sensors/conftest.py:33-57
class MockBus:
    async def publish(self, topic, payload, qos=0, ledger=None) -> None:
        self.published[topic].append(payload)
    def all_kinds(self) -> list[str]: ...
```

**Frontend — vi.mock + vi.stubGlobal:**
```typescript
// tests/components/AttestationPanel.test.tsx:6-23
vi.stubGlobal("fetch", vi.fn().mockResolvedValue({...}));
vi.mock("@/lib/sse", () => ({
  getSSE: () => ({ on: ..., off: ... }),
}));
```

**Frontend — SSE event simulation helper:**
```typescript
function triggerSSE(eventType: string, payload: unknown) {
  (sseHandlers[eventType] ?? []).forEach((h) => h(payload));
}
```

## Test Types Breakdown

**Unit tests (~70%):** All sensor tick tests, world model tests, agent spec tests, vision head tests, voice TTS tests, attest ledger/signer tests. Use MockBus or direct class instantiation.

**Integration/simulation tests (~25%):** Scenario tests drive the full simulation path — world + sensors + agents + attestation — without a real API key. `tests/scenarios/test_coyote.py`, `test_sick_cow.py`, etc.

**E2E tests (currently skipped, ~5%):**
- `tests/drone/test_sitl_e2e.py` — 6 tests skipped (requires running ArduPilot SITL)
- `tests/drone/test_sitl_smoke.py` — 5 tests skipped (same reason)
- `tests/scenarios/test_coyote_with_sitl.py` — 2 tests skipped
- `tests/test_determinism_e2e.py` — marked `@pytest.mark.slow`; runs if not filtered

**No Playwright E2E** for the frontend — only Vitest component tests.

## Frontend Testing Detail

**38 tests across 5 files, all passing:**
- `AgentLane.test.tsx` — 12 tests: render, state chips, event display, AGENT_SHORT mapping
- `AttestationPanel.test.tsx` — 9 tests: SSE integration, entry rendering, expand/collapse
- `CostTicker.test.tsx` — 6 tests: idle/active states, cost display
- `CrossRanchView.test.tsx` — 7 tests: render, SSE cost events
- `RanchMap.test.tsx` — 4 tests: render, basic props

**Pattern:** `describe` + `it` (Vitest globals), `beforeEach` to reset mocks, `act` wrapping for async renders.

**No coverage target enforced** for frontend — vitest coverage provider `v8` is configured but `fail_under` not set.

## CI Pipeline

`make ci` runs: `ruff check src/ tests/` → `pyright src/` → `pytest --cov` (in that order).

Current status:
- ruff: 1 fixable error (unsorted import)
- pyright: 15 errors in hardware-specific files (drone/pymavlink, drone/sitl_emulator)
- pytest: 1106 passed, 13 skipped, 87.42% coverage — gate passed

---

*Testing analysis: 2026-04-22*
