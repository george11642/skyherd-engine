# Code Review — 2026-04-21

Reviewer: senior code reviewer (Opus 4.7 1M) · Python modules in scope: `src/skyherd/**`, `tests/**`, plan v5.1 drift.
Scope: 94 Python source files, 102 test files, ~15.2k Python LOC, plus `web/` excluded (other agents active).

## Summary

- Files reviewed: 40+ Python source files across agents, sensors, drone, vision, attest, scenarios, server, voice, mcp, edge
- **CRITICAL: 6**
- **HIGH: 12**
- **MEDIUM: 14**
- **LOW: 6**

Verdict: **BLOCK** — multiple CRITICAL findings invalidate load-bearing pitch claims (prompt caching not wired, cost ticker broken in live mode, AI-telltale filter dead, MQTT publish churn). The code is lint-clean and superficially well-organised, but two of the four hackathon-headline features (prompt cache, cost ticker) are Potemkin constructions that would not pass an Anthropic judge doing `curl`-deep inspection. Sim-path functionality is broadly correct; the lying happens at the boundaries where real integration should live.

---

## CRITICAL (security, data corruption, silent failure, incorrect results, prize-losing)

### C1 — Prompt caching is built and thrown away on every wake cycle

**File**: `src/skyherd/agents/fenceline_dispatcher.py:143-171` (and same pattern in `herd_health_watcher.py:104-122`, `calving_watch.py:99-114`, `grazing_optimizer.py:92-107`, `predator_pattern_learner.py:87-102`)
**Finding**: All 5 agents call `build_cached_messages(system_prompt, skill_texts, user_message)` which produces a well-formed `{"system": [...cache_control blocks...], "messages": [...]}` payload. The return value is then indexed down to `cached_payload["messages"][0]["content"][0]["text"]` — **a single string** — and handed to `claude_agent_sdk.query(prompt=prompt)`. The system blocks with `cache_control` never reach the API. Every wake is a cold uncached send.
**Evidence**:
```python
# fenceline_dispatcher.py:143-171
cached_payload = build_cached_messages(system_prompt, skill_texts, user_message)
...
if sdk_client is not None and os.environ.get("ANTHROPIC_API_KEY"):
    tool_calls = await _run_with_sdk(sdk_client, cached_payload, session)
...
async def _run_with_sdk(sdk_client, cached_payload, session):
    ...
    prompt = cached_payload["messages"][0]["content"][0]["text"]   # <-- throw away system + skills
    async for msg in sdk_client.query(prompt=prompt):
```
**Impact**: (1) The `$5k Managed Agents` prize narrative rests on "aggressive prompt caching" — demonstrably false in the shipped code. (2) Cost ticker numbers are wrong: `CostTicker.record_api_call(cache_hit_tokens=...)` is never called because no cache reads ever happen. The dashboard cost figure is structurally incapable of reflecting cache hits. (3) Skills (the CrossBeam $50k pattern) are loaded from disk but never enter the prompt — `_load_text` reads files whose content dies in a local variable. (4) A judge who peeks at `_run_with_sdk` will see this immediately.
**Fix**: Use `ClaudeAgentOptions(system_prompt=..., ...)` from `claude_agent_sdk` — the SDK supports structured `system` blocks — or switch to the raw Anthropic Messages API and pass `system=cached_payload["system"]`, `messages=cached_payload["messages"]`. Verify the response reports `cache_creation_input_tokens` on first wake and `cache_read_input_tokens` on subsequent wakes.

### C2 — Live-mode cost tick path will AttributeError on first invocation

**File**: `src/skyherd/server/events.py:347-377` (`_real_cost_tick`)
**Finding**: `_real_cost_tick` pulls tickers via `self._mesh._session_manager._tickers.get(session.id)`. `SessionManager` has **no** `_tickers` attribute; tickers live on each `Session` as `_ticker` (singular). This code path was never run — any deployment with `SKYHERD_MOCK=0` and a real mesh will crash the cost loop the moment a session is created.
**Evidence**:
```python
# src/skyherd/server/events.py:352-353
for name, session in self._mesh._sessions.items():
    ticker = self._mesh._session_manager._tickers.get(session.id)   # AttributeError
```
vs. the actual model in `session.py:345-346`:
```python
def all_tickers(self) -> list[CostTicker]:
    return [s._ticker for s in self._sessions.values() if s._ticker is not None]
```
**Impact**: The dashboard cost ticker — the explicit "$5k Managed Agents money shot" per plan v5.1 — only works in `SKYHERD_MOCK=1`. Live runs crash the broadcaster's cost loop, silently (the `except Exception: logger.debug(...)` at line 343 swallows it). Judges reviewing a live deploy see a dead ticker.
**Fix**: Replace with `session._ticker` or call `self._mesh._session_manager.all_tickers()` and pair by session id. Add an integration test that runs `EventBroadcaster(mock=False, mesh=real_mesh)` end-to-end and asserts the cost event reaches subscribers.

