---
phase: 4
phase_slug: attestation-year-2
status: complete
completed: 2026-04-23
plans: 4
tests_before: 1438
tests_after: 1480
coverage_before: 87.42
coverage_after: 89.13
commits:
  - 7516e11 feat(04-01) signer rotation + ledger memver_id pairing
  - 7bae4b4 feat(04-02) skyherd-verify standalone CLI
  - a6e6008 feat(04-03) /attest/:hash viewer + pair endpoint + badge
  - 2e9b925 docs(04-04) ATTESTATION.md + ATTESTATION_ROTATION.md + integration test
requirements_closed: [ATT-01, ATT-02, ATT-03, ATT-04, ATT-05, ATT-06]
---

# Phase 4 Summary — Attestation Year-2

## One-liner

Year-2 attestation hardening: Ed25519 signer rotation (archived pubkeys), ledger `memver_id` pairing bound in canonical-JSON hash, standalone `skyherd-verify` CLI (7.8ms on 10-event chain), public `/attest/:hash` SPA viewer with per-row Verified ✓ badges, and end-to-end documentation.

## Shipped

| Requirement | Scope | Status |
|---|---|---|
| ATT-01 | Public `/attest/:hash` SPA route with chain walk | GREEN |
| ATT-02 | `Signer.rotate()` archives old key with 0600 chmod, fresh key in-place | GREEN |
| ATT-03 | `skyherd-verify` CLI — 7.8ms on 10-event chain (target <200ms) | GREEN |
| ATT-04 | `memver_id` field bound in canonical JSON + `/api/attest/pair/{id}` | GREEN |
| ATT-05 | `docs/ATTESTATION.md` + `docs/ATTESTATION_ROTATION.md` | GREEN |
| ATT-06 | `AttestationPanel` per-row ✓ badge + `↗` viewer link | GREEN |

## Metrics

- **Tests:** 1438 → 1480 (+42)
- **Coverage:** 87.42% → 89.13% (+1.71%)
- **On modified modules:**
  - `signer.py` — 97% (target ≥85%)
  - `ledger.py` — 96% (target ≥85%)
  - `verify_cli.py` (new) — 92% (target ≥90%)
  - `cli.py` — 99%
- **Vitest:** 78 → 92 (+14)
- **CLI perf:** 10-event chain verify in **7.8ms** (25× under budget)
- **Determinism:** 3/3 PASS on `test_demo_seed42_is_deterministic_3x`
- **8/8 scenarios:** PASS via `make demo SEED=42 SCENARIO=all`

## New files

- `src/skyherd/attest/verify_cli.py` — 2-subcommand CLI (`verify-event`, `verify-chain`).
- `tests/attest/test_verify_cli.py` — 16 tests including <200ms perf gate.
- `tests/attest/test_integration_rotation.py` — 2 e2e tests (rotation + memver pairing + CLI).
- `tests/server/test_attest_api.py` — 12 tests for new API endpoints.
- `web/src/components/AttestChainViewer.tsx` — public viewer component.
- `web/src/components/AttestChainViewer.test.tsx` — 6 vitest specs.
- `docs/ATTESTATION.md` — judge-facing walkthrough.
- `docs/ATTESTATION_ROTATION.md` — rotation runbook.

## Modified files

- `src/skyherd/attest/signer.py` — `Signer.rotate(current, archive, *, timestamp=None)` class method + 0600 archive + collision handling.
- `src/skyherd/attest/ledger.py` — `append(..., memver_id=None)` kwarg binds `_memver_id` into canonical-JSON payload; `Event` gains `memver_id` field; `iter_events` extracts it on read.
- `src/skyherd/agents/memory_hook.py` — passes `memver_id=memory_version_id` with `TypeError` compat fallback for pre-Phase-4 ledgers.
- `src/skyherd/server/app.py` — `GET /api/attest/by-hash/{hash}` (chain walk) + `GET /api/attest/pair/{memver_id}` (dual-receipt). Both with hex/alnum validation, 400/404 on invalid.
- `web/src/components/AttestationPanel.tsx` — per-row ✓ badge from `first_bad_seq` and `↗` button pushing `/attest/{hash}`.
- `web/src/routes.tsx` — new `/attest/:hash` route wired to `AttestChainViewer`.
- `pyproject.toml` — `skyherd-verify = "skyherd.attest.verify_cli:main"` console script.
- `CLAUDE.md` — reading order now includes `docs/ATTESTATION.md`.

## Key decisions

1. **`_memver_id` reserved prefix** for canonical-JSON binding — prevents caller payload collision while keeping the pairing tamper-evident. Chose this over a dedicated column (no schema migration needed; round-trip via JSON extraction).
2. **Archived pubkeys per-row, not central registry** — every row carries its signing pubkey, so verification never needs the archive directory. Archive is purely a recovery aid if a row's pubkey column was ever corrupted.
3. **Two separate console scripts** (`skyherd-attest` and `skyherd-verify`) rather than a mega-CLI. Judge-facing audit surface stays small.
4. **`typer` already in deps** — no new runtime packages added for the verify CLI.
5. **Compat fallback in memory_hook** — `try/except TypeError` around `ledger.append(memver_id=...)` keeps Phase-1 tests passing if they mock an older ledger signature.

## Deviations from plan

**None.** All 4 plans executed exactly as written.

## Security notes

- **Tamper detection for memver pairing:** `test_memver_id_tamper_detected_via_verify` confirms that swapping the `_memver_id` in the payload JSON invalidates the chain.
- **Constant-time compare** preserved throughout new code (`hmac.compare_digest` mirrored in `verify_cli.py`).
- **Input validation** on both new API endpoints: hash must be hex ≤128 chars; memver_id must be alnum+underscore ≤128 chars. Both return 400 on invalid.
- **No new secrets on disk** — archived PEMs are 0600, same as live keys.

## Known gaps / deferred

None. All plan scope closed.

## Next step

Ready for Phase 5 (Hardware H1 Software Prep — Pi 4 + PiCamera + cardboard-coyote) or the Phase 6 determinism CI gate, per ROADMAP.

## Self-Check

Files verified:
- ✓ `src/skyherd/attest/verify_cli.py`
- ✓ `tests/attest/test_verify_cli.py`
- ✓ `tests/attest/test_integration_rotation.py`
- ✓ `tests/server/test_attest_api.py`
- ✓ `web/src/components/AttestChainViewer.tsx`
- ✓ `web/src/components/AttestChainViewer.test.tsx`
- ✓ `docs/ATTESTATION.md`
- ✓ `docs/ATTESTATION_ROTATION.md`

Commits verified in git log:
- ✓ 7516e11 feat(04-01) signer rotation + ledger memver_id pairing
- ✓ 7bae4b4 feat(04-02) skyherd-verify standalone CLI
- ✓ a6e6008 feat(04-03) /attest/:hash viewer + pair endpoint + badge
- ✓ 2e9b925 docs(04-04) ATTESTATION.md + ATTESTATION_ROTATION.md + integration test

## Self-Check: PASSED
