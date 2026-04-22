"""SensorBus — MQTT publish/subscribe bus with optional embedded amqtt broker.

If ``MQTT_URL`` env var is unset, an in-process amqtt broker is started on
``mqtt://localhost:1883``.  If set, the bus connects to that external broker.

Publish path also mirrors every reading into the attestation ledger when one
is supplied.

The bus holds ONE long-lived :class:`aiomqtt.Client` opened in :meth:`start`
and closed in :meth:`stop`.  All ``publish`` calls reuse that connection.
A reconnect loop with exponential back-off (1 s → 2 s → 4 s … capped at 30 s)
handles broker restarts transparently.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import aiomqtt

if TYPE_CHECKING:
    from skyherd.attest.ledger import Ledger

logger = logging.getLogger(__name__)

_DEFAULT_BROKER_HOST = "localhost"
_DEFAULT_BROKER_PORT = 1883
_DEFAULT_MQTT_URL = f"mqtt://{_DEFAULT_BROKER_HOST}:{_DEFAULT_BROKER_PORT}"

# Reconnect back-off: 1 s → 2 s → 4 s → 8 s → … capped at 30 s
_BACKOFF_BASE_S = 1.0
_BACKOFF_CAP_S = 30.0

# Module-level in-memory ring buffer keyed by sensor kind.
# Each deque holds the last 256 published payloads for that kind.
_BUS_STATE: dict[str, deque[dict[str, Any]]] = {}


def get_bus_state() -> dict[str, deque[dict[str, Any]]]:
    """Return a live reference to the module-level sensor bus state.

    The dict is keyed by sensor kind (e.g. ``"water.tank"``, ``"fence.breach"``).
    Each value is a :class:`collections.deque` capped at 256 entries (newest last).
    Callers that need a snapshot should copy: ``dict(get_bus_state())``.
    """
    return _BUS_STATE


def _canonical_json(payload: dict[str, Any]) -> str:
    """Deterministic JSON: sorted keys, compact separators."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


