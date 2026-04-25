#!/usr/bin/env bash
# upload_youtube.sh — Phase 8 autonomous YouTube upload
#
# Uploads skyherd-demo-C-final.mp4 as an unlisted YouTube video using the
# YouTube Data API v3 (OAuth 2.0, access token + refresh flow).
#
# Prerequisites in .env.local:
#   YOUTUBE_CLIENT_ID=<your OAuth client ID>
#   YOUTUBE_CLIENT_SECRET=<your OAuth client secret>
#   YOUTUBE_REFRESH_TOKEN=<your OAuth refresh token>
#   (optional) YOUTUBE_OAUTH_TOKEN=<short-lived access token — auto-refreshed>
#
# If creds are absent, this script writes .planning/research/youtube-upload-pending.md
# with setup instructions and exits 0 (non-blocking).
#
# Usage:
#   bash scripts/upload_youtube.sh
#   bash scripts/upload_youtube.sh --dry-run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env.local"

DRY_RUN="${1:-}"

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

VIDEO_PATH="$PROJECT_ROOT/docs/demo-assets/video/skyherd-demo-C-final.mp4"
THUMB_PATH="$PROJECT_ROOT/docs/demo-assets/video/skyherd-thumb-C.png"
PENDING_DOC="$PROJECT_ROOT/.planning/research/youtube-upload-pending.md"

VIDEO_TITLE="SkyHerd Engine — Built with Claude Opus 4.7 (variant C)"

VIDEO_DESCRIPTION='SkyHerd is a 5-layer nervous system for American ranches. A cow can be sick for 72 hours before anyone notices; a coyote can take three calves in a night. SkyHerd makes the ranch watch itself.

Five Claude Managed Agents — FenceLineDispatcher, HerdHealthWatcher, PredatorPatternLearner, GrazingOptimizer, CalvingWatch — share one platform session each and pause their own billing between events. A 33-file skills library keeps prompts short and cache hits high. Tool calls emit an Ed25519 Merkle attestation chain that a verifier can audit offline. One ranch costs roughly $4/week to monitor — not $4K — because of idle-pause.

The demo runs deterministically: `make demo SEED=42 SCENARIO=all` boots on a fresh clone in under three minutes. Five field scenarios: coyote at the fence, a sick cow flagged, water tank pressure drop, calving, incoming storm. A "Wes" cowboy-persona voice calls the rancher on escalation.

Built for the Anthropic "Built with Claude Opus 4.7" hackathon.

Repo: https://github.com/george11642/skyherd-engine

---

