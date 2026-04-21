"""Ed25519 signing primitives for the SkyHerd attestation chain.

Security contract
-----------------
- Private key material never appears in logs or __repr__.
- PEM serialisation uses standard PKCS8/SubjectPublicKeyInfo formats from
  the *cryptography* library — interoperable and hardware-wallet-friendly.
- ``verify`` is a module-level function so callers that only hold a public
  key PEM can verify without constructing a full Signer.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

log = logging.getLogger(__name__)


class Signer:
    """Wraps an Ed25519 keypair. Private key material is never exposed."""

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        self._private_key = private_key

    @classmethod
    def generate(cls) -> Signer:
        """Generate a fresh Ed25519 keypair."""
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def from_file(cls, path: Path | str) -> Signer:
        """Load a Signer from a PEM-encoded private key file (PKCS8, no password)."""
        path = Path(path)
        pem_bytes = path.read_bytes()
        private_key = serialization.load_pem_private_key(pem_bytes, password=None)
        if not isinstance(private_key, Ed25519PrivateKey):
            raise TypeError(f"Expected Ed25519PrivateKey, got {type(private_key).__name__}")
        return cls(private_key)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path | str) -> None:
        """Serialize the private key as PKCS8 PEM to *path* (mode 0o600)."""
        path = Path(path)
        pem_bytes = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        path.write_bytes(pem_bytes)
        path.chmod(0o600)

    # ------------------------------------------------------------------
    # Public key
    # ------------------------------------------------------------------

    @property
    def public_key_pem(self) -> str:
        """SubjectPublicKeyInfo PEM string (safe to store / transmit)."""
        pub: Ed25519PublicKey = self._private_key.public_key()
        return pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------

    def sign(self, data: bytes) -> bytes:
        """Return a 64-byte Ed25519 signature over *data*."""
        return self._private_key.sign(data)

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover — elides private key
        pub_snippet = self.public_key_pem.splitlines()[1][:12]
        return f"Signer(pubkey={pub_snippet!r}...)"


# ---------------------------------------------------------------------------
# Module-level verify (public-key-only path)
# ---------------------------------------------------------------------------


def verify(pub_pem: str, message: bytes, signature: bytes) -> bool:
    """Verify *signature* over *message* using the PEM-encoded public key.

    Returns ``True`` on success, ``False`` on any cryptographic failure.
    Never raises (unknown PEM formats return ``False``).
    """
    try:
        pub_key = serialization.load_pem_public_key(pub_pem.encode())
        if not isinstance(pub_key, Ed25519PublicKey):
            return False
        pub_key.verify(signature, message)
        return True
    except (InvalidSignature, ValueError, TypeError, Exception):
        return False
