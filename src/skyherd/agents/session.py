"""SessionManager — Managed Agents-compat runtime shim for SkyHerd.

This module emulates the Managed Agents API primitives locally so the demo
runs today without real MA beta access.  When beta access lands the shim is
swappable for the real ``client.beta.sessions.*`` calls.

Key design decisions
--------------------
* ``Session`` is a dataclass that models Managed Agents session state.
* ``state`` is ``"active" | "idle" | "checkpointed"``.
* The cost meter (CostTicker) ticks only while state == "active".
* ``sleep()`` transitions to ``idle`` and halts the token meter — this is the
  "$0 while idle" Managed Agents money shot.
* ``wake()`` transitions to ``active``, appends the wake event, and ensures
  the system prompt cache_control blocks are ready.
* ``checkpoint()`` serialises to ``runtime/sessions/{session_id}.json``.
* ``on_webhook()`` routes an MQTT-originated event to the correct session by
  matching ``agent_spec.wake_topics`` against the event topic.

Prompt caching
--------------
System prompt + loaded skills are sent as ``cache_control: {"type": "ephemeral"}``
blocks (see ``build_cached_messages``).  This drives cache_hit_tokens up on every
subsequent wake cycle, slashing per-wake cost.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from skyherd.agents.cost import CostTicker
from skyherd.agents.spec import AgentSpec

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_RUNTIME_DIR = Path("runtime/sessions")

SessionState = Literal["active", "idle", "checkpointed"]


# ---------------------------------------------------------------------------
# Session dataclass
# ---------------------------------------------------------------------------


@dataclass
class Session:
    """Runtime state for one SkyHerd agent session.

    Attributes map 1:1 to Managed Agents session primitives so this can
    later be replaced by ``client.beta.sessions.retrieve()``.
    """

    id: str
    agent_name: str
    agent_spec: AgentSpec
    state: SessionState = "idle"
    last_active_ts: float = field(default_factory=time.time)
    wake_events_consumed: list[dict[str, Any]] = field(default_factory=list)
    checkpoint_path: str | None = None
    system_prompt_cached_hash: str | None = None

    # Token / cost accounting
    cumulative_tokens_in: int = 0
    cumulative_tokens_out: int = 0
    cumulative_cost_usd: float = 0.0
    run_time_active_s: float = 0.0  # ticks up only when state == "active"
    run_time_idle_s: float = 0.0

    # Internal timing — not serialised in the public repr
    _active_start_ts: float = field(default=0.0, repr=False)

    # CostTicker is wired by SessionManager; not serialised
    _ticker: CostTicker | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable snapshot (excludes internal fields)."""
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "state": self.state,
            "last_active_ts": self.last_active_ts,
            "wake_events_consumed": self.wake_events_consumed,
            "checkpoint_path": self.checkpoint_path,
            "system_prompt_cached_hash": self.system_prompt_cached_hash,
            "cumulative_tokens_in": self.cumulative_tokens_in,
            "cumulative_tokens_out": self.cumulative_tokens_out,
            "cumulative_cost_usd": self.cumulative_cost_usd,
            "run_time_active_s": self.run_time_active_s,
            "run_time_idle_s": self.run_time_idle_s,
        }


# ---------------------------------------------------------------------------
# Prompt-cache helpers
# ---------------------------------------------------------------------------


def build_cached_messages(
    system_prompt: str,
    skill_contents: list[str],
    user_content: str,
) -> dict[str, Any]:
    """Build a ``messages.create``-compatible dict with cache_control blocks.

    The system prompt and each skill file are wrapped with
    ``cache_control: {"type": "ephemeral"}`` so they land in the prompt cache.
    The volatile user content (the wake event) is NOT cached.

    Returns a dict with keys ``system`` and ``messages`` ready to be unpacked
    into ``client.messages.create(**payload)``.
    """
    # System block with cache_control (stable content first)
    system_blocks: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    # Each skill is appended as an additional cache_control block
    for skill_text in skill_contents:
        if skill_text.strip():
            system_blocks.append(
                {
                    "type": "text",
                    "text": skill_text,
                    "cache_control": {"type": "ephemeral"},
                }
            )

    # Volatile wake event as the user message (not cached)
    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": user_content}],
        }
    ]

    return {"system": system_blocks, "messages": messages}


