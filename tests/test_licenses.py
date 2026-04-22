"""License guard: assert no AGPL/GPL packages in the base dep closure.

These tests are blocking Wave 0 gate — they must pass before any pixel
inference code is merged.  They verify:

1. ultralytics (AGPL-3.0) is not a declared direct or transitive base dep.
2. yolov5 (GPL) is not a declared direct or transitive base dep.
3. torch is importable (transitive via supervision / edge extra).
4. torchvision is importable (promoted to direct dep in this plan).
"""

from __future__ import annotations

import importlib.metadata


def _base_dep_closure() -> set[str]:
    """Return the set of package names reachable from skyherd-engine base deps.

    Uses ``importlib.metadata`` to walk the dependency graph starting from
    the declared ``Requires-Dist`` of skyherd-engine (base only — no extras).
    Extras (e.g. ``edge``) are excluded by checking for ``; extra ==`` markers.
    """
    visited: set[str] = set()

    def _walk(pkg_name: str) -> None:
        key = pkg_name.lower().replace("-", "_")
        if key in visited:
            return
        visited.add(key)
        try:
            dist = importlib.metadata.distribution(pkg_name)
        except importlib.metadata.PackageNotFoundError:
            return
        for req in dist.metadata.get_all("Requires-Dist") or []:
            # Skip conditional extras — they are not in the base closure
            if "; extra ==" in req:
                continue
            # Extract package name (before any version specifier)
            dep_name = req.split()[0].split(";")[0].split("[")[0].strip()
            _walk(dep_name)

    _walk("skyherd-engine")
    return visited


def test_no_agpl_in_base_deps() -> None:
    """ultralytics (AGPL-3.0) must NOT appear in the base dep closure.

    PytorchWildlife pulls ultralytics as a hard dep.  It is allowed only in
    the ``edge`` optional extra — never in base.  Adding it to base would
    infect the entire project's license under AGPL-3.0.
    """
    closure = _base_dep_closure()
    assert "ultralytics" not in closure, (
        "ultralytics (AGPL-3.0) is in the base dep closure. "
        "Move PytorchWildlife to the `edge` optional extra only."
    )


def test_no_yolov5_in_base_deps() -> None:
    """yolov5 (GPL) must NOT appear in the base dep closure."""
    closure = _base_dep_closure()
    assert "yolov5" not in closure, (
        "yolov5 (GPL) is in the base dep closure. "
        "Remove it from base deps immediately."
    )


def test_torch_importable() -> None:
    """torch must be importable (transitive via supervision / dev environment)."""
    import torch  # noqa: F401

    assert torch is not None


def test_torchvision_importable() -> None:
    """torchvision must be importable (direct dep promoted in this plan).

    If this test fails, run: uv sync
    torchvision>=0.19,<1 must appear in [project] dependencies in pyproject.toml.
    """
    import torchvision  # noqa: F401

    assert torchvision is not None
