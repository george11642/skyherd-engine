"""Tests for _run_async_shared - the external-deps scenario runner.

Contract: _run_async_shared never mints its own world/ledger/mesh. When a
caller passes their own ledger, scenario tool-calls land in THAT ledger
(not a fresh one). This is the foundation for the ambient driver.
"""

from __future__ import annotations

import tempfile

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.scenarios import SCENARIOS
from skyherd.scenarios.base import _DemoMesh, _run_async_shared
from skyherd.world.world import make_world


def _make_deps(seed: int = 42) -> tuple:
    world = make_world(seed=seed)
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    signer = Signer.generate()
    ledger = Ledger.open(tmp.name, signer)
    mesh = _DemoMesh(ledger=ledger)
    return world, ledger, mesh, tmp.name


async def test_shared_runner_uses_caller_ledger() -> None:
    """Tool-calls land in the caller's ledger, not a freshly-minted one."""
    world, ledger, mesh, _path = _make_deps(seed=42)

    # Baseline: how many entries live in the caller ledger before play.
    before = len(list(ledger.iter_events()))

    scenario = SCENARIOS["coyote"]()
    result = await _run_async_shared(
        scenario,
        world=world,
        ledger=ledger,
        mesh=mesh,
        seed=42,
        speed=0.0,  # fast path - no throttle
        assert_outcome=False,
    )

    # The same ledger we passed grew.
    after = len(list(ledger.iter_events()))
    assert after > before, "caller ledger should accumulate scenario entries"

    # ScenarioResult reports those same entries.
    assert len(result.attestation_entries) == after
    assert result.name == "coyote"
    assert result.outcome_passed is True


async def test_shared_runner_skips_assert_outcome_by_default() -> None:
    """assert_outcome=False is the ambient default; no verdict runs."""
    world, ledger, mesh, _ = _make_deps(seed=42)

    # An always-failing scenario still yields outcome_passed=True in ambient.
    class _BrokenScenario:
        name = "broken"
        description = ""
        duration_s = 10.0

        def setup(self, _world):
            pass

        def inject_events(self, _world, _t):
            return []

        def assert_outcome(self, _events, _mesh):
            raise AssertionError("this should NOT be evaluated when assert_outcome=False")

    result = await _run_async_shared(
        _BrokenScenario(),
        world=world,
        ledger=ledger,
        mesh=mesh,
        speed=0.0,
        assert_outcome=False,
    )
    assert result.outcome_passed is True
    assert result.outcome_error is None


async def test_shared_runner_respects_speed_throttle() -> None:
    """speed>0 sleeps between steps; speed<=0 runs at fast-path speed."""
    import time

    world, ledger, mesh, _ = _make_deps(seed=42)

    class _TinyScenario:
        name = "tiny"
        description = ""
        duration_s = 20.0  # 4 steps at _STEP_DT=5.0

        def setup(self, _world):
            pass

        def inject_events(self, _world, _t):
            return []

        def assert_outcome(self, _events, _mesh):
            pass

    # High speed -> very small sleeps -> fast wall time.
    t0 = time.monotonic()
    await _run_async_shared(
        _TinyScenario(),
        world=world,
        ledger=ledger,
        mesh=mesh,
        speed=1000.0,
        assert_outcome=False,
    )
    elapsed_fast = time.monotonic() - t0

    # No throttle at all -> even faster (and always finishes).
    t0 = time.monotonic()
    await _run_async_shared(
        _TinyScenario(),
        world=world,
        ledger=ledger,
        mesh=mesh,
        speed=0.0,
        assert_outcome=False,
    )
    elapsed_no_throttle = time.monotonic() - t0

    assert elapsed_fast < 1.0, f"even throttled loop should be fast, got {elapsed_fast:.3f}s"
    assert elapsed_no_throttle < 1.0
