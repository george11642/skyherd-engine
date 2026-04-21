"""Tests for Herd — drinking, BCS decay, movement."""

from __future__ import annotations

import random

from skyherd.world.cattle import (
    _DRINK_PROXIMITY_M,
    Cow,
    Herd,
)
from skyherd.world.terrain import (
    BarnConfig,
    FenceLineConfig,
    PaddockConfig,
    Terrain,
    TerrainConfig,
    TroughConfig,
    WaterTankConfig,
)
from skyherd.world.weather import Weather


def _make_terrain(trough_pos: tuple[float, float] = (100.0, 100.0)) -> Terrain:
    """Minimal terrain with a single paddock and one trough."""
    config = TerrainConfig(
        name="test",
        bounds_m=(2000.0, 2000.0),
        paddocks=[
            PaddockConfig(
                id="p_test",
                polygon=[(0.0, 0.0), (2000.0, 0.0), (2000.0, 2000.0), (0.0, 2000.0)],
            )
        ],
        water_tanks=[WaterTankConfig(id="wt1", pos=(100.0, 100.0), capacity_l=5000.0)],
        troughs=[TroughConfig(id="tr1", pos=trough_pos, paddock="p_test")],
        fence_lines=[
            FenceLineConfig(id="fence_s", segment=[(0.0, 0.0), (2000.0, 0.0)], tag="perimeter")
        ],
        barn=BarnConfig(pos=(1900.0, 1900.0)),
    )
    return Terrain(config)


def _make_weather() -> Weather:
    return Weather()


def _make_cow(
    tag: str = "T001",
    pos: tuple[float, float] = (500.0, 500.0),
    thirst: float = 0.2,
    bcs: float = 5.0,
    last_feed_ts: float = 0.0,
    lameness_score: int = 0,
) -> Cow:
    return Cow(
        id=f"cow_{tag}",
        tag=tag,
        pos=pos,
        thirst=thirst,
        bcs=bcs,
        last_feed_ts=last_feed_ts,
        lameness_score=lameness_score,
    )


class TestDrinking:
    def test_cow_drinks_when_thirsty_and_near_trough(self) -> None:
        """Cow placed right next to trough with high thirst should drink."""
        trough_pos = (100.0, 100.0)
        terrain = _make_terrain(trough_pos)
        cow_pos = (100.0 + _DRINK_PROXIMITY_M - 1.0, 100.0)  # just inside range
        cow = _make_cow("T001", pos=cow_pos, thirst=0.9)
        herd = Herd([cow], rng=random.Random(42))

        events = herd.step(dt=1.0, terrain=terrain, weather=_make_weather(), sim_time_s=10.0)

        drink_events = [e for e in events if e["type"] == "cow.drank"]
        assert len(drink_events) >= 1, "Expected a cow.drank event"
        assert drink_events[0]["tag"] == "T001"

        # Thirst should have decreased
        updated_cow = herd.cows[0]
        assert updated_cow.thirst < 0.9

    def test_cow_does_not_drink_when_far_from_trough(self) -> None:
        """Cow far from trough should not get a drink event."""
        terrain = _make_terrain(trough_pos=(100.0, 100.0))
        cow = _make_cow("T002", pos=(1000.0, 1000.0), thirst=0.9)
        herd = Herd([cow], rng=random.Random(42))

        events = herd.step(dt=1.0, terrain=terrain, weather=_make_weather(), sim_time_s=10.0)
        drink_events = [e for e in events if e["type"] == "cow.drank"]
        assert len(drink_events) == 0

    def test_cow_thirst_increases_over_time(self) -> None:
        """Thirst should increase each step when no drinking occurs."""
        terrain = _make_terrain(trough_pos=(1900.0, 1900.0))  # far away
        cow = _make_cow("T003", pos=(100.0, 100.0), thirst=0.1)
        herd = Herd([cow], rng=random.Random(42))

        initial_thirst = herd.cows[0].thirst
        # Step for one hour (3600s)
        herd.step(dt=3600.0, terrain=terrain, weather=_make_weather(), sim_time_s=3600.0)
        assert herd.cows[0].thirst > initial_thirst

    def test_thirst_clamps_at_one(self) -> None:
        """Thirst cannot exceed 1.0."""
        terrain = _make_terrain(trough_pos=(1900.0, 1900.0))
        cow = _make_cow("T004", pos=(100.0, 100.0), thirst=0.99)
        herd = Herd([cow], rng=random.Random(42))

        # Step for a very long time
        herd.step(dt=100000.0, terrain=terrain, weather=_make_weather(), sim_time_s=100000.0)
        assert herd.cows[0].thirst <= 1.0


