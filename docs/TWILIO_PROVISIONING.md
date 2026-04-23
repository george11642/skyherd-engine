# Twilio Provisioning Runbook — SkyHerd Engine live voice + SMS

**Audience:** repo maintainer (you).
**Time required:** 10 minutes.
**Cost:** ~$1.15 / month for a US local number (paid resource — requires explicit CONFIRM).
**When to run:** before the live video shoot, or any time the demo needs a real phone call.

The code path is fully covered by mocked tests in `tests/voice/test_call.py` and
`tests/mcp/test_rancher_mcp_sms.py`. Nothing in the repo depends on Twilio
being provisioned — the fallback chain routes to `dashboard-ring` (SSE event
`rancher.ringing`) whenever credentials are absent. This runbook *only* wires up
the live SMS + voice delivery.

## Prerequisites

- A Twilio account (free trial OK if just testing; paid for real phone number).
  Sign up: https://www.twilio.com/try-twilio
- A US phone number at Twilio's console (Buy a Number → pick a local US number,
  ~$1.15 / month).
- Optional: a public HTTPS tunnel for Twilio to fetch the rendered WAV from.
  We use `cloudflared` (free).

## Step 1 — Sign in / sign up

1. Open https://console.twilio.com.
2. Sign in, or click "Try Twilio for Free" and complete SMS verification (this
   is why the step cannot be fully automated — Twilio requires a real SMS
   verification code).

## Step 2 — Copy Account SID + Auth Token

1. From the Twilio console dashboard, scroll to the "Account Info" card.
2. Copy **Account SID** (starts with `AC...`).
3. Click "Show" next to **Auth Token** and copy it.

## Step 3 — Buy a US local number (PAID, requires CONFIRM)

> :warning: This step spends money. Do not run it without approval.

1. In the left nav: "Phone Numbers" → "Buy a Number".
2. Country: United States. Capabilities: Voice, SMS.
3. Pick any US number (~$1.15 / month). Click "Buy".
4. Copy the E.164 number (e.g., `+15125551234`).

## Step 4 — Save credentials to `.env.local`

Append these lines to `.env.local` (create the file if it doesn't exist — it is
gitignored):

```bash
TWILIO_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_32_char_auth_token_here
TWILIO_FROM=+15125551234
RANCHER_PHONE=+15055550100   # where Wes calls to — set this to your test phone
```

Note: the canonical name is `TWILIO_AUTH_TOKEN`. `TWILIO_TOKEN` is still
accepted but emits a `DeprecationWarning` on first use.

## Step 5 — Optional: expose WAV files to Twilio via Cloudflare Tunnel

Twilio's voice call uses a TwiML `<Play>` verb that needs a publicly reachable
HTTPS URL for the WAV. Locally:

```bash
# In one terminal: start the dashboard
make dashboard

# In another terminal: expose :8000 via a free ephemeral cloudflared tunnel
cloudflared tunnel --url http://127.0.0.1:8000
# Copy the https://<random>.trycloudflare.com URL from the output
```

Add it to `.env.local`:

```bash
CLOUDFLARE_TUNNEL_URL=https://<random>.trycloudflare.com
```

The dashboard serves `/voice/<wav_name>` automatically. If you skip this step,
calls still work — but Twilio falls back to `dashboard-ring` (no real call
placed).

## Step 6 — Verify

### Synthesis-only smoke (no network):

```bash
uv run skyherd-voice say "Howdy boss, tank three is dry."
# -> Wrote runtime/voice/<uuid>.wav
```

### Twilio mock tests (no credits spent):

```bash
uv run pytest tests/voice/test_call.py::TestTryTwilioCall -v
```

Expected: all pass.

### Live SMS test (spends 1 Twilio SMS credit, ~$0.008):

```bash
# Set SKYHERD_VOICE=live to skip the mock-mode gate
SKYHERD_VOICE=live uv run python -c "
from skyherd.mcp.rancher_mcp import _try_send_sms
ok = _try_send_sms('+15055550100', 'Howdy boss. Tank 3 at 18 percent.')
print('sms delivered:', ok)
"
```

Replace `+15055550100` with your `RANCHER_PHONE`. You should receive the text
within a few seconds.

### Live voice call (spends ~$0.014 / min):

```bash
SKYHERD_VOICE=live DEMO_PHONE_MODE=live uv run python -c "
from skyherd.voice.call import render_urgency_call
from skyherd.voice.wes import WesMessage
msg = WesMessage(urgency='call', subject='coyote at the SW fence')
print(render_urgency_call(msg))
"
```

Your test phone should ring. Wes will play the rendered WAV.

## Step 7 — Demo-day modes

| Env | Behavior |
|-----|----------|
| `SKYHERD_VOICE=mock` | Silent backend; Twilio bypassed. B-roll friendly. |
| `SKYHERD_VOICE=live` (or unset) + no Twilio creds | Real TTS, dashboard ring (SSE). |
| `SKYHERD_VOICE=live` + full Twilio creds + `DEMO_PHONE_MODE=live` | Real Twilio call. |

For the submission video hero shot: start with `SKYHERD_VOICE=live DEMO_PHONE_MODE=live make demo SEED=42 SCENARIO=coyote_fence` — coyote detection triggers a real Wes call to the rancher's phone.

## Troubleshooting

**"20003 Authentication failed"** — your `TWILIO_AUTH_TOKEN` is wrong or was rotated. Regenerate from the Twilio console and update `.env.local`.

**"21210 'From' phone number not purchased"** — `TWILIO_FROM` isn't a number on your Twilio account. Double-check the E.164 formatting.

**Call reaches Twilio but drops instantly** — `CLOUDFLARE_TUNNEL_URL` is stale or wrong. Tunnel URLs are ephemeral; regenerate before each session.

**SMS silently fails** — check `runtime/rancher_pages.jsonl`. If `channel: "log"`, the SMS attempt fell through to log. Check server logs for the WARNING line; look for `21408 Permission to send SMS` (your trial account may have region restrictions).

## Why this isn't fully automated

Twilio signup requires a real SMS verification code sent to a human phone.
Number purchase is a paid resource requiring explicit CONFIRM. Both steps need
user presence and therefore live outside the autonomous phase pipeline.

Everything *else* — environment variable parsing, SMS delivery, voice-call
TwiML generation, WAV synthesis, fallback chain — is code-tested and ships
independent of this runbook.
