"""Tests for the water_drop scenario."""

from __future__ import annotations


class TestWaterDropScenario:
    def test_name_and_description(self) -> None:
        from skyherd.scenarios.water_drop import WaterDropScenario

        s = WaterDropScenario()
        assert s.name == "water_drop"
        assert "water" in s.description.lower() or "tank" in s.description.lower()

    def test_setup_sets_low_tank(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.water_drop import WaterDropScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = WaterDropScenario()
        s.setup(world)
        tank = next(t for t in world.terrain.config.water_tanks if t.id == "wt_sw")
        assert tank.level_pct == 18.0
        assert tank.level_pct < 20.0

    def test_setup_sets_hot_weather(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.water_drop import WaterDropScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = WaterDropScenario()
        s.setup(world)
        assert world.weather_driver.current.temp_f > 90.0

    def test_water_low_fires_on_first_step(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.water_drop import WaterDropScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = WaterDropScenario()
        s.setup(world)
        events = world.step(5.0)
        water_events = [e for e in events if e.get("type") == "water.low"]
        assert len(water_events) > 0

    def test_flyover_injected_after_water_low(self) -> None:
        from pathlib import Path

        from skyherd.scenarios.water_drop import _DRONE_FLYOVER_AT_S, WaterDropScenario
        from skyherd.world.world import make_world

        config = Path(__file__).parent.parent.parent / "worlds" / "ranch_a.yaml"
        world = make_world(seed=42, config_path=config)
        s = WaterDropScenario()
        s.setup(world)
        # Step world to fire water.low
        world.step(5.0)
        # Now inject events — flyover should appear
        events = s.inject_events(world, _DRONE_FLYOVER_AT_S + 1.0)
        types = [e["type"] for e in events]
        assert "drone.flyover_complete" in types

    def test_full_run_passes(self) -> None:
        from skyherd.scenarios import run

        result = run("water_drop", seed=42)
        assert result.outcome_passed, f"water_drop scenario failed: {result.outcome_error}"

    def test_full_run_has_water_low(self) -> None:
        from skyherd.scenarios import run

        result = run("water_drop", seed=42)
        wl = next(
            (
                e
                for e in result.event_stream
                if e.get("type") == "water.low" and e.get("tank_id") == "wt_sw"
            ),
            None,
        )
        assert wl is not None

    def test_full_run_has_drone_flyover(self) -> None:
        from skyherd.scenarios import run

        result = run("water_drop", seed=42)
        flyover = next(
            (e for e in result.event_stream if e.get("type") == "drone.flyover_complete"),
            None,
        )
        assert flyover is not None
