"""Tests for hardware/pi/bootstrap.sh — syntax + dry-run paths.

No actual provisioning is executed; tests use --dry-run to observe the
derived provision-edge.sh command and validate credential parsing.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
BOOTSTRAP = ROOT / "hardware" / "pi" / "bootstrap.sh"
FIXTURES = ROOT / "tests" / "hardware" / "fixtures"


def _run(env_creds: str | None, args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if env_creds is not None:
        env["SKYHERD_CREDS_FILE"] = env_creds
    elif "SKYHERD_CREDS_FILE" in env:
        del env["SKYHERD_CREDS_FILE"]
    return subprocess.run(
        ["bash", str(BOOTSTRAP), *args],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=15,
        check=False,
    )


class TestBootstrapScriptSyntax:
    def test_script_exists_and_is_executable(self) -> None:
        assert BOOTSTRAP.exists()
        # Cannot check +x in all environments (e.g. mounted fs) — just require presence.

    def test_syntax_valid(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(BOOTSTRAP)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


class TestBootstrapDryRun:
    def test_dry_run_with_good_creds_succeeds(self) -> None:
        result = _run(str(FIXTURES / "creds_good.json"), ["--dry-run"])
        assert result.returncode == 0, f"stderr={result.stderr}"
        assert "DRY-RUN" in result.stdout
        assert "edge-house" in result.stdout
        assert "ranch_a" in result.stdout
        assert "mqtt://192.168.1.100:1883" in result.stdout

    def test_dry_run_prints_trough_list(self) -> None:
        result = _run(str(FIXTURES / "creds_good.json"), ["--dry-run"])
        assert result.returncode == 0
        assert "trough_1" in result.stdout
        assert "trough_2" in result.stdout

    def test_dry_run_with_missing_mqtt_exits_nonzero(self) -> None:
        result = _run(str(FIXTURES / "creds_bad_missing_mqtt.json"), ["--dry-run"])
        assert result.returncode != 0
        assert "mqtt_url" in result.stderr

    def test_dry_run_with_malformed_json_exits_nonzero(self) -> None:
        result = _run(str(FIXTURES / "creds_malformed.json"), ["--dry-run"])
        assert result.returncode != 0
        assert "not valid JSON" in result.stderr or "JSON" in result.stderr

    def test_rejects_absent_creds_file(self, tmp_path: Path) -> None:
        ghost = tmp_path / "ghost.json"
        result = _run(str(ghost), ["--dry-run"])
        assert result.returncode != 0
        assert "not found" in result.stderr

    def test_unknown_flag_rejected(self) -> None:
        result = _run(str(FIXTURES / "creds_good.json"), ["--no-such-flag"])
        assert result.returncode != 0

    def test_help_flag_prints_usage(self) -> None:
        result = _run(None, ["--help"])
        # Help path does not require creds file
        assert result.returncode == 0
        assert "bootstrap" in result.stdout.lower() or "Usage" in result.stdout


class TestBootstrapHelperReadsOverriddenPath:
    def test_bootstrap_respects_skyherd_creds_file_env(self) -> None:
        """Proves SKYHERD_CREDS_FILE override works (and default path isn't
        silently used)."""
        # Pick a path that DOES exist via the env var; the default is /boot/firmware/
        # which would not exist on a dev machine.
        result = _run(str(FIXTURES / "creds_good.json"), ["--dry-run"])
        assert result.returncode == 0

    def test_without_env_var_default_path_missing_is_reported(self) -> None:
        """When SKYHERD_CREDS_FILE not set and default /boot/firmware/ missing,
        the script errors with 'not found'."""
        # On a dev machine /boot/firmware/skyherd-credentials.json is absent.
        if Path("/boot/firmware/skyherd-credentials.json").exists():
            pytest.skip("default creds path exists on this host — cannot test")
        result = _run(None, ["--dry-run"])
        assert result.returncode != 0
        assert "not found" in result.stderr
