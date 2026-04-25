#!/usr/bin/env bash
# Fetch + normalize the B-roll inventory from public free-stock sources.
#
# Reads SOURCE.md to drive what gets fetched. Each clip is downloaded from its
# Mixkit (or Pexels/Pixabay/Coverr) page, then normalized to 1920x1080 30fps
# H.264 yuv420p AAC stereo with +faststart, 8-second cap.
#
# B-roll MP4s are .gitignore'd (binary). This script reproduces the inventory
# from a fresh clone for the Remotion composition's render.
#
# Usage:
#   bash scripts/fetch_broll.sh                # fetch all clips
#   bash scripts/fetch_broll.sh --check        # only verify which clips already exist
#   bash scripts/fetch_broll.sh <slug>         # fetch a single clip by slug
#
# Requires: curl, ffmpeg, and a JS-capable HTML scrape on Mixkit pages
# (yt-dlp generic extractor handles this).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROLL_DIR="$REPO_ROOT/remotion-video/public/broll"
TMP_DIR="$(mktemp -d -t skyherd-broll-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

CHECK_ONLY=0
SINGLE_SLUG=""
case "${1:-}" in
    --check) CHECK_ONLY=1 ;;
    -h|--help)
        sed -n '2,18p' "$0" | sed 's/^# \?//'
        exit 0
        ;;
    "") ;;
    *) SINGLE_SLUG="$1" ;;
esac

# slug→source-page-URL mapping (mirrors SOURCE.md table)
declare -A SOURCES=(
    ["t1-dawn-corral-golden"]="https://mixkit.co/free-stock-video/sunset-in-the-ranch-2481/"
    ["t1-cattle-grazing-wide"]="https://mixkit.co/free-stock-video/cows-grazing-slowly-on-a-grassy-paddock-44923/"
    ["t1-cattle-herd-countryside"]="https://mixkit.co/free-stock-video/herd-of-cows-in-the-countryside-31433/"
    ["t1-drone-rangeland-aerial"]="https://mixkit.co/free-stock-video/flying-over-a-landscape-of-sun-soaked-desert-land-with-52012/"
    ["t1-drone-arid-mountains"]="https://mixkit.co/free-stock-video/low-flyover-in-an-arid-ecosystem-with-mountains-50199/"
    ["t1-storm-cell-horizon"]="https://mixkit.co/free-stock-video/dark-stormy-clouds-in-the-sky-9704/"
    ["t1-lightning-night"]="https://mixkit.co/free-stock-video/lightning-in-the-night-sky-25081/"
    ["t2-rancher-horse-walk"]="https://mixkit.co/free-stock-video/a-rancher-walks-his-horse-1155/"
    ["t2-cowboy-sunset"]="https://mixkit.co/free-stock-video/cowboy-at-sunset-525/"
    ["t2-rancher-sunset-couple"]="https://mixkit.co/free-stock-video/romantic-scene-of-a-couple-at-sunset-on-a-ranch-42383/"
    ["t2-hardware-circuit-board"]="https://mixkit.co/free-stock-video/high-tech-circuit-board-with-processor-47051/"
    ["t2-hardware-microcircuit"]="https://mixkit.co/free-stock-video/technical-engineer-working-with-a-microcircuit-47047/"
    ["t2-sunrise-clouds"]="https://mixkit.co/free-stock-video/sunrise-shining-through-thick-clouds-26532/"
    ["t3-night-sky-stars"]="https://mixkit.co/free-stock-video/milky-way-seen-at-night-4148/"
    ["t3-meadow-landscape"]="https://mixkit.co/free-stock-video/meadow-landscape-15981/"
    ["t3-cattle-windy-paddock"]="https://mixkit.co/free-stock-video/cows-grazing-in-a-paddock-on-a-windy-day-44958/"
)

mkdir -p "$BROLL_DIR"

fetch_one() {
    local slug="$1"
    local page_url="${SOURCES[$slug]:-}"
    if [[ -z "$page_url" ]]; then
        echo "ERROR: unknown slug: $slug" >&2
        return 1
    fi
    local final_path="$BROLL_DIR/$slug.mp4"
    if [[ -f "$final_path" ]]; then
        echo "OK     $slug.mp4 (already present)"
        return 0
    fi
    if [[ "$CHECK_ONLY" -eq 1 ]]; then
        echo "MISS   $slug.mp4"
        return 0
    fi

    echo "FETCH  $slug from $page_url"
    local raw="$TMP_DIR/$slug-raw.mp4"
    # Mixkit pages embed an MP4 download URL; yt-dlp's generic extractor finds it.
    if ! command -v yt-dlp >/dev/null 2>&1; then
        echo "ERROR: yt-dlp not installed (try: uvx yt-dlp@latest)" >&2
        return 1
    fi
    yt-dlp --quiet --no-warnings --no-progress \
        -f "best[ext=mp4]/best" \
        -o "$raw" \
        "$page_url"
    if [[ ! -f "$raw" ]]; then
        echo "ERROR: download failed for $slug" >&2
        return 1
    fi

    # Normalize: 1920x1080, 30fps, H.264 yuv420p, AAC stereo, 8s cap, +faststart
    ffmpeg -y -i "$raw" \
        -t 8 \
        -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=30" \
        -c:v libx264 -pix_fmt yuv420p -preset medium -crf 22 \
        -c:a aac -ac 2 -ar 44100 \
        -movflags +faststart \
        "$final_path" >/dev/null 2>&1 || {
            echo "ERROR: ffmpeg normalize failed for $slug" >&2
            return 1
        }

    local size; size=$(du -h "$final_path" | cut -f1)
    echo "DONE   $slug.mp4 ($size)"
}

if [[ -n "$SINGLE_SLUG" ]]; then
    fetch_one "$SINGLE_SLUG"
    exit $?
fi

failures=0
for slug in "${!SOURCES[@]}"; do
    if ! fetch_one "$slug"; then
        failures=$((failures + 1))
    fi
done

if [[ "$failures" -gt 0 ]]; then
    echo
    echo "FAILED $failures/$(echo "${!SOURCES[@]}" | wc -w) clips"
    exit 1
fi

echo
echo "All ${#SOURCES[@]} clips present in $BROLL_DIR"
