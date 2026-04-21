"""Tests for TTS backends — focus on SilentBackend (always offline)."""

from __future__ import annotations

import struct
from pathlib import Path

from skyherd.voice.tts import SilentBackend, _write_wav


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
        assert data[44:44 + data_size] == pcm
