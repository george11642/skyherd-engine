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
    """Render 5 Wes lines -- one per urgency level -- and print scripts + wav paths."""
    from skyherd.voice.call import render_urgency_call
    from skyherd.voice.wes import WesMessage

    samples = [
        WesMessage(
            urgency="log",
            subject="gate cam 2 battery swapped",
        ),
        WesMessage(
            urgency="text",
            subject="water tank 3 low",
            context={"tank_id": "Tank 3", "level": "18%"},
        ),
        WesMessage(
            urgency="call",
            subject="coyote at the SW fence",
            context={"location": "SW fence"},
        ),
        WesMessage(
            urgency="emergency",
            subject="predator inside the herd, south pasture",
            context={"predator": "coyote"},
        ),
        WesMessage(
            urgency="silent",
            subject="nightly pattern roll-up",
        ),
    ]

    typer.echo("=== Wes Demo -- 5 urgency levels ===\n")
    for msg in samples:
        result = render_urgency_call(msg)
        label = f"[{msg.urgency.upper()}]"
        script = result.get("script") or "(silent)"
        typer.echo(f"{label:<12} {script}")
        wav_path = result.get("wav_path")
        if wav_path is None:
            typer.echo(f"{'':<12} (log-only)\n")
        else:
            typer.echo(f"{'':<12} wav -> {wav_path}\n")

    typer.echo("Demo complete.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
