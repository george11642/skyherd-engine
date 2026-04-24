---
phase: 6
phase_slug: hardware-h2-software-prep
title: Hardware H2 Software Prep — Desk coyote → SITL drone takeoff
created: 2026-04-24
submission_deadline: 2026-04-26T20:00-05:00
---

# Phase 6 — CONTEXT

## Why this phase now

Phase 5 landed the Pi-side emitter surface: `PiCamSensor` publishes pinkeye readings, `CoyoteHarness` publishes thermal clips + `predator.thermal_hit` alerts.  Today those are consumed only by the in-process mesh in unit tests.  Phase 6 completes the hero demo chain on the **software side** — Pi sensor events must reach `FenceLineDispatcher`, which must call the real `drone_mcp.launch_drone` tool, which must upload a real MAVLink mission to the SITL drone, which must fly the mission and then return-to-launch if SITL dies mid-flight.

Physical hardware (Mavic + cardboard coyote) arrives Friday 4/24.  All the software has to be ready by then, verified on one laptop against SITL in a single `docker compose up`, so the integration pass on Friday is a plug-in-and-it-works demonstration — not a debug session.

## What already exists (Phase 5 handoff)

### Edge emitters
- `src/skyherd/edge/picam_sensor.py` — publishes `skyherd/{ranch}/trough_cam/{cam_id}` (pinkeye readings, 91% coverage, seeded deterministic).
- `src/skyherd/edge/coyote_harness.py` — publishes `skyherd/{ranch}/thermal/{cam_id}` **and** `skyherd/{ranch}/alert/thermal_hit` (schemas match `ThermalCamSensor`, 94% coverage, seeded deterministic, `ts_provider` injectable).
- `src/skyherd/edge/cli.py` — subcommands: `run`, `smoke`, `picam`, `coyote`, `verify-bootstrap`.
- `tests/hardware/test_h1_mqtt_bridge.py` — `InMemoryBroker` wildcard router, 11 passing integration tests, <1 s wall time.

### Drone layer
- `src/skyherd/drone/interface.py` — `DroneBackend` ABC (`connect`, `takeoff`, `patrol`, `return_to_home`, `play_deterrent`, `get_thermal_clip`, `state`, `disconnect`).  `DroneError`, `DroneUnavailable`, `DroneTimeoutError` hierarchy.
- `src/skyherd/drone/stub.py` — pure in-memory `StubBackend` (tests), no Docker.
- `src/skyherd/drone/sitl.py` — MAVSDK-backed SITL backend for real missions.
- `src/skyherd/drone/sitl_emulator.py` — pymavlink-only emulator used by `scripts/sitl_smoke.py`.
- `src/skyherd/mcp/drone_mcp.py` — `launch_drone`, `return_to_home`, `play_deterrent`, `get_thermal_clip`, `drone_status` MCP tools; validates tone 4k–22k Hz.
- `docker-compose.sitl.yml` + `docker/sitl.Dockerfile` — existing ArduPilot SITL stack.

### Agent layer
- `src/skyherd/agents/fenceline_dispatcher.py` — `FENCELINE_DISPATCHER_SPEC` with wake_topics `skyherd/+/fence/+`, `skyherd/+/thermal/+`.  `handler()` branches: API-key present → Claude SDK cycle; absent → `_simulate_handler` which calls `agents/simulate.fenceline_dispatcher`.  Simulation emits deterministic `get_thermal_clip` / `launch_drone` / `play_deterrent` / `page_rancher` tool-call dicts.
- No component today subscribes to `skyherd/+/thermal/+` **outside** of in-process simulation.  The wire from an external MQTT publisher → a running `FenceLineDispatcher` loop is missing.

### Attestation
- `src/skyherd/attest/ledger.py` — `Ledger.append(source, kind, payload, memver_id=None)` — Ed25519-signed Merkle chain, canonical-JSON payload, `GENESIS_PREV_HASH = "GENESIS"`.  `iter_events(since_seq=0)` for read.  `_WALL_CLOCK_TS` is injectable via module attribute.

### Make targets (pre-Phase 6)
- `demo`, `dashboard`, `dashboard-mock`, `sitl-up`, `sitl-down`, `bus-up`, `bus-down`, `mesh-smoke`, `hardware-demo` (hardware-only, `DRONE_BACKEND=mavic`, requires hardware).
- No `h2-smoke`, no laptop-only hardware-demo, no SITL-based hardware-demo.

## What this phase adds

