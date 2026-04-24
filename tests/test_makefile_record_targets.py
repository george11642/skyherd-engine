"""Phase 9 VIDEO-06: Makefile `rehearsal` + `record-ready` target smoke tests.

These tests prove the targets exist, parse cleanly via `make -n`, and are
declared `.PHONY`. No real execution — a rehearsal loop or live dashboard
would hang CI.

The `preflight` target (PF-04) is tested here too for consistency; its
underlying pytest suite is exercised separately.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
MAKE_BIN = shutil.which("make") or "/usr/bin/make"


def _make_dry_run(target: str) -> subprocess.CompletedProcess[str]:
    """Run `make -n <target>` from the repo root, no side effects."""
    return subprocess.run(
        [MAKE_BIN, "-n", target],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def test_make_binary_resolvable() -> None:
    """Guard: CI images must provide make."""
    assert Path(MAKE_BIN).exists() or MAKE_BIN == "/usr/bin/make", (
        f"make binary not found at {MAKE_BIN}"
    )


class TestRehearsalTarget:
    def test_rehearsal_dry_run_succeeds(self) -> None:
        result = _make_dry_run("rehearsal")
        assert result.returncode == 0, (
            f"make -n rehearsal failed. stdout={result.stdout!r} stderr={result.stderr!r}"
        )

    def test_rehearsal_references_seed_variable(self) -> None:
        result = _make_dry_run("rehearsal")
        # The recipe should expand $(SEED) — default 42
        assert "SEED=42" in result.stdout or "Seed=42" in result.stdout, (
            f"rehearsal target did not expand SEED. stdout={result.stdout!r}"
        )

    def test_rehearsal_invokes_demo_target(self) -> None:
        result = _make_dry_run("rehearsal")
        # rehearsal delegates to $(MAKE) demo ...
        assert "demo" in result.stdout, (
            f"rehearsal target did not invoke demo. stdout={result.stdout!r}"
        )


class TestRecordReadyTarget:
    def test_record_ready_dry_run_succeeds(self) -> None:
        result = _make_dry_run("record-ready")
        assert result.returncode == 0, (
            f"make -n record-ready failed. stdout={result.stdout!r} stderr={result.stderr!r}"
        )

    def test_record_ready_mentions_dashboard_launch(self) -> None:
        result = _make_dry_run("record-ready")
        assert "8000" in result.stdout, (
            "record-ready target does not launch the dashboard at port 8000"
        )

    def test_record_ready_references_video_script(self) -> None:
        """record-ready surfaces scrub-points from DEMO_VIDEO_SCRIPT.md."""
        result = _make_dry_run("record-ready")
        assert "DEMO_VIDEO_SCRIPT.md" in result.stdout, (
            "record-ready does not reference docs/DEMO_VIDEO_SCRIPT.md"
        )


class TestPreflightTarget:
    def test_preflight_dry_run_succeeds(self) -> None:
        result = _make_dry_run("preflight")
        assert result.returncode == 0, (
            f"make -n preflight failed. stdout={result.stdout!r} stderr={result.stderr!r}"
        )

    def test_preflight_invokes_e2e_test(self) -> None:
        result = _make_dry_run("preflight")
        assert "test_preflight_e2e" in result.stdout, (
            "preflight target does not invoke the E2E pytest module"
        )


class TestPhonyDeclaration:
    @pytest.fixture(scope="class")
    def makefile_text(self) -> str:
        return (ROOT / "Makefile").read_text()

    def test_rehearsal_is_phony(self, makefile_text: str) -> None:
        phony_lines = [
            ln for ln in makefile_text.splitlines() if ln.startswith(".PHONY:")
        ]
        assert any("rehearsal" in ln for ln in phony_lines), (
            "rehearsal not declared .PHONY"
        )

    def test_record_ready_is_phony(self, makefile_text: str) -> None:
        phony_lines = [
            ln for ln in makefile_text.splitlines() if ln.startswith(".PHONY:")
        ]
        assert any("record-ready" in ln for ln in phony_lines), (
            "record-ready not declared .PHONY"
        )

    def test_preflight_is_phony(self, makefile_text: str) -> None:
        phony_lines = [
            ln for ln in makefile_text.splitlines() if ln.startswith(".PHONY:")
        ]
        assert any("preflight" in ln for ln in phony_lines), (
            "preflight not declared .PHONY"
        )
