# SkyHerd Demo Video v2 — Variant A · Winner-Pattern

**Variant strategy:** 3-act Setup/Demo/Close (33% / 50% / 17%) per top-3 4.6 winner skeleton.
**Hook style:** Identity / contrarian punch — "Everyone thinks ranchers need smarter sensors. They don't — they need a nervous system."
**Captions:** Emphasis-only — lower-thirds + kinetic punch-words, **no** word-by-word captions on full VO.
**Voice:** Antoni — `ErXwobaYiN019PkySvjV` — neutral 19yo male, college-student-engineer tone. No swagger, no folksy "Boss," no cowboy-isms.
**Total runtime:** 3:00 ± 1s.

> Pattern source: `.planning/research/winner-top3-analysis.md` cross-cutting patterns 1-7. Highest base-rate odds — every top-3 placer used this skeleton.

---

## Act timing (3-act, winner-skeleton)

```
┌──────── ACT 1 — Setup ──────────────────┐ 0:00 – 1:00  (60 s · 33%)
│ Identity hook · context · founder/      │
│ project credibility · why-this-matters  │
├──────── ACT 2 — Demo ────────────────────┤ 1:00 – 2:30  (90 s · 50%)
│ 5-scenario sim (≤55s) +                  │
│ "under the hood" mesh diagram (35s)      │
├──────── ACT 3 — Close ───────────────────┤ 2:30 – 3:00  (30 s · 17%)
│ Substance signals · close · wordmark     │
└──────────────────────────────────────────┘
```

CrossBeam boundaries (1:07 / 2:32) and PostVisit (1:06 / 2:42) put Setup at ~1:00. We follow that.

---

## ACT 1 — Setup (0:00 – 1:00, 60s)

### 0:00 – 0:08 · Cold open · contrarian punch

**Visual:** Black card. Punch-words pop in one at a time, deep-sage on warm cream gradient (CrossBeam pattern). No music — just open. Fade through to dawn-corral B-roll at 0:06.

**Kinetic punch:**
- 0:01 — "Everyone thinks" (light weight)
- 0:02 — "ranchers need smarter sensors." (light)
- 0:04 — "**They don't.**" (bold, sage emphasis)
- 0:06 — "**They need a nervous system.**" (bold, dust emphasis)

**VO:** *(silent — black card holds the beat. Reads on screen, not voiced.)*

**B-roll cue:** `broll/dawn-corral.mp4` fades in under final punch line at 0:06.

### 0:08 – 0:22 · Identity / project credibility

**Visual:** Continued dawn-corral B-roll, slow zoom-in. Lower-third: "George Teifel · UNM · licensed drone op." Sage accent line.

**VO cue `vo-intro`:**
> "I'm George. I'm a senior at UNM, I've spent a lot of nights on ranches in New Mexico, and I have a Part 107 drone ticket. SkyHerd is my hackathon submission — what came out of asking one question. *(beat)* What if the ranch checked itself?"

*(~13s. Plain, conversational.)*

**Emphasis caption:** *"What if the ranch checked itself?"* — fades in over the final beat, 0:20-0:22.

### 0:22 – 0:50 · Why this exists · market context

**Visual:** Cuts through B-roll: cattle-grazing wide → fence-line silhouette dusk → empty pasture → NM high-desert. Each shot 5-7s, hard cuts. Kinetic typography hero overlays the market data — one number per cut, large, sage on dust.

**VO cue `vo-market`:**
> "Beef is at record highs. The American cow herd is at a sixty-five-year low. Ranches can't hire their way out — labor is gone, and ranchers are aging out of the business. So every existing ranch has to do more, with fewer eyes on it. The herd already has a nervous system. The rancher does not."

*(~26s. Steady, no urgency.)*

**Kinetic typography hero (one per VO beat, holds 4-5s each):**
- 0:24 — "Beef · record highs"
- 0:30 — "Cow herd · 65-yr low"
- 0:36 — "Labor · gone"
- 0:42 — "Eyes · fewer per acre"
- 0:48 — "The herd has a nervous system. *The rancher does not.*"

### 0:50 – 1:00 · Setup → Demo bridge

**Visual:** Hold on the "the rancher does not" line for 1.5s. Cut to dashboard establish — full-screen `clips/ambient_establish.mp4`, slow vertical pan. Wordmark fades in bottom-right.

**VO cue `vo-bridge`:**
> "So we built one. Five Claude Managed Agents, watching one ranch, twenty-four-seven. Four dollars and seventeen cents a week."

*(~8s. Calm, factual. Metric lands here, late, after the problem is set up — opposite of Variant B.)*

