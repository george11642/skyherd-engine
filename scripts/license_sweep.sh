#!/usr/bin/env bash
# license_sweep.sh — Phase 8 pre-release license check
#
# Walks remotion-video/public/{clips,music,sfx,voiceover,captions}/
# Asserts each asset has an entry in its dir's SOURCE.md.
# BGM and stings are EXCLUDED from strict licensing per locked decision #8
# (they live in remotion-video/public/BGM-SOURCE.md which is disclosure-only).
#
# Exit 1 only on orphans in our-asset directories: clips/, voiceover/, captions/
# music/ and sfx/ are informational-only (BGM exclusion).
#
# Usage:
#   bash scripts/license_sweep.sh
#   bash scripts/license_sweep.sh --strict   # also check music/ and sfx/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PUBLIC_DIR="$PROJECT_ROOT/remotion-video/public"

STRICT="${1:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

orphan_count=0
checked_count=0
dirs_checked=()

check_dir() {
  local dir_name="$1"   # e.g. "clips"
  local strict_mode="$2"  # "strict" or "info"
  local dir_path="$PUBLIC_DIR/$dir_name"

  if [[ ! -d "$dir_path" ]]; then
    echo -e "  ${YELLOW}SKIP${RESET}  $dir_name/ — directory does not exist"
    return 0
  fi

  local source_md="$dir_path/SOURCE.md"
  if [[ ! -f "$source_md" ]]; then
    echo -e "  ${YELLOW}WARN${RESET}  $dir_name/SOURCE.md missing — run with --generate to create it"
    if [[ "$strict_mode" == "strict" ]]; then
      (( orphan_count++ )) || true
    fi
    return 0
  fi

  local dir_orphans=0
  while IFS= read -r asset; do
    local basename
    basename="$(basename "$asset")"
    # skip hidden files, EDIT_LOG, and SOURCE.md itself
    [[ "$basename" == .* ]] && continue
    [[ "$basename" == "SOURCE.md" ]] && continue
    [[ "$basename" == "EDIT_LOG.md" ]] && continue

    # Check if filename appears anywhere in SOURCE.md
    if ! grep -qF "$basename" "$source_md" 2>/dev/null; then
      echo -e "  ${RED}ORPHAN${RESET}  $dir_name/$basename — not found in $dir_name/SOURCE.md"
      (( dir_orphans++ )) || true
      if [[ "$strict_mode" == "strict" ]]; then
        (( orphan_count++ )) || true
      fi
    else
      (( checked_count++ )) || true
    fi
  done < <(find "$dir_path" -maxdepth 1 -type f | sort)

  if [[ "$dir_orphans" -eq 0 ]]; then
    local asset_count
    asset_count=$(find "$dir_path" -maxdepth 1 -type f ! -name 'SOURCE.md' ! -name 'EDIT_LOG.md' ! -name '.*' | wc -l)
    echo -e "  ${GREEN}OK${RESET}    $dir_name/ — $asset_count assets, all covered"
  fi

  dirs_checked+=("$dir_name")
}

echo ""
echo -e "${BOLD}SkyHerd license_sweep.sh${RESET}"
echo "Checking: $PUBLIC_DIR"
echo ""

# --- OUR-ASSET DIRECTORIES (strict: orphan = exit 1) ---
echo -e "${BOLD}Our-asset directories (strict)${RESET}"
check_dir "clips"      "strict"
check_dir "voiceover"  "strict"
check_dir "captions"   "strict"

echo ""

# --- BGM/SFX DIRECTORIES (info only per locked decision #8) ---
echo -e "${BOLD}BGM/SFX directories (info only — locked decision #8)${RESET}"
if [[ "$STRICT" == "--strict" ]]; then
  echo "  [--strict mode: promoting music/ and sfx/ to strict]"
  check_dir "music" "strict"
  check_dir "sfx"   "strict"
else
  check_dir "music" "info"
  check_dir "sfx"   "info"
  echo "  (BGM and stings excluded from strict licensing per locked decision #8)"
  echo "  (See remotion-video/public/BGM-SOURCE.md for disclosure)"
fi

echo ""

# --- SUMMARY ---
if [[ "$orphan_count" -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}LICENSE SWEEP PASSED${RESET} — $checked_count assets verified, 0 strict orphans"
  exit 0
else
  echo -e "${RED}${BOLD}LICENSE SWEEP FAILED${RESET} — $orphan_count strict orphan(s) found"
  echo "Add entries for the above assets to their respective SOURCE.md files."
  exit 1
fi
