"""
render_urgency_call — full pipeline: WesMessage → wav → deliver.

Delivery priority:
  1. Twilio voice call (if TWILIO_SID + TWILIO_AUTH_TOKEN + TWILIO_FROM are set
     AND DEMO_PHONE_MODE != "dashboard").
  2. Dashboard ring — writes to runtime/phone_rings.jsonl; SSE event
     "rancher.ringing" is picked up by the /rancher PWA.
  3. log-only — urgency "silent" or "log".
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from skyherd.voice._twilio_env import _get_twilio_auth_token
from skyherd.voice.tts import get_backend
from skyherd.voice.wes import WesMessage, wes_script

logger = logging.getLogger(__name__)

_RUNTIME_DIR = Path("runtime")
_PHONE_RINGS_FILE = _RUNTIME_DIR / "phone_rings.jsonl"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _write_ring(record: dict) -> None:
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with _PHONE_RINGS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def _twilio_available() -> bool:
    return bool(
        os.environ.get("TWILIO_SID")
        and _get_twilio_auth_token()
        and os.environ.get("TWILIO_FROM")
    )


def _demo_mode() -> bool:
    return os.environ.get("DEMO_PHONE_MODE", "dashboard") == "dashboard"


def _try_twilio_call(script: str, wav_path: Path, to: str) -> str | None:
    """
    Attempt a Twilio voice call using TwiML <Play> pointing at the .wav.

    The .wav must be publicly reachable.  In production, serve from a
    Cloudflare tunnel or equivalent.  Returns call SID on success, None
    on failure.
    """
    try:
        from twilio.rest import Client  # type: ignore[import]
    except ImportError:
        logger.debug("twilio not installed; skipping voice call")
        return None

    sid = os.environ.get("TWILIO_SID", "")
    token = _get_twilio_auth_token()
    from_num = os.environ.get("TWILIO_FROM", "")
    tunnel_base = os.environ.get("CLOUDFLARE_TUNNEL_URL", "").rstrip("/")

    if not (sid and token and from_num):
        return None

    if not tunnel_base:
        # Cannot expose wav without a public URL — fallback to dashboard
        logger.debug("CLOUDFLARE_TUNNEL_URL not set; skipping Twilio call")
        return None

    wav_url = f"{tunnel_base}/voice/{wav_path.name}"
    twiml = f"<Response><Play>{wav_url}</Play></Response>"

    try:
        client = Client(sid, token)
        call = client.calls.create(
            to=to,
            from_=from_num,
            twiml=twiml,
        )
        return call.sid  # type: ignore[no-any-return]
    except Exception as exc:  # noqa: BLE001
        # Catches TwilioRestException, requests.exceptions.RequestException,
        # ssl.SSLError, asyncio.TimeoutError, and similar network/auth errors.
        logger.warning(
            "Twilio voice call failed (to=%s): %s: %s",
            to,
            type(exc).__name__,
            exc,
        )
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_urgency_call(message: WesMessage) -> dict:
    """
    Full pipeline: compose Wes script → synthesize wav → deliver.

    Returns a dict with keys:
        wav_path      — absolute path to the rendered .wav
        script        — the Wes-phrased text that was synthesized
        urgency       — message urgency level
        delivered_to  — "twilio" | "dashboard-ring" | "log-only"
        call_id       — uuid or Twilio call SID
    """
    call_id = str(uuid.uuid4())[:8]

    # Ensure script is set
    if not message.scripted_text:
        message = message.model_copy(update={"scripted_text": wes_script(message)})
    script: str = message.scripted_text or ""

    # log / silent — no wav needed
    if message.urgency in ("silent", "log"):
        record = {
            "call_id": call_id,
            "ts": datetime.now(UTC).isoformat(),
            "urgency": message.urgency,
            "subject": message.subject,
            "script": script,
            "delivered_to": "log-only",
            "wav_path": None,
        }
        if message.urgency == "log":
            _write_ring(record)
        return {**record, "wav_path": None}

    # Synthesize wav
    backend = get_backend()
    wav_path: Path = backend.synthesize(script)

    rancher_phone = os.environ.get("RANCHER_PHONE", "+15055550100")
    delivered_to = "dashboard-ring"
    twilio_sid: str | None = None

    # Attempt real Twilio call if configured and not in demo mode
    if _twilio_available() and not _demo_mode() and message.urgency in ("call", "emergency"):
        twilio_sid = _try_twilio_call(script, wav_path, to=rancher_phone)
        if twilio_sid:
            delivered_to = "twilio"
            call_id = twilio_sid

    # Dashboard ring (default or fallback)
    ring_record = {
        "call_id": call_id,
        "ts": datetime.now(UTC).isoformat(),
        "urgency": message.urgency,
        "subject": message.subject,
        "script": script,
        "wav_path": str(wav_path.resolve()),
        "wav_name": wav_path.name,
        "delivered_to": delivered_to,
    }
    _write_ring(ring_record)

    # Emit SSE event name for the PWA  (written to a side channel if SSE server running)
    _maybe_emit_sse(ring_record)

    return {
        "wav_path": wav_path,
        "script": script,
        "urgency": message.urgency,
        "delivered_to": delivered_to,
        "call_id": call_id,
    }


def _maybe_emit_sse(record: dict) -> None:
    """
    Best-effort: emit a rancher.ringing SSE event by writing to the
    runtime/sse_events.jsonl queue that the /events endpoint tails.
    """
    events_file = _RUNTIME_DIR / "sse_events.jsonl"
    try:
        _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        with events_file.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "event": "rancher.ringing",
                        "data": record,
                        "ts": datetime.now(UTC).isoformat(),
                    }
                )
                + "\n"
            )
    except OSError as exc:
        logger.debug("sse events.jsonl write failed (non-fatal): %s", exc)
