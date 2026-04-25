#!/usr/bin/env bash
# Phase C VO render: regenerate the entire voice-over bus for the v2 demo cut.
#
# Voice: Antoni — ElevenLabs voice ID ErXwobaYiN019PkySvjV (neutral 19yo male,
# college-student-engineer tone). Selected during Phase C voice audition over
# Arnold-young (VR6AewLTigWG4xSOukaG) and Bill/Liam (pqHfZKP75CvOlQylNhV4) —
# Antoni reads closest to "19yo guy who built this in his dorm," which is the
# brand we want after retiring the Wes cowboy persona.
#
# Filename pattern: vo-*.mp3 (was wes-*.mp3 in v1). Variant-shared cues
# (vo-coyote, vo-sick-cow, vo-calving, vo-storm) get one MP3 used by A/B/C.
# Variant-specific cues are suffixed -B / -C; Variant A's intro/bridge are
# unsuffixed since A is the default render target.
#
# All outputs land in remotion-video/public/voiceover/ as 44.1 kHz stereo MP3,
# loudnormed to -18 LUFS.
#
# Idempotent: re-running re-renders all cues. The script reads the canonical
# text for every cue from the variant scripts in docs/scripts/.
#
# Requires: ELEVENLABS_API_KEY in env (sourced from .env.local), uv, ffmpeg.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Source .env.local if present so this is runnable as `bash scripts/render_vo_phase1.sh`.
if [ -f ".env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
fi

# Voice ID is locked at script level — overrideable via env for one-off
# auditions but the canonical pick is Antoni.
export ELEVENLABS_VOICE_ID="${ELEVENLABS_VOICE_ID:-ErXwobaYiN019PkySvjV}"
echo "[render] using voice_id=$ELEVENLABS_VOICE_ID (Antoni — neutral 19yo male)"

OUT_DIR="$REPO_ROOT/remotion-video/public/voiceover"
mkdir -p "$OUT_DIR"

render() {
  local label="$1"
  local text="$2"
  local out="$OUT_DIR/${label}.mp3"
  echo "[render] $label"
  local raw
  raw=$(uv run --extra voice skyherd-voice say "$text" 2>&1 || true)
  local wrote
  wrote=$(echo "$raw" | awk '/^Wrote /{print $2}' | head -1)
  if [ -z "$wrote" ] || [ ! -f "$wrote" ]; then
    echo "[render] FAILED to render $label — output:"
    echo "$raw"
    return 1
  fi
  ffmpeg -y -hide_banner -loglevel error \
    -i "$wrote" \
    -ac 2 -ar 44100 \
    -af "loudnorm=I=-18:TP=-1:LRA=11" \
    -c:a libmp3lame -b:a 192k \
    "$out"
  local dur
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out")
  echo "[render] saved $out (${dur}s)"
}

# ─── Variant-shared scenario cues (used by A, B, and C) ──────────────────────
render "vo-coyote"    "Heads up — coyote at the south fence. Drone's en route."
render "vo-sick-cow"  "Cow A014 — eye irritation, eighty-three percent confidence. Vet packet's on your phone."
render "vo-calving"   "Cow one-seventeen is going into labor. Pre-labor signals — flagged priority."
render "vo-storm"     "Hail in forty-five minutes. Moving the herd to shelter two."

# ─── Variant-shared market + close cues (used by A and B; C has its own variants) ──
render "vo-market"    "Beef is at record highs. The American cow herd is at a sixty-five-year low. Ranches can't hire their way out — labor is gone, and ranchers are aging out of the business. So every existing ranch has to do more, with fewer eyes on it. The herd already has a nervous system. The rancher does not."
render "vo-mesh"      "Each agent runs on its own Managed Agents session. They're idle until a sensor wakes them — and they go right back to idle when the work is done. That's how a ranch this size runs on four dollars a week of Claude. Every tool call gets signed. Every signature lands in a Merkle chain. The whole thing replays from a seed — same input, same bytes, every time."
render "vo-close-substance" "Eleven-hundred-six tests. Eighty-seven-percent coverage. An Ed25519 attestation chain. Clone the repo, run one command, watch the same five scenarios play out — bit-for-bit."
render "vo-close-final"     "Beef at record highs. Cow herd at a sixty-five-year low. Now the ranch can watch itself."

# ─── Variant A — Winner-pattern (identity / contrarian hook) ─────────────────
render "vo-intro"     "I'm George. I'm a senior at UNM, I've spent a lot of nights on ranches in New Mexico, and I have a Part 107 drone ticket. SkyHerd is my hackathon submission — what came out of asking one question. What if the ranch checked itself?"
render "vo-bridge"    "So we built one. Five Claude Managed Agents, watching one ranch, twenty-four-seven. Four dollars and seventeen cents a week."

# ─── Variant B — Hybrid (metric-first hook) ──────────────────────────────────
render "vo-intro-B"   "I'm George. I'm a senior at UNM, I've spent a lot of nights on ranches in New Mexico, and I have a Part 107 drone ticket. SkyHerd is my hackathon submission. Five Claude Managed Agents that watch one ranch — every fence, every trough, every cow."
render "vo-bridge-B"  "So we built one. Watch."

# ─── Variant C — Differentiated (5-act, dedicated substance + Opus beats) ────
render "vo-hook-C"    "I'm George — UNM senior, drone op. SkyHerd watches one ranch. Every fence. Every trough. Every cow."
render "vo-story-C"   "Beef is at record highs. The American cow herd is at a sixty-five-year low. Ranches can't hire their way out — labor is gone. Ranchers are aging out. Every existing ranch has to do more with fewer eyes on it. Coyotes don't read business hours. Hail doesn't wait for the next vet visit. A cow can be dying for seventy-two hours before anyone sees her. The herd already has a nervous system. The rancher does not. So we built one."
render "vo-synthesis-C" "Five agents. Idle until a sensor wakes them. Skills loaded per-task. Cost ticker freezes between events."
render "vo-opus-C"    "Each agent runs on its own Managed Agents session — Claude beta header, prompt-cached system + skills prefix. Idle-pause billing means a sleeping agent costs nothing. We also let Opus 4.7 author the on-screen captions you're reading right now — per-word semantic styling, generated as JSON, committed to the repo."
render "vo-depth-C"   "Eleven-hundred-six tests. Eighty-seven-percent coverage. Every tool call signed. Ed25519 Merkle chain. Replay from a seed — same input, same bytes. Every. Time."
render "vo-close-C"   "Beef at record highs. Cow herd at a sixty-five-year low. Now — finally — the ranch can watch itself."

echo ""
echo "[render] Done. Voiceover files:"
ls -lh "$OUT_DIR"/vo-*.mp3 2>/dev/null || true
