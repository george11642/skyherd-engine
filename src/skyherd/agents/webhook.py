"""Webhook router for Managed Agents platform callbacks.

Mounts at ``/webhooks/managed-agents`` and verifies HMAC-SHA256 signatures
using the ``SKYHERD_WEBHOOK_SECRET`` environment variable.

The Managed Agents platform POSTs events here when a session emits
``agent.custom_tool_use`` or changes state.  We forward them into the
AgentMesh via ``on_webhook()``.

Security
--------
Every request must include the header::

    X-SkyHerd-Signature: sha256=<hex_digest>

computed as ``HMAC-SHA256(body_bytes, SKYHERD_WEBHOOK_SECRET)``.
Requests with a missing or invalid signature return 401.

If ``SKYHERD_WEBHOOK_SECRET`` is not set the router still loads but
signature verification is **skipped** — for local-dev convenience only.
A warning is emitted at startup.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

logger = logging.getLogger(__name__)

_WEBHOOK_SECRET = os.environ.get("SKYHERD_WEBHOOK_SECRET", "")
if not _WEBHOOK_SECRET:
    logger.warning(
        "SKYHERD_WEBHOOK_SECRET not set — webhook signature verification disabled. "
        "Set this env var in production."
    )

webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Module-level mesh reference — set by app.py after AgentMesh is created.
_mesh_ref: Any = None


def set_mesh(mesh: Any) -> None:
    """Register the AgentMesh instance for event routing."""
    global _mesh_ref
    _mesh_ref = mesh


def _verify_signature(body: bytes, signature_header: str | None) -> bool:
    """Return True if signature_header matches HMAC-SHA256(body, secret).

    If the secret is not configured, always returns True (dev mode).
    """
    if not _WEBHOOK_SECRET:
        return True
    if not signature_header:
        return False
    expected = "sha256=" + hmac.new(_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@webhook_router.post("/managed-agents", status_code=status.HTTP_204_NO_CONTENT)
async def managed_agents_event(
    request: Request,
    x_skyherd_signature: str | None = Header(default=None),
) -> None:
    """Receive a Managed Agents platform event and route it into AgentMesh.

    The platform POSTs JSON payloads of the form::

        {
            "type": "agent.custom_tool_use",
            "session_id": "...",
            "name": "launch_drone",
            "input": { ... }
        }

    We convert these into the same ``wake_event`` dict format the mesh uses
    for MQTT events, then call ``mesh.on_webhook(event)``.
    """
    body = await request.body()

    if not _verify_signature(body, x_skyherd_signature):
        logger.warning("Webhook signature verification failed — rejected request.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-SkyHerd-Signature",
        )

    try:
        payload: dict[str, Any] = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be valid JSON",
        ) from exc

    event_type: str = payload.get("type", "unknown")
    logger.debug("Managed Agents webhook: type=%s payload_keys=%s", event_type, list(payload))

    mesh = _mesh_ref
    if mesh is None:
        # Mesh not yet initialised — accept the event but don't route it.
        logger.warning("Webhook received but AgentMesh not registered — dropping event.")
        return

    # Build a topic from the session_id so on_webhook() can route to the
    # correct session.  Format mirrors MQTT topic convention.
    session_id: str = payload.get("session_id", "unknown")
    topic = f"skyherd/managed/{session_id}/{event_type.replace('.', '/')}"

    event = {
        "topic": topic,
        "type": event_type,
        "session_id": session_id,
        **{k: v for k, v in payload.items() if k not in ("type", "session_id")},
    }

    # on_webhook() is synchronous — safe to call from async context.
    try:
        mesh.on_webhook(event)
    except Exception as exc:  # noqa: BLE001
        logger.error("AgentMesh.on_webhook failed: %s", exc)
        # Don't surface internal errors to the platform — return 204 anyway.
