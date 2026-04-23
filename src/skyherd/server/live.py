"""Live-mode dashboard bootstrap - constructs real mesh/world/ledger
and hands them to create_app(). Inverse of SKYHERD_MOCK=1.

An in-process ambient scenario driver (v1.1 Part A) rotates through the
8 demo scenarios against the same deps so the live dashboard has visible
activity without a second process. Disable with ``--no-ambient`` or
``SKYHERD_AMBIENT=0``.
"""

from __future__ import annotations

import logging
import os
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


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@app.command()
def start(
    port: int = typer.Option(8000, "--port", "-p", help="HTTP port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host (127.0.0.1 for safety)"),
    seed: int = typer.Option(42, "--seed", help="World RNG seed"),
    log_level: str = typer.Option("info", "--log-level"),
    ambient: bool = typer.Option(
        None,  # sentinel - resolved from env when omitted
        "--ambient/--no-ambient",
        help="Run the in-process ambient scenario loop (default on; env SKYHERD_AMBIENT=0 to disable)",
    ),
    speed: float = typer.Option(
        None,  # sentinel - resolved from env when omitted
        "--speed",
        help="Ambient sim-to-wall speed ratio (default 15.0; env SKYHERD_AMBIENT_SPEED)",
    ),
) -> None:
    """Start dashboard in live mode: real world + in-memory ledger + demo mesh."""
    logging.basicConfig(level=log_level.upper())

    ambient_on = _env_bool("SKYHERD_AMBIENT", True) if ambient is None else ambient
    ambient_speed = _env_float("SKYHERD_AMBIENT_SPEED", 15.0) if speed is None else speed

    # Construct real deps (same pattern as scenarios/base.py)
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
    if ambient_on:
        typer.echo(
            f"  Ambient scenario loop: ON @ {ambient_speed}x "
            "(coyote -> sick_cow -> water_drop -> storm -> calving -> "
            "wildfire -> rustling -> cross_ranch_coyote, repeat)"
        )
    else:
        typer.echo("  Ambient scenario loop: OFF (SKYHERD_AMBIENT=0 or --no-ambient)")

    live_app = create_app(mock=False, mesh=mesh, world=world, ledger=ledger)

    if ambient_on:
        from contextlib import asynccontextmanager  # noqa: PLC0415

        from skyherd.server import app as _app_module  # noqa: PLC0415
        from skyherd.server.ambient import AmbientDriver  # noqa: PLC0415

        # create_app() already installs its own lifespan (broadcaster start/stop),
        # so FastAPI's @on_event("startup") hooks are ignored. Wrap the existing
        # lifespan to attach the ambient driver while the broadcaster is alive.
        original_lifespan = live_app.router.lifespan_context

        @asynccontextmanager
        async def _ambient_lifespan(fastapi_app):  # type: ignore[no-untyped-def]
            async with original_lifespan(fastapi_app):
                broadcaster = getattr(_app_module, "_broadcaster", None)
                driver = AmbientDriver(
                    mesh=mesh,
                    world=world,
                    ledger=ledger,
                    broadcaster=broadcaster,
                    speed=ambient_speed,
                )
                live_app.state.ambient_driver = driver
                await driver.start()
                logger.info("AmbientDriver started @ %.2fx", ambient_speed)
                try:
                    yield
                finally:
                    await driver.stop()
                    logger.info("AmbientDriver stopped")

        live_app.router.lifespan_context = _ambient_lifespan

    uvicorn.run(live_app, host=host, port=port, log_level=log_level)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
