"""skyherd-demo-hw CLI — hardware-only demo runner.

Commands
--------
play --prop coyote|sick-cow|combo    Run the specified hardware demo prop.

Examples
--------
    skyherd-demo-hw play --prop combo
    skyherd-demo-hw play --prop coyote
    DRONE_BACKEND=mavic skyherd-demo-hw play --prop combo
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

import typer

app = typer.Typer(
    name="skyherd-demo-hw",
    help=(
        "SkyHerd hardware-only demo — 2× Pi 4 + Mavic Air 2 coyote+sick-cow combo. "
        "Set DRONE_BACKEND=mavic for real drone; defaults to SITL."
    ),
    add_completion=False,
)

logger = logging.getLogger(__name__)


@app.command("play")
def play(
    prop: Annotated[
        str,
        typer.Option(
            "--prop",
            help="Which prop to run: coyote, sick-cow, or combo (default).",
        ),
    ] = "combo",
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Seconds to wait for Pi detection before fallback."),
    ] = 180.0,
) -> None:
    """Run the hardware demo with real Pi cameras and Mavic drone.

    Supported props::

        coyote    — Pi #1 at fence, coyote cutout, Mavic dispatched
        sick-cow  — Pi #2 at trough, sick cow with ocular discharge
        combo     — coyote first, then sick-cow back-to-back

    Environment variables::

        ANTHROPIC_API_KEY     — real Claude calls (absent = sim path)
        DRONE_BACKEND         — mavic | sitl (default) | stub
        MAVIC_WS_URL          — ws://192.168.x.x:8765
        HARDWARE_OVERRIDES    — trough_cam:trough_1:edge-fence,...
        TWILIO_SID            — Twilio account SID for real Wes call
        TWILIO_TO_NUMBER      — George's phone (+1...)

    Examples::

        skyherd-demo-hw play --prop combo
        DRONE_BACKEND=mavic skyherd-demo-hw play --prop coyote --timeout 120
    """
    valid_props = {"coyote", "sick-cow", "combo"}
    if prop not in valid_props:
        typer.echo(
            f"Unknown prop: {prop!r}. Choose from: {', '.join(sorted(valid_props))}",
            err=True,
        )
        raise typer.Exit(code=2)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    typer.echo(f"Starting SkyHerd hardware-only demo — prop={prop}, timeout={timeout:.0f}s")
    typer.echo("Dashboard: http://localhost:8000")

    from skyherd.demo.hardware_only import HardwareOnlyDemo

    demo = HardwareOnlyDemo(prop=prop, timeout_s=timeout)
    result = asyncio.run(demo.run())

    typer.echo("\n" + "=" * 60)
    typer.echo(f"Demo complete — prop={result.prop}")
    typer.echo(f"  Hardware detection : {result.hardware_detection_received}")
    typer.echo(f"  Drone launched     : {result.drone_launched}")
    typer.echo(f"  Wes called         : {result.wes_called}")
    typer.echo(f"  Fallback used      : {result.fallback_used}")
    if result.fallback_reason:
        typer.echo(f"  Fallback reason    : {result.fallback_reason}")
    typer.echo(f"  Events recorded    : {len(result.events)}")
    typer.echo(f"  Tool calls         : {len(result.tool_calls)}")
    if result.jsonl_path:
        typer.echo(f"  Run log            : {result.jsonl_path}")
    typer.echo("=" * 60)

    if result.fallback_used:
        raise typer.Exit(code=0)  # fallback is graceful, not a failure


def main() -> None:
    """Entry point registered as console_script skyherd-demo-hw."""
    app()


if __name__ == "__main__":
    main()
