"""SQLite-backed Merkle-chained event ledger for the SkyHerd attestation chain.

Design
------
- Each row carries a ``prev_hash`` forming a hash-linked chain (Merkle chain).
- Event hash = blake2b(prev_hash_hex || canonical_json(payload) || ts_iso
                       || source || kind)  — all UTF-8 encoded and
  concatenated in a fixed order before hashing.
- Signatures are Ed25519 over the raw event_hash bytes (not hex).
- Hash comparisons use ``hmac.compare_digest`` for constant-time equality.
- WAL + synchronous=NORMAL gives crash-safe durability without fsync on
  every write.

Schema is CREATE TABLE IF NOT EXISTS — safe to call on an existing DB.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from skyherd.attest.signer import Signer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GENESIS_PREV_HASH = "GENESIS"

_DDL = """
CREATE TABLE IF NOT EXISTS events(
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_iso       TEXT    NOT NULL,
    source       TEXT    NOT NULL,
    kind         TEXT    NOT NULL,
    payload_json TEXT    NOT NULL,
    prev_hash    TEXT    NOT NULL,
    event_hash   TEXT    NOT NULL UNIQUE,
    signature    TEXT    NOT NULL,
    pubkey       TEXT    NOT NULL
);
"""

# Default wall-clock ts_provider — replaced with world.clock.sim_time_s in sim
_WALL_CLOCK_TS: Callable[[], float] = time.time

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class Event(BaseModel):
    """Immutable mirror of one ledger row."""

    seq: int
    ts_iso: str
    source: str
    kind: str
    payload_json: str
    prev_hash: str
    event_hash: str
    signature: str  # hex
    pubkey: str  # PEM


class VerifyResult(BaseModel):
    """Result of a full ledger integrity check."""

    valid: bool
    total: int
    first_bad_seq: int | None = None
    reason: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _canonical_json(payload: dict) -> str:
    """Deterministic JSON — sorted keys, compact separators, no NaN/Inf."""
    # json.dumps raises ValueError for NaN / Inf floats by default when
    # allow_nan=False (Python default is True — we flip it).
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _compute_hash(
    prev_hash: str,
    canonical_payload: str,
    ts_iso: str,
    source: str,
    kind: str,
) -> bytes:
    """Return raw blake2b-256 digest over the fixed-order concatenation."""
    h = hashlib.blake2b(digest_size=32)
    for field in (prev_hash, canonical_payload, ts_iso, source, kind):
        h.update(field.encode())
    return h.digest()


def _constant_eq(a: str, b: str) -> bool:
    """Constant-time string comparison (wraps hmac.compare_digest)."""
    return hmac.compare_digest(a.encode(), b.encode())


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


class Ledger:
    """Append-only, hash-chained, Ed25519-signed event log."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        signer: Signer,
        ts_provider: Callable[[], float] | None = None,
    ) -> None:
        self._conn = conn
        self._signer = signer
        self._ts: Callable[[], float] = ts_provider if ts_provider is not None else _WALL_CLOCK_TS

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def open(
        cls,
        path: Path | str,
        signer: Signer,
        ts_provider: Callable[[], float] | None = None,
    ) -> Ledger:
        """Open (or create) the ledger at *path*."""
        path = Path(path)
        conn = sqlite3.connect(str(path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(_DDL)
        conn.commit()
        return cls(conn, signer, ts_provider=ts_provider)

    # ------------------------------------------------------------------
    # Context manager (optional but handy in tests)
    # ------------------------------------------------------------------

    def __enter__(self) -> Ledger:
        return self

    def __exit__(self, *_) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def append(self, source: str, kind: str, payload: dict) -> Event:
        """Append one event atomically; returns the committed Event."""
        ts_iso = datetime.fromtimestamp(self._ts(), tz=UTC).isoformat()
        canonical_payload = _canonical_json(payload)
        prev_hash = self._last_hash()

        raw_hash = _compute_hash(prev_hash, canonical_payload, ts_iso, source, kind)
        event_hash_hex = raw_hash.hex()

        raw_sig = self._signer.sign(raw_hash)
        sig_hex = raw_sig.hex()

        pubkey = self._signer.public_key_pem

        with self._transaction():
            cur = self._conn.execute(
                """
                INSERT INTO events
                    (ts_iso, source, kind, payload_json,
                     prev_hash, event_hash, signature, pubkey)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts_iso,
                    source,
                    kind,
                    canonical_payload,
                    prev_hash,
                    event_hash_hex,
                    sig_hex,
                    pubkey,
                ),
            )
            seq = cur.lastrowid or 0

        return Event(
            seq=seq,
            ts_iso=ts_iso,
            source=source,
            kind=kind,
            payload_json=canonical_payload,
            prev_hash=prev_hash,
            event_hash=event_hash_hex,
            signature=sig_hex,
            pubkey=pubkey,
        )

    # ------------------------------------------------------------------
    # Read paths
    # ------------------------------------------------------------------

    def iter_events(self, since_seq: int = 0) -> Iterator[Event]:
        """Yield all events with seq > since_seq in insertion order."""
        cur = self._conn.execute(
            """
            SELECT seq, ts_iso, source, kind, payload_json,
                   prev_hash, event_hash, signature, pubkey
            FROM events
            WHERE seq > ?
            ORDER BY seq
            """,
            (since_seq,),
        )
        for row in cur:
            yield Event(
                seq=row[0],
                ts_iso=row[1],
                source=row[2],
                kind=row[3],
                payload_json=row[4],
                prev_hash=row[5],
                event_hash=row[6],
                signature=row[7],
                pubkey=row[8],
            )

    def export_jsonl(self, path: Path | str) -> None:
        """Write all events as newline-delimited JSON to *path*."""
        path = Path(path)
        with path.open("w", encoding="utf-8") as fh:
            for event in self.iter_events():
                fh.write(event.model_dump_json() + "\n")

    # ------------------------------------------------------------------
    # Verify
    # ------------------------------------------------------------------

    def verify(self) -> VerifyResult:
        """Walk the entire chain and re-verify every hash and signature."""
        from skyherd.attest.signer import verify as sig_verify

        total = 0
        expected_prev = GENESIS_PREV_HASH

        for event in self.iter_events():
            total += 1

            # 1. Prev-hash linkage
            if not _constant_eq(event.prev_hash, expected_prev):
                return VerifyResult(
                    valid=False,
                    total=total,
                    first_bad_seq=event.seq,
                    reason=(
                        f"prev_hash mismatch at seq={event.seq}: "
                        f"expected {expected_prev!r}, got {event.prev_hash!r}"
                    ),
                )

            # 2. Re-compute event hash
            raw_hash = _compute_hash(
                event.prev_hash,
                event.payload_json,
                event.ts_iso,
                event.source,
                event.kind,
            )
            computed_hex = raw_hash.hex()

            if not _constant_eq(event.event_hash, computed_hex):
                return VerifyResult(
                    valid=False,
                    total=total,
                    first_bad_seq=event.seq,
                    reason=f"hash mismatch at seq={event.seq}",
                )

            # 3. Signature check
            try:
                raw_sig = bytes.fromhex(event.signature)
            except ValueError:
                return VerifyResult(
                    valid=False,
                    total=total,
                    first_bad_seq=event.seq,
                    reason=f"invalid signature hex at seq={event.seq}",
                )

            if not sig_verify(event.pubkey, raw_hash, raw_sig):
                return VerifyResult(
                    valid=False,
                    total=total,
                    first_bad_seq=event.seq,
                    reason=f"signature verification failed at seq={event.seq}",
                )

            expected_prev = event.event_hash

        return VerifyResult(valid=True, total=total)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _last_hash(self) -> str:
        """Return the event_hash of the most-recent row, or GENESIS."""
        row = self._conn.execute(
            "SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else GENESIS_PREV_HASH

    @contextmanager
    def _transaction(self):
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
