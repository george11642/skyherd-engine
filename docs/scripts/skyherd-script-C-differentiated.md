# SkyHerd Demo Video v2 — Variant C · Differentiated (iter2 humanized)

**Variant strategy:** 5-act layout, restructured for iter2. Hook (20s) / Story (40s) / Demo — deep+montage (55s) / Substance — with explicit Opus 4.7 + traditional-comparison (45s) / Close (20s).
**Hook style:** Metric-first, humanized.
**Captions:** **Word-level kinetic captions throughout.** Per-word semantic styling authored by Opus 4.7 via `styled-captions-C.json`.
**Voice:** See `scripts/render_vo_phase1.sh` — swapped off Antoni. Model `eleven_v3` (fallback `eleven_turbo_v2_5`).
**Total runtime:** 3:00 ± 1s.

> iter2 fix: keep the 5-act differentiation, but humanize every line and bake in the traditional-comparison beat + deep/montage demo restructure. The word-level captions get the humanize pass too — no "Heads up —" in the caption track.

---

## Act timing (5-act — iter2 retuned)

```
┌──── ACT 1 — Hook ─────────────┐ 0:00 – 0:20  (20 s · 11%)
├──── ACT 2 — Story ────────────┤ 0:20 – 1:00  (40 s · 22%)
│ Market arc · traditional-vs   │
│ -SkyHerd comparison fused in  │
├──── ACT 3 — Demo ─────────────┤ 1:00 – 1:55  (55 s · 31%)
│ Deep coyote (25s) + montage   │
│ (25s) + synthesis (5s)        │
├──── ACT 4 — Substance ────────┤ 1:55 – 2:40  (45 s · 25%)
│ Opus 4.7 named + ledger/depth │
├──── ACT 5 — Close ────────────┤ 2:40 – 3:00  (20 s · 11%)
│ Bookend · wordmark            │
└───────────────────────────────┘
```

Story + compare fold into Act 2. Demo restructured (deep + montage). Act 4 dedicates explicit screen-time to Opus 4.7. Total still 180s.

---

## ACT 1 — Hook (0:00 – 0:20, 20s)

### 0:00 – 0:08 · Metric punch (no VO)

**Visual:** Black card. Three numbers stagger in. No word-level captions in this beat (no VO to caption).

**Kinetic punch:**
- 0:01 — "$4.17"
- 0:02 — "a week"
- 0:03 — "24/7"
- 0:04 — "nervous system"
- 0:06 — "10,000-acre ranch"
- 0:07 — fades through to dawn-corral B-roll

### 0:08 – 0:20 · Who I am (~12s)

**Word-level kinetic captions ENABLE.**

**VO cue `vo-hook-C`:**
> "I'm George. Senior at UNM, Part 107 drone ticket, a lot of nights on New Mexico ranches. SkyHerd. One ranch. Every fence. Every trough. Every cow."

**Delivery:** credentials run together fast — throwaway. Then the three-item list is paced and deliberate, like you're counting on fingers.

---

## ACT 2 — Story + compare (0:20 – 1:00, 40s)

**Visual:** B-roll heavy. Cuts: cattle wide → fence dusk → empty pasture → NM high-desert → pickup-at-sunrise (for the "today" beat) → dashboard map glow (for the "now" beat).

**Word-level kinetic captions ENABLE.**

**VO cue `vo-story-C`:**
> "Beef is at record highs. The American cow herd's at a sixty-five-year low. Labor's gone. Ranchers are aging out. Here's how a ranch runs today. A guy drives two hundred miles a week, checks every trough, every fence, every sick cow. Six runs a day. Anything between runs, he misses. So. Same ranch. Five Claude Managed Agents, built on Opus 4.7. Every fence. Every trough. Every cow. Every minute. The herd already has a nervous system. The rancher finally does too."

**Delivery:** first four sentences fast, stacked. "Here's how a ranch runs today" is the pivot — slow it. "So." is a hinge. Last two lines ride the bookend back in.

