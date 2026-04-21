"""SkyHerd Attestation Chain.

Public API
----------
``Ledger``       — append-only, hash-chained, Ed25519-signed event log.
``Signer``       — Ed25519 keypair wrapper (generate / save / load / sign).
``Event``        — Pydantic model for one ledger row.
``VerifyResult`` — Result dataclass returned by ``Ledger.verify()``.
``verify``       — Module-level function: verify a signature with only a PEM.
"""

from skyherd.attest.ledger import Event, Ledger, VerifyResult
from skyherd.attest.signer import Signer, verify

__all__ = [
    "Event",
    "Ledger",
    "Signer",
    "VerifyResult",
    "verify",
]
