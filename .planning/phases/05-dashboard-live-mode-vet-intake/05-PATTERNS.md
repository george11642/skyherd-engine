# Phase 5: Dashboard Live-Mode & Vet-Intake — Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 13 new/modified files
**Analogs found:** 12 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/skyherd/server/app.py` | controller | request-response | `src/skyherd/server/app.py` (self — add 2 endpoints) | exact |
| `src/skyherd/server/cli.py` | config/entrypoint | request-response | `src/skyherd/server/cli.py` (self — add `--live` flag) | exact |
| `src/skyherd/server/vet_intake.py` | service | file-I/O | `src/skyherd/mcp/rancher_mcp.py` | role-match |
| `src/skyherd/server/events.py` | service | event-driven | `src/skyherd/server/events.py` (self — harden `_real_cost_tick`) | exact |
| `src/skyherd/agents/herd_health_watcher.py` | service | event-driven | `src/skyherd/agents/herd_health_watcher.py` (self — add drafter step) | exact |
| `src/skyherd/scenarios/sick_cow.py` | test | batch | `src/skyherd/scenarios/sick_cow.py` (self — add assertion) | exact |
| `web/src/components/VetIntakePanel.tsx` | component | request-response | `web/src/components/AttestationPanel.tsx` | role-match |
| `web/src/components/CostTicker.tsx` | component | event-driven | `web/src/components/CostTicker.tsx` (self — polish paused state) | exact |
| `web/src/components/AttestationPanel.tsx` | component | event-driven | `web/src/components/AttestationPanel.tsx` (self — add verify button) | exact |
| `web/src/components/RanchMap.tsx` | component | event-driven | `web/src/components/RanchMap.tsx` (self — predator ring RAF) | exact |
| `web/src/lib/sse.ts` | utility | event-driven | `web/src/lib/sse.ts` (self — add `vet_intake.drafted` event) | exact |
| `web/index.html` | config | — | `web/index.html` (self — add font preload links) | exact |
| `web/vite.config.ts` | config | — | `web/vite.config.ts` (self — add `manualChunks`) | exact |
| `.github/workflows/lighthouse.yml` | config/CI | — | `.github/workflows/ci.yml` | role-match |

---

## Pattern Assignments

### `src/skyherd/server/app.py` — Add `/api/attest/verify` and `/api/vet-intake/{id}`

**Analog:** `src/skyherd/server/app.py` (existing endpoints, lines 134–156)

**Imports pattern** (lines 26–47):
```python
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from skyherd.server.events import (
    AGENT_NAMES,
    EventBroadcaster,
    _mock_attest_entry,
    _mock_world_snapshot,
)
```

**Existing endpoint pattern** (lines 150–156 — copy shape for `/api/attest/verify`):
```python
@app.get("/api/attest")
async def api_attest(since_seq: int = Query(default=0, ge=0)) -> JSONResponse:
    if use_mock or ledger is None:
        entries = [_mock_attest_entry() for _ in range(min(10, 50))]
    else:
        entries = [e.model_dump() for e in ledger.iter_events(since_seq=since_seq)][:50]
    return JSONResponse(content={"entries": entries, "ts": time.time()})
```

**New `POST /api/attest/verify` endpoint — copy this shape:**
```python
@app.post("/api/attest/verify")
async def api_attest_verify() -> JSONResponse:
    if use_mock or ledger is None:
        return JSONResponse(content={"valid": True, "total": 0, "reason": "mock"})
    result = ledger.verify()   # returns VerifyResult(valid, total, first_bad_seq, reason)
    return JSONResponse(content=result.model_dump())
```

**New `GET /api/vet-intake/{intake_id}` endpoint — copy FileResponse pattern (lines 210–216):**
```python
@app.get("/api/vet-intake/{intake_id}")
async def api_vet_intake(intake_id: str) -> Response:
    from skyherd.server.vet_intake import get_intake_path
    path = get_intake_path(intake_id)
    if not path.exists():
        return JSONResponse(content={"error": "not found"}, status_code=404)
    return Response(content=path.read_text(encoding="utf-8"), media_type="text/markdown")
