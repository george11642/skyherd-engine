# Verify Loop T6 — 20260422-053000

Generated: 2026-04-22T05:30:00Z  
Loop tag: **T6**  
Operator: verify-loop-T6

---

## 1. Repo State

| Item | Value |
|------|-------|
| HEAD | `291e4105f8088af02210eb344df2b99c371c66cd` |
| Commit on top | `fix(agents): HerdHealthWatcher skills include 7 disease + behavior + ranch-ops (H7)` |
| Total commits | 50 |
| PROGRESS.md `[x]` | 92 |
| PROGRESS.md `[ ]` | 8 |

**Recent 5 commits:**
```
291e410 fix(agents): HerdHealthWatcher skills include 7 disease + behavior + ranch-ops (H7)
0ebd8c6 perf(vision): gate disease heads with should_evaluate() + vectorize numpy loops (H5, H-10)
aec3730 fix(mcp,voice): narrow Twilio/ElevenLabs exception handling (C6)
8878e3c fix(drone): asyncio.wait_for on every SITL await + DroneTimeoutError (C5)
8266382 fix(edge): persistent aiomqtt client on edge watcher (C4)
```

Pull rebase status: clean (stash-pop required for one unstaged file in `tests/`).

---

## 2. Lint / Type / Test

### ruff check
```
Found 1 error.
[*] 1 fixable with the --fix option.
```
**Verdict: FAIL** — 1 lint error (unused import `os` in a test file). Fixable with `ruff --fix`.

### ruff format --check
```
9 files would be reformatted, 196 files already formatted
```
**Verdict: FAIL** — 9 test files need formatting. No src/ files affected.

Files needing format:
- `tests/obs/test_metrics.py`
- `tests/scenarios/test_cross_ranch_coyote.py`
- `tests/sensors/test_bus_persistent.py`
- `tests/voice/test_wes.py`
- (5 more)

### pyright
```
0 errors, 5 warnings, 0 informations
```
**Verdict: PASS** — 5 warnings are all `reportMissingTypeStubs` for `mavsdk` and `supervision` (expected, no stubs available).

### pytest + coverage
```
1033 passed, 5 skipped, 5 warnings in 112.30s
Total coverage: 82.09% (required 80.0%) PASS
```
**Verdict: PASS** — 1033/1038 green, coverage 82.09% (floor 80%).

---

## 3. Determinism

### Raw md5sum (includes wall-clock timestamps)
```
92972212eede641f6892395a83ffdf13  /tmp/det_a_T6.log
69938ea629590e242c90c15008b55f6e  /tmp/det_b_T6.log
```
Raw hashes DIFFER (expected — HH:MM:SS timestamps and wall durations differ between runs).

### Content-sanitized comparison (ISO timestamps + HH:MM:SS + UUIDs + 8-char session IDs + wall-clock durations removed)

After full sanitization, Python-level diff shows **0 content differences**. All 8 remaining
diff lines in the summary table are wall-clock timing fields `(X.XXs wall, N events)` — event
counts are identical in all 8 scenarios.

**Verdict: CONTENT_DETERMINISTIC** — seed=42 produces identical event streams, scenario
results, and message content on repeated runs.

---

## 4. 8-Scenario Markers

All 8/8 scenarios PASS on `skyherd-demo play all --seed 42`:

| Scenario | Result | Events | Wall time |
|----------|--------|--------|-----------|
| coyote | PASS | 131 | 0.31s |
| sick_cow | PASS | 62 | 1.06s |
| water_drop | PASS | 121 | 0.24s |
| calving | PASS | 123 | 0.27s |
| storm | PASS | 124 | 0.28s |
| cross_ranch_coyote | PASS | 131 | 0.37s |
| wildfire | PASS | 122 | 0.32s |
| rustling | PASS | 123 | 0.35s |

**Verdict: 8/8 PASS**

---

## 5. Architect Bugs Status

| Bug | Location | Status |
|-----|----------|--------|
| `_tickers` private attribute access | `server/events.py:353` | **PRESENT** — `self._mesh._session_manager._tickers.get(session.id)` still uses private `_tickers` dict |
| DRONE_BACKEND=mavic dispatch | `drone/interface.py` | **FIXED** — returns `MavicBackend` |
| DRONE_BACKEND=f3_inav dispatch | `drone/interface.py` | **FIXED** — returns `F3InavBackend` |
| `get_bus_state` missing from bus.py | `sensors/bus.py` | **PRESENT** — `sensor_mcp.py:41` imports `get_bus_state` from `bus.py` but function does not exist there; import is guarded by `type: ignore[import]` but will fail at runtime if the MCP tool is invoked |

---

## 6. Code-Review CRITICALS Status

