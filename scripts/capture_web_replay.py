#!/usr/bin/env python3
"""Capture one end-to-end sim run to web/public/replay.v2.json.

Runs 5 scenarios (coyote, sick_cow, water_drop, calving, storm) in-process
against a real EventBroadcaster + _DemoMesh + World + Ledger, subscribes to
every (kind, payload) event the broadcaster emits, and writes them to a
single JSON bundle the browser replays faithfully in demo mode.

Usage
-----
    uv run python scripts/capture_web_replay.py \\
        --seed 42 --out web/public/replay.v2.json

The output is committed to the repo and shipped as a static asset.

Determinism
-----------
World evolution + agent tool-call order are seed-driven and byte-identical
across runs. Wall-clock timestamps inside event payloads (``ts`` fields,
``ts_iso``) are NOT sanitized here — the web replay keys on ``ts_rel`` only.
Ledger hashes change run-to-run because Signer.generate() is random; this
is expected and fine for the demo (judges don't diff hashes).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from skyherd.attest.ledger import Ledger  # noqa: E402
from skyherd.attest.signer import Signer  # noqa: E402
from skyherd.scenarios import SCENARIOS  # noqa: E402
from skyherd.scenarios.base import _DemoMesh, _run_async_shared  # noqa: E402
from skyherd.server.events import EventBroadcaster  # noqa: E402
from skyherd.world.world import make_world  # noqa: E402

logger = logging.getLogger("capture_web_replay")

# Canonical order for the web demo. Matches plan Phase A3.3.
SCENARIOS_FOR_DEMO: list[str] = [
    "coyote",
    "sick_cow",
    "water_drop",
    "calving",
    "storm",
]

# Drone "home base" and target waypoints per scenario (normalized [0..1] coords).
# _DemoMesh only records launch_drone tool calls — it never moves a drone.
# We synthesize motion in-process so the web replay shows real dispatch paths.
_DRONE_HOME: tuple[float, float] = (0.5, 0.95)

_SCENARIO_DRONE_TARGETS: dict[str, tuple[float, float]] = {
    "coyote": (0.08, 0.20),  # SW fence
    "sick_cow": (0.35, 0.55),  # interior, near flagged cow cluster
    "water_drop": (0.82, 0.18),  # NE water tank
    "calving": (0.60, 0.40),  # calving paddock
    "storm": (0.50, 0.50),  # center — weather observation
}

# Seconds from scenario start at which the drone takes off, reaches target,
# loiters, then returns. Keyed to scenario pacing — all scenarios are 600 s.
_DRONE_TAKEOFF_S = 60.0
_DRONE_ARRIVAL_S = 180.0
_DRONE_LOITER_END_S = 300.0
_DRONE_RETURN_S = 420.0

# Dedupe: drop any event identical (kind, canonical_payload) to the prior
# one within this ts_rel window — kills the water.low repeat spam without
# losing meaningful deltas.
_DEDUPE_WINDOW_S = 10.0

# Clamp world.snapshot emission to every 2s-in-sim-time (matches live cadence)
# and cost.tick to every 1s. Anything faster is redundant.
_SNAPSHOT_MIN_INTERVAL_S = 1.8
_COST_MIN_INTERVAL_S = 0.9


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
        return out
    except Exception:  # noqa: BLE001
        return "unknown"


# ---------------------------------------------------------------------------
# DroneChoreographer — synthesizes drone telemetry into World.set_drone_state
# each sim step. Triggered by scenario name; _DemoMesh never moves drones.
# ---------------------------------------------------------------------------


class DroneChoreographer:
    """Push drone state into the World on each tick based on scenario phase."""

    def __init__(self, world: Any, scenario_name: str) -> None:
        self._world = world
        self._name = scenario_name
        self._target = _SCENARIO_DRONE_TARGETS.get(scenario_name, (0.5, 0.5))
        self._home = _DRONE_HOME
        self._battery = 100.0

    def _lerp(
        self,
        a: tuple[float, float],
        b: tuple[float, float],
        t: float,
    ) -> tuple[float, float]:
        t = max(0.0, min(1.0, t))
        # Ease in/out cubic for graceful motion.
        if t < 0.5:
            ease = 4.0 * t * t * t
        else:
            ease = 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0
        return (
            a[0] + (b[0] - a[0]) * ease,
            a[1] + (b[1] - a[1]) * ease,
        )

    def update(self, sim_elapsed_s: float) -> None:
        """Compute drone state at *sim_elapsed_s* and push into world."""
        # Battery drains ~7% over a 600 s scenario when airborne.
        if sim_elapsed_s < _DRONE_TAKEOFF_S:
            # Idle at base — altitude = 0. Don't show drone on map.
            self._world.set_drone_state(None)
            return

        if sim_elapsed_s < _DRONE_ARRIVAL_S:
            # Takeoff + transit home → target.
            t = (sim_elapsed_s - _DRONE_TAKEOFF_S) / (_DRONE_ARRIVAL_S - _DRONE_TAKEOFF_S)
            pos = self._lerp(self._home, self._target, t)
            alt = 10.0 + t * 35.0
            state = "transit"
        elif sim_elapsed_s < _DRONE_LOITER_END_S:
            # Loiter over target with small orbit.
            phase = (sim_elapsed_s - _DRONE_ARRIVAL_S) * 0.3
            pos = (
                self._target[0] + 0.015 * math.cos(phase),
                self._target[1] + 0.015 * math.sin(phase),
            )
            alt = 45.0
            state = "loiter"
        elif sim_elapsed_s < _DRONE_RETURN_S:
            # Transit target → home.
            t = (sim_elapsed_s - _DRONE_LOITER_END_S) / (_DRONE_RETURN_S - _DRONE_LOITER_END_S)
            pos = self._lerp(self._target, self._home, t)
            alt = 45.0 - t * 35.0
            state = "rtb"
        else:
            # Landed at base.
            self._world.set_drone_state(None)
            return

        battery = max(70.0, 100.0 - (sim_elapsed_s / 600.0) * 25.0)
        self._world.set_drone_state(
            {
                "pos": [pos[0], pos[1]],
                "state": state,
                "alt_m": round(alt, 1),
                "battery_pct": round(battery, 1),
                "target": list(self._target),
            }
        )


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------


def _register_subscriber(
    broadcaster: EventBroadcaster,
) -> asyncio.Queue[tuple[str, dict[str, Any]] | None]:
    """Register a subscriber queue on the broadcaster synchronously.

    Using the async-generator ``subscribe()`` API has a registration race: the
    queue only gets added to ``_subscribers`` after the first ``__anext__()``
    awaits, which can miss the opening scenario.active / cost.tick events.
    Register the queue directly so it captures the very first broadcast.
    """
    q: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue(maxsize=4096)
    broadcaster._subscribers.append(q)  # noqa: SLF001 — capture-script-only
    return q


async def _drain_queue(
    q: asyncio.Queue[tuple[str, dict[str, Any]] | None],
    sink: list[tuple[float, str, dict[str, Any]]],
    scenario_start_ref: list[float],
) -> None:
    """Drain *q* into *sink* until None sentinel arrives."""
    n = 0
    while True:
        item = await q.get()
        if item is None:
            logger.debug("drain_queue: received None sentinel after %d events", n)
            return
        kind, payload = item
        ts_rel = max(0.0, time.monotonic() - scenario_start_ref[0])
        sink.append((ts_rel, kind, payload))
        n += 1


async def _drone_ticker(
    world: Any,
    scenario_name: str,
    start_ref: list[float],
    duration_s: float,
    speed: float,
    stop_event: asyncio.Event,
) -> None:
    """Push synthesized drone state into world every 500ms wall = ~7.5s sim."""
    choreographer = DroneChoreographer(world, scenario_name)
    try:
        while not stop_event.is_set():
            # Convert wall elapsed → sim elapsed via the configured speed.
            wall_elapsed = time.monotonic() - start_ref[0]
            sim_elapsed = wall_elapsed * speed
            if sim_elapsed >= duration_s:
                break
            choreographer.update(sim_elapsed)
            await asyncio.sleep(0.5)
    finally:
        world.set_drone_state(None)


def _dedupe(
    events: list[dict[str, Any]],
    window_s: float = _DEDUPE_WINDOW_S,
) -> list[dict[str, Any]]:
    """Drop events with identical (kind, payload) within *window_s* of the prior."""
    out: list[dict[str, Any]] = []
    last_key: dict[str, tuple[str, float]] = {}  # kind → (payload_fp, ts_rel)
    for ev in events:
        kind = ev["kind"]
        try:
            fp = json.dumps(ev["payload"], sort_keys=True, default=str)
        except (TypeError, ValueError):
            fp = repr(ev["payload"])
        prev = last_key.get(kind)
        if prev is not None:
            prev_fp, prev_t = prev
            if prev_fp == fp and (ev["ts_rel"] - prev_t) < window_s:
                continue
        last_key[kind] = (fp, ev["ts_rel"])
        out.append(ev)
    return out


def _throttle_snapshots_and_costs(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Enforce minimum inter-event spacing for world.snapshot and cost.tick.

    The broadcaster fires on wall-clock cadence inside an async loop, but the
    capture runs scenarios at 15x+ speed so many dozens fire in quick succession.
    We keep one every _SNAPSHOT_MIN_INTERVAL_S / _COST_MIN_INTERVAL_S ts_rel
    seconds so the replay bundle stays small.
    """
    out: list[dict[str, Any]] = []
    last_snapshot = -1e9
    last_cost = -1e9
    for ev in events:
        kind = ev["kind"]
        t = ev["ts_rel"]
        if kind == "world.snapshot":
            if t - last_snapshot < _SNAPSHOT_MIN_INTERVAL_S:
                continue
            last_snapshot = t
        elif kind == "cost.tick":
            if t - last_cost < _COST_MIN_INTERVAL_S:
                continue
            last_cost = t
        out.append(ev)
    return out


