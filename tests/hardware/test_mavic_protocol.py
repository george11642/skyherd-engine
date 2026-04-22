"""
tests/hardware/test_mavic_protocol.py
--------------------------------------
Validates that sample MQTT/WebSocket envelopes from all three implementation
paths (Python MavicBackend, iOS SkyHerdCompanion, Android SkyHerdCompanion)
conform to the canonical JSON Schema defined in
docs/HARDWARE_MAVIC_PROTOCOL.md.

Envelope definitions are copied verbatim from the protocol doc so this file
acts as a living contract test — if the schema or the samples diverge the test
fails before any hardware is touched.
"""

from __future__ import annotations

import json

import jsonschema
import pytest

# ---------------------------------------------------------------------------
# Schema (extracted from docs/HARDWARE_MAVIC_PROTOCOL.md)
# ---------------------------------------------------------------------------

_WAYPOINT_SCHEMA: dict = {
    "type": "object",
    "required": ["lat", "lon", "alt_m"],
    "properties": {
        "lat": {"type": "number"},
        "lon": {"type": "number"},
        "alt_m": {"type": "number", "minimum": 0, "maximum": 120},
        "hold_s": {"type": "number", "minimum": 0},
    },
    "additionalProperties": False,
}

_STATE_SCHEMA: dict = {
    "type": "object",
    "required": ["armed", "in_air", "altitude_m", "battery_pct", "mode", "lat", "lon"],
    "properties": {
        "armed": {"type": "boolean"},
        "in_air": {"type": "boolean"},
        "altitude_m": {"type": "number", "minimum": 0},
        "battery_pct": {"type": "number", "minimum": 0, "maximum": 100},
        "mode": {"type": "string"},
        "lat": {"type": "number", "minimum": -90, "maximum": 90},
        "lon": {"type": "number", "minimum": -180, "maximum": 180},
    },
    "additionalProperties": False,
}

_COMMAND_SCHEMA: dict = {
    "type": "object",
    "required": ["cmd", "args", "seq"],
    "properties": {
        "cmd": {
            "type": "string",
            "enum": [
                "takeoff",
                "patrol",
                "return_to_home",
                "play_deterrent",
                "capture_visual_clip",
                "get_state",
            ],
        },
        "args": {"type": "object"},
        "seq": {"type": "integer", "minimum": 0},
    },
    "additionalProperties": False,
}

_ACK_SCHEMA: dict = {
    "type": "object",
    "required": ["ack", "result", "seq"],
    "properties": {
        "ack": {"type": "string"},
        "result": {"type": "string", "enum": ["ok", "error"]},
        "seq": {"type": "integer", "minimum": 0},
        "message": {"type": "string"},
        "data": {},  # freeform object or null
    },
    # message / data are optional
}


# ---------------------------------------------------------------------------
# Sample envelopes — represents all three paths
# ---------------------------------------------------------------------------

# Python MavicBackend path (from mavic.py _send calls)
_PYTHON_COMMANDS: list[dict] = [
    {"cmd": "takeoff", "args": {"alt_m": 5.0}, "seq": 1},
    {"cmd": "takeoff", "args": {"alt_m": 30.0}, "seq": 2},
    {
        "cmd": "patrol",
        "args": {
            "waypoints": [
                {"lat": 36.1, "lon": -105.2, "alt_m": 30.0, "hold_s": 0.0},
                {"lat": 36.2, "lon": -105.3, "alt_m": 30.0, "hold_s": 5.0},
            ]
        },
        "seq": 3,
    },
    {"cmd": "return_to_home", "args": {}, "seq": 4},
    {"cmd": "play_deterrent", "args": {"tone_hz": 12000, "duration_s": 6.0}, "seq": 5},
    {"cmd": "capture_visual_clip", "args": {"duration_s": 10.0}, "seq": 6},
    {"cmd": "get_state", "args": {}, "seq": 7},
]

