#!/usr/bin/env python3
"""Build-time script: reads runtime/scenario_runs/*.jsonl and writes web/public/replay.json.

Usage:
  python3 scripts/build-replay.py

If a seed-42 JSONL is missing for any scenario, the script first attempts to
regenerate via `uv run skyherd-demo play all --seed 42`, then retries.
If that also fails it synthesises 3 sample events per scenario so the deploy
still produces a browsable UI.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RUNS_DIR = REPO_ROOT / "runtime" / "scenario_runs"
OUT_FILE = REPO_ROOT / "web" / "public" / "replay.json"

SCENARIOS = ["coyote", "sick_cow", "water_drop", "calving", "storm"]


def _latest_seed42(scenario: str) -> Path | None:
    """Return the most-recent seed=42 JSONL for a scenario."""
    candidates = sorted(RUNS_DIR.glob(f"{scenario}_42_*.jsonl"))
    return candidates[-1] if candidates else None


def _run_demo() -> None:
    print("No seed-42 runs found — running `uv run skyherd-demo play all --seed 42` ...")
    try:
        subprocess.run(
            ["uv", "run", "skyherd-demo", "play", "all", "--seed", "42"],
            cwd=REPO_ROOT,
            check=True,
            timeout=300,
        )
    except Exception as exc:
        print(f"WARNING: demo run failed ({exc}); will use synthetic events.", file=sys.stderr)


def _synthetic_events(scenario: str) -> list[dict]:
    """Fallback: 3 hand-crafted sample events matching the SSE contract."""
    base = [
        {"ts_rel": 0.5, "kind": "water.low", "payload": {"tank_id": "wt_n", "level_pct": 15.0}},
        {
            "ts_rel": 2.0,
            "kind": "agent.log",
            "payload": {
                "agent": "FenceLineDispatcher",
                "state": "active",
                "msg": f"[{scenario}] monitoring active",
            },
        },
        {"ts_rel": 4.0, "kind": "cost.tick", "payload": {"cost_usd_hr": 0.08, "total_usd": 0.001}},
    ]
    scenario_specials = {
        "coyote": {
            "ts_rel": 6.0,
            "kind": "fence.breach",
            "payload": {
                "fence_id": "fence_west",
                "lat": 34.123,
                "lon": -106.456,
                "species_hint": "coyote",
            },
        },
        "sick_cow": {
            "ts_rel": 6.0,
            "kind": "agent.log",
            "payload": {
                "agent": "HerdHealthWatcher",
                "msg": "Cow A014 — pinkeye flags elevated, escalating",
            },
        },
        "water_drop": {
            "ts_rel": 6.0,
            "kind": "drone.update",
            "payload": {"mission": "water_verify", "tank_id": "wt_sw", "level_pct_confirmed": 18.0},
        },
        "calving": {
            "ts_rel": 6.0,
            "kind": "agent.log",
            "payload": {
                "agent": "CalvingWatch",
                "msg": "Cow B007 pre-labor isolation detected, paging Wes",
            },
        },
        "storm": {
            "ts_rel": 6.0,
            "kind": "agent.log",
            "payload": {
                "agent": "GrazingOptimizer",
                "msg": "Storm ETA 20 min — proposing herd move to paddock_b",
            },
        },
    }
    if scenario in scenario_specials:
        base.append(scenario_specials[scenario])
    return base


def _parse_jsonl(path: Path) -> tuple[float, list[dict]]:
    """Parse a scenario JSONL.  Returns (duration_s, events_list)."""
    lines = path.read_text().splitlines()
    header = json.loads(lines[0])
    duration_s: float = header.get("duration_s", 60.0)

    events: list[dict] = []
    for raw in lines[1:]:
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if rec.get("record") != "event":
            continue

        kind = rec.get("type", "unknown")
        ts_rel: float = rec.get("sim_time_s", 0.0)

        # Build payload: everything except bookkeeping keys
        payload = {k: v for k, v in rec.items() if k not in ("record", "type", "sim_time_s")}

        # Map scenario event types to SSE event kinds understood by the dashboard
        # The SSE spec uses: world.snapshot, cost.tick, attest.append, agent.log,
        # fence.breach, drone.update  — plus passthrough for raw types.
        events.append({"ts_rel": ts_rel, "kind": kind, "payload": payload})

    # Inject a cost.tick every 30 sim-seconds if none present
    has_cost = any(e["kind"] == "cost.tick" for e in events)
    if not has_cost:
        tick = 0.0
        while tick <= duration_s:
            events.append(
                {
                    "ts_rel": tick,
                    "kind": "cost.tick",
                    "payload": {"cost_usd_hr": 0.08, "total_usd": round(tick / 3600 * 0.08, 6)},
                }
            )
            tick += 30.0

    # Sort by ts_rel so the replay driver can walk forward monotonically
    events.sort(key=lambda e: e["ts_rel"])

    # Cap at 300 events to keep replay.json under ~200 KB
    if len(events) > 300:
        # Keep the first event, last event, and a deterministic down-sample
        step = len(events) / 298
        sampled = [events[0]]
        idx = step
        while idx < len(events) - 1:
            sampled.append(events[int(idx)])
            idx += step
        sampled.append(events[-1])
        events = sampled

    return duration_s, events


def main() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Check if we need to regenerate
    missing = [s for s in SCENARIOS if _latest_seed42(s) is None]
    if missing:
        _run_demo()

    scenarios_out: list[dict] = []

    for scenario in SCENARIOS:
        path = _latest_seed42(scenario)
        if path is not None:
            try:
                duration_s, events = _parse_jsonl(path)
                scenarios_out.append(
                    {
                        "name": scenario,
                        "duration_s": duration_s,
                        "events": events,
                    }
                )
                print(f"  {scenario}: {len(events)} events from {path.name}")
            except Exception as exc:
                print(f"WARNING: failed to parse {path}: {exc}", file=sys.stderr)
                scenarios_out.append(
                    {
                        "name": scenario,
                        "duration_s": 60.0,
                        "events": _synthetic_events(scenario),
                    }
                )
        else:
            print(
                f"WARNING: no seed-42 run for {scenario}, using synthetic events", file=sys.stderr
            )
            scenarios_out.append(
                {
                    "name": scenario,
                    "duration_s": 60.0,
                    "events": _synthetic_events(scenario),
                }
            )

    payload = {"scenarios": scenarios_out, "generated_by": "scripts/build-replay.py", "seed": 42}
    OUT_FILE.write_text(json.dumps(payload, separators=(",", ":")))

    total_events = sum(len(s["events"]) for s in scenarios_out)
    size_kb = OUT_FILE.stat().st_size / 1024
    print(f"\nWrote {OUT_FILE}")
    print(
        f"  scenarios: {len(scenarios_out)}, total events: {total_events}, size: {size_kb:.1f} KB"
    )


if __name__ == "__main__":
    main()
