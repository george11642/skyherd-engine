"""TDD tests for to_broll_track() — EDL → BrollCut[] translator.

Written BEFORE implementation per project TDD rules.
Frame-accurate assertions pin fps=30 (Remotion comp rate).
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.openmontage_to_remotion import (  # noqa: E402
    to_broll_track,
)

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _asset_cut(
    id_: str,
    source: str,
    in_s: float,
    out_s: float,
    transition: str = "cut",
    transition_duration: float = 0.0,
    reason: str = "",
) -> dict[str, Any]:
    cut: dict[str, Any] = {
        "id": id_,
        "source": source,
        "in_seconds": in_s,
        "out_seconds": out_s,
        "transition_in": transition,
        "transition_in_duration": transition_duration,
    }
    if reason:
        cut["reason"] = reason
    return cut


def _scene_cut(id_: str, in_s: float, out_s: float) -> dict[str, Any]:
    return _asset_cut(id_, "", in_s, out_s)


def _minimal_edl(cuts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": "1.0",
        "render_runtime": "remotion",
        "cuts": cuts,
    }


# ---------------------------------------------------------------------------
# Basic behaviour
# ---------------------------------------------------------------------------


def test_to_broll_track_returns_dict_with_cuts_key() -> None:
    edl = _minimal_edl(
        [
            _asset_cut("c1", "remotion-video/public/broll/t1-cattle-grazing-wide.mp4", 6.0, 22.0),
        ]
    )
    result = to_broll_track(edl, fps=30)
    assert isinstance(result, dict)
    assert "cuts" in result


def test_to_broll_track_filters_out_scene_components() -> None:
    """scene-component entries (empty source) must NOT appear in broll track."""
    edl = _minimal_edl(
        [
            _scene_cut("cold-open", 0.0, 6.0),
            _asset_cut(
                "broll", "remotion-video/public/broll/t1-cattle-grazing-wide.mp4", 6.0, 22.0
            ),
            _scene_cut("mesh-reveal", 115.0, 150.0),
        ]
    )
    result = to_broll_track(edl, fps=30)
    assert len(result["cuts"]) == 1
    assert result["cuts"][0]["src"] == "broll/t1-cattle-grazing-wide.mp4"


def test_to_broll_track_includes_only_asset_kind_cuts() -> None:
    """Verify that all returned cuts originate from asset entries."""
    edl = _minimal_edl(
        [
            _scene_cut("s1", 0.0, 8.0),
            _asset_cut("a1", "remotion-video/public/broll/t1-dawn-corral-golden.mp4", 8.0, 20.0),
            _asset_cut("a2", "remotion-video/public/broll/t1-cattle-grazing-wide.mp4", 20.0, 28.0),
            _scene_cut("s2", 100.0, 120.0),
        ]
    )
    result = to_broll_track(edl, fps=30)
    assert len(result["cuts"]) == 2


# ---------------------------------------------------------------------------
# Frame-accurate first-cut assertion (fps=30, pinned)
# ---------------------------------------------------------------------------


def test_to_broll_track_frame_accurate_first_cut_at_30fps() -> None:
    """EDL cut starting at 6.0s must have startSeconds=6.0 and endSeconds=22.0.

    Frame check: 6.0 * 30 = 180 frames, 22.0 * 30 = 660 frames.
    The track stores seconds (Remotion handles frame conversion); validate
    that the seconds are preserved exactly so Remotion sees correct frames.
    """
    edl = _minimal_edl(
        [
            _asset_cut(
                "a1-dawn",
                "remotion-video/public/broll/t1-dawn-corral-golden.mp4",
                6.0,
                22.0,
                transition="fade",
                transition_duration=1.5,
            ),
        ]
    )
    result = to_broll_track(edl, fps=30)
    cut = result["cuts"][0]
    assert cut["startSeconds"] == pytest.approx(6.0)
    assert cut["endSeconds"] == pytest.approx(22.0)
    # Frame check: startSeconds * fps must equal integer frame count
    assert round(cut["startSeconds"] * 30) == 180
    assert round(cut["endSeconds"] * 30) == 660


# ---------------------------------------------------------------------------
# EDL fps conversion: source EDL may use 24/60fps editorial timecodes
# The translator must re-pin to 30fps output regardless of source fps.
# ---------------------------------------------------------------------------


def test_to_broll_track_output_fps_is_always_30() -> None:
    """Even if called with explicit fps arg, output seconds must be exact."""
    edl = _minimal_edl(
        [
            _asset_cut("a1", "remotion-video/public/broll/t1-cattle-grazing-wide.mp4", 22.0, 30.0),
        ]
    )
    result_30 = to_broll_track(edl, fps=30)
    result_60 = to_broll_track(edl, fps=60)
    # Both should produce the same startSeconds / endSeconds regardless of fps param
    # (seconds are EDL-native; fps is only used internally for frame resolution)
    assert result_30["cuts"][0]["startSeconds"] == pytest.approx(22.0)
    assert result_60["cuts"][0]["startSeconds"] == pytest.approx(22.0)


def test_to_broll_track_frame_accurate_30fps_vs_24fps_source() -> None:
    """Verify frame-level accuracy when EDL times are 24fps-aligned.

    24fps timecode: frame 144 = 6.0s exactly (144/24). At 30fps target:
    6.0 * 30 = 180 frames. The translator preserves seconds, so both rates
    produce frame 180 at 30fps.
    """
    edl = _minimal_edl(
        [
            _asset_cut("a1", "remotion-video/public/broll/t1-cattle-grazing-wide.mp4", 6.0, 22.0),
        ]
    )
    result = to_broll_track(edl, fps=30)
    cut = result["cuts"][0]
    # 6.0s at 30fps = frame 180 (exact, no rounding needed)
    assert round(cut["startSeconds"] * 30) == 180
    # 22.0s at 30fps = frame 660
    assert round(cut["endSeconds"] * 30) == 660


# ---------------------------------------------------------------------------
# src path stripping: remotion-video/public/ prefix must be stripped
# ---------------------------------------------------------------------------


def test_to_broll_track_strips_remotion_public_prefix() -> None:
    edl = _minimal_edl(
        [
            _asset_cut("a1", "remotion-video/public/broll/t1-cattle-grazing-wide.mp4", 22.0, 30.0),
        ]
    )
    result = to_broll_track(edl, fps=30)
    assert result["cuts"][0]["src"] == "broll/t1-cattle-grazing-wide.mp4"


def test_to_broll_track_keeps_other_asset_paths_as_is() -> None:
    """Non-broll assets (clips/) that pass filter keep their path."""
    edl = _minimal_edl(
        [
            _asset_cut("a1", "remotion-video/public/clips/coyote.mp4", 0.0, 5.0),
        ]
    )
    result = to_broll_track(edl, fps=30)
    assert result["cuts"][0]["src"] == "clips/coyote.mp4"


# ---------------------------------------------------------------------------
# Transition field forwarding
# ---------------------------------------------------------------------------


def test_to_broll_track_forwards_transition_and_duration() -> None:
    edl = _minimal_edl(
        [
            _asset_cut(
                "a1",
                "remotion-video/public/broll/t1-dawn-corral-golden.mp4",
                6.0,
                22.0,
                transition="fade",
                transition_duration=1.5,
            ),
        ]
    )
    result = to_broll_track(edl, fps=30)
    cut = result["cuts"][0]
    assert cut["transition"] == "fade"
    assert cut["transitionDurationFrames"] == round(1.5 * 30)


def test_to_broll_track_defaults_missing_transition_to_cut_zero_frames() -> None:
    edl = _minimal_edl(
        [
            _asset_cut("a1", "remotion-video/public/broll/t1-cattle-grazing-wide.mp4", 22.0, 30.0),
        ]
    )
    result = to_broll_track(edl, fps=30)
    cut = result["cuts"][0]
    assert cut["transition"] == "cut"
    assert cut["transitionDurationFrames"] == 0


# ---------------------------------------------------------------------------
# reason field forwarding
# ---------------------------------------------------------------------------


def test_to_broll_track_forwards_reason_field_when_present() -> None:
    edl = _minimal_edl(
        [
            _asset_cut(
                "a1",
                "remotion-video/public/broll/t1-cattle-grazing-wide.mp4",
                22.0,
                30.0,
                reason="Market context cut 1",
            ),
        ]
    )
    result = to_broll_track(edl, fps=30)
    assert result["cuts"][0]["reason"] == "Market context cut 1"


def test_to_broll_track_omits_reason_when_absent() -> None:
    edl = _minimal_edl(
        [
            _asset_cut("a1", "remotion-video/public/broll/t1-cattle-grazing-wide.mp4", 22.0, 30.0),
        ]
    )
    result = to_broll_track(edl, fps=30)
    assert "reason" not in result["cuts"][0]


# ---------------------------------------------------------------------------
# Empty broll (all scene-component cuts)
# ---------------------------------------------------------------------------


def test_to_broll_track_returns_empty_cuts_list_when_no_assets() -> None:
    edl = _minimal_edl(
        [
            _scene_cut("s1", 0.0, 60.0),
            _scene_cut("s2", 60.0, 120.0),
        ]
    )
    result = to_broll_track(edl, fps=30)
    assert result["cuts"] == []


# ---------------------------------------------------------------------------
# Real EDL smoke test — parse actual docs/edl/openmontage-cuts-A-cinematic.json
# ---------------------------------------------------------------------------

EDL_A = ROOT / "docs" / "edl" / "openmontage-cuts-A-cinematic.json"


@pytest.mark.skipif(not EDL_A.exists(), reason="EDL A not found")
def test_to_broll_track_parses_edl_a_real_file() -> None:
    import json

    edl = json.loads(EDL_A.read_text())
    result = to_broll_track(edl, fps=30)
    # EDL A has these broll assets (filtered out: scene-components a1-cold-open-black,
    # a2-mesh-reveal, a3-wordmark-isometric; also a1-bridge uses clips/ not broll/)
    broll_srcs = [c["src"] for c in result["cuts"]]
    assert "broll/t1-dawn-corral-golden.mp4" in broll_srcs
    assert "broll/t1-cattle-grazing-wide.mp4" in broll_srcs
    assert "broll/t1-drone-rangeland-aerial.mp4" in broll_srcs
    # Scene-component entries must NOT be included
    for c in result["cuts"]:
        assert c["src"] != ""
    # First broll cut is the dawn-corral at 6.0s
    dawn_cut = next(c for c in result["cuts"] if "dawn-corral" in c["src"])
    assert dawn_cut["startSeconds"] == pytest.approx(6.0)
    assert dawn_cut["endSeconds"] == pytest.approx(22.0)
    # Frame check at 30fps
    assert round(dawn_cut["startSeconds"] * 30) == 180
