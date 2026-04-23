---
phase: 05-dashboard-live-mode-vet-intake
plan: "03"
subsystem: fullstack
tags: [api, fastapi, react, sse, vet-intake, attestation, dash-04, dash-06, scen-01, tdd]
dependency_graph:
  requires: [05-01, 05-02]
  provides:
    - "POST /api/attest/verify endpoint (DASH-04)"
    - "GET /api/vet-intake/{intake_id} endpoint (SCEN-01)"
    - "VetIntakePanel React component + PixelDetectionChip (DASH-06 UI)"
    - "AttestationPanel Verify Chain button (DASH-04 UI)"
    - "vet_intake.drafted registered in SSE event-types array"
    - "X-Accel-Buffering: no header on /events SSE response (Pitfall 1)"
    - "Phase 1 public-accessor path for /api/agents live session_id (DASH-06 backend proof)"
    - "get_intake_path() regex + traversal guard (SCEN-01 security)"
  affects:
    - src/skyherd/server/app.py (routes + live-accessor refactor)
    - src/skyherd/server/vet_intake.py (get_intake_path validation)
    - web/src/lib/sse.ts (event-types registry)
    - web/src/components/AttestationPanel.tsx (Verify button)
    - web/src/App.tsx (VetIntakePanel mounted)
tech_stack:
  added: []
  patterns:
    - Inline markdown renderer (~20 lines, HTML-escape first) — avoids 50KB react-markdown
    - Single regex-based pixel-detection extractor from markdown body
    - Fail-soft Phase 1 public-accessor with legacy _sessions fallback
    - state-machine chip mapping (idle→verifying→valid/invalid/error)
    - Two sibling buttons instead of nested <button> (valid HTML)
key_files:
  created:
    - web/src/components/VetIntakePanel.tsx
    - web/src/components/VetIntakePanel.test.tsx
  modified:
    - src/skyherd/server/app.py
    - src/skyherd/server/vet_intake.py
    - web/src/lib/sse.ts
    - web/src/components/AttestationPanel.tsx
    - web/src/components/AttestationPanel.test.tsx
    - web/src/App.tsx
    - tests/server/test_app_coverage.py
decisions:
  - "X-Accel-Buffering header placed on EventSourceResponse in app.py (where EventSourceResponse is constructed), not events.py as originally framed — Pitfall 1 Fix still satisfied; the events.py file holds only the broadcaster producer loops"
  - "_live_agent_statuses refactored to prefer mesh.agent_sessions() (Phase 1 public) but type-checks the return is a dict before iterating — MagicMock auto-generated attributes would otherwise poison the iterator with phantom keys. Legacy mesh._sessions remains the fallback for backward compat with tests/server/test_app_coverage.py::_make_mock_mesh"
  - "Severity-chip test-id format standardized as severity-chip-{intake_id} so UI tests assert specific rows deterministically rather than querying by chip class (survives CSS refactors)"
  - "VetIntakePanel's markdown renderer escapes HTML entities BEFORE running regex replacements so user-visible markdown cannot inject raw HTML — pattern 5 security posture"
  - "PixelDetectionChip uses chip-thermal variant (red/amber) rather than a new color token — keeps design-token palette stable for Plan 05-04's visual regression diff"
metrics:
  duration_min: 25
  completed: "2026-04-23T03:23:00Z"
  tasks_completed: 4
  files_modified: 9
---

# Phase 05 Plan 03: DASH-04 verify button + SCEN-01 vet-intake modal + DASH-06 pixel chip

**One-liner:** Closes DASH-04 (POST /api/attest/verify + Verify Chain UI button), ships the rancher-readable VetIntakePanel modal (SCEN-01), renders Phase 2's pixel bbox as a DASH-06 chip inside the packet, and proves /api/agents live-mode session IDs via Plan 05-01's public-accessor fixture.

## What Was Built

### Task 1 — RED: failing tests for endpoints + verify button + DASH-06 chip (commit 886c01e)

Python tests appended to `tests/server/test_app_coverage.py` (6 new):

- `test_attest_verify_live` — POST /api/attest/verify delegates to `Ledger.verify()`; asserts `valid=True, total=42` from a MagicMock ledger
- `test_attest_verify_mock` — mock mode returns `{valid: True, total: 0, reason: "mock"}`
- `test_vet_intake_endpoint_returns_markdown` — GET /api/vet-intake/{id} returns text/markdown body when file present
- `test_vet_intake_endpoint_404_on_missing` — 404 for absent file
- `test_vet_intake_endpoint_400_on_bad_id` — 400 for malformed intake_id (regex-guarded)
- `test_agents_live_session_ids` — **DASH-06 backend proof** — /api/agents returns 5 entries each with `session_id` matching `^sess_[a-z_]+$`, asserting the live path (not mock fallback)

