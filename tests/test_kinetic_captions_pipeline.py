"""Phase E1 — kinetic-captions transcription pipeline tests.

These tests anchor the contract for ``scripts/generate_kinetic_captions.py``:

  * Sparse mode (variants A, B) — only emphasis windows are transcribed,
    yielding a sparse JSON with `<= 12` words per cue.
  * Dense mode (variant C) — every spoken word is transcribed, yielding
    typically 80–250 words per cue.

We don't run faster-whisper inside the unit tests (that's a 30 s+ model
load + GPU-or-CPU inference). Instead we exercise the pure helpers
(emphasis-window parsing, JSON schema, idempotence guard) and let the
generator script itself live behind ``make video-captions`` for real
transcription work.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
GENERATOR = SCRIPTS_DIR / "generate_kinetic_captions.py"
CAPTIONS_DIR = ROOT / "remotion-video" / "public" / "captions"


# --------------------------------------------------------------------------- #
# Generator script presence + entrypoints                                     #
# --------------------------------------------------------------------------- #


def test_generator_script_exists() -> None:
    """generate_kinetic_captions.py is the Phase E1 entry point."""
    assert GENERATOR.is_file(), f"{GENERATOR} does not exist"


def _load_kc_module() -> Any:
    """Import the generator script as a module (registered in sys.modules so
    @dataclass can resolve type hints)."""
    import importlib.util
    import sys as _sys

    spec = importlib.util.spec_from_file_location("kc_generator", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    _sys.modules["kc_generator"] = module
    spec.loader.exec_module(module)
    return module


def test_generator_exposes_main_and_helpers() -> None:
    """Public API must include parse_emphasis_windows, build_payload, main."""
    module = _load_kc_module()
    for name in (
        "parse_emphasis_windows",
        "build_payload",
        "main",
    ):
        assert hasattr(module, name), f"missing public symbol: {name}"


# --------------------------------------------------------------------------- #
# Emphasis window parsing (sparse mode)                                       #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def kc_module() -> Any:
    """Import the generator script as a module so we can call helpers."""
    return _load_kc_module()


def test_parse_emphasis_windows_variant_a(kc_module: Any) -> None:
    """Variant A script declares 4 punch-word lines in the cold-open hook."""
    windows = kc_module.parse_emphasis_windows("A")
    assert isinstance(windows, list)
    assert len(windows) >= 3, "variant A should yield at least 3 emphasis windows"
    for w in windows:
        assert "text" in w and isinstance(w["text"], str)
        assert "second" in w and isinstance(w["second"], (int, float))


def test_parse_emphasis_windows_variant_b(kc_module: Any) -> None:
    """Variant B script declares ~5 metric-punch lines."""
    windows = kc_module.parse_emphasis_windows("B")
    assert len(windows) >= 4, "variant B should yield at least 4 emphasis windows"


def test_parse_emphasis_windows_variant_c_returns_empty(kc_module: Any) -> None:
    """Variant C is dense mode — emphasis windows aren't applicable."""
    windows = kc_module.parse_emphasis_windows("C")
    # Either empty list or a flag indicating dense mode.
    assert windows == [] or windows is None


# --------------------------------------------------------------------------- #
# Payload schema                                                              #
# --------------------------------------------------------------------------- #


def test_build_payload_sparse(kc_module: Any) -> None:
    """Sparse payload (A/B) lists emphasis windows verbatim with timing."""
    sample_windows = [
        {"second": 1.0, "text": "Everyone thinks"},
        {"second": 4.0, "text": "They don't."},
    ]
    payload = kc_module.build_payload(
        variant="A", mode="sparse", emphasis=sample_windows, segments=[]
    )
    assert payload["variant"] == "A"
    assert payload["mode"] == "sparse"
    assert payload["emphasis"] == sample_windows
    assert payload["segments"] == []


def test_build_payload_dense(kc_module: Any) -> None:
    """Dense payload (C) lists segments with word-level timing."""
    sample_segments = [
        {
            "start": 0.0,
            "end": 1.4,
            "text": "Skyherd is the nervous system",
            "words": [
                {"word": "Skyherd", "start": 0.0, "end": 0.4},
                {"word": "is", "start": 0.4, "end": 0.5},
                {"word": "the", "start": 0.5, "end": 0.6},
                {"word": "nervous", "start": 0.6, "end": 1.0},
                {"word": "system", "start": 1.0, "end": 1.4},
            ],
        }
    ]
    payload = kc_module.build_payload(
        variant="C", mode="dense", emphasis=[], segments=sample_segments
    )
    assert payload["variant"] == "C"
    assert payload["mode"] == "dense"
    assert payload["segments"] == sample_segments
    assert payload["emphasis"] == []


# --------------------------------------------------------------------------- #
# JSON output integrity (round-trip)                                          #
# --------------------------------------------------------------------------- #


def test_payload_round_trips_via_json(kc_module: Any) -> None:
    payload = kc_module.build_payload(
        variant="B",
        mode="sparse",
        emphasis=[{"second": 0.5, "text": "$4.17"}],
        segments=[],
    )
    blob = json.dumps(payload)
    restored = json.loads(blob)
    assert restored == payload
