"""Cross-Ranch Mesh — neighbor broadcaster, listener, and multi-mesh orchestrator.

Architecture
------------
* ``NeighborBroadcaster`` — subscribes to FenceLineDispatcher decision logs for the
  local ranch.  When a decision contains "coyote confirmed near shared fence", it
  publishes a compact neighbor-alert to the inter-ranch topic namespace.

* ``NeighborListener`` — per-mesh plugin.  Subscribes to incoming neighbor alerts
  addressed to this ranch and routes them onto FenceLineDispatcher's wake bus
  as ``neighbor_alert`` events.  Includes dedup (same fence+ranch within TTL)
  and a timeout to expire stale alerts.

* ``CrossRanchMesh`` — multi-mesh orchestrator.  Holds N ``AgentMesh`` instances
  (one per ranch), wires a shared ``NeighborBroadcaster`` across all of them,
  and creates a ``NeighborListener`` per mesh.

Topic schema
------------
Broadcast:   skyherd/neighbor/<from_ranch>/<to_ranch>/<event_kind>
Subscribe:   skyherd/neighbor/+/<this_ranch>/#

Event payload::

    {
        "from_ranch": "ranch_a",
        "to_ranch":   "ranch_b",
        "event_kind": "predator_confirmed",
        "species":    "coyote",
        "confidence": 0.91,
        "shared_fence": "fence_east",
        "ts": 1745200000.0,
        "attestation_hash": "sha256:abcdef…",
    }
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import deque
from typing import Any

from skyherd.agents.mesh import AgentMesh
from skyherd.agents.session import SessionManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Seconds before a previously seen (ranch, fence) dedup key expires
_DEDUP_TTL_S: float = 120.0

# Topic prefix for cross-ranch events
_NEIGHBOR_PREFIX = "skyherd/neighbor"


def _attestation_hash(payload: dict[str, Any]) -> str:
    """Deterministic SHA-256 fingerprint of the event payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# NeighborBroadcaster
# ---------------------------------------------------------------------------


class NeighborBroadcaster:
    """Monitors local FenceLineDispatcher decisions and publishes neighbor alerts.

    Sits between the local mesh's decision log and the inter-ranch MQTT topic.
    Only fires when a decision mentions a shared fence segment.

    Parameters
    ----------
    from_ranch:
        ID of the ranch being monitored (e.g. "ranch_a").
    shared_fence_ids:
        Set of local fence IDs that are shared boundaries.  Events on
        non-shared fences are silently ignored.
    neighbor_map:
        Mapping from shared fence ID → neighbor ranch ID (e.g.
        ``{"fence_east": "ranch_b"}``).
    publish_callback:
        Async callable ``(topic: str, payload: dict) → None``.  Injected so
        tests can intercept without a real MQTT broker.
    """

    def __init__(
        self,
        from_ranch: str,
        shared_fence_ids: set[str],
        neighbor_map: dict[str, str],
        publish_callback: Any | None = None,
    ) -> None:
        self._from_ranch = from_ranch
        self._shared_fence_ids = shared_fence_ids
        self._neighbor_map = neighbor_map  # fence_id → to_ranch
        self._publish = publish_callback
        self._published_count: int = 0
        # CRM-04: ring buffer of recent outbound events for /api/neighbors feed.
        self._recent: deque[dict[str, Any]] = deque(maxlen=100)

    @property
    def recent_events(self) -> list[dict[str, Any]]:
        """Return recent outbound neighbor alerts (oldest first)."""
        return list(self._recent)

    async def on_fenceline_decision(
        self,
        decision: dict[str, Any],
    ) -> bool:
        """Process one FenceLineDispatcher decision.

        Returns True if a neighbor alert was broadcast, False otherwise.

        Parameters
        ----------
        decision:
            A dict that includes at minimum ``fence_id`` (or ``segment``) and
            ``species`` / ``confidence`` fields as produced by the
            FenceLineDispatcher simulation path.
        """
        fence_id: str = decision.get("fence_id") or decision.get("segment", "")

        # Only propagate events on shared fence segments
        if fence_id not in self._shared_fence_ids:
            logger.debug(
                "NeighborBroadcaster[%s]: fence %r not shared — skip",
                self._from_ranch,
                fence_id,
            )
            return False

        to_ranch = self._neighbor_map.get(fence_id)
        if to_ranch is None:
            logger.warning(
                "NeighborBroadcaster[%s]: no neighbor mapping for fence %r",
                self._from_ranch,
                fence_id,
            )
            return False

        species = decision.get("species", "unknown")
        confidence = float(decision.get("confidence", 0.85))
        ts = float(decision.get("ts", time.time()))

        base_payload: dict[str, Any] = {
            "from_ranch": self._from_ranch,
            "to_ranch": to_ranch,
            "event_kind": "predator_confirmed",
            "species": species,
            "confidence": confidence,
            "shared_fence": fence_id,
            "ts": ts,
        }
        base_payload["attestation_hash"] = _attestation_hash(base_payload)

        topic = f"{_NEIGHBOR_PREFIX}/{self._from_ranch}/{to_ranch}/predator_confirmed"

        if self._publish is not None:
            await self._publish(topic, base_payload)
        else:
            logger.info(
                "NeighborBroadcaster[%s → %s] published %s on %s (no broker)",
                self._from_ranch,
                to_ranch,
                species,
                topic,
            )

        self._published_count += 1
        # CRM-04: record outbound event for /api/neighbors feed.
        self._recent.append({
            "direction": "outbound",
            "from_ranch": self._from_ranch,
            "to_ranch": to_ranch,
            "species": species,
            "confidence": confidence,
            "shared_fence": fence_id,
            "ts": ts,
            "attestation_hash": base_payload["attestation_hash"],
        })
        logger.info(
            "NeighborBroadcaster[%s → %s]: broadcast predator_confirmed (fence=%s, species=%s, "
            "confidence=%.2f)",
            self._from_ranch,
            to_ranch,
            fence_id,
            species,
            confidence,
        )
        return True


