"""Shared fixtures for sensor tests.

Unit-level sensor tests use a ``MockBus`` that captures published messages
in-memory — no real MQTT broker needed.  The integration test (test_bus.py)
uses the embedded amqtt broker.
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from skyherd.world.cattle import Cow, Herd
from skyherd.world.clock import Clock
from skyherd.world.predators import PredatorSpawner
from skyherd.world.terrain import Terrain, TerrainConfig
from skyherd.world.weather import WeatherDriver
from skyherd.world.world import World

_RANCH_YAML = Path(__file__).parents[2] / "worlds" / "ranch_a.yaml"


# ---------------------------------------------------------------------------
# MockBus — in-memory capture of all published messages
# ---------------------------------------------------------------------------


class MockBus:
    """Drop-in replacement for SensorBus that records all published payloads."""

    def __init__(self) -> None:
        self.published: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._ledger_appends: list[dict[str, Any]] = []

    async def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        qos: int = 0,
        ledger: Any = None,
    ) -> None:
        self.published[topic].append(payload)
        if ledger is not None:
            kind = payload.get("kind", "sensor.reading")
            ledger.append(source=topic, kind=kind, payload=payload)
            self._ledger_appends.append({"topic": topic, "kind": kind, "payload": payload})

    def all_payloads(self, topic: str) -> list[dict[str, Any]]:
        return list(self.published.get(topic, []))

    def all_kinds(self) -> list[str]:
        return [p["kind"] for msgs in self.published.values() for p in msgs]

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


# ---------------------------------------------------------------------------
# World fixture (full ranch_a, 50 cows)
# ---------------------------------------------------------------------------


@pytest.fixture()
def world() -> World:
    """Return a deterministic World using ranch_a.yaml (50 cows)."""
    rng = random.Random(42)
    terrain_config = TerrainConfig.from_yaml(_RANCH_YAML)
    terrain = Terrain(terrain_config)

    start_utc = datetime(2026, 4, 21, 13, 0, 0, tzinfo=UTC)
    clock = Clock(sim_start_utc=start_utc, rate=1.0)

    cows: list[Cow] = []
    for i, entry in enumerate(terrain_config.cattle_spawn):
        cow = Cow(
            id=f"cow_{i:03d}",
            tag=entry.tag,
            pos=entry.pos,
            paddock_id=entry.paddock,
            bcs=entry.bcs,
            thirst=rng.uniform(0.1, 0.4),
            hunger=rng.uniform(0.1, 0.3),
            pregnancy_days_remaining=(
                entry.pregnancy_days_remaining if entry.pregnant else None
            ),
        )
        cows.append(cow)

    herd_rng = random.Random(rng.randint(0, 2**31))
    herd = Herd(cows=cows, rng=herd_rng)
    pred_rng = random.Random(rng.randint(0, 2**31))
    predator_spawner = PredatorSpawner(rng=pred_rng)
    weather_driver = WeatherDriver()

    return World(
        clock=clock,
        terrain=terrain,
        herd=herd,
        predator_spawner=predator_spawner,
        weather_driver=weather_driver,
    )


@pytest.fixture()
def mock_bus() -> MockBus:
    return MockBus()