**Kinetic typography hero overlays (layered on top of word-level captions):**
- 0:22 — "Beef · record highs" (large dust)
- 0:27 — "Cow herd · 65-yr low" (large dust)
- 0:32 — "Labor · gone" (medium sage)
- 0:36 — "Ranchers · aging out" (medium sage)
- 0:42 — SPLIT: left "Rancher · 200 mi/week · 6 runs a day" · right (fades in 0:46) "Opus 4.7 · 5 Managed Agents · every minute"
- 0:54 — "$4.17 / week" (large dust, bottom-right corner of right column)
- 0:58 — "The rancher finally does too." (bold, center)

---

## ACT 3 — Demo (1:00 – 1:55, 55s)

### 1:00 – 1:25 · Deep coyote scenario (25s)

Same depth beat as A/B.

**Visual timeline (identical to A/B):**
- 1:00 — Dashboard map zooms to SW fence. Music.
- 1:03 — Thermal pulse.
- 1:05 — FenceLineDispatcher lane flashes. `classify_thermal → coyote 91%`.
- 1:07 — VO starts.
- 1:09 — Drone telemetry overlay. `MAVSDK · Mavic · ETA 40s`.
- 1:13 — Drone POV, thermal tinted.
- 1:16 — Deterrent fires. Coyote out of frame.
- 1:19 — Mock SMS: `Wes · 3:14am · "Coyote on W-12. Drone scared it off. Fence intact. You're good."`
- 1:22 — HashChip: `Ed25519 a7c3…f91e · SIGNED`
- 1:24 — Hold.

**VO cue `vo-coyote-deep`:**
> "Three-fourteen in the morning. Thermal on the south fence catches something. FenceLineDispatcher — one of the five agents — wakes up, looks at the frame, says yeah, coyote. Ninety-one percent. Sends the drone. Drone flies it, scares it off, flies home. You get a text. Nobody woke up. Nothing got eaten. Every step signed, hashed, in the ledger."

### 1:25 – 1:50 · Montage — four scenarios (~25s)

Same as A/B. One kinetic callout per scene, no full VO, music carries, SFX bed of keyboard-latch clicks.

- **1:25 – 1:31 · Sick cow:** "A014 — vet packet on his phone in 12 seconds" · Vet packet PDF mock · `HerdHealthWatcher · A014 · pinkeye 83%` · Ed25519 4d82…b03c
- **1:31 – 1:37 · Water tank:** "Tank 7 dropped to 8 PSI — drone flew it before sunrise" · Drone IR still · `GrazingOptimizer · Tank 7 drop` · Ed25519 92e1…5a0d
- **1:37 – 1:44 · Calving:** "117's calving — pinged at 3:14am" · Phone priority page · `CalvingWatch · 117 · pre-labor` · Ed25519 61bf…2c94
- **1:44 – 1:50 · Storm:** "Hail in 45min — herd routed to Shelter 2" · Herd-flow redirect · `Weather-Redirect · Paddock B → Shelter 2` · Ed25519 d3a9…7e11

### 1:50 – 1:55 · Synthesis (5s)

Three callout cards stack right-side:
- 1:50 — "5 Managed Agents · idle-pause billing"
- 1:52 — "33 Skill Files · per-task knowledge"
- 1:54 — "$4.17 / week · 24/7 coverage"

No VO here — music pulls up briefly before Act 4 cut.

---

## ACT 4 — Substance (1:55 – 2:40, 45s)

### 1:55 – 2:20 · Opus 4.7 co-direction (25s)

**Visual:** Split-screen. Left: animated 5-agent mesh node canvas. Right: terminal stream showing `client.beta.messages.create(model="claude-opus-4-7", ...)` with `cache_control: ephemeral` highlighted sage.

**VO cue `vo-opus-C`:**
> "Each agent's its own Managed Agents session. Built on Opus 4.7. Beta header. Prompt-cached system plus skills. When an agent's idle, billing stops — it costs nothing to have it standing by. One more thing. The per-word caption styling you're watching right now — the colors, the emphasis, the pacing — Opus 4.7 authored all of it. The model picks which words to hit. The repo commits the JSON."

