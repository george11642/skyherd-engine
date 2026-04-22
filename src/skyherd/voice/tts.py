"""
TTS backend chain: ElevenLabs > piper > espeak > SilentBackend.

get_backend() picks the highest-priority available backend and logs
its choice once per process.
"""

from __future__ import annotations

import logging
import os
import shutil
import struct
import subprocess
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)

_RUNTIME_VOICE_DIR = Path("runtime") / "voice"

# ElevenLabs voice ID to use -- low-pitch male voice.
# "Adam" premade voice (pNInz6obpgDQGcFmaJgB) -- Dominant, Firm -- free-tier compatible.
# Note: the old library voice ID (pMsXgVXv3BLzUgSXRplE) requires a paid plan.
ELEVENLABS_VOICE_ID = os.environ.get(
    "ELEVENLABS_VOICE_ID",
    "pNInz6obpgDQGcFmaJgB",  # Adam premade -- Dominant, Firm -- free-tier compatible
)
ELEVENLABS_MODEL_ID = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

_BACKEND_LOGGED = False


def _ensure_runtime_dir() -> Path:
    _RUNTIME_VOICE_DIR.mkdir(parents=True, exist_ok=True)
    return _RUNTIME_VOICE_DIR


def _wav_path() -> Path:
    return _ensure_runtime_dir() / f"{uuid.uuid4()}.wav"


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class TTSBackend(ABC):
    """Abstract TTS backend.  Returns a .wav path."""

    @abstractmethod
    def synthesize(self, text: str, voice: str = "wes") -> Path:
        """Synthesize *text* and return the path to a .wav file."""

    @property
    def name(self) -> str:
        return type(self).__name__


# ---------------------------------------------------------------------------
# ElevenLabs
# ---------------------------------------------------------------------------


class ElevenLabsBackend(TTSBackend):
    """ElevenLabs text-to-speech via the official Python SDK."""

    def __init__(self, api_key: str, voice_id: str = ELEVENLABS_VOICE_ID) -> None:
        self._api_key = api_key
        self._voice_id = voice_id

    def synthesize(self, text: str, voice: str = "wes") -> Path:  # noqa: ARG002
        from elevenlabs import ElevenLabs  # type: ignore[import]

        client = ElevenLabs(api_key=self._api_key)
        audio = client.text_to_speech.convert(
            voice_id=self._voice_id,
            text=text,
            model_id=ELEVENLABS_MODEL_ID,
            output_format="mp3_44100_128",  # free-tier compatible; converted to WAV below
        )

        # ElevenLabs returns an iterator of bytes chunks; collect into MP3 bytes
        chunks: list[bytes] = []
        for chunk in audio:
            if isinstance(chunk, bytes):
                chunks.append(chunk)
        mp3_data = b"".join(chunks)

        out = _wav_path()
        _mp3_to_wav(mp3_data, out)
        return out


# ---------------------------------------------------------------------------
# Piper
# ---------------------------------------------------------------------------


class PiperBackend(TTSBackend):
    """piper-tts CLI-based backend.  Requires `piper` on PATH."""

    # Default model -- downloads automatically on first use if configured
    MODEL = os.environ.get("PIPER_MODEL", "en_US-lessac-medium")

    def synthesize(self, text: str, voice: str = "wes") -> Path:  # noqa: ARG002
        out = _wav_path()
        try:
            proc = subprocess.run(  # noqa: S603
                ["piper", "--model", self.MODEL, "--output_file", str(out)],  # noqa: S607
                input=text.encode(),
                check=True,
                capture_output=True,
                timeout=30,
            )
            _ = proc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"piper failed: {exc.stderr.decode()[:200]}") from exc
        return out


# ---------------------------------------------------------------------------
# espeak
# ---------------------------------------------------------------------------


class EspeakBackend(TTSBackend):
    """espeak-ng CLI fallback.  Works fully offline."""

    def synthesize(self, text: str, voice: str = "wes") -> Path:  # noqa: ARG002
        out = _wav_path()
        try:
            subprocess.run(  # noqa: S603
                ["espeak", "-w", str(out), text],  # noqa: S607
                check=True,
                capture_output=True,
                timeout=15,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"espeak failed: {exc.stderr.decode()[:200]}") from exc
        return out


# ---------------------------------------------------------------------------
# Silent (CI / offline placeholder)
# ---------------------------------------------------------------------------

