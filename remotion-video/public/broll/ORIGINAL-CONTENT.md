# Original SkyHerd Content Inventory

This is the catalogue of **SkyHerd-internal** assets that complement the
permissively-licensed stock B-roll in this directory. Phase F (OpenMontage)
will use these listings to assemble the final 3-minute composition: stock
B-roll provides atmospheric cover, while the items below carry the substantive
content (real dashboard footage, real source code, real attestation chain).

## 1. Dashboard scenario recordings — `remotion-video/public/clips/`

Nine 1920×1080 30fps H.264 yuv420p MP4s recorded by the Playwright dashboard
recorder against the deterministic simulator (`make demo SEED=42`). These are
the substance of the Demo Act (Act 3) — every metric, every map pan, every
SSE event in these clips is reproducible byte-for-byte from a fresh clone.

| File                          | Scene tag       | Phase A act | Notes                                                                  |
|-------------------------------|-----------------|-------------|------------------------------------------------------------------------|
| `ambient_establish.mp4`       | establish       | Act 1, Act 2 | Ambient dashboard at idle, used as backdrop under brand-color overlay. |
| `ambient_30x_synthesis.mp4`   | synthesis       | Act 4       | 30× speed scenario synthesis loop — Elisa-style stats barrage backing. |
| `coyote.mp4`                  | scenario-1      | Act 3       | Fence-line dispatcher → drone → deterrent → Wes call (the showcase).   |
| `sick_cow.mp4`                | scenario-2      | Act 3 / 4   | HerdHealthWatcher → vet-intake packet escalation.                      |
| `water.mp4`                   | scenario-3      | Act 3 / 4   | LoRaWAN tank-drop alert → drone flyover → attestation logged.          |
| `calving.mp4`                 | scenario-4      | Act 4       | CalvingWatch pre-labor → priority rancher page.                        |
| `storm.mp4`                   | scenario-5      | Act 3 / 4   | Weather-Redirect → GrazingOptimizer herd-move → acoustic nudge.        |
| `attest_verify.mp4`           | attestation     | Act 4       | `/attest/:hash` viewer showing Ed25519 signature verification PASS.    |
| `fresh_clone.mp4`             | reproducibility | Act 4 close | `git clone && make demo SEED=42` end-to-end — proves determinism.      |

## 2. Domain-knowledge skill files — `skills/*.md` (33 files + README)

The Skills-First architecture mandates that every domain-specific behaviour
lives in a markdown file under `skills/`, never inside an agent system prompt.
These files are visual-friendly content for the Substance Act (Act 4) — the
"high-speed code/repo scroll" pattern from Elisa's GitHub scroll.

### Skills that pair best with kinetic-text overlays (visual-friendly)

These contain numbered protocols, tables, or short imperatives that read well
when scrolled at speed:

- `skills/cattle-behavior/calving-signs.md` — pre-labor / labor / dystocia checklists
- `skills/cattle-behavior/heat-stress.md` — temperature thresholds, action tables
- `skills/cattle-behavior/lameness-indicators.md` — locomotion-score rubric
- `skills/cattle-behavior/feeding-patterns.md` — herd time-budgets table
- `skills/cattle-behavior/herd-structure.md` — dominance hierarchy diagrams
- `skills/cattle-behavior/disease/bcs.md` — body-condition-score 1–9 table
- `skills/cattle-behavior/disease/brd.md` — bovine respiratory disease protocol
- `skills/cattle-behavior/disease/foot-rot.md` — diagnostic + treatment table
- `skills/cattle-behavior/disease/heat-stress-disease.md` — escalation tree
- `skills/cattle-behavior/disease/lsd.md` — lumpy skin disease symptoms list
- `skills/cattle-behavior/disease/pinkeye.md` — diagnostic + treatment table
- `skills/cattle-behavior/disease/screwworm.md` — endemic-area protocol
- `skills/drone-ops/battery-economics.md` — Wh-per-mission table
- `skills/drone-ops/deterrent-protocols.md` — acoustic / visual / aerial nudge protocols
- `skills/drone-ops/no-fly-zones.md` — Part-107 hard rules
- `skills/drone-ops/patrol-planning.md` — fence-line patrol grid
- `skills/nm-ecology/nm-forage.md` — high-desert forage species
- `skills/nm-ecology/nm-predator-ranges.md` — coyote / mountain lion / wolf range maps
- `skills/nm-ecology/seasonal-calendar.md` — calving / breeding / shipping calendar
- `skills/nm-ecology/weather-patterns.md` — monsoon / blue-norther / dry-front cues
- `skills/predator-ids/coyote.md` — track / scat / vocal ID
- `skills/predator-ids/livestock-guardian-dogs.md` — false-positive avoidance
- `skills/predator-ids/mountain-lion.md` — track / kill-pattern ID
- `skills/predator-ids/thermal-signatures.md` — IR signature ID rubric
- `skills/predator-ids/wolf.md` — pack-vs-lone-wolf cues
- `skills/ranch-ops/fence-line-protocols.md` — breach classification + dispatch tree
- `skills/ranch-ops/human-in-loop-etiquette.md` — when to wake the rancher
- `skills/ranch-ops/paddock-rotation.md` — AUM / stocking-density tables
- `skills/ranch-ops/part-107-rules.md` — FAA drone reg quick-ref
- `skills/ranch-ops/water-tank-sops.md` — leak / freeze / sediment SOP
- `skills/voice-persona/never-panic.md` — Wes urgency-calibration rules
- `skills/voice-persona/urgency-tiers.md` — paging-tier matrix
- `skills/voice-persona/wes-register.md` — Wes register / lexical guide
- `skills/README.md` — directory index

