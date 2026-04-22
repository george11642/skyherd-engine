# Phase 4: Build & Quickstart Health - Research

**Researched:** 2026-04-22
**Domain:** Python packaging / hatchling data-files / `importlib.resources` / FastAPI live-wire / CI fresh-clone smoke
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — discuss skipped via `workflow.skip_discuss=true`. All implementation choices are at Claude's discretion within the phase boundary.

### Claude's Discretion
- Method of resolving the default world config (package-data + `importlib.resources` vs. package-relative `Path` fallback)
- Exact `pyproject.toml` data-packaging syntax (`force-include` vs. `sources`)
- Makefile flag naming for mock vs. live dashboard (`make dashboard-mock`, `SKYHERD_MOCK=1 make dashboard`, or a `MOCK=1` param)
- Fresh-clone smoke script location and name (`scripts/fresh_clone_smoke.sh` recommended)
- CI job structure (separate job vs. step inside existing `ci` job)
- Timeout budget for fresh-clone job (≤5 min is the judge SLA)

### Known Constraints from Audit
- `make_world()` at `src/skyherd/world/world.py` currently requires explicit `config_path` → `make_world(seed=42)` raises `TypeError`. Must fix so the canonical quickstart invocation works with no args.
- `make demo SEED=42 SCENARIO=all` currently passes in ~3s.
- `make dashboard` currently ALWAYS uses `SKYHERD_MOCK=1` — live path (real `mesh + world + ledger` injection in `src/skyherd/server/app.py:83,134-140,142-148,150-156`) is 73% covered and not wired in the Makefile target.
- Judge quickstart is 3 commands: clone+cd, `uv sync && (cd web && pnpm install && pnpm run build)`, `make demo SEED=42 SCENARIO=all` → `make dashboard`.
- Fresh-clone verification: documented AND asserted in CI (or a dedicated script that runs on a clean worktree).
- Phase 4 must NOT break Phase 5 — Phase 4 lands live-mode *plumbing*; Phase 5 polishes UX of that plumbing (DASH-01..06).

### Deferred Ideas (OUT OF SCOPE)
- Docker-based quickstart (`docker compose up`) — nice-to-have, not in scope
- Windows-compatible fresh-clone — out of scope (hackathon judges run Linux/macOS)
- Version lock / reproducible build beyond `uv sync` — scope creep
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BLD-01 | `make_world()` accepts default `config_path` resolving to `worlds/ranch_a.yaml` via `importlib.resources` or package-relative `Path`. Judge quickstart `make_world(seed=42)` works without arguments. | §Standard Stack (importlib.resources + hatchling force-include), §Code Examples (1) |
| BLD-02 | Fresh-clone flow documented in README verified on a second machine (or clean worktree): `git clone ... && cd skyherd-engine && uv sync && make demo SEED=42 SCENARIO=all` completes in under 5 minutes and all scenarios PASS. | §Code Examples (2) fresh-clone bash script, §Architecture Patterns (fresh-clone CI job) |
| BLD-03 | `make dashboard` in live (non-mock) mode serves a functional dashboard from a fresh clone. | §Code Examples (3) Makefile live target, §Architecture Patterns (live-mode wiring via `create_app(mesh=…, world=…, ledger=…)`) |
</phase_requirements>

## Summary

Phase 4 closes three related "quickstart trust" gaps in the brownfield codebase so that a fresh-clone judge experience matches what the README promises. All three gaps (BLD-01, BLD-02, BLD-03) are small-diameter fixes with one shared constraint: the `worlds/ranch_a.yaml` canonical config must be locatable both in editable installs (where `Path(__file__)` walking works today) and in installed wheels (where it doesn't, because `worlds/` sits outside `src/skyherd/` and isn't currently packaged).

The stack is already locked: Python 3.11+, hatchling build backend, `uv` package manager, FastAPI app factory, pytest + coverage. Nothing new to introduce. The fix surface is:
1. Move `worlds/` data into the wheel via hatchling's `force-include`, and resolve it at runtime via `importlib.resources.files("skyherd").joinpath(...)` (the modern Python 3.11+ pattern — stable, works across editable + wheel installs).
2. Add a `scripts/fresh_clone_smoke.sh` that clones the repo into `$(mktemp -d)` via `file://` and runs the exact README quickstart — then wire it into GitHub Actions as a new Ubuntu job (≤5-min SLA matching judge SLA).
3. Flip `make dashboard` default to live mode (inject real `mesh`/`world`/`ledger` into the existing `create_app()` factory via a small CLI bootstrap) and keep `make dashboard-mock` for the old `SKYHERD_MOCK=1` synthetic path.

