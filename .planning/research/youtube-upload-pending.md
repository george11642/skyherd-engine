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
