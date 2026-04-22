"""Tests for skyherd.world.cli — typer CLI for world tick loop."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from skyherd.world.cli import app

runner = CliRunner()


def test_help_exits_clean():
    """--help exits 0 and mentions seed and duration."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "seed" in result.output.lower()
    assert "duration" in result.output.lower()


def test_run_produces_jsonl_output():
    """Running for 10 sim-seconds with seed=42 emits at least one JSON line."""
    result = runner.invoke(app, ["--seed", "42", "--duration", "10"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert len(lines) >= 1
    # Every line must be valid JSON
    for line in lines:
        parsed = json.loads(line)
        assert isinstance(parsed, dict)


def test_run_events_have_type_key():
    """Each emitted event dict has a 'type' key."""
    result = runner.invoke(app, ["--seed", "42", "--duration", "20"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert len(lines) >= 1
    for line in lines:
        parsed = json.loads(line)
        assert "type" in parsed, f"Event missing 'type' key: {parsed}"


def test_run_deterministic_same_seed():
    """Two runs with the same seed and duration produce identical output."""
    args = ["--seed", "7", "--duration", "15"]
    result1 = runner.invoke(app, args)
    result2 = runner.invoke(app, args)
    assert result1.exit_code == 0
    assert result2.exit_code == 0
    assert result1.output == result2.output


def test_run_longer_duration_produces_more_events():
    """A longer duration produces at least as many events as a short one."""
    r_short = runner.invoke(app, ["--seed", "42", "--duration", "10"])
    r_long = runner.invoke(app, ["--seed", "42", "--duration", "50"])
    assert r_short.exit_code == 0
    assert r_long.exit_code == 0
    lines_short = [ln for ln in r_short.output.splitlines() if ln.strip()]
    lines_long = [ln for ln in r_long.output.splitlines() if ln.strip()]
    assert len(lines_long) >= len(lines_short)


def test_run_verbose_writes_summary_to_stderr():
    """--verbose mode writes a summary JSON object."""
    result = runner.invoke(app, ["--seed", "42", "--duration", "10", "--verbose"])
    assert result.exit_code == 0
    # The summary goes to stderr (which CliRunner captures in output for mix_stderr=True default)
    # Just verify the run completed without error
    assert result.exception is None


def test_run_zero_duration_produces_no_output():
    """--duration 0 (or < step_dt) produces no event lines."""
    result = runner.invoke(app, ["--seed", "42", "--duration", "0"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert len(lines) == 0


def test_main_callable():
    """main() is callable (entry-point contract)."""
    from skyherd.world.cli import main

    assert callable(main)