**Lower-third:** "SkyHerd · Ranch A · 40,000 acres" — fades in 0:55, sage accent.

---

## ACT 2 — Demo (1:00 – 2:30, 90s)

### 1:00 – 1:55 · Five-scenario sim · ≤55s · ~11s each

Each scenario uses existing `clips/{coyote,sick_cow,water,calving,storm}.mp4`. Cuts overlap by ~1s — N+1 scenario establishes under N's fadeout. Lower-third + AnchorChip per scenario — no full caption.

#### 1:00 – 1:11 · Scenario 1 — Coyote at fence (11s)

**Visual:** Map zooms to SW fence, thermal glyph at 1:01, FenceLineDispatcher lane flashes 1:03, drone telemetry 1:05, AttestationPanel HashChip at 1:08.

**VO cue `vo-coyote`:**
> "Heads up — coyote at the south fence. Drone's en route."

*(~4s. Lands at 1:04 over the agent flash.)*

**Lower-third:** `FenceLineDispatcher · Coyote 91% · Fence W-12 · Mavic dispatched` (sage→thermal accent)
**AnchorChip:** `Attest row · Fence W-12 breach · Ed25519 a7c3…f91e · SIGNED`

#### 1:11 – 1:22 · Scenario 2 — Sick cow (11s)

**Visual:** Map pans to trough 3, A014 highlighted, VetIntakePanel slides in, PixelDetectionChip bbox.

**VO cue `vo-sick-cow`:**
> "Cow A014 — eye irritation, eighty-three percent confidence. Vet packet's on your phone."

*(~6s. Lands at 1:14.)*

**Lower-third:** `HerdHealthWatcher · Cow A014 · pinkeye 83% · Vet packet generated` (warn accent)
**AnchorChip:** `Vet packet · Cow A014 · pinkeye · Ed25519 4d82…b03c · SENT`

#### 1:22 – 1:33 · Scenario 3 — Water tank (11s)

**Visual:** Tank 7 glyph red 1:23, GrazingOptimizer wakes 1:25, drone IR still 1:28, three signed events 1:31.

**VO cue (lower-third only — no spoken VO, music carries):** *(silent)*

**Lower-third:** `GrazingOptimizer · Tank 7 pressure drop · IR flyover scheduled` (sky accent)
**AnchorChip:** `IR flyover · Tank 7 · pressure drop · Ed25519 92e1…5a0d · QUEUED`

#### 1:33 – 1:44 · Scenario 4 — Calving (11s)

**Visual:** CalvingWatch lane activates 1:34, behavior trace draws 1:37, priority page on phone mock 1:41.

**VO cue `vo-calving`:**
> "Cow one-seventeen is going into labor. Pre-labor signals — flagged priority."

*(~5s. Lands at 1:36.)*

**Lower-third:** `CalvingWatch · Cow 117 · pre-labor · Rancher paged (priority)` (sage accent)
**AnchorChip:** `Behavior trace · Cow 117 · pre-labor · Ed25519 61bf…2c94 · PAGED`

#### 1:44 – 1:55 · Scenario 5 — Storm (11s)

**Visual:** Weather overlay 1:45, paddock redirect arrow 1:48, acoustic nudge 1:51, herd animates moving 1:53.

**VO cue `vo-storm`:**
> "Hail in forty-five minutes. Moving the herd to shelter two."

*(~4s. Lands at 1:48.)*

**Lower-third:** `Weather-Redirect · Hail ETA 45 min · Paddock B → Shelter 2` (dust accent)
**AnchorChip:** `Redirect plan · Paddock B → Shelter 2 · Ed25519 d3a9…7e11 · ACTIVE`

### 1:55 – 2:30 · "Under the hood" mesh reveal (35s)

This is the **CrossBeam node-diagram steal** (1:25-1:50 in CrossBeam). Smooth pan across an animated node canvas — not hard cuts. Music holds steady; VO continuous.

**Visual:**
- 1:55 — Cut to dark-mode node canvas. Single sage node at center labeled "Sensor Event."
- 1:58 — Node pulses, fans out to 5 agent nodes (FenceLineDispatcher, HerdHealthWatcher, PredatorPatternLearner, GrazingOptimizer, CalvingWatch). Each labeled.
- 2:05 — Smooth camera pan right. Agent nodes spawn tool nodes (drone, deterrent, vet packet, paddock redirect, priority page). Tool calls animate as edges.
- 2:15 — Pan converges on a center node: `attest.append(hash, sig)`. Pulse outward to a Merkle chain visualization. Counts tick: 360 events, all signed.
- 2:25 — Cost ticker overlay bottom-right: `$4.17/week`. Dust accent.

