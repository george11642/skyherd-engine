# Before screenshots — static analysis baseline

Runtime screenshot capture requires a running dashboard (`make dashboard`) plus
a browser automation tool. In this environment we captured the "before" state
via source inspection (see Phase 10 CONTEXT.md "Translation" section for the
documented pre-change issues):

## Known rendering issues at baseline

1. **Cow dots are indistinguishable**: all cow dots rendered at ~0.8-1.0% of
   canvas width (2.5px floor). No label, no tag, no tooltip. At 12 cows it
   looked like sparse noise on the map, not a herd.

2. **Drone label collision**: drone triangle rendered near (0.5, 0.5) with
   the "DRONE" text label rendered at `dx + dSize + 4`. The EAST paddock
   label starts at `px(0.5) + 6, py(0.5) + 15`. On a 16:9 canvas these text
   baselines overlap at center.

3. **Paddock labels in top-left of each quadrant**: NORTH at (0+6, 0+15);
   SOUTH at (W/2+6, 0+15); WEST at (0+6, H/2+15); EAST at (W/2+6, H/2+15).
   The EAST label is precisely where the drone spawns.

4. **No information hierarchy on the right rail**: Memory + Attestation +
   VetIntake + CrossRanch all stacked vertically, each collapsible
   independently. All expanded = right rail overflow; all collapsed = dead
   space. No primary signal.

5. **Scenario strip is decorative only**: no legend, no "what am I looking at
   right now" micro-copy for the non-rancher judge.

6. **No livestock health surfaced**: bcs scores, state, tags all in SSE
   payload but none rendered.

## File references

- `web/src/components/RanchMap.tsx:246-256` — cow render (dot only, no label)
- `web/src/components/RanchMap.tsx:190-195` — paddock labels (origin corner)
- `web/src/components/RanchMap.tsx:302-306` — drone label collision site
- `web/src/App.tsx:45-78` — right-rail 4-panel stack
