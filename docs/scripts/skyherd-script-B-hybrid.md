# SkyHerd Demo Video v2 — Variant B · Hybrid (iter2 humanized)

**Variant strategy:** 3-act Setup / Demo / Close. Phase H iter2 restructure: metric-first hook, deep coyote scenario, four-scenario montage, traditional-vs-SkyHerd comparison, explicit "Opus 4.7" name-drop.
**Hook style:** Metric-first, humanized. "$4.17 a week. That's what it costs to keep an eye on a ten-thousand-acre ranch. Every minute of every day."
**Captions:** Emphasis-only.
**Voice:** See `scripts/render_vo_phase1.sh` — swapped off Antoni. Model `eleven_v3` (fallback `eleven_turbo_v2_5`).
**Total runtime:** 3:00 ± 1s.

> iter1 scored 9.23 — leading variant. iter2 keeps the metric-first bet but humanizes every line and adds the traditional-comparison beat the user explicitly asked for.

---

## Act timing

```
┌──────── ACT 1 — Setup ──────────────────┐ 0:00 – 1:00  (60 s · 33%)
│ Metric punch · who I am · market ·      │
│ traditional-vs-SkyHerd comparison       │
├──────── ACT 2 — Demo ────────────────────┤ 1:00 – 2:30  (90 s · 50%)
│ Deep coyote (25s) + montage (25s) +     │
│ mesh + Opus 4.7 (40s)                    │
├──────── ACT 3 — Close ───────────────────┤ 2:30 – 3:00  (30 s · 17%)
│ Substance · close · wordmark            │
└──────────────────────────────────────────┘
```

Acts 2 and 3 are identical to Variant A — the divergence is the cold-open hook and the intro.

---

## ACT 1 — Setup (0:00 – 1:00, 60s)

### 0:00 – 0:08 · Metric punch (no VO)

**Visual:** Black card. Three numbers stack. Heavy serif on warm cream. Silent for 1.5s before numbers start.

**Kinetic punch:**
- 0:01 — "$4.17" (huge, dust)
- 0:02 — "a week" (small, cream)
- 0:03 — "**24/7 nervous system**" (bold sage)
- 0:06 — "10,000-acre ranch" (medium dust)
- 0:07 — fades through to dawn-corral B-roll

**VO:** silent.

### 0:08 – 0:22 · Who I am (intro VO, ~14s)

**Visual:** Dawn-corral B-roll, slow zoom. Lower-third: "George Teifel · UNM · Part 107."

**VO cue `vo-intro-B`:**
> "Yeah. Four bucks a week. I'm George, I'm a senior at UNM, I've spent a lot of nights on ranches in New Mexico, and I've got a Part 107 drone ticket. SkyHerd is what came out of that. Five Claude agents. One ranch. Every fence, every trough, every cow."

**Delivery:** the "Yeah." picks up the number on screen, like you're answering the disbelief. Then credentials, fast, throwaway. The three-item list lands clean.

**Emphasis caption:** *"Every fence. Every trough. Every cow."* — fades in 0:20-0:22.

### 0:22 – 0:42 · Market context (~20s)

**Visual:** Hard cuts: cattle-grazing wide → fence-line dusk → empty pasture → NM high-desert. One number per cut.

**VO cue `vo-market`:**
> "Beef is at record highs. The American cow herd's at a sixty-five-year low. Labor's gone. Ranchers are aging out. Every ranch left has to do more, with fewer eyes on it. The herd already has a nervous system. The rancher doesn't."

**Kinetic typography hero:**
- 0:24 — "Beef · record highs"
- 0:28 — "Cow herd · 65-yr low"
- 0:32 — "Labor · gone"
- 0:36 — "Eyes · fewer per acre"
- 0:40 — "The herd has a nervous system. *The rancher doesn't.*"

### 0:42 – 1:00 · Traditional vs SkyHerd (~18s) — NEW

**Visual:** Split-screen. Left: "Traditional." Dust-grade pickup footage, rancher on horseback, sunrise over dirt road. Right: "SkyHerd." Dashboard map glow, agent lanes, cost ticker.

**VO cue `vo-compare`:**
> "Look. This is how a ranch runs today. Rancher drives two hundred miles a week. Checks every trough, every fence, every sick cow. Six runs a day if he's lucky. Anything that happens between runs, he misses. So. Same ranch. Five Claude Managed Agents — built on Opus 4.7. They watch every fence, every trough, every cow. Every minute. Four dollars and seventeen cents a week."

