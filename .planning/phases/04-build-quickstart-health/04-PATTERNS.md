# Phase 4: Build & Quickstart Health - Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 8 new/modified files
**Analogs found:** 7 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/skyherd/world/world.py` | utility (factory) | transform | self (existing `make_world`) | self-edit |
| `pyproject.toml` | config | — | self (existing `[tool.hatch.build.targets.wheel]`) | self-edit |
| `src/skyherd/server/live.py` | service (CLI entrypoint) | request-response | `src/skyherd/server/cli.py` | exact |
| `Makefile` | config | — | self (existing `dashboard` target, line 19-21) | self-edit |
| `scripts/fresh_clone_smoke.sh` | utility (shell script) | batch | `scripts/cloudflared-setup.sh` | role-match |
| `tests/world/test_make_world_default.py` | test | CRUD | `tests/world/test_determinism.py` | exact |
| `tests/server/test_live_app.py` | test | request-response | `tests/server/test_app.py` | exact |
| `tests/test_readme_quickstart.py` | test | transform | `tests/world/test_determinism.py` | role-match |

## Pattern Assignments

---

### `src/skyherd/world/world.py` (factory utility, self-edit)

**Analog:** self — existing file `src/skyherd/world/world.py`

The only change is adding a `_default_world_config()` helper and making `config_path` optional with `None` default. All other code is unchanged.

**Current signature to replace** (line 149):
```python
def make_world(seed: int, config_path: Path) -> World:
```

**Target signature:**
```python
def make_world(seed: int, config_path: Path | None = None) -> World:
```

**Imports pattern — add to existing import block** (lines 1-16):
```python
from importlib.resources import as_file, files
```
(`from __future__ import annotations` already on line 1; `from pathlib import Path` already on line 7.)

**New helper to insert immediately above `make_world`** (after line 147, before the factory docstring):
```python
def _default_world_config() -> Path:
    """Return the packaged worlds/ranch_a.yaml as a filesystem Path.

    Works in both editable installs (uv sync -e .) and wheel installs
    because hatchling force-include ships worlds/ as skyherd/worlds/.
    """
    traversable = files("skyherd").joinpath("worlds/ranch_a.yaml")
    # For uv-managed venv installs (not zipimport), Traversable IS a Path.
    # str() cast is safe here; as_file() only differs for zipimport.
    try:
        return Path(str(traversable))
    except (TypeError, ValueError):
        # Rare fallback: zipimport. Extract to tempfile.
        import tempfile
        tmp = Path(tempfile.mkstemp(suffix=".yaml")[1])
        tmp.write_bytes(traversable.read_bytes())
        return tmp
```

**First two lines of `make_world` body to add** (after the docstring):
```python
    if config_path is None:
        config_path = _default_world_config()
```

**Backward-compat:** All existing callers pass `config_path` explicitly (`scenarios/base.py:222`, `world/cli.py:40`, `tests/world/test_determinism.py:14`) — they continue working unchanged because the parameter stays positional-or-keyword.

---

### `pyproject.toml` (config, self-edit)

**Analog:** self — existing `[tool.hatch.build.targets.wheel]` block (lines 90-91)

**Current block** (lines 90-91):
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/skyherd"]
```

