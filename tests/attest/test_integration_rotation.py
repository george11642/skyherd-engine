"""End-to-end integration: rotation + memver pairing + CLI verify.

The "two-receipts-agree" demo beat walked through in code:

  1. Init signer A on disk.
  2. Append 3 events, one of which pairs a memver_id.
  3. Rotate to signer B (old key archived).
  4. Append 3 more events (new key signs, chain continues).
  5. Ledger.verify() walks the whole chain and returns valid=True.
  6. skyherd-verify CLI on the same DB exits 0.

This is the gate: if this test ever goes red, the rotation story is
broken on camera.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.attest.verify_cli import app as verify_app

runner = CliRunner(mix_stderr=False)


def test_rotation_with_memver_pairing_end_to_end(tmp_path: Path) -> None:
    key_path = tmp_path / "attest.key.pem"
    archive = tmp_path / "attest_keys"
    db_path = tmp_path / "attest.db"

    # ---------- Phase A: signer A, 3 events ----------
    signer_a = Signer.generate()
    signer_a.save(key_path)
    pub_a = signer_a.public_key_pem

    ledger_a = Ledger.open(db_path, signer_a)
    ledger_a.append("sensor.water.1", "water.low", {"tank": 1, "psi": 0.3})
    paired_a = ledger_a.append(
        "memory",
        "memver.written",
        {
            "agent": "HerdHealthWatcher",
            "memory_version_id": "memver_phase_a",
            "content_sha256": "sha256:aaa",
            "path": "notes.md",
        },
        memver_id="memver_phase_a",
    )
    ledger_a.append("FenceLineDispatcher", "fence.breach", {"fence": "n"})
    ledger_a._conn.close()

    assert paired_a.memver_id == "memver_phase_a"
    assert '"_memver_id":"memver_phase_a"' in paired_a.payload_json

    # ---------- Rotation ----------
    signer_b = Signer.rotate(
        key_path, archive, timestamp="20260423T220000Z"
    )
    assert signer_b.public_key_pem != pub_a

    archived = archive / "20260423T220000Z.pem"
    assert archived.exists()
    assert Signer.from_file(archived).public_key_pem == pub_a

    # ---------- Phase B: signer B, 3 more events ----------
    ledger_b = Ledger.open(db_path, signer_b)
    ledger_b.append("sensor.fence.3", "fence.ok", {"fence": "e"})
    paired_b = ledger_b.append(
        "memory",
        "memver.written",
        {
            "agent": "CalvingWatch",
            "memory_version_id": "memver_phase_b",
            "content_sha256": "sha256:bbb",
            "path": "calf.md",
        },
        memver_id="memver_phase_b",
    )
    ledger_b.append("GrazingOptimizer", "rotation.proposal", {"paddock": "w"})

    # ---------- Verify ----------
    result = ledger_b.verify()
    assert result.valid, f"chain invalid at seq={result.first_bad_seq}: {result.reason}"
    assert result.total == 6

    # Pre-rotation row keeps pre-rotation pubkey
    events = list(ledger_b.iter_events())
    assert events[0].pubkey == pub_a
    assert events[3].pubkey == signer_b.public_key_pem  # first post-rotation

    # Both memver rows expose their memver_id
    memver_events = [e for e in events if e.memver_id]
    assert len(memver_events) == 2
    assert {e.memver_id for e in memver_events} == {"memver_phase_a", "memver_phase_b"}

    # Canonical-JSON payload binds the memver id for both
    assert '"_memver_id":"memver_phase_a"' in memver_events[0].payload_json
    assert '"_memver_id":"memver_phase_b"' in memver_events[1].payload_json
    ledger_b._conn.close()

    # ---------- skyherd-verify CLI on the same DB ----------
    cli_result = runner.invoke(
        verify_app,
        [
            "verify-chain",
            "--db",
            str(db_path),
            "--key",
            str(key_path),
        ],
    )
    assert cli_result.exit_code == 0, cli_result.output
    assert "PASS" in cli_result.output
    assert "6 event" in cli_result.output


def test_tamper_on_rotated_memver_detected(tmp_path: Path) -> None:
    """Tamper the paired memver_id in the canonical payload of a
    pre-rotation row — the whole chain must fail verification."""
    import sqlite3

    key_path = tmp_path / "k.pem"
    archive = tmp_path / "arch"
    db = tmp_path / "t.db"

    signer_a = Signer.generate()
    signer_a.save(key_path)
    ledger_a = Ledger.open(db, signer_a)
    ledger_a.append(
        "memory", "memver.written",
        {"agent": "A", "memory_version_id": "memver_real"},
        memver_id="memver_real",
    )
    ledger_a._conn.close()

    signer_b = Signer.rotate(key_path, archive, timestamp="20260423T230000Z")
    ledger_b = Ledger.open(db, signer_b)
    ledger_b.append("s", "k", {"v": 1})

    # Tamper — swap the paired memver id in the signed payload.
    conn = sqlite3.connect(str(db))
    conn.execute(
        "UPDATE events SET payload_json = REPLACE(payload_json, 'memver_real', 'memver_fake') WHERE seq = 1"
    )
    conn.commit()
    conn.close()

    # Re-open because we bypassed the ledger's handle.
    ledger_b._conn.close()
    ledger_c = Ledger.open(db, signer_b)
    result = ledger_c.verify()
    assert result.valid is False
    assert result.first_bad_seq == 1
    ledger_c._conn.close()
