# Code Review TODO — prioritized action queue

Generated: 2026-04-21 alongside `docs/CODE_REVIEW.md`.

**Rule**: every item below references a finding ID (C1, H2, M5, etc.) from CODE_REVIEW.md. Read the finding before starting the fix — the evidence and impact live there, not here.

**Effort key**: S = <30 min · M = ~2 hrs · L = ~half day · XL = full day+

---

## P0 — Do these before the Sim Completeness Gate (Fri noon)

These are load-bearing for the submission narrative. Each one is a judge-detectable lie if left.

| # | ID | Module | Task | Effort |
|---|----|--------|------|--------|
| 1 | **C1** | `agents/*` + `session.py` | Wire `build_cached_messages` output through to `claude_agent_sdk` with `system=` arg (or raw Anthropic client). Verify `cache_read_input_tokens > 0` on second wake. This is the single most important fix in the queue. | **M** |
| 2 | **H1** | `agents/` | Extract the duplicated `_run_with_sdk` + user_message scaffold into `agents/_runner.py`. Do this alongside C1 so the cache fix lives in one place. | **M** |
| 3 | **C2** | `server/events.py` | Fix `_real_cost_tick` to read tickers via `session._ticker` or `manager.all_tickers()`. Add a minimal integration test: real mesh + live broadcaster → at least one `cost.tick` event received with non-mock shape. | **S** |
| 4 | **C3** | `voice/wes.py` | Either wire `_FORBIDDEN_RE` into `_sanitize()` with per-pattern substitutions, or delete the unused guard. Do not ship a filter that lies. | **S** |
| 5 | **C6** | `mcp/rancher_mcp.py` | Replace bare `except Exception` in `_try_send_sms` / `_try_voice_call` with `TwilioRestException` (and narrow ImportError). Return structured result, log at WARNING. | **S** |
| 6 | **H7** | `agents/herd_health_watcher.py` | Delete the `if False else ""` dead ternary. Put the disease Skills (pinkeye, screwworm, etc.) into the actual skills list so HerdHealthWatcher reads them. | **S** |
| 7 | **M3** | `drone/interface.py` | Register `mavic` and `f3_inav` backends in `get_backend()`. `DRONE_BACKEND=mavic` currently raises. | **S** |

**P0 total: one half-day of one engineer.** Stop everything, fix these, replay the coyote scenario, record the demo.

---

## P1 — Fix before code freeze (Sat 6pm MT)

Reliability + correctness for the demo video. Won't be judge-visible if sim is polished enough without them, but they're the delta between "plays cleanly on every take" and "glitches one in five replays".

| # | ID | Module | Task | Effort |
|---|----|--------|------|--------|
| 8 | **C4** | `sensors/bus.py` | Persistent `aiomqtt.Client` in `SensorBus.__init__`. Reuse across publishes. Add a stress test for 1000 publishes/10s at 50 concurrent sensors. | **M** |
| 9 | **C5** | `drone/sitl.py` | Wrap every `async for ... break` telemetry read in `asyncio.wait_for(..., timeout=...)`. Raise `DroneError` on timeout. | **M** |
| 10 | **H5** | `vision/pipeline.py` + `world/` | Add `world.cows_in_frame(trough_id)` filter. Pipeline classifies only those cows. Gate on ~8-12 cows per motion event, not 500. | **M** |
| 11 | **H6** | `scenarios/*` + `world/*` | Add `world.weather_driver.force_wind(dir_deg, speed_kt=...)` and `predator_spawner.inject(predator)` / `set_state(id, state)`. Replace private-attr touches in `coyote.py`, `cross_ranch_coyote.py`, and `base.py`. | **M** |
| 12 | **H2** | `tests/agents/*` | Add at least one `FakeSDKClient` integration test per agent that verifies the cache payload reaches `query()` and tool calls are parsed back correctly. Delete the tautological `_simulate_handler` tests once covered. | **L** |
| 13 | **H10** | `server/app.py:143` | Replace `range(min(10, 50))` with a proper paginated mock that respects `since_seq`. | **S** |
| 14 | **H11** | `server/app.py:154-160` | Swap `sem._value == 0` for `sem.locked()` or remove the pre-check. | **S** |
| 15 | **H12** | `edge/watcher.py` + `sensors/bus.py` | Move `_canonical_json` and `_parse_mqtt_url` to `skyherd/common/`. Import from one place. | **S** |

**P1 total: ~one day.**

---

## P2 — Post-hackathon cleanup (Mon+)

Quality hygiene. Don't let this rot; each item compounds.