async def _capture_one_scenario(
    name: str,
    seed: int,
    speed: float,
) -> dict[str, Any]:
    """Run one scenario end-to-end, return the bundle block for it."""
    scenario_cls = SCENARIOS[name]
    scenario = scenario_cls()

    # Fresh world + ledger + mesh per scenario so state doesn't bleed.
    world = make_world(seed=seed)
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    ledger = Ledger.open(tmp.name, Signer.generate())
    mesh = _DemoMesh(ledger=ledger)

    # Real broadcaster — mock=False so world.snapshot reflects REAL world
    # AND _attest_loop iterates the real signed ledger (real hashes in demo).
    # In addition we piggyback the mock_agent_log producer task so AgentLanes
    # sees rotating chatter on top of the real attest-mirror events.
    broadcaster = EventBroadcaster(mock=False, mesh=mesh, ledger=ledger, world=world)

    sink: list[tuple[float, str, dict[str, Any]]] = []
    start_ref = [time.monotonic()]
    stop_event = asyncio.Event()

    # Register subscriber queue BEFORE broadcaster starts — no registration race.
    sub_queue = _register_subscriber(broadcaster)
    broadcaster.start()
    # Piggyback the mock agent-log loop so AgentLane chatter still streams
    # (broadcaster.start() only launches it when self._mock is True).
    broadcaster._tasks.append(  # noqa: SLF001
        asyncio.create_task(
            broadcaster._mock_agent_log_loop(),  # noqa: SLF001
            name=f"capture-mock-log-{name}",
        )
    )

    sub_task = asyncio.create_task(
        _drain_queue(sub_queue, sink, start_ref),
        name=f"capture-sub-{name}",
    )
    drone_task = asyncio.create_task(
        _drone_ticker(world, name, start_ref, scenario.duration_s, speed, stop_event),
        name=f"capture-drone-{name}",
    )

    logger.info(
        "→ capturing scenario %r (duration=%.0fs sim, speed=%.1fx)",
        name,
        scenario.duration_s,
        speed,
    )
    t0 = time.monotonic()
    try:
        result = await _run_async_shared(
            scenario,
            world=world,
            ledger=ledger,
            mesh=mesh,
            seed=seed,
            speed=speed,
            assert_outcome=False,
            broadcaster=broadcaster,
        )
    finally:
        scenario_wall_end = time.monotonic() - start_ref[0]
        # Stop drone ticker first.
        stop_event.set()
        drone_task.cancel()
        try:
            await drone_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        # Give the subscriber one more tick to drain scenario.ended and any
        # trailing world.snapshot / attest.append that fired right at the end.
        await asyncio.sleep(0.4)
        # Stop the broadcaster — its subscribe() iterator will yield, then
        # receive the None sentinel and exit the async-for cleanly.
        broadcaster.stop()
        try:
            await asyncio.wait_for(sub_task, timeout=2.0)
        except (TimeoutError, asyncio.CancelledError, Exception):  # noqa: BLE001
            if not sub_task.done():
                sub_task.cancel()
                try:
                    await sub_task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
        try:
            ledger._conn.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            Path(tmp.name).unlink()
        except OSError:
            pass

    wall_elapsed = time.monotonic() - t0
    # Re-key ts_rel as sim-time: wall_elapsed → sim_elapsed via speed scalar.
    # Clip to (a) the point where the scenario loop exited and (b) the
    # scenario's declared duration + a short tail for the ended-beacon. This
    # way we never discard real events fired during the scenario even if
    # subscriber cleanup adds wall time afterward.
    events: list[dict[str, Any]] = []
    max_ts_rel_wall = scenario_wall_end + 0.5
    max_ts_rel_sim = scenario.duration_s + 10.0
    for ts_rel_wall, kind, payload in sink:
        if ts_rel_wall > max_ts_rel_wall:
            continue
        # Stretch to sim-time: an event at wall=12s with speed=25x should
        # land at ts_rel=300s in the replay.
        if ts_rel_wall <= scenario_wall_end:
            ts_rel_sim = (ts_rel_wall / max(scenario_wall_end, 0.001)) * scenario.duration_s
        else:
            ts_rel_sim = scenario.duration_s + (ts_rel_wall - scenario_wall_end)
        if ts_rel_sim > max_ts_rel_sim:
            continue
        events.append(
            {
                "ts_rel": round(ts_rel_sim, 3),
                "kind": kind,
                "payload": payload,
            }
        )

    # Stable ordering by ts_rel then kind.
    events.sort(key=lambda e: (e["ts_rel"], e["kind"]))

    before = len(events)
    events = _throttle_snapshots_and_costs(events)
    events = _dedupe(events)
    after = len(events)

    # Per-kind summary for the CLI report.
    kind_counts: dict[str, int] = {}
    for ev in events:
        kind_counts[ev["kind"]] = kind_counts.get(ev["kind"], 0) + 1

    logger.info(
        "  captured %d → %d events (kind breakdown: %s) in %.1fs wall (sim %d tools)",
        before,
        after,
        ", ".join(f"{k}:{v}" for k, v in sorted(kind_counts.items())),
        wall_elapsed,
        sum(len(v) for v in result.agent_tool_calls.values()),
    )

    return {
        "name": name,
        "duration_s": scenario.duration_s,
        "event_count": len(events),
        "kind_counts": kind_counts,
        "events": events,
    }


async def _capture_all(seed: int, speed: float) -> dict[str, Any]:
    bundle: dict[str, Any] = {
        "version": 2,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "seed": seed,
        "git_sha": _git_sha(),
        "scenarios": [],
    }
    for name in SCENARIOS_FOR_DEMO:
        entry = await _capture_one_scenario(name, seed, speed)
        bundle["scenarios"].append(entry)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "web" / "public" / "replay.v2.json",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=25.0,
        help="sim-to-wall ratio (default 25 → ~24s wall per 600s scenario)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bundle = asyncio.run(_capture_all(args.seed, args.speed))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Pretty-print is ~1.5x the size of compact but still trivially gzipped
    # on Vercel. Use compact to keep the wire size down.
    args.out.write_text(json.dumps(bundle, default=str, separators=(",", ":")))

    total_events = sum(s["event_count"] for s in bundle["scenarios"])
    size = args.out.stat().st_size
    logger.info(
        "=== Wrote %s (%d scenarios, %d events, %.1f KB) ===",
        args.out,
        len(bundle["scenarios"]),
        total_events,
        size / 1024.0,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