### C3 — AI-telltale sanitizer is dead code; Wes will ship with every banned phrase intact

**File**: `src/skyherd/voice/wes.py:182-206`
**Finding**: `_FORBIDDEN_PATTERNS` defines a list (em-dash, "I just wanted", "anomaly", "alert", "alarm", "warning", etc.) and compiles `_FORBIDDEN_RE`, but `_FORBIDDEN_RE` is referenced **nowhere else** in the codebase (confirmed by grep). `_sanitize()` only substitutes em/en dashes — none of the other patterns are ever matched. The "never let AI telltales slip through" guard is cosmetic.
**Evidence**:
```python
_FORBIDDEN_PATTERNS = [r"—", r"I just wanted", ..., r"anomaly", r"alert", r"alarm", r"warning"]
_FORBIDDEN_RE = re.compile("|".join(_FORBIDDEN_PATTERNS), re.IGNORECASE)   # compiled...

def _sanitize(text: str) -> str:
    """Strip any residual AI telltales. Replace em/en dashes with commas."""
    text = re.sub(r"[—–]", ",", text)   # ...never referenced again
    return text.strip()
```
Additionally, blocking `"alert"` / `"alarm"` / `"warning"` is nearly impossible to reconcile with normal ranch English — if this filter ever ran it'd gut half the template bank. The list is aspirational and the wiring lies.
**Impact**: "Most Creative Opus 4.7 Exploration ($5k)" rides on the Wes persona. An LLM-augmented Wes (if wired per C1) will produce em-dashes, "I detected", "anomaly" language routinely. Judges will hear the AI in 30 seconds.
**Fix**: Either (a) apply `_FORBIDDEN_RE` inside `_sanitize` and replace matches with sensible substitutions per pattern, or (b) delete `_FORBIDDEN_PATTERNS` / `_FORBIDDEN_RE` as dead code. Don't ship code that claims to guard something it doesn't guard.

### C4 — SensorBus opens a fresh MQTT connection for every publish

**File**: `src/skyherd/sensors/bus.py:121-140`
**Finding**: `SensorBus.publish` wraps every send in `async with aiomqtt.Client(...) as client:` — a fresh TCP/MQTT CONNECT / DISCONNECT per message. With the plan's 500 cows × 60-s collar period, 6 troughs × 10s, water × 5s, thermal × 15s, fence × 3s, acoustic × 30s, weather × 30s, the steady-state rate is several connections per second. Scaled to ~500 collars, ~15 connections/second average.
**Evidence**:
```python
# sensors/bus.py:121-135
async def publish(self, topic, payload, qos=0, ledger=None):
    raw = _canonical_json(payload)
    async with aiomqtt.Client(hostname=self._host, port=self._port) as client:
        await client.publish(topic, payload=raw.encode(), qos=qos)
```
**Impact**: Embedded amqtt broker will exhaust file descriptors / queue tasks / connection-handler slots under demo load. When the sim-completeness gate asks "All 7+ sim sensors emitting realistic telemetry" at full herd size, the bus will thrash or deadlock intermittently. This matches the user's symptom "UI turned out dogshit visually despite green tests" — sensor messages dropping randomly on a loaded run that tests never exercised.
**Fix**: Create one persistent `aiomqtt.Client` in `SensorBus.__init__` / `start()`, reuse on every publish. Add a stress test: 1000 publishes in 10 seconds across 50 concurrent sensors, assert no errors and median latency < 10ms.

### C5 — SitlBackend telemetry awaits have no timeouts; agent hangs indefinitely on SITL stalls

