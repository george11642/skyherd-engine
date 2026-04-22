# Security Review — SkyHerd Engine

**Date**: 2026-04-21  
**Reviewer**: Production Hardening Agent  
**Standard**: OWASP Top 10 (2021)  
**Scope**: Server, MCP, attestation chain, edge watcher, voice pipeline, web frontend

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0     |
| HIGH     | 3     |
| MEDIUM   | 4     |
| LOW      | 3     |
| NOTE     | 2     |

**CRITICAL / HIGH fixes applied in commit `security: review + fixes`.**

---

## Findings

### F-01 — HIGH — `server/app.py`: CORS wildcard origin with `allow_credentials=True`

**File**: `src/skyherd/server/app.py`, line 76-82  
**Risk**: `allow_origins=["http://localhost:5173", "http://localhost:3000", "*"]` combined with `allow_credentials=True` violates the CORS spec (browsers reject `*` with credentials) and, more importantly, in production a wildcard origin allows any site to make credentialed cross-origin requests to the API.  
**Fix applied**: Removed `"*"` from the allow_origins list. Production deployments should restrict to explicit origins via `SKYHERD_CORS_ORIGINS` env var (comma-separated). Dev defaults kept for localhost. `allow_credentials` set to `False` (dashboard uses SSE, no cookies needed).

---

### F-02 — HIGH — `server/app.py`: No rate limiting on SSE `/events` endpoint

**File**: `src/skyherd/server/app.py`, `sse_stream()`  
**Risk**: An adversary can open thousands of concurrent SSE connections, exhausting server file descriptors and memory. No limit on simultaneous subscribers.  
**Fix applied**: Added `SSE_MAX_CONNECTIONS` guard (default 100) with a `429 Too Many Requests` response when exceeded. Connection count tracked with a module-level `asyncio.Semaphore`.

---

### F-03 — HIGH — `voice/call.py`: Unsanitised `wav_path.name` injected into TwiML `<Play>` URL

**File**: `src/skyherd/voice/call.py`, line 80  
**Risk**: `wav_url = f"{tunnel_base}/voice/{wav_path.name}"` — if `wav_path.name` contains path traversal characters (e.g. `../../../etc/passwd`) or a malicious value is injected via the `CLOUDFLARE_TUNNEL_URL` env var, the TwiML `<Play>` element could point to arbitrary URLs. Although `wav_path` is constructed internally (not from user input), future callers may pass untrusted paths.  
**Fix applied**: Added `_safe_wav_name()` sanitiser that strips everything except `[a-zA-Z0-9_.-]` and verifies the result does not start with `.`. This makes the path-to-URL mapping robust against accidental injection.

---

### F-04 — MEDIUM — `mcp/rancher_mcp.py`: Phone number not validated before Twilio call

**File**: `src/skyherd/mcp/rancher_mcp.py`, `_try_send_sms()` / `_try_voice_call()`  
**Risk**: `phone` is sourced from `rancher_prefs.json` (a user-controlled file). No E.164 validation means an attacker who writes to `rancher_prefs.json` could inject arbitrary values into the Twilio `to` field (at worst, billing fraud or SSRF via Twilio).  
**Recommendation (TODO)**: Validate phone numbers match `^\+[1-9]\d{7,14}$` before passing to Twilio. Restrict `rancher_prefs.json` file permissions to 0o600.

---

### F-05 — MEDIUM — `mcp/rancher_mcp.py`: PII in structured logs via `wes_script`

**File**: `src/skyherd/mcp/rancher_mcp.py`, `_write_log()`  
**Risk**: The `wes_script` field written to `rancher_pages.jsonl` may contain animal IDs, GPS coordinates, and rancher phrasing but also the phone number in the `recipient` field and potentially PII from `context` (e.g. vet intake packets with animal owner data).  
**Recommendation (TODO)**: Scrub or hash phone numbers before writing to log. Add `log_scrub_phone(record)` utility that replaces phone values with `***REDACTED***`.

---

### F-06 — MEDIUM — `edge/watcher.py`: MQTT broker connects anonymously without TLS