def _load_text(path: str) -> str:
    """Load a text file; return empty string if missing."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        logger.warning("skill/prompt file not found: %s", path)
        return ""


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------


class SessionManager:
    """Manages the lifecycle of SkyHerd agent sessions.

    Emulates Managed Agents server-side semantics locally:
    * Sessions default to ``idle`` on creation.
    * ``sleep()`` transitions to ``idle``; cost meter pauses.
    * ``wake()`` transitions to ``active``; cost meter resumes.
    * ``checkpoint()`` writes JSON to disk.
    * ``restore_from_checkpoint()`` rehydrates from disk.
    * ``on_webhook()`` routes MQTT events to matching sessions.
    """

    def __init__(
        self,
        mqtt_publish_callback: Any | None = None,
        ledger_callback: Any | None = None,
    ) -> None:
        self._sessions: dict[str, Session] = {}
        self._mqtt_publish = mqtt_publish_callback
        self._ledger = ledger_callback
        _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self, agent_spec: AgentSpec) -> Session:
        """Create a new idle session for the given agent spec."""
        session_id = str(uuid.uuid4())
        ticker = CostTicker(
            session_id=session_id,
            ledger_callback=self._ledger,
            mqtt_publish_callback=self._mqtt_publish,
        )
        session = Session(
            id=session_id,
            agent_name=agent_spec.name,
            agent_spec=agent_spec,
            state="idle",
            _ticker=ticker,
        )
        self._sessions[session_id] = session
        logger.info("session created: %s (%s)", session_id[:8], agent_spec.name)
        return session

    def sleep(self, session_id: str) -> Session:
        """Transition session to ``idle``; halts token/cost meter.

        This is the Managed Agents idle-pause primitive — zero cost while idle.
        """
        session = self._get(session_id)
        if session.state == "active":
            elapsed = time.monotonic() - session._active_start_ts
            session.run_time_active_s += elapsed
        session.state = "idle"
        if session._ticker:
            session._ticker.set_state("idle")
        logger.debug("session %s → idle (active %.1fs)", session_id[:8], session.run_time_active_s)
        return session

    def wake(self, session_id: str, wake_event: dict[str, Any]) -> Session:
        """Transition session to ``active`` and append the wake event.

        Ensures the cached system prompt hash is set (triggers a cache-write
        on first wake, cache-hit on subsequent wakes).
        """
        session = self._get(session_id)
        session.state = "active"
        session.last_active_ts = time.time()
        session._active_start_ts = time.monotonic()
        session.wake_events_consumed.append(wake_event)
        if session._ticker:
            session._ticker.set_state("active")

        # Mark system prompt hash (simulating prompt caching verification)
        if session.system_prompt_cached_hash is None:
            sp_path = session.agent_spec.system_prompt_template_path
            sp_text = _load_text(sp_path)
            session.system_prompt_cached_hash = hashlib.sha256(sp_text.encode()).hexdigest()[:16]

        logger.info(
            "session %s → active (wake_event topic=%s)",
            session_id[:8],
            wake_event.get("topic", "?"),
        )
        return session

    def checkpoint(self, session_id: str) -> Path:
        """Serialise session state to ``runtime/sessions/{session_id}.json``."""
        session = self._get(session_id)
        if session.state == "active":
            # Flush active time before checkpointing
            elapsed = time.monotonic() - session._active_start_ts
            session.run_time_active_s += elapsed
            session._active_start_ts = time.monotonic()

        session.state = "checkpointed"
        if session._ticker:
            session._ticker.set_state("idle")

        path = _RUNTIME_DIR / f"{session_id}.json"
        path.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
        session.checkpoint_path = str(path)
        logger.info("session %s checkpointed → %s", session_id[:8], path)
        return path

    def restore_from_checkpoint(self, session_id: str) -> Session:
        """Restore a session from its checkpoint file."""
        path = _RUNTIME_DIR / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))

        # Find original spec from already-created sessions, or build a minimal one
        existing = self._sessions.get(session_id)
        if existing is not None:
            agent_spec = existing.agent_spec
        else:
            # Minimal recovery — caller should re-register properly
            from skyherd.agents.spec import AgentSpec

            agent_spec = AgentSpec(
                name=data["agent_name"],
                system_prompt_template_path="",
            )

        ticker = CostTicker(
            session_id=session_id,
            ledger_callback=self._ledger,
            mqtt_publish_callback=self._mqtt_publish,
        )
        session = Session(
            id=data["id"],
            agent_name=data["agent_name"],
            agent_spec=agent_spec,
            state="idle",  # always restore to idle
            last_active_ts=data.get("last_active_ts", time.time()),
            wake_events_consumed=data.get("wake_events_consumed", []),
            checkpoint_path=data.get("checkpoint_path"),
            system_prompt_cached_hash=data.get("system_prompt_cached_hash"),
            cumulative_tokens_in=data.get("cumulative_tokens_in", 0),
            cumulative_tokens_out=data.get("cumulative_tokens_out", 0),
            cumulative_cost_usd=data.get("cumulative_cost_usd", 0.0),
            run_time_active_s=data.get("run_time_active_s", 0.0),
            run_time_idle_s=data.get("run_time_idle_s", 0.0),
            _ticker=ticker,
        )
        self._sessions[session_id] = session
        logger.info("session %s restored from checkpoint", session_id[:8])
        return session

    def on_webhook(self, event: dict[str, Any]) -> list[Session]:
        """Route an incoming MQTT event to all sessions whose wake_topics match.

        Returns the list of sessions that were woken.
        """
        topic: str = event.get("topic", "")
        woken: list[Session] = []
        for session in self._sessions.values():
            for pattern in session.agent_spec.wake_topics:
                if _mqtt_topic_matches(topic, pattern):
                    logger.debug(
                        "webhook topic=%s matched pattern=%s → waking %s",
                        topic,
                        pattern,
                        session.agent_name,
                    )
                    self.wake(session.id, event)
                    woken.append(session)
                    break  # only wake once per event per session
        return woken

    def get_session(self, session_id: str) -> Session:
        return self._get(session_id)

    def all_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def all_tickers(self) -> list[CostTicker]:
        return [s._ticker for s in self._sessions.values() if s._ticker is not None]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, session_id: str) -> Session:
        try:
            return self._sessions[session_id]
        except KeyError:
            raise KeyError(f"Unknown session: {session_id}") from None


def _mqtt_topic_matches(topic: str, pattern: str) -> bool:
    """Return True if MQTT *topic* matches MQTT *pattern*.

    Supports ``+`` (one level) and ``#`` (remaining levels).
    """
    if pattern == "#":
        return True
    if pattern.endswith("/#"):
        prefix = pattern[:-2]
        return topic == prefix or topic.startswith(prefix + "/")
    if "#" in pattern:
        # '#' must only appear at the end per MQTT spec
        return False
    # Split and compare level-by-level
    topic_parts = topic.split("/")
    pattern_parts = pattern.split("/")
    if len(topic_parts) != len(pattern_parts):
        return False
    return all(p == "+" or p == t for p, t in zip(pattern_parts, topic_parts, strict=True))
