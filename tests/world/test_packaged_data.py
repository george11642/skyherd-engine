"""Wheel-layout test: force-include ships worlds/ into skyherd/worlds/ (BLD-01)."""

from __future__ import annotations

from importlib.resources import files


def test_worlds_ranch_a_packaged() -> None:
    """importlib.resources can find ranch_a.yaml under the skyherd package."""
    p = files("skyherd").joinpath("worlds/ranch_a.yaml")
    assert p.is_file(), f"expected packaged world config at {p!r}"


def test_worlds_ranch_b_packaged() -> None:
    """Directory-level force-include ships BOTH ranch configs."""
    p = files("skyherd").joinpath("worlds/ranch_b.yaml")
    assert p.is_file(), f"expected packaged world config at {p!r}"
