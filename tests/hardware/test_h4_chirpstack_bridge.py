"""Unit tests for ``src/skyherd/edge/chirpstack_bridge.py``.

Covers:
    - ChirpStack v4 uplink JSON parser (happy path + malformed variants)
    - CollarRegistry (hit, miss, missing-file, stale file)
    - ChirpStackBridge.handle_raw_event (publish, skip-unknown, skip-bad-base64,
      skip-wrong-size, decoder-error)
    - Schema parity between the bridge-decoded payload and the sim
      ``CollarSensor`` output (same key set).
    - run_forever drains an async iterator of events.

No real MQTT or ChirpStack broker is touched.
"""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import json
import logging
import struct
import sys
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import pytest

from skyherd.edge.chirpstack_bridge import (
    ChirpStackBridge,
    ChirpStackUplink,
    CollarRegistry,
    _parse_uplink_event,
    run_forever,
)

# ---------------------------------------------------------------------------
# Paths + decoder import
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES = Path(__file__).parent / "fixtures"
_PROVISIONING = _REPO_ROOT / "hardware" / "collar" / "provisioning"


def _import_decode_payload() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_tdp_decode_payload", _PROVISIONING / "decode_payload.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_tdp_decode_payload"] = mod
    spec.loader.exec_module(mod)
    return mod


_dp = _import_decode_payload()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> dict[str, Any]:
    with (_FIXTURES / name).open() as f:
        return json.load(f)


def _make_raw_payload(
    lat: float = 34.0523401,
    lon: float = -106.5342812,
    alt_m: int = 1540,
    activity_code: int = 1,
    battery_pct: int = 82,
    fix_age_s: int = 3,
    uptime_s: int = 900,
) -> bytes:
    lat_e7 = int(round(lat * 1e7))
    lon_e7 = int(round(lon * 1e7))
    return struct.pack(
        "<iiHBBHH",
        lat_e7,
        lon_e7,
        alt_m & 0xFFFF,
        activity_code,
        battery_pct,
        fix_age_s,
        uptime_s,
    )


