"""
skyherd.voice — Wes cowboy AI voice persona.

Exports:
    WesMessage       — pydantic model for a rancher page
    wes_say          — convenience: script + synthesize + play
    TTSBackend       — abstract base
    get_backend      — env-priority backend selector
    render_urgency_call — full pipeline: script → wav → deliver
"""

from skyherd.voice.call import render_urgency_call
from skyherd.voice.tts import TTSBackend, get_backend
from skyherd.voice.wes import WesMessage, wes_script

__all__ = [
    "WesMessage",
    "wes_script",
    "TTSBackend",
    "get_backend",
    "render_urgency_call",
    "wes_say",
]


def wes_say(text: str, voice: str = "wes") -> None:
    """Synthesize *text* and play it (best-effort)."""
    import subprocess
    from pathlib import Path

    backend = get_backend()
    wav: Path = backend.synthesize(text, voice=voice)

    # Best-effort playback — skip silently if no audio output
    for player in ("aplay", "afplay"):
        try:
            subprocess.run([player, str(wav)], check=True, capture_output=True)  # noqa: S603, S607
            break
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
