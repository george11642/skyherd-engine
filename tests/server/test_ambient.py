"""Tests for AmbientDriver - the in-process scenario rotator.

Uses short/tiny scenarios via monkeypatching SCENARIOS + high speed so the
suite finishes in under a couple seconds per test.
"""

from __future__ import annotations

import asyncio
import tempfile
from typing import Any

import pytest

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.scenarios.base import _DemoMesh
from skyherd.server import ambient as ambient_mod
from skyherd.server.ambient import AmbientDriver
from skyherd.world.world import make_world

# ---------------------------------------------------------------------------
# Lightweight test doubles
# ---------------------------------------------------------------------------


class _RecordingBroadcaster:
    """Duck-typed broadcaster: records emits made by AmbientDriver."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, payload))


class _TinyScenario:
    """10-step fast-finishing scenario for ambient rotation tests."""

    name = "tiny"
    description = "tiny test scenario"
    duration_s = 20.0  # 4 steps @ _STEP_DT=5.0

    def setup(self, _world: Any) -> None:
        pass

    def inject_events(self, _world: Any, _t: float) -> list[dict[str, Any]]:
        return []

    def assert_outcome(self, _events: Any, _mesh: Any) -> None:
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_deps() -> tuple:
    world = make_world(seed=42)
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    signer = Signer.generate()
    ledger = Ledger.open(tmp.name, signer)
    mesh = _DemoMesh(ledger=ledger)
    return world, ledger, mesh


@pytest.fixture
def tiny_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Swap out the 8-scenario rotation for three tiny scenarios."""
    fake = {"tiny": _TinyScenario, "tiny2": _TinyScenario, "tiny3": _TinyScenario}
    monkeypatch.setattr(ambient_mod, "SCENARIOS", fake)
    monkeypatch.setattr(ambient_mod, "_ROTATION", ("tiny", "tiny2", "tiny3"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_driver_emits_active_and_ended(tiny_rotation: None) -> None:
    """scenario.active and scenario.ended events fire in order per scenario."""
    world, ledger, mesh = _build_deps()
    bc = _RecordingBroadcaster()
    driver = AmbientDriver(mesh=mesh, world=world, ledger=ledger, broadcaster=bc, speed=500.0)

    await driver.start()
    # Let one or two scenarios complete.
    try:
        await asyncio.wait_for(_spin_until(bc, at_least_pairs=1), timeout=5.0)
    finally:
        await driver.stop()

    kinds = [k for k, _ in bc.events]
    assert "scenario.active" in kinds
    assert "scenario.ended" in kinds
    # active always precedes ended for each scenario.
    for i in range(len(kinds) - 1):
        if kinds[i] == "scenario.active":
            # Next scenario-related event for this slot must be ended.
            tail = kinds[i + 1 :]
            assert "scenario.ended" in tail


async def test_driver_grows_external_ledger(tiny_rotation: None) -> None:
    """AmbientDriver uses the caller-provided ledger - entries accumulate there."""
    world, ledger, mesh = _build_deps()
    before = len(list(ledger.iter_events()))

    driver = AmbientDriver(mesh=mesh, world=world, ledger=ledger, broadcaster=None, speed=500.0)
    await driver.start()
    try:
        await asyncio.sleep(1.0)
    finally:
        await driver.stop()

    after = len(list(ledger.iter_events()))
    assert after > before, "ambient loop should have appended world events to caller ledger"


async def test_set_speed_updates_live(tiny_rotation: None) -> None:
    """set_speed() takes effect at runtime (checked via the speed property)."""
    world, ledger, mesh = _build_deps()
    driver = AmbientDriver(mesh=mesh, world=world, ledger=ledger, broadcaster=None, speed=500.0)
    assert driver.speed == 500.0
    driver.set_speed(30.0)
    assert driver.speed == 30.0
    driver.set_speed(90.0)
    assert driver.speed == 90.0


async def test_skip_short_circuits_current_scenario(tiny_rotation: None) -> None:
    """skip() bails out of the current scenario and the loop advances."""
    world, ledger, mesh = _build_deps()
    bc = _RecordingBroadcaster()
    # Low speed so the scenario would otherwise take many seconds.
    driver = AmbientDriver(mesh=mesh, world=world, ledger=ledger, broadcaster=bc, speed=2.0)

    await driver.start()
    try:
        # Wait for the first scenario.active, then skip, expect scenario.ended soon.
        await asyncio.wait_for(_wait_for_event(bc, "scenario.active"), timeout=3.0)
        assert driver.active_scenario is not None
        driver.skip()
        await asyncio.wait_for(_wait_for_event(bc, "scenario.ended"), timeout=3.0)
    finally:
        await driver.stop()


async def test_driver_works_without_broadcaster(tiny_rotation: None) -> None:
    """broadcaster=None is legal; driver must still rotate without raising."""
    world, ledger, mesh = _build_deps()
    driver = AmbientDriver(mesh=mesh, world=world, ledger=ledger, broadcaster=None, speed=500.0)
    await driver.start()
    try:
        await asyncio.sleep(0.5)
    finally:
        await driver.stop()


async def test_driver_emits_via_broadcast_fallback(tiny_rotation: None) -> None:
    """Broadcaster with only `_broadcast` (no `emit`/`publish`) still works."""
    world, ledger, mesh = _build_deps()

    class _LegacyBroadcaster:
        def __init__(self) -> None:
            self.events: list[tuple[str, dict[str, Any]]] = []

        def _broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
            self.events.append((event_type, payload))

    bc = _LegacyBroadcaster()
    driver = AmbientDriver(mesh=mesh, world=world, ledger=ledger, broadcaster=bc, speed=500.0)
    await driver.start()
    try:
        await asyncio.wait_for(_spin_until_legacy(bc, at_least=1), timeout=5.0)
    finally:
        await driver.stop()
    kinds = [k for k, _ in bc.events]
    assert "scenario.active" in kinds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _wait_for_event(bc: _RecordingBroadcaster, name: str) -> None:
    while True:
        if any(k == name for k, _ in bc.events):
            return
        await asyncio.sleep(0.05)


async def _spin_until(bc: _RecordingBroadcaster, at_least_pairs: int = 1) -> None:
    while True:
        active = sum(1 for k, _ in bc.events if k == "scenario.active")
        ended = sum(1 for k, _ in bc.events if k == "scenario.ended")
        if active >= at_least_pairs and ended >= at_least_pairs:
            return
        await asyncio.sleep(0.05)


async def _spin_until_legacy(bc: Any, at_least: int = 1) -> None:
    while True:
        if len(bc.events) >= at_least:
            return
        await asyncio.sleep(0.05)
