---
phase: 01
plan: 02
status: complete
completed: 2026-04-23
tests_delta: +43 (44 total in test_memory.py, minus 1 stub removed)
coverage: 96% on src/skyherd/agents/memory.py (target >= 90%)
---

# Plan 01-02 Summary — Memory Layer Unified

## Deliverables

- `src/skyherd/agents/memory.py` (458 lines)
- `tests/agents/test_memory.py` (44 tests, 96% coverage)

## Interface parity with PLAN

Zero drift. Every public symbol matches the `<interfaces>` block:

- `MemoryStore`, `Memory`, `MemoryVersion`, `ListEnvelope` (Pydantic, `extra="allow"` for API-side fields not in schema)
- `MemoryStoreBase` with 7 async methods
- `MemoryStoreManager(api_key, client, store_ids_path)` + all 7 methods + `_opts()` helper
- `LocalMemoryStore(root, store_ids_path)` + all 7 methods
- `get_memory_store_manager(runtime)` factory — `"local" | "managed" | "auto"`

## Deviations

**Deviation 1 — path normalization added.** Required by live API (A1 probe
finding: `^(/[^/\x00]+)+$`). The `_normalize_path()` helper prepends `/` to
memory paths before they hit REST. Plan 01-04 (hook) consumes `decide_write_path`
output (which returns `"patterns/coyote.md"` without leading `/`); the manager
normalizes on the way out. Local shim does the same for parity.

**Deviation 2 — `_opts()` returns `Any`.** The anthropic SDK's `RequestOptions`
is an internal TypedDict; pyright flags `dict[str, Any]` as incompatible. Return
type widened to `Any` with a comment. Runtime validates the shape.

**Deviation 3 — `MemoryStore.model_config = {"extra": "allow"}`.** Live API
returns fields not in the spike-minimal schema (e.g., `metadata`, `access`,
`mount_path`). Allowing extras prevents ValidationError on real responses.

## Key invariants

- Zero non-deterministic stdlib imports (no datetime/uuid/time/random) in memory.py
- Beta header `managed-agents-2026-04-01` asserted on every REST op via test
- LocalMemoryStore IDs are content-derived (sha256 -> 20 hex chars)
- Factory returns LocalMemoryStore on missing env / missing key / auto-fallback

## Commits

- `(commit hash)` — memory.py + tests

## Self-Check: PASSED
- `src/skyherd/agents/memory.py` FOUND (458 lines)
- `tests/agents/test_memory.py` FOUND (44 tests)
- `grep "from skyherd.agents.managed import ManagedAgentsUnavailable"` — true
- `grep -cE "^(from datetime|import datetime|import uuid|import random|import time)"` = 0
- Coverage 96% ≥ 90%
- Ruff + pyright clean