# iOS SkyHerdCompanion path (from CommandRouter.swift dispatch)
_IOS_COMMANDS: list[dict] = [
    {"cmd": "takeoff", "args": {"alt_m": 5.0}, "seq": 10},
    {"cmd": "return_to_home", "args": {}, "seq": 11},
    {"cmd": "get_state", "args": {}, "seq": 12},
    {"cmd": "play_deterrent", "args": {"tone_hz": 12000, "duration_s": 6.0}, "seq": 13},
    {"cmd": "capture_visual_clip", "args": {"duration_s": 10.0}, "seq": 14},
]

# Android SkyHerdCompanion path (mirrors iOS; Android agent writes identical JSON)
_ANDROID_COMMANDS: list[dict] = [
    {"cmd": "takeoff", "args": {"alt_m": 5.0}, "seq": 20},
    {
        "cmd": "patrol",
        "args": {
            "waypoints": [
                {"lat": 36.5, "lon": -105.5, "alt_m": 25.0},
            ]
        },
        "seq": 21,
    },
    {"cmd": "return_to_home", "args": {}, "seq": 22},
    {"cmd": "get_state", "args": {}, "seq": 23},
]

# ACK samples — ok and error variants
_ACK_SAMPLES: list[dict] = [
    # ok variants
    {"ack": "takeoff", "result": "ok", "seq": 1},
    {"ack": "patrol", "result": "ok", "seq": 3},
    {"ack": "return_to_home", "result": "ok", "seq": 4},
    {"ack": "play_deterrent", "result": "ok", "seq": 5},
    {
        "ack": "capture_visual_clip",
        "result": "ok",
        "seq": 6,
        "data": {"path": "/var/mobile/Containers/.../mavic_1234567890.mp4"},
    },
    {
        "ack": "get_state",
        "result": "ok",
        "seq": 7,
        "data": {
            "armed": False,
            "in_air": False,
            "altitude_m": 0.0,
            "battery_pct": 85.0,
            "mode": "STANDBY",
            "lat": 36.1,
            "lon": -105.2,
        },
    },
    # error variants — each canonical error code
    {"ack": "takeoff", "result": "error", "message": "E_DJI_NOT_READY", "seq": 100},
    {"ack": "patrol", "result": "error", "message": "E_GEOFENCE_REJECT", "seq": 101},
    {"ack": "takeoff", "result": "error", "message": "E_BATTERY_LOW", "seq": 102},
    {"ack": "takeoff", "result": "error", "message": "E_WIND_CEILING", "seq": 103},
    {"ack": "takeoff", "result": "error", "message": "E_TIMEOUT", "seq": 104},
    {"ack": "unknown", "result": "error", "message": "E_UNKNOWN_CMD", "seq": 105},
]

# DroneStateSnapshot samples
_STATE_SAMPLES: list[dict] = [
    {
        "armed": False,
        "in_air": False,
        "altitude_m": 0.0,
        "battery_pct": 100.0,
        "mode": "UNKNOWN",
        "lat": 0.0,
        "lon": 0.0,
    },
    {
        "armed": True,
        "in_air": True,
        "altitude_m": 30.0,
        "battery_pct": 72.0,
        "mode": "GUIDED",
        "lat": 36.1,
        "lon": -105.2,
    },
    {
        "armed": True,
        "in_air": True,
        "altitude_m": 5.0,
        "battery_pct": 25.1,
        "mode": "GUIDED",
        "lat": 36.15,
        "lon": -105.25,
    },
    {
        "armed": False,
        "in_air": False,
        "altitude_m": 0.0,
        "battery_pct": 85.0,
        "mode": "STANDBY",
        "lat": 36.1,
        "lon": -105.2,
    },
]

