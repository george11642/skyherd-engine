# SkyHerd — Devpost Submission Draft

**Hackathon:** Built with Opus 4.7 · Anthropic
**Deadline:** Sun 2026-04-26 20:00 EST (target 18:00 EST)
**Form URL:** `https://devpost.com/submissions/<hackathon-slug>` (fill in on Sun)

---

## Project name

**SkyHerd — the nervous system for working land**

Alternate (shorter, if platform requires ≤40 char):

**SkyHerd**

---

## Tagline (≤140 chars)

> Five Claude Managed Agents keep a ranch alive 24/7 — sensors, drones, vet packets, and signed-chain attestation. $4.17/week to watch 50,000 acres.

(134 chars · fits Devpost + Twitter.)

---

## 100–200 word summary

<!-- word count: 187 -->

SkyHerd is a 5-layer nervous system for American ranches. A cow can be sick
for 72 hours before anyone notices; a coyote can take three calves in a night.
SkyHerd makes the ranch watch itself so ranchers stop losing animals to
oversight.

Five Claude Managed Agents — FenceLineDispatcher, HerdHealthWatcher,
PredatorPatternLearner, GrazingOptimizer, CalvingWatch — share one platform
session each and pause their own billing between events. A 33-file skills
library (CrossBeam pattern) keeps prompts short and cache hits high. Tool
calls emit an Ed25519 Merkle attestation chain that a verifier can audit
offline. One ranch costs roughly $4/week to monitor.

The demo is deterministic: `make demo SEED=42 SCENARIO=all` boots on a fresh
clone in under three minutes and plays five field scenarios — coyote at the
fence, a sick cow flagged, water tank pressure drop, calving, incoming storm —
byte-identically every run. A "Wes" cowboy-persona voice (ElevenLabs + Twilio)
calls the rancher on escalation.

Built on Opus 4.7 with Python 3.11, FastAPI, React 19, Tailwind v4, MAVSDK +
pymavlink, MegaDetector V6. 1,100+ tests. 87% coverage. MIT.

---

## Links

- **YouTube video (unlisted):** `{{YOUTUBE_URL}}` — fill in Sun morning after upload.
- **GitHub repo:** `https://github.com/george11642/skyherd-engine`
- **Live one-pager:** `https://github.com/george11642/skyherd-engine/blob/main/docs/ONE_PAGER.md`

---

## Category selections (3 of 3 prize tracks)

### 1. Best Use of Claude Managed Agents ($5,000)

**Why we qualify:**
- 5-agent mesh, each on its own platform session via the `managed-agents-2026-04-01` beta header.
- Idle-pause billing visible live on the dashboard — cost ticker freezes between events, resumes on wake.
- Each agent uses workspace-scoped memory stores (beta) for cross-session learning (PredatorPatternLearner writes nightly, FenceLineDispatcher reads pre-dispatch).
- Prompt caching on every `sessions.events.send` via `cache_control: ephemeral` on the system + skills prefix.
- `make mesh-smoke` exercises the 5-agent mesh end-to-end in CI.

### 2. Keep Thinking ($5,000)

**Why we qualify:**
- Sessions persist across events: 241-sessions-per-scenario → 5 refactor shipped pre-milestone.
- 33 markdown skill files loaded per task (not per agent) — domain knowledge survives session boundaries.
- Memory beta adoption (Phase 1 milestone) for per-ranch pattern accumulation.
- PredatorPatternLearner literally learns multi-day crossing patterns across sessions.

### 3. Most Creative Opus 4.7 Exploration ($5,000)

**Why we qualify:**
- Ranch + Mavic Air 2 + Wes cowboy-persona voice form a physical, audible loop — not a chat app.
- Idle-pause billing ties agent scheduling to real-world sensor cadence (seconds, hours, days).
- Attestation chain → insurance underwriting is a novel commercial hook for agentic systems.
- Sim-first architecture means the demo runs on any laptop, with hardware as a bonus path.
- **Opus 4.7 directed our caption editorial** — see below.

#### Opus 4.7 directed our caption editorial

faster-whisper transcribes the voice-over for each variant. We then send the
word-level transcript and the variant script to **Claude Opus 4.7** with a
33-file skills library prefix, and Opus emits per-word styling JSON: a
warm-earth-tone color, a font weight, an animation (`fade` / `pop` / `pulse`
/ `scale` / `glow`), and an emphasis level (0–3) reserved for the single most
important word in each segment.

The model isn't just narrating the demo — it's making editorial decisions
about how its own narration is rendered on screen. Examples Opus chose:

- `$4.17 → pop + brick (#C04B2D) + emphasis 3`
- `gone → glow + brick + emphasis 3`
- `Skyherd → pop + brick + emphasis 3`
- `eyes → glow + emphasis 3`
- `wakes → pulse + sage`
- `65-year low → pop / glow + brick`

The styled JSON is committed evidence at:

- `remotion-video/public/captions/styled-captions-A.json` (40 words)
- `remotion-video/public/captions/styled-captions-B.json` (35 words)
- `remotion-video/public/captions/styled-captions-C.json` (249 words)

Each file records the model ID (`claude-opus-4-7`), the input fingerprint
(SHA-256 over captions + script + system prompt), and Anthropic's per-call
usage including `cache_read_input_tokens` so the prompt-caching effect is
auditable. We use `cache_control: ephemeral` on the system prompt and skills
prefix per CLAUDE.md, so variants B and C hit the cache (~6.7K tokens read
per call after the first variant warms it).