**Delivery:** proud-but-quiet. "One more thing" is a smile — Jobs nod, not cringe-hard. "The model picks which words to hit" is flat and factual. The meta-caption moment has to land; the captions are the demo of what you're saying.

**On-screen terminal (right column, lines fade in one-by-one):**
```
$ skyherd-mesh smoke
[FenceLineDispatcher]    beta-session-id=fls_8a2f  cache-hit=92%
[HerdHealthWatcher]      beta-session-id=hhw_3c91  cache-hit=88%
[PredatorPatternLearner] beta-session-id=ppl_4d7e  cache-hit=95%
[GrazingOptimizer]       beta-session-id=gop_b211  cache-hit=89%
[CalvingWatch]           beta-session-id=cwc_e604  cache-hit=91%
all 5 idle · cost ticker $4.17/week
```

### 2:20 – 2:40 · Depth + ledger (20s)

**Visual:** Hard cut to terminal — `uv run skyherd-attest verify`. Green chain of 360 entries scrolls. Counter: `tests: 1106 · cov: 87% · seed: 42 · bytes: stable`.

**VO cue `vo-depth-C`:**
> "Eleven-hundred-six tests. Eighty-seven percent coverage. Every tool call signed. Ed25519 Merkle chain. Replay the whole day from a seed — same input, same bytes, every time."

---

## ACT 5 — Close (2:40 – 3:00, 20s)

### 2:40 – 2:53 · Bookend (~13s)

**Visual:** Live drone aerial over rangeland. Quiet music swell. Word-level captions continue.

**VO cue `vo-close-C`:**
> "Beef at record highs. Cow herd at a sixty-five-year low. Now — finally — the ranch can watch itself."

**Delivery:** the "finally" has weight. Long vowel. Slight pause after.

### 2:53 – 3:00 · Wordmark (7s)

Silent.

```
                    SkyHerd

   github.com/george11642/skyherd-engine
   MIT · Python 3.11 · TypeScript 5.8 · Opus 4.7
   1,106 tests · 87% coverage · Ed25519
   George Teifel · UNM · 2026
```

Cut to black at 3:00.

---

## VO cue table (Variant C — iter2 humanized)

**Cues unique to C:** `vo-hook-C`, `vo-story-C`, `vo-opus-C`, `vo-depth-C`, `vo-close-C`.
**Cues shared with A/B:** `vo-coyote-deep`.
**Retired:** `vo-synthesis-C` (the 5s synthesis beat is silent now — music carries).

| Key | File | Duration target | Text | Shared? |
|-----|------|-----------------|------|---------|
| `vo-hook-C` | `vo-hook-C.mp3` | ~11s | "I'm George. Senior at UNM, Part 107 drone ticket, a lot of nights on New Mexico ranches. SkyHerd. One ranch. Every fence. Every trough. Every cow." | No |
| `vo-story-C` | `vo-story-C.mp3` | ~37s | "Beef is at record highs. The American cow herd's at a sixty-five-year low. Labor's gone. Ranchers are aging out. Here's how a ranch runs today. A guy drives two hundred miles a week, checks every trough, every fence, every sick cow. Six runs a day. Anything between runs, he misses. So. Same ranch. Five Claude Managed Agents, built on Opus 4.7. Every fence. Every trough. Every cow. Every minute. The herd already has a nervous system. The rancher finally does too." | No |
| `vo-coyote-deep` | `vo-coyote-deep.mp3` | ~20s | "Three-fourteen in the morning. Thermal on the south fence catches something. FenceLineDispatcher, one of the five agents, wakes up, looks at the frame, says yeah, coyote. Ninety-one percent. Sends the drone. Drone flies it, scares it off, flies home. You get a text. Nobody woke up. Nothing got eaten. Every step signed, hashed, in the ledger." | Yes (A/B) |
| `vo-opus-C` | `vo-opus-C.mp3` | ~24s | "Each agent's its own Managed Agents session. Built on Opus 4.7. Beta header. Prompt-cached system plus skills. When an agent's idle, billing stops. Costs nothing to have it standing by. One more thing. The per-word caption styling you're watching right now — the colors, the emphasis, the pacing — Opus 4.7 authored all of it. The model picks which words to hit. The repo commits the JSON." | No |
| `vo-depth-C` | `vo-depth-C.mp3` | ~13s | "Eleven-hundred-six tests. Eighty-seven percent coverage. Every tool call signed. Ed25519 Merkle chain. Replay the whole day from a seed. Same input, same bytes, every time." | No |
| `vo-close-C` | `vo-close-C.mp3` | ~11s | "Beef at record highs. Cow herd at a sixty-five-year low. Now, finally, the ranch can watch itself." | No |

