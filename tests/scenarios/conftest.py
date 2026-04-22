"""Shared fixtures for scenario tests.

Provides:
- ``scenarios_snapshot``: autouse fixture that snapshots SCENARIOS dict before
  each test and restores it afterward, preventing cross-test pollution from
  any test that registers extra scenarios or mutates the dict.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def scenarios_snapshot():
    """Snapshot the SCENARIOS dict before each test; restore after.

    This prevents test_run_all.py from contaminating wildfire/rustling/
    cross_ranch tests when they share a single pytest session.
    """
    from skyherd.scenarios import SCENARIOS

    # Take a shallow copy of the dict and its reference
    original_keys = list(SCENARIOS.keys())
    original_values = dict(SCENARIOS)

    yield

    # Restore: remove any keys added during the test, restore any removed
    keys_to_remove = [k for k in SCENARIOS if k not in original_values]
    for k in keys_to_remove:
        del SCENARIOS[k]

    for k, v in original_values.items():
        SCENARIOS[k] = v

    # Restore original insertion order
    for k in list(SCENARIOS.keys()):
        if k not in original_keys:
            del SCENARIOS[k]
