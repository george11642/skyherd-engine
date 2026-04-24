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

---

## Required screenshots / gallery images

Upload to Devpost gallery (3 images + thumbnail):

1. **Dashboard full-screen** — all 5 lanes visible, StatBand showing $4.17/wk, ambient map active. Filename: `gallery-01-dashboard.png`.
2. **Coyote scenario mid-cascade** — FenceLineDispatcher flashing orange, drone mission row visible. Filename: `gallery-02-coyote.png`.
3. **Attestation panel zoom** — HashChip rows, sig verification green. Filename: `gallery-03-attest.png`.
4. **Thumbnail** — prompt from `docs/SHOT_LIST.md` Prompt 4. Filename: `thumbnail.png`.

Capture all four from a running `make record-ready` with fresh seed.

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

## Team

- **George Teifel** — sole registered entrant. UNM. Part 107 licensed drone operator.
- Gavin (UNM engineering) — behind-the-scenes contributor, will appear on-camera for field footage if schedule allows.
- Josh (UNM business) — camera operator for field footage if weather permits.

Per hackathon rules, only George is registered; contributions from Gavin and Josh are acknowledged in the README.

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