**Target block** (two tables, no removal):
```toml
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

**New entry-point to add** under `[project.scripts]` (lines 81-88):
```toml
skyherd-server-live = "skyherd.server.live:main"
```

**Verification command** (run after edit, before committing):
```bash
uv build && unzip -l dist/skyherd_engine-*.whl | grep worlds
# Expected: skyherd/worlds/ranch_a.yaml + skyherd/worlds/ranch_b.yaml
```

---

### `src/skyherd/server/live.py` (service CLI entrypoint, request-response)

**Analog:** `src/skyherd/server/cli.py` (lines 1-43) — same typer + uvicorn pattern; same `main()`/`app` structure.

**Imports pattern** — copy from `cli.py` lines 1-9, extend with live-mode deps:
```python
"""Live-mode dashboard bootstrap — constructs real mesh/world/ledger
and passes them to create_app().  Inverse of SKYHERD_MOCK=1."""

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
```

**Typer app declaration** — copy from `cli.py` line 11:
```python
app = typer.Typer(name="skyherd-server-live", add_completion=False)
logger = logging.getLogger(__name__)
```

**Core command pattern** — extend `cli.py` lines 14-35 with live-dep construction:
```python
@app.command()
def start(
    port: int = typer.Option(8000, "--port", "-p", help="HTTP port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host"),
    seed: int = typer.Option(42, "--seed", help="World RNG seed"),
    log_level: str = typer.Option("info", "--log-level"),
) -> None:
    """Start dashboard in live mode: real world + in-memory ledger + demo mesh."""
    logging.basicConfig(level=log_level.upper())

    # Construct real deps (same pattern as scenarios/base.py:226-231)
    world = make_world(seed=seed)  # uses BLD-01 default config

    tmp = tempfile.NamedTemporaryFile(suffix="_skyherd_ledger.db", delete=False)
    tmp.close()
    signer = Signer.generate()
    ledger = Ledger.open(tmp.name, signer)

    from skyherd.scenarios.base import _DemoMesh  # local import — avoids circular
    mesh = _DemoMesh(ledger=ledger)

    logger.info(
        "Live dashboard: seed=%d world_cows=%d ledger=%s",
        seed, len(world.herd.cows), tmp.name,
    )
    typer.echo(f"Starting SkyHerd live dashboard on {host}:{port} (seed={seed})")
    typer.echo("  Agent lanes will populate once 'make demo' runs in another terminal.")

    live_app = create_app(mock=False, mesh=mesh, world=world, ledger=ledger)
    uvicorn.run(live_app, host=host, port=port, log_level=log_level)
```

**`main()` + `__main__` guard** — copy verbatim from `cli.py` lines 38-43:
```python
def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

**Key difference from `cli.py`:** `live.py` passes a string module path to `uvicorn.run()` in `cli.py` (which allows `--reload`), but `live.py` must pass the **live app object** directly because deps were injected before the factory call. No `--reload` support needed.

---

### `Makefile` (config, self-edit)

**Analog:** self — existing `dashboard` target lines 19-21.

**Current target** (lines 19-21):
```make
dashboard:
	(cd web && (pnpm install --frozen-lockfile || pnpm install) && pnpm run build) && \
	SKYHERD_MOCK=1 uv run uvicorn skyherd.server.app:app --port 8000
```

**Target replacement** (flip default to live; add `dashboard-mock`):
```make
dashboard:  ## Build web assets and start live dashboard (real mesh/world/ledger)
	(cd web && (pnpm install --frozen-lockfile || pnpm install) && pnpm run build) && \
	uv run python -m skyherd.server.live --port 8000

dashboard-mock:  ## Legacy mock-only dashboard (synthetic events, no sim required)
	(cd web && (pnpm install --frozen-lockfile || pnpm install) && pnpm run build) && \
	SKYHERD_MOCK=1 uv run uvicorn skyherd.server.app:app --port 8000
```

Also add `dashboard-mock` to the `.PHONY` list on line 1.

---

### `scripts/fresh_clone_smoke.sh` (batch shell script utility)

**Analog:** `scripts/cloudflared-setup.sh` — same bash conventions: `set -euo pipefail`, `#!/usr/bin/env bash`, explanatory header comment, env-var defaults with `${VAR:-default}` pattern.

**Header + safety pattern** (copy from `cloudflared-setup.sh` lines 1-21):
```bash
#!/usr/bin/env bash
# fresh_clone_smoke.sh — verify the README 3-command quickstart on a clean checkout.
#
# Usage:
#   bash scripts/fresh_clone_smoke.sh
#
# Exits 0 if the full quickstart completes successfully; non-zero on failure.
# Target runtime: < 5 min on a cold Ubuntu GitHub Actions runner.
#
# Environment variables:
#   GITHUB_WORKSPACE  — repo root to clone from (default: pwd)

set -euo pipefail
```

