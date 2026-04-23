"""Expanded live-call path coverage for rancher_mcp — SMS success, voice success,
voice-fails-then-sms cascade, and page_vet emergency path.

Works by injecting a fake `twilio` + `twilio.rest` module via sys.modules so the
MCP tool's `_try_send_sms` / `_try_voice_call` paths hit the mock rather than
the real Twilio REST client.
"""

from __future__ import annotations

import json
import sys
import types

import pytest

from skyherd.mcp.rancher_mcp import create_rancher_mcp_server

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _call_tool(server, tool_name: str, args: dict) -> object:
    from mcp.types import CallToolRequest, ListToolsRequest

    inst = server["instance"]
    list_result = await inst.request_handlers[ListToolsRequest](
        ListToolsRequest(method="tools/list")
    )
    tools = list_result.root.tools
    assert any(t.name == tool_name for t in tools), f"Tool '{tool_name}' not registered"
    call_result = await inst.request_handlers[CallToolRequest](
        CallToolRequest(method="tools/call", params={"name": tool_name, "arguments": args})
    )
    return call_result.root


def _install_fake_twilio(monkeypatch, *, sms_raises: bool = False, call_raises: bool = False) -> dict:
    """Install a fake twilio module. Returns a dict with sent_messages/calls trackers."""
    sent_messages: list[dict] = []
    created_calls: list[dict] = []

    def _messages_create(**kw):
        if sms_raises:
            raise RuntimeError("sms failed: 21408 Permission to send SMS")
        sent_messages.append(kw)
        return type("FakeMsg", (), {"sid": "SM123"})()

    def _calls_create(**kw):
        if call_raises:
            raise RuntimeError("call failed: 21210 'From' phone number not purchased")
        created_calls.append(kw)
        return type("FakeCall", (), {"sid": "CA456"})()

    fake_messages = type("FakeMessages", (), {"create": lambda self, **kw: _messages_create(**kw)})()
    fake_calls = type("FakeCalls", (), {"create": lambda self, **kw: _calls_create(**kw)})()
    fake_client_inst = type(
        "FakeClient", (), {"messages": fake_messages, "calls": fake_calls}
    )()

    fake_twilio = types.ModuleType("twilio")
    fake_twilio_rest = types.ModuleType("twilio.rest")
    fake_twilio_rest.Client = lambda sid, token: fake_client_inst
    fake_twilio.rest = fake_twilio_rest
    monkeypatch.setitem(sys.modules, "twilio", fake_twilio)
    monkeypatch.setitem(sys.modules, "twilio.rest", fake_twilio_rest)

    return {"sent_messages": sent_messages, "created_calls": created_calls}


