"""Tests for CostTicker — idle pauses, pricing math, tick payloads."""

from __future__ import annotations

import asyncio

import pytest

from skyherd.agents.cost import (
    _CACHE_HIT_PER_M_USD,
    _CACHE_WRITE_PER_M_USD,
    _INPUT_TOKENS_PER_M_USD,
    _OUTPUT_TOKENS_PER_M_USD,
    _SESSION_HOUR_RATE_USD,
    CostTicker,
    TickPayload,
    run_tick_loop,
)


class TestPricingConstants:
    def test_session_hour_rate(self):
        assert _SESSION_HOUR_RATE_USD == pytest.approx(0.08)

    def test_input_tokens_rate(self):
        assert _INPUT_TOKENS_PER_M_USD == pytest.approx(15.00)

    def test_output_tokens_rate(self):
        assert _OUTPUT_TOKENS_PER_M_USD == pytest.approx(75.00)

    def test_cache_hit_rate(self):
        assert _CACHE_HIT_PER_M_USD == pytest.approx(1.50)

    def test_cache_write_rate(self):
        assert _CACHE_WRITE_PER_M_USD == pytest.approx(18.75)


class TestCostTicker:
    def _ticker(self, session_id: str = "test-session-001") -> CostTicker:
        return CostTicker(session_id=session_id)

    def test_initial_state_idle(self):
        t = self._ticker()
        assert t._current_state == "idle"

    def test_set_state_active(self):
        t = self._ticker()
        t.set_state("active")
        assert t._current_state == "active"

    def test_set_state_idle(self):
        t = self._ticker()
        t.set_state("active")
        t.set_state("idle")
        assert t._current_state == "idle"

    async def test_emit_tick_returns_payload_or_none(self):
        t = self._ticker()
        t.set_state("active")
        result = await t.emit_tick()
        # Active tickers return a TickPayload
        assert result is None or isinstance(result, TickPayload)

    async def test_idle_tick_accrues_zero_cost(self):
        t = self._ticker()
        t.set_state("idle")
        await t.emit_tick()
        assert t.cumulative_cost_usd == pytest.approx(0.0)

    async def test_active_tick_accrues_cost(self):
        t = self._ticker()
        t.set_state("active")
        # Manually advance the internal timer by 3600s to simulate 1 active hour
        t._last_tick_time -= 3600.0
        payload = await t.emit_tick()
        assert payload is not None
        assert payload.cost_delta_usd == pytest.approx(_SESSION_HOUR_RATE_USD, rel=0.05)

    async def test_active_tick_half_hour(self):
        t = self._ticker()
        t.set_state("active")
        t._last_tick_time -= 1800.0
        payload = await t.emit_tick()
        assert payload is not None
        expected = _SESSION_HOUR_RATE_USD * (1800.0 / 3600.0)
        assert payload.cost_delta_usd == pytest.approx(expected, rel=0.05)

    async def test_cumulative_cost_accumulates_across_ticks(self):
        t = self._ticker()
        t.set_state("active")
        for _ in range(3):
            t._last_tick_time -= 3600.0
            await t.emit_tick()
        expected = _SESSION_HOUR_RATE_USD * 3
        assert t.cumulative_cost_usd == pytest.approx(expected, rel=0.05)

    async def test_idle_after_active_stops_accrual(self):
        t = self._ticker()
        t.set_state("active")
        t._last_tick_time -= 3600.0
        await t.emit_tick()
        active_cost = t.cumulative_cost_usd
        t.set_state("idle")
        t._last_tick_time -= 3600.0
        await t.emit_tick()
        # Cumulative should not have grown
        assert t.cumulative_cost_usd == pytest.approx(active_cost, rel=1e-6)

    def test_record_api_call_adds_token_cost(self):
        t = self._ticker()
        t.set_state("active")
        t.record_api_call(
            tokens_in=1_000_000,
            tokens_out=0,
            cache_hit_tokens=0,
            cache_write_tokens=0,
        )
        # 1M input tokens at $15/M
        assert t.cumulative_cost_usd == pytest.approx(15.00, rel=1e-6)

    def test_record_api_call_cache_hit_cheaper(self):
        t = self._ticker()
        t.set_state("active")
        t.record_api_call(
            tokens_in=0,
            tokens_out=0,
            cache_hit_tokens=1_000_000,
            cache_write_tokens=0,
        )
        assert t.cumulative_cost_usd == pytest.approx(_CACHE_HIT_PER_M_USD, rel=1e-6)

    async def test_payload_to_dict(self):
        t = self._ticker()
        t.set_state("active")
        t._last_tick_time -= 1.0
        payload = await t.emit_tick()
        assert payload is not None
        d = payload.to_dict()
        assert "session_id" in d
        assert "state" in d
        assert "cost_delta_usd" in d
        assert "cumulative_cost_usd" in d


class TestRunTickLoop:
    async def test_tick_loop_stops_on_event(self):
        t = CostTicker(session_id="loop-test-session")
        stop_event = asyncio.Event()
        stop_event.set()  # already set — loop should exit immediately
        # Should not raise and should complete quickly
        await run_tick_loop([t], stop_event)

    async def test_tick_loop_with_no_tickers(self):
        stop_event = asyncio.Event()
        stop_event.set()
        await run_tick_loop([], stop_event)
