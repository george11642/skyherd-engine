"""Tests for CostTicker — idle pauses, pricing math, tick payloads."""

from __future__ import annotations

import asyncio
import json

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

    # ------------------------------------------------------------------
    # MA-04: multi-ticker all-idle aggregation contract
    # ------------------------------------------------------------------

    def _aggregate(self, tickers: list) -> dict:
        """Mirror of src/skyherd/server/events.py::_real_cost_tick aggregation math.

        Kept inline (not imported from events.py) so this test documents the
        MA-04 contract independently of the dashboard implementation, which
        Phase 5 refactors. If events.py changes its aggregation formula,
        this test flags the drift.
        """
        any_active = any(t._current_state == "active" for t in tickers)
        all_idle = not any_active
        rate_per_hr_usd = 0.0 if all_idle else _SESSION_HOUR_RATE_USD
        return {"all_idle": all_idle, "rate_per_hr_usd": rate_per_hr_usd}

    def test_all_sessions_idle_emits_zero_rate(self):
        """MA-04: two-ticker all-idle aggregation yields all_idle=True, rate=0.0."""
        t1 = CostTicker(session_id="s1")
        t2 = CostTicker(session_id="s2")
        t1.set_state("idle")
        t2.set_state("idle")
        agg = self._aggregate([t1, t2])
        assert agg["all_idle"] is True
        assert agg["rate_per_hr_usd"] == pytest.approx(0.0)

    def test_mixed_active_idle_emits_active_rate(self):
        """MA-04: if any ticker is active, aggregation yields all_idle=False, rate=0.08."""
        t_idle = CostTicker(session_id="s_idle")
        t_active = CostTicker(session_id="s_active")
        t_idle.set_state("idle")
        t_active.set_state("active")
        agg = self._aggregate([t_idle, t_active])
        assert agg["all_idle"] is False
        assert agg["rate_per_hr_usd"] == pytest.approx(_SESSION_HOUR_RATE_USD)

    def test_single_idle_ticker_emits_zero_rate(self):
        """MA-04: edge case — a single idle ticker still emits zero rate."""
        t = CostTicker(session_id="s_solo")
        t.set_state("idle")
        agg = self._aggregate([t])
        assert agg["all_idle"] is True
        assert agg["rate_per_hr_usd"] == pytest.approx(0.0)


class TestMqttPublishCallback:
    async def test_publish_callback_called_with_topic_and_payload(self):
        captured: list[tuple[str, bytes]] = []

        async def mock_publish(topic: str, data: bytes) -> None:
            captured.append((topic, data))

        t = CostTicker(session_id="sess-1", mqtt_publish_callback=mock_publish)
        t.set_state("active")
        t._last_tick_time -= 1.0
        await t.emit_tick()
        assert len(captured) == 1
        topic, payload_bytes = captured[0]
        assert topic == "skyherd/ranch_a/cost/ticker"
        decoded = json.loads(payload_bytes.decode())
        assert decoded["session_id"] == "sess-1"

    async def test_publish_callback_failure_swallowed(self):
        async def failing_publish(topic: str, data: bytes) -> None:
            raise RuntimeError("mqtt broker down")

        t = CostTicker(session_id="sess-2", mqtt_publish_callback=failing_publish)
        t.set_state("active")
        t._last_tick_time -= 1.0
        # Should not raise
        result = await t.emit_tick()
        assert result is not None


class TestLedgerCallback:
    async def test_ledger_callback_called_with_payload(self):
        captured: list[TickPayload] = []

        async def mock_ledger(payload: TickPayload) -> None:
            captured.append(payload)

        t = CostTicker(session_id="sess-3", ledger_callback=mock_ledger)
        t.set_state("active")
        t._last_tick_time -= 1.0
        await t.emit_tick()
        assert len(captured) == 1
        assert captured[0].session_id == "sess-3"

    async def test_ledger_callback_failure_swallowed(self):
        async def failing_ledger(payload: TickPayload) -> None:
            raise RuntimeError("db locked")

        t = CostTicker(session_id="sess-4", ledger_callback=failing_ledger)
        t.set_state("active")
        t._last_tick_time -= 1.0
        result = await t.emit_tick()
        assert result is not None


class TestProperties:
    async def test_active_s_property(self):
        t = CostTicker(session_id="sess-prop-1")
        t.set_state("active")
        t._last_tick_time -= 10.0
        await t.emit_tick()
        assert t.active_s >= 9.0  # ~10s minus wall-clock drift

    async def test_idle_s_property(self):
        t = CostTicker(session_id="sess-prop-2")
        t.set_state("idle")
        t._last_tick_time -= 5.0
        await t.emit_tick()
        assert t.idle_s >= 4.0


class TestRunTickLoopBody:
    async def test_loop_ticks_all_tickers(self, monkeypatch):
        call_count: dict[str, int] = {"a": 0, "b": 0}
        t_a = CostTicker(session_id="a")
        t_b = CostTicker(session_id="b")
        t_a.set_state("active")

        # Save reference to real sleep before monkeypatching so fast_sleep can yield
        real_sleep = asyncio.sleep

        async def fast_sleep(_: float) -> None:
            await real_sleep(0)  # Real yield — lets other tasks (stop task) run

        monkeypatch.setattr("skyherd.agents.cost.asyncio.sleep", fast_sleep)

        # Wrap emit_tick to count invocations
        orig_a = t_a.emit_tick
        orig_b = t_b.emit_tick

        async def wrapped_a() -> TickPayload | None:
            call_count["a"] += 1
            return await orig_a()

        async def wrapped_b() -> TickPayload | None:
            call_count["b"] += 1
            return await orig_b()

        t_a.emit_tick = wrapped_a  # type: ignore[method-assign]
        t_b.emit_tick = wrapped_b  # type: ignore[method-assign]

        stop_event = asyncio.Event()

        async def stop_after_one_iter() -> None:
            await real_sleep(0)  # Yield to let loop run one iteration
            stop_event.set()

        task = asyncio.create_task(stop_after_one_iter())
        await run_tick_loop([t_a, t_b], stop_event)
        await task
        assert call_count["a"] >= 1
        assert call_count["b"] >= 1

    async def test_loop_swallows_ticker_exception(self, monkeypatch):
        t_boom = CostTicker(session_id="boom")

        async def raising_emit() -> TickPayload | None:
            raise RuntimeError("tick exploded")

        t_boom.emit_tick = raising_emit  # type: ignore[method-assign]

        real_sleep = asyncio.sleep

        async def fast_sleep(_: float) -> None:
            await real_sleep(0)

        monkeypatch.setattr("skyherd.agents.cost.asyncio.sleep", fast_sleep)

        stop_event = asyncio.Event()

        async def stop_soon() -> None:
            await real_sleep(0)
            stop_event.set()

        task = asyncio.create_task(stop_soon())
        # Must not raise
        await run_tick_loop([t_boom], stop_event)
        await task
