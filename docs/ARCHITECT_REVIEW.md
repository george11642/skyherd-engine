# SkyHerd Architect Review — Apr 22 2026

## Headline Verdict

**Adequately architected, structurally weak.** The module layering is clean (no true circular imports, `sensors` never imports `agents`, `server` treats `mesh/ledger/world` as duck-typed injectables), file sizes are reasonable, interfaces are declared. But the system is held together by silent fallbacks. Every production integration point — Claude SDK, MQTT broker, Mavic backend, sensor-MCP bus handoff, cost ticker's live path — has a `_simulate_*` or `except: fallback` layer that lets green tests pass while the real path is broken or unreachable. The code smells exactly like the UI: it compiles, passes linters, passes tests, and fails under actual load because the structural promises (determinism, sim-real parity, live cost metering, hybrid Mavic demo) are decorative, not enforced.

## Top 3 Architectural Risks

### R1 — Determinism is unenforceable as built
Plan v5.1 Gate item: "Full sim replays deterministically — same seed, same scenario, same agent outputs."

Reality:
- `attest/ledger.py:154` uses `datetime.now(tz=UTC)` on every append.
- Every sensor (`water.py`, `weather.py`, `collar.py`, `thermal.py`, `trough_cam.py`, `acoustic.py`, `fence.py`) stamps `time.time()` into its payload.
- `scenarios/base.py:298/383` stamps wall clock into replay filenames and REPLAY_LOG rows.
- `agents/session.py:195` uses `uuid.uuid4()` for session IDs.
- Thermal-clip synthesizers seed `np.random.default_rng(seed=int(time.time()) % 2**32)`.

`World.clock` IS deterministic, but the emission layer sitting on top of it is not — so byte-identical replay is impossible regardless of seed. **Biggest gap between claim and code.**

### R2 — Two critical live-path bugs silently masked by mock fallbacks

**R2a — Cost ticker typo that crashes without mock mode.** `server/events.py:353` accesses `self._mesh._session_manager._tickers.get(...)`. `_tickers` is not an attribute on `SessionManager`, which exposes `all_tickers()` and stores via `session._ticker`. The `_real_cost_tick()` path AttributeErrors the moment you run the dashboard without `SKYHERD_MOCK=1`.

**R2b — Mavic backend factory silently falls back to SITL.** `drone/interface.py:get_backend()` only registers `sitl` and `stub`; passing `"mavic"` or `"f3_inav"` raises `DroneError`. The `Makefile` targets `hardware-demo` with `DRONE_BACKEND=mavic` by default, and `demo/hardware_only.py` advertises "mavic (real) | sitl (default)". The `except DroneError` block in `_launch_drone` converts the resolution failure into a silent SITL fallback labelled "Drone backend 'mavic' unavailable" — so the hybrid Mavic demo runs entirely in SITL while telling the log it's real hardware.

Mirror of the `_simulate_handler` pattern in `agents/fenceline_dispatcher.py:187`: whenever anything fails, the system keeps running with hardcoded dictionary literals pretending to be intelligence.

### R3 — Sim-real parity drifts at the wire

Plan: "sim and hardware share one bus."

- `sensors/trough_cam.py:97` emits `{ts, kind, ranch, entity, trough_id, cows_present, ids[=cow_ids], frame_uri}`.
- `edge/watcher.py:337` emits the same base fields BUT `ids` is `[tag_guess]` (detector label string, not cow entity ID), adds `source: "edge"`, adds `detections: [{tag_guess, bbox, confidence, frame_ts}]`, and writes to `runtime/edge_frames/` while sim writes to `runtime/frames/`.
- Any agent that filters on `ids` or reads `frame_uri` will behave differently depending on which emitter wrote the message.
- Comment at `edge/watcher.py:346` literally says "Edge-only extras (ignored gracefully by sim consumers)" — schemas diverge by design and the author knows it.
- The MCP tool `get_latest_readings` imports a non-existent `skyherd.sensors.bus.get_bus_state` (`mcp/sensor_mcp.py:41`) caught by `except (ImportError, AttributeError): return None` — so agents asking their sensor-MCP tool for real readings always get an empty in-memory stub.

The bus-to-agent-MCP pipe is severed at both ends and nobody notices because nobody checks.

## Top 3 Architectural Strengths

### S1 — Interfaces are well-drawn
`DroneBackend` is a crisp abstract: 8 methods, async, no leaky impl details, factory with lazy imports so Stub users don't pay for `mavsdk`. `Sensor` is a tight 60-line ABC with one abstract `tick()`. `AgentSpec` is a pure dataclass with zero behavior — textbook declarative config. The attestation `Signer`/`Ledger` split separates crypto from storage cleanly. Swapping `SitlBackend` → `MavicBackend` WOULD work at the interface level — the only problem is the factory doesn't register it.

### S2 — Attestation layer is genuinely production-grade
`attest/ledger.py` uses blake2b-256 with fixed-order field concatenation, Ed25519 signatures over raw bytes (not hex), `hmac.compare_digest` for constant-time comparison, SQLite WAL + synchronous=NORMAL, and a `verify()` method that re-computes every hash and every signature in-chain. Canonical JSON with `sort_keys=True, separators=(",", ":"), allow_nan=False` is exactly right. **The one module in the repo that does what it claims.**