**Primary recommendation:** Ship BLD-01 as the foundation (everything else depends on `make_world(seed=42)` working from any install layout), then BLD-03 (live wiring is 90% written — just needs a caller that constructs the deps), then BLD-02 (the smoke script both validates and serves as the end-to-end integration test). Total change footprint: ~5 files, ~150 lines.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| World config resolution (`worlds/ranch_a.yaml`) | Python package (src/skyherd/world/) | Build-time (hatchling wheel assembly) | Runtime consumer is the `make_world()` factory. Build-time step ensures data is physically present in the wheel. |
| `make_world(seed=42)` no-arg default | Python package (src/skyherd/world/world.py) | — | The factory is the only place with authoritative knowledge of "which ranch is canonical" — default belongs there, not in every caller. |
| `make dashboard` live-mode bootstrap | CLI / entrypoint (new small module or extended `server/cli.py`) | FastAPI factory (`server/app.py::create_app`) | The factory already accepts `mesh`/`world`/`ledger` injection (app.py:74-79). Caller-tier responsibility is assembling those objects before calling `create_app(mock=False, mesh=…, world=…, ledger=…)`. |
| Fresh-clone smoke assertion | CI / GitHub Actions (new job) | Shell script (`scripts/fresh_clone_smoke.sh`) | Judge-facing SLA is "under 5 min on a clean checkout" — must be asserted on CI runners that match the judge's environment (Ubuntu + no cached deps). |
| README quickstart truth-check | Docs + CI (grep-based doc-drift test) | — | README and CLAUDE.md both reference the 3-command flow (README:17-22, CLAUDE.md:35-40). Pinning the command strings in a test prevents silent doc-drift. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hatchling | 1.27+ (installed via `build-system.requires = ["hatchling"]`) | Build backend | Already in `pyproject.toml:1-3`. Supports `force-include` for non-Python data files. [CITED: hatch.pypa.io/latest/config/build/] |
| importlib.resources (stdlib) | Python 3.11+ | Runtime resource discovery | Standard library; `files()` + `joinpath()` pattern replaces deprecated `pkg_resources`. Transparent across editable/wheel/zip installs. [CITED: docs.python.org/3/library/importlib.resources.html] |
| uv | latest (pinned via `astral-sh/setup-uv@v5` in CI) | Package manager | Already in use. `uv sync` installs from `uv.lock` deterministically. [VERIFIED: .github/workflows/ci.yml:31-33] |
| pytest | 8+ | Test framework | Already configured (`pyproject.toml:53-55`). asyncio_mode = "auto" is set. [VERIFIED: pyproject.toml:97] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI `create_app()` factory | existing | Dependency injection for live mode | Already accepts `mesh`, `world`, `ledger` params — unused today. [VERIFIED: src/skyherd/server/app.py:74-83] |
| typer | 0.12+ | CLI for server bootstrap | Already in use (`src/skyherd/server/cli.py`). Extend `start` command with `--no-mock` flag. [VERIFIED: src/skyherd/server/cli.py:15-22] |
| bash + mktemp | coreutils | Fresh-clone sandbox | POSIX-standard. `mktemp -d` yields a fresh dir; trap on EXIT for cleanup. |
| actions/checkout@v4 + astral-sh/setup-uv@v5 | pinned | CI primitives | Already used in `.github/workflows/ci.yml`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `importlib.resources.files()` | `Path(__file__).parent.parent.parent.parent / "worlds" / "ranch_a.yaml"` (current pattern in `world/cli.py:23`) | Works in editable installs; BREAKS in wheel installs because `worlds/` isn't next to the installed package. Rejected. |
| hatchling `force-include` | hatchling `sources` (path rewriting) | `sources` rewrites path prefixes but requires the source to be under a discoverable root. `force-include` is more explicit for "grab dir X, place it at wheel path Y". Chose `force-include`. [CITED: hatch.pypa.io] |
| hatchling `force-include` | Move `worlds/` inside `src/skyherd/worlds/` | Would be cleaner but changes the repo layout contract (other code, docs, and CLAUDE.md all reference `worlds/` at root). Higher diff risk. Rejected for scope. |
| `scripts/fresh_clone_smoke.sh` | Reuse existing `sitl-e2e` workflow-dispatch job | Different concern (drone hardware, not quickstart). Reuse would muddy the smoke target. Rejected. |
| New Makefile target `dashboard-live` | Flip `dashboard` default; add `dashboard-mock` for the old path | CLAUDE.md + README both name the target `make dashboard` — judges will type that. Default must be live. Chose the flip. |

**Installation:**
No new dependencies. All required packages (hatchling, typer, pytest) are already in `pyproject.toml`.

**Version verification:**
```bash
uv run python -c "import importlib.resources; print(importlib.resources.__file__)"
uv tree | head -20  # confirm hatchling resolves from uv.lock
```
[VERIFIED: hatchling present in build-system.requires; `importlib.resources.files()` API available since Python 3.9, stable since 3.11 — docs.python.org]

## Architecture Patterns

### System Architecture Diagram

```
  Fresh judge checkout
         │
         ▼
  ┌──────────────────────────────────────────────────────┐
  │  Quickstart (README:17-22 + CLAUDE.md:35-40)         │
  │  1. git clone && cd                                  │
  │  2. uv sync && (cd web && pnpm install &&            │
  │                 pnpm run build)                      │
  │  3. make demo SEED=42 SCENARIO=all → make dashboard  │
  └──────────────────────────────────────────────────────┘
         │
         ├──► uv sync reads pyproject.toml
         │      └─► hatchling wheel build:
         │          • src/skyherd/** → skyherd/…
         │          • worlds/*.yaml → skyherd/worlds/*.yaml   ← BLD-01 new
         │
         ├──► make demo
         │      └─► skyherd-demo play all --seed 42
         │           └─► scenarios/base.py::run()
         │                └─► make_world(seed, config_path=None)
         │                     └─► default: importlib.resources.files("skyherd")
         │                                    .joinpath("worlds/ranch_a.yaml")  ← BLD-01
         │
         └──► make dashboard
                └─► [NEW: live bootstrap]
                     ├─► construct Ledger (in-memory SQLite)
                     ├─► construct World via make_world(seed=42)
                     ├─► construct _DemoMesh(ledger)           (reuse scenarios/base._DemoMesh)
                     └─► uvicorn launches:
                          skyherd.server.app:create_app(
                              mock=False,
                              mesh=_mesh, world=_world, ledger=_ledger)
                          └─► EventBroadcaster live loops
                               ├─► world.snapshot()  (real)     ← DASH-01 plumbing
                               ├─► mesh cost tick    (real)
                               └─► ledger.iter_events() (real)

  ┌──────────────────────────────────────────────────────┐
  │  CI: Fresh-clone smoke job (Ubuntu, ≤5 min)          │
  │  ─ checkout                                          │
  │  ─ setup-uv@v5 (no cache)                            │
  │  ─ bash scripts/fresh_clone_smoke.sh                 │
  │      └─ mktemp -d → clone file://$GITHUB_WORKSPACE   │
  │        → uv sync → pnpm build → make demo            │
  │        → timeout 30 make dashboard + curl /health    │
  └──────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
skyherd-engine/
├── src/skyherd/
│   └── world/world.py         # [EDIT] make_world(seed, config_path=None) + resource resolver
├── worlds/
│   ├── ranch_a.yaml           # [UNCHANGED] but now also shipped via force-include
│   └── ranch_b.yaml           # [UNCHANGED]
├── scripts/
│   └── fresh_clone_smoke.sh   # [NEW] 40-line bash
├── .github/workflows/
│   └── ci.yml                 # [EDIT] add fresh-clone-smoke job
├── Makefile                   # [EDIT] flip dashboard to live; add dashboard-mock
├── pyproject.toml             # [EDIT] add force-include for worlds/
├── src/skyherd/server/cli.py  # [EDIT] --no-mock flag → live bootstrap
└── tests/
    └── world/test_make_world_default.py  # [NEW] BLD-01 regression test
    └── server/test_live_app.py          # [NEW] BLD-03 integration test
    └── test_readme_quickstart.py        # [NEW] BLD-02 doc-drift guard
```

### Pattern 1: `importlib.resources.files()` for Packaged Data