Vitest tests:

- `web/src/components/AttestationPanel.test.tsx` — 3 new tests (Verify button renders; click triggers POST /api/attest/verify and shows VALID/INVALID chip)
- `web/src/components/VetIntakePanel.test.tsx` (new) — 7 tests covering SSE subscription, markdown renderer (## → h3, ** → strong), severity chip mapping (escalate/observe/log), parsePixelDetections regex, DASH-06 pixel-detection chip present, DASH-06 pixel-detection chip absent

RED confirmed: 5/6 Python tests fail on current main, 3 vitest AttestationPanel verify tests fail, VetIntakePanel.test.tsx import-errors because the component file didn't exist.

### Task 2 — GREEN: backend endpoints + live-accessor refactor (commit 11f7db3)

**`src/skyherd/server/app.py`:**

- `api_attest_verify()` POST /api/attest/verify — delegates to `ledger.verify().model_dump()` in live mode; returns `{valid: True, total: 0, reason: "mock"}` in mock mode
- `api_vet_intake(intake_id)` GET /api/vet-intake/{intake_id} — uses `vet_intake.get_intake_path()` which raises `ValueError` → 400 on bad id; `path.exists()` check → 404; returns `PlainTextResponse(..., media_type="text/markdown; charset=utf-8")` with the markdown body
- `/events` SSE response now carries `headers={"X-Accel-Buffering": "no"}` (Pitfall 1 — defeats nginx/reverse-proxy SSE buffering)
- `_live_agent_statuses()` rewritten to prefer `mesh.agent_sessions()` (Phase 1 public API) with `isinstance(candidate, dict)` type-check and graceful legacy-fallback to `mesh._sessions`; each entry now includes `session_id` so DASH-06 acceptance test passes
- `_mock_agent_statuses()` augmented with `session_id: "sess_mock_{name}"` for shape parity

**`src/skyherd/server/vet_intake.py`:**

- `get_intake_path(intake_id)` now validates intake_id against canonical regex `^[A-Z][0-9]{3}_[0-9]{8}T[0-9]{6}Z$` (raises `ValueError` on bad shape), plus resolve()/startswith() path-traversal guard

**`web/src/lib/sse.ts`:**

- `eventTypes` array registers `vet_intake.drafted` AND `neighbor.handoff` (both needed by the dashboard consumers that Plan 05-02 and CrossRanchMesh emit)

### Task 3 — GREEN: AttestationPanel Verify Chain button (commit 0c3cde6)

**`web/src/components/AttestationPanel.tsx`:**

- Header restructured from a single `<button>` wrapping everything to a `<div>` containing two sibling `<button>` elements (toggle button on the left, verify button on the right) — eliminates invalid nested `<button>` in the DOM
- `VerifyState` state-machine: `idle → verifying → valid | invalid | error`
- Click handler: `e.stopPropagation()` so clicking Verify does NOT collapse the panel; `await fetch("/api/attest/verify", {method: "POST"})`; chip render: `chip-sage` for VALID (+ total), `chip-danger` for INVALID (+ first_bad_seq), `chip-warn` for error
- `aria-live="polite"` on result chips for assistive tech

### Task 4 — GREEN: VetIntakePanel + PixelDetectionChip (commit 4f6d7bf)

**`web/src/components/VetIntakePanel.tsx` (new, 359 lines):**

- Subscribes to `vet_intake.drafted` SSE event via `getSSE().on()` (cleanup via `useEffect` return → `off()`)
- On event: prepends intake row to the list (max 20), fires `fetch("/api/vet-intake/{id}")` which resolves into the row's `body`
- Clicking a row toggles the detail pane which renders:
  - DASH-06 `PixelDetectionChip` row for each `pixel_detection` entry parsed from the markdown body
  - The markdown body rendered via the inline `renderMarkdown()` function (HTML-escape first; converts `##` → h3, `#` → h2, `**bold**` → strong, `` `code` `` → code, `- bullet` → li in ul, blank lines break paragraphs)
- `parsePixelDetections(markdown)` exported helper runs a single global regex `/- kind=pixel_detection head=(\w+) bbox=\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\] conf=([\d.]+)/g` against the body
- Severity chip mapping via `SEVERITY_CHIP` lookup: `escalate → chip-danger`, `observe → chip-warn`, `log → chip-muted`; each chip has `data-testid="severity-chip-{id}"`
- `PixelDetectionChip` uses `data-testid="pixel-detection-chip"` and renders `<strong>{head}</strong> [{x0},{y0},{x1},{y1}] {conf%}` with a tooltip showing the full metadata

**`web/src/App.tsx`:**

- `VetIntakePanel` imported and mounted in the right rail between `CostTicker` and `AttestationPanel`

## Coverage Delta

| Module                          | Before (baseline) | After        |
| ------------------------------- | ----------------: | -----------: |
| `src/skyherd/server/app.py`     |               67% |      **83%** |
| `src/skyherd/server/events.py`  |               84% |      **84%** (unchanged — no new code in events.py) |
| `src/skyherd/server/vet_intake.py` |            —     |      **97%** |
| Server module total             |           73–77%  |  **86%**     |

Server-module coverage crosses DASH-02 ≥ 85% target for Plan 05-04 to lock.

## Verification Results

| Check                                                 | Result                          |
| ----------------------------------------------------- | ------------------------------- |
| 6 new Python tests (Plan 05-03 block)                 | **6/6 pass**                    |
| tests/server/ total                                   | **61/61 pass**                  |
| tests/scenarios/ (SCEN-02 zero-regression)            | **150/150 pass** (3 skipped)    |
| Full pytest suite                                     | **1220/1220 pass** (14 skipped) |
| Vitest AttestationPanel                               | **12/12 pass**                  |
| Vitest VetIntakePanel                                 | **7/7 pass**                    |
| Vitest full suite                                     | **48/48 pass**                  |
| `tsc --noEmit`                                        | clean (0 errors)                |
| `uv run ruff check` (touched files)                   | clean                           |
| `uv run pyright src/skyherd/server/{app,vet_intake}.py` | 0 errors, 0 warnings          |
| `pnpm run build`                                      | dist/assets/index.js 401KB      |
| `skyherd-demo play all --seed 42` (SCEN-02)           | **8/8 scenarios pass**          |
| No new npm deps (react-markdown / remark / marked / markdown-it) | confirmed via grep     |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical functionality] `get_intake_path()` didn't validate input**

