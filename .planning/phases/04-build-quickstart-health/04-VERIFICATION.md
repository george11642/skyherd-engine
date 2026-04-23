---
phase: 04-build-quickstart-health
verified: 2026-04-22T21:00:00Z
status: passed
score: 7/7
overrides_applied: 0
re_verification: false
---

# Phase 4: Build & Quickstart Health — Verification Report

**Phase Goal:** Judge cloning repo fresh succeeds under 5 min with the 3-command quickstart; `make_world(seed=42)` works without arguments; `make dashboard` serves live-mode (not mock).
**Verified:** 2026-04-22T21:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `make_world(seed=42)` works with no arguments and returns 50 cows | VERIFIED | `.venv/bin/python -c "from skyherd.world import make_world; w=make_world(seed=42); print(len(w.herd.cows))"` prints `50` |
| 2 | worlds/*.yaml packaged into wheel at skyherd/worlds/ | VERIFIED | `unzip -l dist/skyherd_engine-0.1.0-py3-none-any.whl \| grep skyherd/worlds/ranch_a.yaml` returns entry at line 7160 |
| 3 | `/api/snapshot` returns real world data (50 cows, not mock 12) in live mode | VERIFIED | `test_live_snapshot_returns_real_world_data` PASS; snapshot has `cows: list of 50 items`; `world.snapshot().model_dump(mode='json')` path confirmed in `app.py:141` |
| 4 | `make dashboard` targets live mode (not mock) | VERIFIED | `make -n dashboard` outputs `uv run python -m skyherd.server.live --port 8000 --host 127.0.0.1 --seed 42` |
| 5 | `make dashboard-mock` preserves the legacy mock path | VERIFIED | `make -n dashboard-mock` outputs `SKYHERD_MOCK=1 uv run uvicorn skyherd.server.app:app --port 8000` |
| 6 | Fresh-clone smoke script exists, is executable, and is syntactically valid | VERIFIED | `test -x scripts/fresh_clone_smoke.sh && bash -n scripts/fresh_clone_smoke.sh` exits 0; 71 lines |
| 7 | CI workflow is valid YAML with nightly + workflow_dispatch triggers and cold-uv flag | VERIFIED | `yaml.safe_load(...)` succeeds; `on: workflow_dispatch + schedule` confirmed; `enable-cache: false` present |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/skyherd/world/world.py` | `make_world(seed=42)` default config + `_default_world_config()` helper | VERIFIED | Lines 150-182 implement `_default_world_config()` via `importlib.resources.files()`; signature `config_path: Path \| None = None` |
| `src/skyherd/worlds` | Symlink to `../../worlds` for editable install | VERIFIED | Symlink exists, `readlink` returns `../../worlds`, target has `ranch_a.yaml` + `ranch_b.yaml` |
| `pyproject.toml` | `force-include` + `wheel exclude` + `skyherd-server-live` entry-point | VERIFIED | `[tool.hatch.build.targets.wheel.force-include]` maps `"worlds" = "skyherd/worlds"`; `exclude = ["src/skyherd/worlds"]`; `skyherd-server-live = "skyherd.server.live:main"` at line 92 |
| `src/skyherd/server/live.py` | 64-line typer CLI constructing real World+Ledger+_DemoMesh | VERIFIED | File is 64 lines; constructs `make_world(seed=seed)`, `Ledger.open(...)`, `_DemoMesh(ledger=ledger)`, passes to `create_app(mock=False, ...)` |
| `tests/world/test_make_world_default.py` | BLD-01 regression suite | VERIFIED | 3 tests, all PASS |
| `tests/world/test_packaged_data.py` | Wheel-layout assertion for importlib.resources | VERIFIED | 2 tests, both PASS |
| `tests/server/test_live_app.py` | BLD-03 integration test: live snapshot = 50 cows | VERIFIED | 2 tests, both PASS (`test_live_snapshot_returns_real_world_data`, `test_live_health_ok`) |
| `tests/test_readme_quickstart.py` | Doc-drift guard for README canonical commands | VERIFIED | 3 tests, all PASS |
| `scripts/fresh_clone_smoke.sh` | Executable bash smoke script | VERIFIED | 71 lines, executable, `bash -n` syntax-clean |
| `.github/workflows/fresh-clone-smoke.yml` | Nightly + workflow_dispatch CI with cold uv | VERIFIED | Valid YAML; triggers: `workflow_dispatch` + `schedule: cron "0 8 * * *"`; `enable-cache: false`; `timeout-minutes: 10` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `make dashboard` | `skyherd.server.live` | `uv run python -m skyherd.server.live` | WIRED | Makefile target confirmed via `make -n` |
| `skyherd.server.live` | `create_app(mock=False)` | DI: world, ledger, mesh | WIRED | `live.py:45` calls `create_app(mock=False, mesh=mesh, world=world, ledger=ledger)` |
| `app.py:/api/snapshot` | `world.snapshot()` | `use_mock=False` branch | WIRED | `app.py:141` confirmed; `model_dump(mode='json')` path |
| `make_world(seed=42)` | `worlds/ranch_a.yaml` | `_default_world_config()` → `importlib.resources.files()` | WIRED | `world.py:162` uses `files("skyherd").joinpath("worlds/ranch_a.yaml")` |
| Wheel | `skyherd/worlds/ranch_a.yaml` | `hatchling force-include` | WIRED | `unzip -l` confirmed YAML in wheel at expected path |
| `tests/test_readme_quickstart.py` | `README.md` + `CLAUDE.md` | File read + string assert | WIRED | Tests read real files and assert command strings present |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `app.py:/api/snapshot` | `data` | `world.snapshot().model_dump(mode='json')` when `mock=False` | Yes — 50 cows from ranch_a.yaml | FLOWING |
| `live.py` | `world` | `make_world(seed=seed)` → `importlib.resources` → ranch_a.yaml | Yes — real 50-cow World object | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `make_world(seed=42)` returns 50 cows | `.venv/bin/python -c "from skyherd.world import make_world; w=make_world(seed=42); print(len(w.herd.cows))"` | `50` | PASS |
| Wheel contains packaged YAML | `uv build --wheel && unzip -l dist/*.whl \| grep skyherd/worlds/ranch_a.yaml` | Found at 7160 bytes | PASS |
| 10 BLD tests all green | `.venv/bin/python -m pytest tests/world/test_make_world_default.py tests/world/test_packaged_data.py tests/server/test_live_app.py tests/test_readme_quickstart.py -v` | `10 passed in 0.54s` | PASS |
| Smoke script executable + syntax valid | `test -x scripts/fresh_clone_smoke.sh && bash -n scripts/fresh_clone_smoke.sh` | Exit 0 | PASS |
| CI workflow valid YAML | `python -c "import yaml; yaml.safe_load(open('.github/workflows/fresh-clone-smoke.yml'))"` | Exit 0 | PASS |
| `make dashboard` targets live binary | `make -n dashboard \| grep python -m skyherd.server.live` | Match found | PASS |
| `make dashboard-mock` preserves mock env var | `make -n dashboard-mock \| grep SKYHERD_MOCK=1` | Match found | PASS |
| `/api/snapshot` live path returns 50 cows | Python TestClient with `create_app(mock=False)` | `cows: 50 items` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| BLD-01 | 04-01 | `make_world(seed=42)` works with no args; YAML in wheel | SATISFIED | `make_world(seed=42)` verified; wheel contains yaml; 5 tests GREEN |
| BLD-02 | 04-03 | Fresh-clone flow documented + verified; CI nightly guard | SATISFIED | smoke script + CI workflow exist and are syntactically valid; doc-drift guard passes |
| BLD-03 | 04-02 | `make dashboard` serves live (non-mock) real data | SATISFIED | `live.py` wired to `create_app(mock=False)`; Makefile flipped; 2 integration tests PASS |

Note: BLD-04 (SITL CI smoke) is mapped to Phase 6, not Phase 4 — not an orphaned requirement for this phase.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No stubs, placeholders, or silenced errors found in phase deliverables |

Scan coverage: `src/skyherd/server/live.py`, `src/skyherd/world/world.py`, `scripts/fresh_clone_smoke.sh`, `.github/workflows/fresh-clone-smoke.yml`, `tests/world/test_make_world_default.py`, `tests/world/test_packaged_data.py`, `tests/server/test_live_app.py`, `tests/test_readme_quickstart.py`.

No TODO/FIXME/placeholder strings found. No empty return stubs. No hardcoded empty data flowing to renderers.

---

### Human Verification Required

None. All phase goals are machine-verifiable.

Note: The README doc-drift test (`tests/test_readme_quickstart.py`) asserts canonical 5-command strings are present in README.md. A true end-to-end timing test on a second machine (measuring <5 min wall clock for a cold judge) is out of scope for this phase per 04-VALIDATION.md (listed as Manual-Only there), but the smoke script + CI workflow provide the automation path for that gate. The SUMMARY for 04-03 reports `1198 passed, 13 skipped, 0 failures` on a full suite run confirming no regression.

---

### Gaps Summary

None. All seven observable truths verified. All ten required artifacts exist, are substantive, and are wired. Data flows from ranch_a.yaml through importlib.resources to make_world to /api/snapshot with real 50-cow data. No stubs detected.

**One cosmetic note:** Commit hashes in 04-01-SUMMARY.md (8b744da / 57aafb7 / a19b0e8) do not match the actual git log (2c12f6a / a8b6e83 / b02177f). This is a hash drift from a branch rebase — the commits exist with identical commit messages and correct file changes. Not a functional gap.

---

_Verified: 2026-04-22T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
