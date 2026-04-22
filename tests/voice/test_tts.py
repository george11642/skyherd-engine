"""Tests for TTS backends — focus on SilentBackend (always offline)."""

from __future__ import annotations

import struct
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

from skyherd.voice.tts import (
    ElevenLabsBackend,
    EspeakBackend,
    PiperBackend,
    SilentBackend,
    _mp3_to_wav,
    _write_wav,
)


class TestSilentBackend:
    def test_synthesize_returns_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        backend = SilentBackend()
        wav = backend.synthesize("Test message.")
        assert isinstance(wav, Path)
        assert wav.exists()

    def test_output_is_valid_riff_wav(self, tmp_path, monkeypatch):
        """Verify RIFF header and 44-byte WAV structure."""
        monkeypatch.chdir(tmp_path)
        backend = SilentBackend()
        wav = backend.synthesize("Silence test.")
        data = wav.read_bytes()

        # RIFF magic
        assert data[:4] == b"RIFF", "Missing RIFF magic"
        # WAVE marker at byte 8
        assert data[8:12] == b"WAVE", "Missing WAVE marker"
        # fmt chunk
        assert data[12:16] == b"fmt ", "Missing fmt chunk"
        fmt_size = struct.unpack_from("<I", data, 16)[0]
        assert fmt_size == 16, "fmt chunk should be 16 bytes (PCM)"
        # Audio format = 1 (PCM)
        audio_fmt = struct.unpack_from("<H", data, 20)[0]
        assert audio_fmt == 1, "Audio format should be 1 (PCM)"
        # data chunk at byte 36
        assert data[36:40] == b"data", "Missing data chunk"
        # Header is exactly 44 bytes before payload
        data_size = struct.unpack_from("<I", data, 40)[0]
        assert len(data) == 44 + data_size

    def test_output_has_nonzero_duration(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        backend = SilentBackend()
        wav = backend.synthesize("Duration check.")
        data = wav.read_bytes()
        # At 16kHz, 16-bit mono, 250ms = 4000 samples × 2 bytes = 8000 bytes PCM
        data_size = struct.unpack_from("<I", data, 40)[0]
        assert data_size == 4000 * 2, f"Expected 8000 bytes PCM, got {data_size}"

    def test_name_property(self):
        assert SilentBackend().name == "SilentBackend"


class TestWriteWav:
    def test_round_trip(self, tmp_path):
        pcm = b"\x00\x01" * 100
        out = tmp_path / "test.wav"
        _write_wav(pcm, out, sample_rate=8000, channels=1, sample_width=2)
        data = out.read_bytes()
        assert data[:4] == b"RIFF"
        assert data[8:12] == b"WAVE"
        # data payload should match
        data_size = struct.unpack_from("<I", data, 40)[0]
        assert data[44 : 44 + data_size] == pcm


class TestElevenLabsBackend:
    """Cover ElevenLabsBackend.synthesize with a mocked elevenlabs package."""

    def test_synthesize_produces_wav(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        # Build a minimal fake elevenlabs module
        fake_el = types.ModuleType("elevenlabs")
        fake_client_instance = MagicMock()
        # .text_to_speech.convert returns an iterable of bytes chunks
        fake_client_instance.text_to_speech.convert.return_value = [b"ID3\x00\x00\x00"]
        fake_el.ElevenLabs = MagicMock(return_value=fake_client_instance)
        monkeypatch.setitem(sys.modules, "elevenlabs", fake_el)

        backend = ElevenLabsBackend(api_key="fake-key")
        wav = backend.synthesize("Howdy, boss.")
        assert isinstance(wav, Path)
        assert wav.exists()

    def test_synthesize_uses_voice_id(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        fake_el = types.ModuleType("elevenlabs")
        fake_client_instance = MagicMock()
        fake_client_instance.text_to_speech.convert.return_value = [b"\x00\x01\x02"]
        fake_el.ElevenLabs = MagicMock(return_value=fake_client_instance)
        monkeypatch.setitem(sys.modules, "elevenlabs", fake_el)

        backend = ElevenLabsBackend(api_key="k", voice_id="custom-voice-id")
        backend.synthesize("Test.")
        call_kwargs = fake_client_instance.text_to_speech.convert.call_args
        assert call_kwargs.kwargs["voice_id"] == "custom-voice-id"


class TestPiperBackend:
    """Cover PiperBackend.synthesize via mocked subprocess.run."""

    def test_synthesize_returns_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        def _fake_run(cmd, **kwargs):
            # Write a valid silent WAV to the output path so the pipeline works
            out_path = Path(cmd[cmd.index("--output_file") + 1])
            pcm = b"\x00" * 100
            _write_wav(pcm, out_path, sample_rate=16000, channels=1, sample_width=2)
            result = MagicMock()
            result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", _fake_run)
        backend = PiperBackend()
        wav = backend.synthesize("Heads up.")
        assert isinstance(wav, Path)
        assert wav.exists()

    def test_synthesize_raises_on_failure(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        def _fail_run(cmd, **kwargs):
            raise subprocess.CalledProcessError(1, cmd, stderr=b"piper error")

        monkeypatch.setattr("subprocess.run", _fail_run)
        import pytest

        backend = PiperBackend()
        with pytest.raises(RuntimeError, match="piper failed"):
            backend.synthesize("Test.")


class TestEspeakBackend:
    """Cover EspeakBackend.synthesize via mocked subprocess.run."""

    def test_synthesize_returns_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        def _fake_run(cmd, **kwargs):
            out_path = Path(cmd[2])  # espeak -w <out> <text>
            pcm = b"\x00" * 100
            _write_wav(pcm, out_path, sample_rate=16000, channels=1, sample_width=2)
            result = MagicMock()
            result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", _fake_run)
        backend = EspeakBackend()
        wav = backend.synthesize("Fence alert.")
        assert isinstance(wav, Path)
        assert wav.exists()

    def test_synthesize_raises_on_failure(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        def _fail_run(cmd, **kwargs):
            raise subprocess.CalledProcessError(1, cmd, stderr=b"espeak error")

        monkeypatch.setattr("subprocess.run", _fail_run)
        import pytest

        backend = EspeakBackend()
        with pytest.raises(RuntimeError, match="espeak failed"):
            backend.synthesize("Test.")


class TestMp3ToWav:
    """Cover _mp3_to_wav — pydub path and raw-bytes fallback."""

    def test_fallback_without_pydub(self, tmp_path, monkeypatch):
        """When pydub is absent, raw bytes are written directly."""
        monkeypatch.setitem(sys.modules, "pydub", None)
        out = tmp_path / "out.wav"
        mp3_data = b"fake-mp3-bytes"
        _mp3_to_wav(mp3_data, out)
        assert out.read_bytes() == mp3_data

    def test_pydub_path(self, tmp_path, monkeypatch):
        """When pydub succeeds, a proper WAV is written."""
        # Create a fake pydub.AudioSegment
        fake_pydub = types.ModuleType("pydub")

        class FakeSegment:
            @classmethod
            def from_mp3(cls, fp):
                inst = cls()
                inst.raw_data = b"\x00" * 200
                return inst

            def set_channels(self, n):
                return self

            def set_frame_rate(self, r):
                return self

            def set_sample_width(self, w):
                return self

        fake_pydub.AudioSegment = FakeSegment
        monkeypatch.setitem(sys.modules, "pydub", fake_pydub)

        out = tmp_path / "out.wav"
        _mp3_to_wav(b"fake-mp3", out)
        data = out.read_bytes()
        assert data[:4] == b"RIFF"
