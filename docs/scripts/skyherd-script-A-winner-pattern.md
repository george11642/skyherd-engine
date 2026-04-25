# SkyHerd Demo Video v2 — Variant A · Winner-Pattern (iter2 humanized)

**Variant strategy:** 3-act Setup / Demo / Close. Phase H iter2 restructure: one deep scenario (coyote), four others as rapid montage, explicit traditional-vs-SkyHerd comparison beat, explicit "Opus 4.7" name-drop.
**Hook style:** Contrarian punch, humanized. "Everyone thinks ranchers need smarter sensors. They don't. They need a nervous system. So I built one."
**Captions:** Emphasis-only — lower-thirds + kinetic punch. No word-by-word on full VO.
**Voice:** See `scripts/render_vo_phase1.sh` — swapped off Antoni to a more natural conversational male voice for iter2. Model: `eleven_v3` if available, fallback `eleven_turbo_v2_5`.
**Total runtime:** 3:00 ± 1s.

> iter1 Gemini note: "too clinical, too press-release." iter2 fix: rewrite every VO line the way you'd tell a buddy over a beer. Drop the em-dashes. Add real-person filler. Vary sentence length wildly.

---

## Act timing

```
┌──────── ACT 1 — Setup ──────────────────┐ 0:00 – 1:00  (60 s · 33%)
│ Contrarian hook · who I am · why it     │
│ matters · traditional-vs-SkyHerd beat   │
├──────── ACT 2 — Demo ────────────────────┤ 1:00 – 2:30  (90 s · 50%)
│ Deep coyote scenario (25s) +            │
│ 4-scenario montage (25s) +              │
│ mesh reveal + Opus 4.7 (40s)            │
├──────── ACT 3 — Close ───────────────────┤ 2:30 – 3:00  (30 s · 17%)
│ Substance · close · wordmark            │
└──────────────────────────────────────────┘
```

---

## ACT 1 — Setup (0:00 – 1:00, 60s)

### 0:00 – 0:08 · Cold open · contrarian punch (no VO)

**Visual:** Black card. Punch-words pop in one at a time, deep-sage on warm cream. No music. Fade through to dawn-corral B-roll at 0:06.

**Kinetic punch:**
- 0:01 — "Everyone thinks"
- 0:02 — "ranchers need smarter sensors."
- 0:04 — "**They don't.**"
- 0:06 — "**They need a nervous system.**"

**VO:** silent.

### 0:08 – 0:22 · Who I am (intro VO, ~13s)

**Visual:** Dawn-corral B-roll, slow zoom. Lower-third: "George Teifel · UNM · Part 107."

**VO cue `vo-intro`:**
> "I'm George. Senior at UNM. Part 107 drone ticket. I've spent a lot of nights on ranches in New Mexico. And one question kept coming up. What if the ranch just watched itself?"

**Notes for delivery:** conversational, a little tired, like you've actually been out there. The word "ranch" leans in. Tiny beat before the question.

**Emphasis caption:** *"What if the ranch just watched itself?"* — fades in 0:20-0:22.

### 0:22 – 0:42 · Market context (~20s)

**Visual:** Hard cuts: cattle-grazing wide → fence-line dusk → empty pasture → NM high-desert. One number per cut, large sage-on-dust overlays.

**VO cue `vo-market`:**
> "Beef is at record highs. The American cow herd's at a sixty-five-year low. Labor's gone. Ranchers are aging out. Every ranch left has to do more, with fewer eyes on it. The herd already has a nervous system. The rancher doesn't."

**Kinetic typography hero (one per VO beat):**
- 0:24 — "Beef · record highs"
- 0:28 — "Cow herd · 65-yr low"
- 0:32 — "Labor · gone"
- 0:36 — "Eyes · fewer per acre"
- 0:40 — "The herd has a nervous system. *The rancher doesn't.*"

### 0:42 – 1:00 · Traditional vs SkyHerd (~18s) — NEW

**Visual:** Split-screen. Left column: "Traditional." Dust-grade footage of rancher in pickup, cattle from a truck window, sunrise over a dirt road. Right column: "SkyHerd." Dark-mode dashboard map glow, agent lanes pulsing, cost ticker.

**VO cue `vo-compare`:**
> "Here's how it works today. A rancher drives two hundred miles a week, checks every trough, every fence, every sick cow. Best case: six runs a day. Anything between runs, you miss. Now. Same ranch. Five Claude Managed Agents — built on Opus 4.7. They watch every fence, every trough, every cow. Every minute. Four dollars and seventeen cents a week."

**Notes:** the "Now." hits hard. Quarter-second beat after. Then the list. "Every minute" lands cold. The number lands colder.

