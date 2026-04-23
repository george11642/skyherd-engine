# Phase 6: SITL-CI & Determinism Gate - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

CI proves the SITL MAVLink path works end-to-end in under 2 minutes using a pre-built Docker image, and the deterministic-replay guarantee is strengthened to hash-stable across three back-to-back runs — with the full 8-scenario suite as the final zero-regression gate. This is the milestone's closing gate.

Requirements: BLD-04, SCEN-03, SCEN-02 (milestone-wide criterion verified here).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices at Claude's discretion — discuss skipped per `workflow.skip_discuss=true`.

### Known Constraints from Audit
- SITL path is REAL code (`src/skyherd/drone/sitl.py` uses real MAVSDK-Python calls) but UNTESTED IN CI — `make sitl-up` needs Docker + 25-40 min first build from source; pre-built `SITL_IMAGE=ardupilot/ardupilot-sitl:Copter-4.5.7` is the fix
- Single smoke scenario must prove: MAVLink connect → mission upload → arm → takeoff → RTL, all in under 2 minutes
- SITL CI job MUST be isolated (continue-on-error or separate job) so Docker infra flakiness doesn't mask real scenario/test regressions
- Deterministic replay today uses timestamp sanitization before hashing (scenarios are deterministic in event count + tool-call structure but not byte-identical at JSONL level pre-sanitization). This phase strengthens the test: three back-to-back `make sim SEED=42` runs produce hash-identical sanitized output
- Zero-regression gate: all 8 scenarios PASS `make demo SEED=42 SCENARIO=all` after every prior phase landed — including any new scenarios added (e.g. any Phase 5 sick-cow vet-intake assertions)
- Phase 6 must not interfere with Phase 4's Makefile changes; coordinate via explicit file-ownership in PLAN frontmatter

</decisions>

<code_context>
## Existing Code Insights

Scoped files:
- `docker-compose.sitl.yml` — SITL container spec
- `src/skyherd/drone/sitl.py` — real MAVSDK backend (needs SITL container running)
- `src/skyherd/drone/sitl_emulator.py` — 742-line pure-Python in-process emulator (used when Docker not available)
- `tests/drone/` — existing drone tests (skip cleanly when Docker absent)
- `.github/workflows/ci.yml` (or similar) — CI config; add SITL smoke job
- `Makefile` — `make sitl-up`, `make sitl-smoke` targets
- `tests/test_determinism_e2e.py` — existing `test_demo_seed42_is_deterministic` (sanitizes timestamps)
- `src/skyherd/scenarios/base.py` — replay JSONL emission site
- `CLAUDE.md` Gate re-audit reference — all 10 Gate items retro-verified GREEN here

</code_context>

<specifics>
## Specific Ideas

- CI Docker strategy: `docker pull ardupilot/ardupilot-sitl:Copter-4.5.7` (cached across CI runs via GH Actions cache) — keeps under 2 min target
- SITL smoke scenario: a dedicated minimal flight script in `scripts/sitl_smoke.py` that exits 0 on success, non-zero on failure
- Determinism test: parameterize existing `test_demo_seed42_is_deterministic` to run 3 iterations; assert sanitized JSONL hash equality across all runs
- Gate retro-verification: add a `make gate-check` target that runs the 8-scenario suite + determinism + SITL smoke (if Docker available else skip cleanly) and prints a GREEN/YELLOW/RED table per Gate item
- CI job isolation: put SITL smoke in its own job with `continue-on-error: false` but separate from the main scenario+test job so failure is visible but doesn't block

</specifics>

<deferred>
## Deferred Ideas

- Multi-platform SITL (ArduCopter + ArduPlane + ArduSub) — overkill; Copter is the only SkyHerd target
- Full hardware-in-loop CI with real rotors — Hardware Tier H3 milestone
- Determinism at wall-clock timestamp level (not just sanitized) — scope creep; real timestamps are externally unreachable

</deferred>