BGM: Hans Zimmer "Time" (Inception, 2010, Reprise Records / WaterTower Music). Used per project content-license policy (locked decision #8). AudioCraft MusicGen prompt available for a clean swap post-launch — MusicGen Path A was blocked at build time (torch version conflict). See remotion-video/public/BGM-SOURCE.md in the repo.'

# ---- Load env ----
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

YOUTUBE_CLIENT_ID="${YOUTUBE_CLIENT_ID:-}"
YOUTUBE_CLIENT_SECRET="${YOUTUBE_CLIENT_SECRET:-}"
YOUTUBE_REFRESH_TOKEN="${YOUTUBE_REFRESH_TOKEN:-}"
YOUTUBE_OAUTH_TOKEN="${YOUTUBE_OAUTH_TOKEN:-}"

# ---- Check creds ----
if [[ -z "$YOUTUBE_CLIENT_ID" || -z "$YOUTUBE_CLIENT_SECRET" || -z "$YOUTUBE_REFRESH_TOKEN" ]]; then
  echo -e "${YELLOW}${BOLD}YouTube creds not found in .env.local${RESET}"
  echo "Writing setup instructions to: $PENDING_DOC"
  mkdir -p "$(dirname "$PENDING_DOC")"
  cat > "$PENDING_DOC" << 'PENDINGEOF'
# YouTube Upload — Pending OAuth Setup

Generated: 2026-04-25 (Phase 8)

YouTube creds were not present in `.env.local` when `scripts/upload_youtube.sh` ran.
Once George adds them (one-time setup below), re-run the script and it will upload
automatically with no further gates.

---

## One-time OAuth setup (≈5 minutes)

1. Go to https://console.cloud.google.com/apis/credentials
2. Select (or create) a project.
3. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
4. Application type: **Desktop app**. Name it "SkyHerd Upload".
5. Download the JSON. Extract `client_id` and `client_secret`.
6. Enable the **YouTube Data API v3** at:
   https://console.cloud.google.com/apis/library/youtube.googleapis.com
7. Get a refresh token (one-time authorization):

```bash
# Step 1: Open this URL in your browser, authorize, copy the `code` from redirect URL:
SCOPE="https://www.googleapis.com/auth/youtube.upload"
CLIENT_ID="YOUR_CLIENT_ID"
echo "https://accounts.google.com/o/oauth2/auth?client_id=${CLIENT_ID}&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=${SCOPE}"

# Step 2: Exchange code for refresh token:
curl -s -X POST https://oauth2.googleapis.com/token \
  -d "code=AUTH_CODE_FROM_STEP1" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=urn:ietf:wg:oauth:2.0:oob" \
  -d "grant_type=authorization_code" | python3 -m json.tool
# → copy refresh_token from the response
```

8. Add to `.env.local`:
```
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret
YOUTUBE_REFRESH_TOKEN=your_refresh_token
```

9. Re-run: `bash scripts/upload_youtube.sh`

---

## Upload details (ready to go once creds added)

| Field | Value |
|-------|-------|
| Title | SkyHerd Engine — Built with Claude Opus 4.7 (variant C) |
| Privacy | **unlisted** |
| Video file | `docs/demo-assets/video/skyherd-demo-C-final.mp4` (119 MB) |
| Thumbnail | `docs/demo-assets/video/skyherd-thumb-C.png` (cost-ticker reveal at 0:57) |
| Duration | 185s |
| Description | 100–200 word summary from docs/SUBMISSION.md + repo URL + BGM footnote |

---

## MusicGen clean-swap note

If YouTube Content ID flags the BGM (Hans Zimmer "Time"), run:

```bash
# Clean swap — replace BGM with MusicGen output once torch conflict resolves:
# See remotion-video/public/BGM-SOURCE.md → MusicGen Path A for the exact prompt.
bash scripts/source_bgm.sh --provider musicgen
make video-final variant=C
bash scripts/upload_youtube.sh  # re-upload with clean audio
```

The AudioCraft prompt that matched "Time"'s emotional arc is preserved in BGM-SOURCE.md.
PENDINGEOF
  echo -e "${YELLOW}Pending doc written. Upload is non-blocking — all other Phase 8 tasks continue.${RESET}"
  exit 0
fi

# ---- Verify video file ----
if [[ ! -f "$VIDEO_PATH" ]]; then
  echo -e "${RED}ERROR: Video file not found: $VIDEO_PATH${RESET}" >&2
  exit 1
fi

VIDEO_SIZE=$(stat -c%s "$VIDEO_PATH" 2>/dev/null || stat -f%z "$VIDEO_PATH")
echo -e "${BOLD}SkyHerd upload_youtube.sh${RESET}"
echo "  Video: $VIDEO_PATH ($(( VIDEO_SIZE / 1024 / 1024 )) MB)"
echo "  Title: $VIDEO_TITLE"
echo "  Privacy: unlisted"

if [[ "$DRY_RUN" == "--dry-run" ]]; then
  echo -e "${YELLOW}[DRY RUN] Would upload — creds found, dry-run mode active${RESET}"
  exit 0
fi

# ---- Refresh access token ----
echo ""
echo "Refreshing access token..."
REFRESH_RESPONSE=$(curl -s -X POST https://oauth2.googleapis.com/token \
  -d "client_id=${YOUTUBE_CLIENT_ID}" \
  -d "client_secret=${YOUTUBE_CLIENT_SECRET}" \
  -d "refresh_token=${YOUTUBE_REFRESH_TOKEN}" \
  -d "grant_type=refresh_token")

ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('access_token',''))")
if [[ -z "$ACCESS_TOKEN" ]]; then
  echo -e "${RED}ERROR: Failed to refresh access token${RESET}" >&2
  echo "Response: $REFRESH_RESPONSE" >&2
  exit 1
