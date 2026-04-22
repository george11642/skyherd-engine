# /ultrareview Checklist

Run `/ultrareview` in the Claude Code terminal at the repo root. This document tells you what to look for and how to evaluate what comes back.

---

## Pre-flight (verify before running)

- [ ] `docs/verify-latest.md` reflects the current state (last verified Apr 22 2026 — sim gate 10/10 TRULY-GREEN)
- [ ] `PROGRESS.md` green count is current (90 / 95 as of this commit)
- [ ] `git status` is clean or only has known-untracked files (e.g., `hackathon-info.html`)
- [ ] `make test` passes (`pytest` 1106 tests, 87.42% coverage)
- [ ] `make lint` and `make typecheck` clean (ruff + pyright 0 errors)

---

## How to invoke

```bash
/ultrareview
```

Run at repo root inside an active Claude Code session. No flags needed.

---

## Focus areas — what to read carefully in the review output

### `src/skyherd/agents/_handler_base.py` — prompt-cache fix
The base handler implements `build_cached_messages()` which wraps the system prompt and each skill block in `cache_control: {"type": "ephemeral"}`. Verify that the review confirms cache blocks are applied in the correct order (system → skills → event payload) and that the ephemeral cache is not accidentally applied to the volatile event payload (which would waste a cache slot on data that changes every wake).

### `src/skyherd/agents/managed.py` — real Managed Agent wiring
This is the real `anthropic.beta.managed_agents` integration, not a simulation. The review should confirm that session lifecycle (wake → tool calls → sleep) is handled correctly and that `CostTicker.set_state()` transitions match the actual API session states. Check for any fire-and-forget task leaks in `AgentMesh`.

### `src/skyherd/drone/sitl_emulator.py` + `pymavlink_backend.py` — pure-Python MAVLink
These two files implement the ArduPilot SITL connection without any C extension dependency. The review should confirm that the MAVLink dialect is correctly selected, that `asyncio.wait_for()` wraps all telemetry awaits (C5 fix), and that `DroneTimeoutError(DroneUnavailable)` hierarchy is consistently raised (not bare `Exception`) on timeout.

### `src/skyherd/server/webhook.py` — HMAC signature verification
This is the entry point for LoRaWAN webhook events from the MQTT bridge. The security review flagged HMAC verification as a HIGH item; the fix should be present and the review should confirm that the constant-time comparison (`hmac.compare_digest`) is used, not a plain `==`.

### `src/skyherd/attest/ledger.py` — Ed25519 Merkle chain
This module has been correct since initial implementation — it was the one that always did what it claimed. The review is confirming it has stayed that way. Verify the chain: each entry carries `prev_hash` (SHA-256 of the previous entry's canonical JSON), an Ed25519 signature over `payload + prev_hash`, and that `verify()` raises on any tampered entry. This is the insurance-grade record; it needs to be bulletproof.

---

## Known-yellow items — do not reclassify as blocking

These three items were accepted by the architect review. If `/ultrareview` surfaces them, note them and move on:

1. **`events.py:353` internal `_tickers` access** — direct access to a private attribute of the CostTicker registry. Accepted: the access is within the same module boundary and refactoring would add complexity without safety benefit.

2. **R2a pre-existing internal-attribute accesses** — a small set of `_private` attribute reads across the sensor bus and world simulation. Accepted as pre-existing technical debt; not blocking for hackathon scope.

3. **pyright: 15 third-party stub warnings** — missing type stubs for `pymavlink`, `elevenlabs`, and `aiomqtt` optional extras. These are non-blocking. pyright is configured with `reportMissingModuleSource = "none"` for these. Do not attempt to add stubs during the hackathon window.

---

## What a good ultrareview pass looks like

A passing `/ultrareview` should:
- Confirm no new CRITICAL or HIGH issues in the five focus files
- Surface the three known-yellows without escalating them
- Note coverage at 87%+ (above the 80% floor)
- Note the sim gate 10/10 status
- Not flag the HMAC webhook, cache ordering, or Merkle chain as open issues (all three are fixed)

If a new CRITICAL surfaces, stop and address it before submission. If a new HIGH surfaces, evaluate whether it touches a demo-path code path — if yes, fix it; if no, document and accept.

---

## After the review

Update `PROGRESS.md` if the review changes any item status. The submission deadline is 2026-04-26 8 pm EST. Reserve the final 24 hours for demo video recording, not code changes.