**VO cue `vo-mesh`:**
> "Each agent runs on its own Managed Agents session. They're idle until a sensor wakes them — and they go right back to idle when the work is done. That's how a ranch this size runs on four dollars a week of Claude. Every tool call gets signed. Every signature lands in a Merkle chain. The whole thing replays from a seed — same input, same bytes, every time."

*(~32s, calm, technical, no jargon dump.)*

**Emphasis caption:** *"Same seed. Same bytes. Every time."* fades in 2:24-2:30.

---

## ACT 3 — Close (2:30 – 3:00, 30s)

### 2:30 – 2:48 · Substance · why-it-matters

**Visual:** Cut to live drone aerial over rangeland (`broll/drone-rangeland.mp4`), warm dust grade. Overlay three text blocks left-aligned, fade in sequentially:

- 2:31 — `1,106 tests · 87% coverage`
- 2:35 — `Ed25519 attestation chain · 360 events`
- 2:39 — `Fresh-clone reproducible · < 3 minutes`

**VO cue `vo-close-substance`:**
> "Eleven-hundred-six tests. Eighty-seven-percent coverage. An Ed25519 attestation chain. Clone the repo, run one command, watch the same five scenarios play out — bit-for-bit."

*(~14s. Confident, not boastful.)*

### 2:48 – 3:00 · Wordmark + sign-off (12s)

**Visual:** Hard cut to brand-color isometric ranch animation (CrossBeam pink-on-green pattern, SkyHerd version: tan/sage isometric corral on saturated sunrise-orange). Wordmark scales up at 2:50. Three lines fade in below.

**VO cue `vo-close-final`:**
> "Beef at record highs. Cow herd at a sixty-five-year low. Now the ranch can watch itself."

*(~9s. Lands the bookend echo of the hook.)*

**Wordmark + lines:**
```
                    SkyHerd

   github.com/george11642/skyherd-engine
   MIT · Python 3.11 · TypeScript 5.8 · Opus 4.7
   1,106 tests · 87% coverage · Ed25519
   George Teifel · UNM · 2026
```

Cut to black at 3:00.

---

## VO cue table (Variant A)

Voice: Antoni `ErXwobaYiN019PkySvjV`. Filename pattern: `vo-*.mp3`.

| Key | File | Duration target | Text |
|-----|------|-----------------|------|
| `vo-intro` | `vo-intro.mp3` | ~13s | "I'm George. I'm a senior at UNM, I've spent a lot of nights on ranches in New Mexico, and I have a Part 107 drone ticket. SkyHerd is my hackathon submission — what came out of asking one question. What if the ranch checked itself?" |
| `vo-market` | `vo-market.mp3` | ~26s | "Beef is at record highs. The American cow herd is at a sixty-five-year low. Ranches can't hire their way out — labor is gone, and ranchers are aging out of the business. So every existing ranch has to do more, with fewer eyes on it. The herd already has a nervous system. The rancher does not." |
| `vo-bridge` | `vo-bridge.mp3` | ~8s | "So we built one. Five Claude Managed Agents, watching one ranch, twenty-four-seven. Four dollars and seventeen cents a week." |
| `vo-coyote` | `vo-coyote.mp3` | ~4s | "Heads up — coyote at the south fence. Drone's en route." |
| `vo-sick-cow` | `vo-sick-cow.mp3` | ~6s | "Cow A014 — eye irritation, eighty-three percent confidence. Vet packet's on your phone." |
| `vo-calving` | `vo-calving.mp3` | ~5s | "Cow one-seventeen is going into labor. Pre-labor signals — flagged priority." |
| `vo-storm` | `vo-storm.mp3` | ~4s | "Hail in forty-five minutes. Moving the herd to shelter two." |
| `vo-mesh` | `vo-mesh.mp3` | ~32s | "Each agent runs on its own Managed Agents session. They're idle until a sensor wakes them — and they go right back to idle when the work is done. That's how a ranch this size runs on four dollars a week of Claude. Every tool call gets signed. Every signature lands in a Merkle chain. The whole thing replays from a seed — same input, same bytes, every time." |
| `vo-close-substance` | `vo-close-substance.mp3` | ~14s | "Eleven-hundred-six tests. Eighty-seven-percent coverage. An Ed25519 attestation chain. Clone the repo, run one command, watch the same five scenarios play out — bit-for-bit." |
| `vo-close-final` | `vo-close-final.mp3` | ~9s | "Beef at record highs. Cow herd at a sixty-five-year low. Now the ranch can watch itself." |

