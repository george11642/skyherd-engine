#!/usr/bin/env bash
# Phase H iter2 VO render: regenerate the entire voice-over bus for the
# humanized + restructured demo cut.
#
# Voice pick (iter2): Will — ElevenLabs voice ID bIHbv24MWmeRgasZH58o
# (modern conversational male). Swapped off Antoni (ErXwobaYiN019PkySvjV)
# because Antoni read as a narrator — too clinical, too broadcast. Will
# respects beats (holds pauses in "Now? He sleeps."), doesn't oversell
# the metric, reads "four bucks a week" with a shrug instead of a pitch.
#
# Audition (2026-04-24): same cue ran through Will/Brian/Chris × v3/turbo.
# Will on eleven_v3 landed the 16-word cue at 6.6s with real pause
# weight; Brian was steady-but-flat at 5.8s; Chris was hurried at 5.4s.
# Will on v3 wins on "sounds like a friend telling you about a thing he
# built," which is the brief straight from George.
#
# Model: eleven_v3 (available on this account, checked via HTTP 200 on
# 2026-04-24). Fallback: eleven_turbo_v2_5 if v3 returns 404 per-cue.
#
# Voice settings: stability=0.5, similarity_boost=0.75, style=0.4,
# use_speaker_boost=true. Tuned for conversational not broadcast.
#
# Cue bus (iter2):
#   Shared:    vo-coyote-deep, vo-market, vo-compare, vo-mesh-opus,
#              vo-close-substance, vo-close-final
#   Variant A: vo-intro
#   Variant B: vo-intro-B
#   Variant C: vo-hook-C, vo-story-C, vo-opus-C, vo-depth-C, vo-close-C
#
# Retired cues (no longer in any script; files left on disk but not
# re-rendered — will appear stale in git. Sweep on commit):
#   vo-coyote, vo-sick-cow, vo-calving, vo-storm (replaced by
#   vo-coyote-deep + silent montage),
#   vo-bridge, vo-bridge-B (replaced by vo-compare),
#   vo-mesh (replaced by vo-mesh-opus which names Opus 4.7 explicitly),
#   vo-synthesis-C (silent in iter2; music carries).
#
# All outputs land in remotion-video/public/voiceover/ as 44.1 kHz stereo
# MP3 loudnormed to -18 LUFS. Idempotent — re-running re-renders all
# active cues.
#
# Requires: ELEVENLABS_API_KEY in env (sourced from .env.local), curl,
# ffmpeg, python3.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Source .env.local if present so this is runnable as
# `bash scripts/render_vo_phase1.sh`.
if [ -f ".env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
fi

if [ -z "${ELEVENLABS_API_KEY:-}" ]; then
  echo "[render] ELEVENLABS_API_KEY not set in env or .env.local — aborting"
  exit 1
fi

VOICE_ID="${ELEVENLABS_VOICE_ID:-bIHbv24MWmeRgasZH58o}"
MODEL_ID="${ELEVENLABS_MODEL_ID:-eleven_v3}"
FALLBACK_MODEL="eleven_turbo_v2_5"
echo "[render] voice_id=$VOICE_ID model=$MODEL_ID (fallback=$FALLBACK_MODEL)"

OUT_DIR="$REPO_ROOT/remotion-video/public/voiceover"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
mkdir -p "$OUT_DIR"

# Voice settings JSON — tuned for conversational.
VOICE_SETTINGS_JSON='{"stability":0.5,"similarity_boost":0.75,"style":0.4,"use_speaker_boost":true}'

render() {
  local label="$1"
  local text="$2"
  local out="$OUT_DIR/${label}.mp3"
  local raw="$TMP_DIR/${label}.raw.mp3"
  echo "[render] $label"

  local payload
  payload=$(python3 -c "
import json, sys
print(json.dumps({
  'text': sys.argv[1],
  'model_id': sys.argv[2],
  'voice_settings': json.loads(sys.argv[3]),
}))
" "$text" "$MODEL_ID" "$VOICE_SETTINGS_JSON")

  local http
  http=$(curl -sS -w '%{http_code}' -X POST \
    "https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}" \
    -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
    -H "Content-Type: application/json" \
    -o "$raw" \
    -d "$payload")

  if [ "$http" != "200" ]; then
    echo "[render] $MODEL_ID returned HTTP $http for $label — retrying with $FALLBACK_MODEL"
    payload=$(python3 -c "
import json, sys
print(json.dumps({
  'text': sys.argv[1],
  'model_id': sys.argv[2],
  'voice_settings': json.loads(sys.argv[3]),
}))
" "$text" "$FALLBACK_MODEL" "$VOICE_SETTINGS_JSON")

    http=$(curl -sS -w '%{http_code}' -X POST \
      "https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}" \
      -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
      -H "Content-Type: application/json" \
      -o "$raw" \
      -d "$payload")

    if [ "$http" != "200" ]; then
      echo "[render] fallback also failed HTTP=$http for $label"
      cat "$raw" || true
      return 1
    fi
  fi

  ffmpeg -y -hide_banner -loglevel error \
    -i "$raw" \
    -ac 2 -ar 44100 \
    -af "loudnorm=I=-18:TP=-1:LRA=11" \
    -c:a libmp3lame -b:a 192k \
    "$out"

  local dur
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out")
  echo "[render] saved $out (${dur}s)"
}

# ─── Shared cues (used across A/B, or across A/B/C where noted) ──────────────
render "vo-coyote-deep" "Three-fourteen in the morning. Thermal on the south fence catches something. FenceLineDispatcher, one of the five agents, wakes up, looks at the frame, says yeah, coyote. Ninety-one percent. Sends the drone. Drone flies it, scares it off, flies home. You get a text. Nobody woke up. Nothing got eaten. Every step signed, hashed, in the ledger."
render "vo-market"      "Beef is at record highs. The American cow herd's at a sixty-five-year low. Labor's gone. Ranchers are aging out. Every ranch left has to do more, with fewer eyes on it. The herd already has a nervous system. The rancher doesn't."
render "vo-compare"     "Here's how it works today. A rancher drives two hundred miles a week, checks every trough, every fence, every sick cow. Best case: six runs a day. Anything between runs, you miss. Now. Same ranch. Five Claude Managed Agents, built on Opus 4.7. They watch every fence, every trough, every cow. Every minute. Four dollars and seventeen cents a week."
render "vo-mesh-opus"   "Each agent's its own Managed Agents session. Built on Opus 4.7. Idle-pause billing. When nothing's happening, the agent sleeps. Costs you nothing. Sensor wakes it, it does the work, goes back to sleep. That's how a whole ranch runs on four bucks a week of Claude. Every tool call gets signed. Every signature lands in a Merkle chain. Replay the whole day from a seed. Same input, same bytes, every time."
render "vo-close-substance" "Eleven-hundred-six tests. Eighty-seven percent coverage. Every tool call signed with Ed25519. Clone the repo, run one command, watch the same five scenarios play out. Bit for bit."
render "vo-close-final" "Beef at record highs. Cow herd at a sixty-five-year low. Now the ranch can watch itself."

# ─── Variant A — contrarian hook ─────────────────────────────────────────────
render "vo-intro"       "I'm George. Senior at UNM. Part 107 drone ticket. I've spent a lot of nights on ranches in New Mexico. And one question kept coming up. What if the ranch just watched itself?"

# ─── Variant B — metric-first hook ───────────────────────────────────────────
render "vo-intro-B"     "Yeah. Four bucks a week. I'm George, I'm a senior at UNM, I've spent a lot of nights on ranches in New Mexico, and I've got a Part 107 drone ticket. SkyHerd is what came out of that. Five Claude agents. One ranch. Every fence, every trough, every cow."

# ─── Variant C — 5-act differentiated ────────────────────────────────────────
render "vo-hook-C"      "I'm George. Senior at UNM, Part 107 drone ticket, a lot of nights on New Mexico ranches. SkyHerd. One ranch. Every fence. Every trough. Every cow."
render "vo-story-C"     "Beef is at record highs. The American cow herd's at a sixty-five-year low. Labor's gone. Ranchers are aging out. Here's how a ranch runs today. A guy drives two hundred miles a week, checks every trough, every fence, every sick cow. Six runs a day. Anything between runs, he misses. So. Same ranch. Five Claude Managed Agents, built on Opus 4.7. Every fence. Every trough. Every cow. Every minute. The herd already has a nervous system. The rancher finally does too."
render "vo-opus-C"      "Each agent's its own Managed Agents session. Built on Opus 4.7. Beta header. Prompt-cached system plus skills. When an agent's idle, billing stops. Costs nothing to have it standing by. One more thing. The per-word caption styling you're watching right now, the colors, the emphasis, the pacing, Opus 4.7 authored all of it. The model picks which words to hit. The repo commits the JSON."
render "vo-depth-C"     "Eleven-hundred-six tests. Eighty-seven percent coverage. Every tool call signed. Ed25519 Merkle chain. Replay the whole day from a seed. Same input, same bytes, every time."
render "vo-close-C"     "Beef at record highs. Cow herd at a sixty-five-year low. Now, finally, the ranch can watch itself."

echo ""
echo "[render] Done. Active voiceover cues:"
ls -lh "$OUT_DIR"/vo-*.mp3 2>/dev/null || true
