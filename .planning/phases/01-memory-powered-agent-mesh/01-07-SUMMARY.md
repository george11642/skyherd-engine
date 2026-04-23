---
phase: 01
plan: 07
status: complete
completed: 2026-04-23
tests_delta: +10 (8 determinism + 2 E2E)
---

# Plan 01-07 Summary — Phase gate

## Test suites shipped

- `tests/agents/test_memory_determinism.py` — 8 tests (AST-based forbidden-import
  guard; no-HTTP under local; LocalMemoryStore content-derived IDs; time-invariant
  decide_write_path).
- `tests/integration/test_memory_scenario_e2e.py` — 2 tests (demo-critical dual
  receipts; cross-session read via shared store).
- `tests/test_determinism_e2e.py` — extended with
  `test_demo_seed42_with_local_memory_is_deterministic_3x`.

## Audit results

| Gate | Result |
|------|--------|
| Repo test suite (1363 tests, non-slow) | PASS |
| Repo coverage (target ≥80%) | **88.77%** |
| `memory.py` coverage (target ≥90%) | **96%** |
| `memory_hook.py` coverage (target ≥90%) | **97%** |
| `memory_paths.py` coverage (target ≥90%) | **100%** |
| `memory_api.py` coverage (target ≥90%) | **91%** |
| `SKYHERD_AGENTS=local make mesh-smoke` | PASS ("All agents produced tool calls. Smoke test PASSED.") |
| `test_demo_seed42_is_deterministic_3x` (slow) | PASS |
| `test_demo_seed42_with_local_memory_is_deterministic_3x` (slow) | PASS |
| `cd web && pnpm vitest run` | PASS (77 tests) |
| `cd web && pnpm run build` | PASS (clean) |

## Deviations

**Deviation 1 — AST-based forbidden-import guard.** Initial string-level
check (`"datetime.now" in src`) false-positived on memory_paths.py docstring
which proudly declares "No `datetime.now()`…". Replaced with AST walk over
`ast.Import` / `ast.ImportFrom` — tests module imports, not docstring text.

## 3x sanitized md5 (from memory-enabled replay)

Not recorded — `_sanitize` + `_md5` are internal to the test; test passed
identicals. All three runs produced the same hash (the assertion's
`len(set(hashes)) == 1` is the proof).

## Known limitations

- **Managed-path smoke deferred.** `mesh-smoke` under `SKYHERD_AGENTS=managed`
  not exercised in CI (requires live API key and $$). Per RESEARCH.md MEM-12
  this is explicitly accepted for CI; live-developer runs cover that path.
- **Memory.written SSE on the live dashboard** is test-verified but the
  human-verify visual checkpoint in Plan 01-06 is pending (documented in
  01-CHECKPOINT.md).

## Commits

- `(commit hash)` — determinism tests + E2E scenario

## Self-Check: PASSED
- `tests/agents/test_memory_determinism.py` — 8 tests green
- `tests/integration/test_memory_scenario_e2e.py` — 2 tests green
- Repo coverage 88.77% ≥ 80%
- Per-module coverage all ≥ 90% on new memory modules
- mesh-smoke exit 0
- slow determinism tests both pass (3x replay equality)
- web vitest + build clean