**File**: `src/skyherd/drone/sitl.py:76-93, 105-111, 169-175, 240-275`
**Finding**: Every `async for x in drone.telemetry.Y(): ... break` in `connect`, `takeoff`, `return_to_home`, and `state` has no `asyncio.wait_for(..., timeout=...)`. If SITL is alive but the specific telemetry stream never publishes the awaited condition (e.g. GPS lock never goes green because the sim's GPS model is broken, or `in_air` latches `False` after a dropped MAVLink packet), the coroutine hangs forever and the whole FenceLineDispatcher wake cycle blocks with it. The 30-second `_CONNECT_TIMEOUT_S` exists but only covers `connection_state`, not `health()`, `in_air()`, `position()`, `battery()`, `flight_mode()`.
**Evidence**:
```python
# sitl.py:91-93  (no timeout — can hang forever)
async for health in drone.telemetry.health():
    if health.is_global_position_ok and health.is_home_position_ok:
        break
```
```python
# sitl.py:107-109  (takeoff waits forever for in_air)
async for in_air in drone.telemetry.in_air():
    if in_air:
        break
```
**Impact**: Demo-day risk: one MAVLink hiccup and the coyote scenario never completes. The event cascade the judges watch just... stops. No retry, no error surfaced — the handler coroutine is parked.
**Fix**: Wrap every `async for` in `asyncio.wait_for(...)` with a generous but finite timeout (10–30s), raise `DroneError` on timeout so the caller can retry or fail cleanly.

### C6 — Exception swallowing hides real Twilio / ElevenLabs / voice-call failures

**File**: `src/skyherd/mcp/rancher_mcp.py:81-95`
**Finding**: `_try_send_sms` wraps the Twilio client call in `except Exception: return False`. `_try_voice_call` writes `except (ImportError, AttributeError, Exception)` — which is equivalent to bare `except Exception` (the specific exceptions are shadowed). Any Twilio authentication error, rate limit, network error, or malformed phone number is reported as "not delivered" with zero diagnostic. `page_rancher` then writes a success-looking log record with `"channel": "log"` and returns a cheerful message to Claude.
**Evidence**:
```python
# rancher_mcp.py:81-95
def _try_send_sms(to, body) -> bool:
    ...
    try:
        from twilio.rest import Client
        client = Client(sid, token)
        client.messages.create(body=body, from_=from_num, to=to)
        return True
    except Exception:   # swallows everything
        return False
```
**Impact**: In a real demo or pilot, Wes won't call. The page_rancher tool will quietly fall back to JSONL and the judge/rancher will never know. During the hackathon video this is survivable; post-hackathon when George loads real Twilio creds and a typo or rate limit fires, it fails silently.
**Fix**: Catch `TwilioRestException` specifically. Log the exception at WARNING. Return a `{success, error_kind, message}` dict instead of a bool so callers can surface failures. Add a test that injects a raising Twilio client and asserts the failure propagates to the rancher-page record.

---

## HIGH (tests that lie, duplicated logic, broken abstractions, concurrency)

### H1 — Five agent handlers are 95% copy-paste with the same four-block structure

**Files**: `src/skyherd/agents/{fenceline_dispatcher,herd_health_watcher,calving_watch,grazing_optimizer,predator_pattern_learner}.py`
**Finding**: Each agent file has (i) a `_SKILLS_BASE = "skills"` + `_skill()` helper (identical, 5 copies), (ii) an `_SYSTEM_PROMPT_INLINE` const, (iii) a `handler()` that constructs `user_message`, calls `build_cached_messages`, then branches on `ANTHROPIC_API_KEY`, and (iv) an `_run_with_sdk` body that is byte-for-byte identical across all 5 files aside from a variable name or two. ~180 lines of duplicated control flow. See especially the `_run_with_sdk` bodies at `fenceline_dispatcher.py:162-184`, `herd_health_watcher.py:114-135`, `calving_watch.py:106-125`, `grazing_optimizer.py:99-118`, `predator_pattern_learner.py:94-113` — all identical.
**Evidence**: Same `async for msg in sdk_client.query(prompt=prompt): if isinstance(msg, AssistantMessage): for block in msg.content: if isinstance(block, ToolUseBlock): calls.append(...); if msg.usage: ... elif isinstance(msg, ResultMessage) and msg.total_cost_usd: ...` block in all 5 files.
**Impact**: Fixing C1 (prompt caching) requires editing in 5 places. Any new agent = 100 lines of copy. High correlation risk for prompt-cache regressions, usage accounting mismatches.
**Fix**: Extract `async def run_agent(session, wake_event, sdk_client, system_prompt, user_message_builder) -> list[tool_call]` into `agents/_runner.py`. Each agent file becomes a spec + prompt + user_message_builder. Delete `_run_with_sdk` 5 times.

### H2 — Every agent test asserts the stub returned what the stub is hardcoded to return

**Files**: `tests/agents/test_fenceline.py`, `tests/agents/test_herd_health.py`, `tests/agents/test_calving.py`, etc.
**Finding**: Every `TestXxxSimulateHandler` test calls `_simulate_handler(event, session)` and then asserts `"launch_drone" in tools`. But `_simulate_handler` is a hardcoded list literal in the agent file: it *always* returns `[get_thermal_clip, launch_drone, play_deterrent, page_rancher]`. The test is equivalent to `assert ["a","b","c"] == ["a","b","c"]`. Delete the real `handler`, the real SDK path, and the real agent altogether — every one of these tests still passes.
**Evidence**:
```python
# fenceline_dispatcher.py:194-220 — the stub literally lists the tools
def _simulate_handler(wake_event, session):
    return [{"tool":"get_thermal_clip",...},{"tool":"launch_drone",...},
            {"tool":"play_deterrent",...},{"tool":"page_rancher",...}]

# test_fenceline.py:61-66 — test asserts the list literal contains its own items
def test_launch_drone_called(self):
    calls = _simulate_handler(self._fence_event(), session)
    tools = [c["tool"] for c in calls]
    assert "launch_drone" in tools
```
**Impact**: Test suite gives false confidence. Zero coverage of the SDK path, prompt-cache wiring (C1), error handling, or even wake-event normalization.
**Fix**: Add integration tests with a `FakeSDKClient` that verifies (a) the payload passed to `query()` contains cache_control system blocks, (b) tool calls are routed back correctly, (c) ResultMessage cost accounting updates the session. Delete the tautological "list literal contains literal" tests.

### H3 — Cost-ticker tests assert constants equal themselves

**File**: `tests/agents/test_cost.py:21-35`
**Finding**: `TestPricingConstants` asserts `_SESSION_HOUR_RATE_USD == pytest.approx(0.08)`, `_INPUT_TOKENS_PER_M_USD == pytest.approx(15.00)`, etc. — the values are `0.08`, `15.00` etc. as defined 40 lines up in `cost.py`. This is `assert 0.08 == 0.08`. Also `test_emit_tick_returns_payload_or_none` asserts `result is None or isinstance(result, TickPayload)` — tautological type-system check.
**Impact**: Inflates coverage number without verifying any behavior. If Anthropic changes Opus 4.7 pricing next week, these tests don't protect you — they lock the wrong numbers in place.
**Fix**: Delete the constant-equality tests. Add a behavioral test: `record_api_call(1_000_000, 0, 0, 0)` → `cumulative == 15.0`. Already half-covered at line 110-119 — expand.

### H4 — CrossRanchMesh takes a `meshes` dict and promptly ignores it

**File**: `src/skyherd/agents/mesh_neighbor.py:354-426`
**Finding**: Constructor takes `meshes: dict[str, AgentMesh]` and stores it as `self._meshes`, but in `start()` (line 398) the per-mesh iteration uses `_mesh` as a throwaway variable (`for ranch_id, _mesh in self._meshes.items():`). It then creates its own `SessionManager` for each ranch (`self._session_managers[ranch_id] = SessionManager()`), its own FenceLineDispatcher session, and runs the whole show inside CrossRanchMesh. The passed-in AgentMesh instances are never used. The cross-ranch "multi-mesh orchestrator" doesn't orchestrate the meshes; it reimplements half of one.
**Impact**: Fake abstraction. When someone wants to actually wire agents from a real AgentMesh through neighbor handoff, they'll find CrossRanchMesh useless and rewrite it. Two parallel worlds of session state exist under the same module name.
**Fix**: Either delete the `meshes` parameter (accept `ranch_ids: list[str]` instead, acknowledging this is a standalone orchestrator) or route genuinely through the passed-in meshes' session managers.

### H5 — ClassifyPipeline classifies every cow in the herd for every trough event

**File**: `src/skyherd/vision/pipeline.py:85-96`
**Finding**: `pipeline.run(world, trough_id)` iterates `for cow in world.herd.cows:` and calls `classify(cow, frame_meta)` for all of them. With 7 disease heads, this is 500 × 7 = 3500 head evaluations per `camera.motion` event. The comment on line 83 says "all are 'in frame' for sim purposes" — so the pipeline has no concept of which cows are actually visible at trough_id. In scenarios that fire multiple trough-cam events, this compounds fast.
**Impact**: Per-event latency scales linearly with herd size. Scenarios like `sick_cow` and `storm` that reuse the pipeline will slow to a crawl at the 500-cow target. Dashboard feels laggy; the user's "UI turned out dogshit visually" symptom has a backend component.
**Fix**: Add a `cows_in_frame(trough_id)` method to the World (distance-to-trough filter, max ~10 cows). Classify only those. Alternatively, hold a per-trough RNG-sampled subset. Move the full-herd sweep to a separate daily `herd_survey` call invoked by the cron wake, not the motion wake.

### H6 — Scenarios mutate private world state (`_weather`, `.predators.append`)

**Files**: `src/skyherd/scenarios/base.py:156`, `coyote.py:43-45`, `coyote.py:80-90`, `cross_ranch_coyote.py:50-53, 88-90, 97-99`
**Finding**: `CoyoteScenario.setup` does `world.weather_driver._weather = world.weather_driver.current.model_copy(update={"wind_dir_deg": 180.0})` — reaches into a private attribute to replace state. `inject_events` does `world.predator_spawner.predators.append(coyote)` and later `world.predator_spawner.predators[idx] = updated` — direct list mutation. Scenario base does `ledger._conn.close()`. Violates the CLAUDE.md "never mutate" rule and couples scenarios to world internals.
**Impact**: Any refactor of `WeatherDriver` or `PredatorSpawner` breaks all scenarios silently. Tests that "test the scenario" actually pin implementation details of world internals.
**Fix**: Add `world.weather_driver.force_wind(dir_deg=180.0)` and `world.predator_spawner.inject(predator)` / `set_state(id, state)` public methods. Move scenario pre-conditions to those APIs.

### H7 — `HerdHealthWatcher` skill list has a dead-code ternary and is then overwritten on import

**File**: `src/skyherd/agents/herd_health_watcher.py:45-61`
**Finding**: The original `skills=[..., _skill("cattle-behavior/disease/pinkeye.md") if False else "", ...]` is definitively unreachable (`if False`). Five lines later (line 54) `HERD_HEALTH_WATCHER_SPEC.skills = [...]` overwrites the field entirely. The override has no "pinkeye" entry, so the pinkeye skill never loads — even though this agent is the one that does disease triage.
**Impact**: The Skills-first architecture ($50k pattern) is not delivering the disease skills into the agent that makes disease decisions. The disease vision heads exist but their "what does this detection mean" Skill is never in the prompt.
**Fix**: Delete the original `skills=` arg with the dead ternary. Include `_skill("cattle-behavior/disease/pinkeye.md")` etc. in the canonical list when the files exist.

### H8 — Mutation-heavy update pattern in `PredatorSpawner` used from scenarios

**File**: `src/skyherd/scenarios/coyote.py:82-99` (and `cross_ranch_coyote.py:91-107`)
**Finding**: The fleeing-transition code does `idx = world.predator_spawner.predators.index(pred); world.predator_spawner.predators[idx] = updated`. This in-place list replacement is a mutation antipattern per CLAUDE.md, and worse, it races with any concurrent iteration of `.predators` from `world.step()` or sensor emitters.
**Impact**: Non-deterministic scenario outcomes under full-sim load (the gate requirement). One of the stated pitches is "deterministic replay — same seed, same scenario" — this pattern can break that on a multi-task loop.
**Fix**: Provide `predator_spawner.set_state(id, new_state)` that guards with a lock and rebuilds a new tuple/list immutably.

### H9 — Attestation `verify()` re-hashes entire ledger on every call with no pagination

**File**: `src/skyherd/attest/ledger.py:239-300`
**Finding**: `verify()` re-computes blake2b over every single row of `events` and re-verifies every Ed25519 signature. On a loaded demo (~2000 events accumulated across a 600s scenario with 500-cow collar telemetry), each call is O(N) crypto work. The canonical design ("Merkle chain") implies you shouldn't re-hash historic rows on every audit — you'd re-anchor and verify incrementally.
**Impact**: Lower severity — but the VISION.md insurance claim ("This log is the product, not the drone") is undercut if verify doesn't scale. A judge scripting `skyherd-attest verify --bench 100000` will see the linearity.
**Fix**: Add a `verify_since(since_seq: int)` method that picks up from a known-good anchor. Document the O(N) verify explicitly as a "full audit" path and cache the last known-good seq.

### H10 — `app.py:143` uses a nonsense expression `min(10, 50)` that always equals 10

**File**: `src/skyherd/server/app.py:143`
**Finding**: `entries = [_mock_attest_entry() for _ in range(min(10, 50))]` — `min(10, 50)` is constant 10. Either the intent was `min(since_seq_based_count, 50)` and the parameter was dropped, or this is lazy code.
**Impact**: Low-harm but emblematic — the mock path ignores `since_seq` entirely and always returns exactly 10 entries. Dashboard clients that paginate by `since_seq` will see the same 10 entries on every poll; the attestation panel never advances in mock mode.
**Fix**: `entries = [_mock_attest_entry() for _ in range(10)]` and honour `since_seq` properly, OR call a generator that advances per request.

### H11 — SSE semaphore check touches `_value` private attribute and races with allocation

**File**: `src/skyherd/server/app.py:154-160`
**Finding**: `if sem is not None and sem._value == 0:` reads a CPython-internal asyncio private attribute. The `_value` check is racy: between the check and the subsequent `async with sem:` inside the generator, another connection can acquire the last slot. The error message "Too many SSE connections" then arrives for a caller who could have gotten in otherwise.
**Impact**: Private-attr use can break on any asyncio internal change. Race is not harmful but gives wrong 429s under load.
**Fix**: Use `sem.locked()` (public) or attempt non-blocking `acquire_nowait()`/release() for the check. Or drop the check and let the `async with sem:` gate correctly with a streaming 429 if saturated.

### H12 — `EdgeWatcher` re-implements two utilities already defined in SensorBus

**File**: `src/skyherd/edge/watcher.py:102-116`
**Finding**: `_parse_mqtt_url` and `_canonical_json` are copy-pastes of the same-named functions in `src/skyherd/sensors/bus.py:32-34, 176-187`. Two copies of each drift the moment one is updated.
**Impact**: Duplication. If JSON canonicalisation rules change (e.g. to match the attestation ledger's stricter flavor) only one copy gets updated.
**Fix**: Move both into `skyherd/common/json_utils.py` and `skyherd/common/mqtt_url.py`. Import from there in both places.

---

## MEDIUM (maintainability, naming, weak tests, over/under-engineering)

### M1 — `hardware_only.py` is 596 lines and contains the whole demo orchestrator

**File**: `src/skyherd/demo/hardware_only.py` (596 lines)
**Finding**: Single file carrying scenario orchestration, MQTT wiring, drone handoff, edge pairing, video timing. Five responsibilities in one module. Approaches the 800-line CLAUDE.md ceiling.
**Fix**: Split into `demo/orchestrator.py`, `demo/edge_pair.py`, `demo/drone_handoff.py`, `demo/timing.py`.

### M2 — `mesh_neighbor.py` at 696 lines for what the plan describes as "~4 hrs" of work

**File**: `src/skyherd/agents/mesh_neighbor.py` (696 lines)
**Finding**: Plan v5.1 says Cross-Ranch Mesh = ~4 hours, "2 agent sessions, one shared MQTT topic, a second map panel". Shipping code is a `NeighborBroadcaster` class, a `NeighborListener` class, a `CrossRanchMesh` with its own session managers, dedup TTL tracking, an internal queue router, a standalone `simulate_coyote_at_shared_fence` method. Over-engineered vs. the brief.
**Fix**: Collapse broadcaster+listener+mesh into one `CrossRanchBus` class (~150 lines). Defer the dedup-TTL / router-queue machinery until the second cross-ranch scenario exists.

### M3 — `get_backend()` is a factory that doesn't factor

**File**: `src/skyherd/drone/interface.py:119-156`
**Finding**: `_REGISTRY: dict[str, type[DroneBackend]]` starts empty. `get_backend("sitl")` imports and registers on first call. `get_backend("mavic")` and `get_backend("f3_inav")` — **supported by the plan** — are not handled; both hit the `else: raise DroneError("Unknown drone backend ...")`. In effect this "factory" only dispatches `sitl` and `stub`. The mavic and f3_inav backends exist as classes but are not selectable via env var.
**Impact**: `DRONE_BACKEND=mavic` crashes at runtime. The Tier 2/3 plan (Mavic/F3) doesn't wire up.
**Fix**: Add `elif backend_name == "mavic": from ...mavic import MavicBackend; _register("mavic", MavicBackend)` and same for `f3_inav`. Drop the `_REGISTRY` indirection — a flat dict at module scope is simpler.

### M4 — Five `_make_session()` helpers and six `_event_*` helpers copy-pasted across test files

**Files**: `tests/agents/test_*.py`
**Finding**: Each agent test file has its own `_make_session()` → 5 copies. Each has a `_fence_event()` / `_motion_event()` / `_collar_event()` helper → another 5. None are in a conftest.
**Fix**: Put `make_session(spec)` + standard fixtures in `tests/agents/conftest.py`.

### M5 — Disease heads share a decision-table pattern; extract `ThresholdHead` base

**Files**: `src/skyherd/vision/heads/{pinkeye,brd,foot_rot,lsd,screwworm,bcs,heat_stress}.py`
**Finding**: Every head is (i) threshold constants, (ii) a severity mapping dict, (iii) a confidence-from-offset formula, (iv) a reasoning-string template, (v) a classify() that plugs those together. Seven near-identical scaffolds.
**Fix**: Extract `class ThresholdHead(Head)` with `metric(cow) -> float`, `severity_bands: list[tuple[float, Severity]]`, `reasoning_template: str`. Define each head as a config instance. Drops 70%+ of code.

### M6 — `_canonical_json` duplicated between `attest/ledger.py` and `sensors/bus.py`

**Files**: `src/skyherd/attest/ledger.py:85-89`, `src/skyherd/sensors/bus.py:32-34`, `src/skyherd/edge/watcher.py:114-116`
**Finding**: Three copies of the same canonical-JSON function.
**Fix**: Single `skyherd/common/canonical.py::canonical_json`.

### M7 — Handler names `handler`, `on_webhook`, `run`, `process` are generic

**Files**: multiple
**Finding**: Every agent exports a top-level `handler`. `SessionManager.on_webhook`. `Scenario.run`. `_route_event`. Reader has to trace imports to figure out which `handler` they're looking at.
**Fix**: Rename to `handle_fenceline_wake`, `handle_herd_health_wake`, etc.

### M8 — `test_coyote.py` imports `_BREACH_AT_S` private constant and pins it

**File**: `tests/scenarios/test_coyote.py:6, 19-21`
**Finding**: Test imports a private module constant and asserts `400 < _BREACH_AT_S < 500`. This is a test that reads an implementation constant and re-asserts the range the constant was chosen to be in.
**Fix**: Delete this test; it's a tautology.

### M9 — `page_rancher` treats "medium" urgency as "text" silently

**File**: `src/skyherd/mcp/rancher_mcp.py:124-127`
**Finding**: `"medium"` is not in `_URGENCY_LEVELS` so it gets remapped to `"text"` silently. But the FenceLineDispatcher `_simulate_handler` returns `urgency="call"` (fine) and `coyote.py` test_outcome accepts `"medium"` as valid. Two layers disagree about what "medium" means.
**Fix**: Pick one: either add "medium" to `_URGENCY_LEVELS` with an explicit mapping, or reject unknown urgencies with an error instead of silent remap.

### M10 — `_try_run_classify_pipeline` swallows all errors as debug logs

**File**: `src/skyherd/agents/herd_health_watcher.py:172-191`
**Finding**: `except Exception as exc: logger.debug(...); return {"detection_count": 0, ...}`. Any classifier error — missing ranch config, importerror, world shape mismatch — produces "zero detections" silently. The HerdHealthWatcher then "decides" the cow is fine.
**Fix**: Narrow to `except (ImportError, FileNotFoundError) as exc:` for expected failures; let everything else raise so the agent surface-errors correctly.

### M11 — `Session._ticker: CostTicker | None = None` with `if session._ticker` checks scattered

**File**: `src/skyherd/agents/session.py` (ticker access points)
**Finding**: The session is always created with a ticker via `SessionManager.create_session()`. But `Session._ticker` is typed Optional and every call site repeats `if session._ticker:`. The None case never fires in production code.
**Fix**: Non-optional `_ticker: CostTicker` with a mandatory constructor param. Drop the `if session._ticker:` guards.

### M12 — `make_world(seed=42, config_path=_WORLD_CONFIG)` pattern recurs

**Files**: `scenarios/base.py`, `tests/scenarios/test_coyote.py`, ~8 test files
**Finding**: Every test that touches a world does `make_world(seed=42, config_path=...)` with a redundantly-computed config path. Varies subtly between files.
**Fix**: `from skyherd.testing import default_world` fixture that yields the world. In real `conftest.py`.

### M13 — `AgentSpec._DEFAULT_MODEL = "claude-opus-4-7"` — brittle literal, no version

**File**: `src/skyherd/agents/spec.py:20`
**Finding**: Every agent pins `model="claude-opus-4-7"`. The current model identifier per Anthropic's convention is typically date-suffixed; the plain alias may rotate under you.
**Fix**: Central `skyherd/agents/_models.py` with a date-pinned alias.

### M14 — Scenario `run_all` doesn't short-circuit on fatal scenarios

**File**: `src/skyherd/scenarios/base.py:433-455`
**Finding**: `run_all` runs every scenario sequentially and just logs failures. A first-scenario world-state mutation that poisons later scenarios will silently pass through, printing FAIL for each.
**Fix**: Track failure count; exit nonzero from the CLI wrapper when any scenario fails; optionally have a `--fail-fast` flag.

---

## LOW (style, minor polish)

### L1 — Bare `# noqa: BLE001` littered across 20+ files

Found across sensors/bus.py, agents/mesh.py, scenarios/base.py, server/events.py, mcp/rancher_mcp.py, drone/sitl.py. The `noqa` suppresses ruff's "blind except Exception" without addressing the underlying code smell.
**Fix**: Use specific exception types. When you genuinely must catch everything, `logger.exception(...)` (not `.debug(...)`) so stack traces survive.

### L2 — `# type: ignore[name-defined]` with forward refs for `mavsdk.System`

**File**: `src/skyherd/drone/sitl.py:52, 297`
**Finding**: The `type: ignore` is a fix-around. Use `if TYPE_CHECKING: import mavsdk` for type-only imports.

### L3 — `_SCORE_TO_SEVERITY: dict[int, Severity]` uses int keys but bcs/foot_rot accept float

**File**: `src/skyherd/vision/heads/foot_rot.py:22-34`
**Finding**: `cow.lameness_score` can be a float; keys are ints 2..5. `clamped = min(score, 5)` — if `score=4.7` you end up with `4.7` and a KeyError.
**Fix**: `clamped = min(int(round(score)), 5)` explicitly.

### L4 — `_STATIC_DIR` resolved at import time via `Path(__file__).parent.parent.parent.parent`

**File**: `src/skyherd/server/app.py:52`
**Finding**: Four-`parent`-chain path resolution. If a file is moved, path silently points elsewhere.
**Fix**: Use `importlib.resources` or a `PROJECT_ROOT` constant defined once in `skyherd/__init__.py`.

### L5 — TODO/FIXME-equivalent comments with no ticket reference

Multiple locations carry editorial notes that describe future work without tracking.
**Fix**: Reference issue numbers or delete the comment.

### L6 — Single-letter loop variables in scenarios

**File**: `src/skyherd/scenarios/base.py:128, 139, 147`
**Finding**: `for e in ledger.iter_events()` in `base.py:273` is shadowed later; readability suffers.

---

## Architectural drift from plan v5.1

- **Prompt caching (plan v5.1 Opus 4.7 creative use #4 "Claude API with prompt caching everywhere — non-negotiable per claude-api skill")**: **NOT WIRED** — see C1. The `build_cached_messages` helper exists and is shape-correct, but its output is discarded before any API call. This is the single biggest drift.
- **Skills-first architecture (plan Skills library, $50k CrossBeam pattern)**: **partially drifted** — Skills are read from disk and concatenated into the `system_blocks` list that no one sends (C1). HerdHealthWatcher's disease skills don't even load (H7). The library exists; the delivery into agent prompts does not.
- **Cost ticker money-shot (plan "idle pause + $0.08/session-hour active... Managed Agents money shot")**: **broken in live mode** (C2) — works in mock only. Judges looking at a live session will see a dead ticker or crashes in debug logs.
- **Drone backend selection (plan Component 3 "Tier selected via DRONE_BACKEND=sitl|mavic|f3_inav env var")**: **drifted** — only `sitl` and `stub` are selectable via env var (M3). Mavic and F3 classes exist but are not in the factory registry.
- **7+ sensors (plan Component 2)**: matches — water, trough_cam, thermal, fence, collar, acoustic, weather all present in `sensors/registry.py`. Sim coverage of sensors is good.
- **7 disease heads (plan Component 9)**: matches — pinkeye, screwworm, foot_rot, brd, lsd, heat_stress, bcs all present in `vision/heads/`. Behavior is decent but delivered through a duplicated pattern (M5).
- **5 Managed Agents (plan Component 5)**: matches — all 5 specs exist with correct names. The duplication across handlers (H1) is the story here, plus prompt caching (C1).
- **Attestation SQLite + Ed25519 Merkle chain (plan Extended Vision #7)**: matches — well-built. Tests genuinely verify tamper detection (the rare bright spot).
- **Wes voice (plan Component 5 + Creative use #2)**: exists as hardcoded template table — **underclaimed vs. plan** ("a character... skill-defined register... system-prompted pacing"). The sanitizer lies (C3). No Skill loading in wes.py. This is a TTS template renderer, not a character.
- **CrossRanchMesh (plan Extended Vision #1)**: shipped but over-engineered (M2) and doesn't use its `meshes` param (H4).
- **Rancher MCP / Twilio path**: silent failure on Twilio errors (C6).
- **Deterministic replay (plan Sim Completeness Gate "Full sim replays deterministically")**: at risk — mutation patterns in scenarios (H6, H8) + ClassifyPipeline herd-wide scan (H5) create nondeterminism and load-sensitive timing.

---

## Prompt-cache audit

**Blocks are shape-correct. Delivery path is broken.**

- `build_cached_messages` in `session.py:108-150` produces `{"system": [{type:"text", text:..., cache_control:{type:"ephemeral"}}, ...skill blocks...], "messages": [...]}`. **This matches the Anthropic Messages API spec.**
- All 5 agents **call** `build_cached_messages` and **discard** everything except `messages[0]["content"][0]["text"]`, then hand that string to `claude_agent_sdk.query(prompt=str)`. The SDK wraps it as a plain user message — no system, no cache_control.
- **No agent actually sends the cached payload to Claude.** There is zero prompt-cache activation in the shipped code.
- `CostTicker.record_api_call(..., cache_hit_tokens=..., cache_write_tokens=...)` is public, pricing constants are present, but no call site passes nonzero values for those parameters. The cache path in cost accounting is dead.
- Verification ask: after fix, run one scenario twice and log `response.usage.cache_read_input_tokens`. First run should be zero; second should equal system+skills token count. That's the correctness signal.

---

## Bright spots (not everything is bad)

- **`src/skyherd/attest/ledger.py`** and its test suite are genuinely well-built. Merkle chain, Ed25519 signing, tamper-detection tests that actually mutate the DB and verify the detection. This is the only subsystem where tests would catch real regressions.
- **`src/skyherd/drone/safety.py`** — Geofence checker, battery guard, wind guard are clean, well-documented, and properly exceptioned. Correctly decomposed.
- **`src/skyherd/drone/stub.py`** — genuinely useful in-memory backend that doesn't leak state (returns copies on state() to prevent caller mutation — line 102-111).
- **World sim (`world/cattle.py`, `predators.py`, `terrain.py`)** — wasn't exhaustively reviewed here but spot checks show immutable models via pydantic `model_copy`. The mutation sins are in scenarios reaching into world internals, not the world itself.
- **Disease head threshold logic** — numerically sensible, reasoning strings reference the underlying Skill path explicitly. The problem is delivery (H7) and scaffolding (M5), not the decision tables.
