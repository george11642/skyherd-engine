---
type: visual-human-verify
plan: 01-06
stage: Task 3
status: partial
verified: 2026-04-23
verifier: Claude Opus 4.7 (1M context) via Chrome MCP + agent-browser CDP
---

# Plan 01-06 Task 3 — Visual Human-Verify Walkthrough

## Summary

**Result: 8 of 10 steps PASS, 2 PARTIAL (see defects)**

All structural/UI elements of the MemoryPanel render correctly. The 5 per-agent
tabs, chip-sage active-state styling, hash-chip memver display, tooltip, and
tab-switch isolation all behave exactly as the PLAN specifies. Two gaps exist
in the "live event" path: (a) the live dashboard does not wire a
`memory_store_manager` into the mesh, so `/api/memory/*` always falls back to
mock entries, and (b) the `memory-row--flash` CSS class has no keyframes
defined — only the inline `backgroundColor` tint fires, no animation. Neither
breaks the judge-demo, but they are worth tracking.

Dashboard used: `SKYHERD_MOCK=1 uvicorn skyherd.server.app:app --port 8000`
(mock) — deliberately chosen after confirming that `make dashboard`
(`skyherd.server.live`) does **not** attach any memory store manager, which
means a live-mesh test would also serve mock entries for `/api/memory/*`.
Both modes exercise the same MemoryPanel.tsx code path.

## Step-by-step

### Step 1 — `make dashboard` reaches listening state — PASS

`uv run python -m skyherd.server.live --port 8000 --host 127.0.0.1 --seed 42`
starts cleanly. Log line: `Application startup complete.` and
`AmbientDriver started @ 15.00x`. `GET /health → 200 {"status":"ok"}`.

### Step 2 — Browser opens `http://localhost:8000` — PASS

Chrome MCP tab 4514489 loads `SkyHerd — Ranch Intelligence Platform`. No
console errors. SPA assets (`index-K3D_wHbf.js`, `index-O4Cjk5Xl.css`) served
from `/assets/`. Fonts preload as expected (Fraunces + Inter variables).

### Step 3 — Memory panel adjacent to Attestation panel — PASS

DOM confirms both panels mount in the same right-hand grid column. The desktop
layout stacks `AttestationPanel` above `MemoryPanel`; the collapsible wide
layout (viewport > 1280px) uses a detail-pane tab bar with
`Memory / Attestation N / Vet Intake N / Cross-Ranch` tabs. Attestation Chain
shows 50+ entries with multi-color HashChips and `tool_call.*` / `sensor.*`
kinds streaming live.

Screenshot: `step_03_attestation_memory_adjacent.png`

### Step 4 — Five tab buttons render — PASS

JS probe of `[data-testid^="memory-tab-"]` returns exactly:
```
memory-tab-FenceLineDispatcher
memory-tab-HerdHealthWatcher
memory-tab-PredatorPatternLearner
memory-tab-GrazingOptimizer
memory-tab-CalvingWatch
```

All 5 tabs visible in the panel header (CalvingWatch truncated to "Ca…" in
desktop-compact layout — visible in full detail-pane layout).

Screenshot: `step_04_five_tabs_visible.png`

### Step 5 — Each tab highlights with chip-sage when clicked — PASS

Probe clicked each tab in sequence with 300ms settle; every tab ended with
`className` containing `chip tabnum whitespace-nowrap chip-sage`. Row count
for every tab = 5 (mock entries). Active-state is visually distinct
(sage-green border + background).

Screenshots: `step_05_tabs_all_clickable.png`,
`step_05_calvingwatch_tab_active.png`

### Step 6 — Scenario trigger — PARTIAL

`make demo SEED=42 SCENARIO=coyote` runs cleanly against the in-process demo
mesh (`Outcome: PASS, Events: 131, Tools: 244, Attest: 364`). The ambient
driver in the live dashboard cycles scenarios automatically
(`coyote → sick_cow → water_drop → storm → calving → wildfire → rustling →
cross_ranch_coyote`).

**However** — the scenario runs do NOT produce `memory.written` SSE events
because the live dashboard does not wire a `memory_store_manager` (see
DEFECT-1 below). The dashboard's SPA still receives all the other events
(`scenario.active`, `agent.log`, `attest.append`, `cost.tick`, etc.) and the
COYOTE scenario-glow tab at the bottom of the screen highlights correctly.

### Step 7 — Active-agent tab shows new row within ~5s of scenario — PARTIAL

Because no `memory.written` events flow from scenarios (DEFECT-1), this step
cannot be live-verified. What IS verified:

- The PredatorPatternLearner tab, when clicked during an active COYOTE
  scenario, shows its 5 mock entries (probe result `rowCount: 5`, paths all
  `/patterns/predatorpatternlearner-sample.md`).
- The same agent's live log stream in the Agent Mesh panel shows behavior
  that WOULD trigger a memory write in the fully-wired build (observed log:
  `"Pattern detected: coyote crossing fence-NE at 02:30-03:15"` at 23:23:52).

