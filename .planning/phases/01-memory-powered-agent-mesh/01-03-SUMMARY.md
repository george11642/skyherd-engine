---
phase: 01
plan: 03
status: complete
completed: 2026-04-23
a1_path: extra_body (A1 PASS)
tests_delta: +10
---

# Plan 01-03 Summary — Managed session memory-store wiring

## Path taken: `extra_body`

A1 probe status: **PASS**. Plan 01-03 proceeds on the `extra_body` path:

```python
create_kwargs["extra_body"] = {"resources": resources}
platform_session = await self._client.beta.sessions.create(**create_kwargs)
```

No raw-POST fallback. No `client.post("/v1/sessions", ...)` path was added.

## Deviations

**Deviation 1 — `access` field instead of `mode`.** The A1 probe discovered
that the live API rejects `"mode": "read_write"` with 400 "Extra inputs not
permitted". The correct field name is `"access"`. All attach payloads use
`"access": "read_write"` or `"access": "read_only"` accordingly.

## Modification sites

- `src/skyherd/agents/managed.py`:
  - Lines ~107-128 (was ~107-110 before): added `_build_tools_config(agent_spec)` module-level helper.
  - Lines ~132-168 (was ~132-166): `__init__` gains `memory_store_ids` kwarg.
  - Lines ~220-223 (was ~220-223): `ensure_agent` calls `_build_tools_config(agent_spec)`.
  - Lines ~258-297 (was ~240-244): `create_session_async` resolves resources and passes `extra_body={"resources": [...]}`.

- `src/skyherd/agents/spec.py`:
  - Added `disable_tools: list[str] = field(default_factory=list)` to AgentSpec.

- `tests/agents/test_managed.py`:
  - +3 TestBuildToolsConfig tests (default / with_disable / bareSpec fallback).
  - +1 TestEnsureAgentToolsConfig test (tools kwarg comes from _build_tools_config).
  - +4 TestSessionCreateMemoryAttach tests (both/none/only_shared/only_per_agent).

## Prompt-cache invariant

`git diff src/skyherd/agents/managed.py | grep -E "^[+-].*cache_control"` returns
zero lines. Prompt-cache structure untouched.

## Commits

- `(commit hash)` — spec.py + managed.py + test_managed.py additions

## Self-Check: PASSED
- `grep "memory_store_ids"` in managed.py — true (2 sites: __init__ + create_session_async)
- `grep "extra_body"` in managed.py — true
- `grep "read_write" && grep "read_only"` in managed.py — both true
- `grep "access"` with attach shape — true (NOT "mode")
- 257 agents tests green (10 new, 0 regression)
- cache_control diff zero
