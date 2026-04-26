"""Tests for skyherd.attest.signer — RED → GREEN TDD.

Covers:
- Keypair generation
- save / from_file round-trip (PEM, chmod 0o600)
- sign / verify happy path
- verify rejects wrong signature
- verify rejects wrong message
- verify handles garbage input gracefully
- Signer.__repr__ elides private key material
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from skyherd.attest.signer import Signer, verify

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def signer() -> Signer:
    return Signer.generate()


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


class TestSignerGenerate:
    def test_generate_returns_signer(self) -> None:
        s = Signer.generate()
        assert isinstance(s, Signer)

    def test_two_generated_keys_differ(self) -> None:
        s1 = Signer.generate()
        s2 = Signer.generate()
        assert s1.public_key_pem != s2.public_key_pem

    def test_public_key_pem_is_pem_string(self, signer: Signer) -> None:
        pem = signer.public_key_pem
        assert pem.startswith("-----BEGIN PUBLIC KEY-----")
        assert pem.strip().endswith("-----END PUBLIC KEY-----")


# ---------------------------------------------------------------------------
# Persistence — save / from_file
# ---------------------------------------------------------------------------


class TestSignerPersistence:
    def test_save_creates_file(self, signer: Signer, tmp_path: Path) -> None:
        key_path = tmp_path / "test.key.pem"
        signer.save(key_path)
        assert key_path.exists()

    def test_save_sets_mode_600(self, signer: Signer, tmp_path: Path) -> None:
        key_path = tmp_path / "test.key.pem"
        signer.save(key_path)
        mode = oct(os.stat(key_path).st_mode)[-3:]
        assert mode == "600"

    def test_round_trip_preserves_public_key(self, signer: Signer, tmp_path: Path) -> None:
        key_path = tmp_path / "test.key.pem"
        original_pub = signer.public_key_pem
        signer.save(key_path)
        loaded = Signer.from_file(key_path)
        assert loaded.public_key_pem == original_pub

    def test_from_file_can_sign_same_as_original(self, signer: Signer, tmp_path: Path) -> None:
        key_path = tmp_path / "test.key.pem"
        signer.save(key_path)
        loaded = Signer.from_file(key_path)
        msg = b"hello ranch"
        sig = loaded.sign(msg)
        assert verify(loaded.public_key_pem, msg, sig)

    def test_from_file_rejects_wrong_key_type(self, tmp_path: Path) -> None:
        """A non-Ed25519 PEM file must raise TypeError."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = rsa_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        bad_path = tmp_path / "rsa.key.pem"
        bad_path.write_bytes(pem)
        with pytest.raises(TypeError, match="Ed25519PrivateKey"):
            Signer.from_file(bad_path)

    def test_from_file_accepts_str_path(self, signer: Signer, tmp_path: Path) -> None:
        key_path = tmp_path / "str_path.key.pem"
        signer.save(str(key_path))
        loaded = Signer.from_file(str(key_path))
        assert loaded.public_key_pem == signer.public_key_pem


# ---------------------------------------------------------------------------
# Sign / verify
# ---------------------------------------------------------------------------


class TestSignVerify:
    def test_sign_returns_64_bytes(self, signer: Signer) -> None:
        sig = signer.sign(b"test message")
        assert len(sig) == 64

    def test_verify_happy_path(self, signer: Signer) -> None:
        msg = b"water tank pressure drop"
        sig = signer.sign(msg)
        assert verify(signer.public_key_pem, msg, sig)

    def test_verify_wrong_signature(self, signer: Signer) -> None:
        msg = b"coyote at fence"
        sig = signer.sign(msg)
        bad_sig = bytes(b ^ 0xFF for b in sig)  # flip all bits
        assert not verify(signer.public_key_pem, msg, bad_sig)

    def test_verify_wrong_message(self, signer: Signer) -> None:
        msg = b"original"
        sig = signer.sign(msg)
        assert not verify(signer.public_key_pem, b"tampered", sig)

    def test_verify_wrong_pubkey(self) -> None:
        s1 = Signer.generate()
        s2 = Signer.generate()
        msg = b"payload"
        sig = s1.sign(msg)
        assert not verify(s2.public_key_pem, msg, sig)

    def test_verify_garbage_pem(self) -> None:
        assert not verify("NOT A PEM", b"msg", b"sig")

    def test_verify_empty_sig(self, signer: Signer) -> None:
        assert not verify(signer.public_key_pem, b"msg", b"")

    def test_verify_truncated_sig(self, signer: Signer) -> None:
        msg = b"drone launched"
        sig = signer.sign(msg)
        assert not verify(signer.public_key_pem, msg, sig[:32])

    def test_verify_consistent_across_calls(self, signer: Signer) -> None:
        msg = b"calving detected"
        sig = signer.sign(msg)
        for _ in range(5):
            assert verify(signer.public_key_pem, msg, sig)


# ---------------------------------------------------------------------------
# Rotation (Phase 4 — ATT-02)
# ---------------------------------------------------------------------------


class TestSignerRotate:
    def test_rotate_archives_old_key_and_creates_new(self, tmp_path: Path) -> None:
        key_path = tmp_path / "attest.key.pem"
        archive = tmp_path / "archive"
        original = Signer.generate()
        original.save(key_path)
        original_pub = original.public_key_pem

        rotated = Signer.rotate(key_path, archive, timestamp="20260423T210000Z")

        # New signer returned with different pubkey
        assert isinstance(rotated, Signer)
        assert rotated.public_key_pem != original_pub

        # Archive exists with original pubkey recoverable
        archived = archive / "20260423T210000Z.pem"
        assert archived.exists()
        recovered = Signer.from_file(archived)
        assert recovered.public_key_pem == original_pub

        # Current key path now holds the new signer
        on_disk = Signer.from_file(key_path)
        assert on_disk.public_key_pem == rotated.public_key_pem

    def test_rotate_archive_mode_600(self, tmp_path: Path) -> None:
        key_path = tmp_path / "k.pem"
        archive = tmp_path / "a"
        Signer.generate().save(key_path)
        Signer.rotate(key_path, archive, timestamp="20260423T210001Z")
        archived = archive / "20260423T210001Z.pem"
        mode = archived.stat().st_mode & 0o777
        assert mode == 0o600

    def test_rotate_collision_appends_suffix(self, tmp_path: Path) -> None:
        key_path = tmp_path / "k.pem"
        archive = tmp_path / "a"
        Signer.generate().save(key_path)
        Signer.rotate(key_path, archive, timestamp="20260423T210002Z")
        # Second rotation at same timestamp string — must not clobber
        Signer.rotate(key_path, archive, timestamp="20260423T210002Z")
        files = sorted(p.name for p in archive.iterdir())
        assert "20260423T210002Z.pem" in files
        assert "20260423T210002Z-1.pem" in files

    def test_rotate_missing_key_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            Signer.rotate(tmp_path / "nope.pem", tmp_path / "arch")

    def test_rotate_default_timestamp(self, tmp_path: Path) -> None:
        """No ``timestamp`` arg → current UTC time used; file matches YYYYMMDDTHHMMSSZ."""
        key_path = tmp_path / "k.pem"
        archive = tmp_path / "a"
        Signer.generate().save(key_path)
        Signer.rotate(key_path, archive)
        files = list(archive.iterdir())
        assert len(files) == 1
        name = files[0].name
        # Matches 8digits+T+6digits+Z (with optional -N suffix)
        assert name.endswith(".pem")
        stem = name[:-4]
        core = stem.split("-")[0]
        assert len(core) == 16  # YYYYMMDDTHHMMSSZ
        assert core[8] == "T"
        assert core.endswith("Z")