| # | ID | Module | Task | Effort |
|---|----|--------|------|--------|
| 16 | **H3** | `tests/agents/test_cost.py` | Delete `TestPricingConstants` tautologies. Add real behavior tests for token cost math. | **S** |
| 17 | **H4** | `agents/mesh_neighbor.py` | Drop the unused `meshes` param from `CrossRanchMesh.__init__` or actually route through them. | **S** |
| 18 | **H8** | `world/predators.py` + scenarios | Add `predator_spawner.set_state(id, new_state)` with a lock. Replace in-place list replacements. | **M** |
| 19 | **H9** | `attest/ledger.py` | Add `verify_since(seq)` incremental path. Document the O(N) full verify explicitly. | **M** |
| 20 | **M1** | `demo/hardware_only.py` | Split into 4 files by responsibility (orchestrator, edge_pair, drone_handoff, timing). | **L** |
| 21 | **M2** | `agents/mesh_neighbor.py` | Collapse broadcaster+listener+mesh into one `CrossRanchBus` class (~150 lines). | **L** |
| 22 | **M4** | `tests/agents/` | Move `_make_session()` + event builders into `tests/agents/conftest.py`. | **S** |
| 23 | **M5** | `vision/heads/` | Extract `ThresholdHead` base. Reconfigure the 7 heads as config instances. | **L** |
| 24 | **M6** | `attest/ledger.py` + `sensors/bus.py` + `edge/watcher.py` | Single `skyherd/common/canonical.py::canonical_json`. Delete duplicates. | **S** |
| 25 | **M7** | all | Rename generic `handler` / `run` / `process` to intent-specific names. `ripgrep` first, then batch-rename. | **M** |
| 26 | **M8** | `tests/scenarios/test_coyote.py` | Delete the `test_breach_at_constant` tautology. | **S** |
| 27 | **M9** | `mcp/rancher_mcp.py` | Decide: add "medium" to `_URGENCY_LEVELS` with explicit mapping, or reject unknown urgency with an error. | **S** |
| 28 | **M10** | `agents/herd_health_watcher.py` | Narrow the `_try_run_classify_pipeline` exception handler to `ImportError, FileNotFoundError`. | **S** |
| 29 | **M11** | `agents/session.py` | Make `Session._ticker: CostTicker` non-optional. Drop `if session._ticker:` guards. | **S** |
| 30 | **M12** | `tests/` | `tests/conftest.py::default_world` fixture. Replace `make_world(seed=42, config_path=...)` copies. | **M** |
| 31 | **M13** | `agents/spec.py` | Pin the model to a date-versioned alias in `agents/_models.py`. | **S** |
| 32 | **M14** | `scenarios/base.py` | `run_all` returns nonzero exit code on any scenario failure; add `--fail-fast`. | **S** |

**P2 total: ~2-3 days spread across a week.**

---

## P3 — Nice-to-have polish

| # | ID | Module | Task | Effort |
|---|----|--------|------|--------|
| 33 | **L1** | 20+ files | Sweep `# noqa: BLE001` occurrences. Replace with specific exception types + `logger.exception`. | **M** |
| 34 | **L2** | `drone/sitl.py` | Use `if TYPE_CHECKING: import mavsdk` for type-only imports. Drop `type: ignore[name-defined]`. | **S** |
| 35 | **L3** | `vision/heads/foot_rot.py` | `clamped = min(int(round(score)), 5)` to avoid float-key KeyError. | **S** |
| 36 | **L4** | `server/app.py:52` | Define `PROJECT_ROOT` once in `skyherd/__init__.py`. | **S** |
| 37 | **L5** | multiple | Audit orphan TODO-shaped comments; add ticket IDs or delete. | **S** |
| 38 | **L6** | `scenarios/base.py` | Rename shadowed `e` loop vars to `event` / `entry`. | **S** |

---

## Grouped by module (when you want to do a module-wide sweep)

- **`src/skyherd/agents/`**: C1, C2 (via events.py), H1, H2, H4, H7, M4, M11, M13 → agent rewrite sprint
- **`src/skyherd/sensors/`**: C4, H12, M6 → bus+canonical consolidation
- **`src/skyherd/drone/`**: C5, M3, L2, L3 → drone reliability sprint
- **`src/skyherd/scenarios/`**: H6, H8, M8, M12, M14 → scenario immutability pass
- **`src/skyherd/server/`**: C2, H10, H11, L4 → server correctness pass
- **`src/skyherd/voice/`**: C3 → Wes sanitizer fix
- **`src/skyherd/mcp/`**: C6, M9 → rancher MCP error-handling pass
- **`src/skyherd/vision/`**: H5, M5 → pipeline performance + head refactor
- **`src/skyherd/attest/`**: H9 → (good code, minor incremental-verify add)
- **`src/skyherd/demo/`**: M1 → file split

---

## Triage protocol if behind schedule

If the Fri noon Sim Completeness Gate is at risk:

1. **Must-fix, non-negotiable**: C1, C2, C3, C6 (four items, ~1 engineer-half-day). Anything else can slide.
2. **Sacrifice before C1-C3**: M-level cleanup, L-level polish, test-theater removal. The judges don't read your test suite; they watch the video and poke the repo.
3. **If C1 (prompt caching) is truly infeasible by Sat 6pm**: **stop claiming it** in the pitch. Edit `VISION.md` / submission summary / README to not promise what the code doesn't do. Lying to judges about platform-feature usage is the worst possible outcome.

**Hard rule**: do NOT ship with C1 broken AND the pitch still claiming "aggressive prompt caching." One has to change.
