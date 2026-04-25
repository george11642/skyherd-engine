#!/usr/bin/env bash
# score_competitor.sh <name>
#
# Score a competitor (or SkyHerd variant) video against the canonical rubric.
# Outputs a critique markdown to .planning/research/competitor-cache/${NAME}-critique.md
#
# Usage:
#   scripts/score_competitor.sh crossbeam
#   scripts/score_competitor.sh elisa
#   scripts/score_competitor.sh postvisit
#   scripts/score_competitor.sh skyherd-A-iter2    # works for SkyHerd variants too
#
# Dependencies:
#   - ffmpeg (still extraction)
#   - mcp__gemini__gemini_analyze (full-MP4 Gemini critique) — called via Claude Code MCP
#   - aggregate_score.py (Phase 4 scorer) — integrates when available (see schema note below)
#
# Output schema (for aggregate_score.py integration):
#   The critique markdown uses a fixed structure:
#     ## Impact (30%): X.X/10
#     ## Demo (25%): X.X/10
#     ## Opus 4.7 axis (25%): X.X/10
#     ## Depth (20%): X.X/10
#     ## Aggregate: X.XX/10
#   aggregate_score.py should parse these headings with:
#     re.findall(r'## (Impact|Demo|Opus 4\.7 axis|Depth) \(\d+%\): ([\d.]+)/10', content)
#     re.findall(r'## Aggregate: ([\d.]+)/10', content)
#   See aggregate_score.py --mode competitor --schema for the expected JSON envelope.
#
# Schema note: When aggregate_score.py lands (Phase 4), replace the stub call at the bottom
# of this script with:
#   python3 scripts/aggregate_score.py --mode competitor --input "${CRITIQUE_FILE}" \
#     --variant "${NAME}" --output ".planning/research/competitor-scores.md"

set -euo pipefail

NAME="${1:?Usage: $0 <competitor-name>}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MP4="${PROJECT_ROOT}/.refs/competitors/${NAME}.mp4"
STILLS_DIR="${PROJECT_ROOT}/out/competitor-${NAME}-stills"
CRITIQUE_FILE="${PROJECT_ROOT}/.planning/research/competitor-cache/${NAME}-critique.md"
RUBRIC="${PROJECT_ROOT}/scripts/prompts/gemini-rubric.md"

echo "==> score_competitor.sh: scoring '${NAME}'"
echo "    MP4:      ${MP4}"
echo "    Stills:   ${STILLS_DIR}"
echo "    Critique: ${CRITIQUE_FILE}"

# ── 1. Verify MP4 exists ───────────────────────────────────────────────────────
if [[ ! -f "${MP4}" ]]; then
  echo "ERROR: MP4 not found at ${MP4}"
  echo "  Download with:"
  echo "    yt-dlp --format 'bestvideo[height<=1080]+bestaudio' --merge-output-format mp4 \\"
  echo "      -o '.refs/competitors/%(id)s.mp4' <youtube-url>"
  echo "    mv '.refs/competitors/<id>.mp4' '.refs/competitors/${NAME}.mp4'"
  echo ""
  echo "  Fallback: derive scores from textual analysis in"
  echo "    .planning/research/winner-top3-analysis.md"
  echo "  and write ${CRITIQUE_FILE} manually using the rubric at ${RUBRIC}"
  exit 1
fi

# ── 2. Extract stills at 2fps ──────────────────────────────────────────────────
mkdir -p "${STILLS_DIR}"
echo "==> Extracting stills (2fps) → ${STILLS_DIR}/"
ffmpeg -i "${MP4}" \
  -vf "fps=2" \
  "${STILLS_DIR}/f%04d.jpg" \
  -q:v 4 \
  -y \
  2>&1 | tail -5

STILL_COUNT=$(ls "${STILLS_DIR}"/f*.jpg 2>/dev/null | wc -l)
echo "    Extracted ${STILL_COUNT} stills"

# ── 3. Full-MP4 Gemini critique ────────────────────────────────────────────────
# This step calls mcp__gemini__gemini_analyze via Claude Code's MCP runtime.
# When running inside a Claude Code session, use the MCP tool directly.
# Outside Claude Code (CI), this step is skipped and stills-only mode is used.
#
# MCP call signature:
#   mcp__gemini__gemini_analyze(
#     file_path = "${MP4}",
#     prompt    = <contents of gemini-rubric.md>,
#     system_instruction = "You are a senior hackathon judge. Output only the required structured format."
#   )
#
# The output is written directly to ${CRITIQUE_FILE}.
#
# In CI / non-MCP environments, produce a placeholder:
if [[ -z "${CLAUDE_CODE_MCP:-}" ]]; then
  echo "==> MCP not available in this shell context."
  echo "    Run this script from within a Claude Code session, or invoke:"
  echo "      mcp__gemini__gemini_analyze(file_path='${MP4}', prompt=<gemini-rubric.md contents>)"
  echo "    Then save the output to: ${CRITIQUE_FILE}"
else
  # MCP is available — this branch executes when score_competitor.sh is called
  # by a Claude Code agent. The agent should replace this comment with the actual
  # MCP tool call and write the result to ${CRITIQUE_FILE}.
  echo "==> (MCP branch) Call mcp__gemini__gemini_analyze and write to ${CRITIQUE_FILE}"
fi

# ── 4. aggregate_score.py integration stub ────────────────────────────────────
# TODO(phase4): Replace stub with real call once aggregate_score.py lands:
#
#   python3 "${PROJECT_ROOT}/scripts/aggregate_score.py" \
#     --mode competitor \
#     --input "${CRITIQUE_FILE}" \
#     --variant "${NAME}" \
#     --output "${PROJECT_ROOT}/.planning/research/competitor-scores.md"
#
# Expected JSON envelope from aggregate_score.py:
#   {
#     "variant": "<name>",
#     "mode": "competitor",
#     "scores": {
#       "impact": <float>,
#       "demo":   <float>,
#       "opus":   <float>,
#       "depth":  <float>,
#       "aggregate": <float>
#     },
#     "critique_path": "<path>",
#     "timestamp": "<iso8601>"
#   }
#
# Parse pattern for the markdown output above:
#   import re
#   scores = dict(re.findall(
#     r'## (Impact|Demo|Opus 4\.7 axis|Depth) \(\d+%\): ([\d.]+)/10',
#     critique_content
#   ))
#   aggregate = re.findall(r'## Aggregate: ([\d.]+)/10', critique_content)[0]

echo "==> Done. Critique at: ${CRITIQUE_FILE}"