```

**Error handling pattern** (lines 113–120 — optional module pattern):
```python
try:
    from skyherd.agents.webhook import webhook_router, set_mesh as _set_webhook_mesh
    app.include_router(webhook_router)
    ...
except Exception as exc:  # noqa: BLE001
    logger.warning("Webhook router not mounted: %s", exc)
```

---

### `src/skyherd/server/cli.py` — Add `--live` flag

**Analog:** `src/skyherd/server/cli.py` (lines 14–35)

**Full existing pattern** (lines 1–43):
```python
"""skyherd-server CLI — typer entry point."""

from __future__ import annotations

import logging
import os

import typer
import uvicorn

app = typer.Typer(name="skyherd-server", help="SkyHerd dashboard server")

@app.command()
def start(
    port: int = typer.Option(8000, "--port", "-p", help="HTTP port"),
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host"),
    mock: bool = typer.Option(
        True, "--mock/--no-mock", help="Use mock data (no live sim required)"
    ),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code change"),
    log_level: str = typer.Option("info", "--log-level"),
) -> None:
    """Start the SkyHerd FastAPI dashboard server."""
    if mock:
        os.environ["SKYHERD_MOCK"] = "1"
    logging.basicConfig(level=log_level.upper())
    typer.echo(f"Starting SkyHerd server on {host}:{port} (mock={mock})")
    uvicorn.run(
        "skyherd.server.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )
```

**New `run_live()` command to add — follows same `@app.command()` decorator pattern:**
```python
@app.command("live")
def start_live(
    port: int = typer.Option(8000, "--port", "-p"),
    host: str = typer.Option("0.0.0.0", "--host"),
    log_level: str = typer.Option("info", "--log-level"),
) -> None:
    """Start with real World + AgentMesh + Ledger (requires ANTHROPIC_API_KEY)."""
    import asyncio
    from skyherd.attest.ledger import Ledger
    from skyherd.attest.signer import Signer
    from skyherd.agents.mesh import AgentMesh
    from skyherd.world.sim import make_world
    from skyherd.server.app import create_app

    logging.basicConfig(level=log_level.upper())
    signer = Signer.from_file(os.environ["SKYHERD_SIGNER_KEY_PATH"])
    ledger = Ledger.open("runtime/attest.db", signer)
    world = make_world(config_path="worlds/ranch_a.yaml", seed=42)
    mesh = AgentMesh(world=world, ledger=ledger)
    app = create_app(mock=False, mesh=mesh, ledger=ledger, world=world)
    uvicorn.run(app, host=host, port=port, log_level=log_level)
```

---

### `src/skyherd/server/vet_intake.py` — NEW: drafter + schema + file I/O

**Analog:** `src/skyherd/mcp/rancher_mcp.py` (file-write pattern, lines 59–63; Pydantic model pattern)

**File-write helper pattern** (rancher_mcp.py lines 59–63):
```python
def _write_log(record: dict[str, Any]) -> None:
    """Append *record* to PAGES_FILE as a JSON line."""
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with _PAGES_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
```

**New module — copy this shape:**
```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

_VET_INTAKE_DIR = Path("runtime/vet_intake")

class VetIntakeRecord(BaseModel):
    id: str           # e.g. "A014_20260422T153200Z"
    cow_tag: str
    ts_iso: str
    severity: str     # "log" | "observe" | "escalate"
    symptoms: list[str]
    disease_flags: list[str]
    recommended_action: str
    herd_context: str
    path: str         # relative path to .md artifact

def draft_vet_intake(
    cow_tag: str,
    severity: str,
    symptoms: list[str],
    disease_flags: list[str],
    herd_context: str,
) -> VetIntakeRecord:
    """Write a rancher-readable markdown vet-intake packet to runtime/vet_intake/."""
    ts = datetime.now(UTC)
    ts_str = ts.strftime("%Y%m%dT%H%M%SZ")
    intake_id = f"{cow_tag}_{ts_str}"
    _VET_INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    md_path = _VET_INTAKE_DIR / f"{intake_id}.md"
    # ... render markdown and write to md_path ...
    return VetIntakeRecord(
        id=intake_id,
        cow_tag=cow_tag,
        ts_iso=ts.isoformat(),
        severity=severity,
        symptoms=symptoms,
        disease_flags=disease_flags,
        recommended_action="...",
        herd_context=herd_context,
        path=str(md_path),
    )

def get_intake_path(intake_id: str) -> Path:
    return _VET_INTAKE_DIR / f"{intake_id}.md"
```

**Constants/runtime dir pattern** (rancher_mcp.py lines 23–27):
```python
_RUNTIME_DIR = Path("runtime")
_PAGES_FILE = _RUNTIME_DIR / "rancher_pages.jsonl"
_PREFS_FILE = _RUNTIME_DIR / "rancher_prefs.json"
```

---

### `src/skyherd/server/events.py` — Harden `_real_cost_tick`; add `vet_intake.drafted` broadcast

**Analog:** `src/skyherd/server/events.py` (self — existing `_broadcast`, lines 305–315)

**`_broadcast` pattern** (lines 305–315 — reuse for `vet_intake.drafted`, do NOT create new loop):
```python
def _broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
    for q in self._subscribers:
        try:
            q.put_nowait((event_type, payload))
        except asyncio.QueueFull:
            # Slow consumer — drop oldest, put newest
            try:
                q.get_nowait()
                q.put_nowait((event_type, payload))
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass
```

**`_real_cost_tick` existing pattern** (lines 347–377 — the uncovered branch to test):
```python
def _real_cost_tick(self) -> dict[str, Any]:
    """Aggregate cost tickers from a live AgentMesh."""
    agents = []
    all_idle = True
    total_cost = 0.0
    for name, session in self._mesh._sessions.items():
        ticker = self._mesh._session_manager._tickers.get(session.id)
        if ticker is None:
            continue
        state = ticker._current_state
        if state == "active":
            all_idle = False
        agents.append({
            "name": name,
            "state": state,
            "cost_delta_usd": 0.0,
            "cumulative_cost_usd": round(ticker.cumulative_cost_usd, 6),
            "tokens_in": ticker._cumulative_tokens_in,
            "tokens_out": ticker._cumulative_tokens_out,
        })
        total_cost += ticker.cumulative_cost_usd
    return {
        "ts": time.time(),
        "seq": self._cost_seq,
        "agents": agents,
        "all_idle": all_idle,
        "rate_per_hr_usd": 0.0 if all_idle else 0.08,
        "total_cumulative_usd": round(total_cost, 6),
    }
```

**`_attest_loop` live branch pattern** (lines 379–394 — currently uncovered, extend test to hit):
```python
async def _attest_loop(self) -> None:
    last_seq = 0
    while not self._stop_event.is_set():
        try:
            if self._mock or self._ledger is None:
                if self._cost_seq % 3 == 0:
                    entry = _mock_attest_entry()
                    self._broadcast("attest.append", entry)
            else:
                for event in self._ledger.iter_events(since_seq=last_seq):
                    self._broadcast("attest.append", event.model_dump())
                    last_seq = event.seq
        except Exception as exc:  # noqa: BLE001
            logger.debug("attest loop error: %s", exc)
        await asyncio.sleep(ATTEST_POLL_INTERVAL_S)
```

---

### `src/skyherd/agents/herd_health_watcher.py` — Add `draft_vet_intake` step

**Analog:** `src/skyherd/agents/herd_health_watcher.py` (self — skill loading pattern, lines 28–61)

**AgentSpec pattern** (lines 33–61 — spec definition with skills list):
```python
HERD_HEALTH_WATCHER_SPEC = AgentSpec(
    name="HerdHealthWatcher",
    system_prompt_template_path="src/skyherd/agents/prompts/herd_health_watcher.md",
    wake_topics=["skyherd/+/trough_cam/+"],
    mcp_servers=["sensor_mcp", "rancher_mcp", "galileo_mcp"],
    skills=[
        _skill("cattle-behavior/disease/pinkeye.md"),
        # ... all 7 disease heads ...
        _skill("ranch-ops/human-in-loop-etiquette.md"),
    ],
    ...
)
```

**Pattern for calling `draft_vet_intake` in handler flow:** After `classify_pipeline` resolves with `severity >= "escalate"`, import and invoke `draft_vet_intake` from `skyherd.server.vet_intake`, then emit the `vet_intake.drafted` event via the broadcaster. The tool-call record goes into `all_tool_calls` so `sick_cow.py` assertions can find it by name `"draft_vet_intake"`.

---

### `src/skyherd/scenarios/sick_cow.py` — Add vet-intake artifact assertion

**Analog:** `src/skyherd/scenarios/sick_cow.py` (self — existing `assert_outcome` pattern, lines 90–124)

**Existing assertion pattern** (lines 110–118 — copy shape for new assertions):
```python
all_tools = self._all_tool_calls(mesh)
tool_names = {c.get("tool") for c in all_tools}

assert "classify_pipeline" in tool_names, (
    f"Expected classify_pipeline tool call. Got: {tool_names}"
)
assert "page_rancher" in tool_names, (
    f"Expected page_rancher tool call after pinkeye detection. Got: {tool_names}"
)
```

**New assertions to add** (copy exact same pattern):
```python
assert "draft_vet_intake" in tool_names, (
    f"Expected draft_vet_intake tool call. Got: {tool_names}"
)
# Assert artifact on disk
from pathlib import Path
intake_files = list(Path("runtime/vet_intake").glob("A014_*.md"))
assert len(intake_files) >= 1, "Expected runtime/vet_intake/A014_*.md to exist"
content = intake_files[0].read_text(encoding="utf-8")
assert "pinkeye" in content.lower(), "Expected vet-intake artifact to mention pinkeye"
```

---

### `web/src/components/VetIntakePanel.tsx` — NEW modal component

**Analog:** `web/src/components/AttestationPanel.tsx` (collapsible panel + fetch + SSE registration)

**Imports pattern** (AttestationPanel.tsx lines 1–9):
```typescript
import { useState, useEffect, useCallback, Fragment } from "react";
import { cn } from "@/lib/cn";
import { getSSE } from "@/lib/sse";
```

**SSE registration + one-shot fetch pattern** (AttestationPanel.tsx lines 66–89):
```typescript
const handleAppend = useCallback((entry: LedgerEntry) => {
  setEntries((prev) => [...prev, entry].slice(-MAX_ENTRIES));
}, []);

useEffect(() => {
  const sse = getSSE();
  sse.on("attest.append", handleAppend);
  fetch("/api/attest")
    .then((r) => r.json())
    .then((data) => { /* merge & dedupe */ })
    .catch(() => {});
  return () => sse.off("attest.append", handleAppend);
}, [handleAppend]);
```

**For VetIntakePanel — register on `"vet_intake.drafted"` event (same pattern):**
```typescript
useEffect(() => {
  const sse = getSSE();
  sse.on("vet_intake.drafted", handleDrafted);
  return () => sse.off("vet_intake.drafted", handleDrafted);
}, [handleDrafted]);
```

**Chip/state style pattern** (AttestationPanel.tsx lines 24–31 + AgentLane.tsx lines 92–99):
```typescript
// Severity chip — map to existing chip-* classes
const SEVERITY_CHIP: Record<string, string> = {
  escalate: "chip-danger",   // or "chip-thermal" (red family)
  observe:  "chip-warn",
  log:      "chip-muted",
};
<span className={cn("chip", SEVERITY_CHIP[severity] ?? "chip-muted")}>{severity}</span>
```

**Inline markdown renderer — 20 lines, no dependency:**
```typescript
function renderMarkdown(md: string): string {
  return md
    .replace(/^# (.+)$/gm, "<h2>$1</h2>")
    .replace(/^## (.+)$/gm, "<h3>$1</h3>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>")
    .replace(/\n{2,}/g, "<br><br>");
}
// Usage: <div dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }} />
```

**Panel container style pattern** (AttestationPanel.tsx lines 95–104 — use same tokens):
```typescript
<section
  className="shrink-0 rounded border flex flex-col overflow-hidden transition-all duration-240"
  style={{
    backgroundColor: "var(--color-bg-1)",
    borderColor: "var(--color-line)",
  }}
  aria-label="Vet intake packet"
>
```

---

### `web/src/components/CostTicker.tsx` — Polish "paused" state

**Analog:** `web/src/components/CostTicker.tsx` (self — existing `allIdle` branch, lines 110–143)

**Existing paused chip** (lines 136–143 — this is the chip; add dim/grayscale to the cumulative number):
```typescript
<span className={cn("chip", allIdle ? "chip-muted" : "chip-sage")}>
  {allIdle ? (
    <><span className="h-1.5 w-1.5 rounded-full bg-[var(--color-text-2)] shrink-0" />PAUSED (idle)</>
  ) : (
    <><span className="h-1.5 w-1.5 rounded-full bg-[rgb(148_176_136)] pulse-dot shrink-0" />${rateUsd.toFixed(2)}/hr</>
  )}
</span>
```

**Framer-motion spring pattern already in file** (lines 69–91 — reuse `useSpring/useTransform`):
```typescript
function AnimatedCost({ value }: { value: number }) {
  const spring = useSpring(value, { stiffness: 60, damping: 20 });
  const display = useTransform(spring, (v) => `$${v.toFixed(6)}`);
  useEffect(() => { spring.set(value); }, [value, spring]);
  return (
    <motion.span
      className="tabnum"
      style={{ fontFamily: "var(--font-mono)", ... }}
    >
      {display}
    </motion.span>
  );
}
```

**Polish target — add `opacity` + `filter` to `AnimatedCost` wrapper when idle:**
```typescript
<motion.span
  animate={{ opacity: allIdle ? 0.4 : 1, filter: allIdle ? "grayscale(1)" : "grayscale(0)" }}
  transition={{ duration: 0.4 }}
>
  <AnimatedCost value={totalCost} />
</motion.span>
```

**Agent chip strip fade pattern** (lines 172–208 — agent state drives color inline; add opacity transition):
```typescript
// Add to each agent card:
style={{
  opacity: allIdle ? 0.45 : 1,
  transition: "opacity 0.4s ease",
  backgroundColor: a.state === "active" ? "rgb(148 176 136 / 0.08)" : "var(--color-bg-2)",
  ...
}}
```

---

### `web/src/components/AttestationPanel.tsx` — Add "Verify Chain" button

**Analog:** `web/src/components/AttestationPanel.tsx` (self — header section, lines 106–132)

**Header button pattern** (lines 106–132 — extend with second button inline):
```typescript
<button
  className="flex items-center justify-between px-3 py-2 shrink-0 border-b w-full text-left"
  style={{ borderColor: "var(--color-line)", background: "transparent" }}
  onClick={onToggle}
  aria-expanded={!collapsed}
>
  <span ...>Attestation Chain</span>
  <div className="flex items-center gap-2">
    <span className="chip chip-muted tabnum">{entries.length} entries</span>
    <span ...>{collapsed ? "▲" : "▼"}</span>
  </div>
</button>
```

**New verify button and state** (add alongside header — fetch pattern from fetch in lines 69–87):
```typescript
const [verifying, setVerifying] = useState(false);
const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null);

const handleVerify = useCallback(() => {
  setVerifying(true);
  fetch("/api/attest/verify", { method: "POST" })
    .then((r) => r.json())
    .then((data: VerifyResult) => setVerifyResult(data))
    .catch(() => setVerifyResult(null))
    .finally(() => setVerifying(false));
}, []);

// Button inside header div:
<button
  className={cn("chip", verifyResult?.valid ? "chip-sage" : verifyResult ? "chip-danger" : "chip-muted")}
  onClick={(e) => { e.stopPropagation(); handleVerify(); }}
  disabled={verifying}
  aria-label="Verify attestation chain"
>
  {verifying ? "…" : verifyResult ? (verifyResult.valid ? "VALID" : "INVALID") : "Verify"}
</button>
```

---

### `web/src/components/RanchMap.tsx` — Predator ring RAF-alpha smoothing

**Analog:** `web/src/components/RanchMap.tsx` (self — drone trail alpha decay, lines 258–266; predator ring, lines 289–308)

**Existing drone trail alpha decay** (lines 258–266 — this is the working pattern to mirror for predator rings):
```typescript
const trail = droneTrailRef.current;
for (let i = 1; i < trail.length; i++) {
  const alpha = (i / trail.length) * 0.5;
  ctx.beginPath();
  ctx.moveTo(px(trail[i - 1][0]), py(trail[i - 1][1]));
  ctx.lineTo(px(trail[i][0]), py(trail[i][1]));
  ctx.strokeStyle = `rgba(120,180,220,${alpha})`;
  ctx.lineWidth = 1.5;
  ctx.stroke();
}
```

**Current static predator ring** (lines 295–299 — this is what changes):
```typescript
// Pulsing threat ring (CSS animation handles the pulse; here we just draw a static ring)
ctx.beginPath();
ctx.arc(ppx, ppy, xSize * 1.8, 0, Math.PI * 2);
ctx.strokeStyle = "rgba(224,100,90,0.25)";
ctx.lineWidth = 1;
ctx.stroke();
```

**New RAF-interpolated alpha pattern** (add `predatorPhaseRef` similar to `droneTrailRef`):
```typescript
const predatorPhaseRef = useRef<Map<string, number>>(new Map());

// In RAF draw loop, per predator:
const now = performance.now() / 1000;
const phase = predatorPhaseRef.current.get(pred.id) ?? Math.random();
predatorPhaseRef.current.set(pred.id, phase);
const ringAlpha = 0.1 + 0.2 * Math.abs(Math.sin((now + phase) * Math.PI / 1.8));
ctx.beginPath();
ctx.arc(ppx, ppy, xSize * 1.8, 0, Math.PI * 2);
ctx.strokeStyle = `rgba(224,100,90,${ringAlpha})`;
ctx.lineWidth = 1;
ctx.stroke();
```

**Code-split target:** Wrap `RanchMap` export in `React.lazy()` at its import site in `App.tsx` / the layout component. The `RanchMap.tsx` file itself is unchanged — the split is in the import.

---

### `web/src/lib/sse.ts` — Add `vet_intake.drafted` event type

**Analog:** `web/src/lib/sse.ts` (self — event type registration array, lines 69–76)

**Existing event type registration** (lines 69–76):
```typescript
const eventTypes = [
  "world.snapshot",
  "cost.tick",
  "attest.append",
  "agent.log",
  "fence.breach",
  "drone.update",
];
```

**Add one entry — exact same pattern:**
```typescript
const eventTypes = [
  "world.snapshot",
  "cost.tick",
  "attest.append",
  "agent.log",
  "fence.breach",
  "drone.update",
  "vet_intake.drafted",   // NEW — Phase 5
];
```

---

### `web/index.html` — Add font preload links

**Analog:** `web/index.html` (self — existing `<head>`, lines 1–18)

**Current head** (lines 1–13 — add `<link rel="preload">` before closing `</head>`):
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/skyherd-icon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#0a0c10" />
    <link rel="manifest" href="/manifest.json" />
    <title>SkyHerd — Ranch Intelligence Platform</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
  </head>
```

**New preload hints to add** (Lighthouse font pattern — add inside `<head>` after manifest):
```html
<!-- Preload above-the-fold variable fonts -->
<link rel="preload" as="font" type="font/woff2"
      href="/assets/fraunces-variable.woff2" crossorigin="anonymous" />
<link rel="preload" as="font" type="font/woff2"
      href="/assets/inter-variable.woff2" crossorigin="anonymous" />
```

Note: Exact hashed filenames from `web/dist/assets/` must be used. If fonts are inlined by Vite, this step is unnecessary — verify during execution.

---

### `web/vite.config.ts` — Add `manualChunks` for code splitting

**Analog:** `web/vite.config.ts` (self — existing `build` section, lines 35–38)

**Current build config** (lines 35–38):
```typescript
build: {
  outDir: "dist",
  sourcemap: false,
},
```

**Extended with `manualChunks`:**
```typescript
build: {
  outDir: "dist",
  sourcemap: false,
  rollupOptions: {
    output: {
      manualChunks: {
        // Split heavy canvas/viz components from critical path
        "ranch-map": ["./src/components/RanchMap.tsx"],
        "cross-ranch": ["./src/components/CrossRanchView.tsx"],
      },
    },
  },
},
```

---

### `.github/workflows/lighthouse.yml` — NEW Lighthouse CI job

**Analog:** `.github/workflows/ci.yml` (existing `web` job, lines 57–86)

**Web job pattern to copy** (ci.yml lines 57–86):
```yaml
web:
  name: Web (pnpm build + test)
  runs-on: ubuntu-latest
  defaults:
    run:
      working-directory: web

  steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Setup Node
      uses: actions/setup-node@v4
      with:
        node-version: "20"

    - name: Setup pnpm
      uses: pnpm/action-setup@v4
      with:
        version: 9

    - name: Install dependencies
      run: pnpm install

    - name: Build
      run: pnpm run build

    - name: Test
      run: pnpm test -- --run
```

**New `lighthouse.yml` shape — extend the web pattern:**
```yaml
name: Lighthouse CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

jobs:
  lighthouse:
    name: Lighthouse ≥90
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - uses: pnpm/action-setup@v4
        with:
          version: 9

      - name: Install dependencies
        run: pnpm install

      - name: Build SPA
        run: pnpm run build

      - name: Install @lhci/cli
        run: pnpm add -D @lhci/cli

      - name: Run Lighthouse CI
        run: pnpm exec lhci autorun
        # Requires .lighthouserc.json or lighthouserc.js in web/
        # with assert: { assertions: { "categories:performance": ["error", { minScore: 0.9 }] } }
```

---

### Test coverage files (live-path 73% → ≥85%)

**Analog:** `tests/server/test_app_coverage.py` (MagicMock injection pattern, lines 1–75)

**Fixture pattern to extend** (lines 42–75 — copy `_make_mock_mesh` with `_tickers` for `_real_cost_tick`):
```python
def _make_mock_mesh() -> MagicMock:
    mesh = MagicMock()
    sessions: dict[str, Any] = {}
    for name in AGENT_NAMES:
        session = MagicMock()
        session.state = "active"
        session.last_active_ts = time.time()
        session.cumulative_tokens_in = 1000
        session.cumulative_tokens_out = 400
        session.cumulative_cost_usd = 0.002
        sessions[name] = session
    mesh._sessions = sessions
    return mesh
```

**Extended fixture for `_real_cost_tick` coverage** (add `_session_manager._tickers`):
```python
def _make_mock_mesh_with_tickers() -> MagicMock:
    mesh = _make_mock_mesh()
    tickers = {}
    sm = MagicMock()
    for name, session in mesh._sessions.items():
        ticker = MagicMock()
        ticker._current_state = "active"
        ticker.cumulative_cost_usd = 0.002
        ticker._cumulative_tokens_in = 1000
        ticker._cumulative_tokens_out = 400
        tickers[session.id] = ticker
    sm._tickers = tickers
    mesh._session_manager = sm
    return mesh
```

**AsyncClient + ASGITransport test pattern** (test_app_coverage.py lines 78–85):
```python
@pytest_asyncio.fixture
async def live_client(live_app):
    async with AsyncClient(
        transport=ASGITransport(app=live_app),
        base_url="http://test",
    ) as client:
        yield client
```

---

## Shared Patterns

### Design Token System
**Source:** `web/src/index.css` (`@theme` block) + all components
**Apply to:** `VetIntakePanel.tsx`, `CostTicker.tsx` polish, `AttestationPanel.tsx` additions

Standard color tokens used throughout (copy from any component):
```typescript
// Background tiers
"var(--color-bg-0)"       // darkest
"var(--color-bg-1)"       // card background
"var(--color-bg-2)"       // hover/expanded

// Text hierarchy
"var(--color-text-0)"     // primary
"var(--color-text-1)"     // secondary
"var(--color-text-2)"     // tertiary / timestamps

// Accent colors
"var(--color-accent-sage)"  // rgb(148 176 136) — active/healthy
"var(--color-accent-sky)"   // blue — info
"var(--color-warn)"         // orange — observe
"var(--color-danger)"       // red — escalate/error
"var(--color-line)"         // border dividers

// Fonts
"var(--font-display)"    // Fraunces (headings/labels)
"var(--font-mono)"       // JetBrains Mono (data/hashes/numbers)
```

### Chip Class System
**Source:** `web/src/index.css` (chip variants) — used in every component
**Apply to:** `VetIntakePanel.tsx` severity chip, `AttestationPanel.tsx` verify button
```typescript
// Base: className="chip"
// Variants (append one):
"chip-sage"     // green active state
"chip-muted"    // gray idle state
"chip-sky"      // blue info
"chip-thermal"  // orange/red alert
"chip-warn"     // yellow/orange warning
"chip-danger"   // red critical
"chip-dust"     // neutral dust color
```

### CSS Animation Keyframes
**Source:** `web/src/index.css` lines 198–214
**Apply to:** `AgentLane.tsx` entry, `CostTicker.tsx` pulse, `VetIntakePanel.tsx` mount animation

Existing keyframes (already in `index.css`, reference by class name):
- `log-enter` — 240ms ease-out slide-in for new log rows (already on `AgentLane.tsx` log `<div>`)
- `pulse-dot` — breathing pulse for active status dots (already on `CostTicker.tsx` active chip)
- `threat-ring` — 1.8s ease-out for predator ring CSS path (superseded by RAF in Phase 5)
- `fence-pulse` — fence breach flash
- `phone-ring` — rancher phone notification ring

Standard timing idiom (use consistently): `animation-duration: 240ms; animation-timing-function: cubic-bezier(0.33,1,0.68,1)` (easeOutCubic).

### FastAPI Endpoint Pattern
**Source:** `src/skyherd/server/app.py` lines 134–156
**Apply to:** `/api/attest/verify`, `/api/vet-intake/{id}` (both new endpoints)

All endpoints follow mock/live branch:
```python
@app.get("/api/<resource>")
async def api_<resource>(...) -> JSONResponse:
    if use_mock or dependency is None:
        data = _mock_<resource>()
    else:
        data = dependency.real_method(...)
    return JSONResponse(content={"data": data, "ts": time.time()})
```

### SSE Subscription Pattern (React)
**Source:** `web/src/components/AttestationPanel.tsx` lines 66–89; `CostTicker.tsx` lines 104–108
**Apply to:** `VetIntakePanel.tsx` (new); any future component subscribing to events

```typescript
useEffect(() => {
  const sse = getSSE();
  sse.on("<event_type>", handler);
  return () => sse.off("<event_type>", handler);
}, [handler]);  // handler must be useCallback-wrapped
```

### Python Error Handling (module-optional imports)
**Source:** `src/skyherd/server/app.py` lines 113–120
**Apply to:** `server/cli.py` live bootstrap, `vet_intake.py` integration
```python
try:
    from <optional_module> import <thing>
    <use it>
    logger.info("Mounted X at /path")
except Exception as exc:  # noqa: BLE001
    logger.warning("X not mounted: %s", exc)
```

---

## No Analog Found

All files have close analogs. No files require falling back to RESEARCH.md patterns exclusively.

| File | Note |
|------|------|
| `web/src/components/VetIntakePanel.tsx` | Novel component type but `AttestationPanel.tsx` is a strong role-match (SSE + fetch + modal panel). Inline markdown renderer is 20 lines with no precedent — invent inline per RESEARCH.md guidance. |
| `runtime/vet_intake/` | Directory with no precedent — `runtime/rancher_pages.jsonl` from `rancher_mcp.py` is the closest precedent for the runtime artifact pattern. |

---

## Metadata

**Analog search scope:** `src/skyherd/server/`, `src/skyherd/mcp/`, `src/skyherd/agents/`, `src/skyherd/attest/`, `src/skyherd/scenarios/`, `web/src/components/`, `web/src/lib/`, `web/`, `.github/workflows/`
**Files scanned:** 22 source files read; 14 files used as primary analogs
**Pattern extraction date:** 2026-04-22
