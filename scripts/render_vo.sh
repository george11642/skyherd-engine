#!/usr/bin/env bash
# render_vo.sh — VO render bus for SkyHerd demo video.
#
# Usage:
#   bash scripts/render_vo.sh [--provider {inworld|elevenlabs}]
#   SKYHERD_TTS_PROVIDER=elevenlabs bash scripts/render_vo.sh
#
# Flags:
#   --provider inworld      Use Inworld TTS (default; voice: Nate)
#   --provider elevenlabs   Use ElevenLabs (fallback; voice: Will)
#
# SHA256 cache:
#   hash = sha256(text + voice_id + model_id)
#   cache dir: remotion-video/public/voiceover/.cache/{hash}.mp3
#   manifest:  remotion-video/public/voiceover/.cache/manifest.json
#   On cache hit: copy to target, skip API call.
#
# Output:
#   remotion-video/public/voiceover/vo-*.mp3  (44.1 kHz stereo, -18 LUFS)
#
# Cue source:
#   scripts/vo_cues.sh  (21 total: 14 existing + 5 montage + 2 meta-loop)
#
# SECURITY: INWORLD_API_KEY and ELEVENLABS_API_KEY are sourced from .env.local.
#   Never logged, never committed.
#
# Requires: curl, ffmpeg, ffprobe, python3.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# ─── Source .env.local ────────────────────────────────────────────────────────
if [ -f ".env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
fi

# ─── Parse args ───────────────────────────────────────────────────────────────
PROVIDER="${SKYHERD_TTS_PROVIDER:-inworld}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --provider)
      PROVIDER="$2"
      shift 2
      ;;
    *)
      echo "[render_vo] Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "$PROVIDER" != "inworld" && "$PROVIDER" != "elevenlabs" ]]; then
  echo "[render_vo] --provider must be 'inworld' or 'elevenlabs'" >&2
  exit 1
fi

echo "[render_vo] provider=$PROVIDER"

# ─── Source cue library ───────────────────────────────────────────────────────
# shellcheck source=scripts/vo_cues.sh
source "$REPO_ROOT/scripts/vo_cues.sh"

# ─── Provider config ──────────────────────────────────────────────────────────
if [[ "$PROVIDER" == "inworld" ]]; then
  if [ -z "${INWORLD_API_KEY:-}" ]; then
    echo "[render_vo] INWORLD_API_KEY not set — aborting" >&2
    exit 1
  fi
  INWORLD_MODEL="inworld-tts-1.5-max"
  INWORLD_VOICE="Nate"  # Conversational, sociable male; picked via make video-vo-audition
else
  if [ -z "${ELEVENLABS_API_KEY:-}" ]; then
    echo "[render_vo] ELEVENLABS_API_KEY not set — aborting" >&2
    exit 1
  fi
  EL_VOICE_ID="bIHbv24MWmeRgasZH58o"  # Will
  EL_MODEL_ID="${ELEVENLABS_MODEL_ID:-eleven_v3}"
  EL_FALLBACK_MODEL="eleven_turbo_v2_5"
  EL_VOICE_SETTINGS='{"stability":0.5,"similarity_boost":0.75,"style":0.4,"use_speaker_boost":true}'
  echo "[render_vo] voice_id=$EL_VOICE_ID model=$EL_MODEL_ID (fallback=$EL_FALLBACK_MODEL)"
fi

OUT_DIR="$REPO_ROOT/remotion-video/public/voiceover"
CACHE_DIR="$OUT_DIR/.cache"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
mkdir -p "$OUT_DIR" "$CACHE_DIR"

MANIFEST_FILE="$CACHE_DIR/manifest.json"
# Bootstrap manifest if it doesn't exist
if [ ! -f "$MANIFEST_FILE" ]; then
  echo '{}' > "$MANIFEST_FILE"
fi

# ─── SHA256 cache helpers ─────────────────────────────────────────────────────
cache_key() {
  local text="$1" voice_id="$2" model_id="$3"
  echo -n "${text}${voice_id}${model_id}" | sha256sum | cut -d' ' -f1
}

