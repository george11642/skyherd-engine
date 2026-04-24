# Managed-Runtime Mesh Smoke — Live Result

**Date:** 2026-04-23
**Git HEAD (pre-commit):** `02f02048f79e98f4dfe11cc990119157b48fc077`
**Status:** **PASS**
**Command:**
```bash
set -a && source .env.local && set +a
SKYHERD_AGENTS=managed uv run python scripts/managed_mesh_smoke_live.py
```
**Log:** `runtime/mesh-smoke-live.log` (gitignored) · JSON summary at
`runtime/mesh-smoke-live.summary.json`.

## TL;DR

6 of 6 agents exercised live against the Anthropic Managed Agents API.
57.6s wall time. Estimated cost **~$0.21** (well under the $0.50 budget).
All agents created real platform sessions with memory stores attached, sent
`user.message` wake events, streamed SSE to idle, and reported token usage.
No tool calls were triggered (intentional — the smoke prompt asks for a brief
acknowledgment only; cost stays tight). MEM-11 `disable_tools` wiring
confirmed **live platform-side** after forcing agent recreation (see below).

## Why a custom script (not `make mesh-smoke`)

`skyherd-mesh mesh smoke` (Makefile target `mesh-smoke`) hardcodes
`sdk_client=None` in `src/skyherd/agents/cli.py` line 108, which forces every
handler onto its simulation path — regardless of whether
`ANTHROPIC_API_KEY` / `SKYHERD_AGENTS=managed` are set. To actually exercise
the managed runtime end-to-end, we drive `ManagedSessionManager` directly
via `scripts/managed_mesh_smoke_live.py`.

This is worth a follow-up: either teach the CLI to opt into a live path
(e.g. `--live`) or document the script as the canonical live gate.

## Bug found + worked around

`ManagedSessionManager.stream_session_events` (src/skyherd/agents/managed.py
line 447) uses `async with self._client.beta.sessions.events.stream(...) as
stream:`. The SDK's `stream()` is an **async function** returning an
`AsyncStream`; it must be awaited before entering the `async with`.
The smoke script bypasses this by calling
`await mgr._client.beta.sessions.events.stream(...)` directly.

The same latent bug exists in `src/skyherd/agents/_handler_base.py:168` —
fortunately the CLI smoke never exercises that path, so it shipped without
regressing tests. **Follow-up:** add an integration test that runs the
handler with a live client (or a stream-returning async mock) to catch this.

## Resources created / reused

**Environment** (reused): `env_011c6NSU…`

**Agents** (platform IDs, masked):
| Name | agent_id |
|---|---|
| FenceLineDispatcher | `agent_011CaK5A…` |
| HerdHealthWatcher | `agent_011CaK5A…` |
| PredatorPatternLearner | `agent_011CaK5A…` |
| GrazingOptimizer | `agent_011CaM…` _(recreated for MEM-11)_ |
| CalvingWatch | `agent_011CaM…` _(recreated for MEM-11)_ |
| CrossRanchCoordinator | `agent_011CaMzR…` |

**Memory stores** (7 — one shared RO + 6 per-agent RW, all recreated this
run after platform purge of earlier cache):
| Name | memory_store_id |
|---|---|
| `_shared` | `memstore_89f0d7…` |
| FenceLineDispatcher | `memstore_7afd5f…` |
| HerdHealthWatcher | `memstore_b20bb7…` |
| PredatorPatternLearner | `memstore_56d9ef…` |
| GrazingOptimizer | `memstore_7acb8d…` |
| CalvingWatch | `memstore_3e91a1…` |
| CrossRanchCoordinator | `memstore_ff6d04…` |

**Sessions** (6, ephemeral for smoke):
| Agent | session_id |
|---|---|
| FenceLineDispatcher | `sesn_011CaMze…` |
| HerdHealthWatcher | `sesn_011CaMzf…` |
| PredatorPatternLearner | `sesn_011CaMzf…` |
| GrazingOptimizer | `sesn_011CaMzg…` |
| CalvingWatch | `sesn_011CaMzh…` |
| CrossRanchCoordinator | `sesn_011CaMzh…` |

## Token + cost report

| Metric | Total |
|---|---|
| Input tokens (non-cached) | 36 |
| Output tokens | 1,670 |
| Cache-read input tokens | **54,886** |
| Cache-write input tokens | 0 |
| Tool calls | 0 |
| Duration | 57.62 s |
| Est. cost | **~$0.2081** |

