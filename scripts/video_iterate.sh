#!/usr/bin/env bash
# video_iterate.sh <variant: A|B|C> [--iter N] [--no-render] [--no-gemini] [--dry-run]
#
# Phase 4: Autonomous iteration nervous system.
# One round of the loop:
#   1. Render (Remotion → MP4)
#   2. Sample stills (ffmpeg 2fps → JPEGs)
#   3. Opus stills scoring (score_stills_opus.py — 30 batches, async, cached)
#   4. Gemini critique (Claude Code subagent wrapping mcp__gemini__gemini_analyze)
#   5. Aggregate (aggregate_score.py → score md + iter-history JSON)
#   6. Regression check (revert if any dim drops >0.3 vs prior iter)
#   7. Auto-apply top fix (auto_apply_fix.py → Claude Code subagent → compile + commit)
#
# Hard caps:
#   12 iters per variant  (ITER_HARD_CAP)
#   3 rollbacks per round (ROLLBACK_CAP)
#
# Exit codes:
#   0   Round complete — more iterations possible
#   2   Ship gate passed — stop iterating
#   3   Plateau reached — stop iterating
#   4   Hard cap reached — stop iterating
#   1   Fatal error

set -euo pipefail

# ── Args ──────────────────────────────────────────────────────────────────────
VARIANT="${1:?Usage: $0 <A|B|C> [--iter N] [--no-render] [--no-gemini] [--dry-run]}"
shift

ITER=""
NO_RENDER=0
NO_GEMINI=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --iter)       ITER="$2"; shift 2 ;;
    --no-render)  NO_RENDER=1; shift ;;
    --no-gemini)  NO_GEMINI=1; shift ;;
    --dry-run)    DRY_RUN=1; shift ;;
    *)            echo "Unknown flag: $1"; exit 1 ;;
  esac
done

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_BASE="${PROJECT_ROOT}/out"
PLANNING="${PROJECT_ROOT}/.planning/research"
SCRIPTS="${PROJECT_ROOT}/scripts"
REMOTION_DIR="${PROJECT_ROOT}/remotion-video"

# ── Determine current iteration ───────────────────────────────────────────────
ITER_HISTORY="${OUT_BASE}/iter-history-${VARIANT}.json"
ITER_HARD_CAP=12

if [[ -z "${ITER}" ]]; then
  if [[ -f "${ITER_HISTORY}" ]]; then
    LAST_ITER=$(uv run python -c "import json; h=json.load(open('${ITER_HISTORY}')); print(h[-1]['iter'] if h else 0)")
  else
    LAST_ITER=0
  fi
  ITER=$(( LAST_ITER + 1 ))
fi

echo "==> video_iterate.sh: variant=${VARIANT} iter=${ITER}"

# ── Hard cap check ─────────────────────────────────────────────────────────────
if [[ "${ITER}" -gt "${ITER_HARD_CAP}" ]]; then
  echo "HARD CAP: iter ${ITER} > ${ITER_HARD_CAP} — stopping"
  exit 4
fi

# ── Output directories ─────────────────────────────────────────────────────────
ITER_DIR="${OUT_BASE}/iter-${ITER}"
STILLS_DIR="${ITER_DIR}/${VARIANT}-stills"
OPUS_DIR="${ITER_DIR}/${VARIANT}-opus-stills"
OPUS_JSONL="${ITER_DIR}/${VARIANT}-opus-stills.jsonl"
GEMINI_CACHE="${PLANNING}/gemini-cache"
GEMINI_MD="${GEMINI_CACHE}/iter${ITER}-${VARIANT}-critique.md"
SCORE_MD="${PLANNING}/iter-${ITER}-${VARIANT}-score.md"

mkdir -p "${ITER_DIR}" "${OPUS_DIR}" "${GEMINI_CACHE}"

# ── Step 1: Render ─────────────────────────────────────────────────────────────
RENDER_MP4="${ITER_DIR}/${VARIANT}-iter${ITER}.mp4"

if [[ "${NO_RENDER}" -eq 0 ]]; then
  echo "==> [1/7] Render: ${VARIANT} iter-${ITER}"
  COMP_ID="Main-${VARIANT}"
  (
    cd "${REMOTION_DIR}"
    pnpm exec remotion render \
      "${COMP_ID}" \
      "${RENDER_MP4}" \
      --concurrency=4 \
      --codec=h264 \
      2>&1 | tail -30
  )
  if [[ ! -s "${RENDER_MP4}" ]]; then
    echo "ERROR: render produced no output at ${RENDER_MP4}"
    exit 1
  fi
  echo "    Render complete: ${RENDER_MP4} ($(stat -c%s "${RENDER_MP4}") bytes)"
