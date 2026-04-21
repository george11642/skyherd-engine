"""Tests for Clock — advance, is_night boundaries, iso output."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from skyherd.world.clock import Clock


def _make_clock(hour_utc: int, minute_utc: int = 0) -> Clock:
    """Helper: create a Clock whose sim_start_utc is set to a specific UTC hour."""
    start = datetime(2026, 4, 21, hour_utc, minute_utc, 0, tzinfo=UTC)
    return Clock(sim_start_utc=start, rate=1.0)


class TestClockAdvance:
    def test_initial_sim_time_is_zero(self) -> None:
        clock = Clock()
        assert clock.sim_time_s == 0.0

    def test_advance_increments_sim_time(self) -> None:
        clock = Clock()
        clock.advance(60.0)
        assert clock.sim_time_s == 60.0

    def test_advance_accumulates(self) -> None:
        clock = Clock()
        clock.advance(100.0)
        clock.advance(200.0)
        assert clock.sim_time_s == 300.0

    def test_advance_rejects_zero(self) -> None:
        clock = Clock()
        with pytest.raises(ValueError):
            clock.advance(0.0)

    def test_advance_rejects_negative(self) -> None:
        clock = Clock()
        with pytest.raises(ValueError):
            clock.advance(-1.0)

    def test_iso_returns_string(self) -> None:
        clock = Clock()
        iso = clock.iso()
        assert isinstance(iso, str)
        assert "T" in iso  # basic ISO format check


class TestClockIsNight:
    """Night window: 19:30–06:00 MT (UTC-7), i.e., 02:30–13:00 UTC."""

    # MT 19:30 = UTC 02:30 → night start
    def test_is_night_at_2230_mt(self) -> None:
        # MT 22:30 = UTC 05:30
        clock = _make_clock(hour_utc=5, minute_utc=30)
        assert clock.is_night() is True

    # MT 00:00 (midnight) should be night
    def test_is_night_at_midnight_mt(self) -> None:
        # MT 00:00 = UTC 07:00
        clock = _make_clock(hour_utc=7, minute_utc=0)
        assert clock.is_night() is True

    # MT 03:00 is night
    def test_is_night_at_0300_mt(self) -> None:
        # MT 03:00 = UTC 10:00
        clock = _make_clock(hour_utc=10, minute_utc=0)
        assert clock.is_night() is True

    # MT 05:59 is still night
    def test_is_night_at_0559_mt(self) -> None:
        # MT 05:59 = UTC 12:59
        clock = _make_clock(hour_utc=12, minute_utc=59)
        assert clock.is_night() is True

    # MT 06:00 exactly is day
    def test_is_day_at_0600_mt(self) -> None:
        # MT 06:00 = UTC 13:00
        clock = _make_clock(hour_utc=13, minute_utc=0)
        assert clock.is_night() is False

    # MT 12:00 noon is day
    def test_is_day_at_noon_mt(self) -> None:
        # MT 12:00 = UTC 19:00
        clock = _make_clock(hour_utc=19, minute_utc=0)
        assert clock.is_night() is False

    # MT 19:29 is still day (night starts at 19:30)
    def test_is_day_at_1929_mt(self) -> None:
        # MT 19:29 = UTC 02:29
        clock = _make_clock(hour_utc=2, minute_utc=29)
        assert clock.is_night() is False

    # MT 19:30 exactly is night
    def test_is_night_at_1930_mt(self) -> None:
        # MT 19:30 = UTC 02:30
        clock = _make_clock(hour_utc=2, minute_utc=30)
        assert clock.is_night() is True

    def test_advance_moves_through_night_boundary(self) -> None:
        """Advancing from MT 19:29 by 2 minutes puts us into night."""
        # Start at MT 19:29 = UTC 02:29
        clock = _make_clock(hour_utc=2, minute_utc=29)
        assert clock.is_night() is False
        clock.advance(60.0)  # +1 minute sim time
        assert clock.is_night() is True  # now MT 19:30

    def test_rate_field_stored(self) -> None:
        clock = Clock(rate=60.0)
        assert clock.rate == 60.0
