# After — verified behavior (static + test harness)

## Rendering changes verified via source diff and test suite

### 1. Livestock visualization — fixed

**Before:** cow dots rendered with no distinction beyond sage/dust/danger stripe
on `bcs < 4 || state === "resting"` (RanchMap.tsx:91-96 old).

**After:** `classifyCow()` pure function with 4 states:
- `healthy` (sage  #94b088) — bcs ≥ 4, not resting/sick/calving
- `watch`   (dust  #d2b28a) — bcs 3–4 or state = resting
- `sick`    (salmon #e0645a) — bcs < 3 or state = sick
- `calving` (sky   #78b4dc) — state = calving or labor

Non-healthy cows get:
- 2.2× radius health ring (half-alpha stroke)
- Tag label rendered next to the dot (e.g., `T007`)

Bottom-right corner always shows a live legend with 4 color dots + counts +
total head. Picks up on the existing `cows[].tag` in the mock snapshot
(server/events.py:55–64).

### 2. Layout collision — fixed

**Before:** `EAST` paddock label rendered at `(px(0.5)+6, py(0.5)+15)`, which
is exactly where the drone spawns and draws its `DRONE` label at
`(dx + dSize + 4, dy + 4)`. Every frame these two text rects overlapped at
center-ish.

**After:**
- Paddock labels are now anchored to the OUTSIDE corner of each quadrant
  (NORTH/W → top-left, NORTH/E → top-right, SOUTH/W → bottom-left, SOUTH/E
  → bottom-right) via `paddockLabelAnchor()`. EAST label now lives at the
  bottom-right of the canvas, ~300px from the drone.
- Paddock labels get a translucent background pill so they stay legible
  against terrain.
- Drone label uses `droneLabelOffset()` — picks left/right based on which
  side is farther from center, and flips above/below based on vertical
  half, so it's always readable and never overlaps paddock anchors.
- Drone label also gets a background pill.
- Predator species labels get the same background-pill treatment.
- Forage % bar suppressed on bottom-row paddocks (their ID labels now sit
  where the bar used to be).

### 3. Information hierarchy — redesigned

**Before:** right rail was 4 panels stacked vertically (Memory, Attestation,
VetIntake, CrossRanch) each with its own collapse toggle. When all 4 were
expanded the content overflowed; when all collapsed the rail was empty.

**After:**
- New `RightRailAccordion` component: single-tab-expanded pattern with a
  tab header. One panel visible at a time.
- Tabs: Memory / Attestation / Vet Intake / Cross-Ranch.
- Each tab has a "new activity" badge that increments when the relevant
  SSE event fires (`memory.written`, `attest.append`, `vet_intake.drafted`,
  `neighbor.handoff` / `neighbor.alert`) and resets to 0 when the user
  opens that tab.
- Layout columns reshuffled: map 58%, agent mesh + cost ticker 22%, right
  rail 20% (was 60/40 with the right side carrying everything).

### 4. Animations polish — added

- Scenario-active glow on the matching paddock (coyote → NORTH, water_drop
  → NORTH, sick_cow → EAST, calving → WEST, storm → SOUTH). Breath-pulse
  ~1.3 Hz sine.
- Drone trail widens as it approaches current position (1.5 → 2.3 px line
  width) — gives motion a direction instead of uniform fade.
- Predator threat ring still RAF-driven (preserved from baseline).

### 5. Accessibility — added

- New `KeyboardHelp` component: `?` anywhere opens a shortcut overlay, Esc
  closes, click-outside dismisses, floating `?` button bottom-right for
  discoverability. ARIA dialog semantics + labeled landmarks.
- RightRailAccordion uses ARIA tablist / tab / tabpanel + keyboard nav
  (ArrowLeft/Right/Up/Down, Home, End).
- Updated RanchMap aria-label with all visualized layers enumerated.
- All 4 cow colors preserve brightness + hue differences (colorblind-safe
  triple: sage-green / warm-dust / salmon / sky-blue).
- Weather/legend overlays have 0.78 alpha BG + 0.3 alpha border for WCAG
  contrast against both day and night terrain.

### 6. Test coverage — added

| Test file | Count | What it covers |
|-----------|-------|----------------|
| `RightRailAccordion.test.tsx` | 10 | initial tab, click switch, badge rendering, arrow/home/end keyboard nav, wrap-around, empty tabs, onTabChange |
| `KeyboardHelp.test.tsx`       | 9  | open/close via keyboard (?) + button + backdrop, ignore ? when input focused, Esc closes, dialog body click does NOT close |
| `RanchMap.test.tsx` additions | 9+2 | classifyCow 9 cases (healthy/sick/calving/labor/thin/resting/missing-bcs/state-override), scenario.active subscriptions, safe handling of all 5 known scenario ids + undefined |

Total: 92 → 122 (+30) passing.

### 7. Bundle — under budget

- Before: 70.90 kB gzip (`index-K3D_wHbf.js`)
- After:  72.88 kB gzip (`index-C5ksRwkV.js`)
- Budget: 90 kB  →  **17.1 kB headroom**

### 8. Determinism — preserved

Only web UI changed. `make demo SEED=42 SCENARIO=all` path runs
`skyherd-demo play all --seed $SEED` which never imports anything from
`web/`. Byte-identical replay preserved by construction.

## File refs

- `web/src/components/RanchMap.tsx` (rewritten, Phase 10 treatment)
- `web/src/components/shared/RightRailAccordion.tsx` (new)
- `web/src/components/shared/KeyboardHelp.tsx` (new)
- `web/src/App.tsx` (refactored to use accordion + keyboard help)
- `web/src/components/RanchMap.test.tsx` (added classifyCow + scenario tests)
- `web/src/components/shared/RightRailAccordion.test.tsx` (new)
- `web/src/components/shared/KeyboardHelp.test.tsx` (new)
