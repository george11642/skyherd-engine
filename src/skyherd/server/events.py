"""EventBroadcaster — merges all SkyHerd event sources into a single SSE stream.

Sources merged:
- World snapshot (every SNAPSHOT_INTERVAL_S seconds)
- Agent cost ticks (from AgentMesh / mock)
- Attestation ledger tail (new entries)
- MQTT sensor bus (fence.breach, drone.update, etc.)
- Synthetic mock events (when SKYHERD_MOCK=1)

Each SSE event has the shape:
    event: <event_type>
    data: <json_payload>
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from collections.abc import AsyncIterator
from typing import Any

logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL_S: float = 2.0
COST_TICK_INTERVAL_S: float = 1.0
ATTEST_POLL_INTERVAL_S: float = 3.0
MOCK_EVENT_INTERVAL_S: float = 0.8

AGENT_NAMES = [
    "FenceLineDispatcher",
    "HerdHealthWatcher",
    "PredatorPatternLearner",
    "GrazingOptimizer",
    "CalvingWatch",
]


def _json(obj: Any) -> str:
    return json.dumps(obj, default=str)


# ---------------------------------------------------------------------------
# Mock data generators
# ---------------------------------------------------------------------------


def _mock_world_snapshot() -> dict[str, Any]:
    t = time.time()
    rng = random.Random(int(t * 10) % 10000)
    cows = [
        {
            "id": f"cow_{i:03d}",
            "tag": f"T{i:03d}",
            "pos": [rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9)],
            "bcs": rng.uniform(4.0, 7.0),
            "state": rng.choice(["grazing", "resting", "walking"]),
        }
        for i in range(12)
    ]
    predators = []
    if rng.random() < 0.2:
        predators.append(
            {
                "id": "pred_001",
                "species": "coyote",
                "pos": [rng.uniform(0.0, 1.0), rng.uniform(0.0, 1.0)],
                "threat_level": rng.choice(["low", "medium", "high"]),
            }
        )
    return {
        "ts": t,
        "sim_time_s": t % 86400,
        "clock_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t)),
        "is_night": (int(t / 3600) % 24) < 6 or (int(t / 3600) % 24) > 20,
        "weather": {
            "conditions": rng.choice(["clear", "clear", "clear", "cloudy", "storm"]),
            "temp_f": rng.uniform(55.0, 85.0),
            "wind_kt": rng.uniform(0.0, 25.0),
            "humidity_pct": rng.uniform(20.0, 70.0),
        },
        "cows": cows,
        "predators": predators,
        "drone": {
            "lat": 34.123 + rng.uniform(-0.005, 0.005),
            "lon": -106.456 + rng.uniform(-0.005, 0.005),
            "alt_m": rng.uniform(20.0, 80.0),
            "state": rng.choice(["idle", "patrol", "investigating"]),
            "battery_pct": rng.uniform(50.0, 100.0),
        },
        "paddocks": [
            {"id": "north", "bounds": [0.0, 0.0, 0.5, 0.5], "forage_pct": 72.0},
            {"id": "south", "bounds": [0.5, 0.0, 1.0, 0.5], "forage_pct": 58.0},
            {"id": "east", "bounds": [0.5, 0.5, 1.0, 1.0], "forage_pct": 84.0},
            {"id": "west", "bounds": [0.0, 0.5, 0.5, 1.0], "forage_pct": 43.0},
        ],
        "water_tanks": [
            {"id": "tank_a", "pos": [0.25, 0.25], "level_pct": rng.uniform(30.0, 95.0)},
            {"id": "tank_b", "pos": [0.75, 0.75], "level_pct": rng.uniform(15.0, 90.0)},
        ],
    }


def _mock_cost_tick(seq: int) -> dict[str, Any]:
    t = time.time()
    # Cycle: 10s active, 5s idle per agent
    period = 15
    offset_map = {name: i * 3 for i, name in enumerate(AGENT_NAMES)}
    agents = []
    all_idle = True
    total_cost = 0.0
    for name in AGENT_NAMES:
        phase = int(t + offset_map[name]) % period
        state = "active" if phase < 10 else "idle"
        if state == "active":
            all_idle = False
        cost_delta = (0.08 / 3600.0) if state == "active" else 0.0
        cum_cost = seq * 0.08 / 3600.0 * 10 / 15  # approx
        total_cost += cum_cost
        agents.append(
            {
                "name": name,
                "state": state,
                "cost_delta_usd": round(cost_delta, 8),
                "cumulative_cost_usd": round(cum_cost, 6),
                "tokens_in": seq * 120,
                "tokens_out": seq * 45,
            }
        )
    return {
        "ts": t,
        "seq": seq,
        "agents": agents,
        "all_idle": all_idle,
        "rate_per_hr_usd": 0.0 if all_idle else 0.08,
        "total_cumulative_usd": round(total_cost, 6),
    }


_MOCK_LOG_LINES = {
    "FenceLineDispatcher": [
        "Breach detected on seg_1 — dispatching drone patrol",
        "Thermal signature classified: coyote (87% confidence)",
        "MAVLink mission uploaded: 6-waypoint perimeter sweep",
        "Deterrent played — airhorn.wav 3x",
        "Session sleeping — no active threats",
    ],
    "HerdHealthWatcher": [
        "Motion scan complete — 12 cattle accounted for",
        "Cow T007: lameness indicator score 0.73 (threshold 0.70)",
        "Flagging T007 for vet follow-up",
        "BCS survey: median 5.8 — within normal range",
        "No anomalies detected — returning to idle",
    ],
    "PredatorPatternLearner": [
        "Analyzing last 72h thermal clips",
        "Pattern detected: coyote crossing fence-NE at 02:30–03:15",
        "Updating patrol schedule recommendation",
        "Nightly analysis complete — 2 risk corridors flagged",
        "Session idle until next thermal batch",
    ],
    "GrazingOptimizer": [
        "Forage assessment: west paddock at 43% — rotation recommended",
        "Proposal: move herd from west → east by Thursday",
        "Weather-adjusted: storm front Friday — accelerating move",
        "Rotation plan filed to attestation ledger",
        "Session idle — next run Monday 06:00",
    ],
    "CalvingWatch": [
        "Collar IMU: cow T031 showing pre-labor activity pattern",
        "Elevated flank movement + isolation behavior detected",
        "Paging rancher: PRIORITY — T031 calving imminent",
        "Wes call initiated via Twilio",
        "Session monitoring — next check in 30 min",
    ],
}

_mock_log_seq: dict[str, int] = {name: 0 for name in AGENT_NAMES}
_mock_attest_seq: int = 0


def _mock_agent_log(rng: random.Random) -> dict[str, Any]:
    name = rng.choice(AGENT_NAMES)
    lines = _MOCK_LOG_LINES[name]
    idx = _mock_log_seq[name] % len(lines)
    _mock_log_seq[name] += 1
    phase = int(time.time() + list(AGENT_NAMES).index(name) * 3) % 15
    state = "active" if phase < 10 else "idle"
    return {
        "ts": time.time(),
        "agent": name,
        "state": state,
        "message": lines[idx],
        "level": "INFO",
    }


def _mock_attest_entry() -> dict[str, Any]:
    global _mock_attest_seq
    _mock_attest_seq += 1
    kinds = ["sensor.reading", "cost.tick", "fence.breach", "agent.wake", "agent.sleep"]
    sources = [
        "skyherd/ranch_a/fence/seg_1",
        "skyherd/ranch_a/cost/ticker",
        "skyherd/ranch_a/collar/tag_007",
        "FenceLineDispatcher",
        "HerdHealthWatcher",
    ]
    rng = random.Random(_mock_attest_seq)
    return {
        "seq": _mock_attest_seq,
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": rng.choice(sources),
        "kind": rng.choice(kinds),
        "payload_json": '{"mock":true,"seq":' + str(_mock_attest_seq) + "}",
        "prev_hash": f"deadbeef{_mock_attest_seq - 1:08x}",
        "event_hash": f"cafebabe{_mock_attest_seq:08x}",
        "signature": "a1b2c3d4" * 16,
        "pubkey": "-----BEGIN PUBLIC KEY-----\nMOCK_KEY\n-----END PUBLIC KEY-----",
    }


# ---------------------------------------------------------------------------
# EventBroadcaster
# ---------------------------------------------------------------------------


class EventBroadcaster:
    """Merges all event sources into a shared async queue.

    Consumers call :meth:`subscribe` to get an async iterator of
    ``(event_type, payload_dict)`` tuples.

    Backpressure: each subscriber has a bounded queue (maxsize=100).
    Slow consumers drop old events rather than blocking producers.
    """

    def __init__(
        self,
        mock: bool = False,
        mesh: Any = None,
        ledger: Any = None,
        world: Any = None,
    ) -> None:
        self._mock = mock
        self._mesh = mesh
        self._ledger = ledger
        self._world = world
        self._subscribers: list[asyncio.Queue[tuple[str, dict[str, Any]] | None]] = []
        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []
        self._cost_seq = 0
        self._rng = random.Random(42)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Launch all background producer tasks."""
        self._tasks = [
            asyncio.create_task(self._snapshot_loop(), name="broadcaster-snapshot"),
            asyncio.create_task(self._cost_loop(), name="broadcaster-cost"),
            asyncio.create_task(self._attest_loop(), name="broadcaster-attest"),
        ]
        if self._mock:
            self._tasks.append(
                asyncio.create_task(self._mock_agent_log_loop(), name="broadcaster-mock-log")
            )

    def stop(self) -> None:
        self._stop_event.set()
        for t in self._tasks:
            t.cancel()
        # Signal all subscribers
        for q in self._subscribers:
            q.put_nowait(None)

    # ------------------------------------------------------------------
    # Subscribe
    # ------------------------------------------------------------------

    async def subscribe(self) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        """Yield (event_type, payload) tuples until the broadcaster stops."""
        q: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        try:
            while True:
                item = await q.get()
                if item is None:
                    break
                yield item
        finally:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # Internal broadcast
    # ------------------------------------------------------------------

    def _broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        for q in self._subscribers:
            try:
                q.put_nowait((event_type, payload))
            except asyncio.QueueFull:
                # Slow consumer — drop oldest, put newest
                try:
                    q.get_nowait()
                    q.put_nowait((event_type, payload))
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    # ------------------------------------------------------------------
    # Producer loops
    # ------------------------------------------------------------------

    async def _snapshot_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self._mock or self._world is None:
                    snapshot = _mock_world_snapshot()
                else:
                    snapshot = self._world.snapshot().model_dump()
                self._broadcast("world.snapshot", snapshot)
            except Exception as exc:  # noqa: BLE001
                logger.debug("snapshot loop error: %s", exc)
            await asyncio.sleep(SNAPSHOT_INTERVAL_S)

    async def _cost_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._cost_seq += 1
                if self._mock or self._mesh is None:
                    tick = _mock_cost_tick(self._cost_seq)
                else:
                    # Pull from real mesh tickers
                    tick = self._real_cost_tick()
                self._broadcast("cost.tick", tick)
            except Exception as exc:  # noqa: BLE001
                logger.debug("cost loop error: %s", exc)
            await asyncio.sleep(COST_TICK_INTERVAL_S)

    def _real_cost_tick(self) -> dict[str, Any]:
        """Aggregate cost tickers from a live AgentMesh."""
        agents = []
        all_idle = True
        total_cost = 0.0
        for name, session in self._mesh._sessions.items():
            ticker = self._mesh._session_manager._tickers.get(session.id)
            if ticker is None:
                continue
            state = ticker._current_state
            if state == "active":
                all_idle = False
            agents.append(
                {
                    "name": name,
                    "state": state,
                    "cost_delta_usd": 0.0,
                    "cumulative_cost_usd": round(ticker.cumulative_cost_usd, 6),
                    "tokens_in": ticker._cumulative_tokens_in,
                    "tokens_out": ticker._cumulative_tokens_out,
                }
            )
            total_cost += ticker.cumulative_cost_usd
        return {
            "ts": time.time(),
            "seq": self._cost_seq,
            "agents": agents,
            "all_idle": all_idle,
            "rate_per_hr_usd": 0.0 if all_idle else 0.08,
            "total_cumulative_usd": round(total_cost, 6),
        }

    async def _attest_loop(self) -> None:
        last_seq = 0
        while not self._stop_event.is_set():
            try:
                if self._mock or self._ledger is None:
                    # Emit one mock attest entry every 3 polls
                    if self._cost_seq % 3 == 0:
                        entry = _mock_attest_entry()
                        self._broadcast("attest.append", entry)
                else:
                    for event in self._ledger.iter_events(since_seq=last_seq):
                        self._broadcast("attest.append", event.model_dump())
                        last_seq = event.seq
            except Exception as exc:  # noqa: BLE001
                logger.debug("attest loop error: %s", exc)
            await asyncio.sleep(ATTEST_POLL_INTERVAL_S)

    async def _mock_agent_log_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                log_entry = _mock_agent_log(self._rng)
                self._broadcast("agent.log", log_entry)
            except Exception as exc:  # noqa: BLE001
                logger.debug("mock log loop error: %s", exc)
            await asyncio.sleep(MOCK_EVENT_INTERVAL_S)

    def broadcast_neighbor_handoff(self, payload: dict[str, Any]) -> None:
        """Publish a ``neighbor.handoff`` SSE event to all subscribers.

        Called by CrossRanchMesh when ranch_b FenceLineDispatcher responds to a
        neighbor alert in pre_position mode.  The dashboard ``/?view=cross-ranch``
        uses this to update the side-by-side ranch-map canvases.

        Payload shape::

            {
                "from_ranch": "ranch_a",
                "to_ranch":   "ranch_b",
                "species":    "coyote",
                "shared_fence": "fence_east",
                "response_mode": "pre_position",
                "tool_calls": ["get_thermal_clip", "launch_drone", "log_agent_event"],
                "rancher_paged": false,
                "ts": 1745200000.0,
            }
        """
        self._broadcast("neighbor.handoff", payload)