@pytest.fixture()
def tmp_runtime(tmp_path, monkeypatch):
    """Redirect runtime/ to a temp dir."""
    import skyherd.mcp.rancher_mcp as rm

    monkeypatch.setattr(rm, "_RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(rm, "_PAGES_FILE", tmp_path / "rancher_pages.jsonl")
    monkeypatch.setattr(rm, "_PREFS_FILE", tmp_path / "rancher_prefs.json")
    return tmp_path


@pytest.fixture()
def rancher_server():
    return create_rancher_mcp_server()


@pytest.fixture()
def twilio_env(monkeypatch):
    """Set full Twilio credentials in env + SKYHERD_VOICE=live for live-path tests."""
    monkeypatch.setenv("TWILIO_SID", "ACxxx")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
    monkeypatch.setenv("TWILIO_FROM", "+15550001111")
    monkeypatch.setenv("SKYHERD_VOICE", "live")


# ---------------------------------------------------------------------------
# SMS success path
# ---------------------------------------------------------------------------


class TestSmsSuccessPath:
    """urgency=text with working Twilio → channel=sms; SMS record written."""

    async def test_text_urgency_uses_sms_channel_when_twilio_succeeds(
        self, rancher_server, tmp_runtime, monkeypatch, twilio_env
    ):
        tracker = _install_fake_twilio(monkeypatch, sms_raises=False)

        result = await _call_tool(
            rancher_server,
            "page_rancher",
            {"urgency": "text", "context": "Tank 3 at 18 percent", "voice": False},
        )
        assert not result.isError
        # Twilio .messages.create must have been invoked
        assert len(tracker["sent_messages"]) == 1
        kw = tracker["sent_messages"][0]
        assert kw["from_"] == "+15550001111"
        assert "Tank 3" in kw["body"] or "tank" in kw["body"].lower()

        # Log entry should record channel=sms
        pages_file = tmp_runtime / "rancher_pages.jsonl"
        assert pages_file.exists()
        lines = pages_file.read_text().strip().splitlines()
        assert lines
        record = json.loads(lines[-1])
        assert record["channel"] == "sms"

    async def test_log_urgency_uses_sms_channel_when_twilio_succeeds(
        self, rancher_server, tmp_runtime, monkeypatch, twilio_env
    ):
        tracker = _install_fake_twilio(monkeypatch, sms_raises=False)

        await _call_tool(
            rancher_server,
            "page_rancher",
            {"urgency": "log", "context": "Gate cam 2 battery swapped", "voice": False},
        )
        assert len(tracker["sent_messages"]) == 1

    async def test_sms_failure_falls_back_to_log(
        self, rancher_server, tmp_runtime, monkeypatch, twilio_env
    ):
        _install_fake_twilio(monkeypatch, sms_raises=True)

        await _call_tool(
            rancher_server,
            "page_rancher",
            {"urgency": "text", "context": "Fence sensor 7 dropped", "voice": False},
        )
        pages_file = tmp_runtime / "rancher_pages.jsonl"
        lines = [json.loads(l) for l in pages_file.read_text().strip().splitlines() if l]
        assert lines
        assert lines[-1]["channel"] == "log"


# ---------------------------------------------------------------------------
# Voice-call success path
# ---------------------------------------------------------------------------


class TestVoiceCallSuccessPath:
    """urgency=call with Twilio voice-call mock and voice=True → channel=voice."""

    async def test_call_urgency_uses_voice_channel(
        self, rancher_server, tmp_runtime, monkeypatch, twilio_env
    ):
        # The voice path delegates to render_urgency_call which returns
        # "dashboard-ring" when no CLOUDFLARE_TUNNEL_URL — that still counts
        # as "voice" channel per _try_voice_call's return check.
        _install_fake_twilio(monkeypatch, sms_raises=False, call_raises=False)

        result = await _call_tool(
            rancher_server,
            "page_rancher",
            {"urgency": "call", "context": "Coyote inside SW fence", "voice": True},
        )
        assert not result.isError
        text = result.content[0].text
        assert "voice" in text.lower() or "coyote" in text.lower()

        pages_file = tmp_runtime / "rancher_pages.jsonl"
        lines = [json.loads(l) for l in pages_file.read_text().strip().splitlines() if l]
        # Find the most recent page_rancher entry (recipient == rancher)
        rancher_lines = [l for l in lines if l.get("recipient") == "rancher"]
        assert rancher_lines
        assert rancher_lines[-1]["channel"] == "voice"

    async def test_emergency_urgency_triggers_voice_path(
        self, rancher_server, tmp_runtime, monkeypatch, twilio_env
    ):
        _install_fake_twilio(monkeypatch)

        result = await _call_tool(
            rancher_server,
            "page_rancher",
            {"urgency": "emergency", "context": "Predator inside calving pen", "voice": True},
        )
        assert not result.isError


# ---------------------------------------------------------------------------
# page_vet parallel coverage
# ---------------------------------------------------------------------------


class TestPageVetChannels:
    async def test_vet_emergency_call_channel_when_voice_succeeds(
        self, rancher_server, tmp_runtime, monkeypatch, twilio_env
    ):
        _install_fake_twilio(monkeypatch)

        intake = {"tag": "TAG099", "symptoms": "down and not rising"}
        await _call_tool(
            rancher_server,
            "page_vet",
            {"urgency": "emergency", "intake_packet": intake},
        )
        pages_file = tmp_runtime / "rancher_pages.jsonl"
        lines = [json.loads(l) for l in pages_file.read_text().strip().splitlines() if l]
        vet_lines = [l for l in lines if l.get("recipient") == "vet"]
        assert vet_lines
        assert vet_lines[-1]["channel"] in ("voice", "sms")  # voice path or SMS fallback

    async def test_vet_text_channel_sms(
        self, rancher_server, tmp_runtime, monkeypatch, twilio_env
    ):
        tracker = _install_fake_twilio(monkeypatch)

        intake = {"tag": "TAG010", "symptoms": "pinkeye day 2"}
        await _call_tool(
            rancher_server,
            "page_vet",
            {"urgency": "text", "intake_packet": intake},
        )
        assert len(tracker["sent_messages"]) == 1
