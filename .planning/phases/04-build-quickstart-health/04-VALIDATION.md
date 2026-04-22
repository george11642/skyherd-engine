---
phase: 4
slug: build-quickstart-health
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-22
updated: 2026-04-22
---

# Phase 4 — Validation Strategy

> Per-phase validation contract. See "Validation Architecture" section of `04-RESEARCH.md` for full test specs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8 + bash script + GH Actions |
| **Config file** | `pyproject.toml` + `scripts/fresh_clone_smoke.sh` + `.github/workflows/fresh-clone-smoke.yml` |
| **Quick run command** | `uv run pytest tests/world/test_make_world_default.py tests/world/test_packaged_data.py tests/server/test_live_app.py tests/test_readme_quickstart.py -x -q` |
| **Full suite command** | `uv run pytest -q && bash scripts/fresh_clone_smoke.sh` |
| **Estimated runtime** | ~10-20s (quick) / ~3-5min (full, fresh-clone adds ~3min) |

---

## Sampling Rate

- **After every task commit:** Quick run scoped to the file being modified
- **After every plan wave:** Full suite + `uv build && unzip -l dist/*.whl | grep worlds/` (asserts world YAML ships in wheel)
- **Before `/gsd-verify-work`:** `bash scripts/fresh_clone_smoke.sh` completes in <5min on CI
- **Max feedback latency:** ~20 seconds (quick) / ~5min (full with fresh-clone)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-T1 | 04-01 | 1 | BLD-01 | — | RED tests for default config + wheel packaging | unit (TDD-RED) | `uv run pytest tests/world/test_make_world_default.py tests/world/test_packaged_data.py --tb=no -q 2>&1 \| grep -E "failed\|error" \| head -3` | ❌ Wave 0 (this task creates them) | planned |
| 04-01-T2 | 04-01 | 1 | BLD-01 | T-04-01 (narrow mapping only) | `force-include` does not leak `.env`/`runtime/` into wheel | build | `rm -rf dist && uv build 2>&1 \| tail -5 && unzip -l dist/skyherd_engine-0.1.0-py3-none-any.whl \| grep -c "skyherd/worlds/ranch_.*\.yaml"` | ✓ pyproject.toml | planned |
| 04-01-T3 | 04-01 | 1 | BLD-01 | T-04-02 (tempdir fallback bounded) | `make_world(seed=42)` works without TypeError; no silent errors | unit | `uv run pytest tests/world/test_make_world_default.py tests/world/test_packaged_data.py tests/world/test_determinism.py -x --tb=short -q 2>&1 \| tail -10` | ✓ src/skyherd/world/world.py | planned |
| 04-02-T1 | 04-02 | 2 | BLD-03 | — | Live snapshot returns 50 cows (not 12 mock) | integration | `uv run pytest tests/server/test_live_app.py -x --tb=short -q 2>&1 \| tail -8` | ❌ Wave 0 (this task creates it) | planned |
| 04-02-T2 | 04-02 | 2 | BLD-03 | T-04-04 (bind 127.0.0.1), T-04-06 (no silent excepts) | Live CLI importable + `--help` works; errors logged not swallowed | import/CLI smoke | `uv sync 2>&1 \| tail -3 && uv run python -c "from skyherd.server.live import start, main, app; print('live module importable')" && uv run skyherd-server-live --help 2>&1 \| head -5` | ❌ src/skyherd/server/live.py | planned |
| 04-02-T3 | 04-02 | 2 | BLD-03 | T-04-07 (dashboard-mock is accepted escape hatch) | Makefile `dashboard` -> live; `dashboard-mock` -> SKYHERD_MOCK=1 | makefile parse | `make -n dashboard 2>&1 \| grep -c "python -m skyherd.server.live" && make -n dashboard-mock 2>&1 \| grep -c "SKYHERD_MOCK=1"` | ✓ Makefile | planned |
| 04-03-T1 | 04-03 | 2 | BLD-02 | T-04-08 (quoted `rm -rf "$SANDBOX"`), T-04-09 (background server + cleanup trap) | Smoke script shellcheck-clean; no unquoted rm -rf | shell lint | `test -x scripts/fresh_clone_smoke.sh && bash -n scripts/fresh_clone_smoke.sh && grep -c "make demo SEED=42 SCENARIO=all" scripts/fresh_clone_smoke.sh` | ❌ Wave 0 (this task creates it) | planned |
| 04-03-T2 | 04-03 | 2 | BLD-02 | T-04-10 (GH Actions standard trust model) | CI uses cold uv (`enable-cache: false`); `timeout-minutes: 10` bounds runtime | ci/yaml | `uv run python -c "import yaml; d=yaml.safe_load(open('.github/workflows/fresh-clone-smoke.yml')); ev=d.get(True) or d.get('on') or {}; assert 'workflow_dispatch' in ev and 'schedule' in ev; print('yaml valid')" && grep -c "enable-cache: false" .github/workflows/fresh-clone-smoke.yml` | ❌ .github/workflows/fresh-clone-smoke.yml | planned |
| 04-03-T3 | 04-03 | 2 | BLD-02 | T-04-11 (CLAUDE.md is public repo content) | Doc-drift test fails loudly on canonical command changes | unit (doc-drift) | `uv run pytest tests/test_readme_quickstart.py -x --tb=short -q 2>&1 \| tail -5` | ❌ Wave 0 (this task creates it) | planned |

---

## Wave 0 Requirements (created by Task T1 of each plan)

- [ ] `tests/world/test_make_world_default.py` — created by 04-01-T1; covers BLD-01 no-arg invocation + determinism + backward-compat
- [ ] `tests/world/test_packaged_data.py` — created by 04-01-T1; covers BLD-01 wheel-layout assertion
- [ ] `tests/server/test_live_app.py` — created by 04-02-T1; covers BLD-03 live `/api/snapshot` returns real 50-cow world
- [ ] `tests/test_readme_quickstart.py` — created by 04-03-T3; covers BLD-02 doc-drift guard
- [ ] `scripts/fresh_clone_smoke.sh` — created by 04-03-T1; covers BLD-02 fresh-clone SLA
- [ ] `.github/workflows/fresh-clone-smoke.yml` — created by 04-03-T2; covers BLD-02 nightly CI assertion

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Judge clones repo on a machine with uv already installed and runs 3-command quickstart | BLD-02 | True "fresh" requires a non-CI machine | Pull repo on a second laptop, run the 3 README commands, time it, confirm all scenarios PASS |
| Visual dashboard polish (agent lanes populating, cost ticker paused state, drone trail fade) | DASH-02..06 | Phase 5 owns this; Phase 4 ships plumbing only | Documented in Phase 5 plan; not this phase's concern |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every task has one)
- [x] Wave 0 covers all MISSING references (6 new files all created in Task T1 of their respective plans)
- [x] No watch-mode flags (all `-x -q --tb=short` style — one-shot)
- [x] Feedback latency < 20s (quick) / < 5min (fresh-clone)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned — ready for execution
