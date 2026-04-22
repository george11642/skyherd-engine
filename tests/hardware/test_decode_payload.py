"""Tests for hardware/collar/provisioning/decode_payload.py.

Validates the 16-byte encode/decode round-trip and confirms the decoded
payload shape matches the sim collar schema from src/skyherd/sensors/collar.py.

Run with:
    uv run pytest -q tests/hardware/
"""

from __future__ import annotations

import importlib.util
import struct
import sys
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import decode_payload from provisioning directory (not a package)
# ---------------------------------------------------------------------------

_PROVISIONING = (
    Path(__file__).resolve().parent.parent.parent
    / "hardware"
    / "collar"
    / "provisioning"
)


def _import_decode_payload():
    spec = importlib.util.spec_from_file_location(
        "decode_payload", _PROVISIONING / "decode_payload.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["decode_payload"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_dp = _import_decode_payload()
decode = _dp.decode
encode = _dp.encode
CollarReading = _dp.CollarReading
PAYLOAD_SIZE = _dp.PAYLOAD_SIZE
PAYLOAD_FMT = _dp.PAYLOAD_FMT
NO_FIX_AGE = _dp.NO_FIX_AGE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_raw(
    lat: float = 34.0523401,
    lon: float = -106.5342812,
    alt_m: int = 1540,
    activity_code: int = 1,
    battery_pct: int = 82,
    fix_age_s: int = 3,
    uptime_s: int = 900,
) -> bytes:
    """Build a raw 16-byte payload from Python-native values."""
    lat_e7 = int(round(lat * 1e7))
    lon_e7 = int(round(lon * 1e7))
    alt_raw = alt_m & 0xFFFF
    return struct.pack(
        PAYLOAD_FMT,
        lat_e7,
        lon_e7,
        alt_raw,
        activity_code,
        battery_pct,
        fix_age_s,
        uptime_s,
    )


# ---------------------------------------------------------------------------
# Payload size / format contract
# ---------------------------------------------------------------------------


class TestPayloadFormat:
    def test_payload_size_is_16(self):
        assert PAYLOAD_SIZE == 16

    def test_struct_size_matches_constant(self):
        assert struct.calcsize(PAYLOAD_FMT) == PAYLOAD_SIZE

    def test_raw_helper_produces_16_bytes(self):
        assert len(make_raw()) == 16


# ---------------------------------------------------------------------------
# Round-trip (encode -> decode -> re-encode)
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_typical_nm_location(self):
        """NM ranch GPS coordinates round-trip with sub-metre precision."""
        raw = make_raw(lat=34.0523401, lon=-106.5342812, alt_m=1540)
        reading = decode(raw, ranch_id="ranch_a", cow_tag="A001")

        re_encoded = encode(reading)
        re_decoded = decode(re_encoded, ranch_id="ranch_a", cow_tag="A001")

        assert abs(re_decoded.pos[0] - reading.pos[0]) < 1e-6
        assert abs(re_decoded.pos[1] - reading.pos[1]) < 1e-6
        assert re_decoded.alt_m == reading.alt_m
        assert re_decoded.activity == reading.activity
        assert re_decoded.battery_pct == reading.battery_pct

    def test_zero_coords_no_fix(self):
        """No-fix payload: zero lat/lon + fix_age sentinel 65535."""
        raw = make_raw(lat=0.0, lon=0.0, fix_age_s=NO_FIX_AGE)
        reading = decode(raw, ranch_id="ranch_a", cow_tag="A001")

        assert reading.pos == [0.0, 0.0]
        assert reading.fix_age_s == NO_FIX_AGE

        re_encoded = encode(reading)
        re_decoded = decode(re_encoded, ranch_id="ranch_a", cow_tag="A001")
        assert re_decoded.fix_age_s == NO_FIX_AGE

    def test_southern_hemisphere_negative_lat(self):
        """Negative latitude (southern hemisphere) preserved through round-trip."""
        raw = make_raw(lat=-33.8688, lon=151.2093)
        reading = decode(raw, ranch_id="test", cow_tag="B001")

        assert reading.pos[0] < 0.0
        re_encoded = encode(reading)
        re_decoded = decode(re_encoded, ranch_id="test", cow_tag="B001")
        assert re_decoded.pos[0] < 0.0
        assert abs(re_decoded.pos[0] - reading.pos[0]) < 1e-6

    def test_negative_altitude_below_sea_level(self):
        """Negative altitude (Death Valley etc.) wraps via uint16 and sign-extends."""
        raw = make_raw(alt_m=-50)
        reading = decode(raw, ranch_id="ranch_a", cow_tag="A001")
        assert reading.alt_m == -50

        re_encoded = encode(reading)
        re_decoded = decode(re_encoded, ranch_id="ranch_a", cow_tag="A001")
        assert re_decoded.alt_m == -50

    def test_uptime_max_wrap(self):
        """uptime_s at uint16 max (65535) round-trips cleanly."""
        raw = make_raw(uptime_s=65535)
        reading = decode(raw, ranch_id="ranch_a", cow_tag="A001")
        assert reading.uptime_s == 65535

        re_encoded = encode(reading)
        re_decoded = decode(re_encoded, ranch_id="ranch_a", cow_tag="A001")
        assert re_decoded.uptime_s == 65535

    def test_battery_boundary_full(self):
        raw = make_raw(battery_pct=100)
        reading = decode(raw, ranch_id="ranch_a", cow_tag="A001")
        assert reading.battery_pct == 100.0

    def test_battery_boundary_empty(self):
        raw = make_raw(battery_pct=0)
        reading = decode(raw, ranch_id="ranch_a", cow_tag="A001")
        assert reading.battery_pct == 0.0


# ---------------------------------------------------------------------------
# Activity code classification (mirrors collar.py _classify_activity)
# ---------------------------------------------------------------------------


class TestActivityCodes:
    def test_resting_code_0(self):
        raw = make_raw(activity_code=0)
        assert decode(raw, "ranch_a", "A001").activity == "resting"

    def test_grazing_code_1(self):
        raw = make_raw(activity_code=1)
        assert decode(raw, "ranch_a", "A001").activity == "grazing"

    def test_walking_code_2(self):
        raw = make_raw(activity_code=2)
        assert decode(raw, "ranch_a", "A001").activity == "walking"

    def test_unknown_code_defaults_to_resting(self):
        """Firmware should never send codes > 2, but decoder must be defensive."""
        raw = make_raw(activity_code=7)
        reading = decode(raw, "ranch_a", "A001")
        assert reading.activity == "resting"


# ---------------------------------------------------------------------------
# Schema match against sim collar.py payload keys
# ---------------------------------------------------------------------------

SIM_COLLAR_REQUIRED_KEYS = {
    "ts",
    "kind",
    "ranch",
    "entity",
    "pos",
    "heading_deg",
    "activity",
    "battery_pct",
}


class TestSimCollarSchemaCompatibility:
    """Decoded payload must include all keys emitted by CollarSensor.tick() in collar.py."""

    def test_all_sim_keys_present(self):
        raw = make_raw()
        reading = decode(raw, ranch_id="ranch_a", cow_tag="A001")
        payload = reading.to_mqtt_payload()
        missing = SIM_COLLAR_REQUIRED_KEYS - set(payload.keys())
        assert not missing, f"Missing keys: {missing}"

    def test_kind_is_collar_reading(self):
        raw = make_raw()
        reading = decode(raw, ranch_id="ranch_a", cow_tag="A001")
        assert reading.kind == "collar.reading"

    def test_source_is_real(self):
        """Real collar payloads must identify as 'real' to allow dashboard colouring."""
        raw = make_raw()
        reading = decode(raw, ranch_id="ranch_a", cow_tag="A001")
        assert reading.source == "real"

    def test_pos_is_two_element_list(self):
        raw = make_raw()
        reading = decode(raw, ranch_id="ranch_a", cow_tag="A001")
        payload = reading.to_mqtt_payload()
        assert isinstance(payload["pos"], list)
        assert len(payload["pos"]) == 2

    def test_ts_is_recent(self):
        before = time.time()
        raw = make_raw()
        reading = decode(raw, ranch_id="ranch_a", cow_tag="A001")
        after = time.time()
        assert before <= reading.ts <= after

    def test_ts_override(self):
        raw = make_raw()
        ts = 1_700_000_000.0
        reading = decode(raw, ranch_id="ranch_a", cow_tag="A001", ts=ts)
        assert reading.ts == ts

    def test_ranch_and_entity_propagated(self):
        raw = make_raw()
        reading = decode(raw, ranch_id="my_ranch", cow_tag="X999")
        assert reading.ranch == "my_ranch"
        assert reading.entity == "X999"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestDecodeErrors:
    def test_wrong_length_raises_value_error(self):
        with pytest.raises(ValueError, match="Expected 16 bytes"):
            decode(b"\x00" * 10, ranch_id="ranch_a", cow_tag="A001")

    def test_empty_bytes_raises_value_error(self):
        with pytest.raises(ValueError):
            decode(b"", ranch_id="ranch_a", cow_tag="A001")

    def test_17_bytes_raises_value_error(self):
        with pytest.raises(ValueError):
            decode(b"\x00" * 17, ranch_id="ranch_a", cow_tag="A001")


# ---------------------------------------------------------------------------
# Little-endian byte order
# ---------------------------------------------------------------------------


class TestByteOrder:
    def test_lat_e7_little_endian(self):
        """lat_e7 = 0x01020304 -> bytes 04 03 02 01 at offset 0."""
        lat_e7 = 0x01020304
        lat = lat_e7 / 1e7
        raw = make_raw(lat=lat)
        assert raw[0] == 0x04
        assert raw[1] == 0x03
        assert raw[2] == 0x02
        assert raw[3] == 0x01
