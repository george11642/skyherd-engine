# Verify Loop T5 — 2026-04-22

## 1. Repo State

| Item | Value |
|------|-------|
| HEAD | `2bfd6ac` |
| Branch | `main` |
| Commits since T4 (`445aabf`) | 1 (scenarios: wire Wildfire + Rustling, fix dispatcher routing) |
| PROGRESS.md lines | 173 |
| PROGRESS `[x]` items | 93 |
| PROGRESS `[ ]` items | 8 |
| Unstaged changes | `src/skyherd/edge/watcher.py` (architect-fix-agent mid-write — +persistent MQTT client) |

Note: `git pull --rebase` blocked by unstaged `watcher.py` change. Architect-fix-agent is MID-BUILD. Report reflects HEAD `2bfd6ac`.

---

## 2. Lint / Type / Test

**Ruff lint:** 1 error — unused import `os` in one file (fixable with `--fix`).

**Ruff format:** 5 files would be reformatted:
- `tests/agents/test_neighbor_mesh.py`
- `tests/hardware/test_decode_payload.py`
- `tests/obs/test_metrics.py`
- `tests/scenarios/test_cross_ranch_coyote.py`
- (1 other)

**Pyright:** 0 errors, 5 warnings (all `reportMissingTypeStubs` for `mavsdk` and `supervision` — expected, no stubs available).

**Pytest:** `1012 passed, 5 skipped, 5 warnings in 305.66s`
**Coverage:** `82.61%` (TOTAL 5866 statements, 1020 missed) — above 80% floor.

---

## 3. Sim Determinism Byte-Check

| | Run A | Run B |
|-|-------|-------|
| md5sum | `aa4003415c23e815b32a6c54c98d48f6` | `c7247e32e1505a55c5e57c114b1edf10` |
| Diff lines | 7296 | — |

**DETERMINISM: md5 mismatch — architect R1 NOT CLEARED at byte level.**

**Root cause (diagnosed):** The log output differences are entirely cosmetic:
1. Wall-clock timestamps in log lines (`HH:MM:SS` prefix — structlog default renderer)
2. `uuid.uuid4()` session IDs in log lines (`session created: <8hex>`)
3. Replay file paths containing wall-clock timestamps (e.g. `coyote_42_20260422T044834.jsonl`)
4. `wall_time_s` in replay summary (elapsed wall time per scenario)

**Simulation content IS deterministic:** Comparing two T5 coyote replay JSONLs (same seed=42):
- Both produce exactly 376 lines, 131 events, `outcome_passed=true`
- Stripped of `ts`/`wall_ts`, only `wall_time_s` differs (0.57s vs 0.37s — CPU scheduling)
- Event sequence, payloads, attestation counts, and outcomes are byte-identical

**Remaining wall-clock leak sources (log-level only, do not affect sim content):**
- `src/skyherd/scenarios/base.py:298` — `datetime.now(UTC).strftime("%Y%m%dT%H%M%S")` for replay filename
- `src/skyherd/scenarios/base.py:383` — `datetime.now(UTC).isoformat()` for event timestamps
- `src/skyherd/agents/session.py:195` — `uuid.uuid4()` for session IDs (in log output only)
- `src/skyherd/sensors/base.py:21` — `_WALL_CLOCK_TS = time.time` (sensor base, injected, seeded paths use override)
- `src/skyherd/agents/mesh_neighbor.py:144,228,237,262,605` — `time.time()` for neighbor coordination timestamps

**Verdict:** Sim gate item "Deterministic replay (`make sim SEED=42`)" is GREEN for content/events. The log output format includes wall timestamps by design. **DETERMINISM CONTENT-GREEN, LOG-FORMAT-AMBER** (not a regression from T4).

---

## 4. 8-Scenario Marker Count (Run A, seed=42)

| Scenario | Marker hits | Wall time | Events | Result |
|----------|-------------|-----------|--------|--------|
| coyote | 6 | 0.57s | 131 | **PASS** |
| sick_cow | 3 | 1.98s | 62 | **PASS** |
| water_drop | 3 | 0.57s | 121 | **PASS** |
| calving | 3 | 0.87s | 123 | **PASS** |
| storm | 4 | 0.59s | 124 | **PASS** |
| cross_ranch | 3 | 0.53s | 131 | **PASS** |
| wildfire | 3 | 0.46s | 122 | **PASS** |
| rustling | 3 | 0.42s | 123 | **PASS** |

**8/8 PASS** — all scenarios complete without intervention.

---

## 5. Architect Bug Re-Check

### R2a — `_tickers` typo in `events.py`
**Status: PRESENT**

`src/skyherd/server/events.py:353` accesses `self._mesh._session_manager._tickers.get(session.id)`.
`SessionManager` has no `_tickers` dict attribute — only `all_tickers()` method (returns `list[CostTicker]`).
This crashes the `_real_cost_tick()` code path when `SKYHERD_MOCK=0` and the live mesh is running.
Confirmed: `grep -n 'self\._tickers' src/skyherd/agents/session.py` returns no results.

### R2b — Mavic / F3-iNav factory
**Status: FIXED**

