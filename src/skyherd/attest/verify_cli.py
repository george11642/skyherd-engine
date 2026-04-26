"""Standalone ``skyherd-verify`` CLI — single-purpose chain verification.

Separate from ``skyherd-attest`` to keep the judge-facing "can I audit what
the AI did?" surface tiny and self-contained.

Sub-commands
------------
verify-event  — verify one (event.json, sig.hex, pubkey.pem) triple.
verify-chain  — walk a SQLite ledger chain and report pass/fail.

Performance target: <200ms for a 10-event chain on a modern laptop.

Console script: ``skyherd-verify`` (registered in pyproject.toml).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

import typer
from rich.console import Console

from skyherd.attest.ledger import GENESIS_PREV_HASH, Ledger
from skyherd.attest.signer import Signer
from skyherd.attest.signer import verify as _sig_verify

app = typer.Typer(
    name="skyherd-verify",
    help="Standalone attestation chain verifier for SkyHerd ledgers.",
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Internal helpers — mirror of ledger.py hashing (keep in sync intentionally)
# ---------------------------------------------------------------------------


def _compute_event_hash(
    prev_hash: str,
    canonical_payload: str,
    ts_iso: str,
    source: str,
    kind: str,
) -> bytes:
    h = hashlib.blake2b(digest_size=32)
    for field in (prev_hash, canonical_payload, ts_iso, source, kind):
        h.update(field.encode())
    return h.digest()


def _eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


# ---------------------------------------------------------------------------
# verify-event
# ---------------------------------------------------------------------------


@app.command("verify-event")
def verify_event(
    event_path: Path = typer.Argument(..., help="Path to event JSON file."),
    sig_hex: str = typer.Argument(..., help="Ed25519 signature, hex-encoded."),
    pubkey_path: Path = typer.Argument(..., help="Path to SubjectPublicKeyInfo PEM."),
) -> None:
    """Verify a single attestation event triple.

    The event JSON must include the fields produced by Ledger.append:
    ``ts_iso, source, kind, payload_json, prev_hash, event_hash``. This
    command re-computes the event_hash from the raw fields, compares it in
    constant time, and verifies the Ed25519 signature over the raw hash.
    """
    t0 = time.perf_counter()
    try:
        event_text = event_path.read_text(encoding="utf-8")
    except OSError as exc:
        err_console.print(f"[bold red]FAIL[/bold red] cannot read event file: {exc}")
        raise typer.Exit(2) from exc

    try:
        event = json.loads(event_text)
    except json.JSONDecodeError as exc:
        err_console.print(f"[bold red]FAIL[/bold red] invalid JSON: {exc}")
        raise typer.Exit(2) from exc

    required = ("ts_iso", "source", "kind", "payload_json", "prev_hash", "event_hash")
    missing = [k for k in required if k not in event]
    if missing:
        err_console.print(f"[bold red]FAIL[/bold red] event missing required fields: {missing}")
        raise typer.Exit(2)

    try:
        pub_pem = pubkey_path.read_text(encoding="utf-8")
    except OSError as exc:
        err_console.print(f"[bold red]FAIL[/bold red] cannot read pubkey: {exc}")
        raise typer.Exit(2) from exc

    # 1. Re-compute hash
    raw_hash = _compute_event_hash(
        event["prev_hash"],
        event["payload_json"],
        event["ts_iso"],
        event["source"],
        event["kind"],
    )
    computed_hex = raw_hash.hex()

    if not _eq(computed_hex, event["event_hash"]):
        err_console.print(
            f"[bold red]FAIL[/bold red] hash mismatch\n"
            f"  expected: {event['event_hash']}\n"
            f"  computed: {computed_hex}"
        )
        raise typer.Exit(2)

    # 2. Verify signature
    try:
        raw_sig = bytes.fromhex(sig_hex)
    except ValueError as exc:
        err_console.print(f"[bold red]FAIL[/bold red] invalid signature hex: {exc}")
        raise typer.Exit(2) from exc

    if not _sig_verify(pub_pem, raw_hash, raw_sig):
        err_console.print("[bold red]FAIL[/bold red] signature verification failed")
        raise typer.Exit(2)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    console.print(
        f"[bold green]PASS[/bold green] event {event['event_hash'][:16]}... "
        f"(hash match, sig valid, {elapsed_ms:.1f}ms)"
    )


# ---------------------------------------------------------------------------
# verify-chain
# ---------------------------------------------------------------------------


@app.command("verify-chain")
def verify_chain(
    db_path: Path = typer.Option(Path("attest.db"), "--db", help="Path to SQLite ledger."),
    key_path: Path = typer.Option(
        Path("attest.key.pem"),
        "--key",
        help="Path to private key PEM (for Ledger open; pubkey-per-row is used for verify).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Per-event trace."),
) -> None:
    """Walk the ledger chain and verify every hash + signature.

    Exit code 0 on clean chain, 2 on any failure.
    """
    t0 = time.perf_counter()
    try:
        signer = Signer.from_file(key_path)
    except (FileNotFoundError, OSError) as exc:
        err_console.print(f"[bold red]FAIL[/bold red] cannot load key: {exc}")
        raise typer.Exit(2) from exc

    with Ledger.open(db_path, signer) as ledger:
        total = 0
        expected_prev = GENESIS_PREV_HASH
        for event in ledger.iter_events():
            total += 1
            if not _eq(event.prev_hash, expected_prev):
                err_console.print(
                    f"[bold red]FAIL[/bold red] prev_hash mismatch at seq={event.seq}"
                )
                raise typer.Exit(2)

            raw_hash = _compute_event_hash(
                event.prev_hash,
                event.payload_json,
                event.ts_iso,
                event.source,
                event.kind,
            )
            if not _eq(raw_hash.hex(), event.event_hash):
                err_console.print(f"[bold red]FAIL[/bold red] hash mismatch at seq={event.seq}")
                raise typer.Exit(2)

            try:
                raw_sig = bytes.fromhex(event.signature)
            except ValueError:
                err_console.print(f"[bold red]FAIL[/bold red] invalid sig hex at seq={event.seq}")
                raise typer.Exit(2) from None

            if not _sig_verify(event.pubkey, raw_hash, raw_sig):
                err_console.print(
                    f"[bold red]FAIL[/bold red] signature invalid at seq={event.seq} "
                    f"(pubkey may have been rotated and archived key lost)"
                )
                raise typer.Exit(2)

            if verbose:
                console.print(f"[green]ok[/green] seq={event.seq} hash={event.event_hash[:12]}...")

            expected_prev = event.event_hash

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    console.print(
        f"[bold green]PASS[/bold green] chain valid — {total} event(s) "
        f"verified in {elapsed_ms:.1f}ms"
    )


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover — delegates to typer
    app()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(0)