**Overlays:**
- 0:43 — Left: "Rancher · 6 runs/day · 200 mi/week"
- 0:46 — Left: "Between runs · blind"
- 0:51 — Right: "Opus 4.7 · 5 Managed Agents"
- 0:54 — Right: "Every minute"
- 0:57 — Right: "$4.17 / week"

**Lower-third fades in at 0:58:** "SkyHerd · Ranch A · 40,000 acres"

---

## ACT 2 — Demo (1:00 – 2:30, 90s)

### 1:00 – 1:25 · Deep scenario — coyote at fence (25s)

One scenario. All the way through. This is the cinematic beat.

**Visual timeline:**
- 1:00 — Cut to dashboard map. Zoom to SW fence line. Ambient music, no VO yet.
- 1:03 — Thermal camera pulse. A white heat-signature ghosts in and out of the brush.
- 1:05 — FenceLineDispatcher lane flashes sage. Tool-call ticker: `classify_thermal → coyote 91%`.
- 1:07 — VO starts.
- 1:09 — Drone telemetry overlay slides in bottom-left. `MAVSDK · Mavic · ETA 40s`.
- 1:13 — Drone-view POV (thermal-tinted), approaching fence.
- 1:16 — Deterrent fires. Acoustic sweep overlay, coyote ghost darts out of frame.
- 1:19 — Mock SMS bubble (phone mock, right column): `Wes · 3:14am · "Coyote on W-12. Drone scared it off. Fence intact. You're good."`
- 1:22 — AttestationPanel HashChip slides top-right: `Ed25519 a7c3…f91e · SIGNED`.
- 1:24 — Hold.

**VO cue `vo-coyote-deep`:**
> "Three-fourteen in the morning. Thermal camera on the south fence catches something. FenceLineDispatcher — that's one of the five agents — wakes up, looks at the frame, says yeah, that's a coyote. Ninety-one percent. Sends the drone. Drone flies it, scares it off with a deterrent, flies home. You get a text. Nobody woke up. Nothing got eaten. Every step signed, hashed, in the ledger."

**Delivery:** calm, slightly proud, like you're walking a friend through it. The "Nobody woke up" is almost a smile.

**Lower-third (persists from 1:05):** `FenceLineDispatcher · Coyote 91% · Fence W-12 · Mavic dispatched`

### 1:25 – 1:50 · Montage — four other scenarios (~25s, ~6s each)

Fast cuts. No full VO. Music bed swells. Each scenario gets ONE kinetic-typography callout on top of the scenario clip. Lower-third + AnchorChip land per cut.

**SFX bed:** soft keyboard-latch clicks on each cut. One `skyherd-mesh` terminal line flicks on-screen per scene (bottom-left ticker).

#### 1:25 – 1:31 · Sick cow (A014)

**Visual:** Map pan to trough 3. Bounding box snaps on cow A014's face. VetIntakePanel slides in. PDF mock (vet packet) flashes right side — front page legible: "Cow A014 · suspected pinkeye · 83% · photos attached."

**Kinetic callout:** "A014 — vet packet on his phone in 12 seconds"
**Lower-third:** `HerdHealthWatcher · Cow A014 · pinkeye 83% · Vet packet generated`
**AnchorChip:** `Vet packet · Cow A014 · Ed25519 4d82…b03c · SENT`

#### 1:31 – 1:37 · Water tank drop

**Visual:** Tank 7 glyph turns red. GrazingOptimizer lane lights. Drone IR still pops in — a dark leak-stain on the concrete pad.

**Kinetic callout:** "Tank 7 dropped to 8 PSI — drone flew it before sunrise"
**Lower-third:** `GrazingOptimizer · Tank 7 pressure drop · IR flyover scheduled`
**AnchorChip:** `IR flyover · Tank 7 · Ed25519 92e1…5a0d · QUEUED`

#### 1:37 – 1:44 · Calving (117)

**Visual:** CalvingWatch lane activates. Behavior trace draws a ragged spike. Phone mock — priority page — flashes with timestamp "3:14am."

**Kinetic callout:** "117's calving — pinged at 3:14am"
**Lower-third:** `CalvingWatch · Cow 117 · pre-labor · Rancher paged (priority)`
**AnchorChip:** `Behavior trace · Cow 117 · Ed25519 61bf…2c94 · PAGED`

#### 1:44 – 1:50 · Storm incoming

**Visual:** Weather overlay sweeps across map. Paddock redirect arrow draws. Herd dots flow from Paddock B toward Shelter 2.

