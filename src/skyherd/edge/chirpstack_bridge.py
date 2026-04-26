"""ChirpStack v4 uplink → SkyHerd MQTT bridge.

ChirpStack v4's MQTT integration publishes an event for every uplink frame it
receives to the topic pattern::

    application/{application_id}/device/{dev_eui}/event/up

The payload is a JSON object with (at minimum) ``deviceInfo.devEui``,
``fPort``, ``fCnt``, and ``data`` (base64-encoded raw LoRaWAN payload).

This module wires that stream into SkyHerd's canonical collar topic::

    skyherd/{ranch_id}/collar/{cow_tag}

so that a real RAK3172 collar is indistinguishable, from every agent's point of
view, from a simulated :class:`skyherd.sensors.collar.CollarSensor`.

Pipeline
--------
1. :class:`ChirpStackMqttClient` subscribes to the ChirpStack uplink topic and
   yields raw payload bytes.
2. :class:`ChirpStackBridge` decodes each payload:
   - parse the ChirpStack event JSON → :class:`ChirpStackUplink`
   - look up the DevEUI in :class:`CollarRegistry` → (ranch_id, cow_tag)
   - base64-decode ``data`` → 16 raw bytes
   - invoke the injected decoder (``decode_payload.decode``) → ``CollarReading``
   - publish the reading to SkyHerd MQTT.
3. Any malformed event is logged and skipped (never crashes the loop).

The bridge never introduces wall-clock into the decode path: an optional
``ts_provider`` callable is used to stamp readings for replay determinism.

Schema contract
---------------
The published payload matches :class:`CollarReading.to_mqtt_payload` and, by
construction, the dict emitted by :meth:`CollarSensor.tick`. See
``hardware/collar/provisioning/decode_payload.py`` for the canonical dataclass.

Registry file
-------------
``runtime/collars/registry.json`` (path overridable via
``SKYHERD_COLLAR_REGISTRY``). Format::

    {
      "A8610A3453210A00": {"ranch": "ranch_a", "cow_tag": "A001"},
      "A8610A3453210A01": {"ranch": "ranch_a", "cow_tag": "A002"}
    }

Keys are case-insensitive DevEUI hex strings (16 chars).
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import importlib.util
import json
import logging
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_REGISTRY_ENV = "SKYHERD_COLLAR_REGISTRY"
_DEFAULT_REGISTRY_RELPATH = Path("runtime") / "collars" / "registry.json"
_EXPECTED_PAYLOAD_SIZE = 16
_UPLINK_TOPIC_TEMPLATE = "application/{app_id}/device/+/event/up"
_CANONICAL_TOPIC_TEMPLATE = "skyherd/{ranch}/collar/{cow_tag}"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChirpStackUplink:
    """Subset of ChirpStack v4 uplink event fields we care about."""

    dev_eui: str
    app_id: str
    f_port: int
    f_cnt: int
    payload_b64: str
    rx_ts: float


# ---------------------------------------------------------------------------
# Decode-payload shim (provisioning dir is not a package)
# ---------------------------------------------------------------------------


def _load_decode_payload() -> Any:
    """Dynamically import hardware/collar/provisioning/decode_payload.py.

    Tests monkeypatch this to inject a fake decoder. The module is cached in
    ``sys.modules`` to satisfy Python 3.13's ``@dataclass`` machinery (which
    reads back ``sys.modules[cls.__module__]`` during class construction).
    """
    import sys as _sys

    cache_name = "_skyherd_decode_payload"
    if cache_name in _sys.modules:
        return _sys.modules[cache_name]

    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "hardware" / "collar" / "provisioning" / "decode_payload.py"
    if not module_path.is_file():
        raise FileNotFoundError(
            f"Expected decode_payload.py at {module_path} "
            "(ensure hardware/collar/provisioning is checked in)"
        )
    spec = importlib.util.spec_from_file_location(cache_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    _sys.modules[cache_name] = module  # MUST be before exec_module for dataclass
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Event parser
# ---------------------------------------------------------------------------


def _parse_uplink_event(raw: bytes | str | dict[str, Any]) -> ChirpStackUplink | None:
    """Parse a single ChirpStack v4 uplink event into a :class:`ChirpStackUplink`.

    Returns ``None`` on malformed input (logged at WARNING level).
    """
    try:
        if isinstance(raw, dict):
            obj = raw
        elif isinstance(raw, (bytes, bytearray)):
            obj = json.loads(raw.decode("utf-8"))
        else:
            obj = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Malformed uplink JSON: %s", exc)
        return None

    if not isinstance(obj, dict):
        logger.warning("Uplink event is not a JSON object: %s", type(obj).__name__)
        return None

    device_info = obj.get("deviceInfo") or {}
    dev_eui_raw = device_info.get("devEui") or obj.get("devEui")
    if not dev_eui_raw:
        logger.warning("Uplink missing devEui")
        return None

    app_id = str(device_info.get("applicationId") or obj.get("applicationId") or "")
    f_port = int(obj.get("fPort", 0) or 0)
    f_cnt = int(obj.get("fCnt", 0) or 0)

    payload_b64 = obj.get("data")
    if not isinstance(payload_b64, str):
        logger.warning("Uplink missing or non-string 'data' field (DevEUI=%s)", dev_eui_raw)
        return None

    rx_ts_raw = obj.get("rxInfo", [{}])[0].get("gatewayTime") if obj.get("rxInfo") else None
    try:
        rx_ts = float(rx_ts_raw) if rx_ts_raw is not None else time.time()
    except (TypeError, ValueError):
        rx_ts = time.time()

    return ChirpStackUplink(
        dev_eui=str(dev_eui_raw).upper(),
        app_id=app_id,
        f_port=f_port,
        f_cnt=f_cnt,
        payload_b64=payload_b64,
        rx_ts=rx_ts,
    )


# ---------------------------------------------------------------------------
# Collar registry
# ---------------------------------------------------------------------------


class CollarRegistry:
    """DevEUI → (ranch_id, cow_tag) lookup backed by ``registry.json``.

    The registry is reloaded on every :meth:`lookup` call so that a fresh
    ``register-collar.py`` run takes effect without a bridge restart. For
    high-frequency callers, set ``cache_ttl_s > 0`` in the constructor.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        cache_ttl_s: float = 5.0,
        ts_provider: Callable[[], float] | None = None,
    ) -> None:
        if path is None:
            env_path = os.environ.get(_DEFAULT_REGISTRY_ENV)
            if env_path:
                self._path = Path(env_path)
            else:
                repo_root = Path(__file__).resolve().parents[3]
                self._path = repo_root / _DEFAULT_REGISTRY_RELPATH
        else:
            self._path = Path(path)
        self._cache: dict[str, dict[str, str]] = {}
        self._cache_loaded_ts: float = -1.0
        self._cache_ttl_s = float(cache_ttl_s)
        self._ts_provider = ts_provider or time.monotonic

    def _load_if_stale(self) -> None:
        now = self._ts_provider()
        if self._cache and (now - self._cache_loaded_ts) < self._cache_ttl_s:
            return
        if not self._path.is_file():
            logger.debug("Collar registry missing at %s — all lookups will miss", self._path)
            self._cache = {}
            self._cache_loaded_ts = now
            return
        try:
            raw = self._path.read_text()
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load collar registry %s: %s", self._path, exc)
            self._cache = {}
            self._cache_loaded_ts = now
            return
        if not isinstance(data, dict):
            logger.warning("Collar registry %s is not a JSON object — ignoring", self._path)
            self._cache = {}
        else:
            self._cache = {k.upper(): v for k, v in data.items() if isinstance(v, dict)}
        self._cache_loaded_ts = now

    def lookup(self, dev_eui: str) -> tuple[str, str] | None:
        """Return ``(ranch_id, cow_tag)`` for ``dev_eui`` or ``None`` if unknown."""
        self._load_if_stale()
        entry = self._cache.get(dev_eui.upper())
        if entry is None:
            logger.debug("Unknown DevEUI %s (registry has %d entries)", dev_eui, len(self._cache))
            return None
        ranch = entry.get("ranch")
        cow_tag = entry.get("cow_tag") or entry.get("entity")
        if not (ranch and cow_tag):
            logger.warning("Registry entry for %s missing ranch or cow_tag", dev_eui)
            return None
        return (str(ranch), str(cow_tag))

    def size(self) -> int:
        """Return the number of loaded registry entries (forces a load)."""
        self._load_if_stale()
        return len(self._cache)


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------