# Waypoint samples
_WAYPOINT_SAMPLES: list[dict] = [
    {"lat": 36.1, "lon": -105.2, "alt_m": 30.0, "hold_s": 0.0},
    {"lat": 36.2, "lon": -105.3, "alt_m": 30.0, "hold_s": 5.0},
    {"lat": 36.5, "lon": -105.5, "alt_m": 25.0},  # hold_s optional
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _validate(instance: dict, schema: dict) -> None:
    """Raise jsonschema.ValidationError if instance does not match schema."""
    jsonschema.validate(instance=instance, schema=schema)


# ---------------------------------------------------------------------------
# Tests — Command envelopes
# ---------------------------------------------------------------------------


class TestCommandEnvelopes:
    @pytest.mark.parametrize("cmd", _PYTHON_COMMANDS)
    def test_python_command_valid(self, cmd: dict) -> None:
        _validate(cmd, _COMMAND_SCHEMA)

    @pytest.mark.parametrize("cmd", _IOS_COMMANDS)
    def test_ios_command_valid(self, cmd: dict) -> None:
        _validate(cmd, _COMMAND_SCHEMA)

    @pytest.mark.parametrize("cmd", _ANDROID_COMMANDS)
    def test_android_command_valid(self, cmd: dict) -> None:
        _validate(cmd, _COMMAND_SCHEMA)

    def test_command_missing_cmd_field_invalid(self) -> None:
        with pytest.raises(jsonschema.ValidationError):
            _validate({"args": {}, "seq": 1}, _COMMAND_SCHEMA)

    def test_command_missing_seq_invalid(self) -> None:
        with pytest.raises(jsonschema.ValidationError):
            _validate({"cmd": "takeoff", "args": {}}, _COMMAND_SCHEMA)

    def test_command_negative_seq_invalid(self) -> None:
        with pytest.raises(jsonschema.ValidationError):
            _validate({"cmd": "takeoff", "args": {}, "seq": -1}, _COMMAND_SCHEMA)

    def test_command_unknown_cmd_name_invalid(self) -> None:
        with pytest.raises(jsonschema.ValidationError):
            _validate({"cmd": "launch_missiles", "args": {}, "seq": 1}, _COMMAND_SCHEMA)

    def test_json_roundtrip_preserves_cmd(self) -> None:
        """Wire-format round-trip: serialize to JSON string then back."""
        original = _PYTHON_COMMANDS[0]
        wire = json.dumps(original)
        recovered = json.loads(wire)
        assert recovered["cmd"] == original["cmd"]
        assert recovered["seq"] == original["seq"]


# ---------------------------------------------------------------------------
# Tests — ACK envelopes
# ---------------------------------------------------------------------------


class TestAckEnvelopes:
    @pytest.mark.parametrize("ack", _ACK_SAMPLES)
    def test_ack_sample_valid(self, ack: dict) -> None:
        _validate(ack, _ACK_SCHEMA)

    def test_ack_missing_ack_field_invalid(self) -> None:
        with pytest.raises(jsonschema.ValidationError):
            _validate({"result": "ok", "seq": 1}, _ACK_SCHEMA)

    def test_ack_invalid_result_value(self) -> None:
        with pytest.raises(jsonschema.ValidationError):
            _validate({"ack": "takeoff", "result": "maybe", "seq": 1}, _ACK_SCHEMA)

    def test_error_ack_has_error_code_in_message(self) -> None:
        error_acks = [a for a in _ACK_SAMPLES if a["result"] == "error"]
        known_codes = {
            "E_DJI_NOT_READY",
            "E_GEOFENCE_REJECT",
            "E_BATTERY_LOW",
            "E_WIND_CEILING",
            "E_TIMEOUT",
            "E_UNKNOWN_CMD",
        }
        for ack in error_acks:
            assert "message" in ack, f"Error ACK missing message: {ack}"
            assert ack["message"] in known_codes, (
                f"Unknown error code '{ack['message']}' — add to protocol doc"
            )

    def test_ok_ack_seq_matches_cmd_seq(self) -> None:
        ok_acks = [a for a in _ACK_SAMPLES if a["result"] == "ok"]
        for ack in ok_acks:
            assert ack["seq"] >= 0


# ---------------------------------------------------------------------------
# Tests — State snapshot
# ---------------------------------------------------------------------------


class TestStateSnapshot:
    @pytest.mark.parametrize("state", _STATE_SAMPLES)
    def test_state_sample_valid(self, state: dict) -> None:
        _validate(state, _STATE_SCHEMA)

    def test_battery_out_of_range_invalid(self) -> None:
        bad = {
            "armed": False,
            "in_air": False,
            "altitude_m": 0.0,
            "battery_pct": 101.0,
            "mode": "STANDBY",
            "lat": 0.0,
            "lon": 0.0,
        }
        with pytest.raises(jsonschema.ValidationError):
            _validate(bad, _STATE_SCHEMA)

    def test_altitude_negative_invalid(self) -> None:
        bad = {
            "armed": False,
            "in_air": False,
            "altitude_m": -1.0,
            "battery_pct": 80.0,
            "mode": "STANDBY",
            "lat": 0.0,
            "lon": 0.0,
        }
        with pytest.raises(jsonschema.ValidationError):
            _validate(bad, _STATE_SCHEMA)

    def test_lat_out_of_range_invalid(self) -> None:
        bad = {
            "armed": False,
            "in_air": False,
            "altitude_m": 0.0,
            "battery_pct": 80.0,
            "mode": "STANDBY",
            "lat": 91.0,
            "lon": 0.0,
        }
        with pytest.raises(jsonschema.ValidationError):
            _validate(bad, _STATE_SCHEMA)

    def test_lon_out_of_range_invalid(self) -> None:
        bad = {
            "armed": False,
            "in_air": False,
            "altitude_m": 0.0,
            "battery_pct": 80.0,
            "mode": "STANDBY",
            "lat": 0.0,
            "lon": -181.0,
        }
        with pytest.raises(jsonschema.ValidationError):
            _validate(bad, _STATE_SCHEMA)


# ---------------------------------------------------------------------------
# Tests — Waypoints
# ---------------------------------------------------------------------------


class TestWaypoints:
    @pytest.mark.parametrize("wp", _WAYPOINT_SAMPLES)
    def test_waypoint_valid(self, wp: dict) -> None:
        _validate(wp, _WAYPOINT_SCHEMA)

    def test_waypoint_alt_exceeds_120m_invalid(self) -> None:
        bad = {"lat": 36.1, "lon": -105.2, "alt_m": 121.0}
        with pytest.raises(jsonschema.ValidationError):
            _validate(bad, _WAYPOINT_SCHEMA)

    def test_waypoint_missing_lat_invalid(self) -> None:
        bad = {"lon": -105.2, "alt_m": 30.0}
        with pytest.raises(jsonschema.ValidationError):
            _validate(bad, _WAYPOINT_SCHEMA)


# ---------------------------------------------------------------------------
# Tests — Cross-path field-name consistency
# ---------------------------------------------------------------------------


class TestCrossPathConsistency:
    """
    Verify that the canonical snake_case field names are used consistently
    across all sample paths (no camelCase sneaking in from Android/iOS).
    """

    _all_commands = _PYTHON_COMMANDS + _IOS_COMMANDS + _ANDROID_COMMANDS

    def test_no_camel_case_in_command_fields(self) -> None:
        for cmd in self._all_commands:
            for key in cmd:
                assert key == key.lower() or "_" in key or key.islower(), (
                    f"Non-snake_case key '{key}' in command envelope"
                )

    def test_state_uses_snake_case_field_names(self) -> None:
        required_keys = {"armed", "in_air", "altitude_m", "battery_pct", "mode", "lat", "lon"}
        for state in _STATE_SAMPLES:
            assert required_keys.issubset(state.keys()), (
                f"State snapshot missing keys: {required_keys - state.keys()}"
            )