else
  # No-render: find most recent MP4 for this variant
  RENDER_MP4=$(find "${OUT_BASE}" -name "${VARIANT}-iter*.mp4" | sort -V | tail -1)
  if [[ -z "${RENDER_MP4}" ]]; then
    echo "ERROR: --no-render specified but no MP4 found for variant ${VARIANT}"
    exit 1
  fi
  echo "    Using existing render: ${RENDER_MP4}"
fi

# ── Step 2: Sample stills ──────────────────────────────────────────────────────
echo "==> [2/7] Sample stills: ffmpeg 2fps → ${STILLS_DIR}/"
mkdir -p "${STILLS_DIR}"

if [[ "$(ls "${STILLS_DIR}"/f*.jpg 2>/dev/null | wc -l)" -lt 10 ]]; then
  ffmpeg -i "${RENDER_MP4}" \
    -vf "fps=2" \
    -q:v 4 \
    "${STILLS_DIR}/f%04d.jpg" \
    -y \
    2>&1 | tail -5
fi

STILL_COUNT=$(ls "${STILLS_DIR}"/f*.jpg 2>/dev/null | wc -l)
echo "    Extracted ${STILL_COUNT} stills"

if [[ "${STILL_COUNT}" -lt 10 ]]; then
  echo "ERROR: Not enough stills extracted (${STILL_COUNT} < 10)"
  exit 1
fi

# ── Step 3: Opus stills scoring ────────────────────────────────────────────────
echo "==> [3/7] Opus stills scoring (30 batches, async, semaphore=8)"
uv run python "${SCRIPTS}/score_stills_opus.py" \
  --stills-dir "${STILLS_DIR}" \
  --variant "${VARIANT}" \
  --iter "${ITER}" \
  --output-dir "${OPUS_DIR}" \
  --jsonl "${OPUS_JSONL}"

BATCH_COUNT=$(wc -l < "${OPUS_JSONL}" 2>/dev/null || echo 0)
echo "    Scored ${BATCH_COUNT} batches → ${OPUS_JSONL}"

# ── Step 4: Gemini critique ────────────────────────────────────────────────────
if [[ "${NO_GEMINI}" -eq 0 && ! -f "${GEMINI_MD}" ]]; then
  echo "==> [4/7] Gemini critique (Claude Code subagent)"
  GEMINI_RUBRIC="${SCRIPTS}/prompts/gemini-rubric.md"

  if [[ ! -f "${GEMINI_RUBRIC}" ]]; then
    echo "WARNING: ${GEMINI_RUBRIC} not found — skipping Gemini critique"
    NO_GEMINI=1
  else
    RUBRIC_CONTENT="$(cat "${GEMINI_RUBRIC}")"
    AGENT_PROMPT="You are a Gemini critique subagent for SkyHerd video iteration.

Your ONLY job: call mcp__gemini__gemini_analyze with the following parameters, then save the output to: ${GEMINI_MD}

Parameters:
  file_path: \"${RENDER_MP4}\"
  prompt: <contents of ${GEMINI_RUBRIC} — the full rubric>
  system_instruction: \"You are a senior hackathon judge. Variant: ${VARIANT}, Iter: ${ITER}. Output only the required structured format.\"

Expected output format (copy exactly from gemini output into ${GEMINI_MD}):
  ## Impact (30%): X.X/10
  ## Demo (25%): X.X/10
  ## Opus 4.7 axis (25%): X.X/10
  ## Depth (20%): X.X/10
  ## Aggregate: X.XX/10
  ## Critical issues:
  ## Would change:

Write the raw gemini output to ${GEMINI_MD} and confirm the path.
Return only: DONE: <path>"

    # Spawn subagent (per CLAUDE.md: MCP calls always wrap in subagent)
    claude --dangerously-skip-permissions --print -p "${AGENT_PROMPT}" > /tmp/gemini-critique-result-$$.txt 2>&1 || true

    if [[ -f "${GEMINI_MD}" ]]; then
      echo "    Gemini critique saved: ${GEMINI_MD}"
    else
      echo "    WARNING: Gemini critique not generated — using Opus-only scoring"
      NO_GEMINI=1
      # Create stub gemini md with Opus aggregate scores as fallback
      uv run python -c "
