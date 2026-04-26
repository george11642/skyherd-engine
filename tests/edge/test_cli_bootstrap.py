"""Tests for skyherd-edge CLI — verify-bootstrap + subcommand stubs."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from skyherd.edge.cli import app

runner = CliRunner(mix_stderr=False)
FIXTURES = Path(__file__).parent.parent / "hardware" / "fixtures"


class TestVerifyBootstrap:
    def test_accepts_valid_credentials(self) -> None:
        result = runner.invoke(
            app,
            ["verify-bootstrap", "--credentials-file", str(FIXTURES / "creds_good.json")],
        )
        assert result.exit_code == 0, result.output
        assert "verify-bootstrap OK" in result.output

    def test_reports_missing_mqtt_url(self) -> None:
        result = runner.invoke(
            app,
            [
                "verify-bootstrap",
                "--credentials-file",
                str(FIXTURES / "creds_bad_missing_mqtt.json"),
            ],
        )
        assert result.exit_code == 2
        combined = (result.output or "") + (result.stderr or "")
        assert "mqtt_url" in combined

    def test_reports_malformed_json(self) -> None:
        result = runner.invoke(
            app,
            [
                "verify-bootstrap",
                "--credentials-file",
                str(FIXTURES / "creds_malformed.json"),
            ],
        )
        assert result.exit_code == 2
        combined = (result.output or "") + (result.stderr or "")
        assert "Invalid JSON" in combined

    def test_reports_absent_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "no_such_creds.json"
        result = runner.invoke(app, ["verify-bootstrap", "--credentials-file", str(missing)])
        assert result.exit_code == 2
        combined = (result.output or "") + (result.stderr or "")
        assert "not found" in combined

    def test_rejects_non_object_root(self, tmp_path: Path) -> None:
        arr_creds = tmp_path / "arr.json"
        arr_creds.write_text("[1, 2, 3]")
        result = runner.invoke(app, ["verify-bootstrap", "--credentials-file", str(arr_creds)])
        assert result.exit_code == 2

    def test_accepts_all_optional_fields_empty(self, tmp_path: Path) -> None:
        """Required fields present is enough; optional fields absent is fine."""
        creds = {
            "wifi_ssid": "W",
            "wifi_psk": "P",
            "mqtt_url": "mqtt://x:1",
            "ranch_id": "r",
            "edge_id": "e",
            "trough_ids": "t1",
        }
        p = tmp_path / "minimal.json"
        p.write_text(json.dumps(creds))
        result = runner.invoke(app, ["verify-bootstrap", "--credentials-file", str(p)])
        assert result.exit_code == 0

    def test_empty_required_field_is_missing(self, tmp_path: Path) -> None:
        creds = {
            "wifi_ssid": "",
            "wifi_psk": "P",
            "mqtt_url": "mqtt://x:1",
            "ranch_id": "r",
            "edge_id": "e",
            "trough_ids": "t1",
        }
        p = tmp_path / "empty.json"
        p.write_text(json.dumps(creds))
        result = runner.invoke(app, ["verify-bootstrap", "--credentials-file", str(p)])
        assert result.exit_code == 2
        combined = (result.output or "") + (result.stderr or "")
        assert "wifi_ssid" in combined


class TestCliHelp:
    def test_help_lists_all_subcommands(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in ("run", "smoke", "picam", "coyote", "verify-bootstrap"):
            assert cmd in result.output

    def test_verify_bootstrap_help_shows_flag(self) -> None:
        result = runner.invoke(app, ["verify-bootstrap", "--help"])
        assert result.exit_code == 0
        assert "credentials-file" in result.output
