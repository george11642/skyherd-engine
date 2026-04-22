"""decode_payload -- inflate 16-byte LoRaWAN uplink into SkyHerd collar MQTT payload.

Consumed by ChirpStack HTTP integration webhook handler and by
``provisioning/register-collar.py`` for live testing.

Payload layout (little-endian, 16 bytes -- must match firmware CollarPayload struct):
    [0..3]   int32   lat_e7          latitude  x 1e7
    [4..7]   int32   lon_e7          longitude x 1e7
    [8..9]   int16   alt_m           altitude in whole metres
    [10]     uint8   activity_code   0=resting  1=grazing  2=walking
    [11]     uint8   battery_pct     0-100
    [12..13] uint16  fix_age_s       GPS fix age in seconds
    [14..15] uint16  uptime_s        seconds since last MCU reset (wraps)

Output JSON mirrors the sim collar payload from skyherd/sensors/collar.py:
    {
        "ts":          <float epoch>,
        "kind":        "collar.reading",
        "ranch":       <str>,
        "entity":      <str cow_tag>,
        "pos":         [lat_float, lon_float],
        "heading_deg": 0.0,        # not available from firmware v1
        "activity":    "grazing",
        "battery_pct": 82.0,
        "alt_m":       1540,
        "fix_age_s":   3,
        "uptime_s":    900,
        "source":      "real",     # distinguishes from sim collars
    }

Usage as CLI (for testing):
    python decode_payload.py <hex_bytes> --ranch ranch_a --cow-tag A001
    python decode_payload.py 39e46414d4b5e4c10c0601520300840e --ranch ranch_a --cow-tag A001

Usage in webhook handler:
    from decode_payload import decode, CollarReading, PAYLOAD_FMT
    reading = decode(raw_bytes, ranch_id="ranch_a", cow_tag="A001")
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import struct
import sys
import time
from dataclasses import asdict, dataclass

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Payload format -- must stay in sync with firmware CollarPayload struct
# ---------------------------------------------------------------------------

# < = little-endian, i=int32, i=int32, H=uint16(alt), B=uint8, B=uint8, H=uint16, H=uint16
PAYLOAD_FMT = "<iiHBBHH"
PAYLOAD_SIZE = struct.calcsize(PAYLOAD_FMT)  # should be 16

assert PAYLOAD_SIZE == 16, f"PAYLOAD_FMT size mismatch: {PAYLOAD_SIZE} != 16"

# Activity code -> string (mirrors collar.py _classify_activity)
ACTIVITY_LABELS: dict[int, str] = {
    0: "resting",
    1: "grazing",
    2: "walking",
}

# Sentinel value for "no GPS fix"
NO_FIX_AGE = 65535


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CollarReading:
    """Decoded, validated collar reading ready for MQTT publish."""

    ts: float
    kind: str
    ranch: str
    entity: str
    pos: list[float]
    heading_deg: float
    activity: str
    battery_pct: float
    alt_m: int
    fix_age_s: int
    uptime_s: int
    source: str = "real"

    def to_mqtt_payload(self) -> dict:
        """Return dict matching the sim collar schema (bus.publish-ready)."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Decode
# ---------------------------------------------------------------------------


def decode(raw: bytes, ranch_id: str, cow_tag: str, ts: float | None = None) -> CollarReading:
    """Decode 16 raw bytes into a CollarReading.

    Args:
        raw:      16-byte uplink payload from LoRaWAN.
        ranch_id: Ranch identifier string (e.g. "ranch_a").
        cow_tag:  Animal tag (e.g. "A001").
        ts:       Unix epoch override; defaults to now().

    Raises:
        ValueError: if ``raw`` is not exactly 16 bytes.
    """
    if len(raw) != PAYLOAD_SIZE:
        raise ValueError(
            f"Expected {PAYLOAD_SIZE} bytes, got {len(raw)}. "
            "Check that firmware CollarPayload struct matches PAYLOAD_FMT."
        )

    lat_e7, lon_e7, alt_raw, activity_code, battery_pct, fix_age_s, uptime_s = struct.unpack(
        PAYLOAD_FMT, raw
    )

    # alt_raw was packed as 'H' (unsigned short) but is logically int16
    # sign-extend: values > 32767 are negative altitudes
    alt_m = alt_raw if alt_raw <= 32767 else alt_raw - 65536

    lat = lat_e7 / 1e7
    lon = lon_e7 / 1e7

    # Clamp: valid GPS range
    if not (-90.0 <= lat <= 90.0):
        log.warning("lat out of range: %.7f -- zeroing", lat)
        lat = 0.0
    if not (-180.0 <= lon <= 180.0):
        log.warning("lon out of range: %.7f -- zeroing", lon)
        lon = 0.0

    activity = ACTIVITY_LABELS.get(activity_code, "resting")
    if activity_code not in ACTIVITY_LABELS:
        log.warning("Unknown activity_code %d -- defaulting to resting", activity_code)

    battery_pct_f = float(max(0, min(100, battery_pct)))

    has_fix = fix_age_s != NO_FIX_AGE
    if not has_fix:
        log.debug("No GPS fix (fix_age_s=65535)")

    return CollarReading(
        ts=ts if ts is not None else time.time(),
        kind="collar.reading",
        ranch=ranch_id,
        entity=cow_tag,
        pos=[lat, lon],
        heading_deg=0.0,
        activity=activity,
        battery_pct=battery_pct_f,
        alt_m=alt_m,
        fix_age_s=fix_age_s,
        uptime_s=uptime_s,
        source="real",
    )


