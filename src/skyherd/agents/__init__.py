"""SkyHerd agent mesh — public API surface.

Exports the complete set of symbols needed to start the mesh, inspect sessions,
and work with individual agent specs from outside the package.
"""

from skyherd.agents.calving_watch import CALVING_WATCH_SPEC
from skyherd.agents.calving_watch import handler as calving_handler
from skyherd.agents.cost import CostTicker, TickPayload, run_tick_loop
from skyherd.agents.fenceline_dispatcher import (
    FENCELINE_DISPATCHER_SPEC,
)
from skyherd.agents.fenceline_dispatcher import (
    handler as fenceline_handler,
)
from skyherd.agents.grazing_optimizer import (
    GRAZING_OPTIMIZER_SPEC,
)
from skyherd.agents.grazing_optimizer import (
    handler as grazing_handler,
)
from skyherd.agents.herd_health_watcher import (
    HERD_HEALTH_WATCHER_SPEC,
)
from skyherd.agents.herd_health_watcher import (
    handler as herd_handler,
)
from skyherd.agents.mesh import AgentMesh
from skyherd.agents.predator_pattern_learner import (
    PREDATOR_PATTERN_LEARNER_SPEC,
)
from skyherd.agents.predator_pattern_learner import (
    handler as predator_handler,
)
from skyherd.agents.session import Session, SessionManager, build_cached_messages
from skyherd.agents.spec import AgentSpec

__all__ = [
    # Mesh orchestrator
    "AgentMesh",
    # Session primitives
    "Session",
    "SessionManager",
    "build_cached_messages",
    # Agent spec
    "AgentSpec",
    # Cost tracking
    "CostTicker",
    "TickPayload",
    "run_tick_loop",
    # Agent specs (for external inspection / registration)
    "FENCELINE_DISPATCHER_SPEC",
    "HERD_HEALTH_WATCHER_SPEC",
    "PREDATOR_PATTERN_LEARNER_SPEC",
    "GRAZING_OPTIMIZER_SPEC",
    "CALVING_WATCH_SPEC",
    # Handler factories
    "fenceline_handler",
    "herd_handler",
    "predator_handler",
    "grazing_handler",
    "calving_handler",
]
