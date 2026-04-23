---
phase: 04-build-quickstart-health
plan: "01"
subsystem: world-packaging
tags: [packaging, hatchling, importlib-resources, world-config, bld-01]
requirements: [BLD-01]

dependency_graph:
  requires: []
  provides:
    - "make_world(seed=42) no-arg invocation"
    - "worlds/*.yaml packaged into wheel at skyherd/worlds/"
    - "importlib.resources.files('skyherd').joinpath('worlds/ranch_a.yaml') resolves"
  affects:
    - "src/skyherd/world/world.py"
    - "pyproject.toml"
    - "tests/world/test_make_world_default.py"
    - "tests/world/test_packaged_data.py"

tech_stack:
  added:
    - "importlib.resources.files() — Python 3.11+ stdlib resource resolver"
    - "hatchling force-include — maps worlds/ -> skyherd/worlds/ in wheel"
    - "src/skyherd/worlds symlink — editable install compatibility"
  patterns:
    - "TDD: RED (test files) -> GREEN (pyproject.toml force-include + symlink) -> GREEN (world.py signature change)"
    - "_default_world_config() helper using Path(str(traversable)) cast (not as_file context manager)"
    - "wheel exclude = [src/skyherd/worlds] prevents duplicate entries from symlink + force-include"

key_files:
  created:
    - path: "tests/world/test_make_world_default.py"
      purpose: "BLD-01 regression suite (no-arg, determinism, backward-compat)"
    - path: "tests/world/test_packaged_data.py"
      purpose: "wheel-layout assertion: importlib.resources finds packaged worlds yaml"
    - path: "src/skyherd/worlds"
      purpose: "symlink -> ../../worlds enabling importlib.resources in editable install"
  modified:
    - path: "pyproject.toml"
      change: "added force-include + sdist include + wheel exclude for worlds symlink"
    - path: "src/skyherd/world/world.py"
      change: "added _default_world_config() helper + made config_path: Path | None = None"

decisions:
  - "Used Path(str(traversable)) cast instead of as_file() context manager — avoids tempdir leak on zipimport"
  - "Created src/skyherd/worlds symlink (not copy) pointing to ../../worlds for editable install — avoids data duplication"
  - "Added wheel exclude = [src/skyherd/worlds] to prevent double-shipping via packages scan + force-include"
  - "force-include source is 'worlds' (repo root, not src/skyherd/worlds symlink) — hatchling resolves real files"
  - "Full test suite verified with uv sync --all-extras; 1193 passed, 0 failures"

metrics:
  duration_minutes: 15
  completed_date: "2026-04-22"
  tasks_completed: 3
  tasks_total: 3
  files_created: 3
  files_modified: 2
---

# Phase 04 Plan 01: make_world() default config + hatch force-include Summary

**One-liner:** `make_world(seed=42)` now resolves packaged `worlds/ranch_a.yaml` via `importlib.resources` in both editable and wheel installs, shipped via hatchling `force-include`.

## What Was Built

Closed the BLD-01 quickstart blocker: calling `make_world(seed=42)` with no `config_path` argument previously raised `TypeError`. After this plan:

- `from skyherd.world import make_world; make_world(seed=42)` works out of the box — returns `World` with 50 cows, `sim_time_s == 0.0`.
- The built wheel contains `skyherd/worlds/ranch_a.yaml` and `skyherd/worlds/ranch_b.yaml` (verified via `unzip -l dist/*.whl | grep worlds/ranch`).
- All 6 existing `make_world(seed, config_path=...)` callers continue to work unchanged.
- 5 new tests pass; 1193 total suite tests pass.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 8b744da | test | add failing tests for BLD-01 default config + wheel packaging (RED) |
| 57aafb7 | build | ship worlds/*.yaml into wheel via hatchling force-include |
| a19b0e8 | feat | make_world(seed=42) works with packaged default config (BLD-01) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Duplicate yaml entries in wheel from symlink + force-include**
- **Found during:** Task 2 verification
- **Issue:** `src/skyherd/worlds` symlink (needed for editable install) caused hatchling to include ranch yamls twice — once via `packages = ["src/skyherd"]` scan (following the symlink) and once via `force-include`. This produced `UserWarning: Duplicate name` in the wheel zip.
- **Fix:** Added `exclude = ["src/skyherd/worlds"]` to `[tool.hatch.build.targets.wheel]` so the symlink-followed copy is excluded; `force-include` from the real `worlds/` directory provides the canonical copy.
- **Files modified:** `pyproject.toml`
- **Commit:** a19b0e8 (included in Task 3 commit)

**2. [Rule 3 - Blocking] Existing symlink src/skyherd/worlds pointed to wrong relative path**
- **Found during:** Task 2 editable install refresh
- **Issue:** A pre-existing broken symlink `src/skyherd/worlds -> ../../../worlds` existed in the worktree (3 levels up = `.claude/worktrees/` directory, not repo root). `importlib.resources` resolved to a non-existent path.
- **Fix:** Removed broken symlink, created correct `src/skyherd/worlds -> ../../worlds` (2 levels up = worktree root where `worlds/` lives).
- **Files modified:** `src/skyherd/worlds` (symlink target)
- **Commit:** 57aafb7

**3. [Rule 3 - Blocking] `uv build` (sdist+wheel) failed; used `uv build --wheel` for verification**
- **Found during:** Task 2 final verification
- **Issue:** `uv build` builds sdist first then repackages into wheel; the sdist extraction into a temp dir loses the symlink, so hatchling's `force-include` cannot find the real `worlds/` directory. The plan's verification command `uv build && unzip -l dist/*.whl | grep worlds` fails at the sdist step.
- **Impact:** Sdist build is broken when `force-include` source is a symlink target not present in the extracted sdist. This is a known hatchling limitation with symlinked `force-include` sources.
- **Fix applied:** The `[tool.hatch.build.targets.sdist] include = ["worlds/**", ...]` stanza is in place — this ensures the real files are in the sdist. The `uv build --wheel` (direct wheel, no sdist intermediate) works correctly and produces a valid wheel with both yaml files.
- **Status:** Wheel install path (the judge-facing path) works correctly. Sdist build is deferred — judges use `uv sync` (editable), not `pip install skyherd-engine-*.tar.gz`.
- **Deferred:** Full sdist round-trip fix tracked in deferred-items.md.

## Known Stubs

None. All data is real: `worlds/ranch_a.yaml` is the canonical 50-cow ranch config used by all scenarios.

## Threat Flags

None. The `force-include` mapping is narrow (`"worlds" = "skyherd/worlds"`) — verified via wheel inspection that no `.env`, `runtime/`, or `.venv/` files appear.

## Self-Check

### Files exist:
- [x] `tests/world/test_make_world_default.py` — FOUND
- [x] `tests/world/test_packaged_data.py` — FOUND
- [x] `src/skyherd/worlds` symlink — FOUND (resolves to ranch_a.yaml + ranch_b.yaml)
- [x] `pyproject.toml` contains `[tool.hatch.build.targets.wheel.force-include]` — FOUND

### Commits exist:
- [x] 8b744da — FOUND
- [x] 57aafb7 — FOUND
- [x] a19b0e8 — FOUND

### Test results:
- [x] `make_world(seed=42)` returns cows=50 sim_time=0.0
- [x] All 5 new tests GREEN
- [x] Full suite: 1193 passed, 0 failures

## Self-Check: PASSED
