"""Regression tests: SensorBus uses ONE persistent MQTT connection per session.

C4 fix — SensorBus must not open a fresh CONNECT per publish.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from skyherd.sensors.bus import SensorBus


class _FakeClient:
    """Minimal aiomqtt.Client stub that records connect/disconnect counts."""

    _instances: list[_FakeClient] = []

    def __init__(self, **kwargs: object) -> None:
        _FakeClient._instances.append(self)
        self._publish_calls: list[tuple[str, bytes]] = []

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def publish(self, topic: str, *, payload: bytes, qos: int = 0) -> None:
        self._publish_calls.append((topic, payload))

    # aiomqtt v2 uses an async iterator for messages
    @property
    def messages(self):  # type: ignore[return]
        return self  # pragma: no cover

    def __aiter__(self):  # pragma: no cover
        return self

    async def __anext__(self):  # pragma: no cover
        raise StopAsyncIteration

    async def subscribe(self, _topic: str) -> None:  # pragma: no cover
        pass


@pytest.mark.asyncio
async def test_single_connect_for_many_publishes() -> None:
    """100 publishes must result in exactly 1 MQTT CONNECT (one persistent client)."""
    _FakeClient._instances.clear()

    with patch("skyherd.sensors.bus.aiomqtt.Client", side_effect=_FakeClient):
        bus = SensorBus()
        # Manually start without embedded broker
        bus._use_embedded = False
        await bus._open_client()

        payload = {"ts": 1.0, "kind": "test.reading", "ranch": "ranch_a", "entity": "t1"}
        for i in range(100):
            payload_i = {**payload, "seq": i}
            # Directly call publish on already-opened client
            client = await bus._ensure_connected()
            import json

            await client.publish(
                f"skyherd/ranch_a/test/t{i}", payload=json.dumps(payload_i).encode(), qos=0
            )

        await bus._close_client()

    # Only 1 client instance should have been created (1 CONNECT)
    assert len(_FakeClient._instances) == 1, (
        f"Expected 1 CONNECT, got {len(_FakeClient._instances)} — "
        "SensorBus is not reusing the persistent connection."
    )
    # All 100 publishes should have gone through that one client
    assert len(_FakeClient._instances[0]._publish_calls) == 100


@pytest.mark.asyncio
async def test_reconnect_on_missing_client() -> None:
    """If _client is None (e.g. after a broker restart), _ensure_connected reconnects."""
    _FakeClient._instances.clear()

    with patch("skyherd.sensors.bus.aiomqtt.Client", side_effect=_FakeClient):
        bus = SensorBus()
        bus._use_embedded = False

        # Simulate: client was never opened (or dropped)
        assert bus._client is None

        client = await bus._ensure_connected()
        assert client is not None
        assert bus._connect_count == 1

        # Second call reuses the same client — no new CONNECT
        client2 = await bus._ensure_connected()
        assert client2 is client
        assert bus._connect_count == 1

        await bus._close_client()

    assert len(_FakeClient._instances) == 1


@pytest.mark.asyncio
async def test_connect_count_accessible() -> None:
    """connect_count is publicly readable for test introspection."""
    _FakeClient._instances.clear()

    with patch("skyherd.sensors.bus.aiomqtt.Client", side_effect=_FakeClient):
        bus = SensorBus()
        bus._use_embedded = False
        assert bus._connect_count == 0
        await bus._open_client()
        assert bus._connect_count == 1
        await bus._close_client()