**Sandbox + trap pattern** (no existing analog; use POSIX best-practices):
```bash
START=$(date +%s)
SANDBOX=$(mktemp -d -t skyherd-smoke.XXXXXX)
trap 'rm -rf "$SANDBOX"' EXIT INT TERM

SOURCE_REPO="${GITHUB_WORKSPACE:-$(pwd)}"

echo "===> [smoke] sandbox: $SANDBOX"
echo "===> [smoke] source:  $SOURCE_REPO"

git clone --depth 1 "file://${SOURCE_REPO}" "$SANDBOX/repo"
cd "$SANDBOX/repo"
```

**Quickstart steps** (match README exactly):
```bash
echo "===> [smoke] step 1: uv sync"
uv sync

echo "===> [smoke] step 2: pnpm install + build"
(cd web && pnpm install --frozen-lockfile && pnpm run build)

echo "===> [smoke] step 3: make demo SEED=42 SCENARIO=all"
timeout 180 make demo SEED=42 SCENARIO=all
```

**Dashboard health probe** (background + curl poll — avoids CI hang from Pitfall 5):
```bash
echo "===> [smoke] step 4: dashboard /health probe"
uv run python -m skyherd.server.live --port 18765 &
SERVER_PID=$!
# Re-register trap to also kill server
trap "kill $SERVER_PID 2>/dev/null || true; rm -rf '$SANDBOX'" EXIT INT TERM

for i in $(seq 1 20); do
    if curl -sf "http://127.0.0.1:18765/health" > /dev/null 2>&1; then
        echo "===> [smoke] /health OK after ${i}s"
        break
    fi
    sleep 1
    if [ "$i" -eq 20 ]; then
        echo "===> [smoke] FAIL: /health never responded"
        exit 1
    fi
done

END=$(date +%s)
echo "===> [smoke] PASS in $((END - START))s"
```

---

### `tests/world/test_make_world_default.py` (unit test)

**Analog:** `tests/world/test_determinism.py` — same structure: module-level imports, class-free functions, `make_world` calls, `len(world.herd.cows) == 50` assertion.

**Imports pattern** (copy from `test_determinism.py` lines 1-7, strip config path):
```python
"""make_world(seed=42) must work with no config_path argument (BLD-01)."""

from __future__ import annotations

from skyherd.world.world import make_world
```

**Core test pattern** (modeled on `test_determinism.py:70-73` — `test_world_loads_from_config`):
```python
def test_make_world_no_config_path() -> None:
    """The canonical judge quickstart invocation — no config_path arg."""
    world = make_world(seed=42)
    assert world is not None
    assert len(world.herd.cows) == 50  # ranch_a.yaml has 50 cows
    assert world.clock.sim_time_s == 0.0


def test_make_world_deterministic_without_config() -> None:
    """Same seed + default config → identical cow positions."""
    w1 = make_world(seed=7)
    w2 = make_world(seed=7)
    assert [c.pos for c in w1.herd.cows] == [c.pos for c in w2.herd.cows]


def test_make_world_explicit_config_still_works() -> None:
    """Backward-compat: existing callers passing config_path= still pass."""
    from pathlib import Path
    config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
    world = make_world(seed=42, config_path=config)
    assert len(world.herd.cows) == 50
```

---

### `tests/server/test_live_app.py` (integration test)

**Analog:** `tests/server/test_app.py` — same fixture shape (`create_app`, `TestClient`/`AsyncClient`), same endpoint probing pattern.

**Imports pattern** (extend `test_app.py` lines 1-15 with live-mode deps):
```python
"""Live-mode /api/snapshot returns real world data, not mock data (BLD-03)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.server.app import create_app
from skyherd.world.world import make_world
```

