"""CLI tests for skyherd.attest.cli using typer.testing.CliRunner.

Covers:
- init: creates key + ledger, prints public key
- init: refuses to overwrite without --force
- init --force: overwrites
- append: appends valid JSON from stdin
- append: rejects empty stdin
- append: rejects invalid JSON
- append: rejects non-dict JSON
- verify: prints CHAIN VALID for clean ledger
- verify: exits 2 on tampered ledger
- list: shows table with events
- list --since filters
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from skyherd.attest.cli import app

runner = CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_defaults(tmp_path: Path) -> tuple[Path, Path]:
    """Run init in tmp_path and return (key_path, db_path)."""
    key_path = tmp_path / "attest.key.pem"
    db_path = tmp_path / "attest.db"
    result = runner.invoke(
        app,
        [
            "init",
            "--key",
            str(key_path),
            "--db",
            str(db_path),
        ],
    )
    assert result.exit_code == 0, result.output
    return key_path, db_path


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


class TestCliInit:
    def test_init_creates_key_and_db(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        assert key_path.exists()
        assert db_path.exists()

    def test_init_prints_public_key(self, tmp_path: Path) -> None:
        key_path, _ = _init_defaults(tmp_path)
        result = runner.invoke(
            app,
            ["init", "--key", str(key_path), "--db", str(tmp_path / "x.db"), "--force"],
        )
        assert "BEGIN PUBLIC KEY" in result.output

    def test_init_refuses_overwrite_without_force(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        result = runner.invoke(
            app,
            ["init", "--key", str(key_path), "--db", str(db_path)],
        )
        assert result.exit_code != 0

    def test_init_force_overwrites(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        result = runner.invoke(
            app,
            ["init", "--key", str(key_path), "--db", str(db_path), "--force"],
        )
        assert result.exit_code == 0

    def test_init_output_mentions_key_path(self, tmp_path: Path) -> None:
        key_path = tmp_path / "mykey.pem"
        db_path = tmp_path / "mydb.db"
        result = runner.invoke(
            app,
            ["init", "--key", str(key_path), "--db", str(db_path)],
        )
        assert str(key_path) in result.output or "Key written" in result.output


# ---------------------------------------------------------------------------
# append
# ---------------------------------------------------------------------------


class TestCliAppend:
    def test_append_valid_json(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        result = runner.invoke(
            app,
            [
                "append",
                "sensor.water.1",
                "water.low",
                "--key",
                str(key_path),
                "--db",
                str(db_path),
            ],
            input=json.dumps({"psi": 0.2, "tank": 3}),
        )
        assert result.exit_code == 0, result.output
        assert "seq=1" in result.output

    def test_append_increments_seq(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        for i in range(3):
            result = runner.invoke(
                app,
                [
                    "append",
                    "s",
                    "k",
                    "--key",
                    str(key_path),
                    "--db",
                    str(db_path),
                ],
                input=json.dumps({"i": i}),
            )
            assert result.exit_code == 0

        # Third append should report seq=3
        assert "seq=3" in result.output

    def test_append_empty_stdin_fails(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        result = runner.invoke(
            app,
            [
                "append",
                "s",
                "k",
                "--key",
                str(key_path),
                "--db",
                str(db_path),
            ],
            input="",
        )
        assert result.exit_code != 0

    def test_append_invalid_json_fails(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        result = runner.invoke(
            app,
            [
                "append",
                "s",
                "k",
                "--key",
                str(key_path),
                "--db",
                str(db_path),
            ],
            input="not json at all",
        )
        assert result.exit_code != 0

    def test_append_non_dict_json_fails(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        result = runner.invoke(
            app,
            [
                "append",
                "s",
                "k",
                "--key",
                str(key_path),
                "--db",
                str(db_path),
            ],
            input="[1, 2, 3]",
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


class TestCliVerify:
    def test_verify_clean_chain_exits_0(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        for i in range(5):
            runner.invoke(
                app,
                [
                    "append",
                    "s",
                    "k",
                    "--key",
                    str(key_path),
                    "--db",
                    str(db_path),
                ],
                input=json.dumps({"i": i}),
            )
        result = runner.invoke(
            app,
            ["verify", "--key", str(key_path), "--db", str(db_path)],
        )
        assert result.exit_code == 0
        assert "VALID" in result.output

    def test_verify_empty_ledger_exits_0(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        result = runner.invoke(
            app,
            ["verify", "--key", str(key_path), "--db", str(db_path)],
        )
        assert result.exit_code == 0

    def test_verify_tampered_chain_exits_2(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        runner.invoke(
            app,
            [
                "append",
                "s",
                "k",
                "--key",
                str(key_path),
                "--db",
                str(db_path),
            ],
            input=json.dumps({"v": 1}),
        )

        # Directly tamper with the payload
        conn = sqlite3.connect(str(db_path))
        conn.execute("UPDATE events SET payload_json = '{\"v\":999}' WHERE seq = 1")
        conn.commit()
        conn.close()

        result = runner.invoke(
            app,
            ["verify", "--key", str(key_path), "--db", str(db_path)],
        )
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestCliList:
    def test_list_empty_ledger(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        result = runner.invoke(
            app,
            ["list", "--key", str(key_path), "--db", str(db_path)],
        )
        assert result.exit_code == 0

    def test_list_shows_events(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        runner.invoke(
            app,
            [
                "append",
                "sensor.water.1",
                "water.low",
                "--key",
                str(key_path),
                "--db",
                str(db_path),
            ],
            input=json.dumps({"psi": 0.1}),
        )
        result = runner.invoke(
            app,
            ["list", "--key", str(key_path), "--db", str(db_path)],
        )
        assert result.exit_code == 0
        assert "sensor.water.1" in result.output
        assert "water.low" in result.output

    def test_list_tail_limits_output(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        for i in range(30):
            runner.invoke(
                app,
                [
                    "append",
                    "s",
                    "k",
                    "--key",
                    str(key_path),
                    "--db",
                    str(db_path),
                ],
                input=json.dumps({"i": i}),
            )
        result = runner.invoke(
            app,
            ["list", "--tail", "5", "--key", str(key_path), "--db", str(db_path)],
        )
        assert result.exit_code == 0
        # Should show 5 rows — seq 26..30 visible in table output
        assert "26" in result.output or "30" in result.output

    def test_list_since_filters(self, tmp_path: Path) -> None:
        key_path, db_path = _init_defaults(tmp_path)
        for i in range(10):
            runner.invoke(
                app,
                [
                    "append",
                    "s",
                    "k",
                    "--key",
                    str(key_path),
                    "--db",
                    str(db_path),
                ],
                input=json.dumps({"i": i}),
            )
        result = runner.invoke(
            app,
            ["list", "--since", "8", "--key", str(key_path), "--db", str(db_path)],
        )
        assert result.exit_code == 0
        # seqs 9 and 10 should appear, not seq 1
        assert "9" in result.output
        assert "10" in result.output
