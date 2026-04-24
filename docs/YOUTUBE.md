# YouTube Upload Metadata — SkyHerd Submission Video

**Upload target:** YouTube channel (George's personal or `@skyherd` if created in time).
**Visibility:** **Unlisted** (per hackathon rules — the Devpost form just needs a link, not public view).
**Upload date:** 2026-04-26 (between 14:00 and 17:00 EST on submission day).

---

## Title options

### Option A (recommended — keyword-front)

> **SkyHerd — Five Claude Managed Agents Run a Ranch for $4/week · Built with Opus 4.7**

(92 chars — fits 100-char YouTube title limit, leads with project name + prize track, lands the $4/week hook.)

### Option B (benefit-front alternative)

> **$4/week Watches 50,000 Acres — SkyHerd · 5 Managed Agents · Opus 4.7**

(80 chars — punchier hook, slightly weaker on SEO for "Claude".)

### Option C (literal, for A/B)

> **SkyHerd Demo — The Ranch That Watches Itself (Built with Opus 4.7 Hackathon)**

(79 chars — best for click-through in agri circles.)

**Recommendation:** Option A. Keywords up front + $4/week curiosity gap.

---

## Description (paste into YouTube description field)

```
SkyHerd is a 5-layer nervous system for American ranches. Five Claude Managed
Agents watch a working cattle operation 24/7, pausing their own billing between
events. A cow can be dying for 72 hours before anyone sees it — SkyHerd makes
the ranch watch itself.

Built for the Anthropic "Built with Opus 4.7" hackathon, 2026-04-26.

▶ Code: https://github.com/george11642/skyherd-engine (MIT)
▶ One-pager: https://github.com/george11642/skyherd-engine/blob/main/docs/ONE_PAGER.md
▶ Architecture: https://github.com/george11642/skyherd-engine/blob/main/docs/ARCHITECTURE.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱ TIMESTAMPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
0:00 Cold open — "A cow can be dying for 72 hours before anyone sees it"
0:08 The ask — what if the ranch watched itself?
0:18 One-line pitch — 5 Managed Agents, idle-paused billing, Opus 4.7
0:25 Dashboard establish — 5 agent lanes, $4.17/week cost ticker
0:38 Scenario 1 — Coyote at the SW fence (drone deterrent + Wes voice call)
0:52 Scenario 2 — Sick cow flagged (pinkeye → vet intake packet)
1:06 Scenario 3 — Water tank pressure drop (LoRaWAN → drone flyover)
1:20 Scenario 4 — Calving detected (priority rancher page)
1:34 Scenario 5 — Storm incoming (grazing redirect + acoustic nudge)
1:48 Why it works — idle-pause billing, skills library, persistent sessions
2:20 Attestation chain + fresh-clone reproducibility (<3 min)
2:40 Why it matters — beef at record highs, cow herd at 65-year low
2:55 Close

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 PRIZE TRACKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Best Use of Claude Managed Agents ($5k)
• Keep Thinking ($5k)
• Most Creative Opus 4.7 Exploration ($5k)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛠 STACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Claude Opus 4.7 + Managed Agents beta (managed-agents-2026-04-01)
• claude-agent-sdk 0.1.64, anthropic 0.96 (client.beta.*)
• Python 3.11 / uv / FastAPI / SSE
• React 19 / Tailwind v4 (SPA + /rancher PWA)
• MAVSDK + pymavlink (ArduCopter SITL) / DJI SDK V5 (Mavic Air 2)
• MegaDetector V6 for trough-cam vision (MIT-compatible)
• Ed25519 + Merkle attestation ledger
• ElevenLabs ("Wes" cowboy voice clone) + Twilio
• 2× Raspberry Pi 4 edge nodes (collar-free path)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ STATS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 1,100+ tests, 87% coverage
• Deterministic: `make demo SEED=42 SCENARIO=all` byte-identical across replays
• Fresh-clone quickstart: <3 min on a clean machine
• 33-file skills library (CrossBeam pattern — same as the Opus 4.6 $50k winner)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 TEAM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
George Teifel — UNM, Part 107 licensed drone operator.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 LICENSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MIT throughout. No AGPL dependencies.

#ClaudeAI #Opus4 #BuiltWithOpus47 #ManagedAgents #AgTech #OpenSource
#Ranching #CattleIndustry #AIforGood
```

---

## Tags (comma-separated, paste into YouTube tags field)

```
SkyHerd, Claude Managed Agents, Claude AI, Opus 4.7, Anthropic, Built with Opus 47,
AI ranching, agentic AI, LoRaWAN, MAVSDK, DJI Mavic, MegaDetector, Ed25519,
attestation, FastAPI, Raspberry Pi, drone, cattle, AgTech, hackathon, open source,
Python, TypeScript, CrossBeam skills
```

(23 tags · YouTube soft-caps at 500 chars total, well under.)

---

## Thumbnail brief

Primary thumbnail: see `docs/SHOT_LIST.md` → Image-gen Prompt 4.

**Composition requirements:**
- **1280 × 720 px**, 16:9, <2 MB, JPG or PNG.
- Three-zone layout: silhouette/human (left), dashboard UI (center), Mavic drone (right).
- Bold title text over center: **"THE RANCH WATCHES ITSELF"** — Inter Bold or similar
  sans, 80–100 pt, white with 2 px charcoal stroke for legibility at 320×180 preview.
- Sub-line: **"5 Managed Agents · 24/7"** — 40 pt, sage-green accent.
- Warm amber-to-sage gradient background.
- Avoid:
  - Small text (fails mobile preview).
  - Clickbait arrow graphics (feels cheap for a judged submission).
  - Face close-up (the pitch is about the system, not the person).

**A/B alternate:** see SHOT_LIST Prompt 5 ("$4.17/week to watch 50,000 acres").

**File locations:**
- `docs/screenshots/thumbnail.png` (primary)
- `docs/screenshots/thumbnail-alt.png` (alternate)

---

## Captions / subtitles

Upload CEA-608 closed captions generated from `docs/demo-assets/captions.json`.
If captions.json isn't ready at upload time, enable YouTube auto-captions as a
fallback and upload the manual SRT post-submission (before end of judging).

---

## End screen + cards

- **End screen (last 20 s):**
  - Subscribe button (lower-left).
  - Link card to `https://github.com/george11642/skyherd-engine` (lower-right).
  - Video card "SkyHerd: Architecture Deep-Dive" (if follow-up recorded; skip for
    MVP submission).

- **Cards during the video:**
  - 0:30 — link card to GitHub repo.
  - 2:20 — link card to `docs/ARCHITECTURE.md`.
  - 2:55 — end-screen trigger.

---

## Post-upload checklist

- [ ] Title, description, tags pasted (from this doc).
- [ ] Thumbnail uploaded.
- [ ] Visibility: **Unlisted**.
- [ ] Category: Science & Technology.
- [ ] Language: English.
- [ ] "Not made for kids" selected.
- [ ] Captions uploaded OR auto-captions confirmed running.
- [ ] End screen + cards configured.
- [ ] URL copied → pasted into:
  - `docs/SUBMISSION.md` (replace `{{YOUTUBE_URL}}`)
  - `docs/LINKEDIN_LAUNCH.md` (replace `{{YOUTUBE_URL}}`)
- [ ] Commit + push: `docs: fill YouTube URL`.
- [ ] Short-URL optional: shorten via `bit.ly/skyherd-submission` for LinkedIn if desired.

---

## Backup host (if YouTube rejects / delays)

If YouTube takes > 30 min to process or rejects for any reason:

1. Upload to **Vimeo** as a private link with review password.
2. Paste Vimeo URL into Devpost as the primary submission.
3. Continue trying YouTube in the background; update Devpost when YouTube URL
   is live.

Devpost allows edits up to the deadline — submit early with whatever URL is
live at 18:00 EST, then swap to YouTube if needed.