# ---------------------------------------------------------------------------
# NeighborListener
# ---------------------------------------------------------------------------


class NeighborListener:
    """Per-mesh plugin: routes incoming neighbor alerts to FenceLineDispatcher.

    Deduplicates alerts: the same (from_ranch, shared_fence) pair is suppressed
    for ``_DEDUP_TTL_S`` seconds to prevent storm-mode cascades.

    Parameters
    ----------
    this_ranch:
        ID of the ranch this listener belongs to (e.g. "ranch_b").
    session_manager:
        The ``SessionManager`` for this mesh.  Used to wake the
        FenceLineDispatcher session with a synthetic ``neighbor_alert`` event.
    fenceline_session_id:
        Session ID of the FenceLineDispatcher in this mesh.
    wake_bus:
        Optional async queue to push wake events onto (injected by
        ``CrossRanchMesh``; if None, uses ``session_manager.wake()`` directly).
    """

    def __init__(
        self,
        this_ranch: str,
        session_manager: SessionManager,
        fenceline_session_id: str,
        wake_bus: asyncio.Queue[dict[str, Any]] | None = None,
    ) -> None:
        self._this_ranch = this_ranch
        self._session_manager = session_manager
        self._fenceline_session_id = fenceline_session_id
        self._wake_bus = wake_bus

        # Dedup: (from_ranch, shared_fence) → last_seen_ts
        self._dedup: dict[tuple[str, str], float] = {}
        self._received_count: int = 0
        self._deduped_count: int = 0
        # CRM-04: ring buffer of recent inbound events for /api/neighbors feed.
        self._recent: deque[dict[str, Any]] = deque(maxlen=100)

    @property
    def recent_events(self) -> list[dict[str, Any]]:
        """Return recent inbound neighbor alerts (oldest first)."""
        return list(self._recent)

    def _is_duplicate(self, from_ranch: str, shared_fence: str) -> bool:
        """Return True if this alert was recently seen and should be suppressed."""
        key = (from_ranch, shared_fence)
        now = time.time()
        last = self._dedup.get(key)
        if last is not None and (now - last) < _DEDUP_TTL_S:
            return True
        self._dedup[key] = now
        return False

    def _expire_dedup(self) -> None:
        """Remove expired dedup entries to prevent memory growth."""
        now = time.time()
        expired = [k for k, t in self._dedup.items() if (now - t) >= _DEDUP_TTL_S]
        for k in expired:
            del self._dedup[k]

    async def on_neighbor_event(self, topic: str, payload: dict[str, Any]) -> bool:
        """Handle one incoming neighbor alert.

        Returns True if the alert was forwarded to FenceLineDispatcher,
        False if it was deduped or malformed.

        Parameters
        ----------
        topic:
            MQTT topic of the incoming message.
        payload:
            Parsed JSON payload (the NeighborBroadcaster event dict).
        """
        self._expire_dedup()
        self._received_count += 1

        from_ranch = payload.get("from_ranch", "unknown")
        shared_fence = payload.get("shared_fence", "unknown")
        species = payload.get("species", "unknown")
        confidence = float(payload.get("confidence", 0.0))
        ts = float(payload.get("ts", time.time()))
        attestation_hash = payload.get("attestation_hash", "")

        # Validate this alert is addressed to us
        to_ranch = payload.get("to_ranch", "")
        if to_ranch and to_ranch != self._this_ranch:
            logger.debug(
                "NeighborListener[%s]: alert addressed to %r — ignore",
                self._this_ranch,
                to_ranch,
            )
            return False

        if self._is_duplicate(from_ranch, shared_fence):
            self._deduped_count += 1
            logger.debug(
                "NeighborListener[%s]: deduped alert from %s fence=%s",
                self._this_ranch,
                from_ranch,
                shared_fence,
            )
            return False

        # CRM-04: record inbound event for /api/neighbors feed (after dedup).
        self._recent.append({
            "direction": "inbound",
            "from_ranch": from_ranch,
            "to_ranch": self._this_ranch,
            "species": species,
            "confidence": confidence,
            "shared_fence": shared_fence,
            "ts": ts,
            "attestation_hash": attestation_hash,
        })

        # Build a synthetic neighbor_alert wake event for FenceLineDispatcher
        wake_event: dict[str, Any] = {
            "type": "neighbor_alert",
            "topic": f"{_NEIGHBOR_PREFIX}/{from_ranch}/{self._this_ranch}/predator_confirmed",
            "ranch_id": self._this_ranch,
            "from_ranch": from_ranch,
            "species": species,
            "confidence": confidence,
            "shared_fence": shared_fence,
            "ts": ts,
            "attestation_hash": attestation_hash,
            # Response mode hint for FenceLineDispatcher
            "response_mode": "pre_position",
        }

        if self._wake_bus is not None:
            await self._wake_bus.put(wake_event)
        else:
            try:
                self._session_manager.wake(self._fenceline_session_id, wake_event)
            except KeyError:
                logger.warning(
                    "NeighborListener[%s]: FenceLineDispatcher session %s not found",
                    self._this_ranch,
                    self._fenceline_session_id[:8],
                )
                return False

        logger.info(
            "NeighborListener[%s]: forwarded neighbor_alert (from=%s, fence=%s, species=%s)",
            self._this_ranch,
            from_ranch,
            shared_fence,
            species,
        )
        return True


