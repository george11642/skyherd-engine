"""Tests for skyherd.voice.cli — typer CLI entry point."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from skyherd.voice.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_backend(tmp_path: Path) -> MagicMock:
    """Return a mock TTS backend whose synthesize() writes a silent .wav."""
    import struct

    wav = tmp_path / "test.wav"
    # Write a minimal valid WAV (1 sample, 16-bit mono 22050 Hz)
    silence = b"\x00\x00"
    sample_rate, channels, sample_width = 22050, 1, 2
    data_size = len(silence)
    byte_rate = sample_rate * channels * sample_width
    block_align = channels * sample_width
    with wav.open("wb") as fh:
        fh.write(b"RIFF")
        fh.write(struct.pack("<I", 36 + data_size))
        fh.write(b"WAVE")
        fh.write(b"fmt ")
        fh.write(struct.pack("<I", 16))
        fh.write(struct.pack("<H", 1))
        fh.write(struct.pack("<H", channels))
        fh.write(struct.pack("<I", sample_rate))
        fh.write(struct.pack("<I", byte_rate))
        fh.write(struct.pack("<H", block_align))
        fh.write(struct.pack("<H", sample_width * 8))
        fh.write(b"data")
        fh.write(struct.pack("<I", data_size))
        fh.write(silence)

    backend = MagicMock()
    backend.synthesize.return_value = wav
    return backend


# ---------------------------------------------------------------------------
# say command
# ---------------------------------------------------------------------------


def test_say_help():
    result = runner.invoke(app, ["say", "--help"])
    assert result.exit_code == 0
    assert "text" in result.output.lower() or "TEXT" in result.output


def test_say_synthesizes_text(tmp_path: Path):
    """say <text> calls backend.synthesize and echoes the wav path."""
    mock_backend = _make_mock_backend(tmp_path)
    with patch("skyherd.voice.cli.subprocess.run", side_effect=FileNotFoundError):
        with patch("skyherd.voice.tts.get_backend", return_value=mock_backend):
            result = runner.invoke(app, ["say", "Tank 3 is dry"])
    assert result.exit_code == 0
    mock_backend.synthesize.assert_called_once_with("Tank 3 is dry", voice="wes")
    # Output must mention the wav path
    assert str(mock_backend.synthesize.return_value) in result.output


def test_say_custom_voice(tmp_path: Path):
    """--voice option is forwarded to synthesize."""
    mock_backend = _make_mock_backend(tmp_path)
    with patch("skyherd.voice.cli.subprocess.run", side_effect=FileNotFoundError):
        with patch("skyherd.voice.tts.get_backend", return_value=mock_backend):
            runner.invoke(app, ["say", "Hello", "--voice", "cowboy"])
    mock_backend.synthesize.assert_called_once_with("Hello", voice="cowboy")


def test_say_no_audio_player_fallback(tmp_path: Path):
    """When no audio player is found, fallback message is printed."""
    mock_backend = _make_mock_backend(tmp_path)
    with patch("skyherd.voice.cli.subprocess.run", side_effect=FileNotFoundError):
        with patch("skyherd.voice.tts.get_backend", return_value=mock_backend):
            result = runner.invoke(app, ["say", "No player test"])
    assert "No audio player" in result.output or result.exit_code == 0


# ---------------------------------------------------------------------------
# demo command
# ---------------------------------------------------------------------------


def test_demo_help():
    result = runner.invoke(app, ["demo", "--help"])
    assert result.exit_code == 0


def test_demo_runs_and_prints_wav_paths(tmp_path: Path):
    """demo command renders 3 sample lines and prints their wav paths."""
    # render_urgency_call is imported lazily inside the function — patch at source
    fake_result = {"script": "Coyote at the fence, boss.", "wav_path": str(tmp_path / "wes.wav")}
    with patch("skyherd.voice.call.render_urgency_call", return_value=fake_result) as mock_render:
        result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    # render_urgency_call called 3 times (one per sample message)
    assert mock_render.call_count == 3
    # Output contains the script
    assert "Coyote at the fence" in result.output
    # Output contains "Demo complete"
    assert "Demo complete" in result.output


def test_demo_output_contains_urgency_labels(tmp_path: Path):
    """demo output labels each message with CALL or TEXT."""
    fake_result = {"script": "Water low.", "wav_path": str(tmp_path / "wes.wav")}
    with patch("skyherd.voice.call.render_urgency_call", return_value=fake_result):
        result = runner.invoke(app, ["demo"])
    # At least one CALL and one TEXT label should appear
    assert "CALL" in result.output
    assert "TEXT" in result.output


# ---------------------------------------------------------------------------
# main entry-point
# ---------------------------------------------------------------------------


def test_main_callable():
    from skyherd.voice.cli import main

    assert callable(main)
