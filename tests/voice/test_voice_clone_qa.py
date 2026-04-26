"""Voice-clone QA — lightweight, deterministic regression tests.

Zero new runtime dependencies. Uses stdlib ``hashlib`` + committed reference
hash fixtures at ``tests/voice/fixtures/*.sha256`` to catch drift in:

1. ``SilentBackend`` WAV output (header + silence generator).
2. ``_mp3_to_wav`` converter fallback path (raw-bytes write when pydub fails).

A real-ElevenLabs smoke test is opt-in via ``ELEVENLABS_CLONE_QA=1`` so CI
stays offline + deterministic.
"""

from __future__ import annotations

import hashlib
import os
import struct
import sys
import types
from pathlib import Path

import pytest

from skyherd.voice.tts import ElevenLabsBackend, SilentBackend, _mp3_to_wav

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SILENT_REFERENCE_SHA256 = (FIXTURES_DIR / "wes_reference_silent.sha256").read_text().strip()
FAKE_EL_WAV_SHA256 = (FIXTURES_DIR / "fake_elevenlabs_wav.sha256").read_text().strip()


# ---------------------------------------------------------------------------
# Helper: reproducible fake MP3 byte sequence
# ---------------------------------------------------------------------------


def _fake_mp3_bytes(n: int = 512) -> bytes:
    """Deterministic pseudo-random bytes that are NOT a valid MP3.

    Forces the ``_mp3_to_wav`` pydub path to raise and the raw-bytes fallback
    to write the payload verbatim.  The hash is pinned so any change in the
    fallback path (e.g. someone accidentally wraps the raw bytes in a WAV
    header instead of writing them directly) is caught immediately.
    """
    return bytes(((i * 37 + 11) & 0xFF) for i in range(n))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Silent-backend reference hash
# ---------------------------------------------------------------------------


