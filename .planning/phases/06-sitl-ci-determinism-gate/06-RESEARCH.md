# Phase 6: SITL-CI & Determinism Gate — Research

**Researched:** 2026-04-22
**Domain:** CI-integrated SITL smoke testing + deterministic replay hardening + retroactive Gate audit
**Confidence:** HIGH (local code context), MEDIUM (Docker Hub image availability — see critical correction below), HIGH (CI patterns, pytest determinism)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
All implementation choices at Claude's discretion — discuss skipped per `workflow.skip_discuss=true`. Known constraints from audit that nevertheless function as locked:

- SITL path is REAL code (`src/skyherd/drone/sitl.py` uses real MAVSDK-Python calls) but UNTESTED IN CI. `make sitl-up` currently needs Docker + 25–40 min first build from source. Pre-built image intended as the fix.
- Single smoke scenario must prove: MAVLink connect → mission upload → arm → takeoff → RTL, all in under 2 minutes.
- SITL CI job MUST be isolated (continue-on-error or separate job) so Docker infra flakiness doesn't mask real scenario/test regressions.
- Deterministic replay today uses timestamp sanitization before hashing (scenarios are deterministic in event count + tool-call structure but not byte-identical at JSONL level pre-sanitization). This phase strengthens the test: three back-to-back `make sim SEED=42` runs produce hash-identical sanitized output.
- Zero-regression gate: all 8 scenarios PASS `make demo SEED=42 SCENARIO=all` after every prior phase landed — including any new scenarios added (e.g. any Phase 5 sick-cow vet-intake assertions).
- Phase 6 must not interfere with Phase 4's Makefile changes; coordinate via explicit file-ownership in PLAN frontmatter.

### Claude's Discretion
All implementation choices at Claude's discretion.

### Deferred Ideas (OUT OF SCOPE)
- Multi-platform SITL (ArduCopter + ArduPlane + ArduSub) — overkill; Copter is the only SkyHerd target.
- Full hardware-in-loop CI with real rotors — Hardware Tier H3 milestone.
- Determinism at wall-clock timestamp level (not just sanitized) — scope creep; real timestamps are externally unreachable.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BLD-04 | SITL smoke test added to CI using pre-built image; single smoke scenario proves real MAVLink mission upload + arm + takeoff + RTL in under 2 minutes. | See §§ "SITL Docker Image Reality", "SITL Smoke Script", "CI Job Layout". Resolves SITL being technically real but untested in CI per `CONCERNS.md §6 Priority 4`. |
| SCEN-03 | Deterministic replay strengthened — scenario JSONL output byte-identical at hash level after timestamp sanitization; `make sim SEED=42` verified stable across three back-to-back runs. | See § "Determinism Strengthening". Existing `tests/test_determinism_e2e.py` already runs two seed=42 invocations and compares sanitized MD5. Phase 6 lifts that to N=3 (parametrized or reference-hash comparison). |
| SCEN-02 | All 8 scenarios pass `make demo SEED=42 SCENARIO=all` after all other changes. Zero regression. Milestone-wide criterion VERIFIED in Phase 6. | See § "Zero-Regression Gate". `make gate-check` + retro-audit of CLAUDE.md 10 Gate items closes this out. |
</phase_requirements>

## Summary

Phase 6 closes the milestone by producing (a) a CI job that actually executes a real MAVLink mission against a running ArduPilot binary, (b) a stronger determinism guarantee than today's 2-run sanitized comparison, and (c) a one-shot gate-check that confirms none of Phases 1–5 broke the 8-scenario suite and retroactively re-audits CLAUDE.md's 10 Gate items.

The single most important research finding: **the image name in CONTEXT.md (`ardupilot/ardupilot-sitl:Copter-4.5.7`) does NOT exist on Docker Hub**. `hub.docker.com/v2/repositories/ardupilot/ardupilot-sitl/` returns `{"message":"object not found"}`. The only community image that exists for SITL is `radarku/ardupilot-sitl` (SHA-based tags, last semantic release from 2021, no `Copter-4.5` tag at all). This means the "FAST PATH" comment at the top of `docker-compose.sitl.yml` is aspirational, not verified. The planner must decide between three reality-aligned paths: (1) build the image in CI once, push to GHCR under the SkyHerd org, and cache-pull from there on subsequent runs; (2) build in CI with Buildx GHA cache (first run 25–40 min, subsequent cached builds ~3 min); (3) skip Docker entirely in CI and rely on the existing 742-line `sitl_emulator.py` + `PymavlinkBackend` path which already proves real MAVLink wire traffic — this is the fast, reliable, already-working option.

Secondary finding: the repo already has a **pure-Python in-process MAVLink emulator** (`sitl_emulator.py`) that speaks MAVLink 2.0 over UDP — this is NOT a stub; it is a real emulator with CRC-correct wire framing for HEARTBEAT / SYS_STATUS / GPS_RAW_INT / GLOBAL_POSITION_INT / HOME_POSITION / EKF_STATUS_REPORT / mission upload / COMMAND_ACK. Combined with `PymavlinkBackend`, it passes 6 real MAVLink e2e tests (`tests/drone/test_sitl_e2e.py` — currently skipped behind `SITL_EMULATOR=1`). The fastest path to a "SITL CI in <2 min" that actually proves the wire protocol is to simply **flip the existing emulator-mode CI job from `workflow_dispatch` to `push/pull_request`** — zero Docker needed.

Tertiary: the determinism test already exists, sanitizes correctly, and passes. Phase 6 effort here is small — parameterize for N=3 and decide whether to commit a reference hash.

