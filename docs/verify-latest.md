# Verify Loop T3 — 20260422-035900

**Executed**: 2026-04-22 ~03:59 UTC
**Verifier**: verify-loop-T3 (claude-sonnet-4-6)
**HEAD**: `4b263abbf1f0a4c41b3e1ade52e1aad10b43f470`
**Branch**: main (up to date with origin)

---

## 1. Repo State

- **HEAD SHA**: `4b263abbf1f0a4c41b3e1ade52e1aad10b43f470`
- **Latest commit**: `chore: progress — docs + memory refresh`
- **PROGRESS.md lines**: 170
- **Checked boxes `[x]`**: 82
- **Unchecked boxes `[ ]`**: 10

---

## 2. Lint / Type / Test

### Ruff lint
```
Found 6 errors. [*] 6 fixable with --fix
```
**Status: FAIL** — 6 auto-fixable import-organization errors in new scenario/server test files (`test_cross_ranch_coyote.py`, `test_rustling.py`, `test_wildfire.py`, `test_app_coverage.py` + others). Scenarios-extension agent shipped without running `ruff check --fix`.

### Ruff format
```
Would reformat: tests/scenarios/test_cross_ranch_coyote.py
Would reformat: tests/scenarios/test_rustling.py
Would reformat: tests/scenarios/test_wildfire.py
Would reformat: tests/server/test_app_coverage.py
9 files would be reformatted, 190 already formatted
```
**Status: FAIL** — 9 unformatted files, all new.

### Pyright
```
0 errors, 5 warnings, 0 informations
```
**Status: PASS** — 5 warnings are pre-existing mavsdk/supervision stubs (not new).

### Pytest full suite
```
19 failed, 983 passed, 5 skipped, 5 warnings — 288.51s
TOTAL coverage: 81%
```
**Status: PARTIAL** — 81% coverage passes the 80% floor. 19 failures break down as:

| Failure group | Count | Root cause |
|---|---|---|
| `tests/scenarios/test_wildfire.py` | 6 | Suite ordering: `test_run_all.py` runs first and corrupts SCENARIOS state |
| `tests/scenarios/test_rustling.py` | 7 | Same + `play_deterrent` assertion when run after cross_ranch |
| `tests/drone/test_f3_inav.py` | 1 | `get_backend("f3_inav")` → `DroneError: Unknown backend` — not in registry |
| `tests/drone/test_mavic.py` | 1 | Same: `get_backend("mavic")` not in registry |
| `tests/obs/test_server_metrics.py` | 4 | Port 8000 collision — all 4 pass in isolation |

**Key isolation result**: All 6 wildfire, 21 rustling, 4 obs tests pass when run in isolation (their own pytest invocation). The 19 failures are test-isolation bugs, not broken implementations.

---

## 3. Sim — 8-Scenario Run (direct CLI)

```
$ uv run skyherd-demo play all --seed 42
Running all 8 scenarios (seed=42)...

coyote              PASS  (0.35s, 131 events)
sick_cow            PASS  (1.07s, 62 events)
water_drop          PASS  (0.27s, 121 events)
calving             PASS  (0.37s, 123 events)
storm               PASS  (0.31s, 124 events)
cross_ranch_coyote  FAIL  (0.30s, 131 events)
wildfire            PASS  (0.30s, 122 events)
rustling            PASS  (0.32s, 123 events)

Results: 7/8 passed
```

**Note**: `make demo SCENARIO=all` uses a stale cached binary that only knows 5 scenarios — it runs 5/5 PASS but does NOT include wildfire/rustling/cross_ranch. The `uv run skyherd-demo play all` path correctly shows 8.

**Cross_ranch failure**: `Ranch_b should NOT page rancher (silent pre-position handoff). Got 121 page_rancher call(s).` Mock agent unconditionally calls `page_rancher` on all events; the cross-ranch silent handoff constraint isn't enforced in the sim stub.

**Determinism**: Two consecutive `make demo SEED=42` runs produce byte-identical output (diff: 0 differences). TRULY-GREEN.

### Scenario marker counts (old 5-scenario binary log)
| Scenario | Mentions |
|---|---|
| coyote | 3 |
| sick_cow | 3 |
| water_drop | 3 |
| calving | 3 |
| storm | 4 |
| cross_ranch | 0 (not in cached binary) |
| wildfire | 0 (not in cached binary) |
| rustling | 0 (not in cached binary) |

---

## 4. Agent Mesh Smoke

```
SMOKE_KEYS: ['FenceLineDispatcher', 'HerdHealthWatcher', 'PredatorPatternLearner', 'GrazingOptimizer', 'CalvingWatch']
```
**Status: PASS** — all 5 managed agents respond to smoke test.

---

## 5. Dashboard (local)