import json, pathlib, sys
jsonl = pathlib.Path('${OPUS_JSONL}')
if not jsonl.exists():
    sys.exit(0)
from statistics import median
dims = {'impact': [], 'demo': [], 'opus': [], 'depth': []}
aliases = {'opus 4.7 axis': 'opus', 'impact': 'impact', 'demo': 'demo', 'depth': 'depth'}
for line in jsonl.read_text().splitlines():
    if not line.strip(): continue
    rec = json.loads(line)
    for k,v in rec.get('scores', {}).items():
        canon = aliases.get(k.lower())
        if canon: dims[canon].append(float(v))
meds = {k: median(v) if v else 0.0 for k,v in dims.items()}
agg = meds['impact']*0.30 + meds['demo']*0.25 + meds['opus']*0.25 + meds['depth']*0.20
out = pathlib.Path('${GEMINI_MD}')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(f'''# Gemini critique (Opus-fallback stub)
## Impact (30%): {meds['impact']:.1f}/10
## Demo (25%): {meds['demo']:.1f}/10
## Opus 4.7 axis (25%): {meds['opus']:.1f}/10
## Depth (20%): {meds['depth']:.1f}/10
## Aggregate: {agg:.2f}/10
## Critical issues:
(none — stub)
## Would change:
(none — stub)
''')
print(f'Stub critique written to ${GEMINI_MD}')
"
    fi
  fi
else
  if [[ -f "${GEMINI_MD}" ]]; then
    echo "==> [4/7] Gemini critique: using cached ${GEMINI_MD}"
  else
    echo "==> [4/7] Gemini critique: skipped (--no-gemini)"
    # Same stub generation as above when --no-gemini
    uv run python -c "
import json, pathlib, sys
jsonl = pathlib.Path('${OPUS_JSONL}')
if not jsonl.exists(): sys.exit(0)
from statistics import median
dims = {'impact': [], 'demo': [], 'opus': [], 'depth': []}
aliases = {'opus 4.7 axis': 'opus', 'impact': 'impact', 'demo': 'demo', 'depth': 'depth'}
for line in jsonl.read_text().splitlines():
    if not line.strip(): continue
    rec = json.loads(line)
    for k,v in rec.get('scores', {}).items():
        canon = aliases.get(k.lower())
        if canon: dims[canon].append(float(v))
meds = {k: median(v) if v else 0.0 for k,v in dims.items()}
agg = meds['impact']*0.30 + meds['demo']*0.25 + meds['opus']*0.25 + meds['depth']*0.20
out = pathlib.Path('${GEMINI_MD}')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(f'''## Impact (30%): {meds['impact']:.1f}/10
## Demo (25%): {meds['demo']:.1f}/10
## Opus 4.7 axis (25%): {meds['opus']:.1f}/10
## Depth (20%): {meds['depth']:.1f}/10
## Aggregate: {agg:.2f}/10
## Critical issues:
## Would change:
''')
" 2>/dev/null || true
  fi
fi

# ── Step 5: Aggregate ──────────────────────────────────────────────────────────
echo "==> [5/7] Aggregate scores"
set +e
AGG_OUTPUT=$(uv run python "${SCRIPTS}/aggregate_score.py" \
  --variant "${VARIANT}" \
  --iter "${ITER}" \
  --opus-jsonl "${OPUS_JSONL}" \
  --gemini-md "${GEMINI_MD}" \
  --output "${SCORE_MD}" 2>&1)
AGG_EXIT=$?
set -e

echo "${AGG_OUTPUT}"

# Extract key metrics from output
AGGREGATE=$(echo "${AGG_OUTPUT}" | grep "^AGGREGATE:" | awk '{print $2}')
SHIP_STATUS=$(echo "${AGG_OUTPUT}" | grep "^SHIP_GATE:" | awk '{print $2}')
PLATEAU_STATUS=$(echo "${AGG_OUTPUT}" | grep "^PLATEAU:" | awk '{print $2}')

echo "    Aggregate: ${AGGREGATE:-?}"
echo "    Ship gate: ${SHIP_STATUS:-?}"
echo "    Plateau: ${PLATEAU_STATUS:-?}"

