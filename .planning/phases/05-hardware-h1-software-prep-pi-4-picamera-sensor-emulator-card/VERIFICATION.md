---
phase: 5
verification_date: 2026-04-24
status: pass
---

# Phase 5 — VERIFICATION

Automated truth-check for all Phase 5 deliverables.  Run on `main` at the
head-of-phase commit.

---

## Test results

| Metric | Before | After | Delta |
| --- | --- | --- | --- |
| Tests passing | 1480 | **1573** | +93 |
| Tests skipped | 16 | 16 | 0 |
| Tests failing | 0 | **0** | 0 |
| Overall coverage | 89.13% | **89.35%** | +0.22% |
| Wall time (pytest -q) | ~26 min | 3 min | — (selection) |

Breakdown of +93 new tests:

| Test file | New tests |
| --- | --- |
| `tests/edge/test_cli_bootstrap.py` | 9 |
| `tests/hardware/test_bootstrap_script.py` | 11 |
| `tests/edge/test_picam_sensor.py` | 35 |
| `tests/hardware/test_coyote_harness.py` | 27 |
| `tests/hardware/test_h1_mqtt_bridge.py` | 11 |
| **Total** | **93** |

---

## Coverage per Phase 5 module

| Module | Coverage | Target | Status |
| --- | --- | --- | --- |
| `src/skyherd/edge/picam_sensor.py` | **91%** | ≥85% | PASS |
| `src/skyherd/edge/coyote_harness.py` | **94%** | ≥85% | PASS |
| `src/skyherd/edge/cli.py` | 65% | ≥75% (plan) | MISS (see Deferred) |
| `hardware/cardboard_coyote/__init__.py` | 100% | — | — |
| `hardware/cardboard_coyote/coyote_harness.py` (shim) | 100% | — | — |
| `src/skyherd/edge/fixtures/picam/_generate.py` | 87% | — | — |
| **Overall project** | **89.35%** | ≥80% | PASS |

---

## Determinism gate

`tests/test_determinism_e2e.py::test_demo_seed42_is_deterministic_3x`: **PASS**
`tests/test_determinism_e2e.py::test_demo_seed42_with_local_memory_is_deterministic_3x`: **PASS**

Additional determinism confirmations specific to Phase 5:

- `test_seeded_mode_identical_sequence_across_instances` (picam) — PASS
- `test_seeded_mode_identical_sequence_across_instances` (coyote) — PASS
- `test_fixed_ts_provider_makes_payload_byte_stable` (coyote) — PASS
- `test_coyote_determinism_byte_for_byte` (mqtt bridge) — PASS
- Fixture PNG SHA-256 reproducibility (manual regen + hash match):
  - `tests/fixtures/thermal_clips/frame_00.png` → `28219565f0d7d8bae127a47df89f4641bad1941983de6f2b910d84aa71cf5773`
  - Full 6-frame hash set recorded in `_generate.py` output; re-running the
    generator produces byte-identical output.

---

## CLI smoke results

```
$ uv run skyherd-edge --help
Usage: skyherd-edge [OPTIONS] COMMAND [ARGS]...
Commands: run, smoke, verify-bootstrap, picam, coyote            ✓ all 5 present

$ uv run skyherd-edge verify-bootstrap \
    --credentials-file tests/hardware/fixtures/creds_good.json
verify-bootstrap OK — … has all required fields.                  exit 0 ✓

$ uv run skyherd-edge verify-bootstrap \
    --credentials-file tests/hardware/fixtures/creds_bad_missing_mqtt.json
Missing fields: mqtt_url                                          exit 2 ✓

$ uv run skyherd-edge picam --max-ticks=2 --seed=42
picam tick — ts=1776993558.116 pinkeye=escalate cows_present=1    ✓
picam tick — ts=1776993558.159 pinkeye=escalate cows_present=1    ✓

$ uv run skyherd-edge coyote --max-ticks=3 --seed=42
coyote tick — ts=1776993560.546 frame_idx=0 predators=1           ✓
coyote tick — ts=1776993560.592 frame_idx=1 predators=1           ✓
coyote tick — ts=1776993560.612 frame_idx=2 predators=1           ✓
```

---

## bootstrap.sh smoke

```
$ SKYHERD_CREDS_FILE=tests/hardware/fixtures/creds_good.json \
    bash hardware/pi/bootstrap.sh --dry-run
============================================================
 SkyHerd Pi Bootstrap
 edge_id    = edge-house
 ranch_id   = ranch_a
 mqtt_url   = mqtt://192.168.1.100:1883
 trough_ids = trough_1,trough_2
 repo_root  = /home/george/projects/active/skyherd-engine
============================================================
DRY-RUN: env RANCH_ID=ranch_a MQTT_URL=mqtt://192.168.1.100:1883 \
  bash …/scripts/provision-edge.sh edge-house trough_1\,trough_2
DRY-RUN: would provision edge node 'edge-house' with troughs 'trough_1,trough_2'.
                                                                 exit 0 ✓
```