**Primary recommendation:** Promote the existing emulator-mode SITL job (`sitl-e2e` in `.github/workflows/ci.yml`) from `workflow_dispatch`-only to `push + pull_request`, add a reference-hash determinism variant to `test_determinism_e2e.py`, and add one `make gate-check` Makefile target that prints a GREEN/YELLOW/RED table aligned to CLAUDE.md's 10 Gate items. Only pursue a Docker-based CI path if the emulator path is deemed insufficient — and if so, use `docker/build-push-action@v5` with GHA cache (`cache-from: type=gha`, `cache-to: type=gha,mode=max`) against `docker/sitl.Dockerfile` which already has ccache wiring. Do NOT rely on `ardupilot/ardupilot-sitl:Copter-4.5.7` — it is not a real image.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SITL MAVLink wire exchange | Pure-Python emulator (in-process) | Docker container (optional escalation) | Emulator already exists, is deterministic, runs in ~5s; Docker adds 60–120s + infra flakiness for identical protocol coverage |
| CI orchestration | GitHub Actions workflows | `make` targets | CI is the authoritative runner; `make` targets are the local-parity mirror |
| Determinism verification | `pytest` + `hashlib` + `subprocess` | `make` wrapper | Python test harness already sanitizes + MD5s; Phase 6 extends to N=3 |
| Zero-regression suite | `make demo SEED=42 SCENARIO=all` | CI matrix | Entry point is the demo CLI; verified by scenario assertions + exit code |
| Gate retro-audit | `make gate-check` + `scripts/gate_check.py` | Manual (docs/verify-latest.md) | Phase 6 needs one command that prints a clean pass/fail table so the phase can be stamped complete |
| Pre-built Docker image hosting | GHCR (GitHub Container Registry) | Docker Hub | GHCR is free for public repos + integrated with GITHUB_TOKEN; Docker Hub has rate limits on unauthenticated pulls |

## Standard Stack

### Core (already in repo)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | ≥8 | Test runner | Already used; `asyncio_mode=auto`; parametrize is native |
| pytest-asyncio | ≥0.24 | Async test support | Already used for all async drone tests |
| pymavlink | (unpinned, latest) | MAVLink wire framing for real CI path | `PymavlinkBackend` + `MavlinkSitlEmulator` already built on it |
| mavsdk | ≥3,<4 | MAVSDK-Python for `SitlBackend` — Docker path only | Used if Docker CI path chosen; sub-binary `mavsdk_server` started by client |
| typer | ≥0.12 | CLI framework for `skyherd-sitl-e2e` | Already used repo-wide |

### Supporting (to introduce)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| docker/setup-buildx-action | v3 | Enable Buildx + GHA cache on CI runner | If building `docker/sitl.Dockerfile` in CI |
| docker/build-push-action | v5 | Build + optionally push + cache layers via GHA backend | Only if Docker SITL path chosen |
| ScribeMD/docker-cache | 0.5.0 (pinned) | Cache pulled images via `docker save`/`load` | Fallback if GHCR push not desired; ~30s saved on 1.3GB image [CITED: marketplace description] |
| GHCR (ghcr.io) | — | Free container registry for public repos | If we build + push the SITL image once per Copter tag change |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Buildx GHA cache on `docker/sitl.Dockerfile` | Pre-push built image to GHCR + `docker pull` in CI | GHCR path is simpler to reason about and decouples CI flakiness from ArduPilot submodule fetch; requires one-time image build + push (manual or workflow_dispatch) |
| Docker SITL at all | Emulator-only path (existing) | Emulator already proves wire traffic; Docker adds 60–120s to CI for zero additional protocol coverage — but Docker exercises real ArduPilot firmware logic (EKF, flight modes), which the emulator fakes |
| Parametrized 3-run determinism test | Single test that loops 3× internally | Parametrize gives 3 separate test IDs in CI output; loop is simpler and shares a single MD5 reference. Loop is more honest: failure aborts on first mismatch |
| `make gate-check` shell target | Python script (`scripts/gate_check.py`) | Python script can parse pytest output, coverage %, and emit structured table; Makefile target calls the script. Both are needed. |

**Installation (if Docker CI path chosen):** No new Python deps. Add to CI workflow only:
```yaml
- uses: docker/setup-buildx-action@v3
- uses: docker/build-push-action@v5
  with:
    context: .
    file: docker/sitl.Dockerfile
    cache-from: type=gha
    cache-to: type=gha,mode=max
    load: true
    tags: skyherd-sitl:ci
```

**Version verification:**
```bash
# Checked 2026-04-22 against actual Docker Hub API
curl -sL "https://hub.docker.com/v2/repositories/ardupilot/ardupilot-sitl/" | jq -r .message
# → "object not found"  [VERIFIED: 2026-04-22 against hub.docker.com API]
```

## Architecture Patterns

### System Architecture Diagram

```
                 ┌──────────────────────────────────────────────────┐
                 │           GitHub Actions CI Pipeline             │
                 └──────────────────────────────────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              ▼                          ▼                          ▼
     ┌─────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
     │  main-ci (fast) │    │ sitl-smoke (<2 min)  │    │  determinism (slow)  │
     │  lint+type+test │    │ SITL MAVLink proof   │    │  3× seed=42 hash eq  │
     │  ~2 min         │    │                      │    │  ~6 min (3 runs)     │
     └─────────────────┘    └──────────────────────┘    └──────────────────────┘
              │                          │                          │
              ▼                          ▼                          ▼
     demo SEED=42 SCENARIO=all    skyherd-sitl-e2e --emulator   subprocess.run x3
     ↓ exit 0 required            (pymavlink path, no Docker)    ↓ sanitize + md5
     all 8 scenarios PASS          OR                             ↓ assert equal
                                  docker compose up sitl
                                   → skyherd-sitl-e2e (docker)
              │                          │                          │
              └──────────────────────────┴──────────────────────────┘
                                         ▼
                            ┌──────────────────────┐
                            │  Gate Retro-Audit    │
                            │  make gate-check     │
                            │  → 10 Gate items     │
                            │  → GREEN/YELLOW/RED  │
                            │  → exit 0 iff GREEN  │
                            └──────────────────────┘
```

**Data flow (SITL smoke, emulator path — recommended):**
1. CI runner starts Python 3.12 + uv sync.
2. `skyherd-sitl-e2e --emulator` invoked via subprocess.
3. `MavlinkSitlEmulator` binds UDP vehicle socket on ephemeral port; proactively sends HEARTBEAT + GPS_RAW_INT + HOME_POSITION + EKF_STATUS_REPORT to `gcs_port=14540`.
4. `PymavlinkBackend` connects as GCS listener on 14540, receives heartbeats, passes health check.
5. Backend issues MAV_CMD_COMPONENT_ARM_DISARM → MAV_CMD_NAV_TAKEOFF → mission upload (3 waypoints) → MISSION_START → wait for MISSION_ITEM_REACHED × 3 → MAV_CMD_NAV_RETURN_TO_LAUNCH → disarm.
6. Emulator responds with correct COMMAND_ACK / MISSION_REQUEST / MISSION_ACK / MISSION_ITEM_REACHED frames.
7. Backend writes `runtime/drone_events.jsonl` with CONNECTED / TAKEOFF / PATROL / THERMAL / RTL events.
8. CLI exits 0; CI job asserts expected events in captured stdout.
9. Total wall time: ~5–10 seconds (emulator path), ~60–120 seconds (Docker path).