- **Found during:** Task 2 implementation
- **Issue:** The Plan 05-02 contract stated `get_intake_path` "raises ValueError on bad intake_id shape", but the existing implementation returned `_VET_INTAKE_DIR / f"{intake_id}.md"` with no validation — any string would resolve, including `../../etc/passwd`.
- **Fix:** Added regex check `_INTAKE_ID_RE.match(intake_id)` (the existing unused constant) + resolve()/startswith() path-traversal guard. Raises `ValueError` with actionable message on both failures. `api_vet_intake` catches it and returns 400.
- **Files modified:** `src/skyherd/server/vet_intake.py`
- **Commit:** 11f7db3

**2. [Rule 1 — Bug] `_live_agent_statuses` returned phantom MagicMock names when pre-existing test fixture was reused**

- **Found during:** Task 2 full-suite regression (2 pre-existing tests failed after refactor)
- **Issue:** `MagicMock().agent_sessions()` auto-returns a MagicMock that happens to support `.items()` (returning phantom tuples). The first refactor used `hasattr(sessions, "items")` which always returned True for MagicMocks.
- **Fix:** Type-guard via `isinstance(candidate, dict)` before trusting the accessor return. If not a real dict, fall through to the legacy `_sessions` attribute (also type-guarded).
- **Files modified:** `src/skyherd/server/app.py`
- **Commit:** 11f7db3

**3. [Rule 1 — Bug] Nested `<button>` in AttestationPanel header was invalid HTML**

- **Found during:** Task 3 initial implementation
- **Issue:** The existing header was a single `<button>` wrapping the title. Adding the Verify button inside it would have produced nested `<button>` elements — invalid HTML that browsers auto-close, mangling the DOM.
- **Fix:** Restructured header into a `<div>` with TWO sibling `<button>` elements (toggle left, verify right). Preserved existing test expectations (`closest("button")`) and `aria-expanded` semantics.
- **Files modified:** `web/src/components/AttestationPanel.tsx`
- **Commit:** 0c3cde6

### Design Adaptations

**Plan frontmatter placed X-Accel-Buffering in events.py:**

The plan's `files_modified` entry listed `src/skyherd/server/events.py` as the target for the `X-Accel-Buffering` header addition. In practice, `EventSourceResponse` is constructed in `src/skyherd/server/app.py:sse_stream` — `events.py` holds only the `EventBroadcaster` producer loops. The header was added to `app.py` at the point of response construction, satisfying the Pitfall 1 intent without requiring an events.py change.

**DASH-06 pixel-detection chip via markdown parse, not JSON endpoint:**

