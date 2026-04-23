"""DASH-01 acceptance — Phase 4 BLD-03 CLI live-mode end-to-end smoke.

Consumes src/skyherd/server/live.py (Phase 4). Does NOT re-implement it.
Proves the CLI returns real (non-mock) data through /api/snapshot when booted
via subprocess — the judge-clone path.
"""

from __future__ import annotations

import json
import shutil
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest


def _pick_free_port() -> int:
    """Bind to port 0, close, reuse. Safe under pytest-xdist."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _get_json(url: str, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _health_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1.0) as resp:  # noqa: S310
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.integration
def test_run_live_smoke() -> None:
    """DASH-01: subprocess-level proof of Phase 4 BLD-03 live-mode plumbing."""
    if shutil.which("uv") is None:
        pytest.skip("uv not installed — cannot invoke Phase 4 CLI")

    try:
        import skyherd.server.live  # noqa: F401
    except ImportError as exc:
        pytest.skip(f"BLD-03 prerequisite — skyherd.server.live missing: {exc}")

    port = _pick_free_port()
    health_url = f"http://127.0.0.1:{port}/health"
    snapshot_url = f"http://127.0.0.1:{port}/api/snapshot"
    repo_root = Path(__file__).resolve().parents[2]

    proc = subprocess.Popen(  # noqa: S603
        [
            "uv", "run", "python", "-m", "skyherd.server.live",
            "--port", str(port),
            "--host", "127.0.0.1",
            "--seed", "42",
        ],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        # Wait up to 20s for /health
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            if _health_ok(health_url):
                break
            time.sleep(0.5)
        else:
            try:
                out = proc.stdout.read(2048).decode("utf-8", errors="replace") if proc.stdout else ""
            except Exception:  # noqa: BLE001
                out = "<stdout unreadable>"
            pytest.fail(
                f"DASH-01: BLD-03 live bootstrap did not reach healthy state "
                f"within 20s on port {port}. Server output:\n{out}"
            )

        # Probe /api/snapshot
        body = _get_json(snapshot_url, timeout=5.0)
        assert "cows" in body, f"/api/snapshot missing 'cows' key: {list(body.keys())}"
        assert len(body["cows"]) == 50, (
            f"DASH-01: expected 50 cows via live CLI, got {len(body['cows'])} "
            f"(mock path returns 12 — CLI did not invoke mock=False)."
        )
    finally:
        try:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2.0)