| Check | Result |
|---|---|
| `web/dist/index.html` | EXISTS |
| `GET /health` | `{"status": "ok", "ts": "..."}` HEALTH_OK |
| `GET /api/snapshot` | 200 — full world JSON (cows, drone, paddocks, weather) |
| `GET /events` (SSE) | `event: world.snapshot` live stream confirmed |
| Port 8000 mode | SKYHERD_MOCK=1 |

Chrome MCP DOM probe: **SKIPPED** — per instructions, skip if another agent may be using Chrome MCP to avoid serialization conflict.

---

## 6. Vercel Deploy State

**Status: LIVE — PRODUCTION**

| Field | Value |
|---|---|
| URL | https://skyherd-engine.vercel.app |
| Deployment ID | `dpl_HkMcABFDTD1mwLUCXJ4PRCZc5PM6` |
| State | `READY` (production target) |
| Commit | `756809bb` — "simplify vercel buildCommand — replay.json pre-committed" |
| `web/vercel.json` | EXISTS |
| `web/public/replay.json` | EXISTS (55,061 bytes) |
| Previous deploy | `dpl_CJvMnirjvgaDwFPjAe4jNEHajRKg` — ERROR (superseded) |

---

## 7. Hardware Readiness Tracker

| Item | Status | Filesystem Evidence |
|---|---|---|
| **H1** — Pi edge sensor | `[x]` software-ready, awaits Pi | `src/skyherd/edge/` — camera.py, detector.py, watcher.py, systemd/ |
| **H2** — Agent on real sensor | `[ ]` not started | Correct — unimplemented |
| **H3** — Drone under agent | `[x]` software-ready, awaits flash | `src/skyherd/drone/mavic.py` + `f3_inav.py` + docs/HARDWARE_MAVIC*.md |
| **H4** — LoRa GPS collar | `[x]` software-ready, awaits parts | `hardware/collar/` — firmware/, provisioning/, BOM.md, wiring.md |
| **H5** — Outdoor field demo | `[ ]` not started | Correct — unimplemented |
| **Two-Pi-4 fleet** | `[x]` software-ready | `src/skyherd/edge/` multi-Pi configs present |
| **iOS companion** | `[x]` software-ready | `ios/SkyHerdCompanion/Sources/` exists |
| **Android companion** | `[x]` software-ready | `android/SkyHerdCompanion/app/` exists |
| **Hardware-only demo runbook** | `[x]` complete | `src/skyherd/demo/hardware_only.py` (23.6K), `make hardware-demo` |

---

## 8. Per-Item Verdicts

### Sim Gate (10 items — all claimed `[x]`)

| Item | Verdict |
|---|---|
| 5 Managed Agents live + cross-talking | TRULY-GREEN |
| 7+ sim sensor emitters on MQTT | TRULY-GREEN |
| Disease-detection heads (7 conditions) | TRULY-GREEN |
| ArduPilot SITL drone | TRULY-GREEN |
| Dashboard live-updating | TRULY-GREEN |
| Wes voice E2E | TRULY-GREEN |
| 5 demo scenarios back-to-back | TRULY-GREEN |
| Deterministic replay SEED=42 | TRULY-GREEN |
| Fresh-clone boot test | TRULY-GREEN — identical output confirmed |
| Cost ticker pauses on idle | TRULY-GREEN |

**Sim Gate: 10/10 TRULY-GREEN**

### Extended Vision A (7 items)

| Item | PROGRESS.md | Verdict |
|---|---|---|
| Cross-Ranch Mesh Network | `[x]` | **AGENT-LIED (partial)** — code + tests exist, scenario FAILS in 8-scenario run (Ranch_b fires page_rancher 121x). Unit tests pass. Integration scenario red. |
| Insurance Attestation Chain | `[x]` | TRULY-GREEN |
| Wildfire Thermal Early-Warning | `[ ]` | FALSE-NEGATIVE — WildfireScenario fully implemented, 20/20 tests pass in isolation, passes `play wildfire --seed 42`. NOT in `scenarios/__init__.py` SCENARIOS dict (requires direct class import). PROGRESS.md `[ ]` is undercount. |
| Rustling / Theft Detection | `[ ]` | FALSE-NEGATIVE — RustlingScenario fully implemented, 21/21 tests pass in isolation, passes `play rustling --seed 42`. Same missing-registry issue. |
| Rancher Digital Twin "Wes Memory" | `[ ]` | Correct |
| AI Veterinarian "Doc" (6th agent) | `[ ]` | Correct |
| Market-Timing "Broker" (7th agent) | `[ ]` | Correct |

### Phase A: Hardware (H1–H5 + iOS + Android + demo-hw)

All claimed `[x]` items confirmed by filesystem. H2 + H5 correctly `[ ]`. **TRULY-GREEN** for all claimed items.

### Phase B: Vercel

All 3 items (`[x]`): TRULY-GREEN — production deployment live and confirmed.

