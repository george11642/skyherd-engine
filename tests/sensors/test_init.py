"""Tests for skyherd.sensors.__init__ — public API and publish helper."""

from __future__ import annotations

import pytest

from skyherd.sensors import EMITTERS, Sensor, SensorBus, publish, run_all


def test_exports_available() -> None:
    """All documented public names are importable from skyherd.sensors."""
    assert Sensor is not None
    assert SensorBus is not None
    assert EMITTERS is not None
    assert run_all is not None
    assert publish is not None


def test_emitters_has_all_seven() -> None:
    """EMITTERS registry contains all 7 sensor kinds."""
    expected = {"water", "trough_cam", "thermal", "fence", "collar", "acoustic", "weather"}
    assert set(EMITTERS.keys()) == expected


@pytest.mark.asyncio
async def test_publish_with_mock_bus(world, mock_bus) -> None:
    """publish() with a bus kwarg routes directly through that bus."""
    payload = {"ts": 1.0, "kind": "test.event", "ranch": "ranch_a", "entity": "x"}
    await publish("skyherd/ranch_a/test/x", payload, bus=mock_bus)

    msgs = mock_bus.all_payloads("skyherd/ranch_a/test/x")
    assert len(msgs) == 1
    assert msgs[0]["kind"] == "test.event"