MqttPublishFn = Callable[[str, bytes], Awaitable[None]]


class ChirpStackBridge:
    """Consumes ChirpStack uplink events, publishes SkyHerd collar readings.

    Dependencies are injected to keep the bridge unit-testable without real
    MQTT, ChirpStack, or filesystem registries.
    """

    def __init__(
        self,
        *,
        mqtt_publish: MqttPublishFn,
        registry: CollarRegistry,
        decoder: Callable[[bytes, str, str], Any] | None = None,
        ts_provider: Callable[[], float] | None = None,
    ) -> None:
        self._mqtt_publish = mqtt_publish
        self._registry = registry
        self._ts_provider = ts_provider
        if decoder is None:
            dp = _load_decode_payload()
            self._decoder: Callable[[bytes, str, str], Any] = dp.decode
        else:
            self._decoder = decoder
        self._stats = {"ok": 0, "skipped": 0}

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    async def handle_raw_event(self, raw: bytes | str | dict[str, Any]) -> bool:
        """Process one raw ChirpStack uplink event.

        Returns True on successful publish, False on any skip (malformed,
        unknown DevEUI, bad base64, wrong payload size). Every skip is logged.
        """
        uplink = _parse_uplink_event(raw)
        if uplink is None:
            self._stats["skipped"] += 1
            return False

        resolved = self._registry.lookup(uplink.dev_eui)
        if resolved is None:
            logger.info(
                "Skipping uplink from unknown DevEUI %s (fCnt=%d)",
                uplink.dev_eui,
                uplink.f_cnt,
            )
            self._stats["skipped"] += 1
            return False
        ranch_id, cow_tag = resolved

        try:
            payload_bytes = base64.b64decode(uplink.payload_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            logger.warning("Bad base64 in uplink for %s: %s", uplink.dev_eui, exc)
            self._stats["skipped"] += 1
            return False

        if len(payload_bytes) != _EXPECTED_PAYLOAD_SIZE:
            logger.warning(
                "Unexpected payload size %d for DevEUI %s (expected %d)",
                len(payload_bytes),
                uplink.dev_eui,
                _EXPECTED_PAYLOAD_SIZE,
            )
            self._stats["skipped"] += 1
            return False

        ts = self._ts_provider() if self._ts_provider is not None else uplink.rx_ts
        try:
            reading = self._decoder(payload_bytes, ranch_id, cow_tag)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Decoder error for DevEUI %s (%s): %s", uplink.dev_eui, type(exc).__name__, exc
            )
            self._stats["skipped"] += 1
            return False

        # CollarReading is a frozen dataclass; we replicate its to_mqtt_payload
        # but substitute our replay-safe ts if provided.
        try:
            payload_dict = reading.to_mqtt_payload()
        except AttributeError:
            logger.warning("Decoded object for DevEUI %s has no to_mqtt_payload()", uplink.dev_eui)
            self._stats["skipped"] += 1
            return False

        if self._ts_provider is not None:
            payload_dict["ts"] = ts

        topic = _CANONICAL_TOPIC_TEMPLATE.format(ranch=ranch_id, cow_tag=cow_tag)
        payload_json = json.dumps(
            payload_dict, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()

        await self._mqtt_publish(topic, payload_json)
        self._stats["ok"] += 1
        logger.debug(
            "Published %s (DevEUI=%s fCnt=%d bat=%.1f%%)",
            topic,
            uplink.dev_eui,
            uplink.f_cnt,
            payload_dict.get("battery_pct", -1),
        )
        return True


async def run_forever(
    bridge: ChirpStackBridge,
    client: Any,
    *,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Pump ``client.uplinks()`` through ``bridge.handle_raw_event`` until cancelled.

    ``client`` must expose ``async uplinks() -> AsyncIterator[bytes | dict]``.
    """
    iterator: AsyncIterator[bytes | dict[str, Any]] = client.uplinks()
    async for raw in iterator:
        if stop_event is not None and stop_event.is_set():
            return
        try:
            await bridge.handle_raw_event(raw)
        except asyncio.CancelledError:  # noqa: PERF203
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled bridge error: %s", exc)


# ---------------------------------------------------------------------------
# Real MQTT client (integration-only)
# ---------------------------------------------------------------------------


class ChirpStackMqttClient:  # pragma: no cover  (integration-only)
    """Thin wrapper around ``aiomqtt.Client`` that yields raw uplink payloads.

    Not exercised in unit tests (requires a real broker). Integration tests
    substitute a fake client that implements the same ``uplinks()`` async
    iterator protocol. Exercise path is the H4 runbook.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int = 1883,
        username: str | None = None,
        password: str | None = None,
        app_id: str,
        tls: bool = False,
        client_id: str = "skyherd-chirpstack-bridge",
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._app_id = app_id
        self._tls = tls
        self._client_id = client_id
        self._client: Any = None

    async def __aenter__(self) -> ChirpStackMqttClient:
        import aiomqtt

        kwargs: dict[str, Any] = {
            "hostname": self._host,
            "port": self._port,
            "identifier": self._client_id,
        }
        if self._username:
            kwargs["username"] = self._username
        if self._password:
            kwargs["password"] = self._password
        self._client = aiomqtt.Client(**kwargs)
        await self._client.__aenter__()
        topic = _UPLINK_TOPIC_TEMPLATE.format(app_id=self._app_id)
        await self._client.subscribe(topic)
        logger.info("Subscribed to ChirpStack uplink topic: %s", topic)
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._client is not None:
            await self._client.__aexit__(*exc_info)
            self._client = None

    async def uplinks(self) -> AsyncIterator[bytes]:
        if self._client is None:
            raise RuntimeError("ChirpStackMqttClient.uplinks() called outside `async with`")
        async for message in self._client.messages:
            payload = message.payload
            if isinstance(payload, (bytes, bytearray)):
                yield bytes(payload)
            elif isinstance(payload, str):
                yield payload.encode()
            else:
                logger.debug("Ignoring non-bytes MQTT payload: %s", type(payload).__name__)


__all__ = [
    "ChirpStackBridge",
    "ChirpStackMqttClient",
    "ChirpStackUplink",
    "CollarRegistry",
    "run_forever",
]