fi
echo "  Access token: OK"

# ---- Upload video (resumable upload) ----
echo ""
echo "Starting resumable upload..."

# Step 1: Initialize resumable upload session
METADATA=$(python3 -c "
import json
print(json.dumps({
    'snippet': {
        'title': '''$VIDEO_TITLE''',
        'description': $(python3 -c "import json; print(json.dumps('''$VIDEO_DESCRIPTION'''))"),
        'tags': ['ranching', 'AI', 'Claude', 'Opus 4.7', 'Anthropic', 'hackathon', 'agriculture', 'drones'],
        'categoryId': '28'
    },
    'status': {
        'privacyStatus': 'unlisted',
        'selfDeclaredMadeForKids': False
    }
}))
")

UPLOAD_SESSION_RESPONSE=$(curl -s -D - -X POST \
  "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json; charset=UTF-8" \
  -H "X-Upload-Content-Type: video/mp4" \
  -H "X-Upload-Content-Length: $VIDEO_SIZE" \
  -d "$METADATA")

UPLOAD_URL=$(echo "$UPLOAD_SESSION_RESPONSE" | grep -i "^location:" | tr -d '\r' | awk '{print $2}')
if [[ -z "$UPLOAD_URL" ]]; then
  echo -e "${RED}ERROR: Could not get resumable upload URL${RESET}" >&2
  echo "Response: $UPLOAD_SESSION_RESPONSE" >&2
  exit 1
fi
echo "  Upload session: OK"

# Step 2: Upload the file
echo "  Uploading ${VIDEO_PATH}..."
UPLOAD_RESPONSE=$(curl -s -X PUT "$UPLOAD_URL" \
  -H "Content-Type: video/mp4" \
  -H "Content-Length: $VIDEO_SIZE" \
  --data-binary "@$VIDEO_PATH")

VIDEO_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")
if [[ -z "$VIDEO_ID" ]]; then
  echo -e "${RED}ERROR: Upload failed or no video ID returned${RESET}" >&2
  echo "Response: $UPLOAD_RESPONSE" >&2
  exit 1
fi

YOUTUBE_URL="https://www.youtube.com/watch?v=${VIDEO_ID}"
echo ""
echo -e "${GREEN}${BOLD}UPLOAD COMPLETE${RESET}"
echo -e "  YouTube URL: ${BOLD}${YOUTUBE_URL}${RESET}"
echo ""

# ---- Upload thumbnail ----
if [[ -f "$THUMB_PATH" ]]; then
  echo "Uploading thumbnail..."
  THUMB_RESPONSE=$(curl -s -X POST \
    "https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId=${VIDEO_ID}&uploadType=media" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: image/png" \
    --data-binary "@$THUMB_PATH")
  THUMB_STATUS=$(echo "$THUMB_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('kind','error'))" 2>/dev/null || echo "error")
  if [[ "$THUMB_STATUS" == *"thumbnail"* ]]; then
    echo -e "  Thumbnail: ${GREEN}OK${RESET}"
  else
    echo -e "  Thumbnail: ${YELLOW}WARN — may need manual upload${RESET}"
  fi
fi

# ---- Write URL to file for downstream use ----
YOUTUBE_URL_FILE="$PROJECT_ROOT/.planning/research/youtube-url.txt"
echo "$YOUTUBE_URL" > "$YOUTUBE_URL_FILE"
echo "  URL saved to: $YOUTUBE_URL_FILE"
echo ""
echo "Done. Paste this URL into docs/SUBMISSION.md → YouTube video field."