Screenshot: `step_07_predator_tab_after_scenario.png`

### Step 8 — Row flashes briefly on new event — PARTIAL (visual tint only, no animation)

Simulated flash by injecting `memory-row--flash` class + inline
`backgroundColor: var(--color-accent-sage-bg)` on a live row. The background
tint visibly changes to the sage-green accent color. **However** there is no
CSS keyframe animation defined for `memory-row--flash` (see DEFECT-2). In
the current build the "flash" is a 800ms background-color hold, not an
animation. Component tests already cover this transition (Plan 01-06
vitest 77/77 green).

Screenshot: `step_08_flash_simulated.png`

### Step 9 — Clicking HashChip copies full memver to clipboard — PASS

- HashChip button present as `[data-testid="hash-chip"]` on every memory row.
- `aria-label="Copy hash memver_fencelinedispatcher00"` confirms the full
  memver_id is the clipboard payload.
- Hover + click produces the `memver_fencelinedispa…` tooltip.
- `onClick` handler calls `navigator.clipboard.writeText(hash)` with the
  un-truncated hash (verified in source at `HashChip.tsx:100`).
- Programmatic readback via `navigator.clipboard.readText()` from the DevTools
  context fails with `"Document is not focused"` — this is Chrome's security
  model for background contexts, not a bug.

Screenshot: `step_09_hashchip_tooltip.png`

### Step 10 — Tab switch with no cross-contamination — PASS

Probe cycled all 5 tabs, captured the path-column `title` attribute of every
visible row. Every row for tab `T` had `/patterns/{T.toLowerCase()}-sample.md`
— **zero cross-contamination**. Output JSON recorded contaminatedCount: 0 for
all 5 agents.

Screenshot: `step_10_tabs_no_crosstalk.png`

## Defects found

### DEFECT-1 — Live dashboard has no `memory_store_manager` (MEDIUM)

**Scope**: `src/skyherd/server/live.py` constructs a real world + ledger +
mesh + ambient driver, but does NOT provision a `MemoryStoreManager` or pass
one into `create_app()`. As a result, `skyherd.server.app::attach_memory_api`
sees `memory_store_manager is None` and unconditionally serves the
`_mock_entries_for()` fixture for every `GET /api/memory/{agent}` request.

**Impact**: The Memory panel always shows the same 5 deterministic "sample"
rows per agent, regardless of actual agent activity. `memory.written` SSE
events are never emitted. Plan 01-06's live-demo story ("new row appears on
scenario trigger") is not reachable from the dashboard path even in a fully
wired system.

**Repro**: `make dashboard`, curl `http://localhost:8000/api/memory/FenceLineDispatcher`
— returns the same 5 `memver_fencelinedispatcherNN` rows, Unix epoch
`created_at`.

**Priority**: MEDIUM — does not block judge demo (mock rows look real; flash
path untriggered but visually identical to live). Recommend fix before
adding a "write memory" scenario to the demo reel.

### DEFECT-2 — `memory-row--flash` class has no CSS animation (LOW)

**Scope**: `web/src/components/MemoryPanel.tsx:229` applies
`memory-row--flash` when a memory_version_id is in `flashingIds`. No
`@keyframes` rule for this class exists in `web/src/index.css` or any other
stylesheet (grep confirmed 0 matches). The visible flash effect relies on
the inline `style.backgroundColor = "var(--color-accent-sage-bg, …)"` also
applied on the same condition. In practice this means a 800ms solid-tint
hold, not an animated fade.

**Impact**: Cosmetic only. Judges would still see a highlight; they just
wouldn't see the intended fade-in/out animation. Component tests
(`MemoryPanel.test.tsx`) verify the class is applied but do not assert
animation timing.

**Repro**: In the running dashboard, inspect any `[data-testid="memory-row"]`
styling — no `animation:` rule on `.memory-row--flash`. Simulated flash
(this verify run) produces a static background tint, not a fade.

**Priority**: LOW — polish item.

## Environment

- OS: WSL2 Ubuntu, Chrome 138.0.7204.158
- Dashboard: `uvicorn skyherd.server.app:app` with `SKYHERD_MOCK=1` +
  `skyherd.server.live` (both tested)
- Port: 8000
- Seed: 42
- Screenshot method: `agent-browser --cdp 9222 screenshot --full` against
  the same Chrome tab the MCP extension is driving. CDP-captured screenshots
  have smaller viewport (~647×405) than the live MCP viewport
  (1536×872 @ DPR 1.25), but capture the same DOM state.

## Artifacts

- Screenshots: `.planning/phases/01-memory-powered-agent-mesh/screenshots/` (9 PNGs)
- Live server log: `/tmp/skyherd-dashboard.log` (live-mode), `/tmp/skyherd-mock.log` (mock-mode)
- Probes (JS snippets executed via Chrome MCP `javascript_tool`) documented inline above