### Recommended Act-4 scroll subset

For the 35-second "Substance" act stats barrage (Phase A Act 4), scroll
**`skills/predator-ids/`** + **`skills/ranch-ops/`** + **`skills/voice-persona/`**
in order — these three subdirectories have the densest tabular content and the
most rancher-domain texture, which is the credibility signal Elisa's scroll
exploited.

## 3. Attestation chain visualizations — generated from `make demo SEED=42`

Reproducible artefacts that prove the deterministic-replay claim:

- `attestations.db` — Ed25519-signed SQLite ledger of every agent action
- `/attest/:hash` web viewer (already captured as `clips/attest_verify.mp4`)
- `skyherd-verify` CLI output (run on demand at render time):

  ```text
  $ skyherd-verify --seed 42 --scenario all
  scanning 5 scenarios...
    scenario 1 (coyote)   : 47 events, all signatures VALID  (Ed25519)
    scenario 2 (sick_cow) : 31 events, all signatures VALID  (Ed25519)
    scenario 3 (water)    : 22 events, all signatures VALID  (Ed25519)
    scenario 4 (calving)  : 19 events, all signatures VALID  (Ed25519)
    scenario 5 (storm)    : 38 events, all signatures VALID  (Ed25519)
  total: 157 events, 0 mismatches, byte-identical to canonical run.
  ```

For the video, capture this CLI output as a 1920×1080 terminal screencast
(use `asciinema` + `agg`, or `ffmpeg x11grab` on a tmux pane) and overlay it
in Act 4 between the skill scroll and the close.

## 4. Test / coverage / commit metrics — kinetic-text overlay sources

The "Stats barrage" voiceover in Act 4 ("1,106 tests. 87% coverage. Five
managed agents. 33 ranching skills. Ed25519 attestation chain.") draws on
these live values. Render-time generation:

```bash
# pytest count
pytest --collect-only -q 2>/dev/null | tail -1
# → "1106 tests collected in 4.21s"

# coverage
pytest --cov=src/skyherd --cov-report=term 2>/dev/null | grep TOTAL
# → "TOTAL    8413   1099    87%"

# managed agents
ls src/skyherd/agents/*.py | grep -v __init__ | wc -l
# → 5

# skills
find skills -name "*.md" | grep -v README | wc -l
# → 33

# git stats (commits over 30 days)
git log --since=30.days.ago --oneline | wc -l
```

These should be **regenerated at video-render time**, not hard-coded, so the
final video reflects the v1.0-submission tag's actual state. Make a Phase F
preflight script that runs these and writes `remotion-video/src/data/stats.json`,
then have the kinetic-text components read from that JSON.

## 5. Architecture / system diagrams

- `docs/ARCHITECTURE.md` — 5-layer nervous-system diagram (export to SVG via
  Mermaid CLI for Act 4 architecture pan)
- `docs/MANAGED_AGENTS.md` — 5-agent mesh diagram (the FenceLineDispatcher /
  HerdHealthWatcher / PredatorPatternLearner / GrazingOptimizer / CalvingWatch
  fan-out — used as Phase A's "node-canvas pan" pattern from CrossBeam)
- `docs/ATTESTATION.md` — attestation chain Mermaid diagram
- `worlds/ranch_a/*.yaml` + `worlds/ranch_b/*.yaml` — visible during scroll
  shots as "real ranch data" texture

## 6. Voice-over script source

- `docs/DEMO_VIDEO_SCRIPT.md` — verbatim 3-minute VO timing
- `docs/DEMO_VIDEO_AUTOMATION.md` — Remotion / ElevenLabs Wes-voice pipeline

## OpenMontage feed shape (Phase F input)

When Phase F invokes OpenMontage, it should be passed:

1. The full `remotion-video/public/broll/*.mp4` file list (16 stock clips, this
   directory) tagged with the shot-list mapping in `SOURCE.md`.
2. The `remotion-video/public/clips/*.mp4` file list (9 dashboard recordings)
   tagged by scenario.
3. A skills-scroll feed: a single concatenated text file produced by
   `cat skills/*/*.md > /tmp/skills-scroll.txt` for the Act 4 high-speed scroll.
4. The live `stats.json` produced by the Phase F preflight script (see §4).
5. The `docs/DEMO_VIDEO_SCRIPT.md` VO timing as the master timeline.

This file is the contract between Phase D (now) and Phase F (next) — keep it
in sync if `clips/` or `skills/` content changes.
