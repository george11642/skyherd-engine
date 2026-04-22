"""skyherd-server CLI — typer entry point."""

from __future__ import annotations

import logging
import os

import typer
import uvicorn

app = typer.Typer(name="skyherd-server", help="SkyHerd dashboard server")


@app.command()
def start(
    port: int = typer.Option(8000, "--port", "-p", help="HTTP port"),
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host"),
    mock: bool = typer.Option(
        True, "--mock/--no-mock", help="Use mock data (no live sim required)"
    ),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code change"),
    log_level: str = typer.Option("info", "--log-level"),
) -> None:
    """Start the SkyHerd FastAPI dashboard server."""
    if mock:
        os.environ["SKYHERD_MOCK"] = "1"
    logging.basicConfig(level=log_level.upper())
    typer.echo(f"Starting SkyHerd server on {host}:{port} (mock={mock})")
    uvicorn.run(
        "skyherd.server.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
