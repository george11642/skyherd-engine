#!/usr/bin/env bash
# Phase 1 VO render: 7 new Wes lines + convert 3 existing WAVs.
# All outputs land in remotion-video/public/voiceover/ as 44.1 kHz stereo MP3, loudnormed to -18 LUFS.
#
# Requires: ELEVENLABS_API_KEY in env, uv, ffmpeg.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

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
  # wrote is an MP3 masquerading as .wav (ElevenLabs path returns MP3 bytes).
  # Normalize: force 44.1kHz stereo MP3, -18 LUFS integrated.
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

convert_existing() {
  local label="$1"
  local src="docs/demo-assets/audio/${label}.wav"
  local out="$OUT_DIR/${label}.mp3"
  if [ ! -f "$src" ]; then
    echo "[convert] SKIP — missing $src"
    return 0
  fi
  echo "[convert] $label"
  ffmpeg -y -hide_banner -loglevel error \
    -i "$src" \
    -ac 2 -ar 44100 \
    -af "loudnorm=I=-18:TP=-1:LRA=11" \
    -c:a libmp3lame -b:a 192k \
    "$out"
  local dur
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out")
  echo "[convert] saved $out (${dur}s)"
}

# 7 new Wes VO lines
render "wes-calving"     "Boss. 117 is fixin' to calve. You'll want to see this one."
render "wes-storm"       "Boss. Hail inbound. Movin' the herd to paddock six."
render "wes-establish"   "One ranch. Five agents. Thirty-three domain skill files. Idle until the sensors call them."
render "wes-synthesis"   "Each agent runs on its own Managed Agents session and only wakes when the sensors call it. The skills library loads just what the task needs. Sessions persist so the predator learner actually learns. And the cost ticker freezes in between — this whole ranch runs at four dollars a week."
render "wes-attest"      "Ed25519 Merkle chain. Every tool call signed. Reproducible in a fresh clone in under three minutes — same seed, same bytes, every run. That's the underwriting data we think insurance will pay for in year two."
render "wes-george-hook" "George here. Licensed drone op, spent a lot of time on ranches in New Mexico. Wanted to know — what if the ranch checked itself?"
render "wes-why"         "Beef is at record highs. The cow herd is at a 65-year low. Ranchers can't hire their way out of this. The ranch has to watch itself."

# Existing WAVs in docs/demo-assets/audio/ turned out to be 250ms SilentBackend
# placeholders, not real TTS. Re-render fresh via ElevenLabs here.
render "wes-coyote"   "Boss. Coyote at the south fence. Drone's on it."
render "wes-sick-cow" "Boss. A014's got something in her left eye. Pulled together a vet packet for you."
render "wes-close"    "That's the ranch takin' care of itself, boss."

echo ""
echo "[render] Done. Voiceover files:"
ls -lh "$OUT_DIR"/*.mp3 2>/dev/null || true
