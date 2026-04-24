# OpenMontage Integration Design (Phase B)

**Date:** 2026-04-24
**Status:** Phase B complete (research + design + adapter scaffold + TDD test suite).
**Phase F operator:** see `docs/OPENMONTAGE_INTEGRATION.md` for the operating model.

## TL;DR

OpenMontage is not a CLI. It's a blueprint repo for AI coding assistants (Claude Code /
Cursor / Codex). Production = a separate Claude Code session targeted at
`~/tools/openmontage/`, walking pipeline_defs/*.yaml + skill/director files
stage-by-stage with human checkpoints. The output is a JSON artifact
(`edit_decisions.json`, schema v1.0) that our adapter
`scripts/openmontage_to_remotion.py` translates into Remotion `<Sequence>` props.

## Architecture

```
                ┌─────────────────────────────┐
                │   ~/tools/openmontage/      │  AGPLv3 — outside our repo
                │   (host Claude Code session)│
                └────────────┬────────────────┘
                             │ writes
                             ▼
            ┌──────────────────────────────────────┐
            │ ~/tools/openmontage-runs/            │  outside our repo
            │   skyherd/<pipeline>/                │
            │     edit_decisions.json              │  ← our only ingest surface
            └────────────┬─────────────────────────┘
                         │ uv run python
                         ▼
   ┌────────────────────────────────────────────────────────┐
   │ scripts/openmontage_to_remotion.py  (MIT, our code)    │
   │   load_edl → validate_edl → to_remotion → write JSON   │
   └────────────┬───────────────────────────────────────────┘
                │
                ▼
   ┌────────────────────────────────────────────────────────┐
   │ docs/edl/openmontage-cuts-<act>.json                   │  in our repo, MIT
   └────────────┬───────────────────────────────────────────┘
                │ static import
                ▼
   ┌────────────────────────────────────────────────────────┐
   │ remotion-video/src/Main.tsx + acts/*.tsx               │  Remotion composer
   └────────────────────────────────────────────────────────┘
```

## Capability triage (12 pipelines)

| Pipeline | Verdict | Why |
|----------|---------|-----|
| `screen-demo` | **YES** (primary, Act 3) | Our 9 dashboard MP4s ARE the source media. Edit-director skill at `skills/pipelines/screen-demo/edit-director.md` codifies pacing rules ("typing accelerated, result moments at normal speed, no cut ends before payoff"). Maps cleanly to our 5-scenario montage. |
| `cinematic` | **YES** (Act 2 story) | B-roll-led mood pipeline; will pick which stock clip lands behind which VO line in the 50s market-context arc. |
| `hybrid` | **YES** (Acts 1+5) | Source footage + designed overlays — fits Hook (metric card + dashboard glimpse) and Close (wordmark + GitHub URL) exactly. |
| `clip-factory` | maybe | Could extract sub-clips from our 9 MP4s for fast cuts. Hold for Phase F decision. |
| `documentary-montage` | maybe | Stock-footage corpus retrieval (Pexels/Archive.org/Wikimedia) could feed Phase D's B-roll fetching. Investigate during Phase F. |
| `talking-head` | NO | Sim-first hardline; no on-camera George. |
| `animated-explainer` | NO | Remotion handles this in our composition. |
| `animation` | NO | Same — Remotion + Lottie. |
| `avatar-spokesperson` | NO | Out of scope. |
| `localization-dub` | NO | English-only. |
| `podcast-repurpose` | NO | Wrong format. |
| `framework-smoke` | NO | Internal OpenMontage QA. |

## Adapter contract

```python
# scripts/openmontage_to_remotion.py
def load_edl(path: pathlib.Path) -> dict
def validate_edl(edl: dict) -> list[str]                      # [] = valid
def to_remotion(edl: dict, *, fps=60, asset_root="public") -> dict   # pure
def main(input_path, output_path, fps=60, asset_root="public") -> int  # CLI

class EdlPathOutsideRepo(ValueError): ...
class EdlWrongRuntime(ValueError): ...
```

### Translation rules

- `fromFrame = round(in_seconds * fps)`, fps locked to 60
- `cuts[].source == ""` → `{"kind": "scene-component"}`, preserve `type` field in metadata
- `cuts[].source` relative path → `{"kind": "asset", "path": <as-is>}`
- `cuts[].source` absolute path inside REPO_ROOT → rewritten to repo-relative
- Absolute path outside REPO_ROOT → raises `EdlPathOutsideRepo`
- Missing `transition_in` → default `"cut"`, 0 frames
- Missing `audio` block → emit empty `{narrationSegments: [], music: null, sfx: []}`
- Cuts out-of-order by `in_seconds` → sort and accept (warn if needed)
- `render_runtime != "remotion"` → raise `EdlWrongRuntime`

### Output shape (RemotionEdl)

```typescript
interface RemotionEdl {
  fps: number
  durationInFrames: number
  sequences: Array<{
    id: string
    fromFrame: number
    durationInFrames: number
    asset: { kind: "scene-component" } | { kind: "asset"; path: string }
    transition: string                 // "cut" | "fade" | "dissolve" | ...
    transitionDurationFrames: number
    metadata: Record<string, unknown>  // type, stat_label, etc.
  }>
  overlays: unknown[]                  // pass-through
  transitions: unknown[]               // pass-through
  audio: {
    narrationSegments: unknown[]       // pass-through from edl.audio.narration
    music: unknown | null
    sfx: unknown[]
  }
  captionEmphasis: unknown | null      // pass-through; consumed by KineticCaptions
  metadata: {
    sourceTool: "openmontage"
    sourceVersion: string | null
    rendererFamily: string | null
    ingestedAt: string                 // ISO-8601
  }
}
```

## TDD test suite (15 cases)

`tests/test_openmontage_edl_ingest.py`:

1. `test_load_edl_reads_json_fixture` — happy path
2. `test_validate_edl_accepts_minimal_valid_doc`
3. `test_validate_edl_rejects_missing_version`
4. `test_validate_edl_rejects_empty_cuts`
5. `test_validate_edl_rejects_wrong_render_runtime` (hyperframes / ffmpeg)
6. `test_to_remotion_converts_seconds_to_frames_at_60fps` — boundary 3.5s → 210f
7. `test_to_remotion_passes_through_synthetic_scene_components`
8. `test_to_remotion_keeps_relative_asset_paths`
9. `test_to_remotion_raises_for_paths_outside_repo`
10. `test_to_remotion_raises_for_wrong_runtime`
11. `test_to_remotion_defaults_missing_transitions_to_cut_zero_frames`
12. `test_to_remotion_sorts_out_of_order_cuts_by_in_seconds`
13. `test_to_remotion_handles_missing_audio_block`
14. `test_to_remotion_preserves_extra_cut_metadata`
15. `test_main_writes_output_json_and_returns_zero_on_success`
16. `test_main_returns_2_on_validation_error`
17. `test_main_returns_1_on_missing_input`

Fixture: `tests/fixtures/openmontage/minimal-edl.json` — hand-authored to match
the schema, no AGPL content imported.

## Phase F operating notes (forward-looking)

1. **OpenMontage isn't a CLI.** Phase F as currently described in the plan
   ("Run OpenMontage's pipelines... OpenMontage produces an EDL/JSON")
   underestimates the orchestration cost. Phase F is a **separate Claude Code agent
   session** running for 1-3 hours against `~/tools/openmontage/` with API keys
   (Anthropic + ElevenLabs + Pexels minimum). Budget impact: ~$3-10 in tokens, real
   human checkpoints at 6-7 stages per pipeline.
2. **Multi-pipeline merge.** Two or three pipelines (cinematic for Acts 1/2/5,
   screen-demo for Act 3) means two or three separate Phase F sessions. Adapter
   must support ID-namespacing on merge — recommend prefix like `act2:cut-3`.
3. **Phase F input format.** OpenMontage's `idea-director` stage produces a
   `brief` artifact via human conversation, not from a pre-written brief.txt.
   Our SkyHerd brief.txt becomes the *seed* for that conversation, not the
   artifact itself.
4. **Render runtime hard rule.** OpenMontage's `AGENT_GUIDE.md` mandates the host
   agent "MUST present BOTH Remotion and HyperFrames options to the user before
   locking render_runtime". The Phase F operator must explicitly pick remotion at
   proposal stage; silent default is forbidden by OpenMontage and would also break
   our adapter (`EdlWrongRuntime`).
5. **No real smoke test ran.** Phase B subagent could not run a host session
   (no Anthropic key in subagent env, ~3hr session needed). The hand-authored
   fixture (`minimal-edl.json`) is structurally representative but lacks the
   tone/asset paths a real SkyHerd run would produce. Phase F's first session is
   the actual smoke test.

## Open questions for Phase F

- Do we run all three pipelines (cinematic / screen-demo / hybrid) or pilot with
  one (screen-demo on Act 3) first to validate the adapter end-to-end?
- How do we feed OpenMontage our Wes-VO/19yo-VO bus? Probably via the `script`
  artifact stage with explicit narration timing.
- Should the hackathon-criteria-coverage rubric be passed to OpenMontage as part
  of the brief so its edit-director optimizes for it?

## References

- OpenMontage repo: `~/tools/openmontage/`
- AGENT_GUIDE: `~/tools/openmontage/AGENT_GUIDE.md` (37KB)
- Pipelines: `~/tools/openmontage/pipeline_defs/*.yaml`
- Skill files: `~/tools/openmontage/skills/pipelines/*/`
- Schema: `~/tools/openmontage/schemas/artifacts/edit_decisions.schema.json`
- Real demo EDL (NOT copied): `~/tools/openmontage/remotion-composer/public/demo-props/world-in-numbers.json`
- Sample stash: `~/tools/openmontage-runs/skyherd-brief-test/sample-edit-decisions.json`