**Delivery:** the "Look." and the "So." are the humanizer hinges — real-person pivots. "Every minute" is cold. "Four dollars and seventeen cents" is colder.

**Overlays:**
- 0:43 — Left: "Rancher · 6 runs/day · 200 mi/week"
- 0:46 — Left: "Between runs · blind"
- 0:51 — Right: "Opus 4.7 · 5 Managed Agents"
- 0:54 — Right: "Every minute"
- 0:57 — Right: "$4.17 / week"

**Lower-third 0:58:** "SkyHerd · Ranch A · 40,000 acres"

---

## ACT 2 — Demo (1:00 – 2:30, 90s)

**Identical to Variant A.** Deep coyote + montage + mesh + Opus 4.7. The hook variant doesn't change the demo.

### 1:00 – 1:25 · Deep scenario — coyote at fence (25s)

**Visual timeline:**
- 1:00 — Dashboard map. Zoom to SW fence.
- 1:03 — Thermal pulse. Heat-signature in the brush.
- 1:05 — FenceLineDispatcher lane flashes. Tool-call ticker: `classify_thermal → coyote 91%`.
- 1:07 — VO starts.
- 1:09 — Drone telemetry: `MAVSDK · Mavic · ETA 40s`.
- 1:13 — Drone-view POV, thermal tinted.
- 1:16 — Deterrent fires. Coyote darts out.
- 1:19 — Mock SMS on phone mock: `Wes · 3:14am · "Coyote on W-12. Drone scared it off. Fence intact. You're good."`
- 1:22 — AttestationPanel HashChip: `Ed25519 a7c3…f91e · SIGNED`
- 1:24 — Hold.

**VO cue `vo-coyote-deep`:**
> "Three-fourteen in the morning. Thermal camera on the south fence catches something. FenceLineDispatcher — that's one of the five agents — wakes up, looks at the frame, says yeah, that's a coyote. Ninety-one percent. Sends the drone. Drone flies it, scares it off with a deterrent, flies home. You get a text. Nobody woke up. Nothing got eaten. Every step signed, hashed, in the ledger."

**Lower-third (persists from 1:05):** `FenceLineDispatcher · Coyote 91% · Fence W-12 · Mavic dispatched`

### 1:25 – 1:50 · Montage — four other scenarios (~25s)

Fast cuts. No full VO. Music bed. One kinetic-typography callout per scene.

#### 1:25 – 1:31 · Sick cow (A014)
- **Kinetic callout:** "A014 — vet packet on his phone in 12 seconds"
- Lower-third: `HerdHealthWatcher · Cow A014 · pinkeye 83% · Vet packet generated`
- AnchorChip: `Vet packet · Cow A014 · Ed25519 4d82…b03c · SENT`
- Visual: bounding box snaps on A014's face. Vet-packet PDF mockup flashes right-side — "Cow A014 · suspected pinkeye · 83% · photos attached."

#### 1:31 – 1:37 · Water tank drop
- **Kinetic callout:** "Tank 7 dropped to 8 PSI — drone flew it before sunrise"
- Lower-third: `GrazingOptimizer · Tank 7 pressure drop · IR flyover scheduled`
- AnchorChip: `IR flyover · Tank 7 · Ed25519 92e1…5a0d · QUEUED`
- Visual: Tank 7 glyph red. Drone IR still of the leak-stain on concrete.

#### 1:37 – 1:44 · Calving (117)
- **Kinetic callout:** "117's calving — pinged at 3:14am"
- Lower-third: `CalvingWatch · Cow 117 · pre-labor · Rancher paged (priority)`
- AnchorChip: `Behavior trace · Cow 117 · Ed25519 61bf…2c94 · PAGED`
- Visual: behavior trace spike, priority page mock, "3:14am" timestamp.

#### 1:44 – 1:50 · Storm incoming
- **Kinetic callout:** "Hail in 45min — herd routed to Shelter 2"
- Lower-third: `Weather-Redirect · Hail ETA 45 min · Paddock B → Shelter 2`
- AnchorChip: `Redirect plan · Ed25519 d3a9…7e11 · ACTIVE`
- Visual: weather sweep, redirect arrow, herd dots flowing to shelter.

### 1:50 – 2:30 · Under the hood — mesh + Opus 4.7 (40s)

**Visual:**
- 1:50 — Dark-mode node canvas. Sage node "Sensor Event."
- 1:53 — Fans out to 5 agent nodes.
- 2:00 — Pan right. Tool nodes spawn.
- 2:10 — Pan to center: `attest.append(hash, sig)` + Merkle chain. Counter: "360 events."
- 2:20 — Cost ticker `$4.17 / week` bottom-right.
- 2:25 — Terminal mock: `client.beta.messages.create(model="claude-opus-4-7"...)` with `cache_control: ephemeral` highlighted.

