"""Tests for :mod:`skyherd.drone.mission_schema`.

Target coverage ≥ 85 %.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from skyherd.drone.interface import Waypoint
from skyherd.drone.mission_schema import (
    SCHEMA_VERSION,
    FailoverHint,
    MissionMetadata,
    MissionV1,
)

# ---------------------------------------------------------------------------
# Basic round-trip + version pin
# ---------------------------------------------------------------------------


def test_schema_version_constant_is_1() -> None:
    assert SCHEMA_VERSION == 1


def test_missionv1_round_trip() -> None:
    mission = MissionV1(
        metadata=MissionMetadata(mission_id="m1", ranch_id="ranch_a"),
        waypoints=[Waypoint(lat=34.1, lon=-106.1, alt_m=30.0)],
    )
    wire = mission.to_wire()
    rebuilt = MissionV1.from_wire(wire)
    assert rebuilt == mission


def test_missionv1_version_literal_rejects_other_versions() -> None:
    with pytest.raises(ValidationError):
        MissionV1.model_validate(
            {
                "version": 2,
                "metadata": {"mission_id": "m1", "ranch_id": "r1"},
                "waypoints": [{"lat": 34.1, "lon": -106.1, "alt_m": 30.0}],
            }
        )


def test_missionv1_extra_allow_forward_compat() -> None:
    """Top-level unknown fields accepted so older readers can parse v1.x payloads."""
    mission = MissionV1.model_validate(
        {
            "version": 1,
            "metadata": {"mission_id": "m1", "ranch_id": "r1"},
            "waypoints": [{"lat": 0.0, "lon": 0.0, "alt_m": 5.0}],
            "future_field": "hello",
            "nested_future": {"a": 1},
        }
    )
    # Parsed cleanly; the extra fields survive (model_dump includes them).
    dumped = mission.model_dump()
    assert dumped["future_field"] == "hello"
    assert dumped["nested_future"] == {"a": 1}


# ---------------------------------------------------------------------------
# Waypoint bounds
# ---------------------------------------------------------------------------


def test_missionv1_requires_at_least_one_waypoint() -> None:
    with pytest.raises(ValidationError):
        MissionV1(
            metadata=MissionMetadata(mission_id="m1", ranch_id="r1"),
            waypoints=[],
        )


def test_missionv1_rejects_more_than_64_waypoints() -> None:
    wps = [Waypoint(lat=0.0, lon=0.0, alt_m=5.0) for _ in range(65)]
    with pytest.raises(ValidationError):
        MissionV1(
            metadata=MissionMetadata(mission_id="m1", ranch_id="r1"),
            waypoints=wps,
        )


def test_missionv1_serialises_waypoints_in_order() -> None:
    wps = [
        Waypoint(lat=1.0, lon=2.0, alt_m=3.0),
        Waypoint(lat=4.0, lon=5.0, alt_m=6.0),
        Waypoint(lat=7.0, lon=8.0, alt_m=9.0),
    ]
    mission = MissionV1(
        metadata=MissionMetadata(mission_id="m1", ranch_id="r1"),
        waypoints=wps,
    )
    wire = mission.to_wire()
    assert wire["waypoints"] == [
        {"lat": 1.0, "lon": 2.0, "alt_m": 3.0, "hold_s": 0.0},
        {"lat": 4.0, "lon": 5.0, "alt_m": 6.0, "hold_s": 0.0},
        {"lat": 7.0, "lon": 8.0, "alt_m": 9.0, "hold_s": 0.0},
    ]


# ---------------------------------------------------------------------------
# Deterrent bounds
# ---------------------------------------------------------------------------


def test_missionv1_deterrent_hz_lower_bound() -> None:
    with pytest.raises(ValidationError):
        MissionV1(
            metadata=MissionMetadata(mission_id="m1", ranch_id="r1"),
            waypoints=[Waypoint(lat=0, lon=0, alt_m=5.0)],
            deterrent_tone_hz=100,  # below 500 floor
        )


def test_missionv1_deterrent_hz_upper_bound() -> None:
    with pytest.raises(ValidationError):
        MissionV1(
            metadata=MissionMetadata(mission_id="m1", ranch_id="r1"),
            waypoints=[Waypoint(lat=0, lon=0, alt_m=5.0)],
            deterrent_tone_hz=30_000,  # above 20 kHz ceiling
        )


def test_missionv1_deterrent_duration_bounds() -> None:
    with pytest.raises(ValidationError):
        MissionV1(
            metadata=MissionMetadata(mission_id="m1", ranch_id="r1"),
            waypoints=[Waypoint(lat=0, lon=0, alt_m=5.0)],
            deterrent_duration_s=-1.0,
        )
    with pytest.raises(ValidationError):
        MissionV1(
            metadata=MissionMetadata(mission_id="m1", ranch_id="r1"),
            waypoints=[Waypoint(lat=0, lon=0, alt_m=5.0)],
            deterrent_duration_s=120.0,
        )


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_metadata_mission_id_min_length() -> None:
    with pytest.raises(ValidationError):
        MissionMetadata(mission_id="", ranch_id="r1")


def test_metadata_ranch_id_min_length() -> None:
    with pytest.raises(ValidationError):
        MissionMetadata(mission_id="m1", ranch_id="")


def test_metadata_battery_floor_bounds() -> None:
    with pytest.raises(ValidationError):
        MissionMetadata(mission_id="m1", ranch_id="r1", battery_floor_pct=-5.0)
    with pytest.raises(ValidationError):
        MissionMetadata(mission_id="m1", ranch_id="r1", battery_floor_pct=150.0)


def test_metadata_wind_kt_bounds() -> None:
    with pytest.raises(ValidationError):
        MissionMetadata(mission_id="m1", ranch_id="r1", wind_kt=-1.0)
    with pytest.raises(ValidationError):
        MissionMetadata(mission_id="m1", ranch_id="r1", wind_kt=200.0)


# ---------------------------------------------------------------------------
# FailoverHint
# ---------------------------------------------------------------------------


def test_failover_hint_defaults() -> None:
    hint = FailoverHint()
    assert hint.preferred_leg == "auto"
    assert hint.retry_on_other_leg is True
    assert hint.retry_budget == 1


def test_failover_hint_rejects_unknown_leg() -> None:
    with pytest.raises(ValidationError):
        FailoverHint(preferred_leg="magic")  # type: ignore[arg-type]


def test_failover_hint_retry_budget_bounds() -> None:
    with pytest.raises(ValidationError):
        FailoverHint(retry_budget=-1)
    with pytest.raises(ValidationError):
        FailoverHint(retry_budget=100)


# ---------------------------------------------------------------------------
# Integration: wire format preserved
# ---------------------------------------------------------------------------


def test_wire_format_keys_stable() -> None:
    """Companion apps rely on these exact top-level keys."""
    mission = MissionV1(
        metadata=MissionMetadata(mission_id="m1", ranch_id="r1"),
        waypoints=[Waypoint(lat=0.0, lon=0.0, alt_m=5.0)],
    )
    wire = mission.to_wire()
    assert set(wire.keys()) >= {
        "version",
        "metadata",
        "waypoints",
        "failover",
    }
    assert wire["version"] == 1
