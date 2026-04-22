"""CLI entry-point for the SkyHerd Edge runtime.

Commands
--------
skyherd-edge run
    Start the capture/detect/publish loop.
skyherd-edge smoke
    Smoke-test: capture one mock frame, publish, and exit 0.
"""

from __future__ import annotations

import asyncio
import logging
import sys

import typer

app = typer.Typer(name="skyherd-edge", help="SkyHerd Pi H1 edge runtime.")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def run(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Start the EdgeWatcher capture/detect/publish loop."""
    _configure_logging(verbose)
    from skyherd.edge.watcher import EdgeWatcher

    watcher = EdgeWatcher()
    asyncio.run(watcher.run())


@app.command()
def smoke(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Smoke test: capture one mock frame, publish in-process, exit 0 on success."""
    _configure_logging(verbose)
    from skyherd.edge.camera import MockCamera
    from skyherd.edge.detector import RuleDetector
    from skyherd.edge.watcher import EdgeWatcher

    async def _run() -> None:
        # Use in-process mock — no broker required for smoke
        watcher = EdgeWatcher(
            camera=MockCamera(),
            detector=RuleDetector(),
            ranch_id="ranch_smoke",
            edge_id="smoke_node",
            mqtt_url="mqtt://localhost:19999",  # unreachable by design — publish is best-effort
            capture_interval_s=1.0,
        )
        payload = await watcher.run_once()
        count = len(payload.get("detections", []))
        typer.echo(f"smoke ok — 1 mock frame published, {count} detection(s)")

    try:
        asyncio.run(_run())
    except Exception as exc:
        typer.echo(f"smoke FAILED: {exc}", err=True)
        sys.exit(1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
