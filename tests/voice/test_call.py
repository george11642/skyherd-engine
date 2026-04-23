"""Tests for render_urgency_call — delivery routing and JSONL output."""

from __future__ import annotations

import json
import logging
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
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
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
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "fake_token")
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
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
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
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
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
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
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
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
        monkeypatch.setenv("TWILIO_FROM", "+15550001111")
        monkeypatch.setenv("CLOUDFLARE_TUNNEL_URL", "https://example.trycloudflare.com")
        monkeypatch.setenv("DEMO_PHONE_MODE", "live")
        monkeypatch.setenv("SKYHERD_VOICE", "live")

        result = render_urgency_call(_msg("call", "coyote"))
        assert result["delivered_to"] == "twilio"
        assert result["call_id"] == "CA_LIVE"


class TestSkyherdVoiceSkipsTwilio:
    """SKYHERD_VOICE=mock short-circuits Twilio even with full creds set."""

    def _make_crashing_twilio_mock(self, monkeypatch):
        """Inject a twilio.rest.Client that raises if .calls.create is invoked."""
        import sys
        import types

        called = {"count": 0}

        def _crash(**kw):
            called["count"] += 1
            raise AssertionError("Twilio must not be called in mock mode")

        fake_twilio = types.ModuleType("twilio")
        fake_twilio_rest = types.ModuleType("twilio.rest")
        fake_calls = type("FakeCalls", (), {"create": lambda self, **kw: _crash(**kw)})()
        fake_client_inst = type("FakeClient", (), {"calls": fake_calls})()
        fake_twilio_rest.Client = lambda sid, token: fake_client_inst
        fake_twilio.rest = fake_twilio_rest
        monkeypatch.setitem(sys.modules, "twilio", fake_twilio)
        monkeypatch.setitem(sys.modules, "twilio.rest", fake_twilio_rest)
        return called

    def test_skyherd_voice_mock_skips_twilio_even_with_creds(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TWILIO_SID", "ACxxx")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
        monkeypatch.setenv("TWILIO_FROM", "+15550001111")
        monkeypatch.setenv("CLOUDFLARE_TUNNEL_URL", "https://example.trycloudflare.com")
        monkeypatch.setenv("DEMO_PHONE_MODE", "live")
        monkeypatch.setenv("SKYHERD_VOICE", "mock")

        call_tracker = self._make_crashing_twilio_mock(monkeypatch)

        result = render_urgency_call(_msg("call", "coyote at fence"))
        assert result["delivered_to"] == "dashboard-ring"
        assert call_tracker["count"] == 0

    def test_skyherd_voice_silent_skips_twilio(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TWILIO_SID", "ACxxx")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
        monkeypatch.setenv("TWILIO_FROM", "+15550001111")
        monkeypatch.setenv("CLOUDFLARE_TUNNEL_URL", "https://example.trycloudflare.com")
        monkeypatch.setenv("DEMO_PHONE_MODE", "live")
        monkeypatch.setenv("SKYHERD_VOICE", "silent")

        call_tracker = self._make_crashing_twilio_mock(monkeypatch)

        result = render_urgency_call(_msg("emergency", "predator inside herd"))
        assert result["delivered_to"] == "dashboard-ring"
        assert call_tracker["count"] == 0

    def test_skyherd_voice_live_still_attempts_twilio(self, tmp_path, monkeypatch):
        """With SKYHERD_VOICE=live, Twilio path still fires when creds present."""
        import sys
        import types

        monkeypatch.chdir(tmp_path)
        fake_call = type("FakeCall", (), {"sid": "CA_REAL_LIVE"})()
        fake_calls = type("FakeCalls", (), {"create": lambda self, **kw: fake_call})()
        fake_client_inst = type("FakeClient", (), {"calls": fake_calls})()
        fake_twilio = types.ModuleType("twilio")
        fake_twilio_rest = types.ModuleType("twilio.rest")
        fake_twilio_rest.Client = lambda sid, token: fake_client_inst
        fake_twilio.rest = fake_twilio_rest
        monkeypatch.setitem(sys.modules, "twilio", fake_twilio)
        monkeypatch.setitem(sys.modules, "twilio.rest", fake_twilio_rest)

        monkeypatch.setenv("TWILIO_SID", "ACxxx")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
        monkeypatch.setenv("TWILIO_FROM", "+15550001111")
        monkeypatch.setenv("CLOUDFLARE_TUNNEL_URL", "https://example.trycloudflare.com")
        monkeypatch.setenv("DEMO_PHONE_MODE", "live")
        monkeypatch.setenv("SKYHERD_VOICE", "live")

        result = render_urgency_call(_msg("call", "coyote at fence"))
        assert result["delivered_to"] == "twilio"
        assert result["call_id"] == "CA_REAL_LIVE"


class TestSynthesizeFailureFallback:
    """When the chosen backend raises in synthesize(), fall back to SilentBackend."""

    def test_synthesize_failure_falls_back_to_silent(self, tmp_path, monkeypatch):
        from skyherd.voice import tts as tts_module

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TWILIO_SID", raising=False)
        monkeypatch.setenv("SKYHERD_VOICE", "live")

        class ExplodingBackend(tts_module.TTSBackend):
            def synthesize(self, text, voice="wes"):  # noqa: ARG002
                raise RuntimeError("boom: elevenlabs 429")

        monkeypatch.setattr(tts_module, "_BACKEND_LOGGED", False)
        monkeypatch.setattr("skyherd.voice.call.get_backend", lambda: ExplodingBackend())

        result = render_urgency_call(_msg("call", "coyote"))
        assert result["delivered_to"] == "dashboard-ring"
        # wav should exist (from SilentBackend fallback)
        wav = Path(result["wav_path"])
        assert wav.exists()

    def test_synthesize_failure_logs_warning(self, tmp_path, monkeypatch, caplog):
        from skyherd.voice import tts as tts_module

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TWILIO_SID", raising=False)

        class ExplodingBackend(tts_module.TTSBackend):
            def synthesize(self, text, voice="wes"):  # noqa: ARG002
                raise RuntimeError("boom: piper process died")

        monkeypatch.setattr("skyherd.voice.call.get_backend", lambda: ExplodingBackend())

        with caplog.at_level(logging.WARNING, logger="skyherd.voice.call"):
            render_urgency_call(_msg("call", "water tank"))

        warnings = [r for r in caplog.records if "falling back to SilentBackend" in r.message]
        assert len(warnings) >= 1


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


class TestTwilioAuthTokenMigration:
    """Verify that call.py reads TWILIO_AUTH_TOKEN (not legacy TWILIO_TOKEN)."""

    def test_twilio_available_prefers_auth_token(self, tmp_path, monkeypatch):
        """_twilio_available() returns True when TWILIO_AUTH_TOKEN is set; no warning."""
        import warnings

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TWILIO_SID", "ACxxx")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "auth_token_value")
        monkeypatch.setenv("TWILIO_FROM", "+15550001111")
        monkeypatch.delenv("TWILIO_TOKEN", raising=False)

        from skyherd.voice.call import _twilio_available

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = _twilio_available()

        assert result is True
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert dep_warnings == [], "No DeprecationWarning expected when TWILIO_AUTH_TOKEN set"

    def test_twilio_available_accepts_legacy_with_warning(self, tmp_path, monkeypatch):
        """_twilio_available() returns True for legacy TWILIO_TOKEN AND emits DeprecationWarning."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TWILIO_SID", "ACxxx")
        monkeypatch.setenv("TWILIO_TOKEN", "legacy_token_value")
        monkeypatch.setenv("TWILIO_FROM", "+15550001111")
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)

        import pytest as _pytest

        from skyherd.voice.call import _twilio_available
        with _pytest.warns(DeprecationWarning):
            result = _twilio_available()

        assert result is True

    def test_sse_write_oserror_logs_debug(self, tmp_path, monkeypatch, caplog):
        """OSError on SSE events.jsonl write is logged at DEBUG, not silently swallowed."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TWILIO_SID", raising=False)

        # Patch Path.open to raise OSError only for the sse_events file
        original_open = Path.open

        def _patched_open(self, *args, **kwargs):
            if "sse_events" in str(self):
                raise OSError("disk full")
            return original_open(self, *args, **kwargs)

        monkeypatch.setattr(Path, "open", _patched_open)

        with caplog.at_level(logging.DEBUG, logger="skyherd.voice.call"):
            render_urgency_call(_msg("call", "coyote at fence"))

        assert "sse events.jsonl write failed" in caplog.text