# ---------------------------------------------------------------------------
# CrossRanchMesh
# ---------------------------------------------------------------------------


class CrossRanchMesh:
    """Multi-mesh orchestrator for cross-ranch agent coordination.

    Holds one ``AgentMesh`` per ranch, wires a ``NeighborBroadcaster`` for
    each mesh to publish shared-fence events, and a ``NeighborListener`` per
    mesh to receive and route them to FenceLineDispatcher.

    Typical usage (simulation / test)::

        mesh_a = AgentMesh(ranch_id="ranch_a")
        mesh_b = AgentMesh(ranch_id="ranch_b")
        cross = CrossRanchMesh(
            meshes={"ranch_a": mesh_a, "ranch_b": mesh_b},
            neighbor_config={
                "ranch_a": {"fence_east": "ranch_b"},
                "ranch_b": {"fence_west": "ranch_a"},
            },
        )
        await cross.start()
        ...
        await cross.stop()

    The ``simulate_coyote_at_shared_fence`` coroutine drives the canonical
    judge demo without a real MQTT broker or API key.
    """

    def __init__(
        self,
        meshes: dict[str, AgentMesh],
        neighbor_config: dict[str, dict[str, str]],
    ) -> None:
        """
        Parameters
        ----------
        meshes:
            Mapping from ranch_id → AgentMesh.
        neighbor_config:
            ``{ranch_id: {fence_id: to_ranch_id}}`` — which local fences are
            shared boundaries and who they connect to.
        """
        self._meshes = meshes
        self._neighbor_config = neighbor_config

        # Wake queues: one per ranch for neighbor-triggered wake events
        self._wake_queues: dict[str, asyncio.Queue[dict[str, Any]]] = {
            rid: asyncio.Queue() for rid in meshes
        }

        # Per-ranch broadcasters
        self._broadcasters: dict[str, NeighborBroadcaster] = {}

        # Per-ranch listeners
        self._listeners: dict[str, NeighborListener] = {}

        # Shared in-memory event bus: (topic, payload) tuples
        self._event_bus: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()

        # Background tasks
        self._tasks: list[asyncio.Task[None]] = []

        # Tool-call log (keyed by ranch_id) — used by assert_outcome
        self._tool_call_log: dict[str, list[dict[str, Any]]] = {rid: [] for rid in meshes}

        self._session_managers: dict[str, SessionManager] = {}
        self._fenceline_session_ids: dict[str, str] = {}

    async def start(self) -> None:
        """Start all meshes and wire broadcasters + listeners."""
        from skyherd.agents.fenceline_dispatcher import FENCELINE_DISPATCHER_SPEC

        for ranch_id, _mesh in self._meshes.items():
            # Each ranch gets its own SessionManager for scenario routing
            sm = SessionManager()
            self._session_managers[ranch_id] = sm

            # Create a FenceLineDispatcher session for this ranch
            session = sm.create_session(FENCELINE_DISPATCHER_SPEC)
            self._fenceline_session_ids[ranch_id] = session.id

            # Broadcaster: fires when local FenceLineDispatcher confirms near shared fence
            fence_neighbor_map = self._neighbor_config.get(ranch_id, {})
            shared_fence_ids = set(fence_neighbor_map.keys())

            broadcaster = NeighborBroadcaster(
                from_ranch=ranch_id,
                shared_fence_ids=shared_fence_ids,
                neighbor_map=fence_neighbor_map,
                publish_callback=self._publish_to_bus,
            )
            self._broadcasters[ranch_id] = broadcaster

            # Listener: receives neighbor events, pushes onto wake queue
            listener = NeighborListener(
                this_ranch=ranch_id,
                session_manager=sm,
                fenceline_session_id=session.id,
                wake_bus=self._wake_queues[ranch_id],
            )
            self._listeners[ranch_id] = listener

        # Start the inter-ranch event router
        router_task = asyncio.create_task(self._event_router_loop(), name="cross-ranch-router")
        self._tasks.append(router_task)

        logger.info(
            "CrossRanchMesh started — %d ranches wired: %s",
            len(self._meshes),
            list(self._meshes),
        )

    async def stop(self) -> None:
        """Cancel background tasks and stop all meshes."""
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        logger.info("CrossRanchMesh stopped.")

    async def _publish_to_bus(self, topic: str, payload: dict[str, Any]) -> None:
        """Internal publish: enqueue onto the shared in-memory event bus."""
        await self._event_bus.put((topic, payload))
        logger.debug("CrossRanchMesh bus: enqueued %s", topic)

    def recent_events(self) -> list[dict[str, Any]]:
        """Phase 02 CRM-04: combined in/out neighbor log for /api/neighbors.

        Returns up to 100 most-recent events across all broadcasters + listeners,
        sorted by ts descending. Safe for sync-callers (no asyncio required).
        """
        out: list[dict[str, Any]] = []
        for b in self._broadcasters.values():
            out.extend(b.recent_events)
        for listener in self._listeners.values():
            out.extend(listener.recent_events)
        out.sort(key=lambda e: float(e.get("ts", 0.0)), reverse=True)
        return out[:100]

    async def _event_router_loop(self) -> None:
        """Route events from the shared bus to the correct NeighborListener."""
        while True:
            topic, payload = await self._event_bus.get()
            to_ranch = payload.get("to_ranch", "")
            listener = self._listeners.get(to_ranch)
            if listener is not None:
                await listener.on_neighbor_event(topic, payload)
            else:
                logger.warning("CrossRanchMesh: no listener for to_ranch=%r", to_ranch)

    # ------------------------------------------------------------------
    # Simulation / demo helpers
    # ------------------------------------------------------------------

    async def simulate_coyote_at_shared_fence(
        self,
        from_ranch: str,
        shared_fence_id: str,
        species: str = "coyote",
        confidence: float = 0.91,
    ) -> dict[str, Any]:
        """Drive the canonical cross-ranch coyote demo without API keys.

        1. Simulates ranch_a FenceLineDispatcher confirming coyote at shared fence.
        2. NeighborBroadcaster fires → event bus → NeighborListener routes to
           ranch_b FenceLineDispatcher as neighbor_alert.
        3. ranch_b FenceLineDispatcher runs ``_simulate_handler`` in pre_position mode.
        4. Returns a summary dict with tool calls from both ranches.
        """
        from skyherd.agents.fenceline_dispatcher import (
            _simulate_handler,
        )

        result: dict[str, Any] = {
            "from_ranch": from_ranch,
            "shared_fence": shared_fence_id,
            "species": species,
            "confidence": confidence,
            "ranch_a_tool_calls": [],
            "ranch_b_tool_calls": [],
            "neighbor_broadcast": False,
            "ranch_b_woken": False,
            "ranch_b_pre_positioned": False,
            "attestation_hashes": [],
        }

        # --- Step 1: ranch_a FenceLineDispatcher fires on breach ---
        breach_event: dict[str, Any] = {
            "type": "fence.breach",
            "ranch_id": from_ranch,
            "fence_id": shared_fence_id,
            "segment": shared_fence_id,
            "species_hint": species,
            "lat": 34.123,
            "lon": -106.456,
            "sim_time_s": 462.0,
            "topic": f"skyherd/{from_ranch}/fence/{shared_fence_id}",
        }

        sm_a = self._session_managers.get(from_ranch)
        fid_a = self._fenceline_session_ids.get(from_ranch)
        if sm_a is None or fid_a is None:
            raise RuntimeError(f"Ranch {from_ranch!r} not started — call start() first")

        sm_a.wake(fid_a, breach_event)
        session_a = sm_a.get_session(fid_a)
        a_calls = _simulate_handler(breach_event, session_a)
        sm_a.sleep(fid_a)
        self._tool_call_log[from_ranch].extend(a_calls)
        result["ranch_a_tool_calls"] = a_calls

        # Log to attestation (simulated)
        attest_entry = {
            "ranch": from_ranch,
            "fence": shared_fence_id,
            "tool_calls": [c["tool"] for c in a_calls],
        }
        result["attestation_hashes"].append(_attestation_hash(attest_entry))

        # --- Step 2: NeighborBroadcaster decides whether to broadcast ---
        broadcaster = self._broadcasters.get(from_ranch)
        if broadcaster is None:
            raise RuntimeError(f"No broadcaster for ranch {from_ranch!r}")

        decision: dict[str, Any] = {
            "fence_id": shared_fence_id,
            "species": species,
            "confidence": confidence,
            "ts": 1745200000.0,
        }
        broadcast_fired = await broadcaster.on_fenceline_decision(decision)
        result["neighbor_broadcast"] = broadcast_fired

        if not broadcast_fired:
            return result

        # --- Step 3: route bus event to listener (give event_router a tick) ---
        await asyncio.sleep(0)  # yield to event_router_loop
        await asyncio.sleep(0)  # second yield ensures listener coroutine runs

        # --- Step 4: drain wake queue for destination ranch ---
        to_ranch_id = self._neighbor_config[from_ranch].get(shared_fence_id, "")
        wake_queue = self._wake_queues.get(to_ranch_id)
        listener = self._listeners.get(to_ranch_id)

        if wake_queue is None or listener is None:
            logger.warning("CrossRanchMesh: no listener/queue for %s", to_ranch_id)
            return result

        # Process all queued wake events for destination ranch
        while not wake_queue.empty():
            neighbor_wake = wake_queue.get_nowait()
            result["ranch_b_woken"] = True

            sm_b = self._session_managers.get(to_ranch_id)
            fid_b = self._fenceline_session_ids.get(to_ranch_id)
            if sm_b is None or fid_b is None:
                continue

            sm_b.wake(fid_b, neighbor_wake)
            session_b = sm_b.get_session(fid_b)

            # Pre-position mode: use neighbour-alert simulation path
            b_calls = _simulate_neighbor_handler(neighbor_wake, session_b)
            sm_b.sleep(fid_b)
            self._tool_call_log[to_ranch_id].extend(b_calls)
            result["ranch_b_tool_calls"].extend(b_calls)

            # Check that no duplicate rancher page was raised (silent handoff)
            rancher_pages = [c for c in b_calls if c.get("tool") == "page_rancher"]
            result["ranch_b_pre_positioned"] = any(c.get("tool") == "launch_drone" for c in b_calls)

            # Log attestation for ranch_b
            attest_b = {
                "ranch": to_ranch_id,
                "fence": neighbor_wake.get("shared_fence", shared_fence_id),
                "tool_calls": [c["tool"] for c in b_calls],
                "triggered_by": from_ranch,
            }
            result["attestation_hashes"].append(_attestation_hash(attest_b))

            # Agent log entry for dashboard
            log_entry: dict[str, Any] = {
                "type": "neighbor_handoff",
                "ranch_id": to_ranch_id,
                "from_ranch": from_ranch,
                "species": species,
                "response_mode": "pre_position",
                "tool_calls": [c["tool"] for c in b_calls],
                "rancher_paged": bool(rancher_pages),
                "ts": time.time(),
            }
            logger.info(
                "CrossRanchMesh neighbor_handoff: %s → %s | tools=%s | rancher_paged=%s",
                from_ranch,
                to_ranch_id,
                [c["tool"] for c in b_calls],
                bool(rancher_pages),
            )
            result["neighbor_handoff_log"] = log_entry

        return result


