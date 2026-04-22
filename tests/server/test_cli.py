"""Tests for skyherd.server.cli — typer CLI entry point."""

from __future__ import annotations

import os
from unittest.mock import patch

from typer.testing import CliRunner

from skyherd.server.cli import app

runner = CliRunner()


def test_help_exit_clean():
    """--help exits cleanly and mentions port option."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "port" in result.output.lower()


def test_start_custom_port_echoed():
    """Invoking with --port 9999 echoes the port and calls uvicorn with it."""
    with patch("skyherd.server.cli.uvicorn.run") as mock_run:
        result = runner.invoke(app, ["--port", "9999", "--mock"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        assert mock_run.call_args.kwargs["port"] == 9999
        assert "9999" in result.output


def test_start_default_port_is_8000():
    """Default port passed to uvicorn is 8000."""
    with patch("skyherd.server.cli.uvicorn.run") as mock_run:
        runner.invoke(app, ["--mock"])
        assert mock_run.call_args.kwargs["port"] == 8000


def test_mock_flag_sets_env_var(monkeypatch):
    """--mock sets SKYHERD_MOCK=1 in os.environ."""
    monkeypatch.delenv("SKYHERD_MOCK", raising=False)
    with patch("skyherd.server.cli.uvicorn.run"):
        runner.invoke(app, ["--mock"])
        assert os.environ.get("SKYHERD_MOCK") == "1"


def test_no_mock_flag_does_not_set_env(monkeypatch):
    """--no-mock leaves SKYHERD_MOCK unset."""
    monkeypatch.delenv("SKYHERD_MOCK", raising=False)
    with patch("skyherd.server.cli.uvicorn.run"):
        runner.invoke(app, ["--no-mock"])
        assert os.environ.get("SKYHERD_MOCK") is None


def test_reload_flag_forwarded():
    """--reload is forwarded to uvicorn.run."""
    with patch("skyherd.server.cli.uvicorn.run") as mock_run:
        runner.invoke(app, ["--reload", "--mock"])
        assert mock_run.call_args.kwargs["reload"] is True


def test_default_reload_is_false():
    """reload defaults to False."""
    with patch("skyherd.server.cli.uvicorn.run") as mock_run:
        runner.invoke(app, ["--mock"])
        assert mock_run.call_args.kwargs["reload"] is False


def test_log_level_forwarded():
    """--log-level is forwarded to uvicorn.run."""
    with patch("skyherd.server.cli.uvicorn.run") as mock_run:
        runner.invoke(app, ["--log-level", "warning", "--mock"])
        assert mock_run.call_args.kwargs["log_level"] == "warning"


def test_app_string_target():
    """uvicorn is pointed at the correct ASGI app string."""
    with patch("skyherd.server.cli.uvicorn.run") as mock_run:
        runner.invoke(app, ["--mock"])
        assert mock_run.call_args.args[0] == "skyherd.server.app:app"


def test_main_callable():
    """main() is callable (entry-point contract)."""
    from skyherd.server.cli import main

    assert callable(main)
