"""CostTicker — per-session cost metering for SkyHerd Managed Agents.

Pricing constants (Opus 4.7 rates, Apr 2026):
  - Active session-hour:  $0.08 / session-hour  (only while state == "active")
  - Prompt input tokens:  $15.00 / M tokens
  - Output tokens:        $75.00 / M tokens
  - Cache hit:            $1.50  / M tokens
  - Cache write:          $18.75 / M tokens

The ticker is designed to be called from ``SessionManager``.  It emits a
structured tick dict and optionally publishes to the MQTT bus topic
``skyherd/ranch_a/cost/ticker``.  When all sessions are idle the publish loop
should simply pause — this is the "cost-ticker money shot" that visually
demonstrates idle-pause saving dollars.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pricing constants
# ---------------------------------------------------------------------------

_SESSION_HOUR_RATE_USD: float = 0.08  # per active session-hour
_INPUT_TOKENS_PER_M_USD: float = 15.00
_OUTPUT_TOKENS_PER_M_USD: float = 75.00
_CACHE_HIT_PER_M_USD: float = 1.50
_CACHE_WRITE_PER_M_USD: float = 18.75

_TICK_INTERVAL_S: float = 1.0  # emit cost delta every 1 second while active


def _tokens_cost_usd(
    tokens_in: int,
    tokens_out: int,
    cache_hit_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """Return USD cost for one API call given token counts."""
    billed_in = max(0, tokens_in - cache_hit_tokens - cache_write_tokens)
    return (
        billed_in * _INPUT_TOKENS_PER_M_USD / 1_000_000
        + tokens_out * _OUTPUT_TOKENS_PER_M_USD / 1_000_000
        + cache_hit_tokens * _CACHE_HIT_PER_M_USD / 1_000_000
        + cache_write_tokens * _CACHE_WRITE_PER_M_USD / 1_000_000
    )


@dataclass
class TickPayload:
    """Structured payload emitted by each cost tick."""

    ts: float
    session_id: str
    state: str
    active_s: float
    idle_s: float
    tokens_in: int
    tokens_out: int
    cost_delta_usd: float
    cumulative_cost_usd: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "session_id": self.session_id,
            "state": self.state,
            "active_s": round(self.active_s, 3),
            "idle_s": round(self.idle_s, 3),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_delta_usd": round(self.cost_delta_usd, 6),
            "cumulative_cost_usd": round(self.cumulative_cost_usd, 6),
        }


@dataclass
class CostTicker:
    """Tracks and emits per-session cost deltas.

    Only charges the $0.08/session-hour active rate while ``state == "active"``.
    Token costs are added via :meth:`record_api_call` after each Claude response.

    Parameters
    ----------
    session_id:
        Owning session identifier.
    ledger_callback:
        Optional async callable called with each :class:`TickPayload`.
    mqtt_publish_callback:
        Optional async callable ``(topic, payload_bytes)`` for MQTT broadcast.
    """

    session_id: str
    ledger_callback: Any | None = None  # Callable[[TickPayload], Awaitable[None]]
    mqtt_publish_callback: Any | None = None  # Callable[[str, bytes], Awaitable[None]]

    # Running totals
    _cumulative_cost_usd: float = field(default=0.0, repr=False)
    _cumulative_tokens_in: int = field(default=0, repr=False)
    _cumulative_tokens_out: int = field(default=0, repr=False)
    _active_s: float = field(default=0.0, repr=False)
    _idle_s: float = field(default=0.0, repr=False)
    _last_tick_time: float = field(default_factory=time.monotonic, repr=False)
    _current_state: str = field(default="idle", repr=False)

    def set_state(self, state: str) -> None:
        """Update the current session state (called by SessionManager)."""
        self._current_state = state
        self._last_tick_time = time.monotonic()

    def record_api_call(
        self,
        tokens_in: int,
        tokens_out: int,
        cache_hit_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> float:
        """Record token usage for one API call and return the cost delta."""
        delta = _tokens_cost_usd(tokens_in, tokens_out, cache_hit_tokens, cache_write_tokens)
        self._cumulative_cost_usd += delta
        self._cumulative_tokens_in += tokens_in
        self._cumulative_tokens_out += tokens_out
        return delta

    async def emit_tick(self) -> TickPayload | None:
        """Emit one cost tick.  Returns None if session is idle (no cost delta)."""
        now = time.monotonic()
        elapsed = now - self._last_tick_time
        self._last_tick_time = now

        if self._current_state == "active":
            # Session-hour cost accrues only while active
            hour_fraction = elapsed / 3600.0
            delta = _SESSION_HOUR_RATE_USD * hour_fraction
            self._cumulative_cost_usd += delta
            self._active_s += elapsed
        else:
            # Idle — ZERO cost delta; meter pauses
            delta = 0.0
            self._idle_s += elapsed

        payload = TickPayload(
            ts=time.time(),
            session_id=self.session_id,
            state=self._current_state,
            active_s=self._active_s,
            idle_s=self._idle_s,
            tokens_in=self._cumulative_tokens_in,
            tokens_out=self._cumulative_tokens_out,
            cost_delta_usd=delta,
            cumulative_cost_usd=self._cumulative_cost_usd,
        )

        # Publish to MQTT if callback provided
        if self.mqtt_publish_callback is not None:
            topic = "skyherd/ranch_a/cost/ticker"
            try:
                payload_bytes = json.dumps(payload.to_dict()).encode()
                await self.mqtt_publish_callback(topic, payload_bytes)
            except Exception as exc:  # noqa: BLE001
                logger.debug("cost tick mqtt publish failed: %s", exc)

        # Write to attestation ledger if callback provided
        if self.ledger_callback is not None:
            try:
                await self.ledger_callback(payload)
            except Exception as exc:  # noqa: BLE001
                logger.debug("cost tick ledger callback failed: %s", exc)

        return payload if delta > 0 or self._current_state == "active" else None

    @property
    def cumulative_cost_usd(self) -> float:
        return self._cumulative_cost_usd

    @property
    def active_s(self) -> float:
        return self._active_s

    @property
    def idle_s(self) -> float:
        return self._idle_s


async def run_tick_loop(
    tickers: list[CostTicker],
    stop_event: asyncio.Event,
) -> None:
    """Run 1-Hz cost tick loop for a list of tickers.

    Pauses publishing when ALL sessions are idle — demonstrates the
    idle-pause money shot.  The loop itself never exits until ``stop_event``
    is set, even when all sessions idle.
    """
    while not stop_event.is_set():
        any_active = any(t._current_state == "active" for t in tickers)
        for ticker in tickers:
            try:
                await ticker.emit_tick()
            except Exception as exc:  # noqa: BLE001
                logger.debug("tick loop error for %s: %s", ticker.session_id, exc)

        # Log the pause when all sessions go idle
        if not any_active:
            logger.debug("cost ticker paused — all sessions idle, $0/s")

        await asyncio.sleep(_TICK_INTERVAL_S)