| Requirement | Deliverable | Primary files |
|---|---|---|
| H2-01 | `pi_to_mission.py` — async MQTT subscriber that routes `thermal.reading` / `fence.breach` events through `FenceLineDispatcher.handler()` (simulation path), extracts the resulting `launch_drone` tool call, and executes it against a real `DroneBackend`.  Seed- and clock-injectable.  Emits attestation entries at every step. | `src/skyherd/edge/pi_to_mission.py` + `tests/edge/test_pi_to_mission.py` |
| H2-02 | `hardware-demo.yml` — laptop-local docker-compose.  Boots mosquitto + SITL (pulls `ardupilot/ardupilot-sitl:Copter-4.5.7` image) + skyherd live server + a `skyherd-edge coyote` container that drives the CoyoteHarness on a 2-s interval.  Image pulls gated by the `hardware-demo` target — NOT by unit tests. | `docker-compose.hardware-demo.yml` + `docker/hardware-demo-edge.Dockerfile` |
| H2-03 | `speaker_bridge.py` — subscribes to `skyherd/{ranch}/deterrent/play` MQTT events, plays a bundled MP3 to the OS audio device.  Guarded ImportError for `pygame`/`pydub`/`simpleaudio`; `SKYHERD_DETERRENT=mute` forces no-audio path.  No new runtime deps. | `src/skyherd/edge/speaker_bridge.py` + `tests/edge/test_speaker_bridge.py` + `src/skyherd/edge/fixtures/deterrent/predator_8khz.mp3` |
| H2-04 | `test_h2_sitl_failover.py` — chaos-monkey test: kills MAVSDK connection mid-mission, asserts RTL is triggered and an attestation `sitl.failover` entry is written.  Uses mocked MAVSDK to avoid real docker dep in CI. | `tests/hardware/test_h2_sitl_failover.py` + `tests/fixtures/fake_sitl.py` |
| H2-05 | `test_h2_e2e.py` — end-to-end in-process: CoyoteHarness emits → InMemoryBroker → `pi_to_mission` dispatches → `FenceLineDispatcher` simulated path → `drone_mcp.launch_drone` against StubBackend → RTL → attestation chain verifies.  < 10 s wall time. | `tests/hardware/test_h2_e2e.py` |
| H2-06 | `hardware-demo` target updated (laptop path) + new `h2-smoke` (fast unit-level chain check, <5s). | `Makefile` |

## Hard constraints

- **Determinism** — `make demo SEED=42 SCENARIO=all` remains byte-identical.  `pi_to_mission.py` and `speaker_bridge.py` **must not import `time.time` at module level or call wall-clock APIs without a `ts_provider` injection hook** (same pattern as CoyoteHarness).
- **Coverage** — keep overall ≥ 87.42% (current baseline after Phase 5), and require ≥ 85% on both new modules (`pi_to_mission.py`, `speaker_bridge.py`).
- **No new runtime deps** — keep `pyproject.toml` unchanged.  Audio guarded via `try/except ImportError`; speaker_bridge degrades to no-op + log.
- **MIT only** — no AGPL imports (already enforced project-wide).
- **SITL image** — pulled only by `hardware-demo` target and CI.  Unit tests use `tests/fixtures/fake_sitl.py` mocks.
- **Offline-tolerant tests** — every test in `tests/edge/` and `tests/hardware/` must run on an airplane.
- **Attestation chain integrity** — every externally-observable event in the pi_to_mission path (event received, mission uploaded, RTL triggered, deterrent played) produces one ledger append.

## What's NOT in scope

- **Real Mavic integration** — that's Phase 7.
- **Physical collar firmware** — Phase 8.
- **Multi-ranch handoff over `pi_to_mission`** — the subscriber stays single-ranch (topic prefix from env); cross-ranch is already wired in Phase 2.
- **Changing `drone_mcp.py` tool signatures** — must stay backwards compatible.
- **Pinkeye → vet intake** — already wired in Phase 5 + scenarios/sick_cow.
- **Replacing `docker-compose.sitl.yml`** — Phase 6 adds a **separate** `docker-compose.hardware-demo.yml` for the laptop demo.

## Risks + mitigations

- **Risk:** real SITL image pull hangs in constrained CI.  **Mitigation:** compose file has `SITL_IMAGE` env override; unit tests never pull it; `h2-smoke` target works against the FakeSITL mock.
- **Risk:** audio playback on headless CI.  **Mitigation:** `SKYHERD_DETERRENT=mute` is the default in CI (`tests/conftest.py` sets it); `speaker_bridge.play()` returns `NopResult` without importing audio libs.
- **Risk:** MQTT subscription races in `pi_to_mission.run()` cause flaky tests.  **Mitigation:** `pi_to_mission.handle_event()` is pure-async and directly callable from tests; `run()` is a thin loop over it.
- **Risk:** Determinism regression because MAVSDK backend timestamps creep into the chain.  **Mitigation:** all timestamps flow through `Ledger._ts` or CoyoteHarness `ts_provider`; tests freeze both with fixed values.

## Execution order (plans)

1. **06-01** — `pi_to_mission.py` + `FenceLineDispatcher` wire + unit tests.  Event received → dispatcher → `launch_drone` tool call invoked against StubBackend → attestation recorded.
2. **06-02** — `speaker_bridge.py` + deterrent MP3 + mocked-audio tests.  Subscribes to `deterrent/play`, routes to audio device or no-op.
3. **06-03** — `docker-compose.hardware-demo.yml` + edge Dockerfile + Makefile targets (`hardware-demo-sim`, `h2-smoke`) + `HARDWARE_H2_RUNBOOK.md`.
4. **06-04** — chaos-monkey SITL failover test + E2E integration test + coverage audit + VERIFICATION doc.

## Acceptance gates (phase-level)

- `pytest` passes on both new modules at ≥85% coverage each.
- Overall coverage ≥87% (no regression from 89.35%).
- `test_h2_e2e.py` runs in <10 s wall time.
- `make h2-smoke` completes in <5 s.
- `make demo SEED=42 SCENARIO=all` still byte-identical (determinism gate).
- `make hardware-demo-sim` documented and lint-clean (may not run in constrained sandbox — that's fine, it's a judge-facing demo target).
- Attestation chain verifies end-to-end when the E2E test runs.

## File-delta estimate

- **New code:** ~900 LOC (pi_to_mission ~220, speaker_bridge ~180, fake_sitl ~140, docker + Makefile ~60, tests ~300)
- **Modified code:** ~40 LOC (Makefile targets, edge/cli.py passthrough).
- **New tests:** ~55 tests across 4 files.
- **New docs:** `docs/HARDWARE_H2_RUNBOOK.md`.