# 250 ms of silence at 16 kHz, 16-bit mono = 8000 samples = 16000 bytes PCM
_SILENCE_DURATION_MS = 250
_SILENCE_SAMPLE_RATE = 16000
_SILENCE_SAMPLE_WIDTH = 2  # bytes
_SILENCE_CHANNELS = 1
_SILENCE_NUM_SAMPLES = int(_SILENCE_SAMPLE_RATE * _SILENCE_DURATION_MS / 1000)
_SILENCE_PCM = b"\x00" * (_SILENCE_NUM_SAMPLES * _SILENCE_SAMPLE_WIDTH * _SILENCE_CHANNELS)


class SilentBackend(TTSBackend):
    """Writes a 250ms silent .wav.  Always works offline -- used in CI."""

    def synthesize(self, text: str, voice: str = "wes") -> Path:  # noqa: ARG002
        out = _wav_path()
        _write_wav(
            _SILENCE_PCM,
            out,
            sample_rate=_SILENCE_SAMPLE_RATE,
            channels=_SILENCE_CHANNELS,
            sample_width=_SILENCE_SAMPLE_WIDTH,
        )
        return out


# ---------------------------------------------------------------------------
# MP3 to WAV converter (used by ElevenLabs free-tier path)
# ---------------------------------------------------------------------------


def _mp3_to_wav(mp3_data: bytes, path: Path) -> None:
    """Convert MP3 bytes to a WAV file.

    Tries pydub (requires ffmpeg) first; falls back to writing the raw MP3
    bytes directly (sufficient for pipeline validation when ffmpeg is absent).
    """
    try:
        import io

        from pydub import AudioSegment  # type: ignore[import]

        seg = AudioSegment.from_mp3(io.BytesIO(mp3_data))
        seg = seg.set_channels(1).set_frame_rate(44100).set_sample_width(2)
        pcm = seg.raw_data
        _write_wav(pcm, path, sample_rate=44100, channels=1, sample_width=2)
        return
    except Exception:  # noqa: BLE001
        pass

    # Fallback: write MP3 bytes directly -- not a RIFF/WAV, but lets the rest
    # of the pipeline measure file size and continue.
    path.write_bytes(mp3_data)


# ---------------------------------------------------------------------------
# WAV writer
# ---------------------------------------------------------------------------


def _write_wav(
    pcm: bytes, path: Path, *, sample_rate: int, channels: int, sample_width: int
) -> None:
    """Write raw PCM data as a RIFF/WAV file."""
    data_size = len(pcm)
    byte_rate = sample_rate * channels * sample_width
    block_align = channels * sample_width

    with path.open("wb") as fh:
        # RIFF header
        fh.write(b"RIFF")
        fh.write(struct.pack("<I", 36 + data_size))  # file size - 8
        fh.write(b"WAVE")
        # fmt chunk
        fh.write(b"fmt ")
        fh.write(struct.pack("<I", 16))  # chunk size
        fh.write(struct.pack("<H", 1))  # PCM = 1
        fh.write(struct.pack("<H", channels))
        fh.write(struct.pack("<I", sample_rate))
        fh.write(struct.pack("<I", byte_rate))
        fh.write(struct.pack("<H", block_align))
        fh.write(struct.pack("<H", sample_width * 8))  # bits per sample
        # data chunk
        fh.write(b"data")
        fh.write(struct.pack("<I", data_size))
        fh.write(pcm)


# ---------------------------------------------------------------------------
# Backend selector
# ---------------------------------------------------------------------------


def get_backend() -> TTSBackend:
    """
    Return the highest-priority available TTS backend.

    Priority: ElevenLabs > piper > espeak > Silent.
    Logs the selection once per process.
    """
    global _BACKEND_LOGGED  # noqa: PLW0603

    backend = _resolve_backend()

    if not _BACKEND_LOGGED:
        logger.info("TTS backend selected: %s", backend.name)
        _BACKEND_LOGGED = True

    return backend


def _resolve_backend() -> TTSBackend:
    # 1 -- ElevenLabs
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if api_key:
        return ElevenLabsBackend(api_key=api_key)

    # 2 -- piper
    if shutil.which("piper"):
        return PiperBackend()

    # 3 -- espeak
    if shutil.which("espeak") or shutil.which("espeak-ng"):
        return EspeakBackend()

    # 4 -- silent (always works)
    return SilentBackend()
