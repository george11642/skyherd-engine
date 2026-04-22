# Voice API Credentials

## Status

| Service | Obtained | Notes |
|---------|----------|-------|
| ElevenLabs | YES (last 4: `61f5`) | Free tier, 10k chars/month, no CC |
| Twilio | NO | Requires phone-verified signup — see below |

## ElevenLabs

**Account**: george.teifel@gmail.com  
**Tier**: Free (10,000 chars/month)  
**Voice**: Adam premade (`pNInz6obpgDQGcFmaJgB`) — Dominant, Firm, free-tier compatible

**Key rotation**:
1. Sign in at https://elevenlabs.io/app/developers/api-keys
2. Click "Create Key", name it, disable "Restrict Key" for full access
3. Copy the key immediately (shown once only)
4. Update `ELEVENLABS_API_KEY` in `.env.local`
5. Delete the old key from the same page

**Security**: key lives only in `.env.local` (gitignored). Never committed. `.env.example` contains only `sk_...` placeholder.

## Twilio

Not yet obtained. To enable real phone calls on demo day:

1. Sign up at https://www.twilio.com/try-twilio (free, $15 trial credit)
2. Complete phone-number verification (requires George's cell)
3. Copy Account SID, Auth Token, and trial phone number
4. Paste into `.env.local`:
   ```
   TWILIO_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_TOKEN=your_auth_token
   TWILIO_FROM=+1xxxxxxxxxx
   TWILIO_TO_NUMBER=+1xxxxxxxxxx  # George's cell
   ```
5. Expose the WAV file via a public URL:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   # then set CLOUDFLARE_TUNNEL_URL=https://xxxx.trycloudflare.com
   ```
6. Flip demo mode: set `DEMO_PHONE_MODE=twilio` in `.env.local`

## Demo Day Flip

By default `DEMO_PHONE_MODE=dashboard` — Wes's voice renders via ElevenLabs and the call appears in the /rancher PWA without placing a real phone call. Zero Twilio charges.

To place a real call on demo day:
```bash
# In .env.local:
DEMO_PHONE_MODE=twilio
TWILIO_TO_NUMBER=+1xxxxxxxxxx   # George's cell
CLOUDFLARE_TUNNEL_URL=https://your-tunnel.trycloudflare.com
```

## Security Posture

- `.env.local` is in `.gitignore` — never committed
- `.env.example` contains only placeholder values, no real keys
- Keys never appear in logs (only last-4-chars shown in diagnostics)
- Rotate immediately if any key is accidentally exposed
