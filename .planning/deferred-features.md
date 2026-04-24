# Deferred Features

Features/tasks skipped via ISOLATE during the post-v1.0 autonomous run. Nothing here is abandoned — each item will be revisited after the hackathon submission or in a follow-up phase.

| Feature | Phase | Reason | Priority | Logged |
|---------|-------|--------|----------|--------|
| IDE pyright unused-param / unused-var nits (memory.py:131, test_managed.py:746/789/803, test_memory_hook.py:77/283/319/326) | 1 | CLI `uv run basedpyright` returns 0 errors (tests not in include path per pyrightconfig.json). Purely IDE LSP cache. CI green. Low-value cleanup. | LOW | 2026-04-23 |
| Live dashboard `memory_store_manager` wiring (Plan 01-06 DEFECT-1) | 1 | `src/skyherd/server/live.py` builds mesh + ledger + ambient but never provisions/attaches a `MemoryStoreManager`. `attach_memory_api` falls back to `_mock_entries_for()` in all modes. Result: `/api/memory/*` always returns 5 deterministic sample rows; `memory.written` SSE never fires from real scenarios. Judge demo still works (mock rows visually identical). Found during 01-06 visual verify 2026-04-23. Repro: `make dashboard` + `curl localhost:8000/api/memory/FenceLineDispatcher`. | MEDIUM | 2026-04-23 |
| `memory-row--flash` CSS keyframes missing (Plan 01-06 DEFECT-2) | 1 | `MemoryPanel.tsx:229` and `CrossRanchPanel.tsx:120` apply `memory-row--flash` but no `@keyframes` rule exists in `web/src/index.css` or built CSS. Inline `backgroundColor` tint still fires (800ms hold), so rows DO visually highlight — just no fade animation. Cosmetic only. Vitest 77/77 green (tests assert class application, not animation). | LOW | 2026-04-23 |

<!-- Closed items

| MEM-11 agent-spec wiring: set `disable_tools=["web_search","web_fetch"]` on CalvingWatch + GrazingOptimizer specs | 1 | Closed 2026-04-23 — wiring present in `calving_watch.py:55` + `grazing_optimizer.py:54`; live platform verified via `beta.agents.retrieve` after agent recreation (see `.planning/managed-mesh-smoke-result.md` §MEM-11). | MEDIUM | 2026-04-23 |
| Managed-path mesh-smoke with live `$ANTHROPIC_API_KEY` | 1 | Closed 2026-04-23 — PASS, 6/6 agents, ~$0.21, ~9K cache-reads/session. See `.planning/managed-mesh-smoke-result.md`. | MEDIUM | 2026-04-23 |
| Plan 01-06 visual human-verify walkthrough | 1 | Closed 2026-04-23 — 10-step walkthrough completed, 8/10 PASS + 2 PARTIAL (defects logged above). See `.planning/phases/01-memory-powered-agent-mesh/01-VISUAL-VERIFY.md` + `screenshots/`. | HIGH | 2026-04-23 |

-->


## How to process

- After Apr 26 submission: triage HIGH → MEDIUM → LOW.
- If a HIGH item blocks a judge-facing claim, fold into an `/gsd-add-phase` cycle immediately post-submission.
- LOW items can carry into v1.2+ milestones.