**Kinetic callout:** "Hail in 45min — herd routed to Shelter 2"
**Lower-third:** `Weather-Redirect · Hail ETA 45 min · Paddock B → Shelter 2`
**AnchorChip:** `Redirect plan · Ed25519 d3a9…7e11 · ACTIVE`

### 1:50 – 2:30 · Under the hood — mesh + Opus 4.7 (40s)

**Visual:** Cut to dark-mode node canvas. Smooth camera pan — not hard cuts.
- 1:50 — Single sage node: "Sensor Event."
- 1:53 — Fans out to 5 agent nodes (FenceLineDispatcher, HerdHealthWatcher, PredatorPatternLearner, GrazingOptimizer, CalvingWatch).
- 2:00 — Camera pans right. Each agent spawns tool nodes — drone, deterrent, vet packet, paddock redirect, priority page.
- 2:10 — Pans to center: `attest.append(hash, sig)`. Merkle chain pulses outward. Counter ticks up: "360 events · all signed."
- 2:20 — Cost ticker bottom-right: `$4.17 / week`.
- 2:25 — Terminal mock: `client.beta.messages.create(model="claude-opus-4-7"...)` with `cache_control: ephemeral` highlighted sage.

**VO cue `vo-mesh-opus`:**
> "Each agent's its own Managed Agents session. Built on Opus 4.7. Idle-pause billing — when nothing's happening, the agent sleeps. Costs you nothing. Sensor wakes it, it does the work, goes back to sleep. That's how a whole ranch runs on four bucks a week of Claude. Every tool call gets signed. Every signature lands in a Merkle chain. Replay the whole day from a seed — same input, same bytes, every time."

**Delivery:** quieter here, like you're showing someone the inside of a box. "Four bucks a week" is thrown away. "Every time" lands.

**Emphasis caption:** *"Same seed. Same bytes. Every time."* fades in 2:24-2:30.

---

## ACT 3 — Close (2:30 – 3:00, 30s)

### 2:30 – 2:48 · Substance (~18s)

**Visual:** Cut to drone aerial over rangeland (`broll/drone-rangeland.mp4`), warm dust grade. Three stat blocks fade in sequentially, left-aligned.
- 2:31 — `1,106 tests · 87% coverage`
- 2:35 — `Ed25519 attestation chain · 360 events`
- 2:39 — `Fresh-clone reproducible · < 3 minutes`

**VO cue `vo-close-substance`:**
> "Eleven-hundred-six tests. Eighty-seven percent coverage. Every tool call signed with Ed25519. Clone the repo, run one command, watch the same five scenarios play out — bit for bit."

### 2:48 – 3:00 · Wordmark (~12s)

**Visual:** Hard cut to brand isometric ranch animation. Wordmark scales up at 2:50. Lines fade in below.

**VO cue `vo-close-final`:**
> "Beef at record highs. Cow herd at a sixty-five-year low. Now the ranch can watch itself."

**Delivery:** slow, a little tired, like "that's the whole pitch, here's the bow."

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

## VO cue table (Variant A — iter2 humanized)

Voice: swap off Antoni — see `scripts/render_vo_phase1.sh`. Filename pattern: `vo-*.mp3`.

| Key | File | Duration target | Text |
|-----|------|-----------------|------|
| `vo-intro` | `vo-intro.mp3` | ~13s | "I'm George. Senior at UNM. Part 107 drone ticket. I've spent a lot of nights on ranches in New Mexico. And one question kept coming up. What if the ranch just watched itself?" |
| `vo-market` | `vo-market.mp3` | ~20s | "Beef is at record highs. The American cow herd's at a sixty-five-year low. Labor's gone. Ranchers are aging out. Every ranch left has to do more, with fewer eyes on it. The herd already has a nervous system. The rancher doesn't." |
| `vo-compare` | `vo-compare.mp3` | ~18s | "Here's how it works today. A rancher drives two hundred miles a week, checks every trough, every fence, every sick cow. Best case: six runs a day. Anything between runs, you miss. Now. Same ranch. Five Claude Managed Agents, built on Opus 4.7. They watch every fence, every trough, every cow. Every minute. Four dollars and seventeen cents a week." |
| `vo-coyote-deep` | `vo-coyote-deep.mp3` | ~22s | "Three-fourteen in the morning. Thermal camera on the south fence catches something. FenceLineDispatcher, that's one of the five agents, wakes up, looks at the frame, says yeah, that's a coyote. Ninety-one percent. Sends the drone. Drone flies it, scares it off with a deterrent, flies home. You get a text. Nobody woke up. Nothing got eaten. Every step signed, hashed, in the ledger." |
| `vo-mesh-opus` | `vo-mesh-opus.mp3` | ~34s | "Each agent's its own Managed Agents session. Built on Opus 4.7. Idle-pause billing. When nothing's happening, the agent sleeps. Costs you nothing. Sensor wakes it, it does the work, goes back to sleep. That's how a whole ranch runs on four bucks a week of Claude. Every tool call gets signed. Every signature lands in a Merkle chain. Replay the whole day from a seed. Same input, same bytes, every time." |
| `vo-close-substance` | `vo-close-substance.mp3` | ~14s | "Eleven-hundred-six tests. Eighty-seven percent coverage. Every tool call signed with Ed25519. Clone the repo, run one command, watch the same five scenarios play out. Bit for bit." |
| `vo-close-final` | `vo-close-final.mp3` | ~9s | "Beef at record highs. Cow herd at a sixty-five-year low. Now the ranch can watch itself." |

