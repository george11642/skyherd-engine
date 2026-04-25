# v5 Per-Scene Diagnostic

> Source: Opus 4.7 vision scoring @ 2fps over 6 scene windows of `out/final/skyherd-C-v4.mastered.mp4`.
> Run: Wave 0, `--variant C --iter 99`, `scripts/score_stills_opus.py`.
> Total cost: $3.91 across 6 windows (234 stills, 17 batches).

---

## TraditionalWay (frames 540–1050, 18s–35s)
**Scores (median):** Impact 7.8 / Demo 6.5 / Opus 3.0 / Depth 5.0

**Top fix suggestions:**
1. Add a quantified loss stat overlay on the "All missed." beat (e.g. "$12K/yr in missed events") @ `remotion-video/src/components/diagrams/TraditionalWay.tsx`
2. Stagger MISSED event flags so each fires at its real time-of-day (coyote 3am, sick cow noon, tank midnight) with a red pulse @ `remotion-video/src/components/diagrams/TraditionalWay.tsx`
3. Add a full-map red vignette pulse (200ms) when each MISSED event fires @ `remotion-video/src/components/diagrams/TraditionalWay.tsx`

**Critical flags:**
- None (all flags MEDIUM severity)
- f0001.jpg: Dark/dimmed fade-in overlay stalls the opening; full content not visible until ~1s in
- f0024.jpg: Window ends on "All missed." with no quantified economic stake shown

**Summary:** Strongest impact/demo in the problem-area windows. Main gap is no dollar figure on the missed events, and the truck animation timing doesn't sync event fires to realistic time-of-day. Opus score (3.0) is low because the architecture isn't mentioned here — expected.

---

## NervousSystemStack (frames 1050–1560, 35s–52s)
**Scores (median):** Impact 7.2 / Demo 6.8 / Opus 8.0 / Depth 7.8

**Top fix suggestions:**
1. Increase agent node label font size by ~40% and center the agent row; add connecting lines between active agents @ `remotion-video/src/components/diagrams/NervousSystemStack.tsx`
2. Prepend a 2-3s problem-stakes beat before the architecture diagram with a bold stat overlay @ `remotion-video/src/components/diagrams/NervousSystemStack.tsx`
3. Increase font size of layer labels by ~30% — currently too small to read at 1080p on first viewing @ `remotion-video/src/acts/v2/CActs.tsx`

**Critical flags:**
- None (all flags MEDIUM severity)
- f0001.jpg: Heavily greyed/dimmed state on first frame looks unfinished; full diagram not visible until ~0.5s in
- f0002.jpg: Large empty whitespace below Sensors block for ~1s; pacing is slow

**Summary:** Best Opus and Depth scores of all 6 windows — the five-agent architecture reads well. Font size and entry animation are the primary fixable gaps. The 8.0 Opus score confirms the mesh is landing.

---

## ScenarioGrid (frames 2760–3300, 92s–110s)
**Scores (median):** Impact 6.5 / Demo 6.8 / Opus 5.5 / Depth 6.2

