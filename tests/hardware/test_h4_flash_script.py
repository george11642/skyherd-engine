"""Tests for ``hardware/collar/flash.sh`` — pre-flight + usage contract.

No real flashing happens; we only exercise the help + missing-tool branches.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FLASH_SH = _REPO_ROOT / "hardware" / "collar" / "flash.sh"


def test_flash_script_exists() -> None:
    assert _FLASH_SH.is_file(), f"flash.sh missing at {_FLASH_SH}"


def test_flash_script_is_executable() -> None:
    assert os.access(_FLASH_SH, os.X_OK), f"flash.sh at {_FLASH_SH} is not executable"


def test_flash_script_has_bash_shebang() -> None:
    first_line = _FLASH_SH.read_text().splitlines()[0]
    assert first_line.startswith("#!") and "bash" in first_line, first_line


def test_flash_script_syntax_valid() -> None:
    """`bash -n` catches parse errors without running the script."""
    result = subprocess.run(
        ["bash", "-n", str(_FLASH_SH)], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"bash -n failed: {result.stderr}"


def test_flash_script_help_exits_zero() -> None:
    result = subprocess.run([str(_FLASH_SH), "--help"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert "Usage" in result.stdout
    assert "--env" in result.stdout


def test_flash_script_short_help_flag_also_works() -> None:
    result = subprocess.run([str(_FLASH_SH), "-h"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0


def test_flash_script_rejects_unknown_arg() -> None:
    result = subprocess.run([str(_FLASH_SH), "--nope"], capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert "Unknown" in result.stderr or "usage" in result.stderr.lower()


def test_flash_script_detects_missing_pio(tmp_path: Path) -> None:
    """When PATH contains bash/coreutils but no `pio`, script exits 2."""
    # Symlink only bash + coreutils so /usr/bin/env can find bash, but pio can't.
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    for tool in ("bash", "env", "cat", "cp", "timeout", "command", "dirname", "pwd"):
        src = Path(f"/usr/bin/{tool}")
        if src.exists():
            try:
                (stub_bin / tool).symlink_to(src)
            except FileExistsError:
                pass
        alt = Path(f"/bin/{tool}")
        if alt.exists() and not (stub_bin / tool).exists():
            try:
                (stub_bin / tool).symlink_to(alt)
            except FileExistsError:
                pass
    env = {
        "PATH": str(stub_bin),
        "HOME": os.environ.get("HOME", ""),
    }
    result = subprocess.run(
        ["bash", str(_FLASH_SH)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2, f"expected 2, got {result.returncode}; stderr={result.stderr}"
    assert "pio" in result.stderr.lower()
    assert "platformio" in result.stderr.lower()


@pytest.mark.parametrize("flag", ["--env", "--monitor", "--no-warn", "--help"])
def test_flash_script_documented_flags_present_in_help(flag: str) -> None:
    result = subprocess.run([str(_FLASH_SH), "--help"], capture_output=True, text=True, timeout=10)
    assert flag in result.stdout, f"flag {flag} not documented in --help"