# ── Step 6: Regression check ───────────────────────────────────────────────────
echo "==> [6/7] Regression check"
ROLLBACK_CAP=3
ROLLBACK_COUNT=0

# Check if any dimension dropped >0.3 vs previous iter
if [[ "${ITER}" -gt 1 && -f "${ITER_HISTORY}" ]]; then
  REGRESSION=$(uv run python -c "
import json
from pathlib import Path
history = json.loads(Path('${ITER_HISTORY}').read_text())
if len(history) < 2:
    print('NO_REGRESSION')
else:
    prev = history[-2]
    curr = history[-1]
    dims = ['impact', 'demo', 'opus', 'depth']
    regressions = []
    for d in dims:
        p = prev.get('final_dims', {}).get(d, 0)
        c = curr.get('final_dims', {}).get(d, 0)
        if p - c > 0.3:
            regressions.append(f'{d}: {p:.2f} → {c:.2f} (drop {p-c:.2f})')
    if regressions:
        print('REGRESSION: ' + ', '.join(regressions))
    else:
        print('NO_REGRESSION')
" 2>/dev/null || echo "NO_REGRESSION")

  if [[ "${REGRESSION}" == REGRESSION:* ]]; then
    echo "    REGRESSION DETECTED: ${REGRESSION}"
    if [[ "${ROLLBACK_COUNT}" -lt "${ROLLBACK_CAP}" ]]; then
      echo "    Reverting last commit (rollback ${ROLLBACK_COUNT}/${ROLLBACK_CAP})"
      git -C "${PROJECT_ROOT}" revert HEAD --no-edit 2>/dev/null || \
        git -C "${PROJECT_ROOT}" reset --hard HEAD~1
      ROLLBACK_COUNT=$(( ROLLBACK_COUNT + 1 ))
      echo "    Rolled back. Moving to next-priority fix."
    else
      echo "    Rollback cap reached (${ROLLBACK_CAP}) — accepting regression and continuing"
    fi
  else
    echo "    No regression detected"
  fi
fi

# ── Stop conditions ────────────────────────────────────────────────────────────
if [[ "${AGG_EXIT}" -eq 2 || "${SHIP_STATUS}" == "PASS" ]]; then
  echo "==> SHIP GATE PASSED — aggregate=${AGGREGATE}"
  exit 2
fi

if [[ "${AGG_EXIT}" -eq 3 || "${PLATEAU_STATUS}" == "YES" ]]; then
  echo "==> PLATEAU REACHED — aggregate=${AGGREGATE}"
  exit 3
fi

# ── Step 7: Auto-apply fix ─────────────────────────────────────────────────────
echo "==> [7/7] Auto-apply top fix"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "    --dry-run: printing fix spec without applying"
  uv run python "${SCRIPTS}/auto_apply_fix.py" \
    --score-md "${SCORE_MD}" \
    --variant "${VARIANT}" \
    --iter "${ITER}" \
    --dry-run
  exit 0
fi

# Try fix 1, then 2, then 3 on failure
MAX_FIX_ATTEMPTS=3
FIX_APPLIED=0

for FIX_IDX in $(seq 1 ${MAX_FIX_ATTEMPTS}); do
  echo "    Attempting fix ${FIX_IDX}/${MAX_FIX_ATTEMPTS}..."
  set +e
  FIX_RESULT=$(uv run python "${SCRIPTS}/auto_apply_fix.py" \
    --score-md "${SCORE_MD}" \
    --variant "${VARIANT}" \
    --iter "${ITER}" \
    --fix-index "${FIX_IDX}" 2>&1)
  FIX_EXIT=$?
  set -e

  echo "${FIX_RESULT}"

  if [[ "${FIX_EXIT}" -eq 0 ]]; then
    echo "    Fix ${FIX_IDX} applied successfully"
    FIX_APPLIED=1
    break
  elif [[ "${FIX_EXIT}" -eq 2 ]]; then
    echo "    No more fix suggestions available"
    break
  else
    echo "    Fix ${FIX_IDX} failed — trying next"
  fi
done

if [[ "${FIX_APPLIED}" -eq 0 ]]; then
  echo "WARNING: No fix could be applied this round — iter still incremented"
fi

echo "==> Round complete: variant=${VARIANT} iter=${ITER} aggregate=${AGGREGATE:-?}"
exit 0
