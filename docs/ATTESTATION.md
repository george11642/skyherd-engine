# SkyHerd Attestation — End-to-End Walkthrough

**Phase 4 — Year-2 hardening**. Ship 2026-04-23.

The SkyHerd attestation chain is a tamper-evident, Ed25519-signed,
Merkle-linked log of every decision an agent makes. Anyone with the public
key can re-derive every hash and verify every signature with zero network
access.

This document is the judge-facing manual. Every command is
copy-pasteable.

---

## 1. What gets signed

Each ledger row captures one event:

| Field          | Example                                   | Purpose                              |
|----------------|-------------------------------------------|--------------------------------------|
| `seq`          | `42`                                      | Strictly-increasing insertion order. |
| `ts_iso`       | `2026-04-23T21:05:00+00:00`               | UTC timestamp.                       |
| `source`       | `FenceLineDispatcher`                     | Who.                                 |
| `kind`         | `fence.breach`                            | What.                                |
| `payload_json` | `{"fence":"north","species":"coyote"}`    | Evidence.                            |
| `prev_hash`    | `cafebabe…` or `GENESIS` for the first    | Chain link.                          |
| `event_hash`   | `blake2b-256(prev_hash‖payload‖ts‖src‖kind)` | Binds everything.                 |
| `signature`    | Ed25519 over `event_hash` (raw bytes)     | Proof of author.                     |
| `pubkey`       | SubjectPublicKeyInfo PEM                  | Self-contained verifier.             |
| `memver_id`    | `memver_01XRSV...` (optional)             | Pair with Managed-Agents memory.     |

Hashing is **constant-time compare** (`hmac.compare_digest`) and the
canonical JSON encoding uses `sort_keys=True, separators=(",", ":"),
allow_nan=False` — NaN/Inf are rejected at write time.

---

## 2. Hands-on — create a chain

```bash
uv run skyherd-attest init --key /tmp/attest.key.pem --db /tmp/attest.db
echo '{"tank":1,"psi":0.3}' | uv run skyherd-attest append \
    sensor.water.1 water.low --key /tmp/attest.key.pem --db /tmp/attest.db
echo '{"species":"coyote","fence":"north"}' | uv run skyherd-attest append \
    FenceLineDispatcher fence.breach --key /tmp/attest.key.pem --db /tmp/attest.db
uv run skyherd-attest list --db /tmp/attest.db --key /tmp/attest.key.pem
uv run skyherd-attest verify --db /tmp/attest.db --key /tmp/attest.key.pem
```

Expected tail:

```
CHAIN VALID — 2 event(s) verified.
```

---

## 3. The two-receipts-agree demo beat

SkyHerd's Managed Agents mesh writes one `memver_` per wake cycle through
the Claude platform's Memory API. **Every** memver is mirrored into the
local Ed25519 ledger with `memver_id` bound into the signed hash:

```python
ledger.append(
    source="memory",
    kind="memver.written",
    payload={
        "agent": "HerdHealthWatcher",
        "memory_store_id": store_id,
        "memory_version_id": memver.memory_version_id,
        "content_sha256": memver.content_sha256,
    },
    memver_id=memver.memory_version_id,   # ← bound into event hash
)
```

If a tamperer edits the memver id in the payload JSON, the event hash no
longer matches and `verify` fails at that row. **Two independent receipts
agree** — one from Anthropic's Memory API, one from our Ed25519 chain.

Query the pair over HTTP:

```bash
curl http://localhost:8000/api/attest/pair/memver_01XRSV...
```

Response:

```json
{
  "memver_id": "memver_01XRSV...",
  "ledger_entry": { "seq": 42, "event_hash": "…", "signature": "…", … },
  "memver": { "id": "memver_01XRSV...", "agent": "HerdHealthWatcher", … }
}
```

---

## 4. The public `/attest/:hash` viewer

Any `event_hash` is a public URL:

```
http://localhost:8000/attest/deadbeef00000001...
```

The page:

1. Fetches `GET /api/attest/by-hash/{hash}` → the chain back to genesis.
2. Kicks off `POST /api/attest/verify` → per-row PASS/FAIL.
3. Renders every row with a ✓ Verified or ✗ Invalid chip.

No auth needed. Share the URL and anyone can verify the chain.

---

## 5. The standalone `skyherd-verify` CLI

When a judge wants off-dashboard, zero-trust verification, they run:

```bash
uv run skyherd-verify verify-chain --db /tmp/attest.db --key /tmp/attest.key.pem
```

Expected:

```
PASS chain valid — 2 event(s) verified in 3.4ms
```

Or verify a single event triple (useful when you only have one row
exported as JSON + sig + pubkey):

