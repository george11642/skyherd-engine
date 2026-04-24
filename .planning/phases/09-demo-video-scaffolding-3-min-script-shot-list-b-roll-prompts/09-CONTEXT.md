# Phase 09 CONTEXT — Demo Video Scaffolding + Pre-Flight Readiness

**Phase:** 09 (final)
**Status:** Executing (2026-04-24 morning)
**Submission:** 2026-04-26 20:00 EST (target 18:00 EST)
**Hardware plug-in day:** **2026-04-24 Friday morning**
**User hardware on-hand:** 2 × Raspberry Pi 4 + 1 × Mavic Air 2 (collar-free)

---

## Mission (two parts, one phase)

### Part A — Demo Video Scaffolding

Everything upstream of the camera button so George can record + edit the 3-minute
Devpost submission video confidently.

### Part B — Pre-Flight Readiness Audit

Guarantee Friday-morning hardware plug-in works with **zero code or config edits**.
George should `curl ... | bash`, watch heartbeats go green on the dashboard, and
start filming.

---

## Hard constraints (inherited from CLAUDE.md + vision)

- Determinism preserved: `make demo SEED=42 SCENARIO=all` byte-identical (modulo
  wall-timestamp sanitization) across 3 consecutive runs.
- Coverage floor: 80% overall (no regression from 87.42% baseline).
- No new runtime deps (dev-only `pytest`/`vitest` additions allowed for new
  tests).
- MIT only, zero-attribution commits.
- **Nothing in `hardware/` or `docs/HARDWARE_*.md` may require George to edit
  code or config on Friday.** If something requires editing, fix it now or move
  the edit into a template George fills in once and commits nothing.

---

## Read-ordered context

1. **Plan authority:** `/home/george/.claude/plans/update-ur-memory-project-context-splendid-swan.md` v5.1.
2. **Roadmap Phase 9 section:** `.planning/ROADMAP.md:207-228`.
3. **Existing video draft:** `docs/VIDEO_SCRIPT.md` — Mavic-hero oriented; we layer a sim-keyed version on top without deleting.
4. **Existing shot list seed:** `docs/demo-assets/shot-list.md` — day-of beats; we expand into full SHOT_LIST.md with B-roll prompts.
5. **Hardware runbooks (Part B inputs):**
   - `docs/HARDWARE_PI_FLEET.md` — canonical two-Pi topology; UPDATE in place.
   - `docs/HARDWARE_DEMO_RUNBOOK.md` — 60-s on-camera demo.
   - `docs/HARDWARE_H1_RUNBOOK.md` / `H2` / `H3` — per-phase bringup docs.
   - `hardware/pi/bootstrap.sh` — curl-pipeable one-command Pi setup.
   - `hardware/pi/credentials.example.json` — credential schema.
   - `scripts/provision-edge.sh` — what bootstrap.sh delegates to.
   - `docker-compose.hardware-demo.yml` — H2 laptop demo stack.
6. **Companion apps:** `android/SkyHerdCompanion/`, `ios/SkyHerdCompanion/`, `.github/workflows/{android,ios}-app.yml`.
7. **State:** `.planning/STATE.md` — tests 1106 pass / 0 fail, coverage 87.42%.

---

## Why this phase is split into 5 plans

The scope is broad (video + hardware readiness) but the surface area is
reviewable per doc/target. Five plans keeps each executor unit < 90 min and each
commit scoped:

| Plan | Scope | Deliverables |
|------|-------|--------------|
| 09-01 | Video scaffolding content | `DEMO_VIDEO_SCRIPT.md`, `SHOT_LIST.md`, `SUBMISSION.md`, `LINKEDIN_LAUNCH.md`, `YOUTUBE.md` |
| 09-02 | Rehearsal + record-ready Makefile targets | `make rehearsal`, `make record-ready` |
| 09-03 | Bootstrap.sh idempotency + Pi-fleet runbook update + pre-flight checklist | Audit fixes, `PREFLIGHT_CHECKLIST.md`, updated `HARDWARE_PI_FLEET.md` |
| 09-04 | Pre-flight E2E test + zero-config audit + companion-app artifact docs | `test_preflight_e2e.py`, audit sweep, H3 runbook URL notes |
| 09-05 | Phase close | `09-SUMMARY.md`, `VERIFICATION.md`, final sign-off |

---

## Requirements (frontmatter ⇢ plans)

| ID | Description | Plan |
|----|-------------|------|
| VIDEO-01 | 3-min shot-by-shot script keyed to `make demo SEED=42` | 09-01 |
| VIDEO-02 | Shot list + B-roll image-gen prompts | 09-01 |
| VIDEO-03 | Devpost submission draft (100–200 word summary, categories) | 09-01 |
| VIDEO-04 | LinkedIn launch draft (with `[APPROVE_BEFORE_POST]`) | 09-01 |
| VIDEO-05 | YouTube metadata (title, description, tags, thumbnail brief) | 09-01 |
| VIDEO-06 | `make rehearsal` + `make record-ready` | 09-02 |
| PF-01 | `bootstrap.sh` idempotent dry-run audit | 09-03 |
| PF-02 | Two-Pi fleet runbook: Friday 15-min sequence | 09-03 |
| PF-03 | `PREFLIGHT_CHECKLIST.md` (20-item Friday checklist) | 09-03 |
| PF-04 | End-to-end preflight test `< 30 s`, mocked | 09-04 |
| PF-05 | Zero-config audit (grep hardware/ for TODO/FIXME/FILL_IN) | 09-04 |
| PF-06 | Companion APK/IPA download URL documented | 09-04 |

---

## Execution pattern

- Autonomous, non-TDD (doc-heavy Part A; Part B has test scaffolding).
- Commit per plan (1 commit each, per repo convention) unless deviations require
  split commits.
- No checkpoints — George requested "start now, be thorough" and the finale
  has no interactive gates (auth is not required for any deliverable).
- After 09-04 closes, plan 09-05 produces SUMMARY + VERIFICATION + final sign-off.

## Friday-morning one-liner (target state)

```
On each Pi: curl -sSfL https://raw.githubusercontent.com/george11642/skyherd-engine/main/hardware/pi/bootstrap.sh | bash
On laptop:   make dashboard     # http://localhost:8000
On phone:    install APK from GitHub Releases, launch, pair Mavic
```

That is the entire Friday sequence. If Plan 09-03 / 09-04 surface anything that
breaks this, we fix it in-phase.