**Top fix suggestions:**
1. Fix gray background flash on entry — ensure cream background (#F5EFE0) is set before first frame renders @ `remotion-video/src/components/diagrams/ScenarioGrid.tsx`
2. Populate Storm card body with action text ("Herd moved to lee pasture") and metadata footer @ `remotion-video/src/components/diagrams/ScenarioGrid.tsx`
3. Add a persistent small badge ("Powered by Opus 4.7 · 5-agent mesh") in corner of grid @ `remotion-video/src/components/diagrams/ScenarioGrid.tsx`

**Critical flags:**
- None (all flags HIGH/MEDIUM severity)
- f0001.jpg [HIGH]: Flat gray/desaturated background on first frame — jarring color discontinuity from previous scene
- f0007.jpg [MEDIUM]: "Drone flies the leak" body text is grammatically incomplete — should be "Drone inspects the leak"

**Summary:** Mid-range scores across all dimensions. Gray flash on entry is the most distracting visual defect. Card bodies need text content (some show as loading skeletons). Tile sizes are confirmed undersized — aligns with user feedback.

---

## SoftwareMVPBlocks (frames 3300–3900, 110s–130s)
**Scores (median):** Impact 6.0 / Demo 5.2 / Opus 3.8 / Depth 6.5

**Top fix suggestions:**
1. Populate the four MVP card bodies with actual screenshots/mockups: web dashboard → ranch map UI, iOS/Android → rancher app mockup, Simulator → replay console @ `remotion-video/src/components/diagrams/SoftwareMVPBlocks.tsx`
2. Add 5th card for Voice-AI Rancher (Wes) with incoming-call animation — currently absent from the grid @ `remotion-video/src/components/diagrams/SoftwareMVPBlocks.tsx`
3. Bottom sub-line type size is too small to read at 1080p; increase by at least 50% @ `remotion-video/src/components/diagrams/SoftwareMVPBlocks.tsx`

**Critical flags:**
- None (all CRITICAL flags triggered at entry beat before diagrams appear — expected)
- f0001.jpg [HIGH]: Opening frame nearly empty grey background — wastes the critical first impression
- f0013.jpg [HIGH]: All four MVP card bodies are empty (labels only, no body content, no screenshots)

**Summary:** Demo score of 5.2 is the lowest among the 6 windows — empty card bodies are the root cause. Platform cards with no screenshots read as mockups to judges. The 5th card (Voice-AI Rancher) is confirmed absent. Text at bottom is confirmed too small.

---

## VisionTimeline (frames 3900–4560, 130s–152s)
**Scores (median):** Impact 6.5 / Demo 4.2 / Opus 2.8 / Depth 4.8

**Top fix suggestions:**
1. Fix gray-background flash on first frame — ensure cream background is rendered before milestone nodes appear @ `remotion-video/src/components/diagrams/VisionTimeline.tsx`
2. Add staggered fade-in + scale animation for each milestone node (Today → 6mo → 1yr → 5yr) — currently all appear simultaneously with no reveal @ `remotion-video/src/components/diagrams/VisionTimeline.tsx`
3. Add momentum to the timeline: pulse dot on TODAY, draw the connecting line left-to-right, then reveal each future milestone with a 0.5s delay @ `remotion-video/src/components/diagrams/VisionTimeline.tsx`

**Critical flags:**
- f0001.jpg [CRITICAL]: Muddy gray background on first frame — looks like a render bug or unstyled component
- f0025.jpg [CRITICAL]: All 12 frames in a 6-second window are visually identical — completely static content, no animation whatsoever

**Summary:** Lowest Demo (4.2) and Opus (2.8) scores. The CRITICAL static-content flag confirms the user's "too simple" call — the component literally has no animation running during this window. The gray flash on entry compounds it. SVG milestone illustrations and staggered reveal are the highest-impact fixes.

---

## AIBodyClose (frames 4560–5250, 152s–175s)
**Scores (median):** Impact 3.5 / Demo 2.0 / Opus 3.2 / Depth 2.0

**Top fix suggestions:**
1. Swap starry-sky/drone-thermal b-roll → arid mountain footage (`broll/t1-drone-arid-mountains.mp4`) immediately — current asset has no ranch relevance @ `remotion-video/src/components/diagrams/AIBodyClose.tsx`
2. Overlay SVG diagram on mountain b-roll: concentric sensor-radius rings + agent-node dots scattered across landscape communicating "AI woven into the world" @ `remotion-video/src/components/diagrams/AIBodyClose.tsx`
3. Ensure wordmark appears OVER held mountain footage (no cross-fade to a different asset at the end) — kill the 1-second tail cut @ `remotion-video/src/components/diagrams/AIBodyClose.tsx`

**Critical flags:**
- f0001.jpg [CRITICAL]: Generic starry-sky stock b-roll with zero SkyHerd branding or problem statement — judges may think they're in a different video
- f0013.jpg [CRITICAL]: No text, captions, or branding visible at 6s — complete information vacuum
- f0024.jpg [CRITICAL]: 6+ seconds of ambient b-roll with zero information density — worst Opus utilization of any window

**Summary:** Lowest scores of all 6 windows (Demo 2.0, Depth 2.0). The wrong b-roll asset is confirmed as the root cause — the starry/thermal footage signals zero ranch context to judges. Three CRITICAL flags are all b-roll related. Swapping to mountain footage and adding SVG overlay will have the highest single-component score impact in v5.
