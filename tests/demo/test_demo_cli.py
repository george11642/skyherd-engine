"""Tests for skyherd.demo.cli — hardware demo CLI entry point."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from skyherd.demo.cli import app

# mix_stderr=True (default) so err=True typer.echo goes to output
runner = CliRunner(mix_stderr=True)


def _fake_demo_result(**kwargs):
    """Build a DemoRunResult with given field overrides."""
    from skyherd.demo.hardware_only import DemoRunResult

    result = DemoRunResult(prop=kwargs.get("prop", "combo"))
    result.hardware_detection_received = kwargs.get("hardware_detection_received", False)
    result.drone_launched = kwargs.get("drone_launched", True)
    result.wes_called = kwargs.get("wes_called", True)
    result.fallback_used = kwargs.get("fallback_used", False)
    result.fallback_reason = kwargs.get("fallback_reason", None)
    result.events = kwargs.get("events", [{"type": "coyote.detected"}])
    result.tool_calls = kwargs.get("tool_calls", [{"tool": "launch_drone"}])
    result.jsonl_path = kwargs.get("jsonl_path", None)
    return result


# ---------------------------------------------------------------------------
# help / validation
# ---------------------------------------------------------------------------


def test_help_exits_clean():
    # Single-command Typer app — no subcommand prefix
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "prop" in result.output.lower()


def test_invalid_prop_exits_with_code_2():
    """Unknown --prop value exits with code 2 and prints an error."""
    result = runner.invoke(app, ["--prop", "not_a_prop"])
    assert result.exit_code == 2
    assert "Unknown prop" in result.output or "not_a_prop" in result.output


# ---------------------------------------------------------------------------
# play command — HardwareOnlyDemo is imported lazily inside the function.
# Patch it at its definition module so the lazy import picks up the mock.
# ---------------------------------------------------------------------------


def test_play_coyote_prop_runs():
    """--prop coyote calls HardwareOnlyDemo.run() and prints summary."""
    fake = _fake_demo_result(prop="coyote")
    with patch("skyherd.demo.hardware_only.HardwareOnlyDemo") as MockClass:
        MockClass.return_value.run = AsyncMock(return_value=fake)
        result = runner.invoke(app, ["--prop", "coyote"])
    assert result.exit_code == 0
    assert "Demo complete" in result.output
    assert "coyote" in result.output


def test_play_sick_cow_prop_runs():
    """--prop sick-cow calls HardwareOnlyDemo.run()."""
    fake = _fake_demo_result(prop="sick-cow")
    with patch("skyherd.demo.hardware_only.HardwareOnlyDemo") as MockClass:
        MockClass.return_value.run = AsyncMock(return_value=fake)
        result = runner.invoke(app, ["--prop", "sick-cow"])
    assert result.exit_code == 0
    assert "Demo complete" in result.output


def test_play_combo_is_default():
    """Default --prop is combo."""
    fake = _fake_demo_result(prop="combo")
    with patch("skyherd.demo.hardware_only.HardwareOnlyDemo") as MockClass:
        MockClass.return_value.run = AsyncMock(return_value=fake)
        result = runner.invoke(app, [])
    assert result.exit_code == 0
    MockClass.assert_called_once_with(prop="combo", timeout_s=180.0)


def test_play_custom_timeout_forwarded():
    """--timeout is forwarded to HardwareOnlyDemo constructor."""
    fake = _fake_demo_result(prop="coyote")
    with patch("skyherd.demo.hardware_only.HardwareOnlyDemo") as MockClass:
        MockClass.return_value.run = AsyncMock(return_value=fake)
        runner.invoke(app, ["--prop", "coyote", "--timeout", "60"])
    MockClass.assert_called_once_with(prop="coyote", timeout_s=60.0)


def test_play_prints_event_and_tool_counts():
    """Output includes event and tool-call counts."""
    fake = _fake_demo_result(prop="combo", events=[{}, {}], tool_calls=[{}, {}, {}])
    with patch("skyherd.demo.hardware_only.HardwareOnlyDemo") as MockClass:
        MockClass.return_value.run = AsyncMock(return_value=fake)
        result = runner.invoke(app, [])
    assert "2" in result.output  # 2 events
    assert "3" in result.output  # 3 tool calls


def test_play_prints_fallback_reason_when_set():
    """When fallback_used=True, the fallback reason is printed."""
    fake = _fake_demo_result(prop="combo", fallback_used=True, fallback_reason="PROP_NOT_DETECTED")
    with patch("skyherd.demo.hardware_only.HardwareOnlyDemo") as MockClass:
        MockClass.return_value.run = AsyncMock(return_value=fake)
        result = runner.invoke(app, [])
    assert "PROP_NOT_DETECTED" in result.output
    assert result.exit_code == 0


def test_play_prints_jsonl_path_when_set(tmp_path):
    """When jsonl_path is set, it appears in output."""
    log_file = tmp_path / "demo.jsonl"
    fake = _fake_demo_result(prop="coyote", jsonl_path=log_file)
    with patch("skyherd.demo.hardware_only.HardwareOnlyDemo") as MockClass:
        MockClass.return_value.run = AsyncMock(return_value=fake)
        result = runner.invoke(app, ["--prop", "coyote"])
    assert str(log_file) in result.output


def test_main_callable():
    from skyherd.demo.cli import main

    assert callable(main)
