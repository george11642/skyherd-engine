"""CollarSimEmitter — deterministic, seed-driven fake collar events.

Distinct from :class:`skyherd.sensors.collar.CollarSensor`, which reads a cow
position from the live World simulator. ``CollarSimEmitter`` is a **standalone
emitter** suited to:

* Dashboard development without spinning up the full world loop.
* Augmenting partial hardware deployments (real collars on some cows, sim
  emitters filling in the rest).
* Dev-only mode for UI prototyping.

All randomness is seeded through :class:`random.Random(seed)` — there is **no
wall clock** in the emit path. The optional ``ts_provider`` callable controls
the timestamp; it defaults to a monotonic integer tick counter so that replay
runs produce byte-identical output.

The emitted dict matches the sim-schema produced by
:meth:`skyherd.sensors.collar.CollarSensor.tick`.
"""

from __future__ import annotations

import logging
import math
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_TOPIC_TEMPLATE = "skyherd/{ranch}/collar/{cow_tag}"

# Activity state transition matrix (seed-driven).
# Row indices: 0=resting, 1=grazing, 2=walking.
# Each row is P(next state) given current state; must sum to 1.0.
_TRANSITION_MATRIX = (
    (0.60, 0.35, 0.05),  # resting → {rest, graze, walk}
    (0.20, 0.60, 0.20),  # grazing → {rest, graze, walk}
    (0.10, 0.50, 0.40),  # walking → {rest, graze, walk}
)
_ACTIVITY_LABELS = ("resting", "grazing", "walking")

# Heart-rate Ornstein-Uhlenbeck parameters (cow resting range 40–80 bpm).
_HR_MEAN = 55.0
_HR_THETA = 0.15  # pull-back strength
_HR_SIGMA = 3.0  # gaussian noise amplitude
_HR_MIN = 30.0
_HR_MAX = 100.0

# Position random-walk step (approx. 2.2 m per tick at the equator).
_POS_STEP_STD = 2e-5  # degrees of lat/lon


@dataclass
class CollarSimEmitter:
    """Seed-driven deterministic collar emitter.

    Parameters
    ----------
    ranch_id:
        Ranch identifier, used to build the MQTT topic.
    cow_tag:
        Cow tag / entity ID.
    seed:
        Seed for the internal :class:`random.Random`. Same seed → same output.
    start_pos:
        Initial ``(lat, lon)`` in decimal degrees. Defaults to NM ranch_a.
    drain_rate_per_tick:
        Battery drain in percentage points per ``tick()`` call.
    initial_battery_pct:
        Starting battery (0–100).
    ts_provider:
        Callable returning a float timestamp. Defaults to a tick counter so
        replays are deterministic. Pass ``time.time`` for live-clock mode.
    """

    ranch_id: str
    cow_tag: str
    seed: int
    start_pos: tuple[float, float] = (34.05, -106.53)
    drain_rate_per_tick: float = 0.05
    initial_battery_pct: float = 100.0
    ts_provider: Callable[[], float] | None = None

    # Internal state (not part of the public constructor)
    _rng: random.Random = field(init=False, repr=False)
    _tick_count: int = field(init=False, default=0, repr=False)
    _pos: tuple[float, float] = field(init=False, repr=False)
    _battery_pct: float = field(init=False, repr=False)
    _activity_idx: int = field(init=False, default=0, repr=False)
    _heart_rate: float = field(init=False, default=_HR_MEAN, repr=False)
    _heading_deg: float = field(init=False, default=0.0, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._pos = self.start_pos
        self._battery_pct = float(max(0.0, min(100.0, self.initial_battery_pct)))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def topic(self) -> str:
        return _TOPIC_TEMPLATE.format(ranch=self.ranch_id, cow_tag=self.cow_tag)

    def tick(self) -> dict[str, object]:
        """Advance one step and return a sim-schema ``collar.reading`` dict."""
        self._tick_count += 1

        # Advance activity state
        row = _TRANSITION_MATRIX[self._activity_idx]
        self._activity_idx = _weighted_choice(self._rng, row)
        activity = _ACTIVITY_LABELS[self._activity_idx]

        # Position random walk — larger step when walking, tiny when resting
        step_scale = (0.2, 0.8, 2.5)[self._activity_idx]
        dlat = self._rng.gauss(0.0, _POS_STEP_STD) * step_scale
        dlon = self._rng.gauss(0.0, _POS_STEP_STD) * step_scale
        new_lat = self._pos[0] + dlat
        new_lon = self._pos[1] + dlon
        if dlat != 0.0 or dlon != 0.0:
            self._heading_deg = (math.degrees(math.atan2(dlon, dlat)) + 360.0) % 360.0
        self._pos = (new_lat, new_lon)

        # Heart rate — Ornstein-Uhlenbeck toward _HR_MEAN + activity lift
        activity_offset = (0.0, 4.0, 12.0)[self._activity_idx]
        target = _HR_MEAN + activity_offset
        drift = _HR_THETA * (target - self._heart_rate)
        noise = self._rng.gauss(0.0, _HR_SIGMA)
        self._heart_rate = max(_HR_MIN, min(_HR_MAX, self._heart_rate + drift + noise))

        # Battery drain (monotonic downward, clamped)
        self._battery_pct = max(0.0, self._battery_pct - self.drain_rate_per_tick)

        ts = self.ts_provider() if self.ts_provider is not None else float(self._tick_count)

        return {
            "ts": ts,
            "kind": "collar.reading",
            "ranch": self.ranch_id,
            "entity": self.cow_tag,
            "pos": [self._pos[0], self._pos[1]],
            "heading_deg": round(self._heading_deg, 2),
            "activity": activity,
            "battery_pct": round(self._battery_pct, 2),
            "heart_rate_bpm": round(self._heart_rate, 2),
            "source": "sim",
        }


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _weighted_choice(rng: random.Random, weights: tuple[float, ...]) -> int:
    """Seed-driven weighted index choice. ``weights`` must sum to ~1.0."""
    r = rng.random()
    acc = 0.0
    for idx, w in enumerate(weights):
        acc += w
        if r < acc:
            return idx
    return len(weights) - 1


# ----------------------------------------------------------------------
# Async driver — pumps N ticks into an injected bus / publish callable
# ----------------------------------------------------------------------


MqttPublishFn = Callable[[str, dict[str, object]], Awaitable[None]]


async def run_async(
    emitter: CollarSimEmitter,
    publish: MqttPublishFn,
    *,
    count: int,
) -> list[dict[str, object]]:
    """Tick the emitter ``count`` times, publish each payload, and return them.

    ``publish`` must be an async callable ``async (topic: str, payload: dict) -> None``.
    This shape is intentionally generic so callers can hand us a mock bus in
    tests or a real :class:`~skyherd.sensors.bus.SensorBus` in production. No
    ``asyncio.sleep`` is introduced — determinism is preserved.
    """
    emitted: list[dict[str, object]] = []
    for _ in range(count):
        payload = emitter.tick()
        await publish(emitter.topic, payload)
        emitted.append(payload)
    return emitted


__all__ = ["CollarSimEmitter", "run_async"]