class _EmbeddedBroker:
    """Thin wrapper around an amqtt broker running in the same event loop."""

    def __init__(self) -> None:
        self._broker: Any = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the embedded broker and wait until it is ready."""
        try:
            from amqtt.broker import Broker  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "amqtt is required for the embedded broker. Run: uv add amqtt"
            ) from exc

        config = {
            "listeners": {
                "default": {
                    "type": "tcp",
                    "bind": f"{_DEFAULT_BROKER_HOST}:{_DEFAULT_BROKER_PORT}",
                }
            },
            "plugins": {
                "amqtt.plugins.authentication.AnonymousAuthPlugin": {},
            },
        }
        self._broker = Broker(config)
        await self._broker.start()
        logger.info("Embedded amqtt broker started on port %s", _DEFAULT_BROKER_PORT)

    async def stop(self) -> None:
        if self._broker is not None:
            await self._broker.shutdown()
            logger.info("Embedded amqtt broker stopped")


class SensorBus:
    """Async MQTT bus used by all sensor emitters.

    Holds ONE long-lived :class:`aiomqtt.Client` for all publishes.
    Call :meth:`start` once before publishing; call :meth:`stop` to clean up.

    Usage::

        bus = SensorBus()
        await bus.start()
        try:
            await bus.publish("skyherd/ranch_a/water/tank_1", {...})
        finally:
            await bus.stop()
    """

    def __init__(self) -> None:
        self._mqtt_url: str = os.environ.get("MQTT_URL", _DEFAULT_MQTT_URL)
        self._use_embedded: bool = "MQTT_URL" not in os.environ
        self._embedded: _EmbeddedBroker | None = None
        self._host, self._port = self._parse_url(self._mqtt_url)
        # Persistent publish client — opened in start(), closed in stop()
        self._client: aiomqtt.Client | None = None
        self._client_lock: asyncio.Lock = asyncio.Lock()
        self._connect_count: int = 0  # for test introspection

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Launch embedded broker (if needed) and open the persistent client."""
        if self._use_embedded:
            self._embedded = _EmbeddedBroker()
            await self._embedded.start()
            # Give the broker a moment to bind
            await asyncio.sleep(0.1)
        await self._open_client()
        logger.info(
            "SensorBus ready — broker %s:%s (embedded=%s)",
            self._host,
            self._port,
            self._use_embedded,
        )

    async def stop(self) -> None:
        """Close the persistent MQTT client and shut down broker (if embedded)."""
        await self._close_client()
        if self._embedded is not None:
            await self._embedded.stop()
            self._embedded = None

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    async def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        qos: int = 0,
        ledger: Ledger | None = None,
    ) -> None:
        """Serialize *payload* and publish to *topic* via the persistent client.

        Reconnects with exponential back-off if the broker dropped the
        connection since the last publish.

        If *ledger* is provided, the reading is also appended to the
        attestation chain as ``(source=topic, kind=payload["kind"], payload=payload)``.
        """
        raw = _canonical_json(payload)
        client = await self._ensure_connected()
        await client.publish(topic, payload=raw.encode(), qos=qos)

        # Accumulate in module-level ring buffer for MCP sensor tool access.
        kind = payload.get("kind", "sensor.reading")
        if kind not in _BUS_STATE:
            _BUS_STATE[kind] = deque(maxlen=256)
        _BUS_STATE[kind].append(payload)

        if ledger is not None:
            # Mirror into ledger — synchronous call (SQLite is fast enough)
            ledger.append(source=topic, kind=kind, payload=payload)

    # ------------------------------------------------------------------
    # Internal connection helpers
    # ------------------------------------------------------------------

    async def _open_client(self) -> None:
        """Open and enter a fresh aiomqtt.Client context."""
        client = aiomqtt.Client(hostname=self._host, port=self._port)
        await client.__aenter__()
        self._client = client
        self._connect_count += 1
        logger.debug("SensorBus: MQTT client connected (connect #%d)", self._connect_count)

    async def _close_client(self) -> None:
        """Exit the aiomqtt.Client context if open."""
        if self._client is not None:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass
            self._client = None

    async def _ensure_connected(self) -> aiomqtt.Client:
        """Return the live client, reconnecting with back-off if disconnected."""
        async with self._client_lock:
            if self._client is not None:
                return self._client
            # Back-off reconnect loop
            backoff = _BACKOFF_BASE_S
            while True:
                try:
                    await self._open_client()
                    assert self._client is not None
                    return self._client
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "SensorBus: reconnect failed (%s) — retrying in %.0f s",
                        exc,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, _BACKOFF_CAP_S)

    # ------------------------------------------------------------------
    # Subscribe
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def subscribe(
        self, topic_pattern: str
    ) -> AsyncIterator[AsyncIterator[tuple[str, dict[str, Any]]]]:
        """Async context manager that yields an async iterator of (topic, payload) pairs.

        Usage::

            async with bus.subscribe("skyherd/#") as messages:
                async for topic, payload in messages:
                    ...
        """
        async with aiomqtt.Client(hostname=self._host, port=self._port) as client:
            await client.subscribe(topic_pattern)

            async def _iter() -> AsyncIterator[tuple[str, dict[str, Any]]]:
                async for message in client.messages:
                    try:
                        data = json.loads(message.payload)
                    except (json.JSONDecodeError, TypeError):
                        logger.warning("Non-JSON message on %s — skipped", message.topic)
                        continue
                    yield str(message.topic), data

            yield _iter()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_url(url: str) -> tuple[str, int]:
        """Parse ``mqtt://host:port`` → (host, port).  Defaults to port 1883."""
        # Strip scheme
        without_scheme = url.split("://", 1)[-1]
        if ":" in without_scheme:
            host, port_str = without_scheme.rsplit(":", 1)
            try:
                return host, int(port_str)
            except ValueError:
                pass
        return without_scheme, _DEFAULT_BROKER_PORT