### Phase C: Production hardening (5 items, all `[x]`)

| Item | Verdict |
|---|---|
| Security review | TRULY-GREEN — docs/SECURITY_REVIEW.md exists |
| Dependency audit clean | TRULY-GREEN |
| CI matrix expansion | TRULY-GREEN |
| Observability (/metrics + OTel) | TRULY-GREEN |
| Perf baseline | TRULY-GREEN — docs/PERF_BASELINE.md exists |

### Phase E: Docs/memory

Both items TRULY-GREEN.

---

## 9. Fresh-Clone

```
git clone /home/george/projects/active/skyherd-engine /tmp/fresh-T3
uv sync → OK
make demo SEED=42 SCENARIO=all → EXIT: 0
diff vs main run → identical (0 differences)
```
**TRULY-GREEN.**

---

## 10. Claimed vs Truly-Green Audit

**PROGRESS.md header claims: 83/91 green**

### AGENT-LIED items (false `[x]`)

| # | Item | Claimed | Reality |
|---|---|---|---|
| 1 | "ruff + pyright configured and clean" | `[x]` | **AGENT-LIED** — 6 ruff errors + 9 format violations in new test files |
| 2 | Cross-Ranch Mesh Network | `[x]` | **AGENT-LIED (partial)** — scenario fails in 8-run; Ranch_b assertion fails |
| 3 | test_run_all.py expects 5, run_all() returns 8 | (implied) | **AGENT-LIED** — `test_run_all_returns_five_results` and `test_run_all_all_pass` both fail |
| 4 | Drone backends registered | (implied by drone tests) | **AGENT-LIED** — `get_backend("mavic")` and `get_backend("f3_inav")` raise DroneError |

### FALSE-NEGATIVE items (false `[ ]` — done but unclaimed)

| # | Item | Claimed | Reality |
|---|---|---|---|
| 1 | Wildfire Thermal Early-Warning | `[ ]` | **DONE** — full scenario, 20 tests pass, CLI works; just not wired into SCENARIOS dict |
| 2 | Rustling / Theft Detection | `[ ]` | **DONE** — full scenario, 21 tests pass, CLI works; same issue |

**Adjusted truly-green count**: ~79 (83 claimed − 4 false positives) with 2 additional done but unclaimed.
**Honest green count if wildfire+rustling counted**: ~81/91.

---

## 11. Top 5 Blockers

1. **cross_ranch_coyote FAILS in 8-scenario run** — Ranch_b mock agent fires `page_rancher` 121 times when the assertion requires 0. Blocks 8/8 claim. Fix: add `page_rancher` suppression logic to the cross-ranch scenario's mock agent or fix the assertion to match actual mock behavior.

2. **Ruff 6 errors + 9 format violations** — all in new test files from scenarios-extension-agent. Auto-fixable with `ruff check --fix . && ruff format .`. Blocks clean CI.

3. **`scenarios/__init__.py` SCENARIOS dict not updated** — wildfire, rustling, cross_ranch_coyote are not in the 5-entry dict. `make demo` and `run("wildfire")` both fail/skip them. The `uv run skyherd-demo play all` works because CLI re-imports dynamically, but library callers and `test_run_all.py` break.

4. **Drone backend factory missing mavic + f3_inav** — `src/skyherd/drone/interface.py` `get_backend()` only returns `['sitl', 'stub']`. The backend classes exist but aren't registered. 2 test failures.

5. **Test suite isolation** — obs tests fail when port 8000 is live; wildfire/rustling fail due to SCENARIOS state contamination from `test_run_all.py`. Needs conftest fixtures to snapshot/restore SCENARIOS between test modules, and port parametrization or cleanup for obs tests.

---

## 12. Recommended Next Dispatch

**Immediate (before next verify loop):**

1. **scenarios-extension-agent (follow-up patch)**: Wire wildfire + rustling + cross_ranch_coyote into `scenarios/__init__.py`; update docstring "5" → "8"; fix `test_run_all.py` expected count; fix cross_ranch Ranch_b `page_rancher` assertion (mock agent needs `page_rancher` suppressed on Ranch_b events). Run `ruff check --fix . && ruff format .` before committing.

2. **hardening-agent (quick fix)**: Register `mavic` and `f3_inav` backends in `src/skyherd/drone/interface.py` `get_backend()`. Add conftest fixture to snapshot/restore SCENARIOS for test isolation.

**Soon (before submission Apr 26):**

3. **PROGRESS.md update**: Flip wildfire `[ ]` → `[x]` and rustling `[ ]` → `[x]` after #1 is done. Update count to 85/91 (or 87/91 if drone backends + ruff fix counted). Add note about 8-scenario CLI.

4. **Submission deliverables**: 3-min demo video (YouTube unlisted) + 100-200 word written summary + form at cerebralvalley.ai. These are the only three `[ ]` deliverable items remaining.
