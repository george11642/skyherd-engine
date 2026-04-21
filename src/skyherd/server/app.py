"""SkyHerd FastAPI application factory.

Serves:
- /health              — 200 OK
- /api/snapshot        — current world snapshot
- /api/agents          — 5 agent statuses
- /api/attest          — recent ledger entries (since_seq param)
- /events              — SSE stream (EventSourceResponse)
- /                    — serves Vite SPA (web/dist/index.html)
- /rancher             — same SPA, client-side router handles /rancher

Mock mode (SKYHERD_MOCK=1): no live mesh/bus/world required.
"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from skyherd.server.events import (
    AGENT_NAMES,
    EventBroadcaster,
    _mock_attest_entry,
    _mock_world_snapshot,
)

logger = logging.getLogger(__name__)

_MOCK_MODE = os.environ.get("SKYHERD_MOCK", "0") == "1"
_STATIC_DIR = Path(__file__).parent.parent.parent.parent / "web" / "dist"

# Shared broadcaster instance (module-level, created at startup)
_broadcaster: EventBroadcaster | None = None


def create_app(
    mock: bool | None = None,
    mesh: Any = None,
    ledger: Any = None,
    world: Any = None,
) -> FastAPI:
    """App factory — injectable for testing."""
    use_mock = mock if mock is not None else _MOCK_MODE

    broadcaster = EventBroadcaster(mock=use_mock, mesh=mesh, ledger=ledger, world=world)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global _broadcaster
        _broadcaster = broadcaster
        broadcaster.start()
        logger.info("SkyHerd server started (mock=%s)", use_mock)
        yield
        broadcaster.stop()
        logger.info("SkyHerd server stopped")

    app = FastAPI(
        title="SkyHerd Dashboard",
        version="0.1.0",
        description="SkyHerd ranch monitoring live dashboard + rancher PWA",
        lifespan=lifespan,
    )

    # CORS — open for Vite dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "ts": str(time.time())}

    # ------------------------------------------------------------------
    # REST endpoints
    # ------------------------------------------------------------------

    @app.get("/api/snapshot")
    async def api_snapshot() -> JSONResponse:
        if use_mock or world is None:
            data = _mock_world_snapshot()
        else:
            data = world.snapshot().model_dump()
        return JSONResponse(content=data)

    @app.get("/api/agents")
    async def api_agents() -> JSONResponse:
        if use_mock or mesh is None:
            agents = _mock_agent_statuses()
        else:
            agents = _live_agent_statuses(mesh)
        return JSONResponse(content={"agents": agents, "ts": time.time()})

    @app.get("/api/attest")
    async def api_attest(since_seq: int = Query(default=0, ge=0)) -> JSONResponse:
        if use_mock or ledger is None:
            entries = [_mock_attest_entry() for _ in range(min(10, 50))]
        else:
            entries = [e.model_dump() for e in ledger.iter_events(since_seq=since_seq)][:50]
        return JSONResponse(content={"entries": entries, "ts": time.time()})

    # ------------------------------------------------------------------
    # SSE endpoint
    # ------------------------------------------------------------------

    @app.get("/events")
    async def sse_stream() -> EventSourceResponse:
        async def _generator():
            async for event_type, payload in broadcaster.subscribe():
                yield {"event": event_type, "data": json.dumps(payload, default=str)}

        return EventSourceResponse(_generator())

    # ------------------------------------------------------------------
    # Static SPA
    # ------------------------------------------------------------------

    if _STATIC_DIR.exists():
        # Mount assets sub-directory for hashed files
        assets_dir = _STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/")
        async def spa_root() -> FileResponse:
            return FileResponse(str(_STATIC_DIR / "index.html"))

        @app.get("/rancher")
        async def spa_rancher() -> FileResponse:
            return FileResponse(str(_STATIC_DIR / "index.html"))

        # Catch-all for client-side routes
        @app.get("/{full_path:path}")
        async def spa_catch(full_path: str) -> FileResponse:
            static_file = _STATIC_DIR / full_path
            if static_file.is_file():
                return FileResponse(str(static_file))
            return FileResponse(str(_STATIC_DIR / "index.html"))
    else:
        # Dev mode: SPA served by Vite, just return a placeholder
        @app.get("/")
        async def dev_root() -> HTMLResponse:
            return HTMLResponse(
                "<html><body><h1>SkyHerd Server</h1>"
                "<p>Vite dev server should be running at :5173</p>"
                "<p>SSE: <a href='/events'>/events</a></p>"
                "<p>API: <a href='/api/snapshot'>/api/snapshot</a></p>"
                "</body></html>"
            )

        @app.get("/rancher")
        async def dev_rancher() -> HTMLResponse:
            return HTMLResponse(
                "<html><body><h1>Rancher PWA (dev)</h1></body></html>"
            )

    return app


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _mock_agent_statuses() -> list[dict[str, Any]]:
    t = time.time()
    result = []
    for i, name in enumerate(AGENT_NAMES):
        phase = int(t + i * 3) % 15
        state = "active" if phase < 10 else "idle"
        result.append(
            {
                "name": name,
                "state": state,
                "last_wake": t - (t % 60),
                "cumulative_tokens_in": 1200 + i * 300,
                "cumulative_tokens_out": 450 + i * 100,
                "cumulative_cost_usd": 0.0023 + i * 0.0005,
            }
        )
    return result


def _live_agent_statuses(mesh: Any) -> list[dict[str, Any]]:
    result = []
    for name, session in mesh._sessions.items():
        result.append(
            {
                "name": name,
                "state": session.state,
                "last_wake": session.last_active_ts,
                "cumulative_tokens_in": session.cumulative_tokens_in,
                "cumulative_tokens_out": session.cumulative_tokens_out,
                "cumulative_cost_usd": session.cumulative_cost_usd,
            }
        )
    return result


# ------------------------------------------------------------------
# Module-level app (for uvicorn direct invocation)
# ------------------------------------------------------------------

app = create_app()