class TestSilentBackendReferenceHash:
    """SilentBackend must produce byte-identical output across runs + inputs."""

    def test_silent_backend_reference_hash_stable(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        hashes: set[str] = set()
        for text in ("Reference.", "completely different text", ""):
            wav = SilentBackend().synthesize(text)
            hashes.add(_sha256(wav.read_bytes()))
        assert len(hashes) == 1, f"SilentBackend output varies by input: {hashes}"
        assert hashes.pop() == SILENT_REFERENCE_SHA256, (
            "SilentBackend output drifted — regenerate fixture or revert the change"
        )

    def test_silent_backend_reference_duration_band(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        wav = SilentBackend().synthesize("Duration probe.")
        data = wav.read_bytes()
        sample_rate = struct.unpack_from("<I", data, 24)[0]
        byte_rate = struct.unpack_from("<I", data, 28)[0]
        data_size = struct.unpack_from("<I", data, 40)[0]
        duration_ms = (data_size / byte_rate) * 1000 if byte_rate else 0
        assert 240 <= duration_ms <= 260, (
            f"Expected ~250ms silence, got {duration_ms:.1f}ms "
            f"(sample_rate={sample_rate}, byte_rate={byte_rate}, data_size={data_size})"
        )

    def test_silent_backend_reference_is_valid_riff(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        wav = SilentBackend().synthesize("RIFF probe.")
        data = wav.read_bytes()
        assert data[:4] == b"RIFF", "Silent ref must be valid RIFF"
        assert data[8:12] == b"WAVE", "Silent ref must have WAVE marker"
        assert data[12:16] == b"fmt ", "Silent ref must have fmt chunk"
        assert data[36:40] == b"data", "Silent ref must have data chunk"


# ---------------------------------------------------------------------------
# ElevenLabs voice-clone QA (mocked audio)
# ---------------------------------------------------------------------------


def _install_fake_elevenlabs(monkeypatch, mp3_chunks: list[bytes]):
    """Inject fake elevenlabs module that yields *mp3_chunks* from convert()."""

    class _FakeTTSClient:
        def convert(self, **kw):  # noqa: ARG002
            yield from mp3_chunks

    class _FakeEL:
        def __init__(self, api_key: str):  # noqa: ARG002
            self.text_to_speech = _FakeTTSClient()

    fake_el = types.ModuleType("elevenlabs")
    fake_el.ElevenLabs = _FakeEL
    monkeypatch.setitem(sys.modules, "elevenlabs", fake_el)


class TestElevenLabsVoiceCloneQA:
    """Mocked ElevenLabs synth — verifies the byte-conversion pipeline is stable."""

    def test_elevenlabs_clone_qa_hash(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mp3 = _fake_mp3_bytes()
        _install_fake_elevenlabs(monkeypatch, [mp3])

        backend = ElevenLabsBackend(api_key="fake")
        wav = backend.synthesize("Howdy boss.")
        data = wav.read_bytes()

        assert _sha256(data) == FAKE_EL_WAV_SHA256, (
            "ElevenLabs -> WAV byte pipeline drifted. Regenerate fixture or revert."
        )

    def test_elevenlabs_clone_qa_size_band(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mp3 = _fake_mp3_bytes()
        _install_fake_elevenlabs(monkeypatch, [mp3])

        backend = ElevenLabsBackend(api_key="fake")
        wav = backend.synthesize("Size probe.")
        size = wav.stat().st_size
        assert 256 <= size <= 10_000, f"WAV out-of-band: {size} bytes"

    def test_elevenlabs_clone_qa_chunks_concatenated_correctly(self, tmp_path, monkeypatch):
        """Yielding MP3 bytes in multiple chunks must equal single-chunk output."""
        monkeypatch.chdir(tmp_path)
        mp3 = _fake_mp3_bytes()

        # First pass: single chunk
        _install_fake_elevenlabs(monkeypatch, [mp3])
        wav_single = ElevenLabsBackend(api_key="fake").synthesize("single")
        data_single = wav_single.read_bytes()

        # Second pass: same bytes split into 3 chunks
        split = [
            mp3[: len(mp3) // 3],
            mp3[len(mp3) // 3 : 2 * len(mp3) // 3],
            mp3[2 * len(mp3) // 3 :],
        ]
        _install_fake_elevenlabs(monkeypatch, split)
        wav_chunked = ElevenLabsBackend(api_key="fake").synthesize("chunked")
        data_chunked = wav_chunked.read_bytes()

        assert data_single == data_chunked, (
            "Chunked MP3 concatenation produced different WAV output"
        )
        assert _sha256(data_chunked) == FAKE_EL_WAV_SHA256

    def test_elevenlabs_ignores_non_bytes_chunks(self, tmp_path, monkeypatch):
        """convert() yielding non-bytes items (strings, None) must be skipped."""
        monkeypatch.chdir(tmp_path)
        mp3 = _fake_mp3_bytes()

        # Inject a sequence with non-bytes items interleaved
        mixed: list = [mp3[:100], "not-bytes", None, mp3[100:]]
        _install_fake_elevenlabs(monkeypatch, mixed)

        wav = ElevenLabsBackend(api_key="fake").synthesize("mixed chunks")
        data = wav.read_bytes()
        # Only the bytes chunks were concatenated
        assert _sha256(data) == FAKE_EL_WAV_SHA256


# ---------------------------------------------------------------------------
# _mp3_to_wav direct regression
# ---------------------------------------------------------------------------


class TestMp3ToWavFallback:
    def test_raw_bytes_fallback_hash_stable(self, tmp_path):
        mp3 = _fake_mp3_bytes()
        out = tmp_path / "fallback.wav"
        _mp3_to_wav(mp3, out)
        assert _sha256(out.read_bytes()) == FAKE_EL_WAV_SHA256


# ---------------------------------------------------------------------------
# Real ElevenLabs smoke (opt-in)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("ELEVENLABS_CLONE_QA"),
    reason="Live ElevenLabs smoke disabled by default — set ELEVENLABS_CLONE_QA=1 to enable",
)
class TestLiveElevenLabs:
    def test_live_elevenlabs_short_phrase_synthesizes(self, tmp_path, monkeypatch):
        """Smoke: real ElevenLabs TTS returns a non-trivial WAV.

        Requires ``ELEVENLABS_API_KEY`` in env and ``ELEVENLABS_CLONE_QA=1``.
        Never runs in CI.
        """
        import os as _os

        api_key = _os.environ.get("ELEVENLABS_API_KEY", "")
        assert api_key, "ELEVENLABS_API_KEY required for live smoke test"

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SKYHERD_VOICE", "live")
        backend = ElevenLabsBackend(api_key=api_key)
        wav = backend.synthesize("Howdy boss, tank three is dry.")
        assert wav.exists()
        assert wav.stat().st_size >= 1024, "Live ElevenLabs WAV should be >= 1KB"