| ID | Location | Description | Status |
|----|----------|-------------|--------|
| **C1** | `agents/*.py` | Prompt caching: `query(prompt=str)` instead of `query(messages=[...])` with `cache_control` blocks | **PRESENT** — all 5 agents still call `sdk_client.query(prompt=prompt)`. `build_cached_messages` helper exists but is not wired to the query call. |
| **C3** | `voice/wes.py` | `_FORBIDDEN_RE` sanitizer invoked on output | **FIXED** — `_sanitize()` defined at line 219, invoked at line 252 before TTS output |
| **C4** | `sensors/bus.py` | MQTT persistent client (not per-publish reconnect) | **FIXED** — `_client: aiomqtt.Client | None` + `_ensure_connected()` + `_client_lock` present |
| **C5** | `drone/sitl.py` | SITL ops wrapped in `asyncio.wait_for` + `DroneTimeoutError` | **FIXED** — all SITL awaits wrapped; `DroneTimeoutError` raised on timeout |
| **C6** | `mcp/rancher_mcp.py`, `voice/call.py` | Narrow exceptions (not bare `except Exception`) | **PRESENT (partial)** — 3 `except Exception as exc: # noqa: BLE001` remain. The noqa suppresses ruff but catches are still broad; true narrowing to Twilio/ElevenLabs specific exception types not completed |
| **H5** | `vision/pipeline.py`, `vision/heads/*.py` | `should_evaluate` gating before expensive classify | **FIXED** — `should_evaluate()` defined on `base.py:33`, implemented in all 7 heads (bcs, brd, foot_rot, heat_stress, lsd, pinkeye, screwworm) |
| **H7** | `agents/herd_health_watcher.py` | HerdHealthWatcher loads disease skills | **FIXED** — 7 disease skills loaded: pinkeye, screwworm, foot-rot, brd, lsd, heat-stress-disease, bcs |
| **C-01** | `agents/session.py` | `hashlib.sha256` for prompt cache hash | **FIXED** — `hashlib.sha256(sp_text.encode()).hexdigest()[:16]` at line 246 |
| **C-02** | `vision/renderer.py` | Insecure `tempfile.mktemp()` usage | **PRESENT** — 3 occurrences of `Path(tempfile.mktemp(suffix=".png"))` at lines 130, 206, 286. Should be `tempfile.mkstemp()` or `NamedTemporaryFile(delete=False)` |
| **H-05** | `agents/mesh.py` | Fire-and-forget tasks retained in `_inflight_handlers` set | **FIXED** — `_inflight_handlers: set[asyncio.Task]` at line 121; `add_done_callback(self._inflight_handlers.discard)` at line 237 |
| **H-10** | `server/app.py:143` | `range(min(10, 50))` always returns 10, pagination broken | **PRESENT** — line 143: `entries = [_mock_attest_entry() for _ in range(min(10, 50))]`. `min(10, 50)` is always 10; `since_seq` param accepted but not respected in mock path |

**Summary: 7 FIXED, 4 PRESENT (C1, C6-partial, C-02, H-10)**

---

## 7. Agent Mesh Smoke

```python
AgentMesh().smoke_test()  # instance method, no API key needed
```

Result: **PASS** — all 5 agents returned tool calls (simulation path):
- `FenceLineDispatcher`: 4 tool calls (get_thermal_clip, launch_drone, play_deterrent, page_rancher)
- `HerdHealthWatcher`: 2 tool calls (classify_pipeline, page_rancher)
- `PredatorPatternLearner`: 2 tool calls (get_thermal_history, log_pattern_analysis)
- `GrazingOptimizer`: 2 tool calls (get_latest_readings, page_rancher)
- `CalvingWatch`: 2 tool calls (get_latest_readings, page_rancher)

**Verdict: MESH_SMOKE_OK**

Note: `smoke_test` is an instance method — must call as `AgentMesh().smoke_test()`, not `AgentMesh.smoke_test()`.

---

## 8. Dashboard Live Mode (SKYHERD_MOCK=0)

```bash
SKYHERD_MOCK=0 uvicorn skyherd.server.app:app --port 8001
```

| Check | Result |
|-------|--------|
| `/health` | `{"status":"ok","ts":...}` — **LIVE_HEALTH_OK** |
| `/events` SSE stream (first 500 bytes) | `event: world.snapshot\ndata: {...cows:[...]}` — **LIVE_SSE_OK** |
| cost/ticker/error in server log | **0 matches** — no errors |

Server log (10 lines total, clean startup and shutdown):
```
INFO: Started server process
INFO: Application startup complete.
INFO: Uvicorn running on http://127.0.0.1:8001
INFO: GET /health 200 OK
INFO: GET /events 200 OK
INFO: Shutting down / Application shutdown complete.
```

**Verdict: DASHBOARD_LIVE_PASS** — SSE stream delivers real `world.snapshot` events with
cow position/state/BCS data at SKYHERD_MOCK=0. No errors in live-mode startup.

---

## 9. Fresh-Clone Content Match