**VO cue `vo-mesh-opus`:**
> "Each agent's its own Managed Agents session. Built on Opus 4.7. Idle-pause billing. When nothing's happening, the agent sleeps. Costs you nothing. Sensor wakes it, it does the work, goes back to sleep. That's how a whole ranch runs on four bucks a week of Claude. Every tool call gets signed. Every signature lands in a Merkle chain. Replay the whole day from a seed. Same input, same bytes, every time."

**Emphasis caption:** *"Same seed. Same bytes. Every time."* fades in 2:24-2:30.

---

## ACT 3 — Close (2:30 – 3:00, 30s)

**Identical to Variant A.**

### 2:30 – 2:48 · Substance

**VO cue `vo-close-substance`:**
> "Eleven-hundred-six tests. Eighty-seven percent coverage. Every tool call signed with Ed25519. Clone the repo, run one command, watch the same five scenarios play out. Bit for bit."

### 2:48 – 3:00 · Wordmark

**VO cue `vo-close-final`:**
> "Beef at record highs. Cow herd at a sixty-five-year low. Now the ranch can watch itself."

**Wordmark + lines:**
```
                    SkyHerd

   github.com/george11642/skyherd-engine
   MIT · Python 3.11 · TypeScript 5.8 · Opus 4.7
   1,106 tests · 87% coverage · Ed25519
   George Teifel · UNM · 2026
```

---

## VO cue table (Variant B — iter2 humanized)

**Cues unique to B:** `vo-intro-B`. Everything else is shared with A (`vo-market`, `vo-compare`, `vo-coyote-deep`, `vo-mesh-opus`, `vo-close-substance`, `vo-close-final`).

**Retired:** `vo-bridge-B` (the 2s "So we built one. Watch." — replaced by the traditional-comparison beat).

| Key | File | Duration target | Text | Shared |
|-----|------|-----------------|------|--------|
| `vo-intro-B` | `vo-intro-B.mp3` | ~14s | "Yeah. Four bucks a week. I'm George, I'm a senior at UNM, I've spent a lot of nights on ranches in New Mexico, and I've got a Part 107 drone ticket. SkyHerd is what came out of that. Five Claude agents. One ranch. Every fence, every trough, every cow." | No |
| `vo-market` | `vo-market.mp3` | ~20s | (same as A) | Yes |
| `vo-compare` | `vo-compare.mp3` | ~18s | (same as A) | Yes |
| `vo-coyote-deep` | `vo-coyote-deep.mp3` | ~22s | (same as A) | Yes |
| `vo-mesh-opus` | `vo-mesh-opus.mp3` | ~34s | (same as A) | Yes |
| `vo-close-substance` | `vo-close-substance.mp3` | ~14s | (same as A) | Yes |
| `vo-close-final` | `vo-close-final.mp3` | ~9s | (same as A) | Yes |

**Sum estimate:** 14 + 20 + 18 + 22 + 34 + 14 + 9 = **131s** across 180s. Same ratio as A.

---

## B-roll inventory

Identical to Variant A.

---

## Hackathon-criteria coverage

| Criterion | Where it lands | Beats |
|-----------|---------------|-------|
| **Impact (30%)** | Act 1 metric hook (first 8s) + compare beat + market + Act 3 close | Metric in the first 8 seconds — judges see the number before they can swipe |
| **Demo (25%)** | Deep coyote + 4-scenario montage | All 5 scenarios in <1 min |
| **Opus 4.7 (25%)** | Named in compare beat + mesh-opus + terminal mock | "Built on Opus 4.7" spoken twice |
| **Depth (20%)** | Mesh reveal + Act 3 substance | 1106 tests + 87% + Ed25519 + "same seed, same bytes" |

B's edge over A: the $4.17 metric lands in the first 8 seconds.

---

## Production notes (iter2)

- **Voice:** Same swap as A. Pick between Will / Brian / Chris. Conversational male.
- **Model:** `eleven_v3` first, fall back to `eleven_turbo_v2_5`.
- **Voice settings:** `stability=0.5`, `similarity_boost=0.75`, `style=0.4`, `use_speaker_boost=true`.
- **Hook tone:** calm, factual, no music. The numbers do the work. Don't sell them.
- **Color grade, cuts, music, aspect:** identical to A.
