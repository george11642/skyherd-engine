"""SCEN-01 + DASH-06: vet-intake drafter unit tests — schema, path-traversal, markdown, pixel bbox."""

from __future__ import annotations

from pathlib import Path

import pytest


def _valid_args(**overrides):
    base = dict(
        cow_tag="A014",
        severity="escalate",
        disease="pinkeye",
        signals=["ocular_discharge=0.70", "pixel_head=pinkeye@0.87"],
        cow_snapshot={
            "tag": "A014",
            "bcs": 5.2,
            "health_score": 0.55,
            "pos": (300.0, 300.0),
        },
        session_id="sess_abc123",
        herd_context="paddock_north · 0 other ocular signs · moderate fly pressure",
    )
    base.update(overrides)
    return base


def test_draft_vet_intake_creates_markdown_file(tmp_path, monkeypatch) -> None:
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)

    rec = vi.draft_vet_intake(**_valid_args())
    assert rec.cow_tag == "A014"
    assert rec.severity == "escalate"
    assert rec.path.startswith(str(tmp_path)) or Path(rec.path).parent == tmp_path
    assert Path(rec.path).exists()
    content = Path(rec.path).read_text(encoding="utf-8")
    assert "pinkeye" in content.lower()
    assert "A014" in content
    assert "escalate" in content.lower() or "ESCALATE" in content


def test_draft_vet_intake_rejects_invalid_cow_tag(tmp_path, monkeypatch) -> None:
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)

    for bad in ["invalid", "a014", "A14", "A0145", "../etc", "A014_extra"]:
        with pytest.raises(ValueError):
            vi.draft_vet_intake(**_valid_args(cow_tag=bad))


def test_draft_vet_intake_path_traversal_guard(tmp_path, monkeypatch) -> None:
    """Even a regex-valid tag must land inside the intake dir after Path.resolve()."""
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)
    rec = vi.draft_vet_intake(**_valid_args(cow_tag="A014"))
    resolved = Path(rec.path).resolve()
    assert str(resolved).startswith(str(tmp_path.resolve())), (
        f"Intake landed outside the intake dir: {resolved}"
    )


def test_get_intake_path_returns_expected_shape(tmp_path, monkeypatch) -> None:
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)
    p = vi.get_intake_path("A014_20260422T153200Z")
    assert p.name == "A014_20260422T153200Z.md"
    assert p.parent == tmp_path


def test_markdown_contains_required_sections(tmp_path, monkeypatch) -> None:
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)
    rec = vi.draft_vet_intake(**_valid_args())
    body = Path(rec.path).read_text(encoding="utf-8")
    for section in ("## Cow", "## Finding", "## Recommended Next Action", "## Herd Context"):
        assert section in body, f"Missing section: {section!r}"


def test_draft_vet_intake_accepts_signals_structured_bbox(tmp_path, monkeypatch) -> None:
    """DASH-06: pixel-head bbox propagates through signals_structured into record + markdown."""
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)
    pixel_signal = {
        "kind": "pixel_detection",
        "head": "pinkeye",
        "bbox": [321, 120, 412, 198],
        "confidence": 0.87,
    }
    rec = vi.draft_vet_intake(**_valid_args(signals_structured=[pixel_signal]))

    # Round-trip into the record
    assert hasattr(rec, "signals_structured"), "VetIntakeRecord missing signals_structured field"
    assert rec.signals_structured, "signals_structured is empty"
    dumped = rec.signals_structured[0]
    # Pydantic may normalize; accept dict or object with bbox attribute
    if hasattr(dumped, "model_dump"):
        dumped = dumped.model_dump()
    assert dumped["kind"] == "pixel_detection"
    assert dumped["head"] == "pinkeye"
    assert list(dumped["bbox"]) == [321, 120, 412, 198]
    assert abs(dumped["confidence"] - 0.87) < 1e-6

    # Markdown body carries the bbox coords (DASH-06 rendering source)
    body = Path(rec.path).read_text(encoding="utf-8")
    for coord in ("321", "120", "412", "198"):
        assert coord in body, f"Markdown body missing bbox coord {coord!r}"
    assert "pixel_detection" in body or "Pixel Detection" in body.title()


def test_draft_vet_intake_signals_structured_defaults_to_empty(tmp_path, monkeypatch) -> None:
    """Backwards-compat: omitting signals_structured yields an empty list."""
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)
    rec = vi.draft_vet_intake(**_valid_args())
    assert hasattr(rec, "signals_structured")
    assert rec.signals_structured == [] or list(rec.signals_structured) == []
