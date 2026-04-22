#!/usr/bin/env bash
# bootstrap.sh — Generate SkyHerdCompanion.xcodeproj via XcodeGen.
# Run once after cloning, and again whenever project.yml changes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 1. Require macOS ────────────────────────────────────────────────────────
if [[ "$(uname)" != "Darwin" ]]; then
  echo "ERROR: bootstrap.sh must be run on macOS." >&2
  exit 1
fi

# ── 2. Install XcodeGen if missing ──────────────────────────────────────────
if ! command -v xcodegen &>/dev/null; then
  echo "▸ XcodeGen not found — installing via Homebrew..."
  if ! command -v brew &>/dev/null; then
    echo "ERROR: Homebrew not installed. Install it first: https://brew.sh" >&2
    exit 1
  fi
  brew install xcodegen
else
  echo "▸ XcodeGen $(xcodegen version 2>/dev/null || echo '') found"
fi

# ── 3. Install ios-deploy if missing (optional, for CLI device installs) ────
if ! command -v ios-deploy &>/dev/null; then
  echo "▸ ios-deploy not found — installing via Homebrew (optional)..."
  brew install ios-deploy || echo "  (ios-deploy install failed — continuing; use Xcode to deploy)"
fi

# ── 4. Create Frameworks placeholder dir ────────────────────────────────────
if [[ ! -d Frameworks ]]; then
  mkdir -p Frameworks
  cat > Frameworks/PLACE_DJISDK_XCFRAMEWORK_HERE.txt <<'TXT'
Download DJISDK.xcframework from https://developer.dji.com/mobile-sdk/
and place the extracted DJISDK.xcframework directory here.

Then, in project.yml, uncomment the two lines under dependencies:
    # - framework: Frameworks/DJISDK.xcframework
    #   embed: true

Re-run ./bootstrap.sh to regenerate the Xcode project.
TXT
  echo "▸ Created Frameworks/ — place DJISDK.xcframework here (see instructions)"
fi

# ── 5. Generate Xcode project ───────────────────────────────────────────────
echo "▸ Generating SkyHerdCompanion.xcodeproj..."
xcodegen generate --spec project.yml

echo ""
echo "Done. Next steps:"
echo "  1. Download DJISDK.xcframework from https://developer.dji.com/mobile-sdk/"
echo "     and place it in ios/SkyHerdCompanion/Frameworks/"
echo "  2. In project.yml, uncomment the DJISDK.xcframework dependency lines."
echo "  3. Run ./bootstrap.sh again to regenerate the project with the SDK."
echo "  4. Open SkyHerdCompanion.xcodeproj in Xcode."
echo "  5. Set your DJI_API_KEY in SupportingFiles/Info.plist."
echo "  6. Select your device and press ⌘R."