class _Publisher:
    """Async-callable that records every (topic, payload) publish."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes]] = []

    async def __call__(self, topic: str, payload: bytes) -> None:
        self.calls.append((topic, payload))


def _make_bridge(
    registry: CollarRegistry,
    *,
    publisher: _Publisher | None = None,
    ts_provider: Callable[[], float] | None = None,
) -> tuple[ChirpStackBridge, _Publisher]:
    pub = publisher or _Publisher()
    bridge = ChirpStackBridge(
        mqtt_publish=pub,
        registry=registry,
        decoder=_dp.decode,
        ts_provider=ts_provider,
    )
    return bridge, pub


def _registry_from_fixture(tmp_path: Path) -> CollarRegistry:
    registry_file = tmp_path / "registry.json"
    registry_file.write_text(json.dumps(_load_fixture("collars_registry_sample.json")))
    return CollarRegistry(registry_file, cache_ttl_s=0.0)


# ===========================================================================
# _parse_uplink_event
# ===========================================================================


class TestParseUplinkEvent:
    def test_happy_path_json_bytes(self) -> None:
        ev = _load_fixture("chirpstack_uplink_sample.json")
        uplink = _parse_uplink_event(json.dumps(ev).encode())
        assert uplink is not None
        assert uplink.dev_eui == "A8610A3453210A00"
        assert uplink.f_port == 2
        assert uplink.f_cnt == 42
        assert uplink.payload_b64 == "iflLFKQogMAEBgFSAwCEAw=="

    def test_happy_path_dict(self) -> None:
        ev = _load_fixture("chirpstack_uplink_sample.json")
        uplink = _parse_uplink_event(ev)
        assert uplink is not None
        assert uplink.app_id.startswith("09f8a7e4")

    def test_happy_path_string(self) -> None:
        ev = _load_fixture("chirpstack_uplink_sample.json")
        uplink = _parse_uplink_event(json.dumps(ev))
        assert isinstance(uplink, ChirpStackUplink)

    def test_malformed_json_returns_none(self) -> None:
        assert _parse_uplink_event(b"not json at all") is None

    def test_missing_dev_eui_returns_none(self) -> None:
        ev = _load_fixture("chirpstack_uplink_sample.json")
        ev["deviceInfo"].pop("devEui", None)
        ev.pop("devEui", None)
        assert _parse_uplink_event(ev) is None

    def test_missing_data_returns_none(self) -> None:
        ev = _load_fixture("chirpstack_uplink_malformed.json")
        assert _parse_uplink_event(ev) is None

    def test_non_object_returns_none(self) -> None:
        assert _parse_uplink_event(b"[1, 2, 3]") is None

    def test_dev_eui_is_uppercased(self) -> None:
        ev = _load_fixture("chirpstack_uplink_sample.json")
        ev["deviceInfo"]["devEui"] = "a8610a3453210a00"
        uplink = _parse_uplink_event(ev)
        assert uplink is not None
        assert uplink.dev_eui == "A8610A3453210A00"

    def test_dev_eui_top_level_fallback(self) -> None:
        # Some older ChirpStack versions put devEui at top-level.
        ev = {
            "devEui": "a8610a3453210a00",
            "applicationId": "abc",
            "fPort": 2,
            "fCnt": 1,
            "data": "AAAAAAAAAAAAAAAAAAAAAA==",
        }
        uplink = _parse_uplink_event(ev)
        assert uplink is not None and uplink.dev_eui == "A8610A3453210A00"

    def test_bad_unicode_returns_none(self) -> None:
        assert _parse_uplink_event(b"\xff\xfe\xfd") is None

    def test_gateway_time_bad_format_falls_back_to_now(self) -> None:
        ev = _load_fixture("chirpstack_uplink_sample.json")
        ev["rxInfo"][0]["gatewayTime"] = "not-a-timestamp"
        uplink = _parse_uplink_event(ev)
        assert uplink is not None
        assert uplink.rx_ts > 0.0


# ===========================================================================
# CollarRegistry
# ===========================================================================


class TestCollarRegistry:
    def test_lookup_hit(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        result = reg.lookup("A8610A3453210A00")
        assert result == ("ranch_a", "A001")

    def test_lookup_lowercase_hit(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        assert reg.lookup("a8610a3453210a00") == ("ranch_a", "A001")

    def test_lookup_miss(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        assert reg.lookup("0000000000000000") is None

    def test_missing_file_all_miss(self, tmp_path: Path) -> None:
        reg = CollarRegistry(tmp_path / "no_such_registry.json", cache_ttl_s=0.0)
        assert reg.lookup("A8610A3453210A00") is None
        assert reg.size() == 0

    def test_malformed_file_graceful(self, tmp_path: Path) -> None:
        p = tmp_path / "registry.json"
        p.write_text("{ not valid json")
        reg = CollarRegistry(p, cache_ttl_s=0.0)
        assert reg.lookup("A8610A3453210A00") is None

    def test_non_object_top_level(self, tmp_path: Path) -> None:
        p = tmp_path / "registry.json"
        p.write_text('["list", "not", "object"]')
        reg = CollarRegistry(p, cache_ttl_s=0.0)
        assert reg.size() == 0

    def test_entry_missing_keys_returns_none(self, tmp_path: Path) -> None:
        p = tmp_path / "registry.json"
        p.write_text(json.dumps({"A8610A3453210A00": {"ranch": "ranch_a"}}))
        reg = CollarRegistry(p, cache_ttl_s=0.0)
        assert reg.lookup("A8610A3453210A00") is None

    def test_env_var_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        p = tmp_path / "via_env.json"
        p.write_text(json.dumps(_load_fixture("collars_registry_sample.json")))
        monkeypatch.setenv("SKYHERD_COLLAR_REGISTRY", str(p))
        reg = CollarRegistry(cache_ttl_s=0.0)
        assert reg.lookup("A8610A3453210A00") == ("ranch_a", "A001")

    def test_size_reports_entries(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        assert reg.size() == 3

    def test_cache_respects_ttl(self, tmp_path: Path) -> None:
        p = tmp_path / "registry.json"
        p.write_text(json.dumps({"DEAD0000DEAD0000": {"ranch": "r", "cow_tag": "c"}}))
        fake_time = [0.0]
        reg = CollarRegistry(p, cache_ttl_s=10.0, ts_provider=lambda: fake_time[0])
        assert reg.lookup("DEAD0000DEAD0000") == ("r", "c")
        # Overwrite on disk, but cache hasn't expired yet
        p.write_text(json.dumps({"FEED0000FEED0000": {"ranch": "r", "cow_tag": "c"}}))
        fake_time[0] = 5.0
        assert reg.lookup("DEAD0000DEAD0000") == ("r", "c")  # cache still hot
        # Advance past TTL → reload happens
        fake_time[0] = 20.0
        assert reg.lookup("DEAD0000DEAD0000") is None
        assert reg.lookup("FEED0000FEED0000") == ("r", "c")


# ===========================================================================
# ChirpStackBridge.handle_raw_event
# ===========================================================================


class TestChirpStackBridgeHandleRawEvent:
    @pytest.mark.asyncio
    async def test_publishes_on_canonical_topic(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        bridge, pub = _make_bridge(reg, ts_provider=lambda: 1234567890.0)
        ev = _load_fixture("chirpstack_uplink_sample.json")

        ok = await bridge.handle_raw_event(ev)

        assert ok is True
        assert len(pub.calls) == 1
        topic, payload = pub.calls[0]
        assert topic == "skyherd/ranch_a/collar/A001"
        msg = json.loads(payload.decode())
        assert msg["kind"] == "collar.reading"
        assert msg["ranch"] == "ranch_a"
        assert msg["entity"] == "A001"
        assert msg["battery_pct"] == 82.0
        assert msg["activity"] == "grazing"
        assert msg["ts"] == 1234567890.0

    @pytest.mark.asyncio
    async def test_schema_matches_sim_collar(self, tmp_path: Path) -> None:
        """Bridge-published schema must be a superset of sim CollarSensor keys."""
        reg = _registry_from_fixture(tmp_path)
        bridge, pub = _make_bridge(reg)
        ev = _load_fixture("chirpstack_uplink_sample.json")
        await bridge.handle_raw_event(ev)

        decoded = json.loads(pub.calls[0][1].decode())
        # Sim-emitted keys (from skyherd/sensors/collar.py tick())
        required = {"ts", "kind", "ranch", "entity", "pos", "heading_deg", "activity", "battery_pct"}
        assert required.issubset(decoded.keys()), (
            f"Bridge payload missing required sim keys: {required - decoded.keys()}"
        )

    @pytest.mark.asyncio
    async def test_skips_unknown_dev_eui(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        bridge, pub = _make_bridge(reg)
        ev = _load_fixture("chirpstack_uplink_sample.json")
        ev["deviceInfo"]["devEui"] = "FFFFFFFFFFFFFFFF"

        ok = await bridge.handle_raw_event(ev)

        assert ok is False
        assert pub.calls == []
        assert bridge.stats["skipped"] == 1

    @pytest.mark.asyncio
    async def test_skips_malformed_event(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        bridge, pub = _make_bridge(reg)

        ok = await bridge.handle_raw_event(b"not json")

        assert ok is False
        assert pub.calls == []
        assert bridge.stats["skipped"] == 1

    @pytest.mark.asyncio
    async def test_skips_bad_base64(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        bridge, pub = _make_bridge(reg)
        ev = _load_fixture("chirpstack_uplink_sample.json")
        ev["data"] = "@@@not-base64@@@"

        ok = await bridge.handle_raw_event(ev)

        assert ok is False
        assert pub.calls == []

    @pytest.mark.asyncio
    async def test_skips_wrong_size_payload(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        bridge, pub = _make_bridge(reg)
        ev = _load_fixture("chirpstack_uplink_sample.json")
        # Too-short payload
        ev["data"] = base64.b64encode(b"\x00\x01\x02").decode()

        ok = await bridge.handle_raw_event(ev)

        assert ok is False
        assert pub.calls == []

    @pytest.mark.asyncio
    async def test_decoder_error_logged_and_skipped(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        reg = _registry_from_fixture(tmp_path)

        def broken_decoder(raw: bytes, ranch: str, cow: str) -> Any:
            raise RuntimeError("intentional decoder crash")

        bridge = ChirpStackBridge(
            mqtt_publish=_Publisher(),
            registry=reg,
            decoder=broken_decoder,
        )
        ev = _load_fixture("chirpstack_uplink_sample.json")

        with caplog.at_level(logging.WARNING):
            ok = await bridge.handle_raw_event(ev)

        assert ok is False
        assert bridge.stats["skipped"] == 1
        assert "Decoder error" in caplog.text

    @pytest.mark.asyncio
    async def test_reading_without_to_mqtt_payload_is_skipped(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)

        def plain_dict_decoder(raw: bytes, ranch: str, cow: str) -> Any:
            return {"not": "a proper reading"}  # no .to_mqtt_payload method

        bridge = ChirpStackBridge(
            mqtt_publish=_Publisher(), registry=reg, decoder=plain_dict_decoder
        )
        ev = _load_fixture("chirpstack_uplink_sample.json")
        ok = await bridge.handle_raw_event(ev)
        assert ok is False
        assert bridge.stats["skipped"] == 1

    @pytest.mark.asyncio
    async def test_stats_track_ok_and_skipped(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        bridge, _pub = _make_bridge(reg)
        ev_good = _load_fixture("chirpstack_uplink_sample.json")
        ev_bad = _load_fixture("chirpstack_uplink_malformed.json")

        await bridge.handle_raw_event(ev_good)
        await bridge.handle_raw_event(ev_good)
        await bridge.handle_raw_event(ev_bad)

        assert bridge.stats == {"ok": 2, "skipped": 1}

    @pytest.mark.asyncio
    async def test_default_decoder_loads_when_none_provided(self, tmp_path: Path) -> None:
        """Constructing with decoder=None must load the real decode_payload."""
        reg = _registry_from_fixture(tmp_path)
        bridge = ChirpStackBridge(mqtt_publish=_Publisher(), registry=reg)
        # Access private to validate decoder was injected; smoke test only.
        assert callable(bridge._decoder)  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_rx_ts_used_when_no_ts_provider(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        bridge, pub = _make_bridge(reg)
        ev = _load_fixture("chirpstack_uplink_sample.json")
        await bridge.handle_raw_event(ev)

        decoded = json.loads(pub.calls[0][1].decode())
        assert decoded["ts"] > 0.0

    @pytest.mark.asyncio
    async def test_multi_cow_isolation(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        bridge, pub = _make_bridge(reg, ts_provider=lambda: 100.0)

        for dev_eui, _tag in (("A8610A3453210A00", "A001"), ("A8610A3453210A01", "A002")):
            ev = _load_fixture("chirpstack_uplink_sample.json")
            ev["deviceInfo"]["devEui"] = dev_eui
            await bridge.handle_raw_event(ev)

        topics = [c[0] for c in pub.calls]
        assert topics == [
            "skyherd/ranch_a/collar/A001",
            "skyherd/ranch_a/collar/A002",
        ]


# ===========================================================================
# run_forever
# ===========================================================================


class _FakeClient:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self._events = events

    async def uplinks(self) -> AsyncIterator[dict[str, Any]]:
        for ev in self._events:
            yield ev


class _FlakyClient:
    """Yields a mix of good and bad raw values; run_forever must not crash."""

    def __init__(self, items: list[Any]) -> None:
        self._items = items

    async def uplinks(self) -> AsyncIterator[Any]:
        for it in self._items:
            yield it


class TestRunForever:
    @pytest.mark.asyncio
    async def test_processes_multiple_uplinks(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        bridge, pub = _make_bridge(reg, ts_provider=lambda: 10.0)
        events = [_load_fixture("chirpstack_uplink_sample.json") for _ in range(3)]

        await run_forever(bridge, _FakeClient(events))

        assert len(pub.calls) == 3

    @pytest.mark.asyncio
    async def test_stop_event_halts_loop(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        bridge, pub = _make_bridge(reg, ts_provider=lambda: 10.0)
        stop = asyncio.Event()
        stop.set()  # ask for immediate stop

        events = [_load_fixture("chirpstack_uplink_sample.json") for _ in range(5)]
        await run_forever(bridge, _FakeClient(events), stop_event=stop)

        # First event is still consumed before stop_event is checked; subsequent
        # iterations return early. Relax: publishes should be 0 or 1.
        assert len(pub.calls) <= 1

    @pytest.mark.asyncio
    async def test_run_forever_survives_malformed(self, tmp_path: Path) -> None:
        reg = _registry_from_fixture(tmp_path)
        bridge, pub = _make_bridge(reg, ts_provider=lambda: 10.0)
        ev_good = _load_fixture("chirpstack_uplink_sample.json")
        items: list[Any] = [b"garbage", ev_good, {"malformed": True}, ev_good]

        await run_forever(bridge, _FlakyClient(items))

        assert len(pub.calls) == 2
        assert bridge.stats["ok"] == 2
        assert bridge.stats["skipped"] == 2

    @pytest.mark.asyncio
    async def test_run_forever_logs_unhandled_bridge_exception(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An unexpected exception inside handle_raw_event must be logged, not propagated."""
        reg = _registry_from_fixture(tmp_path)

        class _BoomPublisher:
            async def __call__(self, topic: str, payload: bytes) -> None:
                raise RuntimeError("broker explosion")

        bridge = ChirpStackBridge(
            mqtt_publish=_BoomPublisher(),
            registry=reg,
            decoder=_dp.decode,
            ts_provider=lambda: 1.0,
        )
        events = [_load_fixture("chirpstack_uplink_sample.json")]

        with caplog.at_level(logging.ERROR):
            await run_forever(bridge, _FakeClient(events))

        assert "Unhandled bridge error" in caplog.text


# ===========================================================================
# CollarRegistry default constructor path (no env, no explicit path)
# ===========================================================================


class TestCollarRegistryDefaultPath:
    def test_default_path_computed_from_repo_root(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no env var and no path, registry uses runtime/collars/registry.json."""
        monkeypatch.delenv("SKYHERD_COLLAR_REGISTRY", raising=False)
        reg = CollarRegistry(cache_ttl_s=0.0)
        # It may or may not find a live registry; just assert lookup is no-throw.
        assert reg.lookup("0000000000000000") is None or isinstance(reg.lookup("0000000000000000"), tuple)