### Recommended Project Structure

```
skyherd-engine/
├── .github/workflows/
│   ├── ci.yml                     # EXISTING — add/promote sitl-smoke job
│   └── sitl-image-publish.yml     # NEW (optional) — build+push SITL to GHCR on tag
├── docker/
│   ├── sitl.Dockerfile            # EXISTING — used if Docker CI path chosen
│   └── sitl-entrypoint.sh         # EXISTING
├── docker-compose.sitl.yml        # EXISTING — update comment block re: image
├── scripts/
│   ├── sitl_smoke.py              # NEW — wrapper around `skyherd-sitl-e2e --emulator`
│   │                              #       parses evidence events, exits 0/1
│   └── gate_check.py              # NEW — runs demo + determinism + SITL smoke,
│                                  #       prints GREEN/YELLOW/RED Gate table
├── tests/
│   └── test_determinism_e2e.py    # EXISTING — extend to N=3 runs
└── Makefile                       # EXISTING — Phase 4 owns make_world/dashboard;
                                   # Phase 6 OWNS: sitl-smoke, gate-check, determinism-3x
```

### Pattern 1: Emulator-Mode SITL CI (Recommended Primary Path)

**What:** Run the existing `test_sitl_e2e.py` emulator tests on every push/PR, not only `workflow_dispatch`.
**When to use:** Always for Phase 6. This is the lowest-risk path that actually delivers BLD-04.
**Example:**
```yaml
# .github/workflows/ci.yml — NEW section (or promote existing)
sitl-smoke:
  name: SITL smoke (emulator, <2 min)
  runs-on: ubuntu-latest
  # REMOVE: if: github.event_name == 'workflow_dispatch'
  timeout-minutes: 5

  steps:
    - uses: actions/checkout@v4
    - uses: astral-sh/setup-uv@v5
      with:
        python-version: "3.12"
    - name: Install dependencies
      run: uv sync --all-extras
    - name: Run SITL E2E (emulator)
      run: |
        uv run skyherd-sitl-e2e --emulator --takeoff-alt 15.0
    - name: Run SITL E2E pytest suite
      run: SITL_EMULATOR=1 uv run pytest tests/drone/test_sitl_e2e.py -v --timeout=120
```
Evidence events asserted (already produced by `e2e.py`): `CONNECTED`, `TAKEOFF OK`, `PATROL OK`, `RTL OK`, `E2E PASS`. Fail loudly if any are missing. [VERIFIED: `src/skyherd/drone/e2e.py` lines 130–164]

### Pattern 2: Docker-Mode SITL CI (Optional Escalation Path)

**What:** Build `docker/sitl.Dockerfile` with Buildx + GHA cache, start the container, run `skyherd-sitl-e2e` against it.
**When to use:** If a reviewer argues the emulator "isn't real SITL" — the Dockerfile-built image runs actual ArduCopter firmware, so this is the strictest proof.
**Cost:** First CI run 25–40 min; warm cache ~3–5 min (well over the 2-min budget).
**Example:**
```yaml
docker-sitl-smoke:
  name: Docker SITL smoke
  runs-on: ubuntu-latest
  timeout-minutes: 15
  continue-on-error: true  # isolate from main CI signal

  steps:
    - uses: actions/checkout@v4
    - uses: docker/setup-buildx-action@v3
    - uses: docker/build-push-action@v5
      with:
        context: .
        file: docker/sitl.Dockerfile
        tags: skyherd-sitl:ci
        load: true
        cache-from: type=gha
        cache-to: type=gha,mode=max
        build-args: |
          ARDUPILOT_TAG=Copter-4.5.7
    - name: Start SITL compose stack
      run: SITL_IMAGE=skyherd-sitl:ci docker compose -f docker-compose.sitl.yml up -d
    - name: Wait for SITL MAVLink port
      run: timeout 90 bash -c 'until nc -u -z 127.0.0.1 14540; do sleep 2; done'
    - uses: astral-sh/setup-uv@v5
    - run: uv sync --all-extras
    - run: uv run skyherd-sitl-e2e --port 14540
```
[CITED: docs.docker.com/build/cache/backends/gha — official Docker GHA cache backend docs]

### Pattern 3: N=3 Determinism Strengthening

**What:** Extend `test_demo_seed42_is_deterministic` to run seed=42 three times and assert all three sanitized MD5s are identical. Optionally commit a reference hash for a full 4-way comparison against a frozen known-good output.
**When to use:** SCEN-03 requires exactly this.
**Example:**
```python
# tests/test_determinism_e2e.py — REPLACE existing test
@pytest.mark.slow
def test_demo_seed42_is_deterministic_3x() -> None:
    """Three back-to-back seed=42 runs must produce identical sanitized output."""
    runs = [_sanitize(_run_demo(42)) for _ in range(3)]
    hashes = [_md5(r) for r in runs]

    assert hashes[0] == hashes[1] == hashes[2], (
        f"Determinism check failed — sanitized md5s differ across 3 runs:\n"
        f"  run_0: {hashes[0]}\n"
        f"  run_1: {hashes[1]}\n"
        f"  run_2: {hashes[2]}\n"
    )
```
Alternative with parametrize (not recommended — sequential stateful comparison, parametrize fights the semantics):
```python
@pytest.mark.parametrize("run_idx", range(3))
def test_determinism_run(run_idx, reference_hash_fixture): ...
```
The in-body loop is honest about the semantics; parametrize would produce 3 separate test functions each missing the cross-run assertion.

### Pattern 4: `make gate-check` Gate Retro-Audit

