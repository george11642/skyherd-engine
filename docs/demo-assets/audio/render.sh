#!/usr/bin/env bash
# Pre-render the 3 Wes voice takes used in the submission video.
# Run from repo root. Requires: ELEVENLABS_API_KEY (best) or piper (fallback) or espeak (last resort).
#
#   bash docs/demo-assets/audio/render.sh
#
# WAVs land alongside this script: wes-coyote.wav, wes-sick-cow.wav, wes-close.wav

set -euo pipefail

cd "$(dirname "$0")/../../.."

OUT_DIR="docs/demo-assets/audio"
mkdir -p "$OUT_DIR"

if [ -z "${ELEVENLABS_API_KEY:-}" ]; then
  echo "[render] ELEVENLABS_API_KEY unset — will use local TTS fallback (piper → espeak → silent)."
fi

render_line() {
  local label="$1"
  local text="$2"
  local out="$OUT_DIR/wes-$label.wav"
  echo "[render] $label → $out"
  # skyherd-voice say writes a wav and plays it via aplay; we capture the path it prints.
  # To avoid playback on render machines, run with DISPLAY unset and ignore playback errors.
  local raw
  raw=$(uv run skyherd-voice say "$text" 2>&1 || true)
  local wrote
  wrote=$(echo "$raw" | awk '/^Wrote /{print $2}' | head -1)
  if [ -z "$wrote" ] || [ ! -f "$wrote" ]; then
    echo "[render] FAILED to render $label — output was:"
    echo "$raw"
    return 1
  fi
  cp -f "$wrote" "$out"
  echo "[render] saved $out"
}

render_line "coyote"   "Boss. Coyote at the south fence. Drone's on it."
render_line "sick-cow" "Boss. A014's got something in her left eye. Pulled together a vet packet for you."
render_line "close"    "That's the ranch taking care of itself, boss."

echo ""
echo "[render] Done. Files:"
ls -lh "$OUT_DIR"/*.wav 2>/dev/null || true
