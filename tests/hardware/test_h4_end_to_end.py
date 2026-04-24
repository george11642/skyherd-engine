"""End-to-end H4 integration — collar_sim -> encode -> ChirpStack uplink
-> ChirpStackBridge -> canonical SkyHerd MQTT payload.

Runs fully in-process with fakes. Proves that:

1. A deterministic :class:`CollarSimEmitter` tick can be wrapped inside the
   exact ChirpStack v4 JSON event shape that the bridge consumes.
2. :class:`ChirpStackBridge` decodes and republishes on the canonical
   ``skyherd/{ranch}/collar/{cow_tag}`` topic.
3. Schema parity holds: the bridge-decoded payload's key set matches what
   a sim-world :class:`CollarSensor` would emit (minus `heart_rate_bpm`,
   which is sim-only).
4. Multiple emitters (different cow_tags / seeds) stay isolated — no
   cross-pollination of topics or seeds.
5. The chain is deterministic: same seed produces byte-identical MQTT
   payloads on two runs (modulo ``ts``).

This test does not touch a real MQTT broker or a real ChirpStack instance.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any

import pytest

from skyherd.edge.chirpstack_bridge import ChirpStackBridge, CollarRegistry
from skyherd.sensors.collar_sim import CollarSimEmitter

# ---------------------------------------------------------------------------
# decode_payload shim (provisioning dir is not a package)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROVISIONING = _REPO_ROOT / "hardware" / "collar" / "provisioning"


def _import_decode_payload() -> Any:
    cache_key = "_h4e2e_decode_payload"
    if cache_key in sys.modules:
        return sys.modules[cache_key]
    spec = importlib.util.spec_from_file_location(cache_key, _PROVISIONING / "decode_payload.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[cache_key] = mod
    spec.loader.exec_module(mod)
    return mod


_dp = _import_decode_payload()


# ---------------------------------------------------------------------------
# Helpers — build a ChirpStack uplink event from a sim tick
# ---------------------------------------------------------------------------


def _sim_tick_to_raw_bytes(tick: dict[str, Any]) -> bytes:
    """Pack a sim tick dict into the 16-byte firmware CollarPayload format.

    We deliberately *don't* try to round-trip heart_rate_bpm / heading_deg
    through the wire — the real LoRa frame does not carry them. This keeps
    the test honest about the sim-vs-real schema overlap.
    """
    lat_e7 = int(round(tick["pos"][0] * 1e7))
    lon_e7 = int(round(tick["pos"][1] * 1e7))
    alt_raw = 1540 & 0xFFFF
    activity_map = {"resting": 0, "grazing": 1, "walking": 2}
    activity_code = activity_map.get(str(tick["activity"]), 0)
    battery_pct = int(max(0, min(100, float(tick["battery_pct"]))))
    fix_age_s = 3
    uptime_s = int(tick["ts"]) & 0xFFFF

    return struct.pack(
        _dp.PAYLOAD_FMT,
        lat_e7,
        lon_e7,
        alt_raw,
        activity_code,
        battery_pct,
        fix_age_s,
        uptime_s,
    )


def _wrap_in_chirpstack_event(
    raw_bytes: bytes,
    *,
    dev_eui: str = "A8610A3453210A00",
    app_id: str = "skyherd-ranch-a",
    f_port: int = 2,
    f_cnt: int = 0,
) -> bytes:
    """Build a minimal ChirpStack v4 uplink event JSON wrapping ``raw_bytes``."""
    event = {
        "deviceInfo": {
            "tenantId": "skyherd",
            "applicationId": app_id,
            "applicationName": "skyherd-collars",
            "deviceName": "test-collar",
            "devEui": dev_eui,
        },
        "devAddr": "01020304",
        "adr": True,
        "dr": 0,
        "fCnt": f_cnt,
        "fPort": f_port,
        "confirmed": False,
        "data": base64.b64encode(raw_bytes).decode("ascii"),
        "rxInfo": [
            {
                "gatewayId": "c0ee40ffff29da3f",
                "gatewayTime": 1_700_000_000.0,
                "rssi": -91,
                "snr": 7.5,
            }
        ],
    }
    return json.dumps(event).encode("utf-8")


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _RecordingRegistry(CollarRegistry):
    """CollarRegistry that serves an in-memory dict — no file I/O, no TTL."""

    def __init__(self, entries: dict[str, tuple[str, str]]) -> None:
        # Don't call super().__init__ — we skip the file-load machinery entirely.
        self._entries = {k.upper(): v for k, v in entries.items()}

    def lookup(self, dev_eui: str) -> tuple[str, str] | None:  # type: ignore[override]
        return self._entries.get(dev_eui.upper())

    def size(self) -> int:  # type: ignore[override]
        return len(self._entries)


class _RecordingMqtt:
    """Fake MQTT publisher that records (topic, json-dict) pairs."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, topic: str, payload: bytes) -> None:
        self.published.append((topic, json.loads(payload.decode("utf-8"))))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sim_to_bridge_round_trip_schema_match() -> None:
    """Single-tick end-to-end: sim tick -> encoded 16 bytes -> ChirpStack
    event -> bridge -> canonical topic + matching key set."""
    emitter = CollarSimEmitter(ranch_id="ranch_a", cow_tag="A001", seed=42)
    registry = _RecordingRegistry({"A8610A3453210A00": ("ranch_a", "A001")})
    mqtt = _RecordingMqtt()
    bridge = ChirpStackBridge(mqtt_publish=mqtt, registry=registry, decoder=_dp.decode)

    tick = emitter.tick()
    raw = _sim_tick_to_raw_bytes(tick)
    event = _wrap_in_chirpstack_event(raw, dev_eui="A8610A3453210A00")

    ok = await bridge.handle_raw_event(event)

    assert ok is True, "Bridge should accept a well-formed uplink"
    assert len(mqtt.published) == 1
    topic, payload = mqtt.published[0]
    assert topic == "skyherd/ranch_a/collar/A001"
    # schema parity: decoded payload must carry the sim-collar keys the
    # dashboard subscribers expect (minus heart_rate_bpm / heading_deg which
    # the LoRa frame does not encode).
    expected_keys = {"ts", "kind", "ranch", "entity", "pos", "activity", "battery_pct"}
    assert expected_keys.issubset(payload.keys())
    assert payload["kind"] == "collar.reading"
    assert payload["ranch"] == "ranch_a"
    assert payload["entity"] == "A001"
    assert payload["source"] == "real"  # bridge marks as real, not sim