**Sum estimate:** 11 + 37 + 20 + 24 + 13 + 11 = **116s** across 180s. Denser than A/B's 131s because C carries word-level captions across more of the runtime — the density fits the captioned look.

---

## B-roll inventory

| Slot | Asset | Location used |
|------|-------|---------------|
| 0:08-0:20 | `broll/dawn-corral.mp4` | Act 1 |
| 0:20-0:42 | `broll/cattle-grazing-wide.mp4`, `broll/fence-line-dusk.mp4`, `broll/empty-pasture.mp4`, `broll/nm-high-desert.mp4` | Act 2 market |
| 0:42-1:00 | `broll/pickup-sunrise.mp4` (left) + dashboard map glow (right) | Act 2 compare split |
| 1:00-1:25 | `clips/coyote.mp4` + overlays | Act 3 deep scenario |
| 1:25-1:50 | `clips/{sick_cow,water,calving,storm}.mp4` | Act 3 montage |
| 1:50-1:55 | `clips/ambient_30x_synthesis.mp4` | Act 3 synthesis |
| 1:55-2:20 | (mesh + terminal — Remotion) | Act 4 Opus |
| 2:20-2:40 | `clips/attest_verify.mp4` | Act 4 depth |
| 2:40-2:53 | `broll/drone-rangeland.mp4` | Act 5 bookend |
| 2:53-3:00 | (isometric brand) | Act 5 wordmark |

---

## Hackathon-criteria coverage

| Criterion | Where | Beats |
|-----------|-------|-------|
| **Impact (30%)** | Act 1 hook + Act 2 compare beat + Act 5 "finally" bookend | Metric front-loaded + traditional-vs-SkyHerd split-screen + emotional close |
| **Demo (25%)** | Act 3 deep coyote + 4-montage | One scenario deep, four rapid |
| **Opus 4.7 (25%)** | Named in Act 2 compare + dedicated Act 4 (25s) + meta-loop (Opus authored captions) | Most Opus-screen-time of any variant |
| **Depth (20%)** | Act 4 depth beat (20s) | 1106 tests + 87% + Ed25519 + seed-stable replay |

C's structural advantage: each criterion gets a dedicated moment. C's risk: 5 acts + word-level captions is dense. If iter2 comparison shows B still leads, ship B.

---

## Production notes (iter2)

- **Voice:** swap off Antoni. See `scripts/render_vo_phase1.sh` header for the chosen voice ID. Model `eleven_v3` first, fall back to `eleven_turbo_v2_5`.
- **Voice settings:** `stability=0.5`, `similarity_boost=0.75`, `style=0.4`, `use_speaker_boost=true`.
- **Captions:** word-level throughout. Style: Inter SemiBold 56px white on 60% black pill, 96px from bottom. Per-word color/weight from `styled-captions-C.json` — Opus 4.7 output. Fallback to uniform white if JSON malformed.
- **Color grade:** warm earth Acts 1-2-5. Dark-mode Acts 3-4. The warm→dark transition at 1:00 is hard and intentional.
- **Music:** single bed. Ducks under VO. Does NOT pump under `vo-opus-C` (24s is long enough that pumping reads as nervous).
- **Cuts:** 95% hard cuts. Split-screens in Act 2 compare and Act 4 Opus are static layouts, not transitions.
- **Aspect:** 16:9, 1080p60.