The plan outlined two strategies:
1. Extend `/api/vet-intake/{id}` with a JSON variant carrying `signals_structured`
2. Parse the markdown body for the `## Structured Signals (DASH-06)` section

Strategy 2 was chosen. Rationale: the SCEN-01 markdown surface is the canonical rancher artifact; adding a JSON variant would split the source of truth. The parsing regex is strict and anchored to the exact line shape Plan 05-02's `_render_markdown` produces, so the two layers stay tightly coupled.

**Empty-state text avoids false match:**

Initial `getByText(/vet intake/i)` matched both the panel title ("Vet Intake") and the empty state ("no vet intakes yet"). The test was tightened to use the exact title string + assert the empty state placeholder is also present — the one-liner edit better reflects the user-visible contract.

## Known Stubs

None. Every contract in the plan's `<must_haves>` section was wired to real code paths with real assertions. The `signals_structured` markdown rendering re-uses Plan 05-02's `[280, 110, 380, 200]` synthetic bbox (intentional sim coverage until Phase 2 VIS-05 lands real detections).

## Threat Flags

None. The new endpoints satisfy their threat model:

- **T-05-03 (vet-intake path traversal):** `get_intake_path()` enforces `^[A-Z][0-9]{3}_[0-9]{8}T[0-9]{6}Z$` regex + resolve/startswith guard — the regex alone already excludes `/` and `..`, and the path check is defense-in-depth
- **T-05-04 (verify endpoint DoS):** `api_attest_verify()` has no auth (consistent with existing `/api/attest`) but is read-only, bounded by chain length, and mock-mode short-circuits without walking — same risk posture as `/api/attest`
- **T-05-05 (XSS via markdown):** `VetIntakePanel::renderMarkdown` HTML-escapes the input BEFORE running regex replacements; no user content bypasses the escape; `dangerouslySetInnerHTML` receives only escaped+transformed output

## Commits

| Hash    | Message                                                                   |
| ------- | ------------------------------------------------------------------------- |
| 886c01e | test(05-03): add failing tests for /api/attest/verify, /api/vet-intake, DASH-06 agents (RED) |
| 11f7db3 | feat(05-03): add /api/attest/verify + /api/vet-intake endpoints + DASH-06 live session IDs |
| 0c3cde6 | feat(05-03): AttestationPanel Verify Chain button (DASH-04 UI)            |
| 4f6d7bf | feat(05-03): VetIntakePanel (SCEN-01 UI + DASH-06 pixel chip)             |

## Self-Check: PASSED

Files verified on disk:

- [x] `src/skyherd/server/app.py` — EXISTS (contains `api_attest_verify`, `api_vet_intake`, `X-Accel-Buffering`)
- [x] `src/skyherd/server/vet_intake.py` — EXISTS (contains `_INTAKE_ID_RE.match(intake_id)`)
- [x] `web/src/lib/sse.ts` — EXISTS (contains `vet_intake.drafted`)
- [x] `web/src/components/AttestationPanel.tsx` — EXISTS (contains `/api/attest/verify`)
- [x] `web/src/components/VetIntakePanel.tsx` — EXISTS (359 lines ≥ 150 min; contains `vet_intake.drafted`, `/api/vet-intake/`, `renderMarkdown`, `pixel_detection`, `bbox`)
- [x] `web/src/components/VetIntakePanel.test.tsx` — EXISTS
- [x] `tests/server/test_app_coverage.py` — contains `test_attest_verify`, `test_vet_intake_endpoint`, `test_agents_live_session_ids`

Commits verified:

- [x] 886c01e — EXISTS (RED)
- [x] 11f7db3 — EXISTS (backend GREEN)
- [x] 0c3cde6 — EXISTS (AttestationPanel GREEN)
- [x] 4f6d7bf — EXISTS (VetIntakePanel GREEN)

Must-have contract coverage:

- [x] POST /api/attest/verify live + mock — tested
- [x] GET /api/vet-intake/{intake_id} markdown + 404 + 400 — tested
- [x] Verify button state machine (VALID / INVALID) — tested
- [x] VetIntakePanel SSE subscription + markdown rendering — tested
- [x] DASH-06 PixelDetectionChip bbox + confidence — tested
- [x] No new markdown npm dependency — grep confirmed
- [x] vet_intake.drafted in eventTypes — grep confirmed
- [x] X-Accel-Buffering header on SSE response — grep confirmed
- [x] test_agents_live_session_ids proves `/api/agents` live-mode returns `sess_*` IDs — passes
- [x] SCEN-02 zero regression — `skyherd-demo play all --seed 42` → 8/8 scenarios pass
- [x] Server coverage ≥ 85% — 86% measured