@pytest.mark.asyncio
async def test_sim_to_bridge_multi_cow_isolation() -> None:
    """Three distinct emitters -> three distinct topics, no seed cross-talk."""
    emitters = [
        CollarSimEmitter(ranch_id="ranch_a", cow_tag=tag, seed=seed)
        for tag, seed in (("A001", 1), ("A002", 2), ("A003", 3))
    ]
    registry = _RecordingRegistry(
        {
            "A8610A3453210A01": ("ranch_a", "A001"),
            "A8610A3453210A02": ("ranch_a", "A002"),
            "A8610A3453210A03": ("ranch_a", "A003"),
        }
    )
    mqtt = _RecordingMqtt()
    bridge = ChirpStackBridge(mqtt_publish=mqtt, registry=registry, decoder=_dp.decode)

    for i, emitter in enumerate(emitters, start=1):
        tick = emitter.tick()
        raw = _sim_tick_to_raw_bytes(tick)
        event = _wrap_in_chirpstack_event(raw, dev_eui=f"A8610A3453210A0{i}")
        ok = await bridge.handle_raw_event(event)
        assert ok is True

    assert len(mqtt.published) == 3
    topics = [t for t, _ in mqtt.published]
    assert topics == [
        "skyherd/ranch_a/collar/A001",
        "skyherd/ranch_a/collar/A002",
        "skyherd/ranch_a/collar/A003",
    ]
    # Verify each payload carries its correct entity tag (no bleed).
    for (topic, payload), expected in zip(mqtt.published, ("A001", "A002", "A003"), strict=True):
        assert payload["entity"] == expected, f"bleed at {topic}"


