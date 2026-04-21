"""Tests for render_urgency_call — delivery routing and JSONL output."""

from __future__ import annotations

import json
from pathlib import Path

from skyherd.voice.call import render_urgency_call
from skyherd.voice.wes import WesMessage


def _msg(urgency: str, subject: str = "test event") -> WesMessage:
    return WesMessage(urgency=urgency, subject=subject)


class TestRenderUrgencyCall:
    def test_silent_returns_log_only(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = render_urgency_call(_msg("silent"))
        assert result["delivered_to"] == "log-only"
        assert result["wav_path"] is None

    def test_log_writes_jsonl(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = render_urgency_call(_msg("log", "battery swap"))
        assert result["delivered_to"] == "log-only"
        rings_file = tmp_path / "runtime" / "phone_rings.jsonl"
        assert rings_file.exists()
        record = json.loads(rings_file.read_text().strip().splitlines()[-1])
        assert record["urgency"] == "log"

    def test_no_twilio_env_gives_dashboard_ring(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TWILIO_SID", raising=False)
        monkeypatch.delenv("TWILIO_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_FROM", raising=False)
        result = render_urgency_call(_msg("call", "coyote at the fence"))
        assert result["delivered_to"] == "dashboard-ring"

    def test_dashboard_ring_writes_jsonl(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TWILIO_SID", raising=False)
        result = render_urgency_call(_msg("call", "water tank dry"))
        rings_file = tmp_path / "runtime" / "phone_rings.jsonl"
        assert rings_file.exists()
        lines = rings_file.read_text().strip().splitlines()
        assert len(lines) >= 1
        record = json.loads(lines[-1])
        assert record["delivered_to"] == "dashboard-ring"
        assert "wav_path" in record
        assert record["wav_path"] is not None

    def test_dashboard_ring_wav_exists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TWILIO_SID", raising=False)
        result = render_urgency_call(_msg("emergency", "predator inside herd"))
        wav = Path(result["wav_path"])
        assert wav.exists()
        assert wav.suffix == ".wav"

    def test_result_has_required_keys(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TWILIO_SID", raising=False)
        result = render_urgency_call(_msg("call", "coyote"))
        for key in ("wav_path", "script", "urgency", "delivered_to", "call_id"):
            assert key in result, f"Missing key {key!r} in result"

    def test_script_in_result_matches_message(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TWILIO_SID", raising=False)
        msg = WesMessage(urgency="text", subject="tank low", scripted_text="Heads up, boss. Tank's low.")
        result = render_urgency_call(msg)
        assert result["script"] == "Heads up, boss. Tank's low."

    def test_sse_event_written(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TWILIO_SID", raising=False)
        render_urgency_call(_msg("call", "coyote"))
        sse_file = tmp_path / "runtime" / "sse_events.jsonl"
        assert sse_file.exists()
        record = json.loads(sse_file.read_text().strip().splitlines()[-1])
        assert record["event"] == "rancher.ringing"

    def test_demo_mode_overrides_twilio(self, tmp_path, monkeypatch):
        """DEMO_PHONE_MODE=dashboard should prevent Twilio call even when keys set."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TWILIO_SID", "ACxxx")
        monkeypatch.setenv("TWILIO_TOKEN", "fake_token")
        monkeypatch.setenv("TWILIO_FROM", "+15551234567")
        monkeypatch.setenv("DEMO_PHONE_MODE", "dashboard")
        result = render_urgency_call(_msg("call", "coyote"))
        assert result["delivered_to"] == "dashboard-ring"
