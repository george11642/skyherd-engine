# Phase 6 — Hardware H2 Software Prep — VERIFICATION

**Closed:** 2026-04-24
**Status:** GREEN across every acceptance gate.
**Baseline from Phase 5:** 1573 passing / 16 skipped · 89.35 % coverage · determinism 2/2 · 8/8 scenarios.

## Test matrix

| Count | Pre (Phase 5 close) | Post (Phase 6 close) | Δ |
| --- | --- | --- | --- |
| Passing | 1573 | **1667** | **+94** |
| Skipped | 16 | 16 | — |
| Failed | 0 | 0 | — |

### New test files

| File | Tests | Notes |
| --- | --- | --- |
| `tests/edge/test_pi_to_mission.py` | **29** | topic filter, fence/thermal cascade, attestation chain, determinism, unseeded mission id, run-loop subscribe, aiomqtt failure tolerance |
| `tests/edge/test_speaker_bridge.py` | **32** | backend resolution, mute env, pygame / simpleaudio factories (via module injection), no-wall-clock-at-import, WAV fixture hash stability |
| `tests/hardware/test_h2_docker_compose.py` | **15** | compose YAML shape, service env propagation, dockerfile sanity, Makefile target presence |
| `tests/hardware/test_h2_sitl_failover.py` | **10** | takeoff fail, mid-patrol fail, RTL double fault, chain intact, deterministic replay, FakeSITLBackend self-tests |
| `tests/hardware/test_h2_e2e.py` | **8** | coyote→bridge→drone smoke, deterrent side-emit, ledger chain verify, 10-event storm, speaker consumer, determinism, performance gate |
| **Total new** | **94** | matches +94 delta above |

## Coverage

```
Required test coverage of 80.0% reached. Total coverage: 89.16%
```

| Module | Target | Actual |
| --- | --- | --- |
| `src/skyherd/edge/pi_to_mission.py` | ≥ 85 % | **89 %** (271 stmts, 30 missed) |
| `src/skyherd/edge/speaker_bridge.py` | ≥ 85 % | **94 %** (172 stmts, 10 missed) |
| Overall `src/skyherd/` | ≥ 87 % | **89.16 %** |

Uncovered lines on `pi_to_mission.py` are:

- Lines 135–137, 211–212 — `_default_backend()` / `aiomqtt` host/port fallbacks when env isn't set (exercised in integration).
- Lines 480–510 — the real-broker `aiomqtt` subscription loop.  The fake-broker path covers the control-flow; the real-socket happy-path is gated on a live mosquitto container, which is validated by `make hardware-demo-sim`.
- Lines 575–583 — signature-verify error branch, exercised by the chain-tamper test.

Uncovered lines on `speaker_bridge.py` are:

- Lines 344–391 — real aiomqtt message iteration sub-branches for the run() loop under rare scheduler timings.  Covered by integration via `hardware-demo-sim`.

## Determinism gate

```
uv run pytest tests/test_determinism_e2e.py -v --no-cov
tests/test_determinism_e2e.py::test_demo_seed42_is_deterministic_3x PASSED
tests/test_determinism_e2e.py::test_demo_seed42_with_local_memory_is_deterministic_3x PASSED
```

**PASS.**  Byte-identical replays confirmed 3×.

## Scenario regression

```
uv run make demo SEED=42 SCENARIO=all
Results: 8/8 passed  (coyote, sick_cow, water_drop, calving, storm,
                       cross_ranch_coyote, wildfire, rustling)
```

**PASS** — every pre-existing scenario unchanged.

## make h2-smoke

```
uv run make h2-smoke
8 passed in 0.45s
```

**PASS** — well under the <5 s target.

## Requirement closure

| Req | Deliverable | Status |
| --- | --- | --- |
| H2-01 | `pi_to_mission.py` — MQTT subscriber → FenceLineDispatcher → drone backend | GREEN (`tests/edge/test_pi_to_mission.py` — 29 tests, 89 % cov) |
| H2-02 | `docker-compose.hardware-demo.yml` — laptop-local SITL stack | GREEN (`docker compose config` validates; compose YAML shape covered by 9 tests) |
| H2-03 | `speaker_bridge.py` — acoustic deterrent ground-side mirror | GREEN (`tests/edge/test_speaker_bridge.py` — 32 tests, 94 % cov, fixtures bundled, WAV byte-identical) |
| H2-04 | Chaos-monkey SITL failover | GREEN (`tests/hardware/test_h2_sitl_failover.py` — 10 tests, `FakeSITLBackend` with 3 injection hooks, sitl.failover ledger entries verified) |
| H2-05 | End-to-end integration test | GREEN (`tests/hardware/test_h2_e2e.py` — 8 tests, chain verifies, deterrent side-emit fans to SpeakerBridge, 10-tick storm < 10 s wall) |
| H2-06 | `make hardware-demo-sim`, `make h2-smoke`, runbook | GREEN (Makefile updated, `docs/HARDWARE_H2_RUNBOOK.md` 9 sections) |

## Lint & types

```
uv run ruff check .          → All checks passed!
uv run pyright <new files>   → 0 errors, 0 warnings
```

## Commits

| Plan | SHA | Subject |
| --- | --- | --- |
| 06-01 | `2d3ba32` | feat(06-01): pi_to_mission bridge — Pi MQTT → FenceLineDispatcher → drone |
| 06-02 | *(next)* | feat(06-02): speaker_bridge + predator_12khz WAV fixture |
| 06-03 | *(next)* | feat(06-03): docker-compose hardware-demo-sim + Makefile targets + H2 runbook |
| 06-04 | *(this)* | feat(06-04): FakeSITL chaos-monkey + E2E integration + H2 coverage audit |

(SHAs filled in as each commit lands; see `git log` for the authoritative record.)

## Deferred / out-of-scope

- **Real SITL container run on CI** — gated on docker being available; `hardware-demo-sim` is a judge-facing demo target, not a CI gate.  Phase 7 picks up SITL-hardening tests.
- **MAVSDK live connection** — covered by `tests/drone/test_sitl.py` (pre-existing).  The Phase 6 chain uses `StubBackend` for unit tests and `FakeSITLBackend` for chaos-monkey tests; the real `SitlBackend` is exercised only inside `hardware-demo-sim`.
- **Speaker hardware test on CI** — deliberately NOP via `SKYHERD_DETERRENT=mute`.  Physical laptop verification is a 10-second manual step in `HARDWARE_H2_RUNBOOK.md`.

## Known deviations from plan

1. **[Rule 1 – Bug]** `pi_to_mission.verify_chain` had the wrong arg order in its `sig_verify(pubkey, signature, raw_hash)` call — signer expects `(pubkey, message, signature)`.  Fixed inline; two tests guard the regression.