# ---------------------------------------------------------------------------
# Pre-position simulation handler (neighbor alert path)
# ---------------------------------------------------------------------------


def _simulate_neighbor_handler(
    wake_event: dict[str, Any],
    session: Any,
) -> list[dict[str, Any]]:
    """Deterministic simulation for FenceLineDispatcher responding to a neighbor_alert.

    response_mode == "pre_position":
    * Proposes a patrol for the shared fence.
    * Does NOT call page_rancher (silent handoff — only page if threat cascades).
    * Emits a neighbor_handoff log entry instead.

    This is the "B ranch hears the alarm before the coyote arrives" money shot.
    """
    shared_fence = wake_event.get("shared_fence", "fence_west")
    ranch_id = wake_event.get("ranch_id", "ranch_b")
    from_ranch = wake_event.get("from_ranch", "ranch_a")
    species = wake_event.get("species", "coyote")
    confidence = float(wake_event.get("confidence", 0.85))

    # Pre-position patrol at the shared fence midpoint
    # ranch_b's west fence runs from (0,0) to (0,1500) — mid is (0, 750)
    patrol_lat = 34.123
    patrol_lon = -106.456

    calls: list[dict[str, Any]] = [
        {
            "tool": "get_thermal_clip",
            "input": {"segment": shared_fence, "ranch_id": ranch_id},
        },
        {
            "tool": "launch_drone",
            "input": {
                "mission": "neighbor_pre_position_patrol",
                "target_lat": patrol_lat,
                "target_lon": patrol_lon,
                "alt_m": 60.0,
                "note": (
                    f"Neighbor alert from {from_ranch}: {species} confirmed near "
                    f"{shared_fence} (confidence={confidence:.0%}). "
                    "Pre-positioning patrol. No direct observation yet."
                ),
            },
        },
        {
            # Log entry for dashboard — NOT a page_rancher call (silent handoff)
            "tool": "log_agent_event",
            "input": {
                "event_type": "neighbor_handoff",
                "ranch_id": ranch_id,
                "from_ranch": from_ranch,
                "species": species,
                "confidence": confidence,
                "shared_fence": shared_fence,
                "response_mode": "pre_position",
                "message": (
                    f"Neighbor ranch {from_ranch} confirmed {species} near shared fence "
                    f"{shared_fence}. Pre-positioning patrol drone. Rancher NOT paged "
                    "(leading indicator — awaiting direct observation)."
                ),
            },
        },
    ]

    logger.info(
        "_simulate_neighbor_handler[%s]: pre_position patrol → %s "
        "(triggered by %s, species=%s, confidence=%.2f)",
        ranch_id,
        shared_fence,
        from_ranch,
        species,
        confidence,
    )
    return calls
