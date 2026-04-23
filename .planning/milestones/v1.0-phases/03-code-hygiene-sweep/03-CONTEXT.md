# Phase 3: Code Hygiene Sweep - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

All silent-except blocks replaced with logged warnings; Twilio auth env var standardized; cost.py billing logic fully tested; ruff + pyright run clean; project coverage holds ≥87%. Pure hygiene — no new feature, no behavior change, just making the existing code honest.

Requirements: HYG-01, HYG-02, HYG-03, HYG-04, HYG-05.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices at Claude's discretion — discuss skipped per `workflow.skip_discuss=true`.

### Known Constraints from Audit
- 15+ silent `except: pass` sites listed at `.planning/codebase/CONCERNS.md §3` — each MUST convert to `except Exception as exc: logger.warning(...)` with meaningful message
- Twilio: `TWILIO_TOKEN` in `src/skyherd/voice/call.py:44,68` vs `TWILIO_AUTH_TOKEN` in `src/skyherd/mcp/rancher_mcp.py` — standardize on `TWILIO_AUTH_TOKEN`, emit deprecation warning if legacy `TWILIO_TOKEN` is set, update `.env.example`
- `src/skyherd/agents/cost.py` at 78% — raise to ≥90% with idle-pause + active-delta + `all_idle` aggregation tests
- 15 pyright errors confined to `src/skyherd/drone/pymavlink_backend.py` and `src/skyherd/drone/sitl_emulator.py` — fix or add typed-ignore with rationale comment
- 1 trivial ruff error (unsorted import, auto-fixable)
- Coverage gate ≥80% must hold; actual project ≥87% preserved

</decisions>

<code_context>
## Existing Code Insights

Scoped files from `.planning/codebase/CONCERNS.md`:
- `src/skyherd/sensors/acoustic.py:72,82`
- `src/skyherd/sensors/bus.py:201,269`
- `src/skyherd/sensors/trough_cam.py:94`
- `src/skyherd/agents/mesh.py:163,170`
- `src/skyherd/agents/fenceline_dispatcher.py:153`
- `src/skyherd/scenarios/base.py:312` (note: Phase 1 also touches base.py — coordinate ordering)
- `src/skyherd/server/events.py:299,315`
- `src/skyherd/drone/f3_inav.py:370,377,386,393,400`
- `src/skyherd/drone/sitl_emulator.py:445,466,742`
- `src/skyherd/voice/tts.py:195`
- `src/skyherd/edge/watcher.py:111,238,323,454,480`

- `src/skyherd/voice/call.py:44,68` — Twilio env var fix site
- `src/skyherd/mcp/rancher_mcp.py` — reference for `TWILIO_AUTH_TOKEN`
- `.env.example` — env var doc
- `src/skyherd/agents/cost.py` — idle-pause tests site
- `tests/` — add new cost.py tests alongside existing patterns
- `pyproject.toml` — ruff + pyright + coverage config

</code_context>

<specifics>
## Specific Ideas

- Logger setup: use the module-level logger pattern already established in the codebase (grep for `logging.getLogger(__name__)` to match convention)
- Test parallelism: Phase 3 touches `scenarios/base.py:312` which Phase 1 owns — plan Phase 3 to DEFER that one site until Phase 1 lands OR carefully coordinate via explicit line-range claim
- Coverage discipline: every new logger.warning site should have a test exercising the error path
- Pyright fixes: prefer real type annotations over `# type: ignore` unless the error is genuinely from the upstream library

</specifics>

<deferred>
## Deferred Ideas

- Introducing structured logging (JSON logs) — scope creep; keep `.warning()` strings for now
- Full type coverage beyond the 15 drone errors — out of scope
- Replacing pytest with something else — no, keep pytest

</deferred>
