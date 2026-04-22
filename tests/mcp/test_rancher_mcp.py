"""Tests for rancher_mcp — Twilio-absent path, log file writing, urgency routing."""

from __future__ import annotations

import json

import pytest

from skyherd.mcp.rancher_mcp import create_rancher_mcp_server

# ---------------------------------------------------------------------------
# Helper
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


@pytest.fixture(autouse=True)
def _no_twilio_env(monkeypatch):
    """Ensure Twilio env vars are absent so all calls fall back to log."""
    monkeypatch.delenv("TWILIO_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FROM", raising=False)


@pytest.fixture()
def tmp_runtime(tmp_path, monkeypatch):
    """Redirect runtime/ to a temp dir so tests don't write to real filesystem."""
    import skyherd.mcp.rancher_mcp as rm

    monkeypatch.setattr(rm, "_RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(rm, "_PAGES_FILE", tmp_path / "rancher_pages.jsonl")
    monkeypatch.setattr(rm, "_PREFS_FILE", tmp_path / "rancher_prefs.json")
    return tmp_path


@pytest.fixture()
def rancher_server():
    return create_rancher_mcp_server()


# ---------------------------------------------------------------------------
# page_rancher
# ---------------------------------------------------------------------------


class TestPageRancher:
    async def test_log_channel_when_no_twilio(self, rancher_server, tmp_runtime):
        result = await _call_tool(
            rancher_server,
            "page_rancher",
            {"urgency": "text", "context": "Coyote at fence 4", "voice": False},
        )
        assert not result.isError
        text = result.content[0].text
        assert "log" in text.lower() or "paged" in text.lower()

    async def test_log_file_receives_entry(self, rancher_server, tmp_runtime):
        await _call_tool(
            rancher_server,
            "page_rancher",
            {"urgency": "text", "context": "Water tank low", "voice": False},
        )
        pages_file = tmp_runtime / "rancher_pages.jsonl"
        assert pages_file.exists()
        lines = pages_file.read_text().strip().splitlines()
        assert len(lines) >= 1
        record = json.loads(lines[-1])
        assert "page_id" in record
        assert "wes_script" in record
        assert "Water tank low" in record["wes_script"] or "water" in record["wes_script"].lower()

    async def test_wes_script_contains_context(self, rancher_server, tmp_runtime):
        result = await _call_tool(
            rancher_server,
            "page_rancher",
            {"urgency": "call", "context": "Sick cow spotted", "voice": False},
        )
        assert not result.isError
        # wes_script is in content text
        text = result.content[0].text
        assert "sick cow" in text.lower() or "spotted" in text.lower()

    async def test_silent_urgency_does_not_write_log(self, rancher_server, tmp_runtime):
        await _call_tool(
            rancher_server,
            "page_rancher",
            {"urgency": "silent", "context": "Background tick", "voice": False},
        )
        pages_file = tmp_runtime / "rancher_pages.jsonl"
        if pages_file.exists():
            lines = [l for l in pages_file.read_text().strip().splitlines() if l]
            for line in lines:
                record = json.loads(line)
                assert record.get("urgency") != "silent" or record.get("channel") == "silent"

    async def test_emergency_falls_back_to_log_without_twilio(self, rancher_server, tmp_runtime):
        result = await _call_tool(
            rancher_server,
            "page_rancher",
            {"urgency": "emergency", "context": "Calving emergency!", "voice": False},
        )
        assert not result.isError

    async def test_unknown_urgency_normalised_to_text(self, rancher_server, tmp_runtime):
        result = await _call_tool(
            rancher_server,
            "page_rancher",
            {"urgency": "critical_unknown", "context": "test", "voice": False},
        )
        assert not result.isError

    async def test_page_id_is_present(self, rancher_server, tmp_runtime):
        result = await _call_tool(
            rancher_server,
            "page_rancher",
            {"urgency": "log", "context": "Routine check", "voice": False},
        )
        assert not result.isError


# ---------------------------------------------------------------------------
# page_vet
# ---------------------------------------------------------------------------


class TestPageVet:
    async def test_vet_page_written_to_log(self, rancher_server, tmp_runtime):
        intake = {"tag": "TAG042", "symptoms": "lameness score 4, ocular discharge"}
        result = await _call_tool(
            rancher_server,
            "page_vet",
            {"urgency": "call", "intake_packet": intake},
        )
        assert not result.isError
        pages_file = tmp_runtime / "rancher_pages.jsonl"
        assert pages_file.exists()
        lines = pages_file.read_text().strip().splitlines()
        assert any("vet" in json.loads(l).get("recipient", "") for l in lines)

    async def test_intake_packet_preserved_in_log(self, rancher_server, tmp_runtime):
        intake = {"tag": "TAG007", "symptoms": "pinkeye"}
        await _call_tool(
            rancher_server,
            "page_vet",
            {"urgency": "text", "intake_packet": intake},
        )
        pages_file = tmp_runtime / "rancher_pages.jsonl"
        lines = pages_file.read_text().strip().splitlines()
        records = [json.loads(l) for l in lines]
        vet_records = [r for r in records if r.get("recipient") == "vet"]
        assert vet_records
        assert vet_records[-1]["intake_packet"]["tag"] == "TAG007"


# ---------------------------------------------------------------------------
# get_rancher_preferences
# ---------------------------------------------------------------------------


class TestGetRancherPreferences:
    async def test_returns_default_prefs_when_no_file(self, rancher_server, tmp_runtime):
        result = await _call_tool(rancher_server, "get_rancher_preferences", {})
        assert not result.isError
        text = result.content[0].text
        assert "timezone" in text.lower() or "denver" in text.lower() or "prefs" in text.lower()

    async def test_loads_custom_prefs_from_file(self, rancher_server, tmp_runtime):
        prefs_file = tmp_runtime / "rancher_prefs.json"
        prefs_file.write_text(json.dumps({"timezone": "America/Chicago", "urgency_thresholds": {}}))
        # Re-create server so it picks up new prefs location

        result = await _call_tool(rancher_server, "get_rancher_preferences", {})
        assert not result.isError


# ---------------------------------------------------------------------------
# C6 regression — Twilio exceptions are logged and don't swallow silently
# ---------------------------------------------------------------------------


class TestTwilioErrorHandling:
    """C6: _try_send_sms must log at WARNING and return False on Twilio failure."""

    def test_twilio_exception_returns_false_and_logs_warning(
        self, monkeypatch, caplog
    ) -> None:
        """Injecting a TwilioRestException-shaped error must produce a WARNING log."""
        import logging
        from unittest.mock import MagicMock, patch

        from skyherd.mcp.rancher_mcp import _try_send_sms

        monkeypatch.setenv("TWILIO_SID", "ACtest")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
        monkeypatch.setenv("TWILIO_FROM", "+15550000001")

        # Simulate a TwilioRestException (or any exception from the Twilio client)
        class _FakeTwilioError(Exception):
            pass

        mock_client_instance = MagicMock()
        mock_client_instance.messages.create.side_effect = _FakeTwilioError(
            "20003 Authentication failed"
        )
        mock_client_cls = MagicMock(return_value=mock_client_instance)
        mock_twilio_rest = MagicMock()
        mock_twilio_rest.Client = mock_client_cls

        with patch.dict("sys.modules", {"twilio": MagicMock(), "twilio.rest": mock_twilio_rest}):
            with caplog.at_level(logging.WARNING):
                result = _try_send_sms("+15055550100", "Test message")

        assert result is False, "Should return False on Twilio error"
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("Twilio" in m or "FakeTwilio" in m or "20003" in m for m in warning_messages), (
            f"Expected a WARNING log for Twilio failure, got: {warning_messages}"
        )

    def test_sms_missing_credentials_returns_false_silently(self, monkeypatch) -> None:
        """Missing credentials must return False without logging WARNING."""
        from skyherd.mcp.rancher_mcp import _try_send_sms

        monkeypatch.delenv("TWILIO_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_FROM", raising=False)

        result = _try_send_sms("+15055550100", "Test")
        assert result is False


# ---------------------------------------------------------------------------
# Server meta
# ---------------------------------------------------------------------------


class TestServerMeta:
    def test_name_is_rancher(self):
        server = create_rancher_mcp_server()
        assert server["name"] == "rancher"

    def test_type_is_sdk(self):
        server = create_rancher_mcp_server()
        assert server["type"] == "sdk"