**What:** One-shot verifier that runs everything Phase 6 owns, prints a table aligned to CLAUDE.md's 10 Gate items, exits 0 iff all GREEN.
**Example:**
```python
# scripts/gate_check.py
"""Retro-audit CLAUDE.md's 10 Sim Completeness Gate items.

Exits 0 if all 10 are GREEN.  Prints a GREEN/YELLOW/RED table to stdout.
Consumed by `make gate-check` and by Phase 6 acceptance.
"""
GATE_ITEMS = [
    ("agents_mesh",      "5 Managed Agents on shared MQTT",        _check_agents_mesh),
    ("sensors",          "7+ sim sensors emitting",                _check_sensors),
    ("vision_heads",     "Disease heads on synthetic frames",      _check_vision_heads),
    ("sitl_mission",     "ArduPilot SITL MAVLink mission",         _check_sitl_emulator),
    ("dashboard",        "Map + lanes + cost + attest + PWA",      _check_dashboard_build),
    ("voice",            "Wes voice chain wired end-to-end",       _check_voice_chain),
    ("scenarios",        "All 8 scenarios back-to-back",           _check_scenarios),
    ("determinism",      "seed=42 replay stable across 3 runs",    _check_determinism),
    ("fresh_clone",      "make sim boots on fresh clone",          _check_fresh_clone_doc),
    ("cost_idle",        "Cost ticker pauses during idle",         _check_cost_idle),
]
# Each _check_* returns ("GREEN" | "YELLOW" | "RED", evidence_str).
```
```makefile
gate-check:
	@uv run python scripts/gate_check.py
```

### Anti-Patterns to Avoid

- **Pinning to `ardupilot/ardupilot-sitl:Copter-4.5.7` without verifying.** This image is not on Docker Hub. A CI job that `docker pull`s it will fail silently or with a 404. If Docker path chosen, either (a) build `docker/sitl.Dockerfile` in CI, or (b) build once and push to GHCR.
- **Using `pytest.mark.parametrize` for cross-run identity.** Each parametrize invocation is an independent test; they can't easily share a comparison. Use an in-body loop.
- **Letting SITL CI failures block the main CI signal.** Docker infra is flaky; if `docker-sitl-smoke` job gates merges, unrelated network hiccups break PRs. Use `continue-on-error: true` on the Docker job; keep the emulator job strict.
- **Duplicating Makefile target ownership between Phase 4 and Phase 6.** Phase 4 owns `make_world` resolution + `make dashboard` live-mode. Phase 6 owns `make sitl-smoke`, `make gate-check`, `make determinism-3x`. The PLAN frontmatter MUST list exact targets added/modified.
- **Hashing un-sanitized scenario output.** Wall-clock ISO timestamps, UUIDs, and session-hash IDs change every run. The existing `DETERMINISM_SANITIZE` list is correct — reuse it, don't re-invent.
- **Running the 8-scenario suite without exit-code check.** `skyherd-demo play all` prints PASS/FAIL per scenario; the CI MUST assert the CLI exit code is 0 (meaning all 8 passed), not just grep for "PASS" in stdout.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MAVLink wire framing for tests | Custom MAVLink encoder | `pymavlink` library (or existing `sitl_emulator.py`) | CRC, packet lengths, crc_extra tables are error-prone; `sitl_emulator.py` already got it right for 12 message types |
| Docker image layer caching in CI | `docker save` → actions/cache round-trip | `docker/build-push-action@v5` with `cache-to: type=gha` | Native Buildx GHA cache is 3× faster than save/load [CITED: dev.to/dtinth research] |
| Deterministic output sanitization | Custom regex per test | Reuse `DETERMINISM_SANITIZE` list from `test_determinism_e2e.py` | Already covers ISO timestamps, UUIDs, HH:MM:SS, session-XXXXXXXX |
| "Run the whole gate" wrapper | Shell script with nested if/fi | Python `scripts/gate_check.py` | Python has structured output, subprocess capture, coverage integration, and is what the project standardizes on |
| Starting + waiting-on SITL container | Hand-coded `docker run` + `sleep` | `docker compose -f docker-compose.sitl.yml up -d` + `timeout 90 bash -c 'until nc -u -z 127.0.0.1 14540'` | Compose file already has healthcheck; reuse |
| `ardupilot/ardupilot-sitl:Copter-4.5.7` pull-based path | Don't write CI steps that expect this image to exist | Use the in-repo Dockerfile or emulator path | Image does not exist on Docker Hub [VERIFIED: 2026-04-22] |

**Key insight:** The SITL domain is a well-populated minefield of "looks easy, actually isn't." The repo has already paid the complexity cost by shipping `sitl_emulator.py` (742 lines, real MAVLink 2.0 framing, CRC-correct). Phase 6's job is to **activate** that existing work in CI — not to invent a new SITL story. Resist any urge to "write a simpler SITL smoke script"; `scripts/sitl_smoke.py` should be a 30-line wrapper that invokes `skyherd-sitl-e2e --emulator` and parses evidence events, nothing more.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `runtime/drone_events.jsonl` (ephemeral, created by SITL backends); `runtime/scenario_runs/*.jsonl` (per-run replay logs — grows every invocation); `docs/REPLAY_LOG.md` (appended every run, grows unbounded) | Phase 6 writes to these; no rename/migration needed. `runtime/` is in `.gitignore`. |
| Live service config | None. No long-lived services touched by Phase 6. | None. |
| OS-registered state | None. No pm2 / systemd / launchd / task scheduler registrations. | None. |
| Secrets/env vars | `ANTHROPIC_API_KEY` (optional — scenarios run without it), `SITL_IMAGE` (optional — Docker override), `SITL_EMULATOR` (env flag for pytest skip), `SITL` (env flag for real-Docker pytest skip) | None — existing names reused. Document `SITL_IMAGE` and `SITL_EMULATOR` in Makefile comments. |
| Build artifacts / installed packages | `skyherd-sitl-e2e` entry point (pyproject.toml scripts) — already installed via `uv sync`; `docker/sitl.Dockerfile` produces `skyherd-sitl:local` or `skyherd-sitl:ci` local image tag | None. |

**Canonical question answer:** After Phase 6 lands, the only runtime state is `runtime/scenario_runs/` growth (expected, gitignored) and GH Actions cache entries under the `type=gha` namespace (managed by GHA, cleared automatically after 7 days of no access). Nothing sticky.

## Common Pitfalls

