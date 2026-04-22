"""Shared handler base for all 5 SkyHerd agent handlers.

This module consolidates the ``_run_with_sdk`` pattern that was duplicated
across all 5 handler files and fixes **code-review item C1** — prompt caching
was previously built but discarded (the old code extracted only the text string
and called ``sdk_client.query(prompt=str)`` which does not pass the
``cache_control`` blocks to Claude).

C1 fix — both runtimes now send ``cache_control`` correctly
-----------------------------------------------------------
**Managed runtime**: the platform applies prompt caching automatically for
system prompts and skills; we stream the session SSE event loop.

**Local runtime** (``SKYHERD_AGENTS`` not set or ``=local``): we call
``client.messages.create(system=system_blocks, messages=messages)`` directly
using the full ``cached_payload`` dict that ``build_cached_messages()`` already
built.  Cache-write tokens appear in ``usage.cache_creation_input_tokens`` on
the first wake, cache-read tokens on subsequent wakes.

Usage
-----
Each handler calls :func:`run_handler_cycle` instead of its own
``_run_with_sdk`` implementation.  The simulation fallback is preserved
unchanged.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


async def run_handler_cycle(
    session: Any,  # Session or ManagedSession
    wake_event: dict[str, Any],
    sdk_client: Any,  # anthropic.AsyncAnthropic or None
    cached_payload: dict[str, Any],  # from build_cached_messages()
    tool_dispatcher: Any | None = None,  # optional async callable(name, input) → str
) -> list[dict[str, Any]]:
    """Run one agent wake cycle and return a list of tool-call records.

    Selects the correct path automatically:

    1. **Managed runtime** (``SKYHERD_AGENTS=managed`` + ``platform_session_id``):
       streams SSE events from the platform session, dispatches
       ``agent.custom_tool_use`` events via *tool_dispatcher*.

    2. **Local runtime** with live API key: calls
       ``client.messages.create()`` with the full ``cached_payload``
       (system + messages with ``cache_control`` blocks).  This is the C1 fix.

    3. **Simulation** (no API key or no client): returns empty list — caller
       invokes its ``_simulate_handler()`` fallback.

    Parameters
    ----------
    session:
        Current session object (local ``Session`` or ``ManagedSession``).
    wake_event:
        The MQTT event that triggered this wake cycle.
    sdk_client:
        An ``anthropic.AsyncAnthropic`` instance, or ``None`` to force
        simulation.
    cached_payload:
        Dict with ``"system"`` (list of cache_control blocks) and
        ``"messages"`` (list with the user turn) — as returned by
        ``build_cached_messages()``.
    tool_dispatcher:
        Optional async callable ``(tool_name: str, tool_input: dict) → str``
        used in the MA runtime to execute custom tools.

    Returns
    -------
    list[dict]
        Tool-call records: ``{"tool": name, "input": {...}}``.
        Empty list if the simulation path was taken (caller handles that).
    """
    if sdk_client is None or not os.environ.get("ANTHROPIC_API_KEY"):
        return []  # signal: caller should use _simulate_handler()

    # Check for managed runtime: session has platform_session_id attribute
    platform_session_id: str | None = getattr(session, "platform_session_id", None)

    if platform_session_id and os.environ.get("SKYHERD_AGENTS") == "managed":
        return await _run_managed(
            session=session,
            sdk_client=sdk_client,
            cached_payload=cached_payload,
            platform_session_id=platform_session_id,
            tool_dispatcher=tool_dispatcher,
        )

    # Local runtime — C1 fix: pass system + messages with cache_control
    return await _run_local_with_cache(
        session=session,
        sdk_client=sdk_client,
        cached_payload=cached_payload,
    )


async def _run_managed(
    session: Any,
    sdk_client: Any,
    cached_payload: dict[str, Any],
    platform_session_id: str,
    tool_dispatcher: Any | None,
) -> list[dict[str, Any]]:
    """Drive a real Managed Agents platform session via SSE stream."""

    calls: list[dict[str, Any]] = []

    # Extract user message from cached_payload to send as wake event
    messages = cached_payload.get("messages", [])
    user_text = ""
    if messages:
        content = messages[0].get("content", [])
        if content and isinstance(content, list):
            user_text = content[0].get("text", "")
        elif isinstance(content, str):
            user_text = content

    # Send the wake event to the platform session
    await sdk_client.beta.sessions.events.send(
        platform_session_id,
        events=[
            {
                "type": "user.message",
                "content": [{"type": "text", "text": user_text}],
            }
        ],
    )

    # Stream events from the platform
    async with sdk_client.beta.sessions.events.stream(platform_session_id) as stream:
        async for event in stream:
            event_type = getattr(event, "type", None)

            if event_type == "agent.custom_tool_use":
                tool_name = getattr(event, "name", "unknown")
                tool_input = getattr(event, "input", {})
                calls.append({"tool": tool_name, "input": tool_input})

                # Dispatch tool and send result back
                result_text = ""
                if tool_dispatcher is not None:
                    try:
                        result_text = await tool_dispatcher(tool_name, tool_input)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Tool %s failed: %s", tool_name, exc)
                        result_text = f"error: {exc}"

                await sdk_client.beta.sessions.events.send(
                    platform_session_id,
                    events=[
                        {
                            "type": "user.custom_tool_result",
                            "custom_tool_use_id": event.id,
                            "content": [{"type": "text", "text": result_text or "ok"}],
                            "is_error": False,
                        }
                    ],
                )

            elif event_type == "span.model_request_end":
                usage = getattr(event, "model_usage", None)
                if usage is not None:
                    session.cumulative_tokens_in += getattr(usage, "input_tokens", 0)
                    session.cumulative_tokens_out += getattr(usage, "output_tokens", 0)

            elif event_type in ("session.status_idle", "session.status_terminated"):
                # Check stop_reason — only break on terminal idle
                stop_reason = getattr(event, "stop_reason", None)
                if event_type == "session.status_terminated":
                    break
                if stop_reason is not None:
                    sr_type = getattr(stop_reason, "type", None)
                    if sr_type != "requires_action":
                        break
                else:
                    break

    return calls


async def _run_local_with_cache(
    session: Any,
    sdk_client: Any,
    cached_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """C1 fix: call messages.create() with full cache_control blocks.

    Previously the shim extracted only the text string and discarded the
    ``cache_control`` blocks.  Now we pass the full ``system`` and
    ``messages`` arrays so Claude actually receives the caching headers.
    """
    import anthropic

    calls: list[dict[str, Any]] = []
    system_blocks = cached_payload.get("system", [])
    messages = cached_payload.get("messages", [])

    # Detect model from session if available
    model = "claude-opus-4-7"
    agent_spec = getattr(session, "agent_spec", None)
    if agent_spec is not None:
        model = getattr(agent_spec, "model", model)

    try:
        response = await sdk_client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_blocks,
            messages=messages,
        )

        # Record token usage (including cache hit/write counts)
        usage = getattr(response, "usage", None)
        if usage is not None:
            input_tokens = getattr(usage, "input_tokens", 0)
            output_tokens = getattr(usage, "output_tokens", 0)
            cache_read = getattr(usage, "cache_read_input_tokens", 0)
            cache_write = getattr(usage, "cache_creation_input_tokens", 0)
            session.cumulative_tokens_in += input_tokens + cache_read + cache_write
            session.cumulative_tokens_out += output_tokens
            if cache_read > 0:
                logger.debug(
                    "Cache hit: %d read tokens, %d write tokens for %s",
                    cache_read,
                    cache_write,
                    getattr(session, "agent_name", "?"),
                )

        # Extract tool-use blocks
        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "tool_use":
                calls.append(
                    {
                        "tool": getattr(block, "name", "unknown"),
                        "input": getattr(block, "input", {}),
                    }
                )

    except anthropic.APIError as exc:
        logger.error("messages.create failed: %s", exc)

    return calls
