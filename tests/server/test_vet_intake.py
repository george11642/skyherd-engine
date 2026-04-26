"""Server-scoped vet-intake coverage (DASH-02).

This module lives under tests/server/ so the Plan 05-04 server-only coverage
gate (``pytest tests/server/ --cov=src/skyherd/server --cov-fail-under=85``)
covers the vet-intake drafter + retrieval helpers. The same logic also has
end-to-end coverage in tests/agents/test_vet_intake.py; these cases are
scoped to the server coverage surface.
"""

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
        session_id="sess_server_01",
        herd_context="paddock_north · moderate fly pressure",
    )
    base.update(overrides)
    return base


def test_draft_vet_intake_writes_markdown(tmp_path, monkeypatch) -> None:
    """Happy path: draft_vet_intake creates a .md file inside the intake dir."""
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)

    rec = vi.draft_vet_intake(**_valid_args())

    assert rec.cow_tag == "A014"
    assert rec.severity == "escalate"
    assert Path(rec.path).exists()
    body = Path(rec.path).read_text(encoding="utf-8")
    assert "A014" in body
    assert "pinkeye" in body.lower()
    assert "ESCALATE" in body


def test_draft_vet_intake_rejects_bad_cow_tag(tmp_path, monkeypatch) -> None:
    """Regex guard rejects tags that do not match ^[A-Z][0-9]{3}$."""
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)

    for bad in ["invalid", "a014", "A14", "A0145", "../A014"]:
        with pytest.raises(ValueError):
            vi.draft_vet_intake(**_valid_args(cow_tag=bad))


def test_draft_vet_intake_signals_structured_roundtrip(tmp_path, monkeypatch) -> None:
    """DASH-06: pixel bbox signals_structured reaches the record and markdown."""
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)

    pixel_signal = {
        "kind": "pixel_detection",
        "head": "pinkeye",
        "bbox": [11, 22, 33, 44],
        "confidence": 0.91,
    }
    rec = vi.draft_vet_intake(**_valid_args(signals_structured=[pixel_signal]))

    assert rec.signals_structured[0]["kind"] == "pixel_detection"
    body = Path(rec.path).read_text(encoding="utf-8")
    for coord in ("11", "22", "33", "44"):
        assert coord in body


def test_draft_vet_intake_signals_structured_defaults_empty(tmp_path, monkeypatch) -> None:
    """Omitting signals_structured yields an empty list (backwards-compat)."""
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)
    rec = vi.draft_vet_intake(**_valid_args())
    assert rec.signals_structured == []


def test_draft_vet_intake_includes_attest_seq_when_given(tmp_path, monkeypatch) -> None:
    """attest_seq, when supplied, renders into the Attestation section."""
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)
    rec = vi.draft_vet_intake(**_valid_args(attest_seq=1234))
    body = Path(rec.path).read_text(encoding="utf-8")
    assert "1234" in body


def test_draft_vet_intake_unknown_disease_uses_default_treatment(
    tmp_path,
    monkeypatch,
) -> None:
    """Unknown disease falls back to the default treatment guidance."""
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)
    rec = vi.draft_vet_intake(**_valid_args(disease="unknown_disease_xyz"))
    body = Path(rec.path).read_text(encoding="utf-8")
    # Default guidance always mentions contacting the vet.
    assert "vet" in body.lower()


@pytest.mark.parametrize("disease", ["pinkeye", "screwworm", "foot_rot", "brd"])
def test_draft_vet_intake_known_diseases_render_treatment(
    tmp_path,
    monkeypatch,
    disease: str,
) -> None:
    """Each listed disease triggers its own treatment block."""
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)
    rec = vi.draft_vet_intake(**_valid_args(disease=disease))
    body = Path(rec.path).read_text(encoding="utf-8")
    assert "Recommended Next Action" in body
    # Treatment guidance lines are rendered as bullets; at least one is present.
    assert body.count("- ") >= 3


def test_get_intake_path_accepts_canonical_id(tmp_path, monkeypatch) -> None:
    """get_intake_path returns the expected .md path for canonical intake IDs."""
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)
    p = vi.get_intake_path("A014_20260422T153200Z")
    assert p.name == "A014_20260422T153200Z.md"
    assert p.parent == tmp_path


@pytest.mark.parametrize(
    "bad_id",
    [
        "not-a-valid-id",
        "a014_20260422T153200Z",  # lowercase tag
        "A014_INVALIDSTAMP",
        "../../etc/passwd",
        "A014_20260422T153200",  # missing trailing Z
    ],
)
def test_get_intake_path_rejects_non_canonical_id(
    tmp_path,
    monkeypatch,
    bad_id: str,
) -> None:
    """Non-canonical intake IDs raise ValueError (HTTP 400 upstream)."""
    from skyherd.server import vet_intake as vi

    monkeypatch.setattr(vi, "_VET_INTAKE_DIR", tmp_path)
    with pytest.raises(ValueError):
        vi.get_intake_path(bad_id)


def test_render_markdown_handles_missing_signals_and_cow_fields() -> None:
    """Internal _render_markdown tolerates minimal inputs (missing bcs / signals)."""
    from datetime import UTC, datetime

    from skyherd.server import vet_intake as vi

    ts = datetime(2026, 4, 22, 15, 32, 0, tzinfo=UTC)
    body = vi._render_markdown(
        intake_id="A014_20260422T153200Z",
        cow_tag="A014",
        severity="log",
        disease="pinkeye",
        signals=[],  # empty signals
        cow_snapshot={},  # missing bcs + health_score
        session_id="sess_test",
        herd_context="",
        ts=ts,
        attest_seq=None,
        signals_structured=[],
    )
    assert "(none recorded)" in body
    assert "N/A" in body  # bcs / health_score fall back to "N/A"
    assert "(not yet recorded)" in body  # attest_seq None