### Pitfall 1: `ardupilot/ardupilot-sitl:Copter-4.5.7` Mirage
**What goes wrong:** Plan writes `docker pull ardupilot/ardupilot-sitl:Copter-4.5.7` into CI; CI fails with `manifest unknown` because the image was never published.
**Why it happens:** Comment in `docker-compose.sitl.yml` lines 3–5 suggests it exists: "Set SITL_IMAGE=ardupilot/ardupilot-sitl:Copter-4.5.7 ... to skip the ~30 min source build". This is aspirational documentation, not a verified fact. CONTEXT.md inherited the same assumption.
**How to avoid:** The plan MUST NOT bake that image reference into CI. Three valid paths: (1) emulator-only (fastest, recommended); (2) build Dockerfile in CI with GHA cache; (3) one-time GHCR push workflow that publishes `ghcr.io/george11642/skyherd-sitl:copter-4.5.7` and CI pulls from there.
**Warning signs:** Any plan task that reads "Pull pre-built SITL image" without specifying the registry or providing the publish path.

### Pitfall 2: GitHub Actions `runs-on: ubuntu-latest` Lacks `docker compose` — Sometimes
**What goes wrong:** Modern GH-hosted runners ship `docker compose` (v2) built in, but older runners or certain self-hosted runners may only have `docker-compose` (v1 with hyphen).
**Why it happens:** `docker compose` vs `docker-compose` confusion.
**How to avoid:** Use `docker compose` (space) — GH-hosted `ubuntu-latest` has had this since 2022. Pin `runs-on: ubuntu-latest` (actions/runner-images 20240101+). [CITED: github/docs — ubuntu-latest runner image]
**Warning signs:** `command not found: docker-compose` in CI logs.

### Pitfall 3: Emulator Port Collision in Parallel CI Jobs
**What goes wrong:** `MavlinkSitlEmulator` defaults to UDP 14540. If two pytest workers / CI matrix entries run simultaneously, they fight for the port.
**Why it happens:** `test_sitl_e2e.py` already handles this via `_BASE_PORT = 14560` + offset-per-test. The top-level `skyherd-sitl-e2e --emulator` CLI uses 14540 by default.
**How to avoid:** In CI, pass `--port` with a distinct offset per job, or restrict the SITL smoke job to one runner and don't run it in the main matrix. The existing CI already isolates it in its own job.
**Warning signs:** `OSError: [Errno 98] Address already in use` in test output.

### Pitfall 4: `make sim` vs `make demo` — Same SEED, Different Commands
**What goes wrong:** REQUIREMENTS.md SCEN-03 says "make sim SEED=42 verified stable". But `make sim` runs `skyherd.world.cli` (world-only 300s simulation, no scenarios), while `make demo` runs `skyherd-demo play all` (all 8 scenarios, ~3s each).
**Why it happens:** Historical Makefile split — `sim` is the raw world loop; `demo` is the scenario orchestrator. The determinism test `test_demo_seed42_is_deterministic` uses `skyherd-demo` (the scenario path) which is what needs to be hash-stable.
**How to avoid:** Plan must clarify in task descriptions that SCEN-03 is verified via `skyherd-demo play all` (what the existing determinism test already exercises), not `make sim`. Update REQUIREMENTS.md wording during Phase 6 if needed, or leave REQUIREMENTS.md alone and just interpret correctly.
**Warning signs:** Test failures where `make sim` output varies (world step wall-times) while `make demo` output is stable.

### Pitfall 5: Floating-Point Determinism Across Python Versions
**What goes wrong:** Seed-driven RNG is deterministic, but downstream floating-point math (e.g. geodesic calcs, disease score aggregation) may produce 1-bit differences on different CPU / libm / Python patch versions, breaking the 3-run hash.
**Why it happens:** `numpy.random` is deterministic per-seed; `math.sin/cos` isn't guaranteed identical across libm versions; Python's FP formatting is stable for floats but not for repr of large dicts.
**How to avoid:** The existing sanitizer already strips the volatile fields (wall timestamps, session hashes). If new YELLOW determinism failures surface, expand `DETERMINISM_SANITIZE` rather than chasing FP equality. The 3-run test is on a single machine in one CI job, so libm/Python are fixed — cross-version drift is a risk only if we add cross-Python matrix coverage, which we should NOT.
**Warning signs:** 3-run test passes locally, fails on CI; passes on Python 3.11, fails on 3.12.

