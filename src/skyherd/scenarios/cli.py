"""skyherd-demo CLI — play and list demo scenarios.

Commands
--------
play <name>        Run one scenario by name.
play all           Run all 5 scenarios back-to-back.
list               List all available scenarios.

Examples
--------
    skyherd-demo play coyote --seed 42
    skyherd-demo play all --seed 42
    skyherd-demo play coyote --dry-run
    skyherd-demo list
"""

from __future__ import annotations

import logging
from typing import Annotated

import typer

from skyherd.scenarios import SCENARIOS, run, run_all

app = typer.Typer(
    name="skyherd-demo",
    help="SkyHerd demo scenario runner — 5 deterministic ranch nervous-system playbacks.",
    add_completion=False,
)

logger = logging.getLogger(__name__)


@app.command("play")
def play(
    name: Annotated[
        str,
        typer.Argument(help="Scenario name or 'all'. One of: " + ", ".join(SCENARIOS) + ", all."),
    ],
    seed: Annotated[int, typer.Option("--seed", help="RNG seed for deterministic replay.")] = 42,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Set up world and return without running the sim loop."),
    ] = False,
) -> None:
    """Play one scenario or all 5 back-to-back.

    Examples::

        skyherd-demo play coyote --seed 42
        skyherd-demo play all --seed 42 --dry-run
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if name == "all":
        typer.echo(f"Running all {len(SCENARIOS)} scenarios (seed={seed})...")
        results = run_all(seed=seed)
        passed = sum(1 for r in results if r.outcome_passed)
        typer.echo(f"\n{'=' * 60}")
        typer.echo(f"Results: {passed}/{len(results)} passed")
        typer.echo(f"{'=' * 60}")
        for result in results:
            status = "PASS" if result.outcome_passed else f"FAIL: {result.outcome_error}"
            jsonl_info = str(result.jsonl_path) if result.jsonl_path else "—"
            typer.echo(
                f"  {result.name:<12} {status}  "
                f"({result.wall_time_s:.2f}s wall, {len(result.event_stream)} events)  "
                f"replay={jsonl_info}"
            )
        if passed < len(results):
            raise typer.Exit(code=1)
    elif name not in SCENARIOS:
        typer.echo(
            f"Unknown scenario: {name!r}. Available: {', '.join(SCENARIOS)}, all",
            err=True,
        )
        raise typer.Exit(code=2)
    else:
        typer.echo(f"Playing scenario: {name} (seed={seed}, dry_run={dry_run})")
        result = run(name, seed=seed, dry_run=dry_run)
        status = "PASS" if result.outcome_passed else f"FAIL: {result.outcome_error}"
        typer.echo(f"\nOutcome : {status}")
        typer.echo(f"Events  : {len(result.event_stream)}")
        typer.echo(f"Tools   : {sum(len(v) for v in result.agent_tool_calls.values())}")
        typer.echo(f"Attest  : {len(result.attestation_entries)}")
        typer.echo(f"Wall    : {result.wall_time_s:.2f}s")
        if result.jsonl_path:
            typer.echo(f"Replay  : {result.jsonl_path}")
        if not result.outcome_passed:
            raise typer.Exit(code=1)


@app.command("list")
def list_scenarios() -> None:
    """List all available demo scenarios."""
    typer.echo("Available SkyHerd demo scenarios:\n")
    for name, cls in SCENARIOS.items():
        scenario = cls()
        typer.echo(f"  {name:<12}  {scenario.description}")
    typer.echo("\nRun with: skyherd-demo play <name> [--seed 42] [--dry-run]")


def main() -> None:
    """Entry point registered as console_script skyherd-demo."""
    app()


if __name__ == "__main__":
    main()