**File**: `src/skyherd/edge/watcher.py`, `_heartbeat_loop()` / `_publish()`  
**Risk**: `aiomqtt.Client(hostname=..., port=...)` uses anonymous, plaintext MQTT. On a production ranch LAN, any device can publish fake sensor readings. An adversary could inject false trough_cam detections triggering unnecessary drone dispatches.  
**Recommendation (TODO — production path)**: Document that production deployments must set `MQTT_USERNAME`, `MQTT_PASSWORD`, and `MQTT_TLS_CA_CERT` env vars. Implement TLS + auth path in `_build_mqtt_client()` when those vars are present. Sim mode remains anonymous.

---

### F-07 — MEDIUM — `server/app.py`: `since_seq` query param accepted but no upper bound

**File**: `src/skyherd/server/app.py`, `api_attest()`  
**Risk**: `since_seq: int = Query(default=0, ge=0)` accepts arbitrarily large integers. While SQLite handles this gracefully, a client could pass `since_seq=0` to dump the entire ledger history in one request. The 50-entry cap is present but only applied after the query executes.  
**Recommendation (TODO)**: Add `le=10_000_000` upper bound to `Query()` and add pagination support.

---

### F-08 — LOW — `attest/signer.py`: Private key saved without password encryption

**File**: `src/skyherd/attest/signer.py`, `save()`  
**Risk**: `NoEncryption()` means the private key file on disk is unprotected beyond file permissions (0o600). If the file is exfiltrated (e.g. backup, container image leak), the signing key is immediately usable.  
**Recommendation (TODO)**: Support `SKYHERD_ATTEST_KEY_PASSPHRASE` env var; use `BestAvailableEncryption(passphrase)` when set.

---

### F-09 — LOW — `web/src/components/AttestationPanel.tsx`: `payload_json` rendered as raw text

**File**: `web/src/components/AttestationPanel.tsx`, line 181  
**Risk**: `{entry.payload_json}` is rendered as React text content (not `dangerouslySetInnerHTML`). React escapes text nodes, so standard XSS is not possible. However, if future code changes this to HTML rendering, payload content could execute scripts. Event hashes, signatures, and source fields are all rendered safely.  
**Recommendation (TODO)**: Add a code comment explicitly noting that `payload_json` must never be rendered via `dangerouslySetInnerHTML` or `innerHTML`. Consider `JSON.parse` + `JSON.stringify(_, null, 2)` to ensure valid JSON display only.

---

### F-10 — LOW — `voice/call.py`: Absolute `wav_path` written to `phone_rings.jsonl`

**File**: `src/skyherd/voice/call.py`, line 155  
**Risk**: `"wav_path": str(wav_path.resolve())` writes the absolute file path (including hostname-derived paths) to a log file. This leaks the server's directory structure to any client reading the log.  
**Recommendation (TODO)**: Log only `wav_path.name` (filename only) in the persistent record; pass the full path only in memory for playback.

---

### F-11 — NOTE — `attest/ledger.py`: SQL queries use parameterized binding correctly

All SQL in `ledger.py` uses positional `?` parameters (lines 167-184, 204-211). No string concatenation in query construction. **No SQL injection risk.**

---

### F-12 — NOTE — `attest/ledger.py` + `signer.py`: Constant-time comparison in place

`hmac.compare_digest` used in `_constant_eq()` (line 107-108). Ed25519 verification is delegation to `cryptography` library which uses constant-time internally. Private key material excluded from `__repr__`. **Cryptographic primitives are correct.**

---

## Fixes Applied (HIGH only)

- **F-01**: CORS wildcard removed; `SKYHERD_CORS_ORIGINS` env var; `allow_credentials=False`
- **F-02**: SSE connection limiter (`SSE_MAX_CONNECTIONS`, default 100)
- **F-03**: `_safe_wav_name()` sanitiser in `voice/call.py`

## TODO (MEDIUM + LOW)

- F-04: Phone number E.164 validation + `rancher_prefs.json` chmod 0o600
- F-05: PII scrubbing in rancher log writer
- F-06: MQTT TLS + auth production path documentation
- F-07: `since_seq` upper bound + pagination
- F-08: Optional passphrase encryption for private key
- F-09: `payload_json` HTML safety comment in AttestationPanel
- F-10: Log only `wav_path.name` in phone_rings.jsonl
