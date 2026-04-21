"""Tests for WeatherDriver — scheduled storms, conditions, ETA."""

from __future__ import annotations

from skyherd.world.weather import Conditions, Weather, WeatherDriver


class TestWeatherInitial:
    def test_initial_conditions_clear(self) -> None:
        driver = WeatherDriver()
        w = driver.current
        assert w.conditions == Conditions.CLEAR.value or w.conditions == "clear"

    def test_step_returns_weather(self) -> None:
        driver = WeatherDriver()
        w = driver.step(dt=1.0, sim_time_s=1.0)
        assert isinstance(w, Weather)


class TestScheduledStorm:
    def test_storm_fires_at_exact_tick(self) -> None:
        """Storm scheduled at t=100 should be active when step brings sim_time_s to 100."""
        driver = WeatherDriver()
        driver.schedule_storm(at_s=100.0, duration_s=60.0, severity=1.0)

        # Step to t=99 — should still be clear
        w = driver.step(dt=99.0, sim_time_s=99.0)
        assert w.conditions != "storm", f"Storm should not be active at t=99, got {w.conditions}"

        # Step to t=100 — storm should fire
        w = driver.step(dt=1.0, sim_time_s=100.0)
        assert w.conditions == "storm", f"Storm should be active at t=100, got {w.conditions}"

    def test_storm_wind_increases(self) -> None:
        driver = WeatherDriver()
        base_wind = driver.current.wind_kt
        driver.schedule_storm(at_s=50.0, duration_s=100.0, severity=1.0)
        w = driver.step(dt=50.0, sim_time_s=50.0)
        assert w.wind_kt > base_wind, "Wind should increase during storm"

    def test_storm_ends_after_duration(self) -> None:
        driver = WeatherDriver()
        driver.schedule_storm(at_s=10.0, duration_s=30.0, severity=1.0)

        # Fire storm
        driver.step(dt=10.0, sim_time_s=10.0)
        w_during = driver.current
        assert w_during.conditions == "storm"

        # Advance past end
        w_after = driver.step(dt=31.0, sim_time_s=41.0)
        assert w_after.conditions != "storm", "Storm should have ended"

    def test_storm_eta_reported_before_arrival(self) -> None:
        driver = WeatherDriver()
        driver.schedule_storm(at_s=200.0, duration_s=60.0)

        w = driver.step(dt=50.0, sim_time_s=50.0)
        assert w.storm_eta_s is not None
        assert w.storm_eta_s > 0.0, "ETA should be positive before storm arrives"

    def test_storm_eta_none_after_storm(self) -> None:
        driver = WeatherDriver()
        driver.schedule_storm(at_s=10.0, duration_s=5.0)
        driver.step(dt=10.0, sim_time_s=10.0)
        w = driver.step(dt=10.0, sim_time_s=20.0)
        # After storm with no further storms queued, ETA is None
        assert w.storm_eta_s is None

    def test_severity_zero_minimal_wind(self) -> None:
        driver = WeatherDriver()
        driver.schedule_storm(at_s=10.0, duration_s=30.0, severity=0.0)
        w = driver.step(dt=10.0, sim_time_s=10.0)
        # With severity=0 it should still show storm conditions
        assert w.conditions == "storm"
        assert w.wind_kt == 0.0  # severity * STORM_WIND_KT

    def test_severity_clamped_to_one(self) -> None:
        driver = WeatherDriver()
        driver.schedule_storm(at_s=5.0, duration_s=10.0, severity=5.0)  # over-range
        w = driver.step(dt=5.0, sim_time_s=5.0)
        assert w.wind_kt <= 35.0 + 1.0  # should not exceed max storm wind

    def test_multiple_storms_sequential(self) -> None:
        """Two storms scheduled sequentially should both fire in order."""
        driver = WeatherDriver()
        driver.schedule_storm(at_s=10.0, duration_s=5.0)
        driver.schedule_storm(at_s=50.0, duration_s=5.0)

        # First storm fires
        w1 = driver.step(dt=10.0, sim_time_s=10.0)
        assert w1.conditions == "storm"

        # After first storm ends, second storm ETA should be present
        driver.step(dt=20.0, sim_time_s=30.0)
        w_between = driver.current
        assert w_between.conditions != "storm"

        # Second storm fires
        w2 = driver.step(dt=20.0, sim_time_s=50.0)
        assert w2.conditions == "storm"
