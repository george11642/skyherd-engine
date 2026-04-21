"""Simulation clock — tracks elapsed sim time and wall-time acceleration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

# Mountain Time offset (MST = UTC-7; approximate — no DST handling needed for sim)
_MT_OFFSET_H = -7

# Night window in local MT hours (inclusive start, exclusive end — wraps midnight)
_NIGHT_START_H = 19
_NIGHT_START_M = 30
_NIGHT_END_H = 6
_NIGHT_END_M = 0


class Clock:
    """Deterministic simulation clock.

    Parameters
    ----------
    sim_start_utc:
        The UTC datetime that ``sim_time_s == 0`` corresponds to.
    rate:
        Sim-seconds per wall-second (>1 = time-accelerated).
    """

    def __init__(
        self,
        sim_start_utc: datetime | None = None,
        rate: float = 1.0,
    ) -> None:
        if sim_start_utc is None:
            # Default: 2026-04-21 06:00 MT = 13:00 UTC
            sim_start_utc = datetime(2026, 4, 21, 13, 0, 0, tzinfo=UTC)
        self.sim_start_utc: datetime = sim_start_utc
        self.rate: float = rate
        self.sim_time_s: float = 0.0

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def advance(self, dt: float) -> None:
        """Advance the clock by *dt* sim-seconds (must be > 0)."""
        if dt <= 0:
            raise ValueError(f"dt must be positive, got {dt}")
        self.sim_time_s += dt

    # ------------------------------------------------------------------
    # Derived values
    # ------------------------------------------------------------------

    def _current_utc(self) -> datetime:
        return self.sim_start_utc + timedelta(seconds=self.sim_time_s)

    def _current_mt(self) -> datetime:
        """Return current sim time expressed in Mountain Time (naive datetime)."""
        utc = self._current_utc()
        mt_offset = timedelta(hours=_MT_OFFSET_H)
        return utc + mt_offset

    def iso(self) -> str:
        """ISO-8601 string of the current sim time (UTC)."""
        return self._current_utc().isoformat()

    def is_night(self) -> bool:
        """Return True if current sim time is between 19:30 and 06:00 MT (wraps midnight)."""
        mt = self._current_mt()
        h, m = mt.hour, mt.minute
        # Convert to fractional hours for easy comparison
        frac = h + m / 60.0
        night_start = _NIGHT_START_H + _NIGHT_START_M / 60.0  # 19.5
        night_end = _NIGHT_END_H + _NIGHT_END_M / 60.0  # 6.0
        # Night wraps midnight: [19.5, 24) ∪ [0, 6.0)
        return frac >= night_start or frac < night_end