**What:** Resolve a data file that was packaged into the wheel via a stable API.
**When to use:** Any time a library needs to read its own shipped data (YAML configs, prompt templates, fixtures).
**Example:**
```python
# Source: https://docs.python.org/3/library/importlib.resources.html
from importlib.resources import files, as_file

# For reading text/bytes directly (preferred):
yaml_text = files("skyherd").joinpath("worlds/ranch_a.yaml").read_text(encoding="utf-8")

# For APIs that need an actual Path (yaml.safe_load, pydantic validators):
with as_file(files("skyherd").joinpath("worlds/ranch_a.yaml")) as path:
    config = TerrainConfig.from_yaml(path)
```
Key property: handles editable install, wheel install, and zip-import transparently. [CITED: docs.python.org/3/library/importlib.resources.html]

### Pattern 2: Hatchling `force-include` for Out-of-Tree Data

**What:** Map a non-src directory (like `worlds/` at repo root) into a specific path inside the built wheel.
**When to use:** When the project layout has data files outside the package root and moving them is undesirable.
**Example:**
```toml
# Source: https://hatch.pypa.io/latest/config/build/
[tool.hatch.build.targets.wheel.force-include]
"worlds" = "skyherd/worlds"
```
Key property: Files under `worlds/` become accessible via `importlib.resources.files("skyherd").joinpath("worlds/…")`. Works for sdist and wheel. [CITED: hatch.pypa.io/latest/config/build/]

### Pattern 3: FastAPI App Factory with Dependency Injection

**What:** Pre-constructed dependencies passed into an app factory — not globals, not `Depends()` for singletons.
**When to use:** When the app needs runtime-assembled singletons (DB connection, mesh, broker) and you want the same factory to serve tests + production.
**Example:**
```python
# Already implemented in src/skyherd/server/app.py:74-83
def create_app(
    mock: bool | None = None,
    mesh: Any = None,
    ledger: Any = None,
    world: Any = None,
) -> FastAPI:
    use_mock = mock if mock is not None else _MOCK_MODE
    broadcaster = EventBroadcaster(mock=use_mock, mesh=mesh, ledger=ledger, world=world)
    # ... mounts routes ...
```
Key property: Phase 4 only needs to *call* this correctly from the live bootstrap — no refactor required. [VERIFIED: src/skyherd/server/app.py:74-83]

### Pattern 4: Fresh-Clone Bash Smoke

**What:** Clone the current checkout via `file://` into a mktemp dir, run the documented quickstart, assert success.
**When to use:** When the README promises a flow — ensures the promise doesn't silently break.
**Example:**
```bash
# Source: standard CI pattern (shellcheck-clean)
set -euo pipefail
SANDBOX=$(mktemp -d)
trap 'rm -rf "$SANDBOX"' EXIT
git clone --depth 1 "file://${GITHUB_WORKSPACE:-$(pwd)}" "$SANDBOX/repo"
cd "$SANDBOX/repo"
uv sync
(cd web && pnpm install --frozen-lockfile && pnpm run build)
timeout 180 make demo SEED=42 SCENARIO=all
```
Key property: Proves fresh-clone health with zero tooling beyond bash + git + uv + pnpm.

### Anti-Patterns to Avoid

- **`__file__` walking for packaged data:** `Path(__file__).parent.parent.parent.parent / "worlds"` only works in editable installs. It will silently break the day someone installs SkyHerd from a wheel (e.g., in a Docker image, on a Pi, or as a dependency of another project). Replace with `importlib.resources.files()`.
- **Module-level `app = create_app()` for live mode:** The current `app.py:288` creates a module-level app with defaults — that's fine for `uvicorn skyherd.server.app:app` mock runs, but live mode needs pre-constructed deps. Do NOT add globals; use a CLI bootstrap that calls `create_app(mock=False, mesh=…, …)` and passes the returned `app` to `uvicorn.run()`.
- **CI job that downloads cached `.venv`:** Masks the fresh-clone SLA. The fresh-clone smoke job must NOT use cache.
- **Hard-coding paths in tests:** `tests/world/test_determinism.py:9` uses `Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"` — that's OK for test-only discovery, but BLD-01 tests should verify the `importlib.resources` path works without arguments, not re-test the `__file__` path.
- **Adding UX polish to the live dashboard in Phase 4:** DASH-02..06 belong to Phase 5. Phase 4 ships *plumbing* only — if `/api/snapshot` returns real sim data and `all_idle`/cost paths work, the phase is done.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Finding the world config at runtime | Custom path-walking with `__file__` / env var lookup / sys.path introspection | `importlib.resources.files("skyherd").joinpath(...)` | Stdlib; handles editable + wheel + zip; no edge cases to maintain. |
| Packaging `worlds/` into the wheel | Custom pre-build script / `setup.py` `package_data` workaround | `[tool.hatch.build.targets.wheel.force-include]` | Hatchling native; one line of TOML; no shim scripts. |
| Fresh-clone verification | Copying the repo manually, writing a Python harness | `scripts/fresh_clone_smoke.sh` with `mktemp -d` + `file://` clone | bash + git + uv are already available on CI and every dev machine. |
| Assembling live-mode deps for the dashboard | Parallel reimplementation of `_DemoMesh` | Reuse `scenarios.base._DemoMesh` (already used in tests) | It already wires Ledger + routing + `make_world()`. |
| Proving README hasn't drifted | Ad-hoc visual inspection | Python test that greps the README for the 3 expected command lines | Catches accidental README edits before they hit a judge. |

**Key insight:** Every one of these problems has a battle-tested stdlib, build-backend, or existing-code solution. The Phase 4 diff should be ~150 lines total; anything larger is scope creep.

## Runtime State Inventory

*Not applicable — Phase 4 is a pure code/config/CI change with no rename, refactor, or migration. No stored data, live service config, OS-registered state, secrets, or build artifacts carry string identifiers that would need migration. Existing callers of `make_world(seed, config_path=…)` continue to work because `config_path` stays optional-with-default.*

