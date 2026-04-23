"""README must contain the canonical 3-command judge quickstart (BLD-02 doc-drift guard).

Locks the quickstart commands against silent edits. If anyone removes or
rewords the canonical strings in README.md, this test fails loudly.

The same commands also appear in CLAUDE.md and scripts/fresh_clone_smoke.sh --
all three must agree.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_README = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
_CLAUDE_MD_PATH = _REPO_ROOT / "CLAUDE.md"

_EXPECTED_COMMANDS = [
    "uv sync",
    "pnpm install",
    "pnpm run build",
    "make demo SEED=42 SCENARIO=all",
    "make dashboard",
]


def test_readme_quickstart_commands_present() -> None:
    """README must contain each canonical quickstart command string verbatim."""
    for cmd in _EXPECTED_COMMANDS:
        assert cmd in _README, (
            f"README missing quickstart command: {cmd!r}. "
            "If you intentionally reworded the quickstart, update "
            "_EXPECTED_COMMANDS in this test AND scripts/fresh_clone_smoke.sh."
        )


def test_readme_has_quickstart_section() -> None:
    """README must have a Quickstart section (case-insensitive)."""
    assert "Quickstart" in _README or "quickstart" in _README.lower(), (
        "README is missing a Quickstart section -- judges will not find the "
        "3-command flow."
    )


def test_claude_md_agrees_on_demo_command() -> None:
    """CLAUDE.md must reference the same make demo command as README."""
    if not _CLAUDE_MD_PATH.exists():
        # CLAUDE.md is not always present in every repo layout -- skip gracefully
        return
    claude_md = _CLAUDE_MD_PATH.read_text(encoding="utf-8")
    assert "make demo SEED=42 SCENARIO=all" in claude_md, (
        "CLAUDE.md has drifted: it no longer references the canonical "
        "'make demo SEED=42 SCENARIO=all' command. Update CLAUDE.md to match "
        "README.md or update the README if the canonical command changed."
    )