**Live fixture pattern** (note: use `TestClient` not `AsyncClient` — simpler for integration without SSE):
```python
def _make_live_client():
    world = make_world(seed=42)
    signer = Signer.generate()
    ledger_path = Path(tempfile.mkstemp(suffix=".db")[1])
    ledger = Ledger.open(str(ledger_path), signer)
    app = create_app(mock=False, mesh=None, world=world, ledger=ledger)
    return TestClient(app)
```

**Core assertion pattern** (real world has 50 cows; mock has 12 — distinction comes from `test_app.py:53-60`):
```python
def test_live_snapshot_returns_real_world_data() -> None:
    client = _make_live_client()
    r = client.get("/api/snapshot")
    assert r.status_code == 200
    snap = r.json()
    assert len(snap["cows"]) == 50   # ranch_a.yaml — mock only returns 12
    assert snap["sim_time_s"] == 0.0  # boot state, not mocked time.time()


def test_live_health_ok() -> None:
    client = _make_live_client()
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```

---

### `tests/test_readme_quickstart.py` (doc-drift guard test)

**Analog:** `tests/world/test_determinism.py` — same role-match: a simple pytest file with no fixtures, only assertions about data loaded at module level.

**Pattern** (plain pytest functions, no classes, `Path(__file__)` anchoring like `test_determinism.py:9`):
```python
"""README must contain the canonical 3-command judge quickstart (BLD-02 doc-drift guard)."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_README = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")

_EXPECTED_COMMANDS = [
    "uv sync",
    "pnpm install",
    "pnpm run build",
    "make demo SEED=42 SCENARIO=all",
    "make dashboard",
]


def test_readme_quickstart_commands_present() -> None:
    for cmd in _EXPECTED_COMMANDS:
        assert cmd in _README, f"README missing quickstart command: {cmd!r}"


def test_readme_has_quickstart_section() -> None:
    assert "Quickstart" in _README or "quickstart" in _README.lower()
```

---

## Shared Patterns

### Typer CLI entrypoint structure
**Source:** `src/skyherd/server/cli.py` (all 43 lines)
**Apply to:** `src/skyherd/server/live.py`

Every CLI module in this project follows the same four-part structure:
```python
app = typer.Typer(name="<name>", add_completion=False)

@app.command()
def start(...) -> None:
    ...

def main() -> None:
    app()

if __name__ == "__main__":
    main()
```
The `main()` wrapper is what the `[project.scripts]` entry-point calls.

### Ledger + Signer construction
**Source:** `src/skyherd/scenarios/base.py` lines 226-231
**Apply to:** `src/skyherd/server/live.py` and `tests/server/test_live_app.py`

```python
import tempfile
from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer

tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmp.close()
signer = Signer.generate()
ledger = Ledger.open(tmp.name, signer)
```

### `_DemoMesh` construction (reuse, do not recreate)
**Source:** `src/skyherd/scenarios/base.py` lines 158-196 and line 231
**Apply to:** `src/skyherd/server/live.py`

```python
from skyherd.scenarios.base import _DemoMesh  # local import — avoids circular
mesh = _DemoMesh(ledger=ledger)
```

`_DemoMesh` is the correct Phase 4 mesh choice (same object all scenarios use; Phase 5 / DASH-06 owns the real `AgentMesh` swap decision).

### `make_world` caller pattern
**Source:** `src/skyherd/scenarios/base.py` line 223 and `src/skyherd/world/cli.py` line 40
**Apply to:** `src/skyherd/server/live.py`, `tests/server/test_live_app.py`, `tests/world/test_make_world_default.py`

After BLD-01 lands, the canonical call for new code is:
```python
world = make_world(seed=42)  # no config_path needed
```
Existing callers that pass `config_path` explicitly keep working unchanged.