**Sum estimate:** 13+26+8+4+6+5+4+32+14+9 = **121s of VO** across 180s of runtime. That leaves ~59s of silent / SFX-only / music-only beats — concentrated in Act 1 cold open (8s), Act 2 scenario 3 water (11s), and Act 3 isometric close (~12s). Healthy ratio per top-3 winners (CrossBeam ran ~40-50% silent/music-only).

---

## B-roll inventory (referenced — Phase D will source the actual MP4s)

Per `.planning/research/winner-top3-analysis.md` "B-roll shot list refinement" section:

| Slot | Asset | Location used | Source pattern |
|------|-------|---------------|----------------|
| 0:06-0:14 | `broll/dawn-corral.mp4` | Act 1 cold-open transition | PostVisit hospital exterior bookend |
| 0:24-0:30 | `broll/cattle-grazing-wide.mp4` | Act 1 market context | top-3 list #6 |
| 0:30-0:36 | `broll/fence-line-dusk.mp4` | Act 1 market context | top-3 list #3 |
| 0:36-0:42 | `broll/empty-pasture.mp4` | Act 1 market context | top-3 list — labor/depopulation |
| 0:42-0:50 | `broll/nm-high-desert.mp4` | Act 1 market context | top-3 list #5 |
| 1:00-1:55 | `clips/{coyote,sick_cow,water,calving,storm}.mp4` | Act 2 demo (existing) | dashboard recordings |
| 1:55-2:30 | (animated node canvas — built in Remotion, no B-roll) | Act 2 mesh reveal | CrossBeam Opus Orchestrator pattern |
| 2:30-2:48 | `broll/drone-rangeland.mp4` | Act 3 substance | top-3 list #5 + CrossBeam suburban-drone close |
| 2:48-3:00 | (isometric brand animation — built in Remotion) | Act 3 wordmark close | CrossBeam pink isometric bookend |

---

## Hackathon-criteria coverage map

Judging weights: 30% Impact / 25% Demo / 25% Opus 4.7 / 20% Depth.

| Criterion | Where it lands | Beats |
|-----------|---------------|-------|
| **Impact (30%)** | Act 1 (0:22-0:50) market context · Act 3 (2:48-3:00) bookend echo | Beef record highs + 65-yr cow herd low + labor crisis + "the rancher does not" + close echo |
| **Demo (25%)** | Act 2 scenarios 1-5 (1:00-1:55) · AnchorChip Ed25519 hashes legible | All 5 scenarios visible · attestation chips on every cut · Mavic + drone telemetry + vet packet + paddock redirect |
| **Opus 4.7 (25%)** | Act 1 bridge (0:50-1:00) "Five Claude Managed Agents" · Act 2 mesh reveal (1:55-2:30) "each agent on its own Managed Agents session" · animated node canvas | Managed Agents called out by name twice + visualized as expanding agent mesh + idle-pause billing model |
| **Depth (20%)** | Act 2 mesh reveal (Merkle chain pulse 2:15) · Act 3 substance (2:30-2:48) | 1106 tests + 87% coverage + Ed25519 ledger + 360 signed events + fresh-clone repro · "same seed, same bytes" emphasis |

Each criterion gets ≥10s of dedicated screen-time. Each is voiced AND visualized — no "tell don't show" beats.

---

## Production notes (Variant A)

- **Color grade:** warm earth tones throughout. Dawn corral (golden-hour 5500K), dusk fence (3200K), node canvas dark-mode (#08-0A blacks with sage edges). Avoid neon / cyberpunk per top-3 anti-pattern #1.
- **Cuts:** 95% hard cuts. The only smooth pan is the Act 2 node-canvas reveal (1:55-2:30) — that beat copies CrossBeam's continuous-canvas technique.
- **Captions:** Lower-thirds + AnchorChips only on demo. Three emphasis-only kinetic moments: "What if the ranch checked itself?" (0:20), "The rancher does not." (0:48), "Same seed. Same bytes. Every time." (2:24). No word-by-word kinetic captions on full VO — keeps the screen visually quiet, which Gemini scored higher in the top-3 analysis.
- **Music:** Single bed throughout. Holds at base volume, ducks under VO smoothly, holds steady through node-canvas reveal (per CrossBeam metronome pattern).
- **Composition:** Centered everywhere. Lower-thirds anchored to bottom-90px-from-edge. AnchorChips top-right. No rule-of-thirds for talking-head shots (we have no talking heads anyway).
- **Aspect:** 16:9 widescreen, 1080p60.
