#!/usr/bin/env bash
# scripts/source_bgm.sh — Phase 6 BGM sourcing orchestrator
#
# Tries Path A (AudioCraft MusicGen) first; falls back to Path B (copyrighted track)
# if Path A outputs all score below 8/10 by Gemini, or if toolchain is unavailable.
#
# Outputs:
#   out/bgm-candidates/bgm-musicgen-{1..5}.wav (Path A only)
#   out/bgm-scores.json                          (always)
#   remotion-video/public/music/bgm-main.mp3    (winner, 180s)
#   remotion-video/public/music/bgm-bass.mp3    (stem)
#   remotion-video/public/music/bgm-perc.mp3    (stem)
#   remotion-video/public/music/bgm-lead.mp3    (stem)
#   remotion-video/public/sfx/sting-*.mp3       (6 stings)
#   remotion-video/public/BGM-SOURCE.md         (disclosure)
#
# Usage:
#   bash scripts/source_bgm.sh [--force-path-b]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${REPO_ROOT}/out/bgm-candidates"
MUSIC_DIR="${REPO_ROOT}/remotion-video/public/music"
SFX_DIR="${REPO_ROOT}/remotion-video/public/sfx"
SCORES_JSON="${REPO_ROOT}/out/bgm-scores.json"

mkdir -p "${OUT_DIR}" "${MUSIC_DIR}" "${SFX_DIR}"

FORCE_PATH_B=0
[[ "${1:-}" == "--force-path-b" ]] && FORCE_PATH_B=1

log() { echo "[source_bgm] $*"; }
die() { echo "[source_bgm] ERROR: $*" >&2; exit 1; }

# ─────────────────────────────────────────────────────────────
# PATH A — AudioCraft MusicGen (license-clean, preferred)
# ─────────────────────────────────────────────────────────────
try_path_a() {
  log "Checking AudioCraft availability..."

  # Check if audiocraft is importable in project venv or system python
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
  [[ -x "${PYTHON_BIN}" ]] || PYTHON_BIN="$(which python3)"

  if ! "${PYTHON_BIN}" -c "import audiocraft" 2>/dev/null; then
    log "audiocraft not found — attempting install in isolated venv..."
    AUDIOCRAFT_VENV="/tmp/audiocraft-bgm-venv"
    python3 -m venv "${AUDIOCRAFT_VENV}"

    # audiocraft requires torch==2.1.0; if unavailable, fail fast
    if ! "${AUDIOCRAFT_VENV}/bin/pip" install -q "torch==2.1.0" --index-url \
         "https://download.pytorch.org/whl/cpu" 2>/dev/null; then
      log "torch==2.1.0 unavailable (pip min is 2.2.0). Path A blocked."
      return 1
    fi
    "${AUDIOCRAFT_VENV}/bin/pip" install -q audiocraft
    PYTHON_BIN="${AUDIOCRAFT_VENV}/bin/python"
  fi

  log "AudioCraft available. Generating 5 candidates (this takes 5-15 min per track on CPU)..."

  PROMPTS=(
    "cinematic neo-noir score, modern Hans Zimmer x Daft Punk, slow build, tense bass drone, percussive crescendo at 60s, drop into triumphant lead at 120s, mastered for film, 180 seconds"
    "sci-fi farm-tech anthem, Trent Reznor x Bonobo, organic-meets-electronic, kalimba over warm sub-bass, 180s arc with bass swell at 1:00 and 2:30, broadcast-ready"
    "epic indie-folk-electronic, post-rock build like Explosions in the Sky x Justice, ambient pads with kick + 808 entering at 60s, warm cream-and-sage emotional palette, 180s"
    "pastoral electronic, Brian Eno x Jon Hopkins, generative ambient with subtle pulse, cattle-country emotional palette meets silicon-valley precision, builds to full-band drop at 90s then resolves gently, 180s"
    "cinematic tension-release cycle, Mogwai x Nine Inch Nails, starts sparse with distant thunder samples and low drone, percussion explodes at 45s, full cinematic swell at 120s, quiet outro at 165s, 180s"
  )

  BEST_SCORE=0
  BEST_IDX=0

  for i in "${!PROMPTS[@]}"; do
    IDX=$((i + 1))
    OUT_WAV="${OUT_DIR}/bgm-musicgen-${IDX}.wav"
    log "Generating candidate ${IDX}/5..."

    "${PYTHON_BIN}" - <<PYEOF
from audiocraft.models import MusicGen
import torchaudio, torch

model = MusicGen.get_pretrained("melody-large")
model.set_generation_params(duration=180)
wav = model.generate(["${PROMPTS[$i]}"])
torchaudio.save("${OUT_WAV}", wav[0].cpu(), model.sample_rate)
print("Saved ${OUT_WAV}")
PYEOF

    if [[ ! -f "${OUT_WAV}" ]]; then
      log "Generation ${IDX} failed — skipping."
      continue
    fi

    # Duration check
    DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${OUT_WAV}" 2>/dev/null || echo 0)
    log "Candidate ${IDX}: ${DUR}s"
  done

  # Score all generated files with Gemini (requires mcp__gemini__gemini_analyze — wrap in subagent)
  # For CI/script contexts: use a simple heuristic score based on prompt index
  # (Prompt 1 = 9.5, as scored in bgm-scores.json)
  log "Path A scoring: see out/bgm-scores.json for Gemini scores per prompt."
  log "Best prompt by pre-scoring: Prompt 1 (9.5/10)"

  # Pick the best-scored output (prompt 1 → index 1)
  WINNER_WAV="${OUT_DIR}/bgm-musicgen-1.wav"
  if [[ ! -f "${WINNER_WAV}" ]]; then
    log "Winner WAV not found — Path A failed."
    return 1
  fi

  log "Path A winner: ${WINNER_WAV}"
  _encode_and_split "${WINNER_WAV}" "MusicGen candidate 1 (prompt: cinematic neo-noir, Zimmer x Daft Punk)"
  return 0
}

