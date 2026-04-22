"""World CLI — tick the world sim for N seconds and print events.

Usage
-----

    uv run python -m skyherd.world.cli --seed 42 --duration 300

Prints one JSON event per line to stdout.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Annotated

import typer

from skyherd.world.world import make_world

_WORLD_CONFIG = Path(__file__).parent.parent.parent.parent / "worlds" / "ranch_a.yaml"
_STEP_DT = 5.0

app = typer.Typer(name="world-cli", add_completion=False)
logger = logging.getLogger(__name__)


@app.command()
def run(
    seed: Annotated[int, typer.Option("--seed", help="RNG seed.")] = 42,
    duration: Annotated[float, typer.Option("--duration", help="Sim seconds to run.")] = 300.0,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Tick the world simulation for DURATION seconds and print events as JSONL."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

    world = make_world(seed=seed, config_path=_WORLD_CONFIG)
    elapsed = 0.0
    event_count = 0

    while elapsed < duration:
        events = world.step(_STEP_DT)
        elapsed += _STEP_DT
        for ev in events:
            print(json.dumps(ev))
            event_count += 1

    if verbose:
        print(
            json.dumps(
                {
                    "summary": True,
                    "seed": seed,
                    "duration_s": duration,
                    "total_events": event_count,
                }
            ),
            file=sys.stderr,
        )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