### Pitfall 6: `continue-on-error` Hides Real SITL Regressions
**What goes wrong:** Setting `continue-on-error: true` on the SITL job means if the MAVLink handshake breaks genuinely, the main CI stays green and we don't notice.
**Why it happens:** Desire to isolate Docker flakiness → accidentally hides protocol regressions.
**How to avoid:** Emulator-mode job → NO `continue-on-error` (it's deterministic, must be green). Docker-mode job (if added) → `continue-on-error: true` is acceptable because Docker is flaky; but add a separate `required` check that looks at ONLY the emulator job's status.
**Warning signs:** Green CI checkmark with a red "docker-sitl-smoke" sub-job nobody reviews.

## Code Examples

### Example 1: Minimal MAVSDK takeoff/RTL sequence (reference only — repo already has `SitlBackend`)

```python
# Source: https://github.com/mavlink/MAVSDK-Python/blob/main/examples/takeoff_and_land.py
# [CITED: MAVSDK-Python official examples, 2026-04-22]
import asyncio
from mavsdk import System

async def run():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")

    async for state in drone.core.connection_state():
        if state.is_connected:
            break

    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            break

    await drone.action.arm()
    await drone.action.takeoff()
    await asyncio.sleep(10)  # hold altitude
    await drone.action.return_to_launch()

    async for in_air in drone.telemetry.in_air():
        if not in_air:
            break
    await drone.action.disarm()
```
**Note:** The `mavsdk` package auto-launches `mavsdk_server` (a Go binary) as a subprocess. On CI runners without Docker this is fine; with Docker SITL it connects via UDP 14540. The repo's `SitlBackend` at `src/skyherd/drone/sitl.py` already implements this pattern with per-operation timeouts — Phase 6 does NOT need to write new MAVSDK code.

### Example 2: Emulator-path smoke CLI (what Phase 6 ships)

```bash
# Exit 0 on success, non-zero on any MAVLink handshake failure
uv run skyherd-sitl-e2e --emulator --takeoff-alt 15.0 --port 14540

# Expected stdout evidence events (already implemented in src/skyherd/drone/e2e.py):
#   CONNECTED
#   TAKEOFF OK
#   PATROL OK
#   THERMAL CLIP: runtime/thermal/<ts>.png
#   RTL OK
#   E2E PASS
```
[VERIFIED: `src/skyherd/drone/e2e.py` lines 130–177]

### Example 3: 3-run determinism test

```python
# tests/test_determinism_e2e.py — REPLACE the existing single test
@pytest.mark.slow
def test_demo_seed42_is_deterministic_3x() -> None:
    """Three back-to-back seed=42 runs must produce identical sanitized output.
    SCEN-03: hash-stable across 3 runs."""
    hashes: list[str] = []
    for i in range(3):
        sanitized = _sanitize(_run_demo(42))
        hashes.append(_md5(sanitized))

    assert len(set(hashes)) == 1, (
        f"Determinism check failed across 3 runs:\n"
        f"  run_0: {hashes[0]}\n"
        f"  run_1: {hashes[1]}\n"
        f"  run_2: {hashes[2]}\n"
        "All three sanitized md5s must match."
    )
```

### Example 4: Gate-check structured output

```
$ make gate-check
SkyHerd Sim Completeness Gate — Retro-Audit
==============================================
[GREEN]   agents_mesh       5 Managed Agents on shared MQTT      (post-Phase 1: sessions reused, 5/5)
[GREEN]   sensors           7+ sim sensors emitting              (7 emitters registered)
[GREEN]   vision_heads      Disease heads on synthetic frames    (post-Phase 2: pinkeye pixel-head)
[GREEN]   sitl_mission      ArduPilot SITL MAVLink mission       (emulator CI green, 8/8 evidence events)
[GREEN]   dashboard         Map + lanes + cost + attest + PWA    (post-Phase 5: live-mode + vet-intake)
[GREEN]   voice             Wes voice chain end-to-end           (chain present; live req. credentials)
[GREEN]   scenarios         All 8 scenarios pass SEED=42         (8/8 PASS in 3.2s)
[GREEN]   determinism       seed=42 stable across 3 runs         (md5 eb3f... across 3/3)
[GREEN]   fresh_clone       make sim boots fresh clone           (post-Phase 4: documented + scripted)
[GREEN]   cost_idle         Cost ticker pauses during idle       (all_idle=True emitted; test covers)

Gate status: 10/10 GREEN — phase 6 complete.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `docker pull` cached via `actions/cache` + `docker save/load` | Buildx + `cache-to: type=gha,mode=max` | 2022 (Docker Buildx v0.9) | ~3× faster than save/load approach; native integration with BuildKit layer cache [CITED: dev.to/dtinth benchmarks] |
| `workflow_dispatch`-only SITL jobs | `push + pull_request` on emulator-mode | Phase 6 change | SITL regressions detected on every PR rather than only manual invocation |
| `ardupilot/ardupilot-sitl:<tag>` (aspirational) | Build `docker/sitl.Dockerfile` in CI, push to GHCR | Phase 6 clarification | No longer depend on a non-existent Docker Hub image; own our artifact |
| Single-run determinism check | N=3 in-body loop | Phase 6 (SCEN-03) | Stronger guarantee; catches intermittent non-determinism |

**Deprecated/outdated:**
- **The comment at top of `docker-compose.sitl.yml` lines 3–5** referring to `ardupilot/ardupilot-sitl:Copter-4.5.7`. Phase 6 should update this comment to reflect reality (either: "build-from-source required by default; use `SITL_IMAGE=ghcr.io/<org>/skyherd-sitl:copter-4.5.7` for the cached path after running the publish workflow").
- **`pytest.mark.slow(pytestmark)`** in `tests/drone/test_sitl_smoke.py` line 21 — this is a no-op syntax error (applying a marker decorator to a variable). Harmless but dead code; Phase 6 can clean up incidentally.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | GHCR push workflow is acceptable if Docker-CI path chosen | Standard Stack | [ASSUMED] Writing to `ghcr.io/george11642/*` requires the repo-scope GITHUB_TOKEN; if org policy restricts this, falls back to build-per-run |
| A2 | CI runner has `docker compose` (v2, space form) | Common Pitfalls | [ASSUMED] Verified in general but not against the exact `ubuntu-latest` image tag active on 2026-04-22 |
| A3 | Python 3.11 + 3.12 produce identical scenario MD5s | Common Pitfalls | [ASSUMED] Not verified; if Phase 6 keeps the matrix, 3-run determinism is within a single job so this is internal; if anyone adds a cross-Python determinism check, this must be re-validated |
| A4 | Phase 5 adds `sick_cow` vet-intake assertions to the scenario suite | Zero-Regression Gate | [ASSUMED from REQUIREMENTS.md SCEN-01] If Phase 5 also renames the scenario or changes its event counts, the determinism reference hash (if committed) must be regenerated post-Phase 5 merge |
| A5 | Phase 4 adds `Makefile` entries for `make_world` / `make dashboard` live-mode without touching `sitl-up` / `sitl-down` lines | File Ownership | [ASSUMED] Needs explicit declaration in both Phase 4 and Phase 6 PLAN frontmatter to avoid merge conflict |
| A6 | `skyherd-sitl-e2e --emulator` wall-time is <30s in a GH-hosted runner | SITL Smoke Script | [ASSUMED: emulator starts in ~1s + executes ~5 mission steps; real measurement needed] |
| A7 | Committing a reference hash for determinism is acceptable practice | Determinism Strengthening | [ASSUMED — alternative is purely relative comparison without a frozen baseline]; if scenario suite evolves, any phase merge that alters event counts must refresh the reference |

**If this table is empty:** [not empty — see above]

## Open Questions

1. **Docker path vs emulator-only path?**
   - What we know: emulator covers MAVLink wire protocol; Docker covers ArduPilot firmware (EKF, flight modes, actual C++ code).
   - What's unclear: whether judge scrutiny on "real ArduPilot" matters for BLD-04 credit, or whether the existing `SitlBackend` code being real (even if only exercised manually) plus emulator-CI is sufficient.
   - Recommendation: ship emulator-CI as the required path (BLD-04 complete). Add Docker-CI as a nightly / `workflow_dispatch` supplementary job with `continue-on-error: true`. Don't gate the milestone on Docker.

2. **Publish SITL image to GHCR now or defer?**
   - What we know: GHCR push is a one-time cost per Copter tag bump; downstream pulls are ~60s.
   - What's unclear: whether future phases will exercise the Docker SITL path often enough to justify the publish workflow.
   - Recommendation: SKIP the GHCR push workflow for this milestone. Add a TODO in `docker-compose.sitl.yml` to introduce it in a future milestone if Hardware Tier H3 wakes up.

3. **Commit a reference hash for determinism?**
   - What we know: committing a hash gives stronger regression detection (catches drift over time, not just within one run).
   - What's unclear: frequency of intentional scenario changes post-milestone — every deliberate tweak will need the hash refreshed.
   - Recommendation: DO NOT commit a reference hash in this phase. Cross-run equality is sufficient for SCEN-03 wording ("stable across 3 runs"). If a future milestone hardens further, add a reference fixture then.

4. **Should `make gate-check` fail on YELLOW or only on RED?**
   - What we know: CLAUDE.md lists Gate items as checkboxes; existing verify-latest shows 9/10 GREEN.
   - What's unclear: whether a retroactive audit allows YELLOWs (honest intermediate state) or must be strict 10/10 GREEN.
   - Recommendation: `make gate-check` prints the table and exits 0 iff all 10 are GREEN. Phase 6 acceptance requires the exit-0 path. If any phase pre-Phase 6 landed as YELLOW, Phase 6 either fixes it OR the milestone is not truly complete.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All tests, demo CLI | ✓ | 3.13.11 (local), 3.11/3.12 (CI) | — |
| uv (package manager) | CI + local dev | ✓ | latest | — |
| pytest + pytest-asyncio | test suite | ✓ | 9.0.3 / 0.24+ | — |
| pymavlink | emulator + PymavlinkBackend | ✓ | latest (unpinned) | — |
| mavsdk-python | SitlBackend (Docker path) | ✓ | ≥3,<4 | Emulator path doesn't need it |
| Docker Engine | `make sitl-up` local + Docker CI job | ✓ CI, variable local | 24+ | Emulator-only path |
| `docker compose` (v2) | `docker-compose.sitl.yml` | ✓ on ubuntu-latest | v2 | — |
| nc (netcat) | `nc -u -z 127.0.0.1 14540` port wait | ✓ on ubuntu-latest | — | `bash </dev/tcp/...` |
| GitHub Actions cache (GHA) | Buildx cache-to | ✓ | backend-v2 | Registry cache (GHCR) |
| `ardupilot/ardupilot-sitl:Copter-4.5.7` image | Optional fast-pull path | **✗** | **does not exist** | Build from `docker/sitl.Dockerfile` OR emulator-only |

**Missing dependencies with no fallback:** None blocking. The non-existence of `ardupilot/ardupilot-sitl:Copter-4.5.7` is resolved by using `docker/sitl.Dockerfile` or the emulator path.

**Missing dependencies with fallback:**
- Pre-built Docker image → build-in-CI or use emulator.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8+ with pytest-asyncio 0.24+ (`asyncio_mode=auto`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/drone/test_sitl_e2e.py -v` (with `SITL_EMULATOR=1`) |
| Full suite command | `uv run pytest --cov=src/skyherd --cov-report=term-missing -q --cov-fail-under=80` |
| Demo run command | `uv run skyherd-demo play all --seed 42` (exits 0 iff 8/8 PASS) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BLD-04 | SITL smoke CI job completes <2 min on emulator path | integration | `SITL_EMULATOR=1 uv run pytest tests/drone/test_sitl_e2e.py -v --timeout=120` | ✅ (already 6 tests) |
| BLD-04 | `skyherd-sitl-e2e --emulator` CLI exits 0 and emits all evidence events | integration | `uv run skyherd-sitl-e2e --emulator` | ✅ CLI exists; CI step to add |
| BLD-04 | SITL handshake breaking produces non-zero exit (loud failure) | integration | Add failing-path test that kills emulator mid-mission | ❌ Wave 0 (one new test) |
| SCEN-03 | `make demo SEED=42 SCENARIO=all` produces identical sanitized MD5 across 3 runs | e2e | `uv run pytest tests/test_determinism_e2e.py -v -m slow` | ✅ (needs N=2→N=3 lift) |
| SCEN-02 | All 8 scenarios PASS on every commit | e2e | `uv run skyherd-demo play all --seed 42; echo $?` | ✅ existing |
| SCEN-02 | Coverage ≥87% (existing project baseline) | unit+integration | `uv run pytest --cov=src/skyherd --cov-fail-under=87` | ✅ existing (currently gated at 80%; Phase 6 may raise to 87%) |
| Gate-check | `make gate-check` emits 10/10 GREEN and exits 0 | integration | `make gate-check` | ❌ Wave 0 (new script + Makefile target) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/drone/test_sitl_e2e.py tests/test_determinism_e2e.py -v` (emulator tests + 3-run determinism, ~2–4 min)
- **Per wave merge:** Full `make ci` (lint + typecheck + all tests incl. slow) + `uv run skyherd-demo play all --seed 42`
- **Phase gate:** `make gate-check` exits 0 (10/10 GREEN); CI signal on `main` all-green including new `sitl-smoke` job

### Wave 0 Gaps
- [ ] `scripts/sitl_smoke.py` — 30-line wrapper invoking `skyherd-sitl-e2e --emulator` with evidence-event parsing + loud failure; owner: Phase 6
- [ ] `scripts/gate_check.py` — retro-audit runner; owner: Phase 6
- [ ] `tests/drone/test_sitl_smoke_failure.py` — new test asserting non-zero exit when MAVLink handshake fails (kill emulator mid-test); owner: Phase 6
- [ ] `Makefile` — add `sitl-smoke`, `gate-check`, `determinism-3x` targets; owner: Phase 6 (Phase 4 does NOT touch these)
- [ ] `.github/workflows/ci.yml` — promote `sitl-e2e` job from `workflow_dispatch` to `push + pull_request`; rename to `sitl-smoke`; optionally add `docker-sitl-smoke` as a separate isolated job
- [ ] Update `tests/test_determinism_e2e.py` to 3-run variant (replace existing 2-run test)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | CI uses `GITHUB_TOKEN` (auto) for GHCR; no user auth in Phase 6 |
| V3 Session Management | no | — |
| V4 Access Control | yes (GHCR) | `GITHUB_TOKEN` with `packages: write` permission only if pushing; read by default |
| V5 Input Validation | yes (CLI args) | `typer` already validates `--port`, `--takeoff-alt` types in `e2e.py` |
| V6 Cryptography | no | No new crypto; Ed25519 attest chain untouched by Phase 6 |
| V14 Config | yes | CI secrets properly scoped; no hardcoded tokens |

### Known Threat Patterns for CI + SITL stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious PR triggers Docker privileged build | Elevation | `pull_request` from forks runs with read-only `GITHUB_TOKEN` by default; don't grant `packages: write` on fork PRs |
| Cached poisoned Docker layer | Tampering | GHA cache is scoped per-repo + per-ref; content-addressable via BuildKit layer digests |
| Resource exhaustion (runaway SITL binary) | DoS | `timeout-minutes: 5` on every SITL job |
| Secret leak in determinism output | Info Disclosure | Sanitizer already strips UUIDs + timestamps; review other fields flowing into JSONL |

## Project Constraints (from CLAUDE.md)

- **Sim-first hardline:** MVP is 100% simulated. Phase 6 MUST NOT require real hardware; emulator path honors this.
- **All code new (hackathon rule):** No imports from sibling `/home/george/projects/active/drone/`. Phase 6 writes only to this repo. All scripts must be net-new or modifications of existing SkyHerd files.
- **MIT throughout:** No AGPL deps. `pymavlink` is LGPL (acceptable — it's an import dependency, not a copyleft-triggered redistribution). `mavsdk` is BSD-3. ArduPilot SITL binary is GPL — but we never ship it, only run it in Docker in CI. Safe.
- **TDD:** Tests first for the new `sitl_smoke.py` failure-path test and `gate_check.py`. `test_demo_seed42_is_deterministic_3x` is the test itself — no new logic to TDD there.
- **Skills-first architecture:** N/A to Phase 6 (no new agent logic).
- **No Claude/Anthropic attribution in commits:** Global git config handles this.
- **Submission deadline Sun Apr 26 2026 8pm EST:** Phase 6 is the closing phase. Target: ship ≤ Sat Apr 25 EOD so the demo video has Sun to record/edit.

## Sources

### Primary (HIGH confidence — in-repo verification)
- `src/skyherd/drone/e2e.py` — `run_sitl_e2e()` + CLI `skyherd-sitl-e2e` already exist with emulator + Docker branches
- `src/skyherd/drone/sitl_emulator.py` — 742-line pure-Python MAVLink 2.0 emulator, CRC-correct framing for 12 message types
- `src/skyherd/drone/pymavlink_backend.py` — `PymavlinkBackend` already implements real MAVLink wire mission
- `src/skyherd/drone/sitl.py` — `SitlBackend` with per-operation timeouts (_CONNECT, _ARM, _IN_AIR, _MISSION, _RTL)
- `tests/drone/test_sitl_e2e.py` — 6 emulator-mode tests, currently skipped unless `SITL_EMULATOR=1`
- `tests/drone/test_sitl_smoke.py` — 5 real-Docker tests, currently skipped unless `SITL=1`
- `tests/test_determinism_e2e.py` — existing 2-run sanitize+MD5 comparison
- `.github/workflows/ci.yml` — existing `sitl-e2e` + `docker-sitl-smoke` jobs behind `workflow_dispatch`
- `docker/sitl.Dockerfile` — builds ArduCopter from source with ccache
- `docker-compose.sitl.yml` — healthcheck + host-gateway forwarding
- `Makefile` — current `sitl-up` / `sitl-down` targets
- `pyproject.toml` — `skyherd-sitl-e2e = "skyherd.drone.e2e:app"` entry point + coverage omits for SITL files

### Secondary (MEDIUM confidence — verified via multiple sources)
- [Docker GHA Cache Backend](https://docs.docker.com/build/cache/backends/gha/) — official Docker docs on `type=gha` cache in build-push-action
- [MAVSDK-Python takeoff_and_land.py](https://github.com/mavlink/MAVSDK-Python/blob/main/examples/takeoff_and_land.py) — reference sequence, matches `SitlBackend` implementation
- [Cache management with GitHub Actions](https://docs.docker.com/build/ci/github-actions/cache/) — official Docker docs on CI caching strategies
- [ScribeMD/docker-cache GitHub Marketplace](https://github.com/marketplace/actions/docker-cache) — fallback image caching action
- [pytest.mark.parametrize docs](https://docs.pytest.org/en/stable/how-to/parametrize.html) — reason NOT to use it for cross-run identity

### Tertiary (LOW confidence — single source, verified as contradicting CONTEXT.md assumption)
- **Docker Hub API direct query** (`curl https://hub.docker.com/v2/repositories/ardupilot/ardupilot-sitl/`): returns `{"message":"object not found"}` — confirms `ardupilot/ardupilot-sitl:Copter-4.5.7` does NOT exist. [VERIFIED: 2026-04-22]
- [radarku/ardupilot-sitl Docker Hub](https://hub.docker.com/r/radarku/ardupilot-sitl) — only community SITL image found; latest semantic tag from 2021, no `Copter-4.5` variant
- [ArduPilot Discourse: Copter 4.5.4 SITL not working in docker](https://discuss.ardupilot.org/t/copter-4-5-4-sitl-not-working-in-docker/134884) — known build issues with recent Copter tags in Docker

## Metadata

**Confidence breakdown:**
- In-repo code context: HIGH — every file referenced was read directly
- SITL CI strategy (emulator path): HIGH — existing code already proven, just needs CI promotion
- SITL CI strategy (Docker path): MEDIUM — assumes first-build pain is acceptable via GHA cache; not benchmarked in this repo yet
- Determinism lift (N=2 → N=3): HIGH — trivial extension of working test
- Gate-check script: MEDIUM — design is sound; exact check functions need Phase 6 implementation
- Docker Hub image availability: HIGH — directly verified as NOT existing (contradicts CONTEXT.md assumption)
- MAVSDK-Python API correctness: HIGH — cross-referenced official examples with in-repo `SitlBackend`

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (30 days — CI actions versions and Docker Hub state may drift; re-verify image existence before submission)

## RESEARCH COMPLETE