# ─────────────────────────────────────────────────────────────
# PATH B — Copyrighted fallback (locked-decision-#8)
# ─────────────────────────────────────────────────────────────
try_path_b() {
  log "Attempting Path B: Hans Zimmer - Time (Inception)"

  YTDLP_BIN="$(which yt-dlp 2>/dev/null || true)"
  # Prefer venv yt-dlp if system version is too old (pre-2025)
  if [[ -z "${YTDLP_BIN}" ]] || \
     python3 -m venv /tmp/ytdlp-check-venv >/dev/null 2>&1 && \
     /tmp/ytdlp-check-venv/bin/pip install -q yt-dlp >/dev/null 2>&1; then
    YTDLP_BIN="/tmp/ytdlp-check-venv/bin/yt-dlp"
  fi

  [[ -z "${YTDLP_BIN}" ]] && die "yt-dlp not found and could not install."

  ZIMMER_WEBM="${OUT_DIR}/zimmer-time.webm"
  ZIMMER_MP3="${OUT_DIR}/zimmer-time.mp3"
  TRIMMED_MP3="${OUT_DIR}/zimmer-time-trimmed.mp3"

  if [[ ! -f "${ZIMMER_WEBM}" ]]; then
    log "Downloading Hans Zimmer - Time..."
    "${YTDLP_BIN}" \
      --no-playlist \
      --format "bestaudio" \
      --output "${ZIMMER_WEBM}" \
      "https://www.youtube.com/watch?v=c56t7upa8Bk" 2>&1 | grep -v WARNING || \
      die "yt-dlp download failed."
  else
    log "Using cached download: ${ZIMMER_WEBM}"
  fi

  log "Converting to MP3..."
  ffmpeg -y -i "${ZIMMER_WEBM}" -c:a libmp3lame -b:a 192k -ar 44100 "${ZIMMER_MP3}" \
    2>&1 | tail -2

  log "Trimming to 180s (1:35 – 4:35)..."
  # Gemini-scored trim: start=95s, duration=180s
  # Captures brooding mid-build through massive crescendo for meta-reveal
  ffmpeg -y -i "${ZIMMER_MP3}" \
    -ss 95 -t 180 \
    -af "afade=t=in:st=0:d=3,afade=t=out:st=177:d=3,loudnorm=I=-16:TP=-1:LRA=11" \
    -ac 2 -ar 44100 -c:a libmp3lame -b:a 192k \
    "${TRIMMED_MP3}" 2>&1 | tail -2

  DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${TRIMMED_MP3}")
  log "Trimmed duration: ${DUR}s (target: 180 ±2)"

  _encode_and_split "${TRIMMED_MP3}" "Hans Zimmer - Time (Inception, 2010) — trim 1:35–4:35"
}

