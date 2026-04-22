"""SkyHerd Mesh CLI — typer commands for the 5-agent managed-agent mesh.

Commands
--------
    skyherd-mesh mesh start   — start the mesh (blocks until Ctrl-C)
    skyherd-mesh mesh stop    — graceful stop (sends SIGTERM to running mesh)
    skyherd-mesh mesh smoke   — run the smoke test without an API key
"""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Annotated

import typer

app = typer.Typer(
    name="skyherd-mesh",
    help="SkyHerd 5-agent managed-agent mesh CLI.",
    add_completion=False,
)

mesh_app = typer.Typer(help="Mesh lifecycle commands.")
app.add_typer(mesh_app, name="mesh")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@mesh_app.command("start")
def mesh_start(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable DEBUG logging.")] = False,
) -> None:
    """Start all 5 agent sessions and the cost-tick loop.

    Blocks until Ctrl-C or SIGTERM.  Sessions are checkpointed on shutdown.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    async def _run() -> None:
        from skyherd.agents.mesh import AgentMesh

        mesh = AgentMesh()
        loop = asyncio.get_running_loop()

        stop = asyncio.Event()

        def _handle_signal() -> None:
            typer.echo("\nShutting down mesh…")
            stop.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _handle_signal)

        await mesh.start()
        typer.echo("AgentMesh started — 5 sessions idle, cost ticker running.  Ctrl-C to stop.")

        await stop.wait()
        await mesh.stop()
        typer.echo("AgentMesh stopped — all sessions checkpointed.")

    asyncio.run(_run())


@mesh_app.command("stop")
def mesh_stop() -> None:
    """Send SIGTERM to the running mesh process (found via PID file).

    This is a convenience wrapper — in practice you can also Ctrl-C the
    ``mesh start`` process directly.
    """
    import os

    pid_file = "runtime/mesh.pid"
    try:
        with open(pid_file) as fh:
            pid = int(fh.read().strip())
        os.kill(pid, signal.SIGTERM)
        typer.echo(f"Sent SIGTERM to PID {pid}.")
    except FileNotFoundError:
        typer.echo(f"PID file not found: {pid_file}.  Is the mesh running?", err=True)
        raise typer.Exit(code=1)
    except ProcessLookupError:
        typer.echo("Mesh process not found — may have already exited.", err=True)
        raise typer.Exit(code=1)


@mesh_app.command("smoke")
def mesh_smoke(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Print per-agent tool calls.")
    ] = False,
) -> None:
    """Run the smoke test — fire one synthetic wake event per agent.

    Works without ANTHROPIC_API_KEY (simulation path).  Exits 0 on success.
    """
    import json

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    async def _run() -> dict[str, object]:
        from skyherd.agents.mesh import AgentMesh

        mesh = AgentMesh()
        results = await mesh.smoke_test(sdk_client=None)
        return results

    results = asyncio.run(_run())

    total_calls = sum(len(v) for v in results.values())
    typer.echo(f"\nSmoke test complete — {len(results)} agents, {total_calls} total tool calls.\n")

    for agent_name, calls in results.items():
        status = "OK" if calls else "WARN (0 calls)"
        typer.echo(f"  {agent_name:<28} {status}")
        if verbose and calls:
            typer.echo(f"    {json.dumps(calls, indent=2)}")

    failed = [name for name, calls in results.items() if not calls]
    if failed:
        typer.echo(f"\nWARN: no tool calls from: {', '.join(failed)}", err=True)
        raise typer.Exit(code=1)

    typer.echo("\nAll agents produced tool calls.  Smoke test PASSED.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
