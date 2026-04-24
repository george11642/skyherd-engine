# OpenMontage Integration

> **Status:** External tool, AGPL-contained. Hackathon mods cleared its use.
> **Source repo:** github.com/calesthio/OpenMontage (AGPLv3) — NOT vendored here.
> **Local install:** `~/tools/openmontage/` — outside the SkyHerd project tree.

## What it is

OpenMontage is **not a CLI**. It's an instruction-driven blueprint repo for AI coding
assistants (Claude Code / Cursor / Codex). Production runs require a host AI agent
that reads `pipeline_defs/*.yaml` + `skills/pipelines/*/*-director.md` and orchestrates
stage-by-stage with human checkpoints. See OpenMontage's `AGENT_GUIDE.md` (Rule Zero —
"All Production Goes Through a Pipeline").

## How we use it

We use OpenMontage as the **agentic edit director**: it produces an
`edit_decisions.json` artifact (schema v1.0) describing cuts, overlays, audio cues,
and transitions. Our adapter `scripts/openmontage_to_remotion.py` translates that
artifact into Remotion props that our deterministic composition consumes.

**Rendering stays in our codebase.** Remotion is the renderer; OpenMontage decides
editorial shape. The two communicate via a single JSON file.

## License containment

- AGPLv3 source lives at `~/tools/openmontage/`. **NEVER `git add` any of it.**
- The adapter `scripts/openmontage_to_remotion.py` is MIT-original code that talks to
  OpenMontage's *output files only* — it never imports OpenMontage modules.
- Test fixtures at `tests/fixtures/openmontage/` are hand-authored to match the schema.
  No demo files are copied from `~/tools/openmontage/` into our repo.
- The `.planning/research/openmontage-integration-design.md` doc describes patterns
  (no source code).

## Containment grep (CI gate)

```bash
rg "openmontage" /home/george/projects/active/skyherd-engine \
    --glob '!*.md' \
    --glob '!.planning/**' \
    --glob '!docs/edl/**' \
    --glob '!scripts/openmontage_to_remotion.py' \
    --glob '!tests/test_openmontage_edl_ingest.py' \
    --glob '!tests/fixtures/openmontage/**'
# expected: zero matches
```

The allowlist is the intentional touchpoint surface: one adapter, one test, one
fixture dir, one received-EDL dir, plus markdown docs. Anything outside = leakage.

## Pipelines we use

| Pipeline | Used in | Why |
|----------|---------|-----|
| `screen-demo` | Act 3 (1:10–2:05) | Maps cleanly onto our 5-scenario montage of dashboard MP4s |
| `cinematic` | Act 2 (0:20–1:10) | B-roll-led mood pipeline for the market-context arc |
| `hybrid` | Acts 1, 5 | Source footage + designed overlays for hook + close |

Skipped: `talking-head` (no on-camera), `animated-explainer` / `animation` (Remotion
covers this), `avatar-spokesperson` / `localization-dub` / `podcast-repurpose` /
`framework-smoke` (out of scope), `clip-factory` / `documentary-montage` (maybe later).

## Operating model

Phase F runs the OpenMontage host session. Concretely:

1. Open a separate Claude Code window targeted at `~/tools/openmontage/`
2. Provide it with the SkyHerd brief (script, dashboard MP4 inventory, B-roll
   inventory, VO bus locations, hackathon judging criteria)
3. The host agent walks the pipeline stage-by-stage. Human checkpoints required at
   `idea`, `script`, `assets`, `proposal`, `edit-decisions`, `render`.
4. **Render runtime selection:** at the proposal stage, explicitly select
   `remotion`. OpenMontage's AGENT_GUIDE.md *requires* the host agent to present
   both Remotion and HyperFrames; we pick remotion. Anything else triggers our
   adapter's `EdlWrongRuntime`.
5. The artifact lands at
   `~/tools/openmontage-runs/skyherd/<pipeline>/edit_decisions.json`.
6. Copy or stream that file path into our repo via:
   ```bash
   uv run python scripts/openmontage_to_remotion.py \
       ~/tools/openmontage-runs/skyherd/screen-demo/edit_decisions.json \
       docs/edl/openmontage-cuts-act3.json
   ```
7. Remotion composition reads `docs/edl/openmontage-cuts-*.json` during render.

For multi-pipeline merges (cinematic + screen-demo + hybrid), namespace cut IDs
(`act2:cut-3`, `act3:cut-1`, …) and concatenate the Remotion outputs in `Main.tsx`.

## Output contract (what OpenMontage emits)

`edit_decisions` artifact, schema v1.0 (see
`~/tools/openmontage/schemas/artifacts/edit_decisions.schema.json`).

**Required:**
- `version` (always `"1.0"`)
- `cuts[]` with `id`, `source`, `in_seconds`, `out_seconds`
- `render_runtime` (we hard-pin `"remotion"`)

**Optional:**
- `overlays[]` (kinetic typography, lower-thirds, callouts)
- `audio.{narration,music,sfx}`
- `subtitles`
- `transitions[]`
- `renderer_family`
- `slideshow_risk_score`
- `metadata`

Schema quirks observed in real outputs:
- Top-level `theme` key (extension)
- `cuts[].source == ""` for synthetic-scene flows (drawn entirely in Remotion)
- `cuts[].type` = `hero_title`, `stat_card`, `bar_chart`, etc — Remotion scene
  selector hint, schema-extra
- `overlays[].position` may be missing for centered overlays

## Disclosure

`docs/SUBMISSION.md` and `docs/ATTESTATION.md` both name OpenMontage as an external
tool with hackathon-mod approval. The artifact in our repo is our composition driven
by its decisions; OpenMontage's source is not in this repo.