### `set -euo pipefail` + `mktemp` + trap shell pattern
**Source:** `scripts/cloudflared-setup.sh` lines 21 (set -euo pipefail), combined with POSIX mktemp best-practices
**Apply to:** `scripts/fresh_clone_smoke.sh`

```bash
set -euo pipefail
SANDBOX=$(mktemp -d -t skyherd-smoke.XXXXXX)
trap 'rm -rf "$SANDBOX"' EXIT INT TERM
```

Always quote the path in `rm -rf` to guard against spaces; never expand an unvalidated var in rm -rf.

### GitHub Actions CI job structure
**Source:** `.github/workflows/ci.yml` — `sitl-e2e` job (lines 113-133) — closest analog: `workflow_dispatch`-only manual job.
**Apply to:** New `fresh-clone-smoke` job (or a new workflow file `.github/workflows/fresh-clone-smoke.yml`)

Copy the `sitl-e2e` job header pattern:
```yaml
fresh-clone-smoke:
  name: Fresh-clone smoke (≤5 min)
  runs-on: ubuntu-latest
  if: github.event_name == 'workflow_dispatch' || github.event_name == 'schedule'

  steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Install uv
      uses: astral-sh/setup-uv@v5
      with:
        python-version: "3.12"
        # NO cache: deliberately cold to match judge environment
        enable-cache: "false"

    - name: Setup Node
      uses: actions/setup-node@v4
      with:
        node-version: "20"

    - name: Setup pnpm
      uses: pnpm/action-setup@v4
      with:
        version: 9

    - name: Run fresh-clone smoke
      timeout-minutes: 10
      run: bash scripts/fresh_clone_smoke.sh
```

`enable-cache: "false"` on `setup-uv` is required — Pitfall 4 in RESEARCH.md. The cold-path SLA is the whole point of the job.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | — | — | All files have close analogs in the codebase |

---

## Critical Pitfalls (for planner action items)

From RESEARCH.md §Common Pitfalls — each needs an explicit planner step:

1. **`force-include` target path verification** — after editing `pyproject.toml`, run `uv build && unzip -l dist/skyherd_engine-*.whl | grep worlds` and assert `skyherd/worlds/ranch_a.yaml` appears. Failing this means `importlib.resources.files("skyherd").joinpath("worlds/ranch_a.yaml")` will raise `FileNotFoundError` on wheel installs.

2. **Dashboard CI hang** — `scripts/fresh_clone_smoke.sh` must spawn `make dashboard` (or `python -m skyherd.server.live`) in the background with `&`, then poll `/health` with a curl retry loop, then kill the PID. Never run the dashboard synchronously in a CI step.

3. **`as_file()` context manager leak** — the `_default_world_config()` helper in `world.py` must NOT use `with as_file(...) as p: return p` (the context manager exits and cleans up before the caller uses `p`). Use the `Path(str(traversable))` approach with try/except fallback instead (see Pattern Assignments above).

4. **`__file__`-walking in `scenarios/base.py:37` and `world/cli.py:23`** — these two constants (`_WORLD_CONFIG = _REPO_ROOT / "worlds" / "ranch_a.yaml"`) remain unchanged in Phase 4 (they work in editable installs; only `make_world()` itself needs the `importlib.resources` fix). Do NOT refactor these in Phase 4 — scope creep.

5. **Agent lane empty at live boot** — `create_app(mock=False, mesh=_DemoMesh(), ...)` will return `{"agents": []}` from `/api/agents` until a scenario runs. This is acceptable Phase 4 behavior. Document in the live bootstrap's CLI output (Pitfall 3 in RESEARCH.md).

---

## Metadata

**Analog search scope:** `src/skyherd/`, `tests/`, `scripts/`, `.github/workflows/`, `Makefile`, `pyproject.toml`
**Files scanned:** 12 source files read directly; directory structure inspected
**Pattern extraction date:** 2026-04-22
