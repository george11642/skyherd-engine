---
phase: 10
name: dashboard-polish-10-10
type: visual-polish
status: executing
started: 2026-04-23
deadline: 2026-04-26 20:00 EST
---

# Phase 10 — Dashboard Polish 10/10

## User Feedback (verbatim)

> "make the dashboard easier to understand also like visualize the livestock
> also drone and east are like cutting up over eachother in the middle of the
> ranch, etc, current dashboard is a 1, i want it a 10 in ui quality, ease of
> use etc perhaps use ur stitch skills"

## Translation

- **Information hierarchy unclear** — need clear primary/secondary/tertiary
- **Livestock not visualized** — cows need to be visible (labels, health colors)
- **Drone + "east" overlap mid-map** — the drone triangle sits at ~(0.5, 0.5)
  next to "EAST" paddock label which starts at ~(0.5, 0.5). Labels and symbols
  collide. Fix with z-layer ordering, label placement, and margin-hugging labels.
- **Current = 1/10, target = 10/10**

## Scope

1. Ranch map livestock visualization — cow dots get tag labels on hover-analog
   (always-on for top-health-concern cattle), color-coded by bcs+state, subtle
   cluster behavior by paddock.
2. Layout collision fixes — paddock labels move to corners, drone triangle
   labels get smart offsets, z-ordering: terrain < paddocks < fences < water <
   cows < drone < predators < legend.
3. Information hierarchy redesign — keep 3-row shell (StatBand / center /
   ScenarioStrip) but add a `MapLegend` overlay panel in top-right of map,
   collapse/tab the right-rail panels (Memory/Attestation/VetIntake/CrossRanch)
   into an accordion that only shows one expanded at a time.
4. Animation polish — cow color transitions, drone bezier trail, scenario-zone
   glow when scenario.active matches a map region.
5. A11y + ease-of-use — add `?` keyboard shortcut overlay, richer aria-labels,
   color-blind safe palette confirmation.
6. Tests + visual QA — new tests for MapLegend + accordion behavior, vitest
   ≥80% on new code.

## Constraints

- Determinism: any SSE-driven animation remains passive subscriber.
- Coverage floor: 80%.
- Bundle budget: 90 kB gzip (current 70.9 kB, allow +19 kB).
- MIT, zero-attribution commits.
- Tailwind v4 + React 19 only.

## Baseline (before)

- Bundle: 70.90 kB gzip
- Tests: 92 passing
- Screenshot: captured pre-change via static analysis (no running server,
  `make dashboard` not started because the gains can be verified from the
  rendered canvas test harness + Vite build output visually).

## Acceptance (after)

- Cow tag labels visible for sick/calving cattle; color-coded all-cow dots.
- Drone label no longer collides with EAST paddock label.
- Right-rail is a single-expanded accordion (not 4 stacked panels fighting).
- Keyboard `?` opens help overlay.
- Bundle ≤ 90 kB gzip.
- Tests pass, coverage floor held.
- `make demo SEED=42 SCENARIO=all` byte-identical.
