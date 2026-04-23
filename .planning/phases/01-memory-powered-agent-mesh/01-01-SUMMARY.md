---
phase: 01
plan: 01
status: complete
completed: 2026-04-23
tests_delta: +20
coverage_delta: unchanged
---

# Plan 01-01 Summary — Wave 0 Foundation

## A1 status

**PASS.** Live probe against api.anthropic.com confirmed that
`client.beta.sessions.create(extra_body={"resources": [{"type":"memory_store", ...}]})`
is accepted and echoed in the response.

**Downstream impact on Plan 01-03:** proceeds on the `extra_body` path. No raw-POST
fallback needed.

### Critical API schema discovery

Two findings from the live probe that downstream plans must honor:

1. **Field name for access permissions is `access`, NOT `mode`**
   - Sending `"mode": "read_write"` triggers 400 with
     `"resources.0.mode: Extra inputs are not permitted"`.
   - Omitting the field entirely defaults to `read_write`.
   - For `read_only` (shared store), the correct key is `"access": "read_only"`.

2. **Memory path field must start with `/`**
   - Server enforces regex `^(/[^/\x00]+)+$`.
   - Plan 01-02 `write_memory` / Plan 01-01 `decide_write_path` MUST emit
     paths that start with `/`. **TODO for Plan 01-02/01-04** — current
     `decide_write_path` returns `"patterns/coyote-crossings.md"`; when wired
     to real REST in `memory.py`, either prepend `/` in the manager or update
     `memory_paths.py` to emit `/patterns/...`.

## Deliverables

| File | Purpose |
|------|---------|
| `scripts/a1_probe.py` | Self-cleaning live probe; idempotent PASS on re-run |
| `docs/A1_PROBE_RESULT.md` | Live-API evidence; status=PASS; apikey_* redacted |
| `src/skyherd/agents/memory_paths.py` | Pure per-agent decide_write_path — no datetime/uuid/time/random |
| `tests/agents/test_memory_paths.py` | 11 tests: per-agent branches, redaction, determinism, unknown-agent ValueError |
| `tests/test_determinism_e2e.py` | DETERMINISM_SANITIZE extended with memver_/mem_/memstore_ regex |
| `web/src/components/shared/HashChip.tsx` | Extracted HashChip; sha256-derived swatches for non-hex hashes |
| `web/src/components/shared/HashChip.test.tsx` | 5 tests: testid render, 4 swatches (hex + non-hex), clipboard copy, short-hash fallback |
| `tests/agents/test_memory.py` | Wave 0 stub for Plan 01-02 |
| `tests/agents/test_memory_hook.py` | Wave 0 stub for Plan 01-04 |
| `tests/agents/test_memory_determinism.py` | Wave 0 stub for Plan 01-07 |
| `tests/server/test_memory_api.py` | Wave 0 stub for Plan 01-05 |
| `web/src/components/MemoryPanel.test.tsx` | Wave 0 stub for Plan 01-06 |

## HashChip import path

Confirmed: `import { HashChip } from "@/components/shared/HashChip";`
- AttestationPanel.tsx consumes shared component; zero visual regression.
- All 14 AttestationPanel.test.tsx tests still green.
- New 5-test HashChip.test.tsx green.

## Commits

- `29daea4` — A1 live probe (PASS)
- (HashChip extraction) — shared component + AttestationPanel wiring + tests
- (memory_paths + sanitizer + stubs) — Wave 0 foundation

## Deviations

None — plan executed as written. One runtime fix during the A1 probe:
anthropic SDK's `client.post(cast_to=dict, ...)` requires a parameterized
generic `Dict[str, Any]`; bare `dict` crashes `construct_type`. Fix recorded
in the probe as `_RESP = Dict[str, Any]`. No plan deviation.

## Self-Check: PASSED

- `scripts/a1_probe.py`: FOUND
- `docs/A1_PROBE_RESULT.md`: FOUND (status=PASS)
- `src/skyherd/agents/memory_paths.py`: FOUND
- `web/src/components/shared/HashChip.tsx`: FOUND
- All 5 Wave 0 stubs: FOUND
- `grep -E "apikey_[A-Za-z0-9]+" docs/A1_PROBE_RESULT.md` returns 0 matches (all redacted)
- `grep -cE "^(from datetime|import datetime|import uuid|import random|import time)" src/skyherd/agents/memory_paths.py` returns 0