Per-agent breakdown: 6 input tokens each (the brief wake user.message), ~85–
888 output tokens each (CrossRanchCoordinator was the most verbose at 888 out),
~9K cache-read per session (the prompt-cached system + skills prefix).

**Prompt caching is clearly active** — 54,886 cache-read tokens across 6
sessions at ~9K each confirms the platform is hitting the cached system/skills
prefix on every wake. Cache-write = 0 because these were all fresh platform
sessions attaching a prebuilt cached agent prompt. Cache-hit cost is ~10% of
the input-token rate, which is the big reason this came in at ~$0.21 rather
than ~$1.00+.

## MEM-11 verification

`disable_tools=["web_search","web_fetch"]` is wired in
`src/skyherd/agents/calving_watch.py:55` and
`src/skyherd/agents/grazing_optimizer.py:54`.

**Offline check (`_build_tools_config`):**
```json
{
  "CalvingWatch":      {"disable_tools": ["web_search","web_fetch"], "pass": true},
  "GrazingOptimizer":  {"disable_tools": ["web_search","web_fetch"], "pass": true}
}
```

**Live platform-side check (`beta.agents.retrieve`):**
Initial retrieval on the pre-MEM-11 cached agent IDs showed empty `configs: []`
— because `ensure_agent` only creates and never updates, the cache in
`runtime/agent_ids.json` still pointed to agents built before MEM-11 shipped.

After dropping CalvingWatch + GrazingOptimizer from `agent_ids.json` and
re-running `ensure_agent`, the new agents' live `tools` now carry:

```json
{
  "type": "agent_toolset_20260401",
  "default_config": {"enabled": true, "permission_policy": {"type": "always_allow"}},
  "configs": [
    {"name": "web_search", "enabled": false, "permission_policy": {"type": "always_allow"}},
    {"name": "web_fetch", "enabled": false, "permission_policy": {"type": "always_allow"}}
  ]
}
```

**MEM-11: VERIFIED on live platform.**

Follow-up: the pre-existing `FenceLineDispatcher`, `HerdHealthWatcher`,
`PredatorPatternLearner`, `CrossRanchCoordinator` agent IDs were *not*
re-created — those four specs don't list `disable_tools`, so there's nothing
to re-verify on them. However, if any of them gain a `disable_tools` entry
later, a cache bust will be required. Worth adding a "drift detector" that
diffs `_build_tools_config(spec)` against `beta.agents.retrieve(cached_id)`
and warns/recreates on mismatch. (Low priority — caching IDs is a one-shot
convenience; ops can just delete the JSON.)

## Anything surprising?

1. **Memory stores were purged platform-side** between runs — the JSON cache
   pointed to 6 stale IDs that 404'd on session create. Script now calls
   `list_stores()` and recreates any missing-from-live entries. The
   `AgentMesh._ensure_memory_stores()` path in the live server will have the
   same issue if the platform aggressively reaps. **Follow-up:** add a
   liveness check there too (probe with `retrieve_store` or `list_stores`
   before trusting cache).

2. **`ensure_agent` has no update semantics.** Changing a spec's
   `disable_tools`, skills, system prompt path, or model does not propagate
   to live platform agents until the cache entry is removed. Worth a guard
   rail pre-demo.

3. The `ManagedSessionManager.stream_session_events` wrapper is broken
   (never awaited the coroutine). The handler-base variant has the same
   shape — it has not surfaced because the CLI smoke path doesn't exercise
   it live. **Blocker for any real production use of managed runtime.**

## Recommendation

**Ready for live demo** — with two caveats:

- **Before demo rehearsal:** fix the `stream()` async-context-manager bug in
  `managed.py` + `_handler_base.py`, or document that the live smoke script
  is the canonical entry. Otherwise `make demo` against managed runtime
  will explode.
- Keep this result file as the gold reference for cost expectations
  (~$0.21 for 6 agents × 1 wake each). Longer-run scenarios (tool-use loops)
  will cost more; set per-scenario budget alerts.

Total follow-ups:
- FIX-A: `_handler_base._run_managed` `stream()` needs `await`.
- FIX-B: `ManagedSessionManager.stream_session_events` needs `await`.
- FIX-C: `ensure_agent` should detect spec-vs-live tools drift or accept
  `force=True`.
- FIX-D: `_ensure_memory_stores` should probe liveness before trusting the
  JSON cache.
- CLI-A: Either teach `skyherd-mesh mesh smoke` a `--live` flag or replace
  with the custom script as the canonical gate.