class TestBcsDecay:
    def test_bcs_decays_without_feed(self) -> None:
        """BCS should drop when cow hasn't been fed for >24h."""
        terrain = _make_terrain(trough_pos=(1900.0, 1900.0))
        # last_feed_ts=0, sim starts at 0; after 25h no feed
        cow = _make_cow("T005", pos=(500.0, 500.0), bcs=5.0, last_feed_ts=0.0)
        herd = Herd([cow], rng=random.Random(42))

        # Step 25 hours (90000s)
        initial_bcs = herd.cows[0].bcs
        herd.step(dt=90000.0, terrain=terrain, weather=_make_weather(), sim_time_s=90000.0)
        assert herd.cows[0].bcs < initial_bcs

    def test_bcs_stable_when_recently_fed(self) -> None:
        """BCS should not decay if feed is recent."""
        terrain = _make_terrain()
        sim_time_s = 3600.0
        # last_feed_ts is same as sim_time_s → just fed
        cow = _make_cow("T006", pos=(500.0, 500.0), bcs=5.0, last_feed_ts=sim_time_s)
        herd = Herd([cow], rng=random.Random(42))

        initial_bcs = herd.cows[0].bcs
        herd.step(
            dt=3600.0, terrain=terrain, weather=_make_weather(), sim_time_s=sim_time_s + 3600.0
        )
        assert herd.cows[0].bcs == initial_bcs

    def test_bcs_floor_is_one(self) -> None:
        """BCS cannot drop below 1.0."""
        terrain = _make_terrain(trough_pos=(1900.0, 1900.0))
        cow = _make_cow("T007", pos=(500.0, 500.0), bcs=1.0, last_feed_ts=0.0)
        herd = Herd([cow], rng=random.Random(42))

        herd.step(
            dt=86400.0 * 30, terrain=terrain, weather=_make_weather(), sim_time_s=86400.0 * 31
        )
        assert herd.cows[0].bcs >= 1.0


class TestLameness:
    def test_lame_cow_emits_event(self) -> None:
        """Cow with lameness_score >= 3 should emit cow.lame event each step."""
        terrain = _make_terrain()
        cow = _make_cow("T008", pos=(500.0, 500.0), lameness_score=4)
        herd = Herd([cow], rng=random.Random(42))

        events = herd.step(dt=1.0, terrain=terrain, weather=_make_weather(), sim_time_s=1.0)
        lame_events = [e for e in events if e["type"] == "cow.lame"]
        assert len(lame_events) == 1
        assert lame_events[0]["lameness_score"] == 4

    def test_healthy_cow_no_lame_event(self) -> None:
        terrain = _make_terrain()
        cow = _make_cow("T009", lameness_score=0)
        herd = Herd([cow], rng=random.Random(42))

        events = herd.step(dt=1.0, terrain=terrain, weather=_make_weather(), sim_time_s=1.0)
        lame_events = [e for e in events if e["type"] == "cow.lame"]
        assert len(lame_events) == 0


class TestMovement:
    def test_thirsty_cow_moves_toward_trough(self) -> None:
        """Very thirsty cow should consistently move closer to the trough."""
        trough_pos = (500.0, 500.0)
        terrain = _make_terrain(trough_pos=trough_pos)
        start_pos = (100.0, 100.0)
        cow = _make_cow("T010", pos=start_pos, thirst=0.95)
        herd = Herd([cow], rng=random.Random(42))

        import math

        initial_dist = math.sqrt(
            (start_pos[0] - trough_pos[0]) ** 2 + (start_pos[1] - trough_pos[1]) ** 2
        )

        # Step many times; on average thirsty cow drifts toward trough
        for i in range(20):
            herd.step(dt=10.0, terrain=terrain, weather=_make_weather(), sim_time_s=float(i * 10))

        final_pos = herd.cows[0].pos
        final_dist = math.sqrt(
            (final_pos[0] - trough_pos[0]) ** 2 + (final_pos[1] - trough_pos[1]) ** 2
        )
        assert final_dist < initial_dist, "Thirsty cow should move closer to trough"

    def test_pos_stays_within_bounds(self) -> None:
        """Cow position should never exceed ranch bounds."""
        terrain = _make_terrain()
        cow = _make_cow("T011", pos=(0.0, 0.0))
        herd = Herd([cow], rng=random.Random(123))

        for i in range(100):
            herd.step(dt=10.0, terrain=terrain, weather=_make_weather(), sim_time_s=float(i * 10))
            p = herd.cows[0].pos
            assert 0.0 <= p[0] <= 2000.0, f"x out of bounds: {p[0]}"
            assert 0.0 <= p[1] <= 2000.0, f"y out of bounds: {p[1]}"