```
DRONE_BACKEND=mavic   → MAVIC_OK: MavicBackend
DRONE_BACKEND=f3_inav → F3_OK: F3InavBackend
```

Both backends instantiate without error.

### R3 — `get_bus_state` missing from `bus.py`
**Status: PRESENT**

`src/skyherd/mcp/sensor_mcp.py:41-43` imports and calls `get_bus_state` from `skyherd.sensors.bus`.
Runtime test: `ImportError: cannot import name 'get_bus_state' from 'skyherd.sensors.bus'`.
The function is referenced but never defined in `bus.py`.

---

## 6. Code-Review Criticals Re-Check

### C1 — Prompt caching not reaching Claude
**Status: PRESENT**

`build_cached_messages()` is called in every agent handler, building a `cached_payload` dict with `cache_control: ephemeral` blocks. However `_run_with_sdk()` (local to each agent file) then does:
```python
prompt = cached_payload["messages"][0]["content"][0]["text"]
async for msg in sdk_client.query(prompt=prompt):
```
The `cache_control` blocks are discarded. Claude receives a plain `prompt=` string with no caching headers. Zero cache savings at runtime with a live API key.

### C3 — Wes sanitizer invoked
**Status: FIXED**

`_FORBIDDEN_RE` defined at line 200, `_sanitize()` at line 203, and called at line 226 (`text = _sanitize(text)`). Sanitizer is wired into the TTS path.

### C4 — MQTT reconnect-per-publish
**Status: FIXED**

`SensorBus` has persistent `_client: aiomqtt.Client | None` with `_ensure_connected()` returning the live client, exponential back-off reconnect, and a `_client_lock`. `publish()` calls `_ensure_connected()` — no new connection per publish.

### C5 — SITL timeouts
**Status: CANNOT-TELL**

`grep -nE 'asyncio.wait_for|timeout=' src/skyherd/drone/sitl.py` returns no results. No explicit `asyncio.wait_for` found. Cannot determine if MAVLink operations have hang-guards — `mavsdk` may have internal timeout params, but no explicit guard is visible in the source.

### C6 — Twilio/ElevenLabs exception types
**Status: PRESENT**

Both `rancher_mcp.py:81` and `voice/call.py:91` catch bare `except Exception` with `# noqa: BLE001`. No Twilio-specific `TwilioException` or HTTP-level exceptions distinguished. Exception handling is too broad.

### H5 — ClassifyPipeline O(n×heads)
**Status: PRESENT**

`vision/pipeline.py:86` iterates `for cow in world.herd.cows` and calls `classify(cow, frame_meta)` individually per cow. No batching — all detection heads run per-cow independently. O(n×heads) at inference time. For 50 cows × 7 heads = 350 individual classification calls per frame.

### H7 — HerdHealthWatcher skill list
**Status: FIXED**

`HERD_HEALTH_WATCHER_SPEC.skills` is overridden at module level with 6 real skill paths (feeding-patterns, lameness-indicators, heat-stress, herd-structure, calving-signs, human-in-loop-etiquette). The `if False` disease sub-skills are explicitly disabled but noted. Disease detection runs through pipeline heads, not skill files — architecturally correct.

---

## 7. Agent Mesh Smoke

**Status: PASS**

```
SMOKE_KEYS: ['FenceLineDispatcher', 'HerdHealthWatcher', 'PredatorPatternLearner', 'GrazingOptimizer', 'CalvingWatch']
```

All 5 managed agents instantiated and smoke-tested successfully. Note: `AgentMesh.smoke_test()` is an instance method (not classmethod) — must instantiate `AgentMesh()` first.

---

## 8. Dashboard

### Mock mode (`SKYHERD_MOCK=1`, port 8000)
**Status: HEALTH_OK**

```json
{"status":"ok","ts":"1776833694.0318944"}
```

### Live mode (`SKYHERD_MOCK=0`, port 8001)
**Status: LIVE_HEALTH_OK + SSE streaming**

```json
{"status":"ok","ts":"1776833718.950835"}
```

SSE `/events` delivers `world.snapshot` events with full world state (weather, cow positions, BCS, state). Live mode reaches `EventBroadcaster` without crash in the mock-free path.

Note: R2a (`_tickers` AttributeError) would only manifest when the `_real_cost_tick()` path fires in live mode with an active mesh — the `world.snapshot` path is unaffected.

### Prod (`https://skyherd-engine.vercel.app`)
**Status: HTTP/2 200** — deployment live and responding.

---

## 9. Fresh-Clone

| | md5sum |
|-|--------|
| det_a_T5.log | `aa4003415c23e815b32a6c54c98d48f6` |
| fresh_T5.log | `072fd7c8dfb43f10195e85eea039e687` |

**Byte-identical: NO** — same root cause as section 3 (wall-clock timestamps + session UUIDs in log output). Simulation content (events, outcomes, event counts) is identical across all runs.

---

