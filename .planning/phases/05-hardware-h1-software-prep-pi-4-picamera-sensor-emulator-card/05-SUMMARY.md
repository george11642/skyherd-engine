---
phase: 5
phase_slug: hardware-h1-software-prep
status: complete
completed: 2026-04-24
plans: 4
tests_before: 1480
tests_after: 1573
coverage_before: 89.13
coverage_after: 89.35
commits:
  - de85d3f feat(05-01) edge CLI bootstrap + pi bringup scaffold
  - 16df9ea feat(05-02) picam_sensor.py — Pi pinkeye sensor emulator
  - db5b946 feat(05-03) cardboard-coyote thermal harness
  - 4fac3fa docs(05-04) H1 runbook + MQTT bridge integration test + Phase 5 verification
requirements_closed: [H1-01, H1-02, H1-03, H1-04, H1-05, H1-06]
---

# Phase 5 Summary — Hardware H1 Software Prep (Pi 4 + PiCamera + cardboard-coyote)

## One-liner

Pi 4 H1 software shipped sim-first: one-command `bootstrap.sh` ingests a
`credentials.json`, `PiCamSensor` runs MobileNetV3-Small pinkeye on captured
frames, `CoyoteHarness` plays deterministic thermal clips as the cardboard-
coyote stand-in — all verified by a <1 s in-process MQTT bridge integration
test, all 8 sim scenarios + determinism gate preserved.

## Shipped

| Requirement | Scope | Status |
| --- | --- | --- |
| H1-01 | `hardware/pi/bootstrap.sh` curl-pipe installer + `credentials.example.json` + `README.md` | GREEN |
| H1-02 | `src/skyherd/edge/picam_sensor.py` — Pi/non-Pi fork, pinkeye on-device head, `trough_cam.reading` schema, deterministic seeded cycling | GREEN |
| H1-03 | `src/skyherd/edge/coyote_harness.py` — deterministic thermal clip playback, `thermal.reading` + `predator.thermal_hit` dual fan-out, 6 bundled fixture PNGs | GREEN |
| H1-04 | `docs/HARDWARE_H1_RUNBOOK.md` — judge-facing one-page runbook | GREEN |
| H1-05 | `tests/hardware/test_h1_mqtt_bridge.py` — 11 integration tests, <1 s wall time | GREEN |
| H1-06 | `skyherd-edge` CLI extended with `verify-bootstrap`, `picam`, `coyote` subcommands | GREEN |

## Metrics

- **Tests:** 1480 → **1573** (+93)
- **Coverage:** 89.13% → **89.35%** (+0.22%)
- **On new modules:**
  - `picam_sensor.py` — **91%** (target ≥85%)
  - `coyote_harness.py` — **94%** (target ≥85%)
  - `edge/cli.py` — 65% (target was 75%; miss documented in VERIFICATION)
- **Determinism:** 2/2 PASS on `test_demo_seed42_is_deterministic_3x`
- **Integration wall time:** `test_h1_mqtt_bridge.py` — **0.65 s** (target <10 s)
- **8/8 scenarios:** PASS unchanged
- **Ruff + pyright on Phase 5 files:** 0 errors, 0 warnings, 0 informations

## New files

### Code (12)
- `src/skyherd/edge/picam_sensor.py` (360 LOC)
- `src/skyherd/edge/coyote_harness.py` (260 LOC)
- `src/skyherd/edge/fixtures/__init__.py`
- `src/skyherd/edge/fixtures/picam/__init__.py`
- `src/skyherd/edge/fixtures/picam/_generate.py`
- `src/skyherd/edge/fixtures/picam/frame_00.png` … `frame_03.png`
- `hardware/pi/bootstrap.sh`
- `hardware/pi/credentials.example.json`
- `hardware/pi/README.md`
- `hardware/cardboard_coyote/__init__.py`
- `hardware/cardboard_coyote/coyote_harness.py` (re-export)

### Tests (5 files, 93 tests total)
- `tests/edge/test_cli_bootstrap.py` — 9 tests
- `tests/edge/test_picam_sensor.py` — 35 tests
- `tests/hardware/test_bootstrap_script.py` — 11 tests
- `tests/hardware/test_coyote_harness.py` — 27 tests
- `tests/hardware/test_h1_mqtt_bridge.py` — 11 tests

### Fixtures
- `tests/fixtures/__init__.py`
- `tests/fixtures/thermal_clips/__init__.py`
- `tests/fixtures/thermal_clips/_generate.py`
- `tests/fixtures/thermal_clips/frame_00.png` … `frame_05.png`
- `tests/hardware/fixtures/creds_good.json`, `creds_bad_missing_mqtt.json`, `creds_malformed.json`

### Docs / planning
- `docs/HARDWARE_H1_RUNBOOK.md`
- `.planning/phases/05-.../05-CONTEXT.md`
- `.planning/phases/05-.../05-01-PLAN.md`
- `.planning/phases/05-.../05-02-PLAN.md`
- `.planning/phases/05-.../05-03-PLAN.md`
- `.planning/phases/05-.../05-04-PLAN.md`
- `.planning/phases/05-.../VERIFICATION.md`
- `.planning/phases/05-.../05-SUMMARY.md` (this file)

