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
        msg = WesMessage(
            urgency="text", subject="tank low", scripted_text="Heads up, boss. Tank's low."
        )
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


class TestTryTwilioCall:
    """Cover _try_twilio_call with a mocked twilio.rest.Client."""

    def _make_twilio_mock(self, monkeypatch, call_sid: str = "CA123"):
        import sys
        import types

        fake_twilio = types.ModuleType("twilio")
        fake_twilio_rest = types.ModuleType("twilio.rest")
        fake_call = type("FakeCall", (), {"sid": call_sid})()
        fake_calls = type("FakeCalls", (), {"create": lambda self, **kw: fake_call})()
        fake_client_inst = type("FakeClient", (), {"calls": fake_calls})()
        fake_twilio_rest.Client = lambda sid, token: fake_client_inst
        fake_twilio.rest = fake_twilio_rest
        monkeypatch.setitem(sys.modules, "twilio", fake_twilio)
        monkeypatch.setitem(sys.modules, "twilio.rest", fake_twilio_rest)
        return fake_client_inst

    def test_returns_sid_on_success(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        self._make_twilio_mock(monkeypatch, call_sid="CA_SUCCESS")
        monkeypatch.setenv("TWILIO_SID", "ACxxx")
        monkeypatch.setenv("TWILIO_TOKEN", "tok")
        monkeypatch.setenv("TWILIO_FROM", "+15550001111")
        monkeypatch.setenv("CLOUDFLARE_TUNNEL_URL", "https://example.trycloudflare.com")

        from skyherd.voice.call import _try_twilio_call
        from skyherd.voice.tts import SilentBackend

        wav_path = SilentBackend().synthesize("Test.")
        result = _try_twilio_call("Heads up.", wav_path, "+15055550100")
        assert result == "CA_SUCCESS"

    def test_returns_none_without_tunnel_url(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TWILIO_SID", "ACxxx")
        monkeypatch.setenv("TWILIO_TOKEN", "tok")
        monkeypatch.setenv("TWILIO_FROM", "+15550001111")
        monkeypatch.delenv("CLOUDFLARE_TUNNEL_URL", raising=False)

        from skyherd.voice.call import _try_twilio_call
        from skyherd.voice.tts import SilentBackend

        wav_path = SilentBackend().synthesize("Test.")
        result = _try_twilio_call("Heads up.", wav_path, "+15055550100")
        assert result is None

    def test_returns_none_when_twilio_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        import sys
        import types

        fake_twilio = types.ModuleType("twilio")
        fake_twilio_rest = types.ModuleType("twilio.rest")

        def _raise(**kw):
            raise RuntimeError("connection refused")

        fake_calls = type("FakeCalls", (), {"create": lambda self, **kw: _raise(**kw)})()
        fake_client_inst = type("FakeClient", (), {"calls": fake_calls})()
        fake_twilio_rest.Client = lambda sid, token: fake_client_inst
        fake_twilio.rest = fake_twilio_rest
        monkeypatch.setitem(sys.modules, "twilio", fake_twilio)
        monkeypatch.setitem(sys.modules, "twilio.rest", fake_twilio_rest)
        monkeypatch.setenv("TWILIO_SID", "ACxxx")
        monkeypatch.setenv("TWILIO_TOKEN", "tok")
        monkeypatch.setenv("TWILIO_FROM", "+15550001111")
        monkeypatch.setenv("CLOUDFLARE_TUNNEL_URL", "https://example.trycloudflare.com")

        from skyherd.voice.call import _try_twilio_call
        from skyherd.voice.tts import SilentBackend

        wav_path = SilentBackend().synthesize("Test.")
        result = _try_twilio_call("Heads up.", wav_path, "+15055550100")
        assert result is None

    def test_render_uses_twilio_when_live_mode(self, tmp_path, monkeypatch):
        """render_urgency_call uses twilio when not in demo mode and keys present."""
        monkeypatch.chdir(tmp_path)
        self._make_twilio_mock(monkeypatch, call_sid="CA_LIVE")
        monkeypatch.setenv("TWILIO_SID", "ACxxx")
        monkeypatch.setenv("TWILIO_TOKEN", "tok")
        monkeypatch.setenv("TWILIO_FROM", "+15550001111")
        monkeypatch.setenv("CLOUDFLARE_TUNNEL_URL", "https://example.trycloudflare.com")
        monkeypatch.setenv("DEMO_PHONE_MODE", "live")

        result = render_urgency_call(_msg("call", "coyote"))
        assert result["delivered_to"] == "twilio"
        assert result["call_id"] == "CA_LIVE"


class TestWesSay:
    """Cover wes_say() in voice/__init__.py."""

    def test_wes_say_calls_synthesize_and_plays(self, tmp_path, monkeypatch):
        from skyherd.voice.tts import SilentBackend

        monkeypatch.chdir(tmp_path)
        wav_path = tmp_path / "test.wav"
        wav_path.write_bytes(b"\x00" * 44)

        fake_backend = SilentBackend()
        monkeypatch.setattr("skyherd.voice.tts.get_backend", lambda: fake_backend)

        played = []

        def _fake_run(cmd, **kwargs):
            played.append(cmd[0])
            result = type("R", (), {"returncode": 0})()
            return result

        monkeypatch.setattr("subprocess.run", _fake_run)

        from skyherd.voice import wes_say

        wes_say("Fence breach detected.")
        # Should have attempted at least one player
        assert len(played) >= 1

    def test_wes_say_silent_when_no_player(self, tmp_path, monkeypatch):
        """wes_say should not raise even when no audio player is available."""
        monkeypatch.chdir(tmp_path)
        from skyherd.voice.tts import SilentBackend

        fake_backend = SilentBackend()
        monkeypatch.setattr("skyherd.voice.tts.get_backend", lambda: fake_backend)


        def _not_found(cmd, **kwargs):
            raise FileNotFoundError("no player")

        monkeypatch.setattr("subprocess.run", _not_found)

        from skyherd.voice import wes_say

        # Should complete without raising
        wes_say("All clear.")
