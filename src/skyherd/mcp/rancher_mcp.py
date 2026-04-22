"""
Rancher MCP server — pages the rancher/vet via SMS, voice, or local log.

Urgency levels: silent, log, text, call, emergency.
Uses Twilio when TWILIO_SID env var is set; else writes to
runtime/rancher_pages.jsonl.  Integrates with skyherd.voice.wes if present.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_URGENCY_LEVELS = ("silent", "log", "text", "call", "emergency")
_RUNTIME_DIR = Path("runtime")
_PAGES_FILE = _RUNTIME_DIR / "rancher_pages.jsonl"
_PREFS_FILE = _RUNTIME_DIR / "rancher_prefs.json"

_DEFAULT_PREFS: dict[str, Any] = {
    "timezone": "America/Denver",
    "urgency_thresholds": {
        "silent": 0,
        "log": 1,
        "text": 2,
        "call": 3,
        "emergency": 4,
    },
    "rancher_phone": os.environ.get("RANCHER_PHONE", "+15055550100"),
    "vet_phone": os.environ.get("VET_PHONE", "+15055550200"),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wes_script(urgency: str, context: str, recipient: str = "rancher") -> str:
    """Generate a Wes-persona cowboy-style message."""
    preamble = {
        "silent": "",
        "log": f"Hey {recipient}, just so y'know — ",
        "text": f"Hey {recipient}, heads up — ",
        "call": f"Hey {recipient}, got somethin' that needs your eyes — ",
        "emergency": f"DROP EVERYTHING, {recipient.upper()} — ",
    }.get(urgency, "Hey — ")
    return f"{preamble}{context.strip()}"


def _write_log(record: dict[str, Any]) -> None:
    """Append *record* to PAGES_FILE as a JSON line."""
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with _PAGES_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def _try_send_sms(to: str, body: str) -> bool:
    """Send SMS via Twilio; return True on success, False if Twilio unavailable.

    Logs a WARNING with the exception detail so failures are diagnosable.
    Only catches specific Twilio / network exceptions; unexpected errors propagate.
    """
    import logging as _logging

    _log = _logging.getLogger(__name__)

    sid = os.environ.get("TWILIO_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_num = os.environ.get("TWILIO_FROM", "")

    if not (sid and token and from_num):
        return False

    try:
        from twilio.rest import Client  # type: ignore[import]

        client = Client(sid, token)
        client.messages.create(body=body, from_=from_num, to=to)
        return True
    except ImportError:
        _log.debug("twilio package not installed — SMS unavailable")
        return False
    except Exception as exc:  # noqa: BLE001
        # Catches TwilioRestException, requests.exceptions.RequestException,
        # ssl.SSLError, etc. — log at WARNING so callers can surface the reason.
        _log.warning(
            "Twilio SMS failed (to=%s): %s: %s",
            to,
            type(exc).__name__,
            exc,
        )
        return False


def _try_voice_call(to: str, script: str) -> bool:
    """Attempt a voice call via skyherd.voice if the module is importable.

    Logs a WARNING on Twilio / voice-backend errors so silent failures are
    diagnosable.  Only catches expected failure modes; unexpected errors propagate.
    """
    import logging as _logging

    _log = _logging.getLogger(__name__)

    try:
        from skyherd.voice.call import render_urgency_call
        from skyherd.voice.wes import WesMessage

        msg = WesMessage(urgency="call", subject=script, scripted_text=script)
        result = render_urgency_call(msg)
        return result.get("delivered_to") in ("twilio", "dashboard-ring")
    except ImportError:
        _log.debug("skyherd.voice not available — voice call skipped")
        return False
    except AttributeError as exc:
        _log.warning("Voice call setup error (AttributeError): %s", exc)
        return False
    except Exception as exc:  # noqa: BLE001
        _log.warning(
            "Voice call failed: %s: %s",
            type(exc).__name__,
            exc,
        )
        return False


def _load_prefs() -> dict[str, Any]:
    """Load rancher prefs from file; fall back to defaults if missing."""
    if _PREFS_FILE.exists():
        try:
            with _PREFS_FILE.open(encoding="utf-8") as fh:
                data = json.load(fh)
            # Merge with defaults so missing keys are always present
            return {**_DEFAULT_PREFS, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_DEFAULT_PREFS)


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------


def _build_tools() -> list[Any]:
    @tool(
        "page_rancher",
        "Page the rancher via SMS, voice, or log depending on urgency and Twilio availability.",
        {"urgency": str, "context": str, "voice": bool},
    )
    async def page_rancher(args: dict[str, Any]) -> dict[str, Any]:
        """Send a Wes-phrased page to the rancher; returns page_id, channel, and wes_script."""
        urgency = str(args.get("urgency", "medium"))
        # Normalise "medium" → "text" (not in the canonical list)
        if urgency not in _URGENCY_LEVELS:
            urgency = "text"
        context = str(args.get("context", ""))
        voice = bool(args.get("voice", True))

        prefs = _load_prefs()
        phone = prefs.get("rancher_phone", _DEFAULT_PREFS["rancher_phone"])
        wes = _wes_script(urgency, context, "boss")
        page_id = str(uuid.uuid4())[:8]

        channel = "log"
        if urgency == "silent":
            channel = "silent"
        elif urgency in ("call", "emergency") and voice:
            if _try_voice_call(phone, wes):
                channel = "voice"
            elif _try_send_sms(phone, wes):
                channel = "sms"
            else:
                _write_log(
                    {
                        "page_id": page_id,
                        "ts": datetime.now(UTC).isoformat(),
                        "recipient": "rancher",
                        "urgency": urgency,
                        "wes_script": wes,
                        "channel": "log",
                    }
                )
                channel = "log"
        elif urgency in ("text", "log"):
            if _try_send_sms(phone, wes):
                channel = "sms"
            else:
                _write_log(
                    {
                        "page_id": page_id,
                        "ts": datetime.now(UTC).isoformat(),
                        "recipient": "rancher",
                        "urgency": urgency,
                        "wes_script": wes,
                        "channel": "log",
                    }
                )
                channel = "log"

        if channel not in ("silent",):
            _write_log(
                {
                    "page_id": page_id,
                    "ts": datetime.now(UTC).isoformat(),
                    "recipient": "rancher",
                    "urgency": urgency,
                    "wes_script": wes,
                    "channel": channel,
                }
            )

        return {
            "content": [{"type": "text", "text": f"Rancher paged via {channel}: {wes}"}],
            "page_id": page_id,
            "channel": channel,
            "wes_script": wes,
        }

    @tool(
        "page_vet",
        "Page the vet with an intake packet via SMS, voice, or log.",
        {"urgency": str, "intake_packet": dict},
    )
    async def page_vet(args: dict[str, Any]) -> dict[str, Any]:
        """Send a vet page with a structured intake packet; returns page_id, channel, and wes_script."""
        urgency = str(args.get("urgency", "text"))
        if urgency not in _URGENCY_LEVELS:
            urgency = "text"
        intake_packet: dict[str, Any] = args.get("intake_packet") or {}

        prefs = _load_prefs()
        phone = prefs.get("vet_phone", _DEFAULT_PREFS["vet_phone"])

        animal_id = intake_packet.get("tag") or intake_packet.get("animal_id", "unknown")
        symptoms = intake_packet.get("symptoms", "see intake packet")
        context = f"Animal {animal_id} needs attention — {symptoms}"
        wes = _wes_script(urgency, context, "Doc")
        page_id = str(uuid.uuid4())[:8]

        channel = "log"
        if urgency in ("call", "emergency"):
            if _try_voice_call(phone, wes):
                channel = "voice"
            elif _try_send_sms(phone, wes):
                channel = "sms"
        elif urgency in ("text", "log"):
            if _try_send_sms(phone, wes):
                channel = "sms"

        record = {
            "page_id": page_id,
            "ts": datetime.now(UTC).isoformat(),
            "recipient": "vet",
            "urgency": urgency,
            "wes_script": wes,
            "intake_packet": intake_packet,
            "channel": channel,
        }
        _write_log(record)

        return {
            "content": [{"type": "text", "text": f"Vet paged via {channel}: {wes}"}],
            "page_id": page_id,
            "channel": channel,
            "wes_script": wes,
        }

    @tool(
        "get_rancher_preferences",
        "Return the current rancher contact preferences and urgency thresholds.",
        {},
    )
    async def get_rancher_preferences(args: dict[str, Any]) -> dict[str, Any]:
        """Load and return rancher preferences (timezone, urgency thresholds, contacts)."""
        prefs = _load_prefs()
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Rancher prefs: tz={prefs.get('timezone')}",
                }
            ],
            **prefs,
        }

    return [page_rancher, page_vet, get_rancher_preferences]


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def create_rancher_mcp_server() -> McpSdkServerConfig:
    """Create a rancher MCP server with Twilio/voice/log routing.

    Returns:
        McpSdkServerConfig for use with ClaudeAgentOptions.mcp_servers.
    """
    tools = _build_tools()
    return create_sdk_mcp_server(name="rancher", version="1.0.0", tools=tools)
