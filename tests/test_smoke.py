"""Smoke test — verifies the skyherd package can be imported and version matches."""

import importlib


def test_skyherd_importable() -> None:
    """Package must import without errors."""
    skyherd = importlib.import_module("skyherd")
    assert skyherd is not None


def test_version_string() -> None:
    """__version__ must match the version declared in pyproject.toml."""
    import skyherd

    assert skyherd.__version__ == "0.1.0"


def test_subpackages_importable() -> None:
    """Every declared sub-package must be importable."""
    subpackages = [
        "skyherd.world",
        "skyherd.sensors",
        "skyherd.agents",
        "skyherd.mcp",
        "skyherd.drone",
        "skyherd.vision",
        "skyherd.attest",
    ]
    for name in subpackages:
        mod = importlib.import_module(name)
        assert mod is not None, f"Could not import {name}"
