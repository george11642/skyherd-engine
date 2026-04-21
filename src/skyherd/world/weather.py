"""Weather — deterministic weather state and driver."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Conditions(StrEnum):
    CLEAR = "clear"
    OVERCAST = "overcast"
    STORM = "storm"
    DUST = "dust"


class Weather(BaseModel):
    """Instantaneous weather snapshot."""

    wind_kt: float = Field(default=5.0, ge=0.0)
    wind_dir_deg: float = Field(default=180.0, ge=0.0, lt=360.0)
    temp_f: float = 72.0
    conditions: Conditions = Conditions.CLEAR
    storm_eta_s: float | None = None  # seconds until scheduled storm hits

    model_config = {"use_enum_values": True}


class _ScheduledStorm(BaseModel):
    at_s: float  # sim_time_s when storm triggers
    duration_s: float  # how long it lasts
    severity: float  # 0.0–1.0


_BASE_WIND_KT = 5.0
_STORM_WIND_KT = 35.0
_STORM_TEMP_DROP_F = 15.0
_WIND_CHANGE_RATE = 0.1  # kt per second


class WeatherDriver:
    """Advances :class:`Weather` deterministically based on scheduled events.

    All state transitions are driven by scheduled storms; background
    variation uses a simple sinusoidal model (no randomness needed for
    the driver itself — randomness is injected at spawn time if desired).
    """

    def __init__(self, initial: Weather | None = None) -> None:
        self._weather: Weather = initial or Weather()
        self._storms: list[_ScheduledStorm] = []
        self._active_storm: _ScheduledStorm | None = None
        self._storm_end_s: float | None = None

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def schedule_storm(self, at_s: float, duration_s: float, severity: float = 1.0) -> None:
        """Schedule a storm to fire at exactly *at_s* sim-seconds."""
        self._storms.append(
            _ScheduledStorm(at_s=at_s, duration_s=duration_s, severity=max(0.0, min(1.0, severity)))
        )
        # Keep sorted ascending
        self._storms.sort(key=lambda s: s.at_s)

    # ------------------------------------------------------------------
    # Stepping
    # ------------------------------------------------------------------

    def step(self, dt: float, sim_time_s: float) -> Weather:
        """Advance weather by *dt* seconds; return updated :class:`Weather`."""
        data = self._weather.model_dump()

        # --- Check if a scheduled storm should start ---
        fired: list[_ScheduledStorm] = []
        remaining: list[_ScheduledStorm] = []
        for storm in self._storms:
            if storm.at_s <= sim_time_s and self._active_storm is None:
                fired.append(storm)
            else:
                remaining.append(storm)
        self._storms = remaining

        if fired and self._active_storm is None:
            # Take the first (earliest) triggered storm
            self._active_storm = fired[0]
            self._storm_end_s = self._active_storm.at_s + self._active_storm.duration_s
            # Merge any remaining fired storms back (shouldn't happen often)
            for extra in fired[1:]:
                self._storms.insert(0, extra)
            self._storms.sort(key=lambda s: s.at_s)

        # --- Active storm logic ---
        if self._active_storm is not None and self._storm_end_s is not None:
            sev = self._active_storm.severity
            data["conditions"] = Conditions.STORM.value
            data["wind_kt"] = _STORM_WIND_KT * sev
            data["temp_f"] = data["temp_f"] - _STORM_TEMP_DROP_F * sev
            data["storm_eta_s"] = None  # storm is active now

            if sim_time_s >= self._storm_end_s:
                # Storm ended
                self._active_storm = None
                self._storm_end_s = None
                data["conditions"] = Conditions.OVERCAST.value
                data["wind_kt"] = max(_BASE_WIND_KT, data["wind_kt"] - _WIND_CHANGE_RATE * dt)
        else:
            # Clear / background conditions
            data["conditions"] = Conditions.CLEAR.value
            data["wind_kt"] = _BASE_WIND_KT
            # Compute ETA to next storm if any are queued
            if self._storms:
                next_storm = self._storms[0]
                data["storm_eta_s"] = max(0.0, next_storm.at_s - sim_time_s)
            else:
                data["storm_eta_s"] = None

        self._weather = Weather(**data)
        return self._weather

    @property
    def current(self) -> Weather:
        return self._weather