cache_get() {
  local hash="$1"
  local cached="$CACHE_DIR/${hash}.mp3"
  if [ -f "$cached" ]; then
    echo "$cached"
  fi
}

cache_put() {
  local hash="$1" src="$2" label="$3" voice_id="$4" model_id="$5"
  local cached="$CACHE_DIR/${hash}.mp3"
  cp "$src" "$cached"
  # Update manifest
  python3 -c "
import json, sys
path = sys.argv[1]
try:
    with open(path) as f:
        m = json.load(f)
except Exception:
    m = {}
m[sys.argv[2]] = {'label': sys.argv[3], 'voice_id': sys.argv[4], 'model_id': sys.argv[5]}
with open(path, 'w') as f:
    json.dump(m, f, indent=2)
" "$MANIFEST_FILE" "$hash" "$label" "$voice_id" "$model_id"
}

# ─── Provider render functions ────────────────────────────────────────────────

render_inworld() {
  local label="$1" text="$2" out="$3"
  local raw="$TMP_DIR/${label}.raw"

  local payload
  payload=$(python3 -c "
import json, sys
print(json.dumps({
  'text': sys.argv[1],
  'voiceId': sys.argv[2],
  'modelId': sys.argv[3],
  'audioConfig': {
    'audioEncoding': 'MP3',
    'sampleRateHertz': 44100
  },
  'temperature': 0.8,
  'applyTextNormalization': 'ON'
}))
" "$text" "$INWORLD_VOICE" "$INWORLD_MODEL")

  local http
  http=$(curl -sS -w '%{http_code}' -X POST \
    "https://api.inworld.ai/tts/v1/voice" \
    -H "Authorization: Basic ${INWORLD_API_KEY}" \
    -H "Content-Type: application/json" \
    -o "$raw" \
    -d "$payload")

  if [ "$http" != "200" ]; then
    echo "[render_vo] Inworld HTTP $http for $label" >&2
    cat "$raw" >&2 || true
    return 1
  fi

  # Decode base64 audioContent from JSON response
  local decoded="$TMP_DIR/${label}.mp3"
  python3 -c "
import json, base64, sys
with open(sys.argv[1], 'rb') as f:
    data = json.load(f)
audio = base64.b64decode(data.get('audioContent', ''))
with open(sys.argv[2], 'wb') as f:
    f.write(audio)
" "$raw" "$decoded"

  master "$decoded" "$out"
}

render_elevenlabs() {
  local label="$1" text="$2" out="$3"
  local raw="$TMP_DIR/${label}.raw.mp3"
  local model_id="$EL_MODEL_ID"

  local payload
  payload=$(python3 -c "
import json, sys
print(json.dumps({
  'text': sys.argv[1],
  'model_id': sys.argv[2],
  'voice_settings': json.loads(sys.argv[3]),
}))
" "$text" "$model_id" "$EL_VOICE_SETTINGS")

  local http
  http=$(curl -sS -w '%{http_code}' -X POST \
    "https://api.elevenlabs.io/v1/text-to-speech/${EL_VOICE_ID}" \
    -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
    -H "Content-Type: application/json" \
    -o "$raw" \
    -d "$payload")

  if [ "$http" != "200" ]; then
    echo "[render_vo] $model_id HTTP $http for $label — retrying with $EL_FALLBACK_MODEL" >&2
    payload=$(python3 -c "
import json, sys
print(json.dumps({
  'text': sys.argv[1],
  'model_id': sys.argv[2],
  'voice_settings': json.loads(sys.argv[3]),
}))
" "$text" "$EL_FALLBACK_MODEL" "$EL_VOICE_SETTINGS")
    http=$(curl -sS -w '%{http_code}' -X POST \
      "https://api.elevenlabs.io/v1/text-to-speech/${EL_VOICE_ID}" \
      -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
      -H "Content-Type: application/json" \
      -o "$raw" \
      -d "$payload")
    if [ "$http" != "200" ]; then
      echo "[render_vo] ElevenLabs fallback also failed HTTP=$http for $label" >&2
      cat "$raw" >&2 || true
      return 1
    fi
  fi

  master "$raw" "$out"
}

# ─── Shared two-pass loudnorm master ─────────────────────────────────────────
# Target: -18 LUFS, TP=-1, LRA=11 (pre-mix level; final video masters to -16).
master() {
  local raw_in="$1" final_out="$2"

  ffmpeg -y -hide_banner -loglevel error \
    -i "$raw_in" \
    -ac 2 -ar 44100 \
    -af "loudnorm=I=-18:TP=-1:LRA=11" \
    -c:a libmp3lame -b:a 192k \
    "$final_out"
}

# ─── Dispatch one cue ─────────────────────────────────────────────────────────
render() {
  local label="$1" text="$2"
  local out="$OUT_DIR/${label}.mp3"

  # Check for provider-specific override text
  local actual_text="$text"
  if [[ "$PROVIDER" == "inworld" ]] && [[ -n "${CUES_INWORLD[$label]+x}" ]]; then
    actual_text="${CUES_INWORLD[$label]}"
    echo "[render_vo] $label (inworld-override)"
  else
    echo "[render_vo] $label"
  fi

  # Cache lookup
  local vid model
  if [[ "$PROVIDER" == "inworld" ]]; then
    vid="$INWORLD_VOICE"
    model="$INWORLD_MODEL"
  else
    vid="$EL_VOICE_ID"
    model="$EL_MODEL_ID"
  fi
  local hash
  hash=$(cache_key "$actual_text" "$vid" "$model")
  local cached
  cached=$(cache_get "$hash")
  if [ -n "$cached" ]; then
    echo "[render_vo] cache hit $label ($hash)"
    cp "$cached" "$out"
    return
  fi

  # Render
  local tmp_out="$TMP_DIR/${label}.mastered.mp3"
  if [[ "$PROVIDER" == "inworld" ]]; then
    render_inworld "$label" "$actual_text" "$tmp_out"
  else
    render_elevenlabs "$label" "$actual_text" "$tmp_out"
  fi

  cp "$tmp_out" "$out"
  cache_put "$hash" "$out" "$label" "$vid" "$model"

  local dur
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out")
  echo "[render_vo] saved $out (${dur}s)"
}

# ─── Render all 21 cues ───────────────────────────────────────────────────────
# Order follows plan Phase 2: existing 14 + 5 montage + 2 meta-loop.

# Shared (A/B/C)
render "vo-coyote-deep"       "${CUES["vo-coyote-deep"]}"

# Shared (A/B)
render "vo-market"             "${CUES["vo-market"]}"
render "vo-compare"            "${CUES["vo-compare"]}"
render "vo-mesh-opus"          "${CUES["vo-mesh-opus"]}"
render "vo-close-substance"    "${CUES["vo-close-substance"]}"
render "vo-close-final"        "${CUES["vo-close-final"]}"

# Variant A
render "vo-intro"              "${CUES["vo-intro"]}"

# Variant B
render "vo-intro-B"            "${CUES["vo-intro-B"]}"

# Variant C
render "vo-hook-C"             "${CUES["vo-hook-C"]}"
render "vo-story-C"            "${CUES["vo-story-C"]}"
render "vo-opus-C"             "${CUES["vo-opus-C"]}"
render "vo-depth-C"            "${CUES["vo-depth-C"]}"
render "vo-close-C"            "${CUES["vo-close-C"]}"

# Montage cues (fills previously-silent 1:25-1:50 window)
render "vo-montage-sick"       "${CUES["vo-montage-sick"]}"
render "vo-montage-tank"       "${CUES["vo-montage-tank"]}"
render "vo-montage-calving"    "${CUES["vo-montage-calving"]}"
render "vo-montage-storm"      "${CUES["vo-montage-storm"]}"
render "vo-montage-bridge"     "${CUES["vo-montage-bridge"]}"

# Meta-loop cues (Phase 3 MetaLoopBeat wires these)
render "vo-meta-A"             "${CUES["vo-meta-A"]}"
render "vo-meta-B"             "${CUES["vo-meta-B"]}"

echo ""
echo "[render_vo] Done. Active voiceover cues:"
ls -lh "$OUT_DIR"/vo-*.mp3 2>/dev/null || true
