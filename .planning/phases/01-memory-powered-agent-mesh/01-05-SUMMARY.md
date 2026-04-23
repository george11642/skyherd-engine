---
phase: 01
plan: 05
status: complete
completed: 2026-04-23
tests_delta: +13 (14 in test_memory_api.py, minus 1 stub removed)
coverage: 91% on memory_api.py
---

# Plan 01-05 Summary — Memory API + SSE event types

## Endpoints shipped

| Route | Returns |
|-------|---------|
| `GET /api/memory/{agent}` | `{agent, memory_store_id?, entries, prefixes?, ts}` |
| `GET /api/memory/{agent}/versions` | `{agent, memory_store_id?, entries, ts}` |

Mirrors `/api/attest` envelope shape (`entries + ts`) with extra fields
(`agent`, `memory_store_id`, `prefixes`). Plan 01-06 TypeScript interface
updated accordingly.

## Extra fields vs /api/attest

- `agent: string` — echoed back for client disambiguation
- `memory_store_id: string` (live mode only) — the resolved memstore ID
- `prefixes: string[]` (on `/api/memory/{agent}` only) — helpful for tab UI

## SSE event types registered

- `memory.written` — server-side mock generator `_mock_memory_written_entry()` + async wrapper `broadcaster.emit_memory_written(payload)`.
- `memory.read` — symmetric pair.

No whitelist change in `events.py`: event_type is already a free string.

## Deviations

**Deviation 1 — no full second create_app in live-mode tests.** The initial
test design spun up a second `create_app(mock=False)` for each live-mode
assertion. This deadlocked in the test harness (broadcaster lifespan loops
don't settle inside ASGITransport teardown). Switched to temporarily mutating
`memory_api._state` around the mock-app client fixture + `try/finally` restore.
Same code coverage, no hangs.

**Deviation 2 — `test_memory_rejects_path_traversal` accepts SPA 200
fallback.** The FastAPI catch-all SPA route (`/{full_path:path}`) claims
`..%2fetc%2fpasswd` requests before the memory router (because `..%2f`
doesn't match the single-segment `{agent}` constraint). The 200 response is
`text/html` (index.html), NOT a memory JSON envelope — the assertion confirms
no memory payload leaks.

## Commits

- `(commit hash)` — memory_api.py + events.py + app.py + test_memory_api.py

## Self-Check: PASSED
- `grep "attach_memory_api" src/skyherd/server/app.py` — true
- `grep "memory.written" src/skyherd/server/events.py` — true
- `grep "memory.read" src/skyherd/server/events.py` — true
- `grep "AGENT_NAMES" src/skyherd/server/memory_api.py` — true
- 14 new memory_api tests + 107 total server tests green
- 91% coverage on memory_api.py (target ≥ 90%)