### S3 — Skills-first architecture is actually shipped
37 skill `.md` files across `skills/{cattle-behavior, drone-ops, nm-ecology, predator-ids, ranch-ops, voice-persona}/` — exceeds the ≥25 plan target. Each `AgentSpec.skills` list references specific files, and `session.build_cached_messages()` wraps each in `cache_control: {"type": "ephemeral"}`. Per-agent skill lists are distinct (Fence doesn't load calving-signs.md, Calving doesn't load coyote.md). **The one piece of the Opus 4.6 winner pattern-match that landed cleanly.**

## Plan v5.1 Traceability

| Promise | File implementing | Verdict |
|---|---|---|
| Skills-first architecture with ≥25 files | `skills/**/*.md` (37), `agents/session.py:108`, `agents/spec.py:37` | **MATCH** |
| 5 Managed Agents | `agents/{fenceline_dispatcher, herd_health_watcher, predator_pattern_learner, grazing_optimizer, calving_watch}.py` + `agents/mesh.py:56 _AGENT_REGISTRY` | **PARTIAL** — 5 specs declared, but `scenarios/base.py:234 _registry` only wires 4 (PredatorPatternLearner missing from scenario runner) |
| Cost ticker idle-pause | `agents/cost.py`, `agents/session.py:{sleep,wake} set_state` | **PARTIAL** — ticker math is right in isolation; `server/events.py:353 _real_cost_tick` reads non-existent `_tickers`. Only the mock path works end-to-end. The "money shot" visualization is mocked. |
| Deterministic replay (seed=42 byte-identical) | `world/world.py:make_world` seeds RNG; `scenarios/base.py:_run_async(seed=42)` | **DRIFT** — world subsystem is deterministic; emission layer above it is not. Two runs at seed=42 produce different `event_hash` chains, different session IDs, different filenames. |
| Ed25519 Merkle attestation | `attest/ledger.py`, `attest/signer.py` | **MATCH** — full correctness. Only caveat: `ts_iso=datetime.now()` inside `append()` means the ledger breaks the deterministic-replay claim, but the crypto itself is correct. |

## Degradation Check

| Failure | Behavior | Verdict |
|---|---|---|
| MQTT broker dies | Sensor tasks die one-by-one as they tick; no retry. `AgentMesh._mqtt_loop` has `except Exception: logger.debug(...)` — mesh keeps running without events, silently. | **Partial crash**: agents silently stop receiving events; no observability signal. |
| `ANTHROPIC_API_KEY` missing | All 5 agent handlers fall through to `_simulate_handler(...)` returning canned tool-call dictionaries. | **Graceful, deceiving** — demo "works" with no API key because nothing is actually thinking. |
| Drone backend unreachable | `SitlBackend.connect` raises `DroneUnavailable` with a "run `make sitl-up`" hint. `drone_mcp.launch_drone` returns `{"is_error": True}`. | **Graceful** — best-handled failure in the system. |
| Anthropic SDK import fails | No guard around `from claude_agent_sdk import ...` in `mcp/*_mcp.py`. | **Crash at import time** — only bites in `edge` extras-only deployment. |
| Ledger DB corruption / disk full | `Ledger._transaction` rolls back and re-raises; `SensorBus.publish` doesn't handle. | **Partial crash**: single sensor task dies, rest continue. Ledger-down silently costs every attest record for that sensor. |

## Recommended Hackathon Scope Cuts

1. **Delete `drone/f3_inav.py` + `drone/mavic.py` from the demo story.** ~950 lines of unreachable code (factory doesn't register them) maintaining a fiction. Either finish the 3-line factory registration + actually test with a real device this week, or cut the chapter.
2. **Remove `scenarios/cross_ranch_coyote.py` + `agents/mesh_neighbor.py` from the critical path.** 700+ lines for a scenario not in the core 5-scenario Gate. Determinism and live-cost-ticker paths are broken — spend the time there.
3. **Collapse `_simulate_handler` hardcoded tool-call dicts into a single `simulate.py` with one table.** Honesty about what's stubbed in one place.
4. **Pick ONE dashboard mode** (`SKYHERD_MOCK=1` OR live) and delete the other code paths. Multiplies cases; exactly where the `_tickers` bug hid.
5. **Drop the "byte-identical replay" claim from VISION/ARCHITECTURE/MANAGED_AGENTS docs** OR inject a `Clock` into `Ledger.append`, every sensor `tick()`, and `session.create_session`. Pick one; shipping the doc with the current code is the worst option.

## Shared Root Cause

The UI shipped dogshit under green tests and the Python has the same bone structure: **tests exercise the simulation/mock paths, production paths are structurally different, and no integration test makes the two meet.** `_simulate_handler`, `SKYHERD_MOCK=1`, `_mock_cost_tick`, `_mock_world_snapshot`, the `except: fallback_to_sitl`, the `except (ImportError, AttributeError): return None` around `get_bus_state` — every one lets a test pass while the real path rots independently.

The `events.py:353 _tickers` typo and the missing `mavic` factory registration both sit dormant because no test runs with `SKYHERD_MOCK=0` against a real `AgentMesh` and a real `DRONE_BACKEND=mavic`. The code is lint-clean because ruff doesn't know `_tickers` doesn't exist on a duck-typed parameter; pyright doesn't know either because `mesh: Any` on `create_app` discards type information.

**The architectural diagnosis**: every public integration point is optional, and the tests only cover the path where it's absent. Fix the same way you'd fix the UI — write one integration test per capability that fails when the production path breaks, and stop letting mock paths satisfy the assertion for claims ("determinism", "live cost ticker", "hybrid Mavic", "sensor-MCP reads live bus") that are supposed to be real.
