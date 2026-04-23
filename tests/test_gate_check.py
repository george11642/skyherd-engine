"""Tests for scripts/gate_check.py Sim Completeness Gate retro-audit runner.

Verifies:
- GATE_ITEMS has exactly 10 entries in CLAUDE.md order.
- Each check callable returns a (status, evidence) tuple with status ∈ {GREEN, YELLOW, RED}.
- --fast mode skips subprocess-invoking checks and runs in under ~2s.
- Exit code is 0 iff all 10 statuses are GREEN.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "gate_check.py"

EXPECTED_KEYS = [
    "agents_mesh",
    "sensors",
    "vision_heads",
    "sitl_mission",
    "dashboard",
    "voice",
    "scenarios",
    "determinism",
    "fresh_clone",
    "cost_idle",
]


def _load_module():
    spec = importlib.util.spec_from_file_location("gate_check", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_check_script_exists() -> None:
    assert SCRIPT_PATH.is_file(), f"{SCRIPT_PATH} missing"


def test_gate_items_has_exactly_ten_entries_in_expected_order() -> None:
    mod = _load_module()
    keys = [entry[0] for entry in mod.GATE_ITEMS]
    assert keys == EXPECTED_KEYS, f"Gate keys mismatch: {keys}"


def test_each_gate_item_is_callable_triple() -> None:
    mod = _load_module()
    for key, desc, check in mod.GATE_ITEMS:
        assert isinstance(key, str) and key
        assert isinstance(desc, str) and desc
        assert callable(check), f"{key}: check is not callable"


def test_fast_mode_returns_valid_statuses_for_all_checks() -> None:
    mod = _load_module()
    for key, _desc, check in mod.GATE_ITEMS:
        status, evidence = check(True)  # fast=True
        assert status in {"GREEN", "YELLOW", "RED"}, f"{key}: bad status {status!r}"
        assert isinstance(evidence, str) and evidence, f"{key}: empty evidence"


def test_fast_cli_invocation_completes_quickly_and_prints_ten_rows() -> None:
    start = time.monotonic()
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--fast"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    elapsed = time.monotonic() - start
    assert elapsed < 10, f"--fast took {elapsed:.1f}s (should be under 10s)"
    assert result.returncode in (0, 1), f"unexpected exit {result.returncode}"
    # 10 rows beginning with [GREEN|YELLOW|RED
    row_lines = [
        line for line in result.stdout.splitlines()
        if line.startswith("[GREEN") or line.startswith("[YELLOW") or line.startswith("[RED")
    ]
    assert len(row_lines) == 10, f"expected 10 rows, got {len(row_lines)}:\n{result.stdout}"
    assert "SkyHerd Sim Completeness Gate" in result.stdout


def test_exit_code_zero_iff_all_green(monkeypatch) -> None:
    """When all checks are stubbed GREEN, main() should sys.exit(0)."""
    mod = _load_module()
    stubbed = [(k, d, (lambda fast, _s="GREEN": (_s, "ok"))) for k, d, _c in mod.GATE_ITEMS]
    monkeypatch.setattr(mod, "GATE_ITEMS", stubbed)
    monkeypatch.setattr(sys, "argv", ["gate_check.py", "--fast"])
    try:
        mod.main()
    except SystemExit as exc:
        assert exc.code == 0
        return
    raise AssertionError("main() did not call sys.exit()")


def test_exit_code_nonzero_if_any_not_green(monkeypatch) -> None:
    mod = _load_module()
    stubbed = [(k, d, (lambda fast, _s="GREEN": (_s, "ok"))) for k, d, _c in mod.GATE_ITEMS]
    # Force first item RED
    k0, d0, _ = stubbed[0]
    stubbed[0] = (k0, d0, lambda fast: ("RED", "bad"))
    monkeypatch.setattr(mod, "GATE_ITEMS", stubbed)
    monkeypatch.setattr(sys, "argv", ["gate_check.py", "--fast"])
    try:
        mod.main()
    except SystemExit as exc:
        assert exc.code == 1
        return
    raise AssertionError("main() did not call sys.exit()")
