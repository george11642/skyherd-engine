"""Determinism e2e test: two seed=42 runs produce identical sanitized output.

Wall-clock timestamps and short session-hash IDs are stripped before comparison
so that only scenario logic, event counts, and PASS/FAIL verdicts are compared.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys

import pytest

# ---------------------------------------------------------------------------
# Sanitization patterns
# ---------------------------------------------------------------------------

DETERMINISM_SANITIZE: list[tuple[str, str]] = [
    # ISO-8601 timestamps (YYYY-MM-DDTHH:MM:SS…)
    (r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.Z+-]+", ""),
    # Full UUID v4
    (r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", ""),
    # HH:MM:SS log-line wall-clock prefixes (with optional sub-seconds)
    (r"\b[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?\b", ""),
    # Short-hash session IDs (session-deadbeef style)
    (r"\bsession-[a-f0-9]{8}\b", "session-XXXXXXXX"),
]


def _sanitize(text: str) -> str:
    """Strip all non-deterministic tokens from *text*."""
    for pattern, replacement in DETERMINISM_SANITIZE:
        text = re.sub(pattern, replacement, text)
    return text


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _run_demo(seed: int) -> str:
    """Run `skyherd-demo play all --seed <seed>` and return stdout."""
    result = subprocess.run(
        [sys.executable, "-m", "skyherd.demo.cli", "play", "all", "--seed", str(seed)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    # Combine stdout + stderr so log lines are included in the comparison
    return result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_demo_seed42_is_deterministic() -> None:
    """Two back-to-back seed=42 runs must produce the same sanitized output."""
    run_a = _sanitize(_run_demo(42))
    run_b = _sanitize(_run_demo(42))

    md5_a = _md5(run_a)
    md5_b = _md5(run_b)

    assert md5_a == md5_b, (
        f"Determinism check failed — sanitized md5 differs:\n"
        f"  run_a: {md5_a}\n"
        f"  run_b: {md5_b}\n"
        "Remaining diff lines are non-deterministic after sanitization."
    )
