"""
skyherd-voice CLI — synthesize Wes lines and run demo.

Usage:
    skyherd-voice say "Tank 3 is dry" [--voice wes]
    skyherd-voice demo
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer

app = typer.Typer(help="Wes voice persona CLI for SkyHerd.")


@app.command()
def say(
    text: str = typer.Argument(..., help="Text to synthesize."),
    voice: str = typer.Option("wes", help="Voice identifier (passed to backend)."),
) -> None:
    """Synthesize TEXT and play it (best-effort)."""
    from skyherd.voice.tts import get_backend

    backend = get_backend()
    wav: Path = backend.synthesize(text, voice=voice)
    typer.echo(f"Wrote {wav}")

    for player in ("aplay", "afplay"):
        try:
            subprocess.run([player, str(wav)], check=True, capture_output=True)  # noqa: S603, S607
            typer.echo(f"Played via {player}.")
            break
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    else:
        typer.echo("No audio player found — wav saved above.")


@app.command()
def demo() -> None:
    """Render 3 sample Wes lines and print the wav paths."""
    from skyherd.voice.call import render_urgency_call
    from skyherd.voice.wes import WesMessage

    samples = [
        WesMessage(
            urgency="call",
            subject="coyote at the SW fence",
            context={"location": "SW fence"},
        ),
        WesMessage(
            urgency="call",
            subject="calving detected — B007 gone off alone",
            context={"animal_id": "B007"},
        ),
        WesMessage(
            urgency="text",
            subject="water tank 3 low",
            context={"tank_id": "Tank 3", "level": "18%"},
        ),
    ]

    typer.echo("=== Wes Demo — 3 sample lines ===\n")
    for msg in samples:
        result = render_urgency_call(msg)
        typer.echo(f"[{msg.urgency.upper()}]  {result['script']}")
        typer.echo(f"           wav -> {result['wav_path']}\n")

    typer.echo("Demo complete.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