```bash
# Export one event:
uv run python -c "
import json, sqlite3
conn = sqlite3.connect('/tmp/attest.db')
row = conn.execute('SELECT seq, ts_iso, source, kind, payload_json, prev_hash, event_hash, signature, pubkey FROM events LIMIT 1').fetchone()
evt = dict(zip(['seq','ts_iso','source','kind','payload_json','prev_hash','event_hash','signature','pubkey'], row))
sig = evt.pop('signature')
pub = evt.pop('pubkey')
open('/tmp/evt.json','w').write(json.dumps(evt))
open('/tmp/pub.pem','w').write(pub)
print('SIG:', sig)
"
# Then verify:
uv run skyherd-verify verify-event /tmp/evt.json <SIG> /tmp/pub.pem
```

**Performance target: `<200ms` on a 10-event chain.** Phase 4 asserts this
in `tests/attest/test_verify_cli.py::test_verify_chain_under_200ms`.

---

## 6. Signature rotation

Signing keys should rotate regularly. Old signatures keep verifying because
the pubkey is stored on every row. See
[`ATTESTATION_ROTATION.md`](./ATTESTATION_ROTATION.md) for the operational
runbook.

TL;DR:

```python
from pathlib import Path
from skyherd.attest.signer import Signer

new = Signer.rotate(
    current_path=Path("/etc/skyherd/attest.key.pem"),
    archive_dir=Path("/etc/skyherd/attest_keys"),
)
# new = Signer with a fresh keypair; old key copied to archive_dir/TIMESTAMP.pem
```

Pre-rotation rows continue to verify against their original (archived)
pubkey. Post-rotation rows verify against the new key. The chain link is
unbroken because `prev_hash` does not depend on the signer — only on the
previous `event_hash`.

---

## 7. Security notes

- **No secrets in `__repr__`.** `Signer.__repr__` prints a 12-char public
  key snippet and nothing else. Private key material never appears in
  logs.
- **Constant-time comparison** on all hash/prev_hash equality checks.
- **PEM permissions** enforced to `0o600` on both the current key and every
  archived key.
- **NaN / Inf rejected** by `_canonical_json(..., allow_nan=False)` so no
  two nodes can ever disagree on float representation.
- **Pubkey type guard** — `verify()` rejects non-Ed25519 public keys early.
- **Signatures are over raw hash bytes**, not hex strings — tampering the
  hex encoding of the hash still invalidates the sig.

---

## 8. References

- `src/skyherd/attest/signer.py` — Ed25519 primitives + rotation.
- `src/skyherd/attest/ledger.py` — SQLite-backed Merkle chain.
- `src/skyherd/attest/cli.py` — `skyherd-attest` (init, append, verify, list).
- `src/skyherd/attest/verify_cli.py` — `skyherd-verify` (verify-event, verify-chain).
- `src/skyherd/server/app.py` — `/api/attest/*` HTTP surface.
- `web/src/components/AttestChainViewer.tsx` — the `/attest/:hash` SPA page.
- `tests/attest/` — 95+ tests covering signer, ledger, CLI, rotation, pairing.

---

## 9. External tools used in the demo video pipeline

The 3-minute submission video was edited with the assistance of OpenMontage
(github.com/calesthio/OpenMontage, AGPLv3) acting as an external **agentic
edit director**, with explicit hackathon-moderator clearance. OpenMontage
itself never touches the attestation chain or any SkyHerd runtime — it lives
entirely outside this MIT repo at `~/tools/openmontage/` and never has its
source vendored, copied, or imported.

What lives in this repo as evidence of OpenMontage's editorial decisions are
six `edit_decisions.json` artifacts at `docs/edl/openmontage-cuts-{A,B,C}-{cinematic,screen-demo}.json`.
These are JSON files we authored as the host AI agent OpenMontage's pipeline
definitions describe, applying the `cinematic` and `screen-demo` pipeline
director skills to our three video variant scripts. Our MIT-original adapter
`scripts/openmontage_to_remotion.py` translates them into Remotion props that
our deterministic composition consumes — so the rendered video itself is our
composition, driven by the OpenMontage pipeline's editorial decisions.

The composition, render path, deterministic seed, and attestation chain are
unchanged. OpenMontage influenced cut order, overlay timing, B-roll
selection, and audio bus structure; it did not produce any code, asset, or
data that is signed into the Ed25519 ledger. See `docs/SUBMISSION.md`
"External tools used" and `docs/OPENMONTAGE_INTEGRATION.md` for the full
operating model and license-containment grep gate.

### Phase G — Opus 4.7 caption-styling artifacts

`make video-style-captions` calls Claude Opus 4.7 to emit per-word visual
styling for the demo video's captions. The output lives at
`remotion-video/public/captions/styled-captions-{A,B,C}.json` and is
considered part of the demo's artifact provenance: each file records the
exact model ID (`claude-opus-4-7`), an `input_fingerprint` SHA-256 over the
captions JSON + script + system prompt + skills prefix, and the per-call
Anthropic usage object (including `cache_read_input_tokens`).

These styled-caption JSONs are **not** signed into the Ed25519 ledger — they
are pre-rendered editorial decisions, not runtime tool calls — but their
fingerprints make the styling step independently reproducible: re-running
`style` on the same inputs produces a byte-identical file (the only
non-deterministic component is Opus's response, which the fingerprint
serves to detect).
