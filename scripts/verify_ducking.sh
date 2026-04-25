#!/usr/bin/env bash
# verify_ducking.sh — post-render ducking gate for SkyHerd demo video.
#
# Usage: bash scripts/verify_ducking.sh <mastered.mp4>
#
# Reads a VO-segment sidecar JSON (<mastered.mp4>.vo-segments.json) if present,
# or falls back to hardcoded default windows derived from the Phase 6 S2
# VO schedule (30 fps, ~180 s composition, variant A/B skeleton).
#
# For each VO window it measures mean RMS (dBFS) via ffmpeg volumedetect,
# then compares against the mean RMS of the 3-second music-only gap preceding
# each window.
#
# Gate: gap_rms - vo_rms must be <= -6 dB
#       i.e. BGM must be at least 6 dB quieter DURING VO than in the gap before it.
#
# Exit 0  — all windows pass (or skipped due to N/A).
# Exit 1  — one or more windows fail the gate.
#
set -uo pipefail

MP4="${1:-}"
if [[ -z "$MP4" || ! -f "$MP4" ]]; then
  echo "Usage: $0 <mastered.mp4>" >&2
  exit 1
fi

command -v ffmpeg  >/dev/null 2>&1 || { echo "ERROR: ffmpeg not found" >&2; exit 1; }
command -v ffprobe >/dev/null 2>&1 || { echo "ERROR: ffprobe not found" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Determine total duration
# ---------------------------------------------------------------------------
DURATION=$(ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 "$MP4")
echo "[verify_ducking] File: $MP4  duration: ${DURATION}s"

# ---------------------------------------------------------------------------
# Load VO segments from sidecar JSON or use hardcoded defaults
# Sidecar format: [{"startFrame": N, "endFrame": M}, ...]  (30 fps)
# ---------------------------------------------------------------------------
SIDECAR="${MP4}.vo-segments.json"
FPS=30

VO_STARTS_S=()
VO_ENDS_S=()

if [[ -f "$SIDECAR" ]]; then
  echo "[verify_ducking] Loading VO segments from $SIDECAR"
  while IFS= read -r line; do
    VO_STARTS_S+=("$line")
  done < <(python3 -c "
import json, sys
segs = json.load(open(sys.argv[1]))
for s in segs:
    print(s['startFrame'] / $FPS)
" "$SIDECAR")
  while IFS= read -r line; do
    VO_ENDS_S+=("$line")
  done < <(python3 -c "
import json, sys
segs = json.load(open(sys.argv[1]))
for s in segs:
    print(s['endFrame'] / $FPS)
" "$SIDECAR")
else
  echo "[verify_ducking] No sidecar found — using hardcoded default VO windows (variant A/B, 30fps)"
  # Default VO windows for A/B variant at 30 fps, actDur.act1 ~= 75s
  VO_STARTS_S=( 8.0  22.0  38.5  57.0  77.0  105.0  150.0  168.0 )
  VO_ENDS_S=(  19.0  35.0  55.0  70.0   94.0  120.0  158.0  175.0 )
fi

N_SEGS=${#VO_STARTS_S[@]}
if [[ $N_SEGS -eq 0 ]]; then
  echo "[verify_ducking] No VO segments found — nothing to verify."
  exit 0
fi

# ---------------------------------------------------------------------------
# Helper: measure mean_volume (dBFS) over a time window via volumedetect
# Outputs a bare number like "-18.7" or "N/A"
# ---------------------------------------------------------------------------
measure_rms() {
  local file="$1"
  local start_s="$2"
  local dur_s="$3"

  # Clamp to file bounds
  local actual_dur
  actual_dur=$(python3 -c "
import sys
end = min(float('$start_s') + float('$dur_s'), float('$DURATION'))
d = max(0.0, end - float('$start_s'))
print(d)
")

  if python3 -c "import sys; sys.exit(0 if float('$actual_dur') < 0.2 else 1)" 2>/dev/null; then
    echo "N/A"
    return
  fi

  local raw
  raw=$(ffmpeg -v info \
    -ss "$start_s" -t "$actual_dur" \
    -i "$file" \
    -vn \
    -af "volumedetect" \
    -f null - 2>&1)

  local val
  val=$(echo "$raw" | grep "mean_volume" | tail -1 | sed -E 's/.*mean_volume: *([^ ]+) dB.*/\1/')

  echo "${val:-N/A}"
}

# ---------------------------------------------------------------------------
# Measure RMS for each VO window and the 3-second gap preceding it
# ---------------------------------------------------------------------------
GATE_DB=-6.0
PASS=0
FAIL=0

echo ""
printf "  %-14s | %-18s | %-13s | %-14s | %-6s | %s\n" \
  "Segment" "VO window (s)" "RMS_vo (dBFS)" "RMS_gap (dBFS)" "Delta" "Gate"
printf "  %s\n" "---------------|--------------------|--------------:|----------------|--------|------"

for i in "${!VO_STARTS_S[@]}"; do
  VO_S="${VO_STARTS_S[$i]}"
  VO_E="${VO_ENDS_S[$i]}"
  VO_DUR=$(python3 -c "print(max(0.0, $VO_E - $VO_S))")

  # 3-second music-only gap immediately before VO window
  GAP_END_S="$VO_S"
  GAP_START_S=$(python3 -c "print(max(0.0, $VO_S - 3.0))")
  GAP_DUR=$(python3 -c "print($GAP_END_S - $GAP_START_S)")

  RMS_VO=$(measure_rms  "$MP4" "$VO_S"      "$VO_DUR")
  RMS_GAP=$(measure_rms "$MP4" "$GAP_START_S" "$GAP_DUR")

  if [[ "$RMS_VO" == "N/A" || "$RMS_GAP" == "N/A" ]]; then
    STATUS="SKIP"
    DELTA="N/A"
  else
    # delta = gap_rms - vo_rms  (should be strongly negative: gap quieter than VO)
    DELTA=$(python3 -c "print(round($RMS_GAP - $RMS_VO, 2))")
    if python3 -c "import sys; sys.exit(0 if float('$DELTA') <= float('$GATE_DB') else 1)" 2>/dev/null; then
      ((PASS++)) || true
      STATUS="PASS"
    else
      ((FAIL++)) || true
      STATUS="FAIL"
    fi
  fi

  printf "  VO seg %2d      | %6.1f – %6.1f s   | %13s | %14s | %6s | %s\n" \
    "$((i+1))" "$VO_S" "$VO_E" "$RMS_VO" "$RMS_GAP" "${DELTA}" "$STATUS"
done

echo ""
echo "[verify_ducking] Results: ${PASS} PASS  ${FAIL} FAIL  (gate: gap_rms - vo_rms <= ${GATE_DB} dB)"

if [[ $FAIL -gt 0 ]]; then
  echo "[verify_ducking] GATE FAILED — BGM not ducked enough during VO segments." >&2
  exit 1
fi

echo "[verify_ducking] GATE PASSED."
exit 0
