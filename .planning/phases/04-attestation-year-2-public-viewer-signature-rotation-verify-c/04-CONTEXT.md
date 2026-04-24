---
phase: 4
phase_slug: attestation-year-2
status: in_progress
created: 2026-04-23
owner: gsd-execute-phase
---

# Phase 4 CONTEXT — Attestation Year-2

## Vision

Judges watching the 3-minute demo must see **"two independent receipts agree"** on camera: a Claude Managed Agents memory version (`memver_...`) paired with an Ed25519-signed ledger row that walks back to genesis. On a fresh laptop, a single command — `skyherd-verify` — must prove the entire chain in under 200 ms.

Three Year-2 hardenings make this story shippable:

1. **Public viewer** — clickable chain walk in the SPA (`/attest/:hash`) so a reviewer can follow any receipt to genesis without CLI.
2. **Signature rotation** — the ranch's signing key is rotated mid-timeline; old rows keep verifying against archived pubkeys, new rows use the rotated key, and the Merkle chain link is unbroken.
3. **`skyherd-verify` standalone CLI** — takes `{event.json, sig.hex}` and outputs PASS/FAIL with a human-readable trace. Zero runtime deps beyond already-bundled `cryptography` + `click`.

## Constraints (repo invariants)

- **Determinism:** `make demo SEED=42 SCENARIO=all` must remain byte-identical across 3 replays (after wall-timestamp sanitization). Adding a `memver_id` field to ledger rows MUST feed through the canonical-JSON hash, so any content change is detected.
- **Coverage floor:** ≥80% project-wide (currently 87.42%). New `attest/` work must land ≥85% on modified files, ≥90% on brand-new `verify_cli.py`.
- **No new runtime deps.** Reuse `cryptography` (already in) and `typer`+`rich` (already in for `skyherd-attest`). The new `skyherd-verify` entry point is a second console-script in the same package.
- **MIT only.** Zero AGPL.
- **Prompt caching untouched.** This phase is backend + SPA only — no agent system-prompt changes.
- **Zero-attribution commits** (global git config enforces).

## Integration surface

Existing Phase 1 code already writes `memver.written` ledger rows (see `src/skyherd/agents/memory_hook.py:69-88`). Payload already includes `memory_version_id` — we expose this via a new pair-endpoint + SPA badge.

Existing Phase 1-3 server (`src/skyherd/server/app.py`) already has:
- `GET /api/attest` — recent entries (mock + live)
- `POST /api/attest/verify` — full chain walk

We extend with:
- `GET /api/attest/{hash}` — one entry + its chain-back-to-genesis
- `GET /api/attest/pair/{memory_version_id}` — memver → paired ledger row (the two-receipts-agree demo beat)

Existing SPA (`web/src/components/AttestationPanel.tsx`) already renders rows and runs bulk verify. We add:
- `/attest/:hash` route in `web/src/routes.tsx` rendering a new `AttestChainViewer` component.
- "Verified ✓" badge per row in `AttestationPanel` (using the per-entry verify result from the full-chain verify already wired).

## Plans

| Plan | Scope | Requirements |
|------|-------|--------------|
| 04-01 | Ledger `memver_id` field + signer rotation + archived-pubkey verification path | ATT-02, ATT-04 (ledger half) |
| 04-02 | `skyherd-verify` standalone CLI (new console-script) + perf benchmark test | ATT-03 |
| 04-03 | API endpoints `/api/attest/{hash}` + `/api/attest/pair/{memver_id}` + SPA viewer route + Verified ✓ badge | ATT-01, ATT-04 (API+UI half), ATT-06 |
| 04-04 | `docs/ATTESTATION.md` + `docs/ATTESTATION_ROTATION.md` end-to-end walkthrough + integration test (rotation + post-rotation verify) | ATT-05 |

## Requirements (traceability)

- **ATT-01** — Public `/attest/:hash` viewer route with chain walk.
- **ATT-02** — Signature rotation protocol: archived pubkeys stored in `runtime/attest_keys/`; rotated entries verify against their original pubkey.
- **ATT-03** — `skyherd-verify` CLI `<200ms` on typical input (10-event chain).
- **ATT-04** — `memver_id` optional field on ledger rows; `/api/attest/pair/{memver_id}` side-by-side receipts.
- **ATT-05** — `docs/ATTESTATION.md` + `docs/ATTESTATION_ROTATION.md` with copy-pasteable commands.
- **ATT-06** — `AttestationPanel` per-row "Verified ✓" badge + click-through to `/attest/:hash`.

## Success criteria

- All 6 requirements GREEN.
- `make ci` passes (lint+typecheck+test).
- `make demo SEED=42 SCENARIO=all` deterministic across 3 replays.
- `skyherd-verify event.json sig.hex --pubkey pub.pem` runs in <200ms.
- Coverage ≥80% overall, ≥85% on modified `signer.py`+`ledger.py`, ≥90% on new `verify_cli.py`.
- SPA builds clean and ships the `/attest/:hash` route.
