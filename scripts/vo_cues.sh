#!/usr/bin/env bash
# vo_cues.sh — Shared VO cue library for render_vo.sh.
#
# Source this file to populate the CUES associative array (21 total).
# All text is provider-neutral; per-provider overrides live in the
# CUES_INWORLD array (only populated where Inworld prosody differs).
#
# Cue inventory (21):
#   Shared (A/B/C):  vo-coyote-deep
#   Shared (A/B):    vo-market, vo-compare, vo-mesh-opus,
#                    vo-close-substance, vo-close-final
#   Variant A:       vo-intro
#   Variant B:       vo-intro-B
#   Variant C:       vo-hook-C, vo-story-C, vo-opus-C, vo-depth-C, vo-close-C
#   Montage (A/B/C): vo-montage-sick, vo-montage-tank, vo-montage-calving,
#                    vo-montage-storm, vo-montage-bridge
#   Meta-loop:       vo-meta-A, vo-meta-B
#
# Silence rules (locked decision #7):
#   Cold open (0–8s) — always SILENT, no cue fills this window.
#   Wordmark tail (last ~3s) — always SILENT.
#
# VO density targets (locked decision #7, ~90%):
#   A: ~149/180s = 83% baseline; montage+bridge adds ~19s → ~168/180 = 93%
#   B: ~150/180s = 83% baseline; montage+bridge adds ~19s → ~169/180 = 94%
#   C: ~121/180s = 67% baseline; extended story arc + montage adds ~24s → ~145/180 = 81%
#      (C remains below 90% target; additional cue authoring deferred to iter loop)
#
# INWORLD notes:
#   Inworld v1 does not process SSML. Prosody-heavy text (pause markers,
#   emphasis) is expressed as natural punctuation only. If a cue sounds
#   rushed on Inworld, add an CUES_INWORLD override with more natural
#   sentence breaks.

declare -A CUES
declare -A CUES_INWORLD

# ─── Shared (A/B/C) ──────────────────────────────────────────────────────────

CUES["vo-coyote-deep"]="Three-fourteen in the morning. Thermal on the south fence catches something. FenceLineDispatcher, one of the five agents, wakes up, looks at the frame, says yeah, coyote. Ninety-one percent. Sends the drone. Drone flies it, scares it off, flies home. You get a text. Nobody woke up. Nothing got eaten. Every step signed, hashed, in the ledger."

# ─── Shared (A/B) ────────────────────────────────────────────────────────────

CUES["vo-market"]="Beef is at record highs. The American cow herd's at a sixty-five-year low. Labor's gone. Ranchers are aging out. Every ranch left has to do more, with fewer eyes on it. The herd already has a nervous system. The rancher doesn't."

CUES["vo-compare"]="Here's how it works today. A rancher drives two hundred miles a week, checks every trough, every fence, every sick cow. Best case: six runs a day. Anything between runs, you miss. Now. Same ranch. Five Claude Managed Agents, built on Opus 4.7. They watch every fence, every trough, every cow. Every minute. Four dollars and seventeen cents a week."

CUES["vo-mesh-opus"]="Each agent's its own Managed Agents session. Built on Opus 4.7. Idle-pause billing. When nothing's happening, the agent sleeps. Costs you nothing. Sensor wakes it, it does the work, goes back to sleep. That's how a whole ranch runs on four bucks a week of Claude. Every tool call gets signed. Every signature lands in a Merkle chain. Replay the whole day from a seed. Same input, same bytes, every time."

CUES["vo-close-substance"]="Eleven-hundred-six tests. Eighty-seven percent coverage. Every tool call signed with Ed25519. Clone the repo, run one command, watch the same five scenarios play out. Bit for bit."

CUES["vo-close-final"]="Beef at record highs. Cow herd at a sixty-five-year low. Now the ranch can watch itself."

# ─── Variant A ───────────────────────────────────────────────────────────────

CUES["vo-intro"]="I'm George. Senior at UNM. Part 107 drone ticket. I've spent a lot of nights on ranches in New Mexico. And one question kept coming up. What if the ranch just watched itself?"

# ─── Variant B ───────────────────────────────────────────────────────────────

CUES["vo-intro-B"]="Yeah. Four bucks a week. I'm George, I'm a senior at UNM, I've spent a lot of nights on ranches in New Mexico, and I've got a Part 107 drone ticket. SkyHerd is what came out of that. Five Claude agents. One ranch. Every fence, every trough, every cow."

# ─── Variant C ───────────────────────────────────────────────────────────────

CUES["vo-hook-C"]="I'm George. Senior at UNM, Part 107 drone ticket, a lot of nights on New Mexico ranches. SkyHerd. One ranch. Every fence. Every trough. Every cow."

CUES["vo-story-C"]="Beef is at record highs. The American cow herd's at a sixty-five-year low. Labor's gone. Ranchers are aging out. Here's how a ranch runs today. A guy drives two hundred miles a week, checks every trough, every fence, every sick cow. Six runs a day. Anything between runs, he misses. So. Same ranch. Five Claude Managed Agents, built on Opus 4.7. Every fence. Every trough. Every cow. Every minute. The herd already has a nervous system. The rancher finally does too."

CUES["vo-opus-C"]="Each agent's its own Managed Agents session. Built on Opus 4.7. Beta header. Prompt-cached system plus skills. When an agent's idle, billing stops. Costs nothing to have it standing by. One more thing. The per-word caption styling you're watching right now, the colors, the emphasis, the pacing, Opus 4.7 authored all of it. The model picks which words to hit. The repo commits the JSON."

CUES["vo-depth-C"]="Eleven-hundred-six tests. Eighty-seven percent coverage. Every tool call signed. Ed25519 Merkle chain. Replay the whole day from a seed. Same input, same bytes, every time."

CUES["vo-close-C"]="Beef at record highs. Cow herd at a sixty-five-year low. Now, finally, the ranch can watch itself."

# ─── Montage cues (A/B/C — fills 1:25-1:50 montage window) ──────────────────
# Each ~4s. Wired into MontageScene/CMontageScene via Audio overlay.
# These replace the previously silent montage window per locked decision #7.

CUES["vo-montage-sick"]="Cow A014. Eye-irritation pattern, eighty-three percent. Vet packet sent before he's awake."

CUES["vo-montage-tank"]="Tank seven dropped to eight P-S-I overnight. Drone flew the leak before sunrise."

CUES["vo-montage-calving"]="One-seventeen's going into labor at three-fourteen A-M. Priority page, priority response."

CUES["vo-montage-storm"]="Hail in forty-five minutes. Paddock B redirects to Shelter Two automatically."

# Bridge cue: ~3s, transition from montage into mesh reveal.
CUES["vo-montage-bridge"]="Five scenarios in one minute. One ranch. Zero humans on shift."

# ─── Meta-loop cues (A and B — ~4.5s each) ───────────────────────────────────
# Used in Phase 3 MetaLoopBeat inside ABAct3Close.tsx.

CUES["vo-meta-A"]="One more thing. The captions you've been reading — Opus 4.7 picked the colors, the weight, the timing. The model edits the video."

CUES["vo-meta-B"]="And the captions you've been reading? Opus 4.7 styled every word — color, weight, pacing. Same JSON, in the repo."

# ─── Inworld prosody overrides ───────────────────────────────────────────────
# Only populated where natural punctuation alone isn't enough for the
# Inworld model to land the right beat. Empty by default.
# Example:
#   CUES_INWORLD["vo-compare"]="Here's how it works today. ..."
