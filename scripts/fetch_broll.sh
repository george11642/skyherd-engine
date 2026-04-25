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

# Phase H iter2 — Pexels gap-fill clips.
# Each value is the direct `video_files[].link` URL from the Pexels API response
# (Pexels License, commercial use OK, no attribution required — attribution is
# recorded in SOURCE.md as a courtesy). These are direct-CDN URLs so a plain
# curl is sufficient; no yt-dlp / API key required at reproduce-time.
declare -A PEXELS_SOURCES=(
    ["t1-pexels-coyote-night"]="https://videos.pexels.com/video-files/34660193/14691738_1920_1080_60fps.mp4"
    ["t1-pexels-fence-wire"]="https://videos.pexels.com/video-files/4650102/4650102-hd_1920_1080_30fps.mp4"
    ["t2-pexels-hand-phone"]="https://videos.pexels.com/video-files/6831196/6831196-hd_1920_1080_25fps.mp4"
    ["t2-pexels-water-tank"]="https://videos.pexels.com/video-files/35529631/15052265_1920_1080_60fps.mp4"
    ["t3-pexels-calf"]="https://videos.pexels.com/video-files/35854640/15204675_1080_1920_30fps.mp4"
    ["t3-pexels-vet-mobile"]="https://videos.pexels.com/video-files/6235179/6235179-uhd_1440_2560_25fps.mp4"
    ["t1-pexels-drone-thermal"]="https://videos.pexels.com/video-files/31711788/13511800_1920_1080_30fps.mp4"
    ["t1-pexels-ranch-dawn"]="https://videos.pexels.com/video-files/10585381/10585381-hd_1920_1080_30fps.mp4"
)

mkdir -p "$BROLL_DIR"

normalize_raw() {
    # Normalize a raw download into our canonical 1920x1080 30fps H.264 + AAC
    # stereo format, 8s cap, +faststart. Some sources (notably Pexels) have no
    # audio track, so we overlay silent audio when the source has none.
    local raw="$1"
    local final_path="$2"

    # Try with silent-audio overlay first (works for any source, with or without audio)
    ffmpeg -y -i "$raw" -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 \
        -t 8 \
        -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=30" \
        -map 0:v:0 -map 1:a:0 -shortest \
        -c:v libx264 -pix_fmt yuv420p -preset medium -crf 22 \
        -c:a aac -ac 2 -ar 44100 \
        -movflags +faststart \
        "$final_path" >/dev/null 2>&1 && return 0

    # Fallback: use the source's own audio track if present
    ffmpeg -y -i "$raw" \
        -t 8 \
        -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=30" \
        -c:v libx264 -pix_fmt yuv420p -preset medium -crf 22 \
        -c:a aac -ac 2 -ar 44100 \
        -movflags +faststart \
        "$final_path" >/dev/null 2>&1 && return 0

    return 1
}

fetch_one() {
    local slug="$1"
    local page_url="${SOURCES[$slug]:-}"
    local pexels_url="${PEXELS_SOURCES[$slug]:-}"
    if [[ -z "$page_url" && -z "$pexels_url" ]]; then
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

    local raw="$TMP_DIR/$slug-raw.mp4"

    if [[ -n "$pexels_url" ]]; then
        # Pexels clip — direct CDN URL, just curl.
        echo "FETCH  $slug from $pexels_url"
        curl -sSL -A "Mozilla/5.0" -o "$raw" "$pexels_url"
    else
        # Mixkit clip — yt-dlp's generic extractor scrapes the embedded MP4.
        echo "FETCH  $slug from $page_url"
        if ! command -v yt-dlp >/dev/null 2>&1; then
            echo "ERROR: yt-dlp not installed (try: uvx yt-dlp@latest)" >&2
            return 1
        fi
        yt-dlp --quiet --no-warnings --no-progress \
            -f "best[ext=mp4]/best" \
            -o "$raw" \
            "$page_url"
    fi

    if [[ ! -s "$raw" ]]; then
        echo "ERROR: download failed for $slug" >&2
        return 1
    fi

    if ! normalize_raw "$raw" "$final_path"; then
        echo "ERROR: ffmpeg normalize failed for $slug" >&2
        return 1
    fi

    local size; size=$(du -h "$final_path" | cut -f1)
    echo "DONE   $slug.mp4 ($size)"
}

if [[ -n "$SINGLE_SLUG" ]]; then
    fetch_one "$SINGLE_SLUG"
    exit $?
fi

failures=0
total_count=0
for slug in "${!SOURCES[@]}"; do
    total_count=$((total_count + 1))
    if ! fetch_one "$slug"; then
        failures=$((failures + 1))
    fi
done
for slug in "${!PEXELS_SOURCES[@]}"; do
    total_count=$((total_count + 1))
    if ! fetch_one "$slug"; then
        failures=$((failures + 1))
    fi
done

if [[ "$failures" -gt 0 ]]; then
    echo
    echo "FAILED $failures/$total_count clips"
    exit 1
fi

echo
echo "All $total_count clips present in $BROLL_DIR"
