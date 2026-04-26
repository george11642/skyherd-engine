"""Tests for the sick_cow scenario."""

from __future__ import annotations


class TestSickCowScenario:
    def test_name_and_description(self) -> None:
        from skyherd.scenarios.sick_cow import SickCowScenario

        s = SickCowScenario()
        assert s.name == "sick_cow"
        assert "pinkeye" in s.description.lower() or "a014" in s.description.lower()

    def test_setup_stamps_a014(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.sick_cow import SickCowScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = SickCowScenario()
        s.setup(world)
        a014 = next((c for c in world.herd.cows if c.tag == "A014"), None)
        assert a014 is not None
        assert a014.ocular_discharge >= 0.7
        assert "pinkeye" in a014.disease_flags

    def test_setup_does_not_affect_other_cows(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.sick_cow import SickCowScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = SickCowScenario()
        s.setup(world)
        # A001 should be unaffected
        a001 = next((c for c in world.herd.cows if c.tag == "A001"), None)
        assert a001 is not None
        assert a001.ocular_discharge == 0.0

    def test_health_check_injected_at_threshold(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.sick_cow import _HEALTH_CHECK_AT_S, SickCowScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = SickCowScenario()
        s.setup(world)
        events = s.inject_events(world, _HEALTH_CHECK_AT_S + 1.0)
        types = [e["type"] for e in events]
        assert "camera.motion" in types
        assert "health.check" in types

    def test_health_check_has_correct_cow_tag(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.sick_cow import _HEALTH_CHECK_AT_S, SickCowScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = SickCowScenario()
        s.setup(world)
        events = s.inject_events(world, _HEALTH_CHECK_AT_S + 1.0)
        health_ev = next((e for e in events if e["type"] == "health.check"), None)
        assert health_ev is not None
        assert health_ev["cow_tag"] == "A014"
        assert "pinkeye" in health_ev["disease_flags"]

    def test_full_run_passes(self) -> None:
        from skyherd.scenarios import run

        result = run("sick_cow", seed=42)
        assert result.outcome_passed, f"sick_cow scenario failed: {result.outcome_error}"

    def test_full_run_has_health_check_event(self) -> None:
        from skyherd.scenarios import run

        result = run("sick_cow", seed=42)
        hc = next((e for e in result.event_stream if e.get("type") == "health.check"), None)
        assert hc is not None
        assert hc.get("cow_tag") == "A014"

    # ------------------------------------------------------------------
    # SCEN-01 + DASH-06 vet-intake assertions (Phase 5, Plan 05-02)
    # ------------------------------------------------------------------

    def _all_tool_calls_from_result(self, result) -> list:  # type: ignore[no-untyped-def]
        """Flatten all tool calls from a ScenarioResult into a single list."""
        out = []
        for calls in result.agent_tool_calls.values():
            out.extend(calls)
        return out

    def test_sick_cow_draft_vet_intake_tool_call(self) -> None:
        """SCEN-01: sick_cow scenario invokes draft_vet_intake as a tool call."""
        from skyherd.scenarios import run

        result = run("sick_cow", seed=42)
        assert result.outcome_passed, result.outcome_error
        tool_names = {c.get("tool") for c in self._all_tool_calls_from_result(result)}
        assert "draft_vet_intake" in tool_names, (
            f"Expected draft_vet_intake tool call. Got: {tool_names}"
        )

    def test_sick_cow_produces_vet_intake_artifact(self) -> None:
        """SCEN-01: sick_cow scenario writes runtime/vet_intake/A014_*.md."""
        from pathlib import Path

        from skyherd.scenarios import run

        intake_dir = Path("runtime/vet_intake")
        # Clear any pre-existing A014_*.md to make the assertion deterministic
        if intake_dir.exists():
            for f in intake_dir.glob("A014_*.md"):
                f.unlink()
        result = run("sick_cow", seed=42)
        assert result.outcome_passed, result.outcome_error
        files = sorted(intake_dir.glob("A014_*.md"))
        assert files, "Expected at least one runtime/vet_intake/A014_*.md, got none"
        content = files[0].read_text(encoding="utf-8")
        assert "pinkeye" in content.lower(), "Intake must mention pinkeye"
        assert "A014" in content
        assert "ESCALATE" in content.upper()

    def test_sick_cow_vet_intake_treatment_guidance(self) -> None:
        """SCEN-01: intake surfaces concrete treatment guidance from pinkeye.md."""
        from pathlib import Path

        intake_dir = Path("runtime/vet_intake")
        files = sorted(intake_dir.glob("A014_*.md"))
        if not files:
            # Run scenario first if artifact not present
            from skyherd.scenarios import run

            if intake_dir.exists():
                for f in intake_dir.glob("A014_*.md"):
                    f.unlink()
            run("sick_cow", seed=42)
            files = sorted(intake_dir.glob("A014_*.md"))
        assert files, "Expected runtime/vet_intake/A014_*.md — run sick_cow scenario first"
        content = files[0].read_text(encoding="utf-8").lower()
        treatment_keywords = ["oxytetracycline", "antibiotic", "uv", "patch", "eye"]
        assert any(kw in content for kw in treatment_keywords), (
            f"Expected treatment guidance in vet intake; content:\n{content[:400]}"
        )

    def test_vet_intake_surfaces_pixel_detection_bbox(self) -> None:
        """DASH-06: Phase 2 VIS-05 DetectionResult.bbox propagates through signals_structured
        into the vet-intake packet — the data source Plan 05-03 renders as a bounding-box chip.
        """
        import re

        import pytest

        # Phase 2 VIS-05 prerequisite — skip gracefully if upstream phase has not landed
        try:
            from skyherd.vision.types import DetectionResult  # noqa: F401

            from skyherd.vision.heads.pinkeye import Pinkeye  # noqa: F401

            # Verify bbox field exists on DetectionResult
            if (
                not hasattr(DetectionResult, "model_fields")
                or "bbox" not in DetectionResult.model_fields
            ):
                pytest.skip("VIS-05 prerequisite — DetectionResult.bbox not yet defined")
        except ImportError as exc:
            pytest.skip(f"VIS-05 prerequisite — Phase 2 pixel head required: {exc}")

        from pathlib import Path

        from skyherd.scenarios import run

        intake_dir = Path("runtime/vet_intake")
        if intake_dir.exists():
            for f in intake_dir.glob("A014_*.md"):
                f.unlink()

        result = run("sick_cow", seed=42)
        assert result.outcome_passed, result.outcome_error

        # Approach A: via the tool-call output
        tool_calls = self._all_tool_calls_from_result(result)
        drafts = [c for c in tool_calls if c.get("tool") == "draft_vet_intake"]
        assert drafts, "draft_vet_intake tool call missing — SCEN-01 tests should flag this first"

        output = drafts[0].get("output", {})
        if isinstance(output, dict):
            structured = output.get("signals_structured", [])
        else:
            structured = []
        pixel_signals = [
            s
            for s in structured
            if (s.get("kind") if isinstance(s, dict) else getattr(s, "kind", None))
            == "pixel_detection"
        ]

        # Approach B fallback: parse the markdown body if tool_call output is opaque
        if not pixel_signals:
            files = sorted(intake_dir.glob("A014_*.md"))
            assert files, "No A014_*.md written — cannot verify bbox propagation"
            body = files[0].read_text(encoding="utf-8")
            assert "pixel_detection" in body or "Pixel Detection" in body, (
                f"DASH-06: expected 'pixel_detection' marker in vet-intake markdown. "
                f"Body head:\n{body[:400]}"
            )
            bbox_match = re.search(r"\[\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\]", body)
            assert bbox_match, "DASH-06: no [x0,y0,x1,y1] bbox in markdown body"
            return

        # Approach A: verify the first pixel_detection signal's shape
        sig = pixel_signals[0]
        if hasattr(sig, "model_dump"):
            sig = sig.model_dump()
        assert sig.get("head") == "pinkeye", f"Expected head=pinkeye, got {sig.get('head')}"
        bbox = sig.get("bbox")
        assert bbox is not None, "DASH-06: bbox is None — pixel path did not propagate"
        assert len(bbox) == 4, f"DASH-06: bbox must be 4 ints, got {bbox}"
        for v in bbox:
            assert isinstance(v, int) or float(v).is_integer(), f"bbox coord not int: {v}"
        conf = sig.get("confidence", -1.0)
        assert 0.0 <= float(conf) <= 1.0, f"DASH-06: confidence out of [0,1]: {conf}"


def test_pinkeye_bbox_flows_through_classify_pipeline(
    sick_pinkeye_world,  # type: ignore[no-untyped-def]
    tmp_path,
) -> None:
    """ClassifyPipeline on a pinkeye-positive world yields a pinkeye detection with real bbox.

    Branch B: uses sick_pinkeye_world fixture (discharge=0.85, disease_flags={'pinkeye'}).
    The sick_cow scenario's A014 has discharge=0.7, which the MobileNetV3-Small model
    classifies as class 0 (healthy) due to the binary-class-ceiling (model reliably predicts
    class 3/escalate only at discharge>=0.8). Branch B uses discharge=0.85 which reliably
    triggers the pixel path's class 3 output.

    Asserts at least one DetectionResult has head_name='pinkeye', bbox is not None,
    and bbox coords are within frame bounds (0<=x0<x1<=640, 0<=y0<y1<=480).
    """
    from skyherd.vision.pipeline import ClassifyPipeline

    pipeline = ClassifyPipeline()
    result = pipeline.run(sick_pinkeye_world, "trough_a", out_dir=tmp_path)

    pinkeye_dets = [d for d in result.detections if d.head_name == "pinkeye"]
    assert pinkeye_dets, (
        "ClassifyPipeline produced no pinkeye detections on a positive world; "
        f"all detections: {[d.head_name for d in result.detections]}"
    )
    bbox_dets = [d for d in pinkeye_dets if d.bbox is not None]
    assert bbox_dets, "pinkeye detections have no bbox — pixel path did not engage"
    for d in bbox_dets:
        x0, y0, x1, y1 = d.bbox  # type: ignore[misc]
        assert 0 <= x0 < x1 <= 640, f"invalid x coords in bbox: {d.bbox}"
        assert 0 <= y0 < y1 <= 480, f"invalid y coords in bbox: {d.bbox}"
