# Phase 2: Vision Pixel Inference - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

The pinkeye disease head performs real pixel-level inference on rendered PNG frames using an MIT/BSD-licensed backbone, sharing the `DiseaseHead` ABC with the other 6 rule-based heads. This protects narrative credibility with judges — TARA ($5k Keep Thinking) won with vision loop on a hard domain, and if SkyHerd's "7 disease detection heads" are threshold classifiers on `Cow.ocular_discharge`, that claim collapses on inspection.

Requirements: VIS-01, VIS-02, VIS-03, VIS-04, VIS-05.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices at Claude's discretion — discuss skipped per `workflow.skip_discuss=true` (George: "do full milestone one fully autonomously"). George re-enabled research + patterns after initial run; researcher will propose MIT/BSD-licensed backbone (MegaDetector V6 crop → small classifier head OR distilled CNN on rendered frames) and planner will finalize.

### Known Constraints from Audit
- Current vision heads (`src/skyherd/vision/heads/*.py`) are rule engines on `Cow` struct fields — NOT pixel inference
- `src/skyherd/vision/renderer.py` generates synthetic PNG frames via PIL — the pixel source exists, just not consumed
- `src/skyherd/vision/pipeline.py::ClassifyPipeline.run()` output format (list of `DetectionResult`) must NOT change — other 6 heads keep working
- `src/skyherd/vision/heads/base.py::DiseaseHead` ABC must stay — pixel head subclasses it
- MIT/BSD licenses ONLY — no Ultralytics (AGPL) in dep tree
- <500ms/frame CPU baseline; sim must still run ≥2× real time
- Sick-cow scenario dashboard panel must display real bounding box + confidence (not mocked)
- `supervision` (38k-star MIT) is already allowed for tracking/zones/annotations

</decisions>

<code_context>
## Existing Code Insights

See `.planning/codebase/ARCHITECTURE.md` §Layer 2 and `.planning/codebase/CONCERNS.md` §1 for the 7-head rule-engine audit.

Key files:
- `src/skyherd/vision/heads/pinkeye.py` — the target (most visually obvious for demo)
- `src/skyherd/vision/heads/base.py` — `DiseaseHead` ABC
- `src/skyherd/vision/renderer.py` — PNG frame generator (consumer of this phase)
- `src/skyherd/vision/pipeline.py` — orchestration
- `src/skyherd/vision/registry.py` — dispatches to heads
- `src/skyherd/vision/result.py` — `DetectionResult` dataclass (unchanged by this phase)
- `src/skyherd/edge/detector.py` — MegaDetector already imported for Pi edge tier

</code_context>

<specifics>
## Specific Ideas

- Research should surface: MegaDetector V6 (MIT, PyTorchWildlife) as animal crop → small task-specific head on eye region OR distilled CNN directly on full rendered frame
- Consider `supervision` for bounding-box annotation in the sick-cow scenario dashboard overlay
- Test strategy: render known-positive and known-negative frames, assert pixel head produces expected detections; benchmark inference time under load
- The pinkeye head is chosen over other 6 because ocular discharge is visually obvious and the sick-cow scenario is a likely demo segment

</specifics>

<deferred>
## Deferred Ideas

- Replacing all 7 heads with pixel inference — explicitly out of scope per PROJECT.md (one head proves the capability without slowing the sim)
- Training a custom CNN — only if a pre-trained MIT-licensed model fits the task
- Real-time video inference (vs frame-by-frame) — scope creep
- Pi edge live-camera pixel inference — Phase H1+H2 (hardware milestone) concern, not this phase

</deferred>