## Modified files

- `src/skyherd/edge/cli.py` — +203 LOC. New subcommands: `verify-bootstrap`,
  `picam`, `coyote`. Updated docstring header to list all 5 subcommands.

## Key decisions

1. **`PiCamSensor` separate from `EdgeWatcher`** — two classes coexist rather
   than folding pinkeye into the existing watcher. EdgeWatcher stays the
   production MegaDetector watchdog; PiCamSensor is the pinkeye-focused demo
   driver.  Reason: single-responsibility + cleaner schemas (pinkeye_result vs
   detections[]).
2. **`coyote_harness.py` lives in `src/skyherd/edge/`, not `hardware/`** — Python
   import path stays clean; `hardware/cardboard_coyote/coyote_harness.py` is a
   thin re-export so judges browsing the hardware dir still find a working
   import.
3. **`InMemoryBroker` over real `amqtt`** in `test_h1_mqtt_bridge.py` — tests
   the contract (canonical JSON + topics + order) without broker-library
   timing flakiness.  Existing `tests/edge/test_fleet.py` already covers real
   amqtt behaviour.
4. **Deterministic seeded cycling via Knuth multiplicative hash** — stateless,
   gives distinct sequences per seed in short replays, preserves replay
   reproducibility.
5. **Fixture frames checked in + regeneratable** — both picam and thermal
   fixtures have `_generate.py` companions that yield byte-identical PNGs
   across runs (hash-verified in the generator's output).

## Deviations from plan

**None.**  All 4 plans executed exactly as written.

Minor coverage miss on `edge/cli.py` (65% vs 75% target) documented in
VERIFICATION.md "Deferred" section; not blocking.

## Security notes

- `credentials.json` parsing uses `json.loads` (safe), not `eval`.
- `bootstrap.sh` uses `jq` for extraction — no shell interpolation of the
  credentials file.
- `verify-bootstrap` validates root is a JSON object before iterating
  required fields (rejects arrays, numbers, etc.).
- No new secrets added to the repo; `credentials.example.json` is a template,
  real credentials live on the Pi's boot partition only.
- `bootstrap.sh` writes `/etc/wpa_supplicant/wpa_supplicant.conf` with `chmod
  600` (wifi PSK protection).
- MQTT publish paths are all best-effort; broker unreachability silently logs
  and continues (never raises or crashes the sensor loop).

## Known gaps / deferred

1. **`edge/cli.py` coverage 65% vs plan target 75%** — uncovered branches are
   long-running `run`/`smoke` subcommands and `max_ticks=None` infinite-loop
   paths. Cost to close: ~4 hours with subprocess test harness. Not blocking.
2. **No live `amqtt` broker in `test_h1_mqtt_bridge.py`** — by design (see Key
   decisions #3).  Real broker behaviour covered by existing fleet tests.
3. **Picamera2 Pi-only lines indirectly tested** — via `sys.modules` stub.
   Real hardware path is trivial (2 library method calls); physical Pi
   verification is manual per project hardline.

## Next step

Ready for **Phase 6** (Hardware H2 Software Prep — Pi → SITL drone takeoff
integration).  Phase 6 will wire:

- `CoyoteHarness` thermal_hit events → `FenceLineDispatcher` agent
- `FenceLineDispatcher` → `drone_mcp.launch_drone` → ArduPilot SITL takeoff
- `skyherd-sitl-e2e` end-to-end integration test
- docker-compose target `hardware-demo`

All the Phase 5 infrastructure (PiCamSensor, CoyoteHarness, bootstrap.sh,
edge CLI) is the launchpad — Phase 6 plugs behaviour into these plumbed pipes.

## Self-Check

Files verified present:
- ✓ `src/skyherd/edge/picam_sensor.py`
- ✓ `src/skyherd/edge/coyote_harness.py`
- ✓ `src/skyherd/edge/cli.py`
- ✓ `hardware/pi/bootstrap.sh`
- ✓ `hardware/pi/credentials.example.json`
- ✓ `hardware/pi/README.md`
- ✓ `hardware/cardboard_coyote/coyote_harness.py`
- ✓ `docs/HARDWARE_H1_RUNBOOK.md`
- ✓ `tests/hardware/test_h1_mqtt_bridge.py`
- ✓ `tests/hardware/test_coyote_harness.py`
- ✓ `tests/hardware/test_bootstrap_script.py`
- ✓ `tests/edge/test_picam_sensor.py`
- ✓ `tests/edge/test_cli_bootstrap.py`
- ✓ `tests/fixtures/thermal_clips/frame_00.png` … `frame_05.png`
- ✓ `src/skyherd/edge/fixtures/picam/frame_00.png` … `frame_03.png`

## Self-Check: PASSED
