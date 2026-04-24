"""Generate ``predator_12khz.wav`` — 6s 12kHz sine wave, mono, 44.1kHz.

Stdlib-only (``wave`` + ``math``) so the build has zero external deps and is
byte-identical across platforms.  Re-runs overwrite the file with the same
bytes — acts as a self-test for generator determinism.

Run from the repo root:

    uv run python -m skyherd.edge.fixtures.deterrent._generate

Tests can import ``generate()`` directly and diff the output against a fresh
regeneration.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

__all__ = ["DEFAULT_OUTPUT", "generate"]


DEFAULT_OUTPUT = Path(__file__).parent / "predator_12khz.wav"


def generate(
    output: Path | str | None = None,
    *,
    tone_hz: int = 12000,
    duration_s: float = 6.0,
    sample_rate: int = 44100,
    amplitude: float = 0.5,
) -> Path:
    """Write a mono 16-bit PCM WAV file and return its path."""
    output_path = Path(output) if output else DEFAULT_OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n_samples = int(duration_s * sample_rate)
    # Peak short-int value; 0.5 amplitude keeps it well under clipping.
    peak = int(32767 * max(0.0, min(1.0, amplitude)))

    frames = bytearray()
    two_pi_f = 2.0 * math.pi * tone_hz / sample_rate
    for i in range(n_samples):
        sample = int(peak * math.sin(two_pi_f * i))
        frames += struct.pack("<h", sample)

    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(frames))

    return output_path


if __name__ == "__main__":
    path = generate()
    size_kb = path.stat().st_size / 1024.0
    print(f"generated {path} ({size_kb:.1f} KB)")