**Nothing found in category:** All 5 runtime-state categories — verified by grep for `make_world` (only 6 callers, all in this repo) and by inspecting `.env.example` / SOPS / CI for env-var references (no env var names depend on this phase's changes).

## Common Pitfalls

### Pitfall 1: `force-include` source missing at sdist build time
**What goes wrong:** If `worlds/` is `.gitignore`'d or missing from the checkout, hatchling errors with `sources that do not exist`.
**Why it happens:** `force-include` is strict — it errors on missing sources rather than silently skipping.
**How to avoid:** Confirm `worlds/ranch_a.yaml` and `worlds/ranch_b.yaml` are tracked in git (they are — verified via `find` output). Add a CI assertion (`test -f worlds/ranch_a.yaml`) in the smoke job.
**Warning signs:** `hatch build` or `uv build` failing with `FileNotFoundError: [Errno 2] No such file or directory: 'worlds'`.

### Pitfall 2: `importlib.resources.files(package)` on a namespace package
**What goes wrong:** If `skyherd/` is ever converted to an implicit namespace package (no `__init__.py`), `files()` returns a `MultiplexedPath` that rejects `joinpath()` in some edge cases.
**Why it happens:** Namespace packages don't have a single root.
**How to avoid:** `src/skyherd/__init__.py` must exist (it does — verified via directory listing; package is regular, not namespace). Do not delete it.
**Warning signs:** `NotADirectoryError` or `IsADirectoryError` from `read_text()` after a refactor.

### Pitfall 3: Dashboard live-mode calls `mesh._sessions` which is empty at boot
**What goes wrong:** `_live_agent_statuses(mesh)` in `app.py:268-281` iterates `mesh._sessions.items()` — if no scenario has run, the dict is empty and `/api/agents` returns `{"agents": [], ...}`.
**Why it happens:** Sessions are lazily created per-agent-dispatch in `_DemoMesh.dispatch()`.
**How to avoid:** Either (a) pre-populate session stubs with zero-state at bootstrap, or (b) accept that a freshly-started live dashboard shows empty agent lanes until the first scenario wakes them. Phase 4 should ship (b) because agent-lane polish belongs to Phase 5 / DASH-06. Document the expected behavior in the live bootstrap docstring.
**Warning signs:** Dashboard loads but "5 agent lanes empty" — confusing to a judge if not explained.

### Pitfall 4: Fresh-clone job exceeds 5-min budget because of pnpm/npm registry cold-path
**What goes wrong:** `pnpm install` on a cold runner can take 60-120s if registry is slow or `web/pnpm-lock.yaml` is large.
**Why it happens:** No cache, by design. 5-min total = uv sync (~30-60s) + pnpm install (~60-120s) + pnpm build (~20-30s) + make demo (~10s) = 120-220s typical, but outliers can hit 4+ min.
**How to avoid:** Run `pnpm install --frozen-lockfile` (already in Makefile:20) — faster than fresh resolve. Cap the CI job at 10 min total; budget 5 min for the critical path and log timings. Don't fail on marginal overruns during development; tighten to 5 min once stable.
**Warning signs:** GitHub Actions job timing out, judge failing the quickstart because their machine is slow.

### Pitfall 5: `make dashboard` blocks indefinitely in CI
**What goes wrong:** `make dashboard` starts `uvicorn` in the foreground and never exits. If the smoke script calls `make dashboard` without a timeout, CI hangs until the 6-hour default timeout.
**Why it happens:** Design intent — it's a dev server.
**How to avoid:** In the smoke script, spawn dashboard in background with `&`, poll `/health` endpoint with curl retry-loop (max 20s), then kill by PID on success. OR: add a separate `make dashboard-smoke` target that starts uvicorn, curls `/api/snapshot`, and exits cleanly.
**Warning signs:** CI job times out at the hard cap.

### Pitfall 6: Package-data path inside wheel differs from expectation
**What goes wrong:** After `force-include`, the data file is inside `skyherd/worlds/ranch_a.yaml` (the `"worlds" = "skyherd/worlds"` mapping) — NOT at `skyherd-engine/worlds/` or `worlds/`. Code that uses `files("skyherd").joinpath("worlds/ranch_a.yaml")` must match this layout exactly.
**Why it happens:** The TOML key is the *target path inside the wheel*, not the *Python import path*.
**How to avoid:** Verify by building a wheel locally (`uv build` or `python -m build`) and unzipping: `unzip -l dist/skyherd_engine-*.whl | grep worlds`. Should show `skyherd/worlds/ranch_a.yaml`.
**Warning signs:** `FileNotFoundError` from `importlib.resources` at runtime on a fresh wheel install.

## Code Examples

Verified patterns from official sources and the existing codebase:

### 1. `make_world()` with default config resolution (BLD-01)
```python
# Target: src/skyherd/world/world.py
# Source: Python 3.11+ importlib.resources docs (docs.python.org)
from __future__ import annotations

import random
from datetime import UTC, datetime
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

# ... existing imports unchanged ...

def _default_world_config() -> Path:
    """Return the packaged ranch_a.yaml as a filesystem Path.

    Uses importlib.resources.files(), so this works in both editable
    installs (finds repo-root worlds/ via src/ layout) and wheel installs
    (finds skyherd/worlds/ inside the installed package).
    """
    # Under hatchling force-include, worlds/ is shipped as skyherd/worlds/.
    # In editable mode, the same path exists because src/skyherd/worlds/
    # is symlinked by the editable install — or falls back to repo-root
    # worlds/ via Path walking.
    packaged = files("skyherd").joinpath("worlds/ranch_a.yaml")
    # Use as_file() so TerrainConfig.from_yaml() receives a real Path
    # (needed because TerrainConfig.from_yaml uses Path.open / yaml.safe_load).
    with as_file(packaged) as p:
        return p  # safe to return: editable install path is stable; wheel path materializes on use


def make_world(seed: int, config_path: Path | None = None) -> World:
    """Build a fully-seeded :class:`World` from a YAML ranch config.

    If *config_path* is None, resolves the packaged ``worlds/ranch_a.yaml``.
    Same *seed* + same *config_path* content = identical world evolution.
    """
    if config_path is None:
        config_path = _default_world_config()
    # ... rest of body UNCHANGED ...
```

**Note on `as_file()` return:** Because `as_file()` is a context manager, the naive `with as_file(...) as p: return p` leaks the tempdir on wheel-zip installs. Safer:

```python
# Alternative: copy into memory if wheel-zipped, else return direct path
def _default_world_config() -> Path:
    traversable = files("skyherd").joinpath("worlds/ranch_a.yaml")
    # If directly on filesystem (editable install or unzipped wheel), use it
    try:
        return Path(str(traversable))  # works when Traversable is a real Path
    except (TypeError, ValueError):
        # Fallback: extract to a temp file (rare; only for zipimport)
        import tempfile
        tmp = Path(tempfile.mkstemp(suffix=".yaml")[1])
        tmp.write_bytes(traversable.read_bytes())
        return tmp
```

**For SkyHerd's install model (uv sync into a venv, not zipimport), the first `with as_file() as p: return p` is safe** because `as_file()` only returns a tempdir for zipimported packages. Document this decision in the planner's decision log.

### 2. Fresh-clone smoke script (BLD-02)
```bash
#!/usr/bin/env bash
# Source: scripts/fresh_clone_smoke.sh
# Verifies the README quickstart on a clean mktemp -d sandbox.
# Exits 0 on success, non-zero on any quickstart failure.
# Target runtime: < 5 min on a cold Ubuntu GitHub Actions runner.

set -euo pipefail

START=$(date +%s)
SANDBOX=$(mktemp -d -t skyherd-smoke.XXXXXX)
# shellcheck disable=SC2064
trap "rm -rf '$SANDBOX'" EXIT INT TERM

SOURCE_REPO="${GITHUB_WORKSPACE:-$(pwd)}"

echo "===> [fresh-clone] sandbox: $SANDBOX"
echo "===> [fresh-clone] source:  $SOURCE_REPO"

# Clone via file:// so git uses the checkout rather than pulling origin
git clone --depth 1 "file://${SOURCE_REPO}" "$SANDBOX/repo"
cd "$SANDBOX/repo"

echo "===> [fresh-clone] step 1: uv sync"
uv sync

echo "===> [fresh-clone] step 2: pnpm install + build"
(cd web && pnpm install --frozen-lockfile && pnpm run build)

echo "===> [fresh-clone] step 3: make demo SEED=42 SCENARIO=all"
timeout 180 make demo SEED=42 SCENARIO=all

echo "===> [fresh-clone] step 4: smoke dashboard live mode"
# Start uvicorn in background, probe /health, then kill
uv run uvicorn skyherd.server.app:app --port 18765 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null || true; rm -rf '$SANDBOX'" EXIT INT TERM

# Poll /health for up to 20s
for i in $(seq 1 20); do
    if curl -sf "http://127.0.0.1:18765/health" > /dev/null; then
        echo "===> [fresh-clone] dashboard /health OK after ${i}s"
        break
    fi
    sleep 1
    if [ "$i" -eq 20 ]; then
        echo "===> [fresh-clone] FAIL: dashboard /health never responded"
        exit 1
    fi
done

# Probe /api/snapshot (mock mode here because we didn't bootstrap live deps —
# that's a separate concern; this script asserts the quickstart, not live mode)
curl -sf "http://127.0.0.1:18765/api/snapshot" | head -c 200

END=$(date +%s)
echo "===> [fresh-clone] PASS in $((END - START))s"
```

### 3. Makefile dashboard target flip (BLD-03)
```make
# Target: Makefile (replaces existing dashboard target lines 19-21)

dashboard:  ## Build web assets + start live dashboard (real mesh/world/ledger)
	(cd web && (pnpm install --frozen-lockfile || pnpm install) && pnpm run build) && \
	uv run python -m skyherd.server.live --port 8000

dashboard-mock:  ## Legacy mock-only dashboard (synthetic events)
	(cd web && (pnpm install --frozen-lockfile || pnpm install) && pnpm run build) && \
	SKYHERD_MOCK=1 uv run uvicorn skyherd.server.app:app --port 8000
```

### 4. New live-mode bootstrap (BLD-03)
```python
# Target: src/skyherd/server/live.py   (NEW FILE, ~60 lines)
"""Live-mode dashboard bootstrap — constructs real mesh/world/ledger
and hands them to create_app().  Opposite of SKYHERD_MOCK=1."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import typer
import uvicorn

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.server.app import create_app
from skyherd.world.world import make_world

app = typer.Typer(name="skyherd-server-live", add_completion=False)
logger = logging.getLogger(__name__)


@app.command()
def start(
    port: int = typer.Option(8000, "--port"),
    host: str = typer.Option("0.0.0.0", "--host"),
    seed: int = typer.Option(42, "--seed"),
) -> None:
    """Start dashboard in live mode: real world + in-memory ledger + demo mesh."""
    logging.basicConfig(level=logging.INFO)

    # Construct real deps
    world = make_world(seed=seed)  # BLD-01 default config

    ledger_db = Path(tempfile.mkstemp(suffix="_skyherd_ledger.db")[1])
    signer = Signer.generate()
    ledger = Ledger.open(str(ledger_db), signer)

    # Defer heavy mesh import; use the demo mesh (already used by scenarios)
    from skyherd.scenarios.base import _DemoMesh
    mesh = _DemoMesh(ledger=ledger)

    logger.info(
        "Live dashboard starting: seed=%d ledger=%s world_cows=%d",
        seed, ledger_db, len(world.herd.cows)
    )

    live_app = create_app(mock=False, mesh=mesh, world=world, ledger=ledger)
    uvicorn.run(live_app, host=host, port=port, log_level="info")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

Module path `skyherd.server.live` matches the Makefile invocation `python -m skyherd.server.live`. Alternatively: register as a `project.scripts` entry `skyherd-server-live = "skyherd.server.live:main"`.

### 5. Hatchling force-include for packaged data (BLD-01)
```toml
# Target: pyproject.toml (addition near existing [tool.hatch.build.targets.wheel])

[tool.hatch.build.targets.wheel]
packages = ["src/skyherd"]

[tool.hatch.build.targets.wheel.force-include]
"worlds" = "skyherd/worlds"

[tool.hatch.build.targets.sdist]
include = [
    "src/**",
    "worlds/**",
    "README.md",
    "LICENSE",
    "pyproject.toml",
    "Makefile",
]
```
[CITED: hatch.pypa.io/latest/config/build/] — `force-include` recursively copies the directory into the wheel at the specified path.

### 6. README quickstart doc-drift guard (BLD-02)
```python
# Target: tests/test_readme_quickstart.py   (NEW)
"""README must document the canonical 3-command quickstart.

Guards against silent drift: if anyone removes or changes the quickstart
commands in README.md, this test fails loudly.  The expected commands
also appear in CLAUDE.md and scripts/fresh_clone_smoke.sh — all three
must agree.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
README = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

EXPECTED_COMMANDS = [
    "uv sync",
    "pnpm install",
    "pnpm run build",
    "make demo SEED=42 SCENARIO=all",
    "make dashboard",
]


def test_readme_quickstart_commands_present() -> None:
    for cmd in EXPECTED_COMMANDS:
        assert cmd in README, f"README missing expected quickstart command: {cmd!r}"


def test_readme_quickstart_section_present() -> None:
    assert "Quickstart (3 commands)" in README or "Quickstart" in README
```

### 7. BLD-03 integration test
```python
# Target: tests/server/test_live_app.py   (NEW)
"""Live-mode /api/snapshot returns real world data, not mock data."""
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.server.app import create_app
from skyherd.world.world import make_world


def test_live_snapshot_returns_real_world_data():
    world = make_world(seed=42)
    signer = Signer.generate()
    ledger_path = Path(tempfile.mkstemp(suffix=".db")[1])
    ledger = Ledger.open(str(ledger_path), signer)

    app = create_app(mock=False, mesh=None, world=world, ledger=ledger)
    with TestClient(app) as client:
        r = client.get("/api/snapshot")
        assert r.status_code == 200
        snap = r.json()
        # Real world: 50 cows (per ranch_a.yaml) — mock has 12
        assert len(snap["cows"]) == 50
        # Real world snapshot has sim_time_s=0.0 at boot — mock is time.time() % 86400
        assert snap["sim_time_s"] == 0.0
```

### 8. BLD-01 regression test
```python
# Target: tests/world/test_make_world_default.py   (NEW)
"""make_world(seed=42) must work with no config_path argument."""
from skyherd.world.world import make_world


def test_make_world_no_config_path() -> None:
    """The canonical judge quickstart invocation."""
    world = make_world(seed=42)
    assert world is not None
    assert len(world.herd.cows) == 50  # ranch_a.yaml has 50 cows


def test_make_world_keyword_only_seed() -> None:
    """Defensive: seed=42 keyword, no positional args."""
    world = make_world(seed=42)
    assert world.clock.sim_time_s == 0.0


def test_make_world_deterministic_without_config() -> None:
    """Same default config + same seed → identical cow positions."""
    w1 = make_world(seed=7)
    w2 = make_world(seed=7)
    assert [c.pos for c in w1.herd.cows] == [c.pos for c in w2.herd.cows]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pkg_resources` / `setuptools`-style resources | `importlib.resources.files()` + `as_file()` | Python 3.9 introduced `files()`, 3.11 stabilized it, 3.12 refined MultiplexedPath handling | Drop-in stable; no more setuptools entry-point hacks. [CITED: docs.python.org/3/library/importlib.resources.html] |
| `setup.py package_data` | `pyproject.toml` with backend-specific data config (hatchling `force-include`, setuptools `package-data`, poetry `include`) | PEP 621 (2021) standardized pyproject.toml; hatchling supports `force-include` as of 1.x | Build backend-specific; SkyHerd uses hatchling, so `force-include` is the right idiom. [CITED: hatch.pypa.io/latest/config/build/] |
| `python setup.py develop` | `uv pip install -e .` / `uv sync` | `uv` reached prod stability in 2025 | Faster, lockfile-pinned; already in use in this repo. [VERIFIED: uv.lock + pyproject.toml:1-3] |
| Makefile targets that hard-code mock | Explicit `make <target>-mock` for legacy + default to live | Best practice for demo-facing tools — defaults should demo what the product does | Quickstart judge sees live dashboard, not synthetic events. |
| Ad-hoc README code-snippet validation | Automated doc-drift test in pytest | CLI tool releases (e.g. `docsgen`, `cogapp`) popularized "doc as code" | Prevents silent drift — judge-critical for a hackathon. |

**Deprecated/outdated:**
- `pkg_resources` (part of `setuptools`): slow, side-effect heavy, deprecated in favor of `importlib.resources`. [CITED: docs.python.org/3/library/importlib.resources.html]
- `Path(__file__).parent.parent.parent…` for packaged data: never worked in wheel installs; works in editable by accident. Replace.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `as_file(files(pkg).joinpath(...))` returns a real filesystem `Path` in wheel installs without zipimport (which is SkyHerd's install model via uv) | §Code Examples (1) | If uv somehow produces a zipimported install (it doesn't today, but future-proofing), `as_file()` would need a context manager. Mitigation: wrap in try/except or use the Traversable-then-copy fallback in Pattern 1 alt. |
| A2 | Fresh-clone on a cold Ubuntu runner completes under 5 min | §Pitfall 4 | If pnpm registry is slow, SLA violated. Mitigation: pnpm cache directive in CI job (one-line fix); cap timeout at 10 min initially, tighten when stable. |
| A3 | `_DemoMesh` from `scenarios/base.py` is the correct mesh to use in live-mode bootstrap (vs constructing the real `AgentMesh` from `agents/mesh.py`) | §Code Examples (4) | If Phase 5 expects a real `AgentMesh`, the live bootstrap needs to swap. `_DemoMesh` is pragmatic for Phase 4 (same object scenarios use). Confirm with Phase 5 plan before finalizing. |
| A4 | Hatchling `force-include` map `"worlds" = "skyherd/worlds"` lands the files at `skyherd/worlds/…` inside the wheel (matching the `importlib.resources.files("skyherd").joinpath("worlds/…")` lookup) | §Pattern 2, §Pitfall 6 | If the target path interpretation differs, `importlib.resources` returns FileNotFoundError. Mitigation: `uv build` locally + `unzip -l dist/*.whl | grep worlds` to verify. |
| A5 | Phase 5 (Dashboard Live-Mode & Vet-Intake) consumes Phase 4's live bootstrap without further plumbing changes | §Domain Context | If Phase 5 rewires the bootstrap, Phase 4 work is partially thrown away. Coordinate: Phase 4 lands the plumbing signature (`create_app(mock=False, mesh, world, ledger)`); Phase 5 can wrap it but should not redesign it. |
| A6 | No existing tests in `tests/` rely on `make_world` *failing* when called without config_path | §Domain Context | If a test pins the current TypeError behavior, BLD-01 would break it. Mitigation: grep `tests/` for `TypeError` near `make_world` — none found in quick audit. |

## Open Questions (RESOLVED)

1. **Should `make dashboard` live-mode run a background scenario loop so agent lanes populate?**
   - What we know: Live `/api/agents` returns empty until a scenario wakes an agent.
   - What's unclear: Whether Phase 4's "functional dashboard" (BLD-03) implies non-empty agent lanes, or whether empty-at-boot is acceptable and Phase 5 polishes this.
   - Recommendation: Phase 4 ships empty-at-boot and documents a "run `make demo` in another terminal to see agent lanes populate" hint in the Makefile comment. Phase 5 (DASH-06) owns the "all 5 agents on distinct lanes with real session IDs" requirement.

2. **Should the fresh-clone CI job gate every PR, or only `main` pushes / nightly?**
   - What we know: CI already has 3 jobs per PR (ci matrix, web, pip-audit). Adding a 4th adds ~5 min to the PR turnaround.
   - What's unclear: George's preference for CI cost vs. coverage.
   - Recommendation: Add as a `workflow_dispatch` + `schedule: '0 8 * * *'` job initially (nightly + manual). Promote to PR-blocking once stable. Document in the plan so the planner can mark this a deferred sub-decision.

3. **Does `uv sync` in a fresh-clone install the edge / voice extras?**
   - What we know: `pyproject.toml` has `[project.optional-dependencies]` for `edge`, `voice`, `obs`, `dev`, `docs`. Default `uv sync` does NOT install extras unless `--all-extras` or `--extra X` is passed. CI uses `--all-extras`.
   - What's unclear: Whether README's `uv sync` implies extras.
   - Recommendation: README's `uv sync` (no `--all-extras`) is the judge-facing command — confirm `make demo SEED=42 SCENARIO=all` works without any extras. Verified via `make demo` running in ~3s per CONCERNS §5 — no extras needed. Document this explicitly in the plan.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All BLD tasks | ✓ | 3.11 / 3.12 (CI matrix) | — |
| uv | BLD-02 smoke + Makefile | ✓ | setup-uv@v5 (latest) | — |
| hatchling | BLD-01 data packaging | ✓ | auto-resolved via `build-system.requires` | — |
| pnpm 9 | BLD-02 (web build) | ✓ | pinned in CI | — |
| Node 20 | BLD-02 (web build) | ✓ | pinned in CI | — |
| bash (for smoke script) | BLD-02 | ✓ | ubuntu-latest + macos-14 both ship bash 4+ | — |
| curl | BLD-02 smoke /health probe | ✓ | standard on GH runners | — |
| git | BLD-02 `file://` clone | ✓ | — | — |
| docker | — (not needed for Phase 4) | ✓ (on runner) | — | N/A — Phase 4 has no Docker dependency. SITL Docker is Phase 6. |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

All infrastructure required for Phase 4 is already provisioned and verified via the existing `.github/workflows/ci.yml` matrix run.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8 + pytest-asyncio 0.24 (`asyncio_mode = "auto"`) |
| Config file | `pyproject.toml` §[tool.pytest.ini_options] (testpaths=["tests"], pythonpath=["src"]) |
| Quick run command | `uv run pytest tests/world/test_make_world_default.py tests/server/test_live_app.py tests/test_readme_quickstart.py -x -q` |
| Full suite command | `uv run pytest --cov=src/skyherd --cov-report=term-missing --cov-fail-under=80 -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| BLD-01 | `make_world(seed=42)` works with no config_path arg | unit | `uv run pytest tests/world/test_make_world_default.py::test_make_world_no_config_path -x` | ❌ Wave 0 |
| BLD-01 | Default config resolves to packaged `worlds/ranch_a.yaml` (50 cows) | unit | `uv run pytest tests/world/test_make_world_default.py::test_make_world_no_config_path -x` | ❌ Wave 0 |
| BLD-01 | Default config is deterministic across two calls | unit | `uv run pytest tests/world/test_make_world_default.py::test_make_world_deterministic_without_config -x` | ❌ Wave 0 |
| BLD-01 | `importlib.resources.files("skyherd").joinpath("worlds/ranch_a.yaml")` resolves | unit | `uv run pytest tests/world/test_packaged_data.py::test_worlds_packaged -x` | ❌ Wave 0 |
| BLD-02 | Fresh-clone quickstart exits 0 under 5 min | smoke (shell) | `bash scripts/fresh_clone_smoke.sh` | ❌ Wave 0 |
| BLD-02 | README contains canonical 3-command strings | unit (doc-drift) | `uv run pytest tests/test_readme_quickstart.py -x` | ❌ Wave 0 |
| BLD-02 | CI has fresh-clone job that runs on main + manual | CI assertion | `gh workflow run fresh-clone-smoke.yml --ref <sha>` | ❌ Wave 0 |
| BLD-03 | `make dashboard` starts live (non-mock) by default | smoke (shell) | `timeout 20 make dashboard &` + `curl /health` + assert 200 | ❌ Wave 0 |
| BLD-03 | `/api/snapshot` returns 50 cows from real world (not 12 mock) | integration | `uv run pytest tests/server/test_live_app.py::test_live_snapshot_returns_real_world_data -x` | ❌ Wave 0 |
| BLD-03 | `make dashboard-mock` still serves mock (backward-compat) | smoke | `timeout 20 make dashboard-mock &` + `curl /api/snapshot` + assert mock shape | ❌ Wave 0 |
| BLD-03 | `create_app(mock=False, mesh, world, ledger)` wiring branch coverage | unit/integration | pytest-cov report shows `src/skyherd/server/app.py:83-95,134-156` covered | partial (73%→85% target) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/world/test_make_world_default.py tests/server/test_live_app.py tests/test_readme_quickstart.py -x -q` (runs in <5s)
- **Per wave merge:** `uv run pytest --cov=src/skyherd --cov-fail-under=80 -q` (full suite, ~2-3 min) + `bash scripts/fresh_clone_smoke.sh` locally
- **Phase gate:** Full suite green + fresh-clone smoke green on CI before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/world/test_make_world_default.py` — covers BLD-01 (default config + determinism)
- [ ] `tests/world/test_packaged_data.py` — covers BLD-01 (importlib.resources + wheel layout)
- [ ] `tests/server/test_live_app.py` — covers BLD-03 (live `/api/snapshot` returns real data)
- [ ] `tests/test_readme_quickstart.py` — covers BLD-02 (doc-drift guard)
- [ ] `scripts/fresh_clone_smoke.sh` — covers BLD-02 (fresh-clone SLA)
- [ ] `.github/workflows/fresh-clone-smoke.yml` (or job in `ci.yml`) — covers BLD-02 (CI assertion)
- [ ] Framework install: none needed — pytest already configured.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 4 adds no auth surface. Dashboard has no auth today (by design — localhost-only). |
| V3 Session Management | no | No user sessions added. |
| V4 Access Control | no | No access-control changes. |
| V5 Input Validation | partial | Live bootstrap reads seed from CLI (`--seed int`) — typer enforces type. No untrusted input accepted. |
| V6 Cryptography | no | Ed25519 signer already exists in `src/skyherd/attest/signer.py`; Phase 4 only *instantiates* it via `Signer.generate()` in the live bootstrap, does not modify crypto. |
| V7 Errors & Logging | yes | Live bootstrap must log (not silently swallow) errors starting the mesh/ledger. Use `logger.info`/`logger.error`, not bare `except: pass` (per CLAUDE.md HYG-01). |
| V9 Configuration | yes | `pyproject.toml` `force-include` must not accidentally ship `.env.local` / `runtime/` (see Pitfall below). |

### Known Threat Patterns for `{hatchling + importlib.resources + FastAPI}` stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Accidentally packaging `.env.local` / `runtime/*.db` / secrets via broad `force-include` | Information Disclosure | Narrow mapping to `"worlds" = "skyherd/worlds"` only; verify wheel contents with `unzip -l dist/*.whl`. Do NOT use `"." = "skyherd"` patterns. |
| Live dashboard exposed publicly → exposes ledger events | Information Disclosure | Default bind host `127.0.0.1` not `0.0.0.0` in the live bootstrap. If `--host 0.0.0.0` is allowed, CORS remains locked (already enforced in `app.py:62-71`). |
| Dashboard `/api/attest` exposes Merkle chain entries with potentially-sensitive payload JSON | Information Disclosure | Already gated by `iter_events(since_seq=…)` which only returns indexed events. Phase 4 does NOT add new payload types. |
| CI fresh-clone script executes arbitrary repo code (e.g., malicious PR) | Tampering | PR-based CI already runs repo code — no new surface. Fresh-clone script just extends this. Standard GH Actions trust model applies. |
| `scripts/fresh_clone_smoke.sh` `rm -rf "$SANDBOX"` accidentally removing non-sandbox | Denial of Service | Use `mktemp -d` (always creates new dir) + trap EXIT. Never use env var-expanded paths in `rm -rf` without the sandbox prefix check. |

**Security sanity on the phase diff:** Phase 4 adds no network endpoints, no auth primitives, no new secret handling, no user-input parsing beyond typer-typed CLI flags. Risk profile: LOW. Enforce HYG-01 (no silent exception swallowing) in the new `src/skyherd/server/live.py` module and `scripts/fresh_clone_smoke.sh`.

## Project Constraints (from CLAUDE.md)

Extracted actionable directives relevant to Phase 4:

- **No AGPL deps:** Phase 4 adds no runtime deps (only stdlib + existing hatchling). Safe.
- **MIT throughout:** hatchling is BSD-licensed, stdlib is PSF-licensed, both compatible with MIT. Safe.
- **All code new, no imports from sibling `/home/george/projects/active/drone/` repo:** Phase 4 only edits code within this repo. Safe.
- **TDD mandatory for features and bug fixes:** All BLD-01/02/03 changes require tests-first per pattern. Wave 0 test list above covers this.
- **No Claude/Anthropic attribution in commits:** Global git config handles this. No action needed.
- **Plan > CLAUDE.md > vision doc > own judgment:** The plan locked v5.1 at `/home/george/.claude/plans/update-ur-memory-project-context-splendid-swan.md` takes precedence — but Phase 4 is in the brownfield-audit closure milestone (v1 requirements), not in the original v5.1 execution plan. So this milestone's RESEARCH.md takes precedence for Phase 4 scope.
- **Skills-first architecture:** Not applicable to this phase (no agent / prompt changes).
- **Code reviewer agent after writing code:** Planner should include a `code-reviewer` invocation in the Wave that lands the diffs.
- **Context preservation is paramount:** Phase 4 is a delegate-friendly phase — small, well-scoped, clear requirements. Planner should use sub-agents for each of: (a) `pyproject.toml` + world.py edit, (b) Makefile + live bootstrap, (c) fresh-clone script + CI, (d) test suite.

## Sources

### Primary (HIGH confidence)
- [docs.python.org/3/library/importlib.resources](https://docs.python.org/3/library/importlib.resources.html) — `files()` + `as_file()` API for Python 3.11+
- [hatch.pypa.io/latest/config/build/](https://hatch.pypa.io/latest/config/build/) — `[tool.hatch.build.targets.wheel.force-include]` TOML syntax
- `src/skyherd/server/app.py:74-83, 134-156, 268-281` — existing `create_app()` factory with DI (already accepts mesh/world/ledger)
- `src/skyherd/world/world.py:149-195` — current `make_world()` signature
- `src/skyherd/world/cli.py:23` — current `__file__`-walking pattern (to be replaced)
- `src/skyherd/scenarios/base.py:222-223, 234` — existing `_DemoMesh` + `make_world` caller
- `tests/world/test_determinism.py:9, 14, 54` — existing test pattern for make_world
- `.github/workflows/ci.yml:17-52, 111-167` — existing CI job structure to extend
- `Makefile:19-21` — current `make dashboard` target to flip
- `pyproject.toml:1-3, 90-91` — hatchling build backend + wheel packaging
- `.planning/codebase/CONCERNS.md §5-6` — ground-truth build health + Priority 10
- `.planning/REQUIREMENTS.md:37-40` — BLD-01/02/03 canonical text

### Secondary (MEDIUM confidence)
- Cross-referenced: README.md:17-22 and CLAUDE.md:35-40 both document the 3-command quickstart identically — safe anchor for doc-drift test.
- Cross-referenced: Makefile:19-21 and CLAUDE.md "Build commands" agree on `make dashboard` as the target name.

### Tertiary (LOW confidence)
- None. All Phase 4 claims verified either from official docs (`docs.python.org`, `hatch.pypa.io`) or from ground-truth inspection of the codebase files.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tooling already present and used in this repo; no new dependencies.
- Architecture: HIGH — app factory already supports the needed DI; plumbing only.
- Pitfalls: MEDIUM — some (A1 as_file behavior, A4 force-include target path) are easily verified via `uv build` + `unzip -l` but haven't been executed yet. Planner should schedule that as a Wave 0 verification step.
- Security: HIGH — risk profile is LOW; phase adds no new attack surface.

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (30 days — hatchling + importlib.resources are both mature stable APIs; no fast-moving concern)

## RESEARCH COMPLETE
