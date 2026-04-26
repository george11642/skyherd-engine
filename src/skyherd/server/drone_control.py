"""Manual drone-control HTTP surface for the laptop-as-controller path (Phase 7.1).

Five token-gated POST endpoints mount onto the FastAPI app to let a human
operator drive the Mavic from the dashboard when the agent mesh should not —
Friday field-test use, emergency stop, or ground-school sanity checks.

Endpoints
---------
``POST /api/drone/arm``       — connect the backend (idempotent when connected).
``POST /api/drone/disarm``    — disconnect the backend (no-op when unarmed).
``POST /api/drone/takeoff``   — optional body ``{"alt_m": float}`` (0 < alt ≤ 120).
``POST /api/drone/rtl``       — return-to-home.
``POST /api/drone/land``      — alias of RTL; Mavic's "land" = RTL-descend.
``POST /api/drone/estop``     — RTL first; on failure, force-disconnect. Always
                                returns 200 with ``best_effort`` flag.

Security
--------
Every call requires header ``X-Manual-Override-Token``. The valid token is
provided at ``create_app()`` time via the ``SKYHERD_MANUAL_OVERRIDE_TOKEN``
env var. When the token is an empty string, all endpoints return 503 —
manual override is disabled until an operator flips it on.

SSE
---
Successful (or best-effort ESTOP) calls emit ``drone.manual_override`` with
payload::

    {
      "action": "arm" | "disarm" | "takeoff" | "rtl" | "land" | "estop",
      "actor": "laptop",
      "ts": float,             # time.time()
      "success": bool,
      "latency_ms": int,
      "error": str | None,     # present on failure
      "best_effort": bool      # present on ESTOP fallback
    }

Determinism note
----------------
Manual endpoints are a no-op (503) when no drone backend is attached. During
``make demo SEED=42 SCENARIO=all`` the sim world runs without a live backend,
so this module is byte-neutral for the determinism gate.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from skyherd.drone.interface import DroneBackend, DroneError, DroneUnavailable

logger = logging.getLogger(__name__)

__all__ = [
    "ManualAction",
    "ManualOverrideRequest",
    "attach_drone_control",
    "TOKEN_HEADER",
]

TOKEN_HEADER = "X-Manual-Override-Token"
_ACTOR = "laptop"
_MIN_ALT_M = 0.5
_MAX_ALT_M = 120.0


class ManualAction(str, Enum):
    """Enumerates the five manual override actions exposed over HTTP."""

    ARM = "arm"
    DISARM = "disarm"
    TAKEOFF = "takeoff"
    RTL = "rtl"
    LAND = "land"
    ESTOP = "estop"


class ManualOverrideRequest(BaseModel):
    """Optional body for TAKEOFF — other actions accept an empty body."""

    alt_m: float | None = Field(
        default=None,
        gt=_MIN_ALT_M - 0.01,  # tolerate 0.5 exactly
        le=_MAX_ALT_M,
        description=(
            "Takeoff altitude in metres AGL. Must be within "
            f"({_MIN_ALT_M}, {_MAX_ALT_M}]. Defaults to 20 m."
        ),
    )


def _broadcast_event(broadcaster: Any, payload: dict[str, Any]) -> None:
    """Emit drone.manual_override via any broadcaster exposing ``_broadcast``.

    Works with the live :class:`skyherd.server.events.EventBroadcaster` and
    with the lightweight fakes the tests inject. Never raises — a broken
    broadcaster must not take down the endpoint.
    """
    if broadcaster is None:
        return
    fn = getattr(broadcaster, "_broadcast", None)
    if not callable(fn):
        return
    try:
        fn("drone.manual_override", payload)
    except Exception as exc:  # noqa: BLE001 — defensive, never crash the endpoint
        logger.debug("drone.manual_override broadcast failed: %s", exc)


def attach_drone_control(
    app: FastAPI,
    *,
    get_backend: Callable[[], DroneBackend | None],
    broadcaster: Any,
    token: str,
) -> None:
    """Mount the five manual-override endpoints onto ``app``.

    Parameters
    ----------
    app:
        The FastAPI application to mount onto.
    get_backend:
        Zero-arg callable returning the currently-attached
        :class:`DroneBackend`, or ``None`` when nothing is wired up. Called
        fresh on each request so reconfigures during runtime are picked up.
    broadcaster:
        The server's :class:`EventBroadcaster` (or a test fake exposing
        ``_broadcast(event_type, payload)``). When ``None`` the endpoints
        simply skip the SSE emit.
    token:
        The expected value of the ``X-Manual-Override-Token`` header. When
        empty, every endpoint returns 503.
    """

    configured_token = token or ""

    def _verify_token(provided: str | None) -> None:
        """Raise the right HTTPException for bad auth; return silently on pass."""
        if not configured_token:
            # Operator has not enabled manual override.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="manual override disabled",
            )
        if not provided:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing X-Manual-Override-Token header",
            )
        if provided != configured_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="invalid manual override token",
            )

    def _resolve_backend() -> DroneBackend:
        backend = get_backend()
        if backend is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="no drone backend attached",
            )
        return backend

    async def _run(
        action: ManualAction,
        fn: Callable[[], Awaitable[Any]],
        *,
        best_effort: Callable[[], Awaitable[Any]] | None = None,
    ) -> JSONResponse:
        """Shared execute-and-emit helper for the six endpoints.

        ``fn`` is the primary coroutine factory. ``best_effort`` is a
        secondary coroutine run only when ``fn`` raises — used by ESTOP to
        fall back from RTL to disconnect.
        """
        started = time.monotonic()
        payload: dict[str, Any] = {
            "action": action.value,
            "actor": _ACTOR,
            "ts": time.time(),
        }

        try:
            await fn()
        except (DroneUnavailable, DroneError) as exc:
            err = str(exc)
            if best_effort is None:
                latency_ms = int((time.monotonic() - started) * 1000)
                payload.update({"success": False, "latency_ms": latency_ms, "error": err})
                _broadcast_event(broadcaster, payload)
                # 502 = upstream (the drone) refused the command.
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=err) from exc

            # ESTOP fallback path: try disconnect to kill the link.
            try:
                await best_effort()
                latency_ms = int((time.monotonic() - started) * 1000)
                payload.update(
                    {
                        "success": True,
                        "latency_ms": latency_ms,
                        "error": err,
                        "best_effort": True,
                    }
                )
                _broadcast_event(broadcaster, payload)
                return JSONResponse(
                    content={
                        "ok": True,
                        "action": action.value,
                        "latency_ms": latency_ms,
                        "best_effort": True,
                        "first_error": err,
                    }
                )
            except (DroneUnavailable, DroneError) as exc2:
                latency_ms = int((time.monotonic() - started) * 1000)
                combined = f"{err} || fallback: {exc2}"
                payload.update(
                    {
                        "success": False,
                        "latency_ms": latency_ms,
                        "error": combined,
                        "best_effort": True,
                    }
                )
                _broadcast_event(broadcaster, payload)
                # Still return 200 — ESTOP must never look "broken" to the
                # operator; the payload tells them what we tried.
                return JSONResponse(
                    content={
                        "ok": False,
                        "action": action.value,
                        "latency_ms": latency_ms,
                        "best_effort": True,
                        "error": combined,
                    }
                )

        latency_ms = int((time.monotonic() - started) * 1000)
        payload.update({"success": True, "latency_ms": latency_ms})
        _broadcast_event(broadcaster, payload)
        return JSONResponse(
            content={
                "ok": True,
                "action": action.value,
                "latency_ms": latency_ms,
            }
        )

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.post("/api/drone/arm")
    async def api_arm(
        x_manual_override_token: str | None = Header(default=None),
    ) -> JSONResponse:
        _verify_token(x_manual_override_token)
        backend = _resolve_backend()

        async def _arm() -> None:
            # Idempotent: connect() on an already-connected backend is a cheap
            # no-op across every shipped backend. StubBackend sets its flag
            # back to True with no side effects.
            await backend.connect()

        return await _run(ManualAction.ARM, _arm)

    @app.post("/api/drone/disarm")
    async def api_disarm(
        x_manual_override_token: str | None = Header(default=None),
    ) -> JSONResponse:
        _verify_token(x_manual_override_token)
        backend = _resolve_backend()

        async def _disarm() -> None:
            # Idempotent: disconnect on an already-disconnected backend is safe.
            await backend.disconnect()

        return await _run(ManualAction.DISARM, _disarm)

    @app.post("/api/drone/takeoff")
    async def api_takeoff(
        body: ManualOverrideRequest | None = None,
        x_manual_override_token: str | None = Header(default=None),
    ) -> JSONResponse:
        _verify_token(x_manual_override_token)
        backend = _resolve_backend()
        alt_m = body.alt_m if body and body.alt_m is not None else 20.0

        async def _takeoff() -> None:
            await backend.takeoff(alt_m=alt_m)

        return await _run(ManualAction.TAKEOFF, _takeoff)

    @app.post("/api/drone/rtl")
    async def api_rtl(
        x_manual_override_token: str | None = Header(default=None),
    ) -> JSONResponse:
        _verify_token(x_manual_override_token)
        backend = _resolve_backend()

        async def _rtl() -> None:
            await backend.return_to_home()

        return await _run(ManualAction.RTL, _rtl)

    @app.post("/api/drone/land")
    async def api_land(
        x_manual_override_token: str | None = Header(default=None),
    ) -> JSONResponse:
        _verify_token(x_manual_override_token)
        backend = _resolve_backend()

        async def _land() -> None:
            # On Mavic, "land" at the current position is identical to RTL
            # with a short home-offset; the adapter's return_to_home handles
            # the descend profile.
            await backend.return_to_home()

        return await _run(ManualAction.LAND, _land)

    @app.post("/api/drone/estop")
    async def api_estop(
        x_manual_override_token: str | None = Header(default=None),
    ) -> JSONResponse:
        _verify_token(x_manual_override_token)
        backend = _resolve_backend()

        async def _rtl() -> None:
            await backend.return_to_home()

        async def _disconnect() -> None:
            await backend.disconnect()

        return await _run(ManualAction.ESTOP, _rtl, best_effort=_disconnect)

    logger.info(
        "Mounted manual drone-control endpoints (token %s)",
        "configured" if configured_token else "disabled",
    )
