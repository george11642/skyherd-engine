# Phase 4: Build & Quickstart Health - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

A judge cloning the repo fresh and running the documented 3-command quickstart succeeds in under 5 minutes, with `make_world(seed=42)` usable without arguments and `make dashboard` serving live-mode (not mock-only). First-30-second-of-demo-video stake.

Requirements: BLD-01, BLD-02, BLD-03.

(BLD-04 SITL-CI is in Phase 6 because Docker infra risk is isolated from this phase's scope.)

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices at Claude's discretion — discuss skipped per `workflow.skip_discuss=true`.

### Known Constraints from Audit
- `make_world()` at `src/skyherd/world/world.py` currently requires explicit `config_path` → `make_world(seed=42)` raises `TypeError`. Fix: default `config_path` resolving to `worlds/ranch_a.yaml` via `importlib.resources` or package-relative `Path` (preferred: `importlib.resources` for install-correctness).
- `make demo SEED=42 SCENARIO=all` currently passes in ~3s (per `CONCERNS.md §5`)
- `make dashboard` currently ALWAYS uses `SKYHERD_MOCK=1` — live path (real `mesh + world + ledger` injection in `src/skyherd/server/app.py:88-94,164-181,189-195`) is 73% covered and not wired in the Makefile target
- Judge quickstart (CLAUDE.md) is 3 commands: `git clone && cd`, `uv sync && (cd web && pnpm install && pnpm run build)`, `make demo SEED=42 SCENARIO=all` → `make dashboard`
- Fresh-clone verification: documented AND asserted in CI (or a dedicated script that runs on a clean worktree)
- Phase 4 must NOT break Phase 5 (live-mode dashboard) — coordinate: Phase 4 lands live-mode plumbing, Phase 5 polishes UX of that plumbing

</decisions>

<code_context>
## Existing Code Insights

Scoped files:
- `src/skyherd/world/world.py` — `make_world()` signature
- `worlds/ranch_a.yaml` — canonical default world config
- `Makefile` — `make demo`, `make dashboard`, `make test`, `make ci` targets
- `src/skyherd/server/app.py` — FastAPI live-path dependency injection (non-mock)
- `src/skyherd/server/events.py` — SSE live-path broadcaster
- `README.md` — Judge Quickstart (3 commands) doc
- `CLAUDE.md` — same quickstart referenced in project orientation
- `.github/workflows/` — CI config (to add fresh-clone smoke if needed)
- `pyproject.toml` — package data config (important for `importlib.resources` to find `worlds/ranch_a.yaml`)

</code_context>

<specifics>
## Specific Ideas

- Use `importlib.resources` (Python 3.11+ style `importlib.resources.files(...).joinpath(...)`) for world config discovery — survives packaging, no brittle `__file__` paths
- `pyproject.toml` likely needs `[tool.setuptools.package-data]` or uv equivalent to ship `worlds/*.yaml` into the install
- `make dashboard` default changes to live mode; add `make dashboard-mock` or `SKYHERD_MOCK=1 make dashboard` for the stub
- Fresh-clone test: add `scripts/fresh_clone_smoke.sh` that runs in a clean `$(mktemp -d)` and asserts pass; optionally wire into CI as a separate job
- `make_world()` backward-compat: keep positional `config_path` optional but NOT required; existing callers pass explicitly and should keep working

</specifics>

<deferred>
## Deferred Ideas

- Docker-based quickstart (`docker compose up`) — nice-to-have, not in scope
- Windows-compatible fresh-clone — out of scope, the hackathon runs on Linux/macOS judges
- Version lock / reproducible build beyond `uv sync` — scope creep

</deferred>
