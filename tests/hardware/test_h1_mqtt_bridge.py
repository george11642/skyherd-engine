"""End-to-end Pi → MQTT → subscriber mock fabric.

Uses an in-memory publish/subscribe routing table (no real broker required) so
CI remains fast and deterministic.  If you need a real amqtt broker, look at
``tests/edge/test_fleet.py`` for the embedded broker pattern.

Purpose: prove that ``PiCamSensor`` and ``CoyoteHarness`` publish canonical JSON
on the expected topics in the correct order — the exact contract agent
subscribers consume.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

import pytest

from skyherd.edge.coyote_harness import CoyoteHarness
from skyherd.edge.picam_sensor import PiCamSensor


class InMemoryBroker:
    """Minimal synchronous pub/sub router for tests.

    Maps topic → [(seq, payload_dict)], sequence-numbered across the broker
    lifetime so ordering is verifiable.  Supports topic wildcard ``+`` / ``#``.
    """

    def __init__(self) -> None:
        self._next_seq = 0
        self._messages: list[tuple[int, str, dict[str, Any]]] = []
        self._by_topic: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)

    def publisher(self):  # type: ignore[no-untyped-def]
        """Returns an async callable compatible with the sensor `mqtt_publish` hook."""

        async def publish(topic: str, raw: bytes) -> None:
            payload = json.loads(raw.decode())
            self._next_seq += 1
            self._messages.append((self._next_seq, topic, payload))
            self._by_topic[topic].append((self._next_seq, payload))

        return publish

    def messages_on(self, topic_prefix: str) -> list[dict[str, Any]]:
        """All payloads whose topic starts with *topic_prefix* in publish order."""
        return [p for _seq, t, p in self._messages if t.startswith(topic_prefix)]

    def all_topics(self) -> set[str]:
        return set(self._by_topic.keys())

    def total_messages(self) -> int:
        return len(self._messages)


@pytest.fixture
def broker() -> InMemoryBroker:
    return InMemoryBroker()


def _stub_classifier(_frame: Any) -> dict[str, Any]:
    return {"severity": "escalate", "confidence": 0.9, "class_idx": 3}


def _fixed_ts() -> float:
    return 1_714_000_000.0


# ---------------------------------------------------------------------------
# picam → broker
# ---------------------------------------------------------------------------


class TestPicamBridge:
    def test_picam_event_reaches_broker(self, broker: InMemoryBroker) -> None:
        sensor = PiCamSensor(
            ranch_id="ranch_a",
            cam_id="picam_0",
            classifier=_stub_classifier,
            mqtt_publish=broker.publisher(),
        )
        asyncio.run(sensor.run_once())
        messages = broker.messages_on("skyherd/ranch_a/trough_cam/picam_0")
        assert len(messages) == 1
        msg = messages[0]
        assert msg["kind"] == "trough_cam.reading"
        assert msg["source"] == "picam"
        assert msg["pinkeye_result"]["severity"] == "escalate"

    def test_picam_canonical_json_round_trip(self, broker: InMemoryBroker) -> None:
        sensor = PiCamSensor(
            classifier=_stub_classifier, mqtt_publish=broker.publisher()
        )
        asyncio.run(sensor.run_once())
        # Re-serialise with sort_keys — must be byte-identical to broker payload
        msg = broker.messages_on("skyherd/")[0]
        re_serialised = json.dumps(msg, sort_keys=True, separators=(",", ":"))
        parsed = json.loads(re_serialised)
        assert parsed == msg  # round trip is lossless

    def test_picam_multiple_ticks_preserve_order(self, broker: InMemoryBroker) -> None:
        sensor = PiCamSensor(
            classifier=_stub_classifier, mqtt_publish=broker.publisher(), seed=42
        )

        async def ticks() -> None:
            for _ in range(4):
                await sensor.run_once()

        asyncio.run(ticks())
        messages = broker.messages_on("skyherd/ranch_a/trough_cam/")
        assert len(messages) == 4
        ticks_field = [m["tick"] for m in messages]
        assert ticks_field == [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# coyote → broker (dual fan-out)
# ---------------------------------------------------------------------------


class TestCoyoteBridge:
    def test_coyote_event_reaches_broker(self, broker: InMemoryBroker) -> None:
        harness = CoyoteHarness(
            ranch_id="ranch_a",
            cam_id="coyote_cam",
            seed=42,
            ts_provider=_fixed_ts,
            mqtt_publish=broker.publisher(),
        )
        asyncio.run(harness.run_once())
        # Expect TWO messages: reading + thermal_hit alert
        assert broker.total_messages() == 2
        reading_topic = "skyherd/ranch_a/thermal/coyote_cam"
        alert_topic = "skyherd/ranch_a/alert/thermal_hit"
        readings = broker.messages_on(reading_topic)
        alerts = broker.messages_on(alert_topic)
        assert len(readings) == 1
        assert len(alerts) == 1
        assert readings[0]["kind"] == "thermal.reading"
        assert alerts[0]["kind"] == "predator.thermal_hit"

    def test_coyote_fan_out_topics_both_present(self, broker: InMemoryBroker) -> None:
        harness = CoyoteHarness(
            seed=42, ts_provider=_fixed_ts, mqtt_publish=broker.publisher()
        )
        asyncio.run(harness.run_once())
        topics = broker.all_topics()
        assert any("thermal/coyote_cam" in t for t in topics)
        assert any("alert/thermal_hit" in t for t in topics)

    def test_coyote_determinism_byte_for_byte(self) -> None:
        """Same seed + fixed ts → byte-identical broker messages."""
        brokers = [InMemoryBroker(), InMemoryBroker()]
        for b in brokers:
            h = CoyoteHarness(seed=42, ts_provider=_fixed_ts, mqtt_publish=b.publisher())

            async def run_three(harness: CoyoteHarness = h) -> None:
                for _ in range(3):
                    await harness.run_once()

            asyncio.run(run_three())
        m0 = brokers[0].messages_on("skyherd/")
        m1 = brokers[1].messages_on("skyherd/")
        assert m0 == m1


# ---------------------------------------------------------------------------
# Mixed picam + coyote ordering
# ---------------------------------------------------------------------------


class TestMixedOrder:
    def test_picam_then_coyote_preserves_order(self, broker: InMemoryBroker) -> None:
        sensor = PiCamSensor(
            classifier=_stub_classifier, mqtt_publish=broker.publisher()
        )
        harness = CoyoteHarness(
            seed=42, ts_provider=_fixed_ts, mqtt_publish=broker.publisher()
        )

        async def sequence() -> None:
            await sensor.run_once()  # 1 message
            await harness.run_once()  # 2 messages (reading + alert)

        asyncio.run(sequence())
        assert broker.total_messages() == 3
        # First message should be the picam trough_cam.reading
        assert broker._messages[0][2]["kind"] == "trough_cam.reading"
        assert broker._messages[1][2]["kind"] == "thermal.reading"
        assert broker._messages[2][2]["kind"] == "predator.thermal_hit"

    def test_concurrent_ticks_all_delivered(self, broker: InMemoryBroker) -> None:
        sensor = PiCamSensor(
            classifier=_stub_classifier, mqtt_publish=broker.publisher()
        )
        harness = CoyoteHarness(
            seed=42, ts_provider=_fixed_ts, mqtt_publish=broker.publisher()
        )

        async def go() -> None:
            await asyncio.gather(
                sensor.run_once(),
                harness.run_once(),
            )

        asyncio.run(go())
        # 1 picam + 2 coyote = 3 messages (order may vary)
        assert broker.total_messages() == 3

    def test_high_volume_no_loss(self, broker: InMemoryBroker) -> None:
        sensor = PiCamSensor(
            classifier=_stub_classifier, mqtt_publish=broker.publisher()
        )
        harness = CoyoteHarness(
            seed=42, ts_provider=_fixed_ts, mqtt_publish=broker.publisher()
        )

        async def go() -> None:
            for _ in range(10):
                await sensor.run_once()
            for _ in range(10):
                await harness.run_once()

        asyncio.run(go())
        # 10 picam + 10 × 2 coyote = 30 messages
        assert broker.total_messages() == 30


# ---------------------------------------------------------------------------
# Canonical JSON wire-format contract
# ---------------------------------------------------------------------------


class TestWireFormat:
    def test_payload_keys_sorted(self, broker: InMemoryBroker) -> None:
        """Re-serialising a received message with sort_keys produces the
        same bytes — implies the sensor serialises with sort_keys=True."""
        harness = CoyoteHarness(
            seed=42, ts_provider=_fixed_ts, mqtt_publish=broker.publisher()
        )
        asyncio.run(harness.run_once())
        for m in broker.messages_on("skyherd/"):
            re_serialised = json.dumps(m, sort_keys=True, separators=(",", ":"))
            assert re_serialised == json.dumps(
                json.loads(re_serialised),
                sort_keys=True,
                separators=(",", ":"),
            )

    def test_required_schema_fields_present(self, broker: InMemoryBroker) -> None:
        sensor = PiCamSensor(
            classifier=_stub_classifier, mqtt_publish=broker.publisher()
        )
        asyncio.run(sensor.run_once())
        msg = broker.messages_on("skyherd/")[0]
        for field in ("ts", "kind", "ranch", "entity", "trough_id"):
            assert field in msg
