"""Tests for get_backend() — env-priority chain."""

from __future__ import annotations

from skyherd.voice import tts as tts_module
from skyherd.voice.tts import (
    ElevenLabsBackend,
    EspeakBackend,
    PiperBackend,
    SilentBackend,
    get_backend,
)


def _reset_logged(monkeypatch):
    """Reset the module-level _BACKEND_LOGGED flag so get_backend logs again."""
    monkeypatch.setattr(tts_module, "_BACKEND_LOGGED", False)


class TestGetBackend:
    def test_elevenlabs_when_key_set(self, monkeypatch):
        _reset_logged(monkeypatch)
        monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-key-xyz")
        backend = get_backend()
        assert isinstance(backend, ElevenLabsBackend)

    def test_piper_when_no_eleven_but_piper_present(self, monkeypatch):
        _reset_logged(monkeypatch)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        # Fake `piper` on PATH
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/piper" if cmd == "piper" else None)
        from skyherd.voice import tts
        backend = tts._resolve_backend()
        assert isinstance(backend, PiperBackend)

    def test_espeak_when_no_eleven_no_piper(self, monkeypatch):
        _reset_logged(monkeypatch)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

        def _which(cmd):
            if cmd == "espeak":
                return "/usr/bin/espeak"
            return None

        monkeypatch.setattr("shutil.which", _which)
        from skyherd.voice import tts
        backend = tts._resolve_backend()
        assert isinstance(backend, EspeakBackend)

    def test_silent_when_nothing_available(self, monkeypatch):
        _reset_logged(monkeypatch)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        from skyherd.voice import tts
        backend = tts._resolve_backend()
        assert isinstance(backend, SilentBackend)

    def test_silent_is_default_in_ci(self, monkeypatch):
        """With no external deps, get_backend() falls back to SilentBackend."""
        _reset_logged(monkeypatch)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        backend = get_backend()
        assert isinstance(backend, SilentBackend)

    def test_logged_once(self, monkeypatch, caplog):
        """get_backend() logs backend name exactly once per process."""
        import logging
        _reset_logged(monkeypatch)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        with caplog.at_level(logging.INFO, logger="skyherd.voice.tts"):
            get_backend()
            get_backend()
        info_msgs = [r for r in caplog.records if "TTS backend selected" in r.message]
        assert len(info_msgs) == 1