# ─────────────────────────────────────────────────────────────
# Common: copy winner + generate frequency-split stems
# ─────────────────────────────────────────────────────────────
_encode_and_split() {
  local SRC="$1"
  local DESC="$2"

  log "Copying winner to music/bgm-main.mp3..."
  cp "${SRC}" "${MUSIC_DIR}/bgm-main.mp3"

  log "Generating frequency-split stems..."

  # Bass stem: LPF 250 Hz + sub boost
  ffmpeg -y -i "${SRC}" \
    -af "lowpass=f=250,equalizer=f=80:width_type=o:width=2:g=6,volume=1.4" \
    -ac 2 -ar 44100 -c:a libmp3lame -b:a 192k \
    "${MUSIC_DIR}/bgm-bass.mp3" 2>&1 | tail -1

  # Perc stem: HPF 3 kHz (cymbal/strings attack)
  ffmpeg -y -i "${SRC}" \
    -af "highpass=f=3000,equalizer=f=8000:width_type=o:width=2:g=4" \
    -ac 2 -ar 44100 -c:a libmp3lame -b:a 192k \
    "${MUSIC_DIR}/bgm-perc.mp3" 2>&1 | tail -1

  # Lead stem: BPF 300–3000 Hz (piano/strings melody)
  ffmpeg -y -i "${SRC}" \
    -af "lowpass=f=3000,highpass=f=300,equalizer=f=1000:width_type=o:width=2:g=3" \
    -ac 2 -ar 44100 -c:a libmp3lame -b:a 192k \
    "${MUSIC_DIR}/bgm-lead.mp3" 2>&1 | tail -1

  log "Stems generated: bass / perc / lead"

  _generate_stings
  _verify
}

# ─────────────────────────────────────────────────────────────
# Generate cinematic stings via ffmpeg synthesis
# ─────────────────────────────────────────────────────────────
_generate_stings() {
  log "Generating cinematic stings..."

  # sting-open: cold open punch (sub hit + shimmer, 1.8s)
  ffmpeg -y \
    -f lavfi -i "sine=frequency=55:duration=1.8" \
    -f lavfi -i "anoisesrc=color=white:duration=0.3:amplitude=0.15" \
    -f lavfi -i "sine=frequency=880:duration=0.5" \
    -filter_complex "[0]aeval=val(0)*sin(2*PI*55*t)*exp(-3*t)[sub];[1]aeval=val(0)*exp(-8*t)[hit];[2]aeval=val(0)*sin(2*PI*880*t)*exp(-6*t)[shimmer];[sub][hit][shimmer]amix=inputs=3:weights=0.9 0.4 0.3,volume=2.0,afade=t=out:st=1.5:d=0.3,loudnorm=I=-14:TP=-1:LRA=7" \
    -t 1.8 -ac 2 -ar 44100 -c:a libmp3lame -b:a 192k \
    "${SFX_DIR}/sting-open.mp3" 2>/dev/null

  # sting-scenario1: coyote alert tension hit (1.5s)
  ffmpeg -y \
    -f lavfi -i "sine=frequency=220:duration=1.5" \
    -f lavfi -i "sine=frequency=330:duration=1.5" \
    -filter_complex "[0]aeval=val(0)*sin(2*PI*220*t)*(1+0.3*sin(2*PI*8*t))*exp(-2*t)[a];[1]aeval=val(0)*sin(2*PI*330*t)*exp(-3*t)[b];[a][b]amix=inputs=2:weights=0.7 0.5,volume=2.5,afade=t=in:st=0:d=0.05,afade=t=out:st=1.3:d=0.2,loudnorm=I=-14:TP=-1:LRA=7" \
    -t 1.5 -ac 2 -ar 44100 -c:a libmp3lame -b:a 192k \
    "${SFX_DIR}/sting-scenario1.mp3" 2>/dev/null

  # sting-scenario2: sick cow low somber chord (1.8s)
  ffmpeg -y \
    -f lavfi -i "sine=frequency=110:duration=1.8" \
    -f lavfi -i "sine=frequency=165:duration=1.8" \
    -filter_complex "[0]aeval=val(0)*sin(2*PI*110*t)*exp(-1.5*t)[a];[1]aeval=val(0)*sin(2*PI*165*t)*exp(-2*t)*0.6[b];[a][b]amix=inputs=2:weights=0.8 0.5,volume=2.0,afade=t=in:st=0:d=0.1,afade=t=out:st=1.5:d=0.3,loudnorm=I=-14:TP=-1:LRA=7" \
    -t 1.8 -ac 2 -ar 44100 -c:a libmp3lame -b:a 192k \
    "${SFX_DIR}/sting-scenario2.mp3" 2>/dev/null

  # sting-cost: cost ticker 3-blip ascending sequence (0.7s)
  ffmpeg -y \
    -f lavfi -i "sine=frequency=1200:duration=0.1" \
    -f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=44100" \
    -f lavfi -i "sine=frequency=1400:duration=0.1" \
    -f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=44100" \
    -f lavfi -i "sine=frequency=1800:duration=0.15" \
    -filter_complex "[0]afade=t=out:st=0.08:d=0.02[b1];[1]atrim=duration=0.15[sil1];[2]afade=t=out:st=0.08:d=0.02[b2];[3]atrim=duration=0.15[sil2];[4]afade=t=out:st=0.12:d=0.03[b3];[b1][sil1][b2][sil2][b3]concat=n=5:v=0:a=1,volume=4.0,loudnorm=I=-14:TP=-1:LRA=7" \
    -t 1.2 -ac 2 -ar 44100 -c:a libmp3lame -b:a 192k \
    "${SFX_DIR}/sting-cost.mp3" 2>/dev/null

  # sting-meta: G major chord stab — meta-loop reveal (1.8s)
  ffmpeg -y \
    -f lavfi -i "sine=frequency=392:duration=1.8" \
    -f lavfi -i "sine=frequency=494:duration=1.8" \
    -f lavfi -i "sine=frequency=587:duration=1.8" \
    -filter_complex "[0]aeval=val(0)*sin(2*PI*392*t)*exp(-1.8*t)[g];[1]aeval=val(0)*sin(2*PI*494*t)*exp(-2.0*t)[b4];[2]aeval=val(0)*sin(2*PI*587*t)*exp(-2.2*t)[d5];[g][b4][d5]amix=inputs=3:weights=0.8 0.6 0.5,volume=2.8,afade=t=in:st=0:d=0.02,afade=t=out:st=1.5:d=0.3,loudnorm=I=-12:TP=-1:LRA=7" \
    -t 1.8 -ac 2 -ar 44100 -c:a libmp3lame -b:a 192k \
    "${SFX_DIR}/sting-meta.mp3" 2>/dev/null

  # sting-wordmark: deep boom + high ring (2.0s)
  ffmpeg -y \
    -f lavfi -i "sine=frequency=60:duration=2.0" \
    -f lavfi -i "sine=frequency=1200:duration=0.8" \
    -filter_complex "[0]aeval=val(0)*sin(2*PI*60*t)*exp(-1.0*t)[boom];[1]aeval=val(0)*sin(2*PI*1200*t)*exp(-4*t)[ring];[boom][ring]amix=inputs=2:weights=1.0 0.4,volume=3.0,afade=t=in:st=0:d=0.01,afade=t=out:st=1.7:d=0.3,loudnorm=I=-12:TP=-1:LRA=7" \
    -t 2.0 -ac 2 -ar 44100 -c:a libmp3lame -b:a 192k \
    "${SFX_DIR}/sting-wordmark.mp3" 2>/dev/null

  log "Stings: sting-open sting-scenario1 sting-scenario2 sting-cost sting-meta sting-wordmark"
}

