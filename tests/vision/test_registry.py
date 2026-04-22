"""Registry classify() gate regression tests — H5.

Verifies that:
- should_evaluate() gates fire correctly (healthy cows produce no detections)
- 500-cow herd with exactly 3 sick cows produces exactly the expected detections
  without false positives from the 497 healthy cows.
"""

from __future__ import annotations

from skyherd.vision.registry import classify
from skyherd.world.cattle import Cow

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _healthy_cow(tag: str, idx: int = 0) -> Cow:
    return Cow(
        id=f"cow_{tag}",
        tag=tag,
        pos=(float(50 + idx * 10), 300.0),
        health_score=1.0,
        lameness_score=0,
        ocular_discharge=0.0,
        bcs=5.5,
        disease_flags=set(),
        pregnancy_days_remaining=None,
    )


def _sick_cow(tag: str) -> Cow:
    """Sick cow that should trigger pinkeye, foot_rot, brd, heat_stress, bcs heads."""
    return Cow(
        id=f"cow_{tag}",
        tag=tag,
        pos=(300.0, 300.0),
        health_score=0.25,
        lameness_score=4,
        ocular_discharge=0.9,
        bcs=2.5,
        disease_flags={"respiratory"},
        pregnancy_days_remaining=None,
    )


_FRAME_META_HOT: dict = {"temp_f": 100.0, "respiration_bpm": 70, "trough_id": "trough_a"}
_FRAME_META_NORMAL: dict = {"temp_f": 72.0, "respiration_bpm": 20, "trough_id": "trough_a"}


# ---------------------------------------------------------------------------
# Gate correctness — unit level
# ---------------------------------------------------------------------------


def test_healthy_cow_produces_no_detections() -> None:
    """A fully healthy cow yields zero detections from all heads."""
    cow = _healthy_cow("HLTH01")
    results = classify(cow, _FRAME_META_NORMAL)
    assert results == [], f"Expected no detections for healthy cow, got {results}"


def test_sick_cow_produces_detections() -> None:
    """A severely sick cow yields at least one detection."""
    cow = _sick_cow("SICK01")
    results = classify(cow, _FRAME_META_HOT)
    assert len(results) >= 1, "Expected at least one detection for sick cow"


# ---------------------------------------------------------------------------
# H5 regression — 500-cow herd, 3 sick → no false positives from 497 healthy
# ---------------------------------------------------------------------------


def test_large_herd_no_false_positives_from_healthy_cows() -> None:
    """497 healthy cows produce zero detections — should_evaluate gate prevents O(N×heads) work.

    This is the H5 regression: gate short-circuits healthy cows so classify()
    is never called unnecessarily.
    """
    healthy_cows = [_healthy_cow(f"H{i:04d}", i) for i in range(497)]
    total_detections = 0
    for cow in healthy_cows:
        total_detections += len(classify(cow, _FRAME_META_NORMAL))
    assert total_detections == 0, (
        f"Expected 0 detections across 497 healthy cows, got {total_detections}"
    )


def test_large_herd_exactly_three_sick_cows_detected() -> None:
    """500-cow herd: 497 healthy + 3 sick → detections come from exactly those 3 cows (H5)."""
    healthy_tags = {f"H{i:04d}" for i in range(497)}
    sick_tags = {"S001", "S002", "S003"}

    detection_tags: set[str] = set()
    for i, tag in enumerate(healthy_tags):
        results = classify(_healthy_cow(tag, i), _FRAME_META_NORMAL)
        for r in results:
            detection_tags.add(r.cow_tag)

    for tag in sick_tags:
        results = classify(_sick_cow(tag), _FRAME_META_HOT)
        for r in results:
            detection_tags.add(r.cow_tag)

    # All 3 sick cows must appear in detections
    for tag in sick_tags:
        assert tag in detection_tags, f"Sick cow {tag} was not detected"

    # No healthy cow should appear
    false_positives = detection_tags & healthy_tags
    assert not false_positives, f"False positive detections for healthy cows: {false_positives}"


def test_should_evaluate_gate_skips_healthy_bcs() -> None:
    """BCS head skips cows with BCS in 4.0–6.5 (fast reject path)."""
    from skyherd.vision.heads.bcs import BCS

    head = BCS()
    cow = _healthy_cow("BCS_OK")  # bcs=5.5, in safe window
    assert not head.should_evaluate(cow, {}), "BCS gate should reject bcs=5.5"


def test_should_evaluate_gate_passes_emaciated_bcs() -> None:
    """BCS head passes through cows with BCS below 4.0."""
    from skyherd.vision.heads.bcs import BCS

    head = BCS()
    cow = _sick_cow("BCS_BAD")  # bcs=2.5
    assert head.should_evaluate(cow, {}), "BCS gate should pass bcs=2.5"


def test_should_evaluate_gate_skips_healthy_brd() -> None:
    """BRD head skips cows with health_score >= 0.6 and no respiratory signal."""
    from skyherd.vision.heads.brd import BRD

    head = BRD()
    cow = _healthy_cow("BRD_OK")
    assert not head.should_evaluate(cow, _FRAME_META_NORMAL), "BRD gate should reject healthy cow"


def test_should_evaluate_gate_passes_sick_brd() -> None:
    """BRD head passes cows with health_score < 0.6 and respiratory flag."""
    from skyherd.vision.heads.brd import BRD

    head = BRD()
    cow = _sick_cow("BRD_BAD")
    assert head.should_evaluate(cow, _FRAME_META_NORMAL), "BRD gate should pass sick cow"
