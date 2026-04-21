"""SensorBus — MQTT publish/subscribe bus with optional embedded amqtt broker.

If ``MQTT_URL`` env var is unset, an in-process amqtt broker is started on
``mqtt://localhost:1883``.  If set, the bus connects to that external broker.

Publish path also mirrors every reading into the attestation ledger when one
is supplied.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
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
                "amqtt is required for the embedded broker. "
                "Run: uv add amqtt"
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

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Launch embedded broker (if needed) and verify connectivity."""
        if self._use_embedded:
            self._embedded = _EmbeddedBroker()
            await self._embedded.start()
            # Give the broker a moment to bind
            await asyncio.sleep(0.1)
        logger.info(
            "SensorBus ready — broker %s:%s (embedded=%s)",
            self._host,
            self._port,
            self._use_embedded,
        )

    async def stop(self) -> None:
        """Gracefully shut down broker (if embedded)."""
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
        """Serialize *payload* and publish to *topic*.

        If *ledger* is provided, the reading is also appended to the
        attestation chain as ``(source=topic, kind=payload["kind"], payload=payload)``.
        """
        raw = _canonical_json(payload)
        async with aiomqtt.Client(hostname=self._host, port=self._port) as client:
            await client.publish(topic, payload=raw.encode(), qos=qos)

        if ledger is not None:
            kind = payload.get("kind", "sensor.reading")
            # Mirror into ledger — synchronous call (SQLite is fast enough)
            ledger.append(source=topic, kind=kind, payload=payload)

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
