---
phase: 5
phase_slug: hardware-h1-software-prep
title: Hardware H1 Software Prep — Pi 4 + PiCamera emulator + cardboard-coyote harness
created: 2026-04-24
submission_deadline: 2026-04-26T20:00-05:00
---

# Phase 5 — CONTEXT

## Why this phase now

Hackathon submission is 2026-04-26 20:00 EST. Phases 6/7/8 all consume the Pi→bus→agents plumbing laid here. The sim is locked (Phase 0-4 shipped, 1438→1480 tests, 89.13% cov). This phase takes the **physical-side affordances** from concept to reproducible software — so when George plugs in a Pi on Friday 4/24, the path to "sensor live on dashboard" is `curl bootstrap | bash`.

Actual Pi hardware never runs in this phase; everything is built and verified on the dev machine. The Pi is a deploy target, not a test dependency.

## What already exists (Phase 4 handoff)

- `src/skyherd/edge/` — `camera.py` (PiCamera/MockCamera/get_camera), `detector.py` (RuleDetector, MegaDetectorHead), `watcher.py` (EdgeWatcher full async loop with healthz/heartbeat/MQTT), `cli.py` (skyherd-edge run/smoke), `configs/` (per-Pi env examples), `systemd/skyherd-edge.service`.
- `scripts/provision-edge.sh` — ssh-pipe provisioner, 8 steps, writes `/etc/skyherd/edge.env`, installs systemd.
- `docs/HARDWARE_PI_EDGE.md` + `docs/HARDWARE_PI_FLEET.md` — per-unit + fleet runbooks.
- `tests/edge/` — 4 test files (camera, watcher, heartbeat, fleet). ~1500 tests project-wide.
- `src/skyherd/vision/heads/pinkeye.py` — MobileNetV3-Small on-device classifier; weights bundled in `src/skyherd/vision/_models/pinkeye_mbv3s.pth`, load is deterministic (`torch.use_deterministic_algorithms`).
- `src/skyherd/sensors/trough_cam.py` — canonical schema for `skyherd/{ranch}/trough_cam/{cam_id}` wire format.
- `src/skyherd/sensors/thermal.py` — canonical schema for `skyherd/{ranch}/thermal/{cam_id}` + `predator.thermal_hit` alert fan-out.

## What this phase adds

| Requirement | Deliverable | Location |
|---|---|---|
| H1-01 | `bootstrap.sh` — curl-pipe-able **one-shot** Pi installer. Reads `credentials.json` (wifi + mqtt) from stdin or local file. Thin wrapper over existing `scripts/provision-edge.sh` with credential ingestion. | `hardware/pi/bootstrap.sh` + `hardware/pi/credentials.example.json` |
| H1-02 | `picam_sensor.py` — higher-level sensor emitter. On Pi captures via `picamera2`; on dev machine loops a sample-frame directory. Runs MobileNetV3-Small pinkeye head on each frame; emits `skyherd/{ranch}/trough_cam/{cam_id}` payloads matching `TroughCamSensor` schema. Deterministic when `seed` is passed. | `src/skyherd/edge/picam_sensor.py` + `tests/edge/test_picam_sensor.py` |
| H1-03 | `coyote_harness.py` — deterministic thermal-frame generator. Plays pre-recorded thermal PNG sequence (from `tests/fixtures/thermal_clips/`) and publishes to `skyherd/{ranch}/thermal/{cam_id}` + `predator.thermal_hit` with identical-per-seed frame order. | `hardware/cardboard_coyote/coyote_harness.py` + `tests/hardware/test_coyote_harness.py` + `tests/fixtures/thermal_clips/*.png` |
| H1-04 | `HARDWARE_H1_RUNBOOK.md` — consolidation doc. Judge-facing: one page that links `HARDWARE_PI_EDGE.md` + new `bootstrap.sh` + `picam_sensor` + `coyote_harness` + troubleshooting grid. | `docs/HARDWARE_H1_RUNBOOK.md` |
| H1-05 | `test_h1_mqtt_bridge.py` — in-process `amqtt` broker + EdgeWatcher + coyote harness + ledger + server SSE. Asserts: Pi event → MQTT → dashboard SSE → ledger attest chain, all ordered correctly, in < 5 s. | `tests/hardware/test_h1_mqtt_bridge.py` |
| H1-06 | Edge CLI scaffold + subcommands. Extend `edge/cli.py` with `picam` (drive picam_sensor) and `coyote` (drive coyote_harness). | `src/skyherd/edge/cli.py` (extend) |

## Hard constraints

- **Determinism** — `make demo SEED=42 SCENARIO=all` byte-identical across replays. Nothing in this phase runs inside `make demo`; but coyote_harness.py in seeded mode must yield byte-identical frame order on replay (regression-tested in test_coyote_harness).
- **Coverage** — ≥80% overall (global gate); ≥85% on `src/skyherd/edge/picam_sensor.py`; ≥85% on everything new in `hardware/cardboard_coyote/coyote_harness.py`.
- **MIT only** — pinkeye MobileNetV3-Small is MIT via torchvision. MegaDetector V6 MIT. No AGPL imports.
- **Zero new runtime deps** — guardrail `try: from picamera2 import ...; except ImportError: ...`. Degrade to PIL sample loader on non-Pi. `cv2` for thermal MP4 ingestion is already in deps (`opencv-python-headless`).
- **Sim-first preserved** — nothing in this phase requires actual Pi hardware to run `make test`, `make ci`, or `make demo`.
- **Zero-attribution commits** — global git config enforced.

## Scope boundaries (out of scope)

- Physical Pi hardware flashing/SSH/cabling — manual steps live in `HARDWARE_PI_EDGE.md`.
- SITL drone takeoff wiring — Phase 6.
- Mavic app updates — Phase 7.
- LoRa collar firmware — Phase 8.
- Thermal camera physical integration (real FLIR) — manual, deferred; `coyote_harness.py` is the sim-side substitute.

## Plans

- **05-01** — Edge CLI extension + bootstrap.sh + H1 package manifest. *Foundational; enables downstream plans.*
- **05-02** — `picam_sensor.py` with Pi/non-Pi fork + pinkeye on-device head + trough_cam schema + 20+ tests.
- **05-03** — `coyote_harness.py` deterministic thermal clip generator + thermal_clips fixtures + 15+ tests.
- **05-04** — `HARDWARE_H1_RUNBOOK.md` + `test_h1_mqtt_bridge.py` integration test + final verification.

## Risks

- **amqtt in-process broker flakiness** — mitigate by using aiomqtt against a port-per-test mosquitto, fall back to a recorded-publish stub if amqtt is unstable. (Test_fleet.py uses this pattern already.)
- **pinkeye model load time** — ~100ms first call, then cached via `lru_cache`. Budget: tests < 5 s each including first-call warmup. Mitigate by mocking `_get_model()` in unit tests, integration test tolerates warmup.
- **PIL sample-loop determinism** — iterate filenames sorted lexicographically, include seed in frame-ts provider so replay is reproducible.

## Context refs

- `docs/HARDWARE_PI_EDGE.md` — existing Pi single-unit runbook
- `docs/HARDWARE_PI_FLEET.md` — two-Pi fleet topology
- `src/skyherd/sensors/trough_cam.py` — canonical trough_cam.reading schema
- `src/skyherd/sensors/thermal.py` — canonical thermal.reading + predator.thermal_hit
- `src/skyherd/vision/heads/pinkeye.py` — MobileNetV3-Small pattern
- `src/skyherd/edge/watcher.py` — EdgeWatcher async pattern to mirror
- `.planning/phases/04-.../04-SUMMARY.md` — previous phase working pattern