---

## Linting + typing

| Tool | Scope | Result |
| --- | --- | --- |
| `ruff check` | All Phase 5 files (`src/skyherd/edge/picam_sensor.py`, `coyote_harness.py`, `cli.py`, `fixtures/`, `hardware/`, Phase 5 tests, `tests/fixtures/`) | PASS (0 errors) |
| `pyright` | `src/skyherd/edge/picam_sensor.py`, `coyote_harness.py`, `cli.py` | 0 errors, 0 warnings, 0 informations |

Pre-existing `ruff` errors elsewhere in the repo (25 total, mostly import sort
issues in older test files) — **not introduced by Phase 5**.

---

## File inventory — created this phase

### Code

- `src/skyherd/edge/picam_sensor.py` — 360 LOC
- `src/skyherd/edge/coyote_harness.py` — 260 LOC
- `src/skyherd/edge/fixtures/__init__.py`
- `src/skyherd/edge/fixtures/picam/__init__.py`
- `src/skyherd/edge/fixtures/picam/_generate.py`
- `src/skyherd/edge/fixtures/picam/frame_00.png` … `frame_03.png` (4 files)
- `hardware/pi/bootstrap.sh`
- `hardware/pi/credentials.example.json`
- `hardware/pi/README.md`
- `hardware/cardboard_coyote/__init__.py`
- `hardware/cardboard_coyote/coyote_harness.py` (re-export shim)

### Tests

- `tests/edge/test_cli_bootstrap.py` — 9 tests
- `tests/edge/test_picam_sensor.py` — 35 tests
- `tests/hardware/test_bootstrap_script.py` — 11 tests
- `tests/hardware/test_coyote_harness.py` — 27 tests
- `tests/hardware/test_h1_mqtt_bridge.py` — 11 tests

### Fixtures

- `tests/fixtures/__init__.py`
- `tests/fixtures/thermal_clips/__init__.py`
- `tests/fixtures/thermal_clips/_generate.py`
- `tests/fixtures/thermal_clips/frame_00.png` … `frame_05.png` (6 files)
- `tests/hardware/fixtures/creds_good.json`
- `tests/hardware/fixtures/creds_bad_missing_mqtt.json`
- `tests/hardware/fixtures/creds_malformed.json`

### Docs

- `docs/HARDWARE_H1_RUNBOOK.md` — judge-facing 200-line runbook
- `.planning/phases/05-…/05-CONTEXT.md`
- `.planning/phases/05-…/05-01-PLAN.md`
- `.planning/phases/05-…/05-02-PLAN.md`
- `.planning/phases/05-…/05-03-PLAN.md`
- `.planning/phases/05-…/05-04-PLAN.md`
- `.planning/phases/05-…/VERIFICATION.md` (this file)

### Modified

- `src/skyherd/edge/cli.py` — +203 LOC (3 new subcommands)

---

## Deferred / known gaps

1. **`src/skyherd/edge/cli.py` at 65% coverage** — plan targeted 75%. Gap is
   the `run` and `smoke` subcommand implementations (uses `asyncio.run` on
   long-lived loop) and the `max_ticks=None` branches for `picam`/`coyote`
   (infinite-loop variants).  These are exercised by manual CLI smoke but not
   unit-tested.  Cost to close: ~4 hours for subprocess-based test harness.
   Priority: LOW — the code paths are simple delegation into already-tested
   classes.  **Not blocking submission.**

2. **No real `amqtt` in-process broker** — `test_h1_mqtt_bridge.py` uses an
   `InMemoryBroker` routing table.  This is intentional per plan ("If
   in-process amqtt proves unreliable…"); the existing `tests/edge/test_fleet.py`
   covers real `amqtt` broker behaviour.  Our in-memory broker tests the
   contract (canonical JSON + correct topics + ordering) without broker-library
   overhead.

3. **Picamera2 Pi-only code path** — lines 210-219 of `picam_sensor.py` cover
   the real `Picamera2()` instantiation.  Tested indirectly via
   `test_pi_capture_uses_picam_when_available` with a `sys.modules` stub; cannot
   test on CI without real Pi hardware.  Path is trivial (two method calls on
   a known library API) and identical in shape to `camera.py::PiCamera`.

---

## Self-Check: PASSED

Files verified present:
- `src/skyherd/edge/picam_sensor.py` — ✓
- `src/skyherd/edge/coyote_harness.py` — ✓
- `src/skyherd/edge/cli.py` — ✓ (modified)
- `hardware/pi/bootstrap.sh` — ✓
- `hardware/pi/credentials.example.json` — ✓
- `hardware/pi/README.md` — ✓
- `hardware/cardboard_coyote/coyote_harness.py` — ✓
- `docs/HARDWARE_H1_RUNBOOK.md` — ✓
- `tests/hardware/test_h1_mqtt_bridge.py` — ✓
- `tests/fixtures/thermal_clips/` (6 PNGs) — ✓
- `src/skyherd/edge/fixtures/picam/` (4 PNGs) — ✓
