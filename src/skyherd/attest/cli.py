"""Typer CLI for the SkyHerd attestation chain.

Sub-commands
------------
init    — Create a new signer keypair + ledger.
append  — Read a JSON payload from stdin and append an event.
verify  — Run full chain verification and print a coloured report.
list    — Print recent events (tail).

Console script: ``skyherd-attest`` (registered in pyproject.toml).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer

app = typer.Typer(
    name="skyherd-attest",
    help="Tamper-evident attestation chain for SkyHerd ranch events.",
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Default paths (overridable via options)
# ---------------------------------------------------------------------------

_DEFAULT_KEY = Path("attest.key.pem")
_DEFAULT_DB = Path("attest.db")


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@app.command()
def init(
    key_path: Path = typer.Option(_DEFAULT_KEY, "--key", help="Path to write private key PEM."),
    db_path: Path = typer.Option(_DEFAULT_DB, "--db", help="Path to create SQLite ledger."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing key/db."),
) -> None:
    """Create a new Ed25519 signer and initialise the ledger."""
    if key_path.exists() and not force:
        err_console.print(
            f"[red]Key already exists at {key_path}. Use --force to overwrite.[/red]"
        )
        raise typer.Exit(1)

    signer = Signer.generate()
    signer.save(key_path)

    with Ledger.open(db_path, signer):
        pass  # creates the table

    console.print(f"[green]Key written to[/green] {key_path} (chmod 600)")
    console.print(f"[green]Ledger created at[/green] {db_path}")
    console.print(f"[dim]Public key:[/dim]\n{signer.public_key_pem}")


# ---------------------------------------------------------------------------
# append
# ---------------------------------------------------------------------------


@app.command()
def append(
    source: str = typer.Argument(..., help='Event source, e.g. "sensor.water.3".'),
    kind: str = typer.Argument(..., help='Event kind, e.g. "water.low".'),
    key_path: Path = typer.Option(_DEFAULT_KEY, "--key", help="Path to private key PEM."),
    db_path: Path = typer.Option(_DEFAULT_DB, "--db", help="Path to SQLite ledger."),
) -> None:
    """Read JSON payload from stdin, append to the ledger."""
    raw = sys.stdin.read().strip()
    if not raw:
        err_console.print("[red]No JSON payload on stdin.[/red]")
        raise typer.Exit(1)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        err_console.print(f"[red]Invalid JSON: {exc}[/red]")
        raise typer.Exit(1)

    if not isinstance(payload, dict):
        err_console.print("[red]Payload must be a JSON object (dict).[/red]")
        raise typer.Exit(1)

    signer = Signer.from_file(key_path)
    with Ledger.open(db_path, signer) as ledger:
        event = ledger.append(source, kind, payload)

    console.print(
        f"[green]Appended seq={event.seq}[/green] "
        f"source={event.source!r} kind={event.kind!r} "
        f"hash={event.event_hash[:16]}..."
    )


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


@app.command()
def verify(
    db_path: Path = typer.Option(_DEFAULT_DB, "--db", help="Path to SQLite ledger."),
    key_path: Path = typer.Option(_DEFAULT_KEY, "--key", help="Path to private key PEM."),
) -> None:
    """Walk the entire chain and verify every hash and signature."""
    signer = Signer.from_file(key_path)
    with Ledger.open(db_path, signer) as ledger:
        result = ledger.verify()

    if result.valid:
        console.print(
            f"[bold green]CHAIN VALID[/bold green] — {result.total} event(s) verified."
        )
    else:
        err_console.print(
            f"[bold red]CHAIN INVALID[/bold red] — "
            f"first bad seq={result.first_bad_seq}, reason: {result.reason}"
        )
        raise typer.Exit(2)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@app.command(name="list")
def list_events(
    db_path: Path = typer.Option(_DEFAULT_DB, "--db", help="Path to SQLite ledger."),
    key_path: Path = typer.Option(_DEFAULT_KEY, "--key", help="Path to private key PEM."),
    since: int = typer.Option(0, "--since", help="Only show events with seq > SINCE."),
    tail: int = typer.Option(20, "--tail", "-n", help="Maximum number of events to display."),
) -> None:
    """Print recent events from the ledger."""
    signer = Signer.from_file(key_path)
    with Ledger.open(db_path, signer) as ledger:
        events = list(ledger.iter_events(since_seq=since))

    if not events:
        console.print("[dim]No events found.[/dim]")
        return

    # Show last N
    shown = events[-tail:]

    table = Table(title="SkyHerd Attestation Ledger", show_lines=False)
    table.add_column("seq", style="cyan", no_wrap=True)
    table.add_column("ts", style="dim")
    table.add_column("source")
    table.add_column("kind")
    table.add_column("hash[:12]", style="green")

    for ev in shown:
        table.add_row(
            str(ev.seq),
            ev.ts_iso[:19],
            ev.source,
            ev.kind,
            ev.event_hash[:12],
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------


def main() -> None:
    """Console-script entry-point (``skyherd-attest``)."""
    app()
