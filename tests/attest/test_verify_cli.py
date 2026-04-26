"""Tests for skyherd.attest.verify_cli — the standalone skyherd-verify CLI.

Covers:
- verify-event PASS on clean triple
- verify-event FAIL on wrong sig / wrong pubkey / tampered payload
- verify-chain PASS on clean ledger
- verify-chain FAIL on tampered row
- verify-chain perf gate: 10-event chain under 200ms (p50 of 3 runs)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.attest.verify_cli import app

runner = CliRunner(mix_stderr=False)


@pytest.fixture()
def chain(tmp_path: Path) -> tuple[Path, Path, Signer]:
    """10-event ledger + key on disk. Returns (db_path, key_path, signer)."""
    key_path = tmp_path / "attest.key.pem"
    db_path = tmp_path / "attest.db"
    signer = Signer.generate()
    signer.save(key_path)
    ledger = Ledger.open(db_path, signer)
    for i in range(10):
        ledger.append("sensor.water", "water.reading", {"psi": i, "tank": 1})
    ledger._conn.close()
    return db_path, key_path, signer


# ---------------------------------------------------------------------------
# verify-event
# ---------------------------------------------------------------------------


class TestVerifyEvent:
    def test_verify_event_pass(self, tmp_path: Path) -> None:
        key_path = tmp_path / "key.pem"
        pub_path = tmp_path / "pub.pem"
        signer = Signer.generate()
        signer.save(key_path)
        pub_path.write_text(signer.public_key_pem, encoding="utf-8")

        db_path = tmp_path / "db.sqlite"
        ledger = Ledger.open(db_path, signer)
        event = ledger.append("s", "k", {"v": 42})
        ledger._conn.close()

        event_path = tmp_path / "event.json"
        event_path.write_text(event.model_dump_json(), encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "verify-event",
                str(event_path),
                event.signature,
                str(pub_path),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "PASS" in result.output
        assert "hash match" in result.output
        assert "sig valid" in result.output

    def test_verify_event_fail_wrong_sig(self, tmp_path: Path) -> None:
        key_path = tmp_path / "key.pem"
        pub_path = tmp_path / "pub.pem"
        signer = Signer.generate()
        signer.save(key_path)
        pub_path.write_text(signer.public_key_pem, encoding="utf-8")

        db_path = tmp_path / "db.sqlite"
        ledger = Ledger.open(db_path, signer)
        event = ledger.append("s", "k", {"v": 42})
        ledger._conn.close()

        event_path = tmp_path / "event.json"
        event_path.write_text(event.model_dump_json(), encoding="utf-8")

        # Corrupt the signature by flipping the last byte.
        bad_sig = event.signature[:-2] + ("ff" if event.signature[-2:] != "ff" else "aa")

        result = runner.invoke(
            app,
            ["verify-event", str(event_path), bad_sig, str(pub_path)],
        )
        assert result.exit_code == 2
        combined = (result.output or "") + (result.stderr or "")
        assert "FAIL" in combined

    def test_verify_event_fail_wrong_pubkey(self, tmp_path: Path) -> None:
        key_path = tmp_path / "key.pem"
        signer = Signer.generate()
        signer.save(key_path)

        # Write a DIFFERENT pubkey file
        other = Signer.generate()
        pub_path = tmp_path / "wrong_pub.pem"
        pub_path.write_text(other.public_key_pem, encoding="utf-8")

        db_path = tmp_path / "db.sqlite"
        ledger = Ledger.open(db_path, signer)
        event = ledger.append("s", "k", {"v": 1})
        ledger._conn.close()

        event_path = tmp_path / "event.json"
        event_path.write_text(event.model_dump_json(), encoding="utf-8")

        result = runner.invoke(
            app, ["verify-event", str(event_path), event.signature, str(pub_path)]
        )
        assert result.exit_code == 2

    def test_verify_event_fail_tampered_payload(self, tmp_path: Path) -> None:
        key_path = tmp_path / "key.pem"
        pub_path = tmp_path / "pub.pem"
        signer = Signer.generate()
        signer.save(key_path)
        pub_path.write_text(signer.public_key_pem, encoding="utf-8")

        db_path = tmp_path / "db.sqlite"
        ledger = Ledger.open(db_path, signer)
        event = ledger.append("s", "k", {"v": 1})
        ledger._conn.close()

        # Tamper with payload_json AFTER signing — hash will not match.
        ev_dict = json.loads(event.model_dump_json())
        ev_dict["payload_json"] = '{"v":999}'
        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps(ev_dict), encoding="utf-8")

        result = runner.invoke(
            app, ["verify-event", str(event_path), event.signature, str(pub_path)]
        )
        assert result.exit_code == 2
        combined = (result.output or "") + (result.stderr or "")
        assert "hash mismatch" in combined

    def test_verify_event_fail_missing_fields(self, tmp_path: Path) -> None:
        pub_path = tmp_path / "pub.pem"
        pub_path.write_text(Signer.generate().public_key_pem, encoding="utf-8")
        event_path = tmp_path / "event.json"
        event_path.write_text('{"kind":"k"}', encoding="utf-8")  # missing fields

        result = runner.invoke(
            app,
            ["verify-event", str(event_path), "ab" * 32, str(pub_path)],
        )
        assert result.exit_code == 2
        combined = (result.output or "") + (result.stderr or "")
        assert "missing required fields" in combined

    def test_verify_event_invalid_json(self, tmp_path: Path) -> None:
        pub_path = tmp_path / "pub.pem"
        pub_path.write_text(Signer.generate().public_key_pem, encoding="utf-8")
        event_path = tmp_path / "event.json"
        event_path.write_text("{not json", encoding="utf-8")

        result = runner.invoke(
            app,
            ["verify-event", str(event_path), "ab" * 32, str(pub_path)],
        )
        assert result.exit_code == 2

    def test_verify_event_invalid_sig_hex(self, tmp_path: Path) -> None:
        key_path = tmp_path / "key.pem"
        pub_path = tmp_path / "pub.pem"
        signer = Signer.generate()
        signer.save(key_path)
        pub_path.write_text(signer.public_key_pem, encoding="utf-8")

        db_path = tmp_path / "db.sqlite"
        ledger = Ledger.open(db_path, signer)
        event = ledger.append("s", "k", {"v": 1})
        ledger._conn.close()
        event_path = tmp_path / "event.json"
        event_path.write_text(event.model_dump_json(), encoding="utf-8")

        result = runner.invoke(
            app,
            ["verify-event", str(event_path), "ZZZZnothex", str(pub_path)],
        )
        assert result.exit_code == 2

    def test_verify_event_missing_event_file(self, tmp_path: Path) -> None:
        pub_path = tmp_path / "pub.pem"
        pub_path.write_text(Signer.generate().public_key_pem, encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "verify-event",
                str(tmp_path / "does-not-exist.json"),
                "ab" * 32,
                str(pub_path),
            ],
        )
        assert result.exit_code == 2

    def test_verify_event_missing_pubkey(self, tmp_path: Path) -> None:
        key_path = tmp_path / "key.pem"
        signer = Signer.generate()
        signer.save(key_path)
        db_path = tmp_path / "db.sqlite"
        ledger = Ledger.open(db_path, signer)
        event = ledger.append("s", "k", {"v": 1})
        ledger._conn.close()
        event_path = tmp_path / "event.json"
        event_path.write_text(event.model_dump_json(), encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "verify-event",
                str(event_path),
                event.signature,
                str(tmp_path / "no-pub.pem"),
            ],
        )
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# verify-chain
# ---------------------------------------------------------------------------


class TestVerifyChain:
    def test_verify_chain_pass(self, chain: tuple[Path, Path, Signer]) -> None:
        db_path, key_path, _ = chain
        result = runner.invoke(
            app,
            ["verify-chain", "--db", str(db_path), "--key", str(key_path)],
        )
        assert result.exit_code == 0, result.output
        assert "PASS" in result.output
        assert "10 event" in result.output

    def test_verify_chain_verbose(self, chain: tuple[Path, Path, Signer]) -> None:
        db_path, key_path, _ = chain
        result = runner.invoke(
            app,
            ["verify-chain", "--db", str(db_path), "--key", str(key_path), "--verbose"],
        )
        assert result.exit_code == 0
        # Per-event trace printed
        assert result.output.count("ok seq=") == 10

    def test_verify_chain_fail_tampered(self, chain: tuple[Path, Path, Signer]) -> None:
        import sqlite3

        db_path, key_path, _ = chain

        # Tamper: overwrite payload of seq=5.
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "UPDATE events SET payload_json = ? WHERE seq = 5",
            ('{"tampered":true}',),
        )
        conn.commit()
        conn.close()

        result = runner.invoke(
            app,
            ["verify-chain", "--db", str(db_path), "--key", str(key_path)],
        )
        assert result.exit_code == 2
        combined = (result.output or "") + (result.stderr or "")
        assert "FAIL" in combined

    def test_verify_chain_missing_key_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "verify-chain",
                "--db",
                str(tmp_path / "no.db"),
                "--key",
                str(tmp_path / "no-key.pem"),
            ],
        )
        assert result.exit_code == 2

    def test_verify_chain_under_200ms(self, chain: tuple[Path, Path, Signer]) -> None:
        """ATT-03 perf gate — 10-event chain verify <200ms (p50 of 3 runs)."""
        db_path, key_path, _ = chain
        durations: list[float] = []
        for _ in range(3):
            t0 = time.perf_counter()
            result = runner.invoke(
                app,
                ["verify-chain", "--db", str(db_path), "--key", str(key_path)],
            )
            durations.append((time.perf_counter() - t0) * 1000.0)
            assert result.exit_code == 0

        durations.sort()
        p50 = durations[1]
        assert p50 < 200.0, f"verify-chain p50={p50:.1f}ms exceeded 200ms budget"


# ---------------------------------------------------------------------------
# Module entry point
# ---------------------------------------------------------------------------


class TestEntryPoint:
    def test_module_has_main(self) -> None:
        from skyherd.attest import verify_cli as vc

        assert callable(vc.main)

    def test_app_help_lists_both_subcommands(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "verify-event" in result.output
        assert "verify-chain" in result.output
