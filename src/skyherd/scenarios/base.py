"""Base classes for SkyHerd demo scenarios.

A Scenario is a deterministic, seed-driven, end-to-end playback that
demonstrates one complete nervous-system cascade.  Every scenario:

* Seeds the world from a known integer seed (default 42).
* Injects synthetic events at specific sim-time offsets.
* Drives the AgentMesh simulation path (no real API key required).
* Asserts expected outcomes on the resulting event stream + tool calls.
* Writes a JSONL replay log to runtime/scenario_runs/.
* Appends a human-readable summary to docs/REPLAY_LOG.md.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from skyherd.agents.calving_watch import CALVING_WATCH_SPEC
from skyherd.agents.calving_watch import handler as calving_handler
from skyherd.agents.fenceline_dispatcher import FENCELINE_DISPATCHER_SPEC
from skyherd.agents.fenceline_dispatcher import handler as fenceline_handler
from skyherd.agents.grazing_optimizer import GRAZING_OPTIMIZER_SPEC
from skyherd.agents.grazing_optimizer import handler as grazing_handler
from skyherd.agents.herd_health_watcher import HERD_HEALTH_WATCHER_SPEC
from skyherd.agents.herd_health_watcher import handler as herd_handler
from skyherd.agents.predator_pattern_learner import PREDATOR_PATTERN_LEARNER_SPEC
from skyherd.agents.predator_pattern_learner import handler as predator_handler
from skyherd.agents.session import Session, SessionManager
from skyherd.agents.spec import AgentSpec
from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.world.world import World, make_world

logger = logging.getLogger(__name__)

# Canonical agent registry — spec, handler pairs in mesh.py order.
# Mirrors src/skyherd/agents/mesh.py::_AGENT_REGISTRY so the scenario driver
# stays aligned with the live mesh. PredatorPatternLearner is included here
# (ROUT-01); the scenario routing table (line ~326) gains the wake-event
# types for it in Plan 02.
_SCENARIO_AGENT_REGISTRY: list[tuple[AgentSpec, Any]] = [
    (FENCELINE_DISPATCHER_SPEC, fenceline_handler),
    (HERD_HEALTH_WATCHER_SPEC, herd_handler),
    (PREDATOR_PATTERN_LEARNER_SPEC, predator_handler),
    (GRAZING_OPTIMIZER_SPEC, grazing_handler),
    (CALVING_WATCH_SPEC, calving_handler),
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent.parent  # src/skyherd/scenarios → skyherd-engine/
_WORLD_CONFIG = _REPO_ROOT / "worlds" / "ranch_a.yaml"
_RUNTIME_DIR = _REPO_ROOT / "runtime" / "scenario_runs"
_DOCS_DIR = _REPO_ROOT / "docs"

# Sim step size in seconds for scenario playback
_STEP_DT = 5.0


# ---------------------------------------------------------------------------
# ScenarioResult
# ---------------------------------------------------------------------------


@dataclass
class ScenarioResult:
    """Captures the full output of one scenario run."""

    name: str
    seed: int
    duration_s: float
    event_stream: list[dict[str, Any]] = field(default_factory=list)
    agent_tool_calls: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    attestation_entries: list[dict[str, Any]] = field(default_factory=list)
    outcome_passed: bool = False
    outcome_error: str | None = None
    wall_time_s: float = 0.0
    jsonl_path: Path | None = None


# ---------------------------------------------------------------------------
# Scenario abstract base
# ---------------------------------------------------------------------------


class Scenario(ABC):
    """Abstract base for all SkyHerd demo scenarios."""

    #: Machine-readable name (used as dict key and CLI argument).
    name: str

    #: One-sentence description shown in ``skyherd-demo list``.
    description: str

    #: How many sim-seconds to play back.
    duration_s: float = 600.0

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def setup(self, world: World) -> None:
        """Mutate the world state before the sim loop begins.

        Use this to stamp pre-conditions (e.g. sick cow, low tank).
        """

    @abstractmethod
    def inject_events(self, world: World, sim_time_s: float) -> list[dict[str, Any]]:
        """Return synthetic events to inject at *sim_time_s*.

        Called once per sim step.  Return an empty list when nothing should
        be injected at this time.
        """

    @abstractmethod
    def assert_outcome(
        self,
        event_stream: list[dict[str, Any]],
        mesh: Any,  # _DemoMesh at runtime; AgentMesh-compatible interface
    ) -> None:
        """Raise AssertionError if the expected outcome was not observed.

        Parameters
        ----------
        event_stream:
            All events emitted by the world + injected events, chronologically.
        mesh:
            The mesh after playback — inspect ``mesh._tool_call_log``.
        """

    # ------------------------------------------------------------------
    # Helpers available to subclasses
    # ------------------------------------------------------------------

    def _find_event(
        self,
        event_stream: list[dict[str, Any]],
        event_type: str,
    ) -> dict[str, Any] | None:
        """Return the first event of *event_type*, or None."""
        for ev in event_stream:
            if ev.get("type") == event_type:
                return ev
        return None

    def _find_tool_call(
        self,
        mesh: Any,  # _DemoMesh at runtime; AgentMesh in real usage
        tool_name: str,
    ) -> dict[str, Any] | None:
        """Return the first tool call named *tool_name* across all agents."""
        for calls in mesh._tool_call_log.values():
            for call in calls:
                if call.get("tool") == tool_name:
                    return call
        return None

    def _all_tool_calls(self, mesh: Any) -> list[dict[str, Any]]:
        """Flatten all tool calls from all agents into a single list."""
        result: list[dict[str, Any]] = []
        for calls in mesh._tool_call_log.values():
            result.extend(calls)
        return result


# ---------------------------------------------------------------------------
# Demo AgentMesh — simulation path only, no real API calls
# ---------------------------------------------------------------------------


class _DemoMesh:
    """Lightweight scenario driver that replays agent responses without API keys.

    Holds ONE SessionManager and FIVE persistent Session objects (one per agent)
    for the lifetime of a scenario run — mirrors the production AgentMesh pattern
    in src/skyherd/agents/mesh.py. Dispatching an event looks up the existing
    session by name and drives wake/handle/sleep through the shared manager.

    Public accessors (stable API for Phase 5 dashboard live-mode):
      - agent_sessions() -> dict[str, Session]
      - agent_tickers()  -> list[CostTicker]
    """

    def __init__(self, ledger: Ledger | None = None) -> None:
        self._tool_call_log: dict[str, list[dict[str, Any]]] = {}
        self._ledger = ledger

        # ONE SessionManager per scenario run (was 241 before this refactor).
        self._session_manager = SessionManager()

        # Eagerly create one session per agent, mirroring AgentMesh.start().
        # create_session is sync and ~microseconds — safe to call 5x in __init__.
        self._sessions: dict[str, Session] = {}
        self._handlers: dict[str, Any] = {}
        for spec, handler_fn in _SCENARIO_AGENT_REGISTRY:
            session = self._session_manager.create_session(spec)
            self._sessions[spec.name] = session
            self._handlers[spec.name] = handler_fn
            logger.debug(
                "_DemoMesh: registered %s (session %s)", spec.name, session.id[:8]
            )

    # ------------------------------------------------------------------
    # Public accessors — stable API consumed by Phase 5 dashboard live-mode.
    # DO NOT reach into self._sessions / self._session_manager from outside
    # this class; use these instead.
    # ------------------------------------------------------------------

    def agent_sessions(self) -> dict[str, Session]:
        """Return a shallow copy of the agent-name -> Session registry."""
        return dict(self._sessions)

    def agent_tickers(self) -> list:
        """Return the list of CostTicker objects for cost aggregation.

        Phase 5 (DASH-03 cost ticker live-mode) consumes this to avoid the
        deprecated ``_mesh._session_manager._tickers`` path that no longer
        exists on SessionManager.
        """
        return self._session_manager.all_tickers()

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(
        self,
        agent_name: str,
        wake_event: dict[str, Any],
        spec: Any,  # accepted for API compat with _route_event; unused after refactor
        handler_fn: Any,  # accepted for API compat; resolved via self._handlers
    ) -> list[dict[str, Any]]:
        """Wake the named agent's existing session, run its handler, sleep on exit.

        Reuses the session created at __init__ time — does NOT instantiate a fresh
        SessionManager (that was the 241-leak pre-fix). ``sleep()`` is guaranteed
        by ``finally:`` so the cost ticker idle-pauses even on handler exception.
        """
        session = self._sessions.get(agent_name)
        if session is None:
            logger.warning(
                "dispatch: unknown agent %r — not in scenario registry", agent_name
            )
            return []

        # Prefer the handler registered at __init__ (stable), fall back to the
        # handler_fn argument for callers still passing it explicitly.
        effective_handler = self._handlers.get(agent_name, handler_fn)

        self._session_manager.wake(session.id, wake_event)
        calls: list[dict[str, Any]] = []
        try:
            calls = await effective_handler(session, wake_event, sdk_client=None)
        except Exception as exc:  # noqa: BLE001
            logger.error("handler error for %s: %s", agent_name, exc)
            calls = []
        finally:
            # Idle-pause ticker — MUST fire even on exception (Pitfall 3).
            self._session_manager.sleep(session.id)

        if agent_name not in self._tool_call_log:
            self._tool_call_log[agent_name] = []
        self._tool_call_log[agent_name].extend(calls)

        if self._ledger is not None:
            for call in calls:
                self._ledger.append(
                    source=agent_name,
                    kind=f"tool_call.{call.get('tool', 'unknown')}",
                    payload=call,
                )
        return calls


# ---------------------------------------------------------------------------
# run() — top-level scenario runner
# ---------------------------------------------------------------------------


def _build_registry() -> dict[str, tuple[Any, Any]]:
    """Return a fresh (spec, handler) registry used by the event router."""
    return {
        "FenceLineDispatcher": (FENCELINE_DISPATCHER_SPEC, fenceline_handler),
        "HerdHealthWatcher": (HERD_HEALTH_WATCHER_SPEC, herd_handler),
        "PredatorPatternLearner": (PREDATOR_PATTERN_LEARNER_SPEC, predator_handler),
        "GrazingOptimizer": (GRAZING_OPTIMIZER_SPEC, grazing_handler),
        "CalvingWatch": (CALVING_WATCH_SPEC, calving_handler),
    }


async def _run_async_shared(
    scenario: Scenario,
    *,
    world: World,
    ledger: Ledger,
    mesh: _DemoMesh,
    seed: int = 42,
    speed: float = 15.0,
    assert_outcome: bool = False,
    dry_run: bool = False,
) -> ScenarioResult:
    """Run *scenario* against caller-provided ``world`` / ``ledger`` / ``mesh``.

    Never mints deps - callers own them. Used by the in-process ambient
    driver in ``src/skyherd/server/ambient.py`` so scenario activity lands
    in the live dashboard's mesh/world/ledger and feeds the SSE broadcaster
    naturally.

    Parameters
    ----------
    scenario:
        Instantiated scenario.
    world, ledger, mesh:
        Externally owned - this function neither creates nor closes them.
    seed:
        Recorded on the result; the world is expected to already be seeded.
    speed:
        Sim-to-wall ratio. ``speed > 0`` sleeps ``_STEP_DT / speed`` between
        steps; ``speed <= 0`` means no throttle (preserves the byte-identical
        fast path used by ``_run_async``).
    assert_outcome:
        When True, runs ``scenario.assert_outcome()`` after the loop. Ambient
        playback passes False - this is a heartbeat, not a test.
    dry_run:
        Skip the playback loop entirely (scenario setup still runs).
    """
    # Setup pre-conditions
    scenario.setup(world)

    all_events: list[dict[str, Any]] = []
    wall_start = time.monotonic()
    registry = _build_registry()
    throttle = speed > 0
    sleep_dt = _STEP_DT / speed if throttle else 0.0

    if not dry_run:
        elapsed = 0.0
        while elapsed < scenario.duration_s:
            step_events = world.step(_STEP_DT)
            elapsed += _STEP_DT

            # Record world events to ledger
            for ev in step_events:
                ledger.append(
                    source="world",
                    kind=ev.get("type", "unknown"),
                    payload=ev,
                )

            # Inject scenario-specific synthetic events
            injected = scenario.inject_events(world, elapsed)
            all_events.extend(step_events)
            all_events.extend(injected)

            # Route events to agents
            for ev in step_events + injected:
                await _route_event(ev, mesh, registry, ledger)

            if throttle:
                await asyncio.sleep(sleep_dt)

    wall_time_s = time.monotonic() - wall_start

    # Collect attestation entries
    attest_entries = [e.model_dump() for e in ledger.iter_events()]

    result = ScenarioResult(
        name=scenario.name,
        seed=seed,
        duration_s=scenario.duration_s,
        event_stream=all_events,
        agent_tool_calls=dict(mesh._tool_call_log),
        attestation_entries=attest_entries,
        wall_time_s=wall_time_s,
    )

    if dry_run:
        result.outcome_passed = True
    elif assert_outcome:
        try:
            scenario.assert_outcome(all_events, mesh)  # type: ignore[arg-type]
            result.outcome_passed = True
        except AssertionError as exc:
            result.outcome_error = str(exc)
            logger.warning("Scenario %r assertion failed: %s", scenario.name, exc)
    else:
        # Ambient / heartbeat mode - no verdict.
        result.outcome_passed = True

    return result


async def _run_async(
    scenario: Scenario,
    seed: int = 42,
    dry_run: bool = False,
    world_config: Path | None = None,
) -> ScenarioResult:
    """Async inner implementation of run().

    Thin wrapper around :func:`_run_async_shared`: mints a fresh world,
    ledger, and :class:`_DemoMesh` (preserving the byte-identical seed=42
    fast path), then delegates. Afterwards writes the JSONL replay log and
    appends to ``docs/REPLAY_LOG.md``.
    """
    import tempfile

    config_path = world_config or _WORLD_CONFIG
    world = make_world(seed=seed, config_path=config_path)

    # Build an in-memory ledger
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    signer = Signer.generate()
    ledger = Ledger.open(tmp.name, signer)

    mesh = _DemoMesh(ledger=ledger)

    result = await _run_async_shared(
        scenario,
        world=world,
        ledger=ledger,
        mesh=mesh,
        seed=seed,
        speed=0.0,  # byte-identical fast path - no sleep between steps
        assert_outcome=True,
        dry_run=dry_run,
    )

    # Write JSONL replay log
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S")
    jsonl_path = _RUNTIME_DIR / f"{scenario.name}_{seed}_{ts}.jsonl"
    _write_jsonl(jsonl_path, result)
    result.jsonl_path = jsonl_path

    # Append human-readable replay log
    _append_replay_log(result)

    ledger._conn.close()
    import os as _os

    try:
        _os.unlink(tmp.name)
    except OSError:
        logger.debug("tmp ledger file already gone (cleanup race â non-fatal): %s", tmp.name)

    return result


async def _route_event(
    event: dict[str, Any],
    mesh: _DemoMesh,
    registry: dict[str, tuple[Any, Any]],
    ledger: Ledger,
) -> None:
    """Route one world/injected event to the appropriate agents."""
    event_type = event.get("type", "")

    routing: dict[str, list[str]] = {
        "fence.breach": ["FenceLineDispatcher"],
        "predator.spawned": ["FenceLineDispatcher"],
        "camera.motion": ["HerdHealthWatcher"],
        "health.check": ["HerdHealthWatcher"],
        "collar.activity_spike": ["CalvingWatch"],
        "calving.prelabor": ["CalvingWatch"],
        "water.low": ["FenceLineDispatcher", "GrazingOptimizer"],
        "weather.storm": ["GrazingOptimizer"],
        "weekly.schedule": ["GrazingOptimizer"],
        "storm.warning": ["GrazingOptimizer"],
        # ROUT-02 — PredatorPatternLearner wake fan-out.
        # thermal.anomaly: rustling/predator-thermal clip → dispatcher + learner.
        # nightly.analysis: cron-style daily analysis → learner only.
        "thermal.anomaly": ["FenceLineDispatcher", "PredatorPatternLearner"],
        "nightly.analysis": ["PredatorPatternLearner"],
    }

    targets = routing.get(event_type, [])
    for agent_name in targets:
        if agent_name in registry:
            spec, handler_fn = registry[agent_name]
            try:
                await mesh.dispatch(agent_name, event, spec, handler_fn)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Handler error for %s: %s", agent_name, exc)


def _write_jsonl(path: Path, result: ScenarioResult) -> None:
    """Write the scenario result as JSONL."""
    with path.open("w", encoding="utf-8") as fh:
        # Header record
        fh.write(
            json.dumps(
                {
                    "record": "scenario_header",
                    "name": result.name,
                    "seed": result.seed,
                    "duration_s": result.duration_s,
                    "outcome_passed": result.outcome_passed,
                    "outcome_error": result.outcome_error,
                    "wall_time_s": result.wall_time_s,
                    "event_count": len(result.event_stream),
                    "tool_call_count": sum(len(v) for v in result.agent_tool_calls.values()),
                    "attestation_count": len(result.attestation_entries),
                }
            )
            + "\n"
        )
        # Events
        for ev in result.event_stream:
            fh.write(json.dumps({"record": "event", **ev}) + "\n")
        # Tool calls
        for agent_name, calls in result.agent_tool_calls.items():
            for call in calls:
                fh.write(json.dumps({"record": "tool_call", "agent": agent_name, **call}) + "\n")


def _append_replay_log(result: ScenarioResult) -> None:
    """Append a human-readable entry to docs/REPLAY_LOG.md."""
    _DOCS_DIR.mkdir(parents=True, exist_ok=True)
    replay_log = _DOCS_DIR / "REPLAY_LOG.md"
    ts = datetime.now(tz=UTC).isoformat()
    status = "PASS" if result.outcome_passed else f"FAIL: {result.outcome_error}"
    tool_count = sum(len(v) for v in result.agent_tool_calls.items())
    line = (
        f"| {ts} | {result.name} | seed={result.seed} | "
        f"events={len(result.event_stream)} | tools={tool_count} | "
        f"attest={len(result.attestation_entries)} | {status} |\n"
    )
    if not replay_log.exists():
        replay_log.write_text(
            "# SkyHerd Demo Replay Log\n\n"
            "| timestamp | scenario | params | events | tools | attest | status |\n"
            "|-----------|----------|--------|--------|-------|--------|--------|\n"
        )
    with replay_log.open("a", encoding="utf-8") as fh:
        fh.write(line)


def run(
    scenario_name: str,
    seed: int = 42,
    dry_run: bool = False,
) -> ScenarioResult:
    """Bootstrap world + sensors + mesh and play one named scenario.

    Parameters
    ----------
    scenario_name:
        Key in SCENARIOS dict (e.g. "coyote", "sick_cow").
    seed:
        RNG seed for deterministic replay.
    dry_run:
        If True, sets up the world and returns without running the sim loop.

    Returns
    -------
    ScenarioResult
        Full replay including event stream, tool calls, attestation entries.
    """
    from skyherd.scenarios import SCENARIOS

    if scenario_name not in SCENARIOS:
        raise KeyError(f"Unknown scenario: {scenario_name!r}. Available: {list(SCENARIOS)}")

    scenario_cls = SCENARIOS[scenario_name]
    scenario = scenario_cls()

    return asyncio.run(_run_async(scenario, seed=seed, dry_run=dry_run))


def run_all(seed: int = 42) -> list[ScenarioResult]:
    """Run all 5 demo scenarios sequentially with the given seed.

    Parameters
    ----------
    seed:
        Common RNG seed applied to every scenario.

    Returns
    -------
    list[ScenarioResult]
        One result per scenario, in canonical order.
    """
    from skyherd.scenarios import SCENARIOS

    results: list[ScenarioResult] = []
    for name in SCENARIOS:
        logger.info("Running scenario: %s (seed=%d)", name, seed)
        result = run(name, seed=seed)
        results.append(result)
        status = "PASS" if result.outcome_passed else f"FAIL({result.outcome_error})"
        logger.info("  %s -> %s (%.2fs wall)", name, status, result.wall_time_s)
    return results
