# SkyHerd Demo Video v2 — Variant C · Differentiated

**Variant strategy:** 5-act layout (Hook 20s / Story 50s / Demo ≤55s / Substance 35s / Close 20s) — original locked plan, bets on differentiation over winner-pattern conformance.
**Hook style:** Metric-first — same as Variant B. "$4.17 a week. Twenty-four-seven nervous system. Ten-thousand-acre ranch."
**Captions:** **Word-level kinetic captions throughout** — every spoken word renders on screen via faster-whisper word-timestamps + `<KineticCaptions>` component (Phase G/E1).
**Voice:** Antoni — `ErXwobaYiN019PkySvjV` — neutral 19yo male, college-student-engineer tone. No swagger, no folksy "Boss," no cowboy-isms.
**Total runtime:** 3:00 ± 1s.

> Bet: top-3 winners all used 3-act + emphasis-only captions. We deliberately go 5-act + word-level captions to create a more textured, info-dense cut. Highest variance — could read as cluttered (anti-pattern from PostVisit's always-on captions Gemini-flag) or as differentiated and modern. The iteration loop decides.

---

## Act timing (5-act, original locked layout)

```
┌──── ACT 1 — Hook ─────────────┐ 0:00 – 0:20  (20 s · 11%)
│ Metric · problem framing      │
├──── ACT 2 — Story / market ───┤ 0:20 – 1:10  (50 s · 28%)
│ Ranching crisis arc · B-roll  │
├──── ACT 3 — Demo / sim ───────┤ 1:10 – 2:05  (55 s · 31%)
│ 5 scenarios @ ~8s each + 15s  │
│ synthesis beat                │
├──── ACT 4 — Substance ────────┤ 2:05 – 2:40  (35 s · 19%)
│ Opus 4.7 · 1106 tests · ledger│
├──── ACT 5 — Close ────────────┤ 2:40 – 3:00  (20 s · 11%)
│ Why-it-matters · wordmark     │
└───────────────────────────────┘
```

---

## ACT 1 — Hook (0:00 – 0:20, 20s)

### 0:00 – 0:08 · Metric punch (no VO)

**Visual:** Black card. Same metric punch as Variant B — three numbers pop in one at a time, dust accent on cream gradient. Word-level kinetic captions are NOT used in this beat (no VO to caption). Pure typography.

**Kinetic punch (one beat each):**
- 0:01 — "$4.17"
- 0:02 — "a week"
- 0:03 — "24/7"
- 0:04 — "nervous system"
- 0:06 — "10,000-acre ranch"
- 0:07 — fades through to dawn-corral B-roll

### 0:08 – 0:20 · Identity + problem framing

**Visual:** Dawn-corral B-roll, slow zoom. Lower-third: "George Teifel · UNM · licensed drone op."

**Word-level kinetic captions ENABLE:** Every word of the VO renders on screen via `<KineticCaptions>`. Style: Inter SemiBold 56px white on 60%-opacity black pill, 96px from bottom-safe margin. ≤7 words simultaneous, line-break on commas/periods.

**VO cue `vo-hook`:**
> "I'm George — UNM senior, drone op. SkyHerd watches one ranch. Every fence. Every trough. Every cow."

*(~12s. Compressed intro — Act 2 picks up the longer market arc.)*

---

## ACT 2 — Story / market context (0:20 – 1:10, 50s)

**Visual:** B-roll heavy. Cuts: cattle wide → fence dusk → empty pasture → NM high-desert → lightning silhouette → drone aerial. Each shot 6-8s, hard cuts.

**Word-level kinetic captions ENABLE.** All VO captioned word-by-word with semantic emphasis (color/weight per Opus-4.7-authored styled-captions.json — see Phase G).

**VO cue `vo-story`:**
> "Beef is at record highs. The American cow herd is at a sixty-five-year low. Ranches can't hire their way out — labor is gone. Ranchers are aging out. Every existing ranch has to do more with fewer eyes on it. Coyotes don't read business hours. Hail doesn't wait for the next vet visit. A cow can be dying for seventy-two hours before anyone sees her. The herd already has a nervous system. The rancher does not. So we built one."

*(~46s. Longer than Variants A/B's market beat because Act 2 here owns the entire Setup arc — there's no pre-Demo bridge in the 5-act layout. The Story act ends with "So we built one." then hard-cuts into Act 3 demo.)*

**Kinetic typography hero overlays (in addition to word-level captions):**
- 0:24 — "Beef · record highs" (large dust)
- 0:30 — "Cow herd · 65-yr low" (large dust)
- 0:36 — "Labor · gone" (medium sage)
- 0:42 — "Ranchers · aging out" (medium sage)
- 0:50 — "72 hours blind" (large warn-orange)
- 0:58 — "The rancher does not." (huge bold dust)
- 1:06 — "So we built one." (medium sage, fades into Act 3 cut)

---

## ACT 3 — Demo / sim ≤55s (1:10 – 2:05, 55s)

### 1:10 – 1:50 · Five-scenario montage · ~8s each

Each scenario gets ~8s (was 14s in v1). Cuts overlap — N+1's setup begins under N's tail.

**Word-level kinetic captions ENABLE for each VO cue.**

#### 1:10 – 1:18 · Coyote (8s)
- VO `vo-coyote`: *"Heads up — coyote at the south fence. Drone's en route."* (~4s, lands at 1:11)
- Lower-third: `FenceLineDispatcher · Coyote 91% · Mavic dispatched` (thermal)
- AnchorChip: `Fence W-12 · Ed25519 a7c3…f91e · SIGNED`

#### 1:18 – 1:26 · Sick cow (8s)
- VO `vo-sick-cow`: *"Cow A014 — eye irritation, eighty-three percent confidence. Vet packet's on your phone."* (~6s, lands at 1:18)
- Lower-third: `HerdHealthWatcher · Cow A014 · pinkeye 83%` (warn)
- AnchorChip: `Vet packet · A014 · Ed25519 4d82…b03c · SENT`

#### 1:26 – 1:34 · Water tank (8s)
- VO: *(silent — visual + lower-third only — variants A and B also silenced this scenario, kept consistent)*
- Lower-third: `GrazingOptimizer · Tank 7 pressure drop` (sky)
- AnchorChip: `IR flyover · Tank 7 · Ed25519 92e1…5a0d · QUEUED`

#### 1:34 – 1:42 · Calving (8s)
- VO `vo-calving`: *"Cow one-seventeen is going into labor. Pre-labor signals — flagged priority."* (~5s, lands at 1:34)
- Lower-third: `CalvingWatch · Cow 117 · pre-labor · priority` (sage)
- AnchorChip: `Behavior trace · Cow 117 · Ed25519 61bf…2c94 · PAGED`

#### 1:42 – 1:50 · Storm (8s)
- VO `vo-storm`: *"Hail in forty-five minutes. Moving the herd to shelter two."* (~4s, lands at 1:43)
- Lower-third: `Weather-Redirect · Hail ETA 45 min · Paddock B → Shelter 2` (dust)
- AnchorChip: `Redirect plan · Ed25519 d3a9…7e11 · ACTIVE`

### 1:50 – 2:05 · Synthesis beat (15s, was 32s in v1)

**Visual:** Cut to ambient `clips/ambient_30x_synthesis.mp4` at 30× speed. Three callout cards stack right-side, fade in over 4s each:
- 1:50 — "5 Managed Agents · idle-pause billing"
- 1:54 — "33 Skill Files · per-task domain knowledge"
- 1:58 — "$4.17/week · 24/7 ranch coverage"

**VO cue `vo-synthesis`:**
> "Five agents. Idle until a sensor wakes them. Skills loaded per-task. Cost ticker freezes between events."

*(~13s. Tight, factual.)*

---

## ACT 4 — Substance (2:05 – 2:40, 35s)

This act covers what Variant A/B compress into Act 2's 35s mesh-reveal + Act 3's 14s substance VO. Variant C separates them — gets its own dedicated beat.

### 2:05 – 2:25 · Opus 4.7 + co-direction (20s)

**Visual:** Split-screen. Left: animated 5-agent mesh node canvas (CrossBeam Opus Orchestrator pattern). Right: terminal stream — `client.beta.messages.create(model="claude-opus-4-7", ...)`, with `cache_control: ephemeral` highlighted in sage.

**VO cue `vo-opus`:**
> "Each agent runs on its own Managed Agents session — Claude beta header, prompt-cached system + skills prefix. Idle-pause billing means a sleeping agent costs nothing. We also let Opus 4.7 author the on-screen captions you're reading right now — per-word semantic styling, generated as JSON, committed to the repo."

*(~20s. This is the "Opus 4.7 co-direction" creative beat — the captions you're watching ARE the demo of Opus's editorial role.)*

**On-screen text overlay (right column):**
```
$ skyherd-mesh smoke
[FenceLineDispatcher] beta-session-id=fls_8a2f  cache-hit=92%
[HerdHealthWatcher]   beta-session-id=hhw_3c91  cache-hit=88%
[PredatorPatternLearner] beta-session-id=ppl_4d7e  cache-hit=95%
[GrazingOptimizer]    beta-session-id=gop_b211  cache-hit=89%
[CalvingWatch]        beta-session-id=cwc_e604  cache-hit=91%
all 5 idle · cost ticker $4.17/week
```

### 2:25 – 2:40 · Depth signals + ledger (15s)

**Visual:** Hard cut to terminal: `uv run skyherd-attest verify` running. Green chain of 360 entries scrolls. Ed25519 sigs blink green. Counter: `tests: 1106 · cov: 87% · seed: 42 · bytes: stable`.

**VO cue `vo-depth`:**
> "Eleven-hundred-six tests. Eighty-seven-percent coverage. Every tool call signed. Ed25519 Merkle chain. Replay from a seed — same input, same bytes. Every. Time."

*(~14s. Lands the depth criterion.)*

---

## ACT 5 — Close (2:40 – 3:00, 20s)

### 2:40 – 2:53 · Why-it-matters bookend

**Visual:** Cut to live drone aerial over rangeland (`broll/drone-rangeland.mp4`), warm dust grade. Quiet music swell. Word-level kinetic captions continue.

**VO cue `vo-close`:**
> "Beef at record highs. Cow herd at a sixty-five-year low. Now — finally — the ranch can watch itself."

*(~12s. The "finally" is intentional. Variants A/B don't have it. This beat is more emotional than factual.)*

### 2:53 – 3:00 · Wordmark + sign-off (7s)

**Visual:** Hard cut to brand-color isometric ranch animation. Wordmark scales up at 2:54. Lines fade in below.

**VO:** *(silent — let the wordmark hold)*

```
                    SkyHerd

   github.com/george11642/skyherd-engine
   MIT · Python 3.11 · TypeScript 5.8 · Opus 4.7
   1,106 tests · 87% coverage · Ed25519
   George Teifel · UNM · 2026
```

Cut to black at 3:00.

---

## VO cue table (Variant C)

Voice: Antoni `ErXwobaYiN019PkySvjV`. Filename pattern: `vo-*.mp3`.

**Cues unique to Variant C:** `vo-hook`, `vo-story`, `vo-synthesis`, `vo-opus`, `vo-depth`, `vo-close` — six cues.
**Cues shared with A/B:** `vo-coyote`, `vo-sick-cow`, `vo-calving`, `vo-storm` — four cues, byte-identical, single MP3 used by all three variants.

| Key | File | Duration target | Text | Shared? |
|-----|------|-----------------|------|---------|
| `vo-hook-C` | `vo-hook-C.mp3` | ~12s | "I'm George — UNM senior, drone op. SkyHerd watches one ranch. Every fence. Every trough. Every cow." | No |
| `vo-story-C` | `vo-story-C.mp3` | ~46s | "Beef is at record highs. The American cow herd is at a sixty-five-year low. Ranches can't hire their way out — labor is gone. Ranchers are aging out. Every existing ranch has to do more with fewer eyes on it. Coyotes don't read business hours. Hail doesn't wait for the next vet visit. A cow can be dying for seventy-two hours before anyone sees her. The herd already has a nervous system. The rancher does not. So we built one." | No |
| `vo-coyote` | `vo-coyote.mp3` | ~4s | (same as A/B) | Yes |
| `vo-sick-cow` | `vo-sick-cow.mp3` | ~6s | (same as A/B) | Yes |
| `vo-calving` | `vo-calving.mp3` | ~5s | (same as A/B) | Yes |
| `vo-storm` | `vo-storm.mp3` | ~4s | (same as A/B) | Yes |
| `vo-synthesis-C` | `vo-synthesis-C.mp3` | ~13s | "Five agents. Idle until a sensor wakes them. Skills loaded per-task. Cost ticker freezes between events." | No |
| `vo-opus-C` | `vo-opus-C.mp3` | ~20s | "Each agent runs on its own Managed Agents session — Claude beta header, prompt-cached system + skills prefix. Idle-pause billing means a sleeping agent costs nothing. We also let Opus 4.7 author the on-screen captions you're reading right now — per-word semantic styling, generated as JSON, committed to the repo." | No |
| `vo-depth-C` | `vo-depth-C.mp3` | ~14s | "Eleven-hundred-six tests. Eighty-seven-percent coverage. Every tool call signed. Ed25519 Merkle chain. Replay from a seed — same input, same bytes. Every. Time." | No |
| `vo-close-C` | `vo-close-C.mp3` | ~12s | "Beef at record highs. Cow herd at a sixty-five-year low. Now — finally — the ranch can watch itself." | No |

**Sum estimate:** 12+46+4+6+5+4+13+20+14+12 = **136s of VO** across 180s of runtime. That's denser than A (121s) or B (116s) — Variant C's 5-act layout intentionally fills more screen-time with narration. The word-level captions reinforce this density.

---

## B-roll inventory (Variant C)

Uses the same Phase D source pool as A/B, but with one extra slot for the lightning silhouette in Act 2 (per top-3 list #10):

| Slot | Asset | Location used |
|------|-------|---------------|
| 0:08-0:20 | `broll/dawn-corral.mp4` | Act 1 hook tail |
| 0:20-0:28 | `broll/cattle-grazing-wide.mp4` | Act 2 story open |
| 0:28-0:36 | `broll/fence-line-dusk.mp4` | Act 2 |
| 0:36-0:44 | `broll/empty-pasture.mp4` | Act 2 |
| 0:44-0:52 | `broll/nm-high-desert.mp4` | Act 2 |
| 0:52-1:00 | `broll/lightning-silhouette.mp4` | Act 2 — adds drama for "hail doesn't wait" line. C-only. |
| 1:00-1:10 | `broll/drone-aerial.mp4` | Act 2 close |
| 1:10-1:50 | `clips/{coyote,sick_cow,water,calving,storm}.mp4` | Act 3 demo |
| 1:50-2:05 | `clips/ambient_30x_synthesis.mp4` (existing) | Act 3 synthesis |
| 2:05-2:25 | (animated mesh + terminal — Remotion-built) | Act 4 Opus |
| 2:25-2:40 | `clips/attest_verify.mp4` (existing) | Act 4 depth |
| 2:40-2:53 | `broll/drone-rangeland.mp4` | Act 5 close |
| 2:53-3:00 | (isometric brand animation) | Act 5 wordmark |

---

## Hackathon-criteria coverage map

| Criterion | Where it lands | Beats |
|-----------|---------------|-------|
| **Impact (30%)** | Act 1 hook (0:00-0:08) **metric front-loaded** · Act 2 (0:20-1:10) full market arc · Act 5 (2:40-2:53) bookend with "finally" | $4.17/week + 24/7 + 65-yr cow herd low + 72-hours-blind line + close echo. Most Impact-screen-time of any variant. |
| **Demo (25%)** | Act 3 (1:10-1:50) all 5 scenarios · Act 3 synthesis (1:50-2:05) | 5 scenarios @ 8s each + synthesis · AnchorChips · Mavic + vet packet + paddock |
| **Opus 4.7 (25%)** | Act 4 dedicated 20s beat (2:05-2:25) · meta-loop (Opus authoring captions you're watching) | Most Opus-screen-time of any variant. Calls out beta header + cache_control + Managed Agents sessions + the styled-captions.json self-reference. |
| **Depth (20%)** | Act 4 dedicated 15s beat (2:25-2:40) | 1106 tests · 87% cov · Ed25519 · Merkle · seed-stable replay |

Variant C's structural advantage: each judging criterion gets a **dedicated act**. Variants A/B compress Substance into 35s of demo + 18s of close; C gets 35s of pure substance with no demo competing for attention.

Variant C's structural risk: 5 acts in 3 minutes is dense. The word-level captions on top of the kinetic typography hero may feel cluttered — that's the bet against winner-pattern.

---

## Production notes (Variant C)

- **Color grade:** same warm-earth palette as A/B in Acts 1-2-5. Acts 3-4 stay dark-mode dashboard / terminal aesthetic — the only variant where dark-mode dominates the middle. Carefully grade the Act 2 → Act 3 cut so the warm-to-dark shift feels intentional, not jarring.
- **Cuts:** 95% hard cuts. The Act 4 split-screen is not a transition — it's a static layout.
- **Captions:** Word-level kinetic throughout VO beats. Background style: 60%-opacity black pill, white Inter SemiBold 56px, 96px from bottom. Per-word color/weight comes from `remotion-video/public/captions/styled-captions-C.json` (Phase G — Opus 4.7 authors). Fallback to uniform white if JSON malformed.
- **Music:** Same single bed as A/B. Holds steady through Act 4 substance — the ducking algorithm should NOT pump under `vo-opus-C` since 20s of pumping reads as nervous editing.
- **Composition:** Centered for Acts 1, 2, 5. Left-right split for Act 4 (50/50 mesh + terminal). Standard for Act 3 demo.
- **Aspect:** 16:9 widescreen, 1080p60.

---

## Why this variant exists

Per `.planning/research/winner-top3-analysis.md`, **zero of three top-3 winners** used a 5-act layout, and Gemini specifically flagged PostVisit's always-on captions as a saturation risk. This variant deliberately violates both findings.

The hypothesis: differentiation matters at the long tail. If 200 hackathon submissions all use the 3-act + emphasis-only pattern (which they will, because it's what wins), being the one with 5 acts and word-level kinetic captions could either stand out as "this team had a clear point of view" or read as "this team didn't watch the winners." We render and find out.

The dual-vision iteration loop (Phase H) compares all three variants on aggregate Opus + Gemini score. If C scores below A or B by ≥1.5 points after 3 rounds, retire C and ship the better of A/B. If C is within 1.0 point, keep iterating — differentiation has option value at the awards ceremony.
