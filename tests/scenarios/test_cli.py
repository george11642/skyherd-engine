"""Tests for skyherd-demo CLI (typer CliRunner)."""

from __future__ import annotations

from typer.testing import CliRunner

from skyherd.scenarios.cli import app

runner = CliRunner(mix_stderr=False)


class TestCliList:
    def test_list_shows_all_scenarios(self) -> None:
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "coyote" in result.output
        assert "sick_cow" in result.output
        assert "water_drop" in result.output
        assert "calving" in result.output
        assert "storm" in result.output

    def test_list_shows_descriptions(self) -> None:
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        # At least some descriptive text
        assert len(result.output) > 100


class TestCliPlay:
    def test_play_coyote(self) -> None:
        result = runner.invoke(app, ["play", "coyote", "--seed", "42"])
        assert result.exit_code == 0, f"CLI error: {result.output}"
        assert "PASS" in result.output

    def test_play_sick_cow(self) -> None:
        result = runner.invoke(app, ["play", "sick_cow", "--seed", "42"])
        assert result.exit_code == 0, f"CLI error: {result.output}"
        assert "PASS" in result.output

    def test_play_water_drop(self) -> None:
        result = runner.invoke(app, ["play", "water_drop", "--seed", "42"])
        assert result.exit_code == 0, f"CLI error: {result.output}"
        assert "PASS" in result.output

    def test_play_calving(self) -> None:
        result = runner.invoke(app, ["play", "calving", "--seed", "42"])
        assert result.exit_code == 0, f"CLI error: {result.output}"
        assert "PASS" in result.output

    def test_play_storm(self) -> None:
        result = runner.invoke(app, ["play", "storm", "--seed", "42"])
        assert result.exit_code == 0, f"CLI error: {result.output}"
        assert "PASS" in result.output

    def test_play_all(self) -> None:
        result = runner.invoke(app, ["play", "all", "--seed", "42"])
        assert result.exit_code == 0, f"CLI error: {result.output}"
        assert "5/5" in result.output or "passed" in result.output.lower()

    def test_play_unknown_exits_nonzero(self) -> None:
        result = runner.invoke(app, ["play", "not_a_scenario"])
        assert result.exit_code != 0

    def test_play_dry_run_succeeds(self) -> None:
        result = runner.invoke(app, ["play", "coyote", "--dry-run"])
        assert result.exit_code == 0, f"CLI error: {result.output}"

    def test_play_outputs_event_count(self) -> None:
        result = runner.invoke(app, ["play", "coyote", "--seed", "42"])
        assert "Events" in result.output or "events" in result.output.lower()

    def test_play_outputs_replay_path(self) -> None:
        result = runner.invoke(app, ["play", "coyote", "--seed", "42"])
        assert "runtime" in result.output or "Replay" in result.output
