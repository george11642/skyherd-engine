# SkyHerd Signing-Key Rotation Runbook

**Audience:** ranch operators, on-call SRE.

## When to rotate

| Trigger                              | Priority  |
|--------------------------------------|-----------|
| Scheduled quarterly                  | routine   |
| After staff with key access departs  | **high**  |
| Suspected compromise (lost device)   | **critical** |
| Before publishing a new attestation root (public release) | routine |

Keys do NOT have to rotate for existing rows to stay verifiable — the
pubkey lives on every row. Rotation only changes what key signs **future**
rows.

## What rotation does

`Signer.rotate(current_path, archive_dir)`:

1. Copies the current private key to `archive_dir / f"{timestamp}.pem"`
   with mode `0600`.
2. Generates a fresh Ed25519 keypair.
3. Writes the new keypair to `current_path` (mode `0600`).
4. Returns the new `Signer`.

The chain link is preserved because `prev_hash` is purely derived from the
previous row's `event_hash` — it does not reference the signer at all.

## Manual rotation — safe path

```bash
# 0. Snapshot the current chain BEFORE rotation.
uv run skyherd-attest verify \
    --db /etc/skyherd/attest.db \
    --key /etc/skyherd/attest.key.pem

# 1. Rotate.
uv run python -c "
from pathlib import Path
from skyherd.attest.signer import Signer
new = Signer.rotate(
    Path('/etc/skyherd/attest.key.pem'),
    Path('/etc/skyherd/attest_keys'),
)
print('Rotated. New pubkey:')
print(new.public_key_pem)
"

# 2. Append a rotation-marker event so the chain self-documents the event.
echo '{"event":"key_rotated","ts":"'$(date -u +%FT%TZ)'"}' | \
    uv run skyherd-attest append attest key.rotated \
        --key /etc/skyherd/attest.key.pem \
        --db /etc/skyherd/attest.db

# 3. Verify — pre-rotation rows still pass, new rows too.
uv run skyherd-attest verify \
    --db /etc/skyherd/attest.db \
    --key /etc/skyherd/attest.key.pem

# 4. Off-dashboard verify with the standalone CLI.
uv run skyherd-verify verify-chain \
    --db /etc/skyherd/attest.db \
    --key /etc/skyherd/attest.key.pem
```

All four commands should exit `0`.

## Emergency rotation (compromised key)

Same flow, but **before** appending the `key.rotated` marker:

1. Revoke any systems that still hold the old key (rm `-f`, revoke SSH
   keys that pulled it).
2. Announce the rotation timestamp to the pubkey-pinned viewer consumers.
3. Any row appended by the leaked key **after** the known-good checkpoint
   should be manually invalidated via a `kind=rotation.revoke` event
   signed by the fresh key.

## Restoring an archived key

```bash
# List archived keys.
ls -la /etc/skyherd/attest_keys/

# Restore a specific archived key to verify old rows off-dashboard.
cp /etc/skyherd/attest_keys/20260423T210000Z.pem /tmp/archived.pem
chmod 600 /tmp/archived.pem
uv run skyherd-verify verify-chain \
    --db /etc/skyherd/attest.db \
    --key /tmp/archived.pem
```

The archived key is only needed if you lost the per-row pubkey data. In
normal operation every row self-describes its pubkey, so the archived PEM
is a **belt-and-suspenders** recovery path, not required for verification.

## Failure modes

| Symptom | Cause | Remedy |
|---------|-------|--------|
| `FileNotFoundError: No key at ...` | Wrong `current_path`. | Pass the path to the **live** key; rotate refuses if it does not exist. |
| Archived `.pem` file readable by `others` | Umask problem during archive write. | `chmod 600` on `archive_dir/*.pem`; rotate() already calls chmod but double-check after filesystem sync. |
| Timestamp collision (same-second rotation) | Two rotations in one second. | `Signer.rotate` auto-appends `-1`, `-2`, … suffix. |

## Scheduled-rotation automation

Cron (quarterly at 02:00 UTC on the first of Jan/Apr/Jul/Oct):

```cron
0 2 1 1,4,7,10 * cd /opt/skyherd && uv run python -m tools.rotate_signer \
    >> /var/log/skyherd/rotate.log 2>&1
```

`tools/rotate_signer.py` is left as a one-liner wrapper over
`Signer.rotate(...)` — the repo ships the primitive, operators plumb the
cron.

## Links

- Primitive: `src/skyherd/attest/signer.py::Signer.rotate`
- Tests: `tests/attest/test_signer.py::TestSignerRotate`
- Integration: `tests/attest/test_integration_rotation.py`
- End-to-end walkthrough: [`ATTESTATION.md`](./ATTESTATION.md)
