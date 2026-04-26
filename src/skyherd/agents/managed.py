"""ManagedSessionManager — real Anthropic Managed Agents platform client.

Wraps ``client.beta.{agents,sessions,environments}.*`` with the same public
interface as the local ``LocalSessionManager`` (session.py).  Drop-in
replacement: call ``SessionManager.get(runtime="managed")`` instead of
instantiating directly.

Beta header ``managed-agents-2026-04-01`` is added automatically by the SDK
on every ``client.beta.*`` call — no manual header injection needed.

Prompt caching (C1 fix)
-----------------------
When using the real platform, prompt caching is automatic — the platform caches
the system prompt + skills prefix on first session use.  For the local fallback,
``build_cached_messages()`` now correctly calls ``client.messages.create()``
with the ``system`` and ``messages`` arrays (with ``cache_control`` blocks)
rather than discarding them.  Both runtimes therefore actually send
``cache_control`` blocks to Claude.

Usage
-----
``SKYHERD_AGENTS=managed ANTHROPIC_API_KEY=$KEY`` in environment enables the
managed runtime.  Without those vars, falls back to ``LocalSessionManager``.

    from skyherd.agents.session import SessionManager
    sm = SessionManager.get()           # auto-selects
    sm = SessionManager.get("managed")  # force managed (raises if no creds)
    sm = SessionManager.get("local")    # force local shim
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentinel exception
# ---------------------------------------------------------------------------


class ManagedAgentsUnavailable(RuntimeError):
    """Raised when MA runtime is requested but prerequisites are not met."""


# ---------------------------------------------------------------------------
# Session dataclass (MA-extended)
# ---------------------------------------------------------------------------


@dataclass
class ManagedSession:
    """Runtime state for one SkyHerd agent session on the real MA platform.

    Mirrors the shim ``Session`` dataclass but carries the platform IDs.
    """

    id: str  # local UUID (kept for API compat)
    agent_name: str
    platform_session_id: str  # returned by sessions.create()
    platform_agent_id: str  # returned by agents.create()
    platform_env_id: str  # environment used for this session
    state: str = "idle"
    last_active_ts: float = field(default_factory=time.time)
    wake_events_consumed: list[dict[str, Any]] = field(default_factory=list)
    checkpoint_path: str | None = None
    system_prompt_cached_hash: str | None = None

    # Token / cost accounting (populated from span.model_request_end events)
    cumulative_tokens_in: int = 0
    cumulative_tokens_out: int = 0
    cumulative_cost_usd: float = 0.0
    run_time_active_s: float = 0.0
    run_time_idle_s: float = 0.0

    # Store the agent_spec for wake_topics matching
    agent_spec: Any = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "platform_session_id": self.platform_session_id,
            "platform_agent_id": self.platform_agent_id,
            "platform_env_id": self.platform_env_id,
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
# Tool config builder (MEM-11)
# ---------------------------------------------------------------------------


def _build_tools_config(agent_spec: Any) -> dict[str, Any]:
    """Build the tools config for a managed agent.

    Default: ``agent_toolset_20260401`` with ``default_config.enabled=True``.
    If ``agent_spec.disable_tools`` is non-empty, emit explicit per-tool
    disables.

    MEM-11: CalvingWatch + GrazingOptimizer disable ``web_search`` + ``web_fetch``
    for determinism (preserves ``make demo SEED=42 SCENARIO=all`` byte-identical).
    """
    cfg: dict[str, Any] = {
        "type": "agent_toolset_20260401",
        "default_config": {"enabled": True},
    }
    disable = getattr(agent_spec, "disable_tools", None) or []
    if disable:
        cfg["configs"] = [{"name": t, "enabled": False} for t in disable]
    return cfg


# ---------------------------------------------------------------------------
# ManagedSessionManager
# ---------------------------------------------------------------------------


class ManagedSessionManager:
    """Session manager that talks to the real Anthropic Managed Agents platform.

    Public API is identical to ``LocalSessionManager`` so callers are
    unaware of which runtime is active.

    Parameters
    ----------
    api_key:
        Anthropic API key.  Defaults to ``ANTHROPIC_API_KEY`` env var.
    environment_id:
        Pre-created environment ID.  If ``None``, one will be created on
        first use and cached in ``runtime/ma_environment_id.txt``.
    agent_ids_path:
        Path to ``runtime/agent_ids.json`` that maps agent names to
        platform agent IDs.  Created on first use.
    mqtt_publish_callback:
        Optional async callable for MQTT publishing (cost ticks, etc).
    ledger_callback:
        Optional async callable for attestation ledger.
    """

    def __init__(
        self,
        api_key: str | None = None,
        environment_id: str | None = None,
        agent_ids_path: str = "runtime/agent_ids.json",
        mqtt_publish_callback: Any | None = None,
        ledger_callback: Any | None = None,
        memory_store_ids: dict[str, str] | None = None,
    ) -> None:
        import anthropic

        _key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not _key:
            raise ManagedAgentsUnavailable(
                "ANTHROPIC_API_KEY not set — cannot initialise ManagedSessionManager. "
                "Set ANTHROPIC_API_KEY or use runtime='local'."
            )

        self._client = anthropic.AsyncAnthropic(api_key=_key)
        self._sync_client = anthropic.Anthropic(api_key=_key)
        self._environment_id: str | None = environment_id
        self._agent_ids_path = Path(agent_ids_path)
        self._agent_ids: dict[str, str] = {}  # name → platform_agent_id
        self._sessions: dict[str, ManagedSession] = {}  # local_id → ManagedSession
        self._mqtt_publish = mqtt_publish_callback
        self._ledger = ledger_callback
        # MEM-01: per-agent + _shared memory store IDs populated by AgentMesh startup.
        self._memory_store_ids: dict[str, str] = memory_store_ids or {}

        # Load persisted agent IDs if available
        if self._agent_ids_path.exists():
            import json

            try:
                self._agent_ids = json.loads(self._agent_ids_path.read_text())
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not load agent_ids.json: %s", exc)

    # ------------------------------------------------------------------
    # Environment management
    # ------------------------------------------------------------------

    async def _ensure_environment(self) -> str:
        """Return a valid environment ID, creating one if needed."""
        if self._environment_id:
            return self._environment_id

        # Check persisted env ID
        env_cache = Path("runtime/ma_environment_id.txt")
        if env_cache.exists():
            self._environment_id = env_cache.read_text().strip()
            logger.info("MA environment loaded from cache: %s", self._environment_id)
            return self._environment_id

        # Create a new environment
        logger.info("Creating new MA environment…")
        env = await self._client.beta.environments.create(
            name="skyherd-ranch-env",
            config={
                "type": "cloud",
                "networking": {"type": "unrestricted"},
            },
        )
        self._environment_id = env.id
        env_cache.parent.mkdir(parents=True, exist_ok=True)
        env_cache.write_text(self._environment_id)
        logger.info("MA environment created: %s", self._environment_id)
        return self._environment_id

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    async def ensure_agent(self, agent_spec: Any) -> str:
        """Return a platform agent ID for *agent_spec*, creating it if needed.

        Persists agent IDs in ``runtime/agent_ids.json`` so the agent is
        created only once.  Idempotent: re-running uses the cached ID.
        """
        import json

        if agent_spec.name in self._agent_ids:
            return self._agent_ids[agent_spec.name]

        logger.info("Creating MA agent for %s…", agent_spec.name)
        system_prompt = self._load_text(agent_spec.system_prompt_template_path)

        agent = await self._client.beta.agents.create(
            name=agent_spec.name,
            model=agent_spec.model,
            system=system_prompt or f"You are {agent_spec.name} for SkyHerd.",
            tools=cast(Any, [_build_tools_config(agent_spec)]),
        )

        self._agent_ids[agent_spec.name] = agent.id
        self._agent_ids_path.parent.mkdir(parents=True, exist_ok=True)
        self._agent_ids_path.write_text(json.dumps(self._agent_ids, indent=2))
        logger.info("MA agent created: %s → %s", agent_spec.name, agent.id)
        return agent.id

    # ------------------------------------------------------------------
    # Session lifecycle  (same public API as LocalSessionManager)
    # ------------------------------------------------------------------

    async def create_session_async(self, agent_spec: Any) -> ManagedSession:
        """Create a new MA session for *agent_spec* (async).

        Attaches memory stores as session ``resources`` via ``extra_body`` —
        the anthropic 0.96 SDK's typed Resource union lacks ``memory_store``,
        so we smuggle the field via extra_body. Confirmed PASS by A1 probe
        against the live API 2026-04-23 (docs/A1_PROBE_RESULT.md).

        Per-agent store gets ``access: read_write``; shared store gets
        ``access: read_only``. Field name is ``access`` (NOT ``mode``) per the
        A1 probe schema finding — ``mode`` triggers 400 "Extra inputs".
        """
        agent_id = await self.ensure_agent(agent_spec)
        env_id = await self._ensure_environment()

        # Resolve memory store IDs (per-agent read_write + shared read_only).
        per_agent_store_id = self._memory_store_ids.get(agent_spec.name)
        shared_store_id = self._memory_store_ids.get("_shared")
        resources: list[dict[str, Any]] = []
        if per_agent_store_id:
            resources.append(
                {
                    "type": "memory_store",
                    "memory_store_id": per_agent_store_id,
                    "access": "read_write",
                }
            )
        if shared_store_id:
            resources.append(
                {
                    "type": "memory_store",
                    "memory_store_id": shared_store_id,
                    "access": "read_only",
                }
            )

        create_kwargs: dict[str, Any] = {
            "agent": agent_id,
            "environment_id": env_id,
            "title": f"skyherd-{agent_spec.name}",
        }
        if resources:
            create_kwargs["extra_body"] = {"resources": resources}

        platform_session = await self._client.beta.sessions.create(**create_kwargs)

        local_id = str(uuid.uuid4())
        session = ManagedSession(
            id=local_id,
            agent_name=agent_spec.name,
            platform_session_id=platform_session.id,
            platform_agent_id=agent_id,
            platform_env_id=env_id,
            state="idle",
            agent_spec=agent_spec,
        )
        self._sessions[local_id] = session
        logger.info(
            "MA session created: %s (platform=%s)",
            local_id[:8],
            platform_session.id[:16],
        )
        return session

    def create_session(self, agent_spec: Any) -> ManagedSession:
        """Sync wrapper for create_session_async (used in non-async contexts)."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If called from within an async context, caller should use await
                raise RuntimeError("Use 'await create_session_async(spec)' inside async code.")
            return loop.run_until_complete(self.create_session_async(agent_spec))
        except RuntimeError:
            raise

    def sleep(self, session_id: str) -> ManagedSession:
        """Mark session as idle (platform auto-pauses billing)."""
        session = self._get(session_id)
        session.state = "idle"
        logger.debug("MA session %s → idle", session_id[:8])
        return session

    def wake(self, session_id: str, wake_event: dict[str, Any]) -> ManagedSession:
        """Mark session as active and record wake event."""
        session = self._get(session_id)
        session.state = "active"
        session.last_active_ts = time.time()
        session.wake_events_consumed.append(wake_event)
        logger.info(
            "MA session %s → active (wake_event topic=%s)",
            session_id[:8],
            wake_event.get("topic", "?"),
        )
        return session

    def checkpoint(self, session_id: str) -> Path:
        """No-op on the real platform (checkpointing is automatic).

        Writes a small marker file for compatibility with existing code.
        """
        session = self._get(session_id)
        session.state = "checkpointed"
        _dir = Path("runtime/sessions")
        _dir.mkdir(parents=True, exist_ok=True)
        path = _dir / f"{session_id}.json"
        import json

        path.write_text(json.dumps(session.to_dict(), indent=2))
        session.checkpoint_path = str(path)
        return path

    def restore_from_checkpoint(self, session_id: str) -> ManagedSession:
        """Restore local metadata from checkpoint file."""
        import json

        path = Path("runtime/sessions") / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")
        data = json.loads(path.read_text())
        existing = self._sessions.get(session_id)
        if existing:
            return existing
        session = ManagedSession(
            id=data["id"],
            agent_name=data["agent_name"],
            platform_session_id=data.get("platform_session_id", ""),
            platform_agent_id=data.get("platform_agent_id", ""),
            platform_env_id=data.get("platform_env_id", ""),
            state="idle",
            last_active_ts=data.get("last_active_ts", time.time()),
            wake_events_consumed=data.get("wake_events_consumed", []),
            cumulative_tokens_in=data.get("cumulative_tokens_in", 0),
            cumulative_tokens_out=data.get("cumulative_tokens_out", 0),
            cumulative_cost_usd=data.get("cumulative_cost_usd", 0.0),
        )
        self._sessions[session_id] = session
        return session

    def on_webhook(self, event: dict[str, Any]) -> list[ManagedSession]:
        """Route MQTT event to sessions whose wake_topics match."""
        from skyherd.agents.session import _mqtt_topic_matches

        topic: str = event.get("topic", "")
        woken: list[ManagedSession] = []
        for session in self._sessions.values():
            if session.agent_spec is None:
                continue
            for pattern in session.agent_spec.wake_topics:
                if _mqtt_topic_matches(topic, pattern):
                    self.wake(session.id, event)
                    woken.append(session)
                    break
        return woken

    def get_session(self, session_id: str) -> ManagedSession:
        return self._get(session_id)

    def all_sessions(self) -> list[ManagedSession]:
        return list(self._sessions.values())

    def all_tickers(self) -> list[Any]:
        """MA runtime uses platform billing; no local tickers."""
        return []

    # ------------------------------------------------------------------
    # Platform event helpers
    # ------------------------------------------------------------------

    async def send_wake_event(
        self,
        session: ManagedSession,
        user_text: str,
    ) -> None:
        """Send a user.message to the platform session (wakes it from idle)."""
        await self._client.beta.sessions.events.send(
            session.platform_session_id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": user_text}],
                }
            ],
        )

    async def stream_session_events(self, session: ManagedSession):
        """Yield platform SSE events from the session stream."""
        # AsyncEvents.stream() is a coroutine (async def) that returns AsyncStream.
        # Must await the coroutine to obtain the AsyncStream before using it as a
        # context manager — omitting await would enter the coroutine object itself,
        # which is not an async context manager and raises TypeError at runtime.
        async with await self._client.beta.sessions.events.stream(
            session.platform_session_id
        ) as stream:
            async for event in stream:
                yield event

    async def send_tool_result(
        self,
        session: ManagedSession,
        tool_use_id: str,
        result_content: str,
        is_error: bool = False,
    ) -> None:
        """Send a custom tool result back to the platform session."""
        await self._client.beta.sessions.events.send(
            session.platform_session_id,
            events=[
                {
                    "type": "user.custom_tool_result",
                    "custom_tool_use_id": tool_use_id,
                    "content": [{"type": "text", "text": result_content}],
                    "is_error": is_error,
                }
            ],
        )

    # ------------------------------------------------------------------
    # Smoke test
    # ------------------------------------------------------------------

    async def smoke_test_session(self, agent_spec: Any, wake_event: dict[str, Any]) -> str:
        """Create a session, send a wake event, return the platform session ID."""
        session = await self.create_session_async(agent_spec)
        user_text = (
            f"SMOKE TEST — WAKE EVENT: {wake_event.get('type', 'unknown')}\n"
            f"Ranch: {wake_event.get('ranch_id', 'ranch_a')}\n"
            f"Topic: {wake_event.get('topic', 'unknown')}\n"
            "Respond with a brief status acknowledgment only."
        )
        await self.send_wake_event(session, user_text)
        logger.info(
            "Smoke test session %s (platform=%s) sent wake event.",
            session.id[:8],
            session.platform_session_id[:16],
        )
        return session.platform_session_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, session_id: str) -> ManagedSession:
        try:
            return self._sessions[session_id]
        except KeyError:
            raise KeyError(f"Unknown MA session: {session_id}") from None

    @staticmethod
    def _load_text(path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return ""