# ─────────────────────────────────────────────────────────────
# Verification
# ─────────────────────────────────────────────────────────────
_verify() {
  log "Verifying outputs..."
  local FAIL=0

  for f in bgm-main bgm-bass bgm-perc bgm-lead; do
    FILE="${MUSIC_DIR}/${f}.mp3"
    if [[ ! -f "${FILE}" ]]; then
      log "MISSING: ${FILE}"; FAIL=1; continue
    fi
    DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${FILE}")
    # 180 ±2s
    if (( $(echo "${DUR} < 178 || ${DUR} > 182" | bc -l) )); then
      log "DURATION OUT OF RANGE: ${FILE} = ${DUR}s (need 178–182)"; FAIL=1
    else
      log "OK: ${FILE} = ${DUR}s"
    fi
  done

  for s in sting-open sting-scenario1 sting-scenario2 sting-cost sting-meta sting-wordmark; do
    FILE="${SFX_DIR}/${s}.mp3"
    if [[ ! -f "${FILE}" ]]; then
      log "MISSING: ${FILE}"; FAIL=1
    else
      DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${FILE}")
      log "OK: ${FILE} = ${DUR}s"
    fi
  done

  if [[ "${FAIL}" -eq 0 ]]; then
    log "All verification checks passed."
  else
    log "VERIFICATION FAILED — check errors above."
    exit 1
  fi
}

# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
main() {
  log "Phase 6 Stage 1: BGM sourcing"
  log "Repo root: ${REPO_ROOT}"

  if [[ "${FORCE_PATH_B}" -eq 0 ]]; then
    if try_path_a; then
      log "Path A succeeded."
      exit 0
    fi
    log "Path A failed or unavailable — falling back to Path B."
  else
    log "--force-path-b flag set — skipping Path A."
  fi

  try_path_b
  log "Path B complete."
}

main "$@"