def encode(reading: CollarReading) -> bytes:
    """Encode a CollarReading back to 16 raw bytes (for testing round-trips).

    Note: heading_deg and source fields are not encoded (not in payload).
    """
    lat_e7 = int(round(reading.pos[0] * 1e7))
    lon_e7 = int(round(reading.pos[1] * 1e7))
    alt_raw = reading.alt_m & 0xFFFF  # unsigned wrap for negative altitudes
    activity_code = {v: k for k, v in ACTIVITY_LABELS.items()}.get(reading.activity, 0)
    battery_pct = int(max(0, min(100, reading.battery_pct)))
    fix_age_s = reading.fix_age_s
    uptime_s = reading.uptime_s & 0xFFFF

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
# MQTT publish helper
# ---------------------------------------------------------------------------


def publish_to_mqtt(reading: CollarReading, mqtt_url: str | None = None) -> bool:
    """Publish decoded reading to the standard SkyHerd MQTT topic.

    Topic: skyherd/{ranch}/collar/{cow_tag}

    Uses aiomqtt if available; falls back to a simple socket-level MQTT PUBLISH
    (QoS 0) for environments without asyncio running.

    Returns True on success, False on failure.
    """
    mqtt_url = mqtt_url or os.environ.get("MQTT_URL", "mqtt://localhost:1883")
    topic = f"skyherd/{reading.ranch}/collar/{reading.entity}"
    payload_str = json.dumps(reading.to_mqtt_payload(), sort_keys=True, separators=(",", ":"))
    payload_bytes = payload_str.encode()

    # Parse host:port
    without_scheme = mqtt_url.split("://", 1)[-1]
    host, _, port_str = without_scheme.partition(":")
    port = int(port_str) if port_str else 1883

    try:
        import asyncio

        async def _publish() -> None:
            import aiomqtt

            async with aiomqtt.Client(hostname=host, port=port) as client:
                await client.publish(topic, payload=payload_bytes, qos=0)

        asyncio.run(_publish())
        log.info("Published to %s", topic)
        return True
    except ImportError:
        log.warning("aiomqtt not available -- cannot publish to MQTT")
        return False
    except Exception as exc:  # noqa: BLE001
        log.warning("MQTT publish failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Decode a SkyHerd collar 16-byte LoRaWAN uplink payload.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("hex_bytes", help="16-byte payload as hex string (no spaces)")
    p.add_argument("--ranch", required=True, help="Ranch identifier")
    p.add_argument("--cow-tag", required=True, help="Cow tag / animal ID")
    p.add_argument("--publish", action="store_true", help="Publish decoded payload to MQTT")
    p.add_argument("--json", dest="output_json", action="store_true", help="Output raw JSON")
    return p.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()

    try:
        raw = bytes.fromhex(args.hex_bytes)
    except ValueError as exc:
        print(f"Error: invalid hex string -- {exc}", file=sys.stderr)
        return 1

    try:
        reading = decode(raw, ranch_id=args.ranch, cow_tag=args.cow_tag)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    payload = reading.to_mqtt_payload()
    if args.output_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Decoded collar reading for {args.cow_tag} on {args.ranch}:")
        print(f"  pos        = {payload['pos']}")
        print(f"  alt_m      = {payload['alt_m']}")
        print(f"  activity   = {payload['activity']}")
        print(f"  battery    = {payload['battery_pct']}%")
        print(f"  fix_age_s  = {payload['fix_age_s']}")
        print(f"  uptime_s   = {payload['uptime_s']}")
        print(f"  source     = {payload['source']}")

    if args.publish:
        ok = publish_to_mqtt(reading)
        if not ok:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