The Remotion `KineticCaptions` component reads the styled JSON
preferentially, falling back to the plain Phase E1 captions if the styled
file is missing or malformed (graceful degrade per the plan's risk register).

Pipeline entry point: `make video-style-captions`.

---

## Required screenshots / gallery images

Upload to Devpost gallery (3 images + thumbnail):

1. **Dashboard full-screen** — all 5 lanes visible, StatBand showing $4.17/wk, ambient map active. Filename: `gallery-01-dashboard.png`.
2. **Coyote scenario mid-cascade** — FenceLineDispatcher flashing orange, drone mission row visible. Filename: `gallery-02-coyote.png`.
3. **Attestation panel zoom** — HashChip rows, sig verification green. Filename: `gallery-03-attest.png`.
4. **Thumbnail** — prompt from `docs/SHOT_LIST.md` Prompt 4. Filename: `thumbnail.png`.

Capture all four from a running `make record-ready` with fresh seed.

---

## Hardware path — laptop-primary (2026-04-25 · Phase 7.1)

iOS + Android companion code is feature-complete and tested (880+ tests
including the DJI SDK V5 mock path), but the installed demo uses the
**laptop path** because judges can't install iOS builds without a Mac and
we pivoted away from requiring a phone in the loop. The canonical Friday
demo is: Ubuntu laptop + USB-C data cable + DJI RC + Mavic Air 2, driven
through the MAVSDK-over-USB-C leg of `MavicAdapter` plus the manual-
override `/api/drone/*` endpoints added in Phase 7.1. Full procedure in
[`docs/LAPTOP_DRONE_CONTROL.md`](./LAPTOP_DRONE_CONTROL.md); phone-based
control remains documented as the premium path in
[`docs/HARDWARE_H3_RUNBOOK.md`](./HARDWARE_H3_RUNBOOK.md) §9.

---

## Tech stack (for Devpost tags)

`python` `typescript` `react` `fastapi` `claude-sdk` `anthropic` `tailwind`
`mavsdk` `pymavlink` `mqtt` `edge-ai` `mega-detector` `ed25519` `elevenlabs`
`twilio` `raspberry-pi` `dji` `agentic-ai` `managed-agents` `opus-4`

---

## License

MIT. All source under `/src`, `/web`, `/hardware`, `/android`, `/ios` is MIT.
No AGPL dependencies; vision uses MegaDetector V6 (Apache 2.0 / MIT). Attribution
file: `LICENSE`.

---

## External tools used

### OpenMontage (AGPLv3, external editorial director)

We used OpenMontage (github.com/calesthio/OpenMontage, AGPLv3) as an external
agentic edit director, with explicit clearance from hackathon moderators.
OpenMontage's source lives at `~/tools/openmontage/` — outside our MIT repo —
and we never imported its code. Our `scripts/openmontage_to_remotion.py`
adapter ingests its `edit_decisions.json` outputs (committed at
`docs/edl/openmontage-cuts-*.json`) and translates them to Remotion props.
The adapter and tests are MIT-original code.

Two pipelines were applied per variant: `cinematic` (Acts 1, 2, 5 — B-roll-led
story arc, mesh-reveal, substance close) and `screen-demo` (Act 3 — dashboard
scenario montage). The resulting 6 EDLs are committed at
`docs/edl/openmontage-cuts-{A,B,C}-{cinematic,screen-demo}.json` as evidence
of the editorial decisions, alongside their adapter-translated Remotion props
at `docs/edl/remotion-props-{A,B,C}-{cinematic,screen-demo}.json`.

A repo-wide containment grep (`docs/OPENMONTAGE_INTEGRATION.md` §"Containment
grep") enforces that no AGPL OpenMontage source ever lands in this MIT tree;
the only allowlisted touchpoints are the adapter, its test, fixtures, the
EDL artifact directory, and markdown disclosures.

---

## Team

- **George Teifel** — sole entrant, sole builder. UNM. Part 107 licensed drone operator.

---

## Submission-day checklist

Run through this sequence on 2026-04-26 starting at 14:00 EST (4 hours pre-deadline):

- [ ] Final video exported: `~/Downloads/skyherd-submission-final.mp4` (≤500 MB, 1080p60 H.264).
- [ ] Upload to YouTube as **unlisted**. Copy URL.
- [ ] Paste URL into this file (replace `{{YOUTUBE_URL}}`).
- [ ] Paste URL into `docs/LINKEDIN_LAUNCH.md`.
- [ ] Paste URL into `docs/YOUTUBE.md`.
- [ ] `git commit -am "docs: fill YouTube URL across submission docs"`.
- [ ] `git push origin main`.
- [ ] `git tag v1.0-submission && git push origin v1.0-submission`.
- [ ] Open Devpost form.
- [ ] Fill project name, tagline, summary (copy from this doc).
- [ ] Upload 4 gallery images from the `docs/screenshots/` folder.
- [ ] Paste YouTube URL, GitHub URL.
- [ ] Check 3 prize-category boxes.
- [ ] Tech stack tags.
- [ ] Submit — target 18:00 EST (2-hour buffer to 20:00 EST deadline).
- [ ] Screenshot Devpost confirmation page → save to `docs/screenshots/submission-confirmation.png`.
- [ ] Post LinkedIn launch per `docs/LINKEDIN_LAUNCH.md` only after George approval.

---

## Fallback if YouTube upload stalls

If processing takes > 30 min:
- Submit Devpost with a **temporary note**: "Video processing — final URL in <repo>/docs/SUBMISSION.md commit `{{SHA}}`."
- Upload to a backup host (Vimeo private link) and paste that URL as secondary.
- Keep retrying YouTube; update Devpost as soon as final URL is available.

Devpost allows URL edits post-submission as long as it's before the deadline.