```bash
git clone /home/george/projects/active/skyherd-engine /tmp/fresh-T6
cd /tmp/fresh-T6 && uv sync && skyherd-demo play all --seed 42
```

| Check | Result |
|-------|--------|
| uv sync | OK — all deps resolved |
| demo run | OK — 8/8 PASS, 3651 log lines |
| Content diff vs det_a (sanitized) | 8 lines differ — all wall-clock durations only |
| Event counts | Identical across all 8 scenarios |
| All diffs are wall-clock only | True |

**Verdict: FRESH_CONTENT_MATCH YES** — deterministic content on a cold clone, wall-clock
timing naturally varies.

---

## 10. Sim Gate Per-Item

| Gate | Status |
|------|--------|
| SG-1: coyote scenario PASS | PASS |
| SG-2: sick_cow scenario PASS | PASS |
| SG-3: water_drop scenario PASS | PASS |
| SG-4: calving scenario PASS | PASS |
| SG-5: storm scenario PASS | PASS |
| SG-6: cross_ranch_coyote PASS | PASS |
| SG-7: wildfire PASS | PASS |
| SG-8: rustling PASS | PASS |
| SG-9: Coverage >= 80% | PASS (82.09%) |
| SG-10: Deterministic replay (seed=42) | PASS |
| SG-11: Fresh-clone boots + matches | PASS |
| SG-12: Dashboard SSE live-mode | PASS |
| SG-13: Agent mesh smoke | PASS |

**13/13 sim gates pass.**

---

## 11. Extended Vision A Per-Item

| Item | Status |
|------|--------|
| EV-A1: should_evaluate gates on all 7 heads | PASS |
| EV-A2: H7 disease skills loaded (7 skills) | PASS |
| EV-A3: Vision pipeline test coverage 100% | PASS |
| EV-A4: Renderer coverage 97% | PASS |

---

## 12. Claimed Green vs Truly Green

| Claim | Truly Green? |
|-------|-------------|
| C3 Wes sanitizer | YES |
| C4 MQTT persistent client | YES |
| C5 SITL timeouts | YES |
| C-01 sha256 | YES |
| H-05 task retention | YES |
| H7 disease skills | YES |
| H5 should_evaluate gating | YES |
| C1 prompt caching | NO — `query(prompt=)` unchanged |
| C6 narrow exceptions | PARTIAL — noqa suppression added but catches still broad |
| C-02 secure tempfile | NO — mktemp() still at 3 locations in renderer.py |
| H-10 pagination mock | NO — `min(10, 50)` still present |

**Agent-lied list: C1, C-02, H-10** (not addressed by review-fix-agent despite being in scope)

---

## 13. Top 5 Blockers

1. **C1 (CRITICAL)** — Prompt caching not wired. `sdk_client.query(prompt=str)` bypasses
   the entire `build_cached_messages` infrastructure. The pitch claims prompt caching as a
   feature; it is not functioning. Fix: thread `cached_payload` through to the query call
   using `messages=` form with `cache_control` blocks.

2. **Lint/Format (LOW but noisy)** — 1 ruff error + 9 format violations in test files.
   `uv run ruff check --fix . && uv run ruff format .` clears all in under 1 minute. Should
   run before every commit.

3. **C-02 (HIGH)** — `tempfile.mktemp()` is a TOCTOU race condition (deprecated).
   Three locations in `vision/renderer.py` (lines 130, 206, 286). Replace with
   `tempfile.NamedTemporaryFile(suffix=".png", delete=False)` or `tempfile.mkstemp()`.

4. **H-10 (MEDIUM)** — `/api/attest?since_seq=N` mock path always returns 10 entries
   ignoring `since_seq`. Replace `range(min(10, 50))` with `range(50)` and filter by
   `since_seq`.

5. **`get_bus_state` missing from `bus.py`** — `sensor_mcp.py:41` imports a function that
   does not exist. Currently guarded by `type: ignore[import]` but will raise `ImportError`
   at runtime if the sensor MCP tool is invoked. Either define the function stub in `bus.py`
   or remove the import.

---

## 14. Recommended Next Dispatch

**Immediate (pre-submission, T7 target):**
- `review-fix-agent` with bypassPermissions — fix C1 (prompt caching, wire messages= form),
  C-02 (mktemp -> mkstemp), H-10 (pagination mock), lint/format auto-fix, add `get_bus_state`
  stub to `bus.py`, true narrow C6 exception types.
- Then run T7 verify loop to confirm all PRESENT items cleared.

**Parallel:**
- `tdd-guide` agent — add `FakeSDKClient` integration tests that verify SDK path + assert
  `cache_read_input_tokens > 0` on second wake (currently zero SDK-path coverage).

**Submission copy:**
- Remove or qualify "prompt caching" claim in pitch until C1 is confirmed working with a
  real API key run showing `cache_read_input_tokens > 0`.

---

*verify-loop-T6 complete — HEAD 291e4105f8088af02210eb344df2b99c371c66cd*
