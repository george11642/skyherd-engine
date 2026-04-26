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
        monkeypatch.setenv("SKYHERD_VOICE", "live")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-key-xyz")
        backend = get_backend()
        assert isinstance(backend, ElevenLabsBackend)

    def test_piper_when_no_eleven_but_piper_present(self, monkeypatch):
        _reset_logged(monkeypatch)
        monkeypatch.setenv("SKYHERD_VOICE", "live")
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        # Fake `piper` on PATH
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/usr/bin/piper" if cmd == "piper" else None
        )
        from skyherd.voice import tts

        backend = tts._resolve_backend()
        assert isinstance(backend, PiperBackend)

    def test_espeak_when_no_eleven_no_piper(self, monkeypatch):
        _reset_logged(monkeypatch)
        monkeypatch.setenv("SKYHERD_VOICE", "live")
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
        monkeypatch.setenv("SKYHERD_VOICE", "live")
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        from skyherd.voice import tts

        backend = tts._resolve_backend()
        assert isinstance(backend, SilentBackend)

    def test_silent_is_default_in_ci(self, monkeypatch):
        """With no external deps, get_backend() falls back to SilentBackend."""
        _reset_logged(monkeypatch)
        monkeypatch.setenv("SKYHERD_VOICE", "live")
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        backend = get_backend()
        assert isinstance(backend, SilentBackend)

    def test_logged_once(self, monkeypatch, caplog):
        """get_backend() logs backend name exactly once per process."""
        import logging

        _reset_logged(monkeypatch)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.delenv("SKYHERD_VOICE", raising=False)
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        with caplog.at_level(logging.INFO, logger="skyherd.voice.tts"):
            get_backend()
            get_backend()
        info_msgs = [r for r in caplog.records if "TTS backend selected" in r.message]
        assert len(info_msgs) == 1


# ---------------------------------------------------------------------------
# SKYHERD_VOICE env flag — mock/silent force SilentBackend regardless of chain
# ---------------------------------------------------------------------------


class TestSkyherdVoiceFlag:
    def test_skyherd_voice_mock_forces_silent(self, monkeypatch):
        """SKYHERD_VOICE=mock wins over ELEVENLABS_API_KEY being set."""
        _reset_logged(monkeypatch)
        monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-key-xyz")
        monkeypatch.setenv("SKYHERD_VOICE", "mock")
        backend = get_backend()
        assert isinstance(backend, SilentBackend)

    def test_skyherd_voice_silent_alias(self, monkeypatch):
        """SKYHERD_VOICE=silent is an alias for mock."""
        _reset_logged(monkeypatch)
        monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-key-xyz")
        monkeypatch.setenv("SKYHERD_VOICE", "silent")
        backend = get_backend()
        assert isinstance(backend, SilentBackend)

    def test_skyherd_voice_live_uses_chain(self, monkeypatch):
        """SKYHERD_VOICE=live keeps the existing priority chain."""
        _reset_logged(monkeypatch)
        monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-key-xyz")
        monkeypatch.setenv("SKYHERD_VOICE", "live")
        backend = get_backend()
        assert isinstance(backend, ElevenLabsBackend)

    def test_skyherd_voice_unset_uses_chain(self, monkeypatch):
        """SKYHERD_VOICE unset → normal chain resolution."""
        _reset_logged(monkeypatch)
        monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-key-xyz")
        monkeypatch.delenv("SKYHERD_VOICE", raising=False)
        backend = get_backend()
        assert isinstance(backend, ElevenLabsBackend)

    def test_skyherd_voice_invalid_warns_and_falls_through(self, monkeypatch, caplog):
        """Unknown SKYHERD_VOICE value logs warning, falls through to normal chain."""
        import logging

        _reset_logged(monkeypatch)
        monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-key-xyz")
        monkeypatch.setenv("SKYHERD_VOICE", "banana")
        with caplog.at_level(logging.WARNING, logger="skyherd.voice.tts"):
            backend = get_backend()
        # Falls through to live chain
        assert isinstance(backend, ElevenLabsBackend)
        # And emits a warning
        warnings = [r for r in caplog.records if "SKYHERD_VOICE" in r.message]
        assert len(warnings) >= 1
        assert warnings[0].levelname == "WARNING"

    def test_skyherd_voice_mock_case_insensitive(self, monkeypatch):
        """SKYHERD_VOICE=MOCK (uppercase) behaves same as lowercase."""
        _reset_logged(monkeypatch)
        monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-key-xyz")
        monkeypatch.setenv("SKYHERD_VOICE", "MOCK")
        backend = get_backend()
        assert isinstance(backend, SilentBackend)


# ---------------------------------------------------------------------------
# Fallback-chain cascade — parametrized walk through all 4 resolution states
# ---------------------------------------------------------------------------


class TestResolveBackendCascade:
    """Verify each pruning step of the priority chain selects the next backend."""

    def test_cascade_elevenlabs_priority(self, monkeypatch):
        _reset_logged(monkeypatch)
        monkeypatch.delenv("SKYHERD_VOICE", raising=False)
        monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-key-xyz")
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/usr/bin/piper" if cmd == "piper" else None
        )
        from skyherd.voice import tts

        backend = tts._resolve_backend()
        assert isinstance(backend, ElevenLabsBackend)

    def test_cascade_piper_when_no_elevenlabs(self, monkeypatch):
        _reset_logged(monkeypatch)
        monkeypatch.delenv("SKYHERD_VOICE", raising=False)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setattr(
            "shutil.which",
            lambda cmd: (
                "/usr/bin/piper"
                if cmd == "piper"
                else ("/usr/bin/espeak" if cmd == "espeak" else None)
            ),
        )
        from skyherd.voice import tts

        backend = tts._resolve_backend()
        assert isinstance(backend, PiperBackend)

    def test_cascade_espeak_when_no_elevenlabs_no_piper(self, monkeypatch):
        _reset_logged(monkeypatch)
        monkeypatch.delenv("SKYHERD_VOICE", raising=False)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/usr/bin/espeak" if cmd == "espeak" else None
        )
        from skyherd.voice import tts

        backend = tts._resolve_backend()
        assert isinstance(backend, EspeakBackend)

    def test_cascade_silent_when_nothing(self, monkeypatch):
        _reset_logged(monkeypatch)
        monkeypatch.delenv("SKYHERD_VOICE", raising=False)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        from skyherd.voice import tts

        backend = tts._resolve_backend()
        assert isinstance(backend, SilentBackend)
