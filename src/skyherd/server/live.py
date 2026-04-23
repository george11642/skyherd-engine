"""Live-mode dashboard bootstrap — constructs real mesh/world/ledger
and hands them to create_app(). Inverse of SKYHERD_MOCK=1."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import typer
import uvicorn

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.server.app import create_app
from skyherd.world.world import make_world

app = typer.Typer(name="skyherd-server-live", add_completion=False)
logger = logging.getLogger(__name__)


@app.command()
def start(
    port: int = typer.Option(8000, "--port", "-p", help="HTTP port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host (127.0.0.1 for safety)"),
    seed: int = typer.Option(42, "--seed", help="World RNG seed"),
    log_level: str = typer.Option("info", "--log-level"),
) -> None:
    """Start dashboard in live mode: real world + in-memory ledger + demo mesh."""
    logging.basicConfig(level=log_level.upper())

    # Construct real deps (same pattern as scenarios/base.py:226-231)
    world = make_world(seed=seed)  # BLD-01: no config_path needed

    tmp = tempfile.NamedTemporaryFile(suffix="_skyherd_ledger.db", delete=False)
    tmp.close()
    ledger_path = Path(tmp.name)
    signer = Signer.generate()
    ledger = Ledger.open(str(ledger_path), signer)

    # Local import to avoid circular dep (scenarios imports server indirectly)
    from skyherd.scenarios.base import _DemoMesh  # noqa: PLC0415

    mesh = _DemoMesh(ledger=ledger)

    logger.info(
        "Live dashboard: seed=%d world_cows=%d ledger=%s",
        seed,
        len(world.herd.cows),
        ledger_path,
    )
    typer.echo(f"Starting SkyHerd live dashboard on {host}:{port} (seed={seed})")
    typer.echo("  Agent lanes will populate once 'make demo' runs in another terminal.")

    live_app = create_app(mock=False, mesh=mesh, world=world, ledger=ledger)
    uvicorn.run(live_app, host=host, port=port, log_level=log_level)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