**Sum estimate:** 13 + 20 + 18 + 22 + 34 + 14 + 9 = **130s of narration** across 180s of runtime. ~50s of music-only / SFX-only space, concentrated in: cold open (8s), montage (~10-12s), wordmark tail (~3s).

**Retired cues from iter1:** `vo-coyote`, `vo-sick-cow`, `vo-calving`, `vo-storm`, `vo-bridge`, `vo-mesh`. Replaced by `vo-coyote-deep` + silent montage + `vo-compare` + `vo-mesh-opus`. Script removes the em-dash and "Heads up" patterns that Gemini flagged as press-release.

---

## B-roll inventory

| Slot | Asset | Location used |
|------|-------|---------------|
| 0:06-0:22 | `broll/dawn-corral.mp4` | Act 1 intro |
| 0:22-0:42 | `broll/cattle-grazing-wide.mp4`, `broll/fence-line-dusk.mp4`, `broll/empty-pasture.mp4`, `broll/nm-high-desert.mp4` | Act 1 market |
| 0:42-1:00 | `broll/pickup-sunrise.mp4` (left) + dashboard map (right — Remotion built) | Act 1 traditional-vs-SkyHerd |
| 1:00-1:25 | `clips/coyote.mp4` + overlays | Act 2 deep scenario |
| 1:25-1:50 | `clips/{sick_cow,water,calving,storm}.mp4` | Act 2 montage |
| 1:50-2:30 | (animated node canvas + terminal mock — Remotion built) | Act 2 mesh + Opus |
| 2:30-2:48 | `broll/drone-rangeland.mp4` | Act 3 substance |
| 2:48-3:00 | (isometric brand animation — Remotion built) | Act 3 wordmark |

---

## Hackathon-criteria coverage

Judging weights: 30% Impact / 25% Demo / 25% Opus 4.7 / 20% Depth.

| Criterion | Where it lands | Beats |
|-----------|---------------|-------|
| **Impact (30%)** | Act 1 market (0:22-0:42) + compare beat (0:42-1:00) + Act 3 close | Record beef + 65-yr cow-herd low + labor gone + traditional-vs-SkyHerd split-screen (the new Impact beat) + bookend echo |
| **Demo (25%)** | Deep coyote (1:00-1:25) + 4-scenario montage (1:25-1:50) | One scenario taken all the way through + four rapid callouts — judges see all 5 in under a minute |
| **Opus 4.7 (25%)** | Compare beat names it (0:51) + mesh-opus beat names it again (1:53) + terminal mock at 2:25 | "Built on Opus 4.7" spoken twice, shown on screen once in a beta API call |
| **Depth (20%)** | Mesh reveal (1:50-2:30) + Act 3 substance (2:30-2:48) | 1106 tests + 87% coverage + Ed25519 ledger + 360 signed events + "same seed, same bytes" |

---

## Production notes (iter2)

- **Voice:** swap off Antoni. Candidates — Will (`bIHbv24MWmeRgasZH58o`), Brian (`nPczCjzI2devNBz1zQrb`), Chris (`iP95p4xoKVk53GoZ742B`). Pick the one that sounds least like a narrator.
- **Model:** try `eleven_v3` first for natural intonation; fall back to `eleven_turbo_v2_5` if the account doesn't have v3 access.
- **Voice settings:** `stability=0.5`, `similarity_boost=0.75`, `style=0.4`, `use_speaker_boost=true`. Tuned for conversational not broadcast.
- **Color grade:** warm earth tones Acts 1 + 3. Dark-mode for the dashboard beats in Act 2. The traditional-vs-SkyHerd split gets a desaturated left column and a saturated right column to reinforce the comparison visually.
- **Cuts:** 95% hard cuts. Smooth pan only on the mesh reveal.
- **Music:** single bed. Holds at base volume, ducks under VO.
- **Aspect:** 16:9 widescreen, 1080p60.
