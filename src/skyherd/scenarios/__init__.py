"""SkyHerd demo scenarios — 8 deterministic, seed-driven playbacks.

Usage
-----

Run a single scenario::

    from skyherd.scenarios import run
    result = run("coyote", seed=42)
    print(result.outcome_passed)

Run all 8 back-to-back::

    from skyherd.scenarios import run_all
    results = run_all(seed=42)

CLI::

    skyherd-demo play coyote --seed 42
    skyherd-demo play all --seed 42
    skyherd-demo list
"""

from __future__ import annotations

from skyherd.scenarios.base import ScenarioResult, run, run_all
from skyherd.scenarios.calving import CalvingScenario
from skyherd.scenarios.coyote import CoyoteScenario
from skyherd.scenarios.cross_ranch_coyote import CrossRanchCoyoteScenario
from skyherd.scenarios.rustling import RustlingScenario
from skyherd.scenarios.sick_cow import SickCowScenario
from skyherd.scenarios.storm import StormScenario
from skyherd.scenarios.water_drop import WaterDropScenario
from skyherd.scenarios.wildfire import WildfireScenario

# Canonical order for ``play all`` — 8 scenarios
SCENARIOS: dict[str, type] = {
    "coyote": CoyoteScenario,
    "sick_cow": SickCowScenario,
    "water_drop": WaterDropScenario,
    "calving": CalvingScenario,
    "storm": StormScenario,
    "cross_ranch_coyote": CrossRanchCoyoteScenario,
    "wildfire": WildfireScenario,
    "rustling": RustlingScenario,
}

__all__ = [
    "SCENARIOS",
    "ScenarioResult",
    "CalvingScenario",
    "CoyoteScenario",
    "CrossRanchCoyoteScenario",
    "RustlingScenario",
    "SickCowScenario",
    "StormScenario",
    "WaterDropScenario",
    "WildfireScenario",
    "run",
    "run_all",
]