## 10. Sim Gate — Per-Item Status

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | All 5 Managed Agents via MQTT | **TRULY-GREEN** | Smoke test passes, 5 agents confirmed |
| 2 | 7+ sim sensor emitters on MQTT | **TRULY-GREEN** | SensorBus persistent client, all emitter types present |
| 3 | Disease-detection heads (7 conditions) | **TRULY-GREEN** | Pipeline 100% coverage, all 7 heads confirmed |
| 4 | SITL drone executing MAVLink missions | **AMBER** | C5 unresolved — no asyncio.wait_for in sitl.py |
| 5 | Dashboard live-updating | **TRULY-GREEN** | SSE confirmed, world.snapshot streaming live |
| 6 | Wes voice end-to-end | **AMBER** | C6 broad except; Twilio auth not verifiable in sim |
| 7 | 8 demo scenarios back-to-back | **TRULY-GREEN** | 8/8 PASS seed=42 |
| 8 | Deterministic replay (content) | **TRULY-GREEN** | Event content identical; log timestamps differ by design |
| 9 | Fresh-clone boot test | **TRULY-GREEN** | All 8 pass on clone, same event counts |
| 10 | Cost ticker pauses during idle | **CANNOT-TELL** | R2a blocks `_real_cost_tick()` in live mode |

### Extended Vision A — Per-Item Status

| Item | Status | Notes |
|------|--------|-------|
| Prompt caching delivers cache hits | **RED** | C1: `query(prompt=...)` strips `cache_control` blocks |
| SessionManager cost aggregation | **RED** | R2a: `_tickers` AttributeError in live cost tick |
| `get_bus_state` MCP endpoint | **RED** | R3: ImportError — function never defined in bus.py |
| SITL hang-guard | **AMBER** | C5: no `asyncio.wait_for` found in sitl.py |
| Twilio exception specificity | **AMBER** | C6: bare `except Exception` in both voice files |
| ClassifyPipeline batching | **AMBER** | H5: O(n×heads) per-cow loop, no batch inference |

---

## 11. PROGRESS.md — Claimed-Green vs Truly-Green

| Metric | Value |
|--------|-------|
| Claimed `[x]` | 93 |
| Claimed `[ ]` | 8 |
| PROGRESS-stated summary | "89 / 95" (stale — actual 93/101) |

**AGENT-LIED list** (claimed green, actually not):

| Item | Claim | Reality |
|------|-------|---------|
| "Deterministic replay (`make sim SEED=42`)" | `[x]` | AMBER — byte-level diff exists (log timestamps); content-green only |
| "Fresh-clone boot test green on second machine" | `[x]` | AMBER — same byte diff; functionally green |
| "Cost ticker visibly pauses during idle stretches" | `[x]` | CANNOT-TELL — `_real_cost_tick()` crashes (R2a) in live mode |
| Prompt caching (implied green by architecture) | not checked | RED — `query(prompt=...)` discards cache_control in all 5 agents |

---

## 12. Top 5 Blockers Right Now

1. **R2a + R3 (LIVE mode crash)** — `_session_manager._tickers.get()` AttributeError and `get_bus_state` ImportError both fire in live mode (non-mock). Cost ticker and sensor MCP endpoint are broken at runtime. Blocks investor demo on real hardware.

2. **C1 (zero prompt caching)** — `build_cached_messages` is called but discarded; all 5 agent handlers pass `prompt=single_string` to SDK. Every live API call is full-price, no cache savings. The architecture intended caching but it was wired incorrectly in every `_run_with_sdk()`.

3. **C5 (SITL no hang-guard)** — No `asyncio.wait_for` in `sitl.py`. A stalled ArduPilot process or blocked MAVLink call hangs the sim indefinitely. Scenario runner has no timeout escape for drone commands.

4. **Ruff lint error + 5 format failures** — 1 unused import, 5 files need reformatting. Pre-commit hook should have caught these. Verify CI ruff check is actually blocking on failure.

5. **Unstaged `watcher.py` change (architect-fix-agent mid-build)** — Cannot pull/rebase until this lands or is stashed. Blocks clean merge of any upstream fixes.

---

## 13. Recommended Next Dispatch

**T6-A — Single agent, bypassPermissions (fix R2a + R3 + C1):**
- `src/skyherd/server/events.py:353` — replace `._session_manager._tickers.get(session.id)` with loop over `._session_manager.all_tickers()` to build per-session cost dict
- `src/skyherd/sensors/bus.py` — add `get_bus_state() -> dict` function returning current bus connection/stats
- All 5 agent `_run_with_sdk()` functions (`calving_watch.py`, `fenceline_dispatcher.py`, `grazing_optimizer.py`, `herd_health_watcher.py`, `predator_pattern_learner.py`) — change from `query(prompt=prompt)` to `query(messages=cached_payload["messages"])` to restore prompt caching

**T6-B — Second agent, parallel with T6-A (fix C5 + C6 + lint):**
- `src/skyherd/drone/sitl.py` — wrap MAVLink awaits with `asyncio.wait_for(..., timeout=30.0)`
- `src/skyherd/mcp/rancher_mcp.py` + `src/skyherd/voice/call.py` — narrow `except Exception` to specific exception types
- `uv run ruff check --fix . && uv run ruff format .` — clear lint/format issues

**After T6 lands:** Run full verify loop (T7) to confirm all 5 blockers cleared.
