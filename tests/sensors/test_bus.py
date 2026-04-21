"""Integration test: SensorBus pub/sub round-trip via embedded amqtt broker.

Starts a real embedded broker, publishes a message, subscribes and reads it
back, verifies the payload, and optionally mirrors to the ledger.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.sensors.bus import SensorBus

_BROKER_PORT = 18883  # non-standard to avoid collisions with local Mosquitto


@pytest.fixture()
def ledger(tmp_path: Path) -> Ledger:
    signer = Signer.generate()
    return Ledger.open(tmp_path / "test.db", signer)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_embedded_broker_pubsub() -> None:
    """Publish then subscribe — message round-trips through embedded broker."""
    os.environ.pop("MQTT_URL", None)
    bus = SensorBus()
    await bus.start()

    published_payloads: list[dict] = []
    target_topic = "skyherd/test/water/tank_99"

    # Subscribe in a background task
    async def _collect() -> None:
        async with bus.subscribe(target_topic) as messages:
            async for _topic, payload in messages:
                published_payloads.append(payload)
                return  # collect exactly one

    collect_task = asyncio.create_task(_collect())
    # Give subscriber time to connect
    await asyncio.sleep(0.3)

    payload_in = {"ts": 12345.0, "kind": "water.reading", "ranch": "test", "entity": "tank_99", "level_pct": 42.0}
    await bus.publish(target_topic, payload_in)

    await asyncio.wait_for(collect_task, timeout=5.0)
    await bus.stop()

    assert len(published_payloads) == 1
    received = published_payloads[0]
    assert received["level_pct"] == 42.0
    assert received["kind"] == "water.reading"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_ledger_mirror_on_publish(ledger: Ledger) -> None:
    """Publishing with a ledger argument appends the event to the chain."""
    os.environ.pop("MQTT_URL", None)
    bus = SensorBus()
    await bus.start()

    payload = {
        "ts": 9999.0,
        "kind": "fence.breach",
        "ranch": "ranch_a",
        "entity": "fence_south",
        "segment_id": "fence_south",
        "subject_kind": "predator",
        "thermal_hint": 0.4,
    }
    await bus.publish("skyherd/ranch_a/fence/fence_south", payload, ledger=ledger)
    await bus.stop()

    events = list(ledger.iter_events())
    assert len(events) == 1
    ev = events[0]
    assert ev.source == "skyherd/ranch_a/fence/fence_south"
    assert ev.kind == "fence.breach"
    result = ledger.verify()
    assert result.valid