@pytest.mark.asyncio
async def test_sim_to_bridge_determinism_same_seed() -> None:
    """Two runs with the same seed produce byte-identical MQTT payloads
    modulo the ``ts`` field (which the bridge stamps from the uplink).

    We freeze the bridge ``ts_provider`` to make ts deterministic too.
    """

    async def run_once() -> list[tuple[str, dict[str, Any]]]:
        emitter = CollarSimEmitter(ranch_id="ranch_a", cow_tag="A001", seed=42)
        registry = _RecordingRegistry({"A8610A3453210A00": ("ranch_a", "A001")})
        mqtt = _RecordingMqtt()
        tick_counter = [0.0]

        def fixed_ts() -> float:
            tick_counter[0] += 1.0
            return tick_counter[0]

        bridge = ChirpStackBridge(
            mqtt_publish=mqtt,
            registry=registry,
            decoder=_dp.decode,
            ts_provider=fixed_ts,
        )
        for _ in range(10):
            tick = emitter.tick()
            raw = _sim_tick_to_raw_bytes(tick)
            event = _wrap_in_chirpstack_event(raw, dev_eui="A8610A3453210A00")
            await bridge.handle_raw_event(event)
        return mqtt.published

    run_a = await run_once()
    run_b = await run_once()

    # Serialise both runs and compare — byte-identical proves replay determinism.
    dump_a = [json.dumps((t, p), sort_keys=True) for t, p in run_a]
    dump_b = [json.dumps((t, p), sort_keys=True) for t, p in run_b]
    assert dump_a == dump_b


@pytest.mark.asyncio
async def test_sim_and_real_schemas_agree_on_core_keys() -> None:
    """Sim CollarSensor output and bridge-decoded output must share their
    dashboard-facing keys. The dashboard subscribes on the same topic for
    both; a key-set drift would break consumers silently.
    """
    sim_tick = CollarSimEmitter(ranch_id="ranch_a", cow_tag="A001", seed=7).tick()

    registry = _RecordingRegistry({"A8610A3453210A00": ("ranch_a", "A001")})
    mqtt = _RecordingMqtt()
    bridge = ChirpStackBridge(mqtt_publish=mqtt, registry=registry, decoder=_dp.decode)
    raw = _sim_tick_to_raw_bytes(sim_tick)
    event = _wrap_in_chirpstack_event(raw, dev_eui="A8610A3453210A00")
    await bridge.handle_raw_event(event)

    real_payload = mqtt.published[0][1]

    # Core subset the dashboard depends on — present in both emitters.
    core_keys = {"ts", "kind", "ranch", "entity", "pos", "activity", "battery_pct"}
    assert core_keys.issubset(set(sim_tick.keys()))
    assert core_keys.issubset(set(real_payload.keys()))
    # Both must use identical ``kind`` discriminator so a single subscriber matches.
    assert sim_tick["kind"] == real_payload["kind"] == "collar.reading"


@pytest.mark.asyncio
async def test_bridge_skips_registry_miss_without_cross_talk() -> None:
    """Unknown DevEUI must not produce an MQTT publish — isolation guarantee."""
    registry = _RecordingRegistry({"A8610A3453210A00": ("ranch_a", "A001")})
    mqtt = _RecordingMqtt()
    bridge = ChirpStackBridge(mqtt_publish=mqtt, registry=registry, decoder=_dp.decode)

    # Craft a valid payload but from an unknown DevEUI.
    tick = CollarSimEmitter(ranch_id="ranch_a", cow_tag="A001", seed=42).tick()
    raw = _sim_tick_to_raw_bytes(tick)
    event = _wrap_in_chirpstack_event(raw, dev_eui="DEADBEEFDEADBEEF")

    ok = await bridge.handle_raw_event(event)
    assert ok is False
    assert mqtt.published == []
    # And the stats counter records the skip.
    assert bridge.stats["skipped"] >= 1
    assert bridge.stats["ok"] == 0
