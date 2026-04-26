"""Tests for scripts/openmontage_to_remotion.py — EDL → Remotion props translator.

TDD-first per project rules. Fixtures are MIT-clean (hand-authored to match the
OpenMontage edit_decisions.json schema; no AGPL-tainted content imported).
"""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

import pytest

# Make scripts/ importable without modifying pyproject's pytest pythonpath
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.openmontage_to_remotion import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    EdlPathOutsideRepo,
    EdlWrongRuntime,
    load_edl,
    main,
    to_remotion,
    validate_edl,
)

FIXTURE = ROOT / "tests" / "fixtures" / "openmontage" / "minimal-edl.json"


def _minimal_valid_edl() -> dict[str, Any]:
    return {
        "version": "1.0",
        "render_runtime": "remotion",
        "cuts": [
            {
                "id": "c1",
                "source": "",
                "in_seconds": 0.0,
                "out_seconds": 3.5,
                "type": "hero_title",
            },
        ],
    }


def test_load_edl_reads_json_fixture() -> None:
    if not FIXTURE.exists():
        pytest.skip(f"fixture missing: {FIXTURE}")
    data = load_edl(FIXTURE)
    assert isinstance(data, dict)
    assert "cuts" in data and len(data["cuts"]) >= 1


def test_validate_edl_accepts_minimal_valid_doc() -> None:
    assert validate_edl(_minimal_valid_edl()) == []


def test_validate_edl_rejects_missing_version() -> None:
    edl = _minimal_valid_edl()
    edl["version"] = "0.9"
    assert any("version" in err for err in validate_edl(edl))


def test_validate_edl_rejects_empty_cuts() -> None:
    edl = _minimal_valid_edl()
    edl["cuts"] = []
    assert any("cuts" in err for err in validate_edl(edl))


def test_validate_edl_rejects_wrong_render_runtime() -> None:
    for runtime in ("hyperframes", "ffmpeg"):
        edl = _minimal_valid_edl()
        edl["render_runtime"] = runtime
        assert any("render_runtime" in err for err in validate_edl(edl))


def test_to_remotion_converts_seconds_to_frames_at_60fps() -> None:
    edl = _minimal_valid_edl()
    edl["cuts"][0]["in_seconds"] = 3.5
    edl["cuts"][0]["out_seconds"] = 3.5
    out = to_remotion(edl, fps=60)
    assert out["sequences"][0]["fromFrame"] == 210
    assert out["fps"] == 60


def test_to_remotion_passes_through_synthetic_scene_components() -> None:
    out = to_remotion(_minimal_valid_edl(), fps=60)
    assert out["sequences"][0]["asset"] == {"kind": "scene-component"}


def test_to_remotion_keeps_relative_asset_paths() -> None:
    edl = _minimal_valid_edl()
    edl["cuts"][0]["source"] = "remotion-video/public/clips/coyote.mp4"
    out = to_remotion(edl, fps=60)
    assert out["sequences"][0]["asset"] == {
        "kind": "asset",
        "path": "remotion-video/public/clips/coyote.mp4",
    }


def test_to_remotion_raises_for_paths_outside_repo() -> None:
    edl = _minimal_valid_edl()
    edl["cuts"][0]["source"] = "/etc/passwd"
    with pytest.raises(EdlPathOutsideRepo):
        to_remotion(edl, fps=60)


def test_to_remotion_raises_for_wrong_runtime() -> None:
    edl = _minimal_valid_edl()
    edl["render_runtime"] = "hyperframes"
    with pytest.raises(EdlWrongRuntime):
        to_remotion(edl, fps=60)


def test_to_remotion_defaults_missing_transitions_to_cut_zero_frames() -> None:
    out = to_remotion(_minimal_valid_edl(), fps=60)
    seq = out["sequences"][0]
    assert seq["transition"] == "cut"
    assert seq["transitionDurationFrames"] == 0


def test_to_remotion_sorts_out_of_order_cuts_by_in_seconds() -> None:
    edl = _minimal_valid_edl()
    edl["cuts"] = [
        {"id": "second", "source": "", "in_seconds": 5.0, "out_seconds": 7.0},
        {"id": "first", "source": "", "in_seconds": 0.0, "out_seconds": 5.0},
    ]
    out = to_remotion(edl, fps=60)
    assert [s["id"] for s in out["sequences"]] == ["first", "second"]


def test_to_remotion_handles_missing_audio_block() -> None:
    out = to_remotion(_minimal_valid_edl(), fps=60)
    assert out["audio"]["narrationSegments"] == []
    assert out["audio"]["sfx"] == []
    assert out["audio"]["music"] is None


def test_to_remotion_preserves_extra_cut_metadata() -> None:
    edl = _minimal_valid_edl()
    edl["cuts"][0]["type"] = "hero_title"
    edl["cuts"][0]["custom_field"] = "value"
    out = to_remotion(edl, fps=60)
    md = out["sequences"][0]["metadata"]
    assert md["type"] == "hero_title"
    assert md["custom_field"] == "value"


def test_main_writes_output_json_and_returns_zero_on_success(tmp_path) -> None:
    src = tmp_path / "edl.json"
    dst = tmp_path / "remotion.json"
    src.write_text(json.dumps(_minimal_valid_edl()))
    rc = main(str(src), str(dst))
    assert rc == 0
    payload = json.loads(dst.read_text())
    assert payload["fps"] == 60
    assert payload["metadata"]["sourceTool"] == "openmontage"


def test_main_returns_2_on_validation_error(tmp_path) -> None:
    bad = _minimal_valid_edl()
    bad["render_runtime"] = "hyperframes"
    src = tmp_path / "bad.json"
    dst = tmp_path / "out.json"
    src.write_text(json.dumps(bad))
    rc = main(str(src), str(dst))
    assert rc == 2
    assert not dst.exists()


def test_main_returns_1_on_missing_input(tmp_path) -> None:
    rc = main(str(tmp_path / "nope.json"), str(tmp_path / "out.json"))
    assert rc == 1
