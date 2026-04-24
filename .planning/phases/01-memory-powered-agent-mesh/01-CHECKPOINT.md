---
type: human-verify
plan: 01-06
stage: Task 3
status: approved-partial
created: 2026-04-23
verified: 2026-04-23
verify_doc: 01-VISUAL-VERIFY.md
---

# Plan 01-06 Task 3 — MemoryPanel human-verify checkpoint

## What was built

- `web/src/lib/sse.ts` eventTypes extended with `memory.written` + `memory.read`.
- `web/src/components/MemoryPanel.tsx` — 5 per-agent tabs, HashChip rows, flash animation on SSE, mounted in App.tsx dashboard grid after AttestationPanel.

## Automated status

- `pnpm vitest run` — 77 passed (7 new MemoryPanel tests).
- `pnpm run build` — clean.

## Human verification (10-step visual checklist from PLAN)

1. Run `make dashboard` in the project root and wait for `Uvicorn running on http://0.0.0.0:8000`.
2. Open `http://localhost:8000` in a browser.
3. Confirm the **Memory** panel appears on the dashboard, adjacent to the Attestation panel.
4. Confirm five tab buttons are visible: FenceLineDispatcher, HerdHealthWatcher, PredatorPatternLearner, GrazingOptimizer, CalvingWatch.
5. Click each tab — the tab should highlight (chip-sage styling).
6. In a separate terminal run `make demo SEED=42 SCENARIO=coyote_at_fence` (or whichever scenario triggers the PredatorPatternLearner path).
7. Within ~5 seconds of the scenario completing, the Memory panel's active agent tab (PredatorPatternLearner) should show at least one new row with a HashChip.
8. The new row should briefly flash (CSS animation ~800ms).
9. Click the HashChip — it should copy the full `memver_…` ID to clipboard.
10. Switch to `FenceLineDispatcher` tab — it should show its own feed without cross-contamination.

## Reject conditions

- Panel doesn't render at all.
- Tabs don't switch.
- No rows appear after running a scenario.
- Flash animation is missing or broken.
- Tabs cross-contaminate.
- Build failures or visible console errors.

## Resume signal

Once confirmed, update this file's frontmatter `status: approved` (or
`status: rejected` with notes on each failing step). The phase can then be
formally marked complete.
