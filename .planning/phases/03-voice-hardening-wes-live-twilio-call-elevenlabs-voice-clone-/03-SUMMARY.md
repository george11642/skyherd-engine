---
phase: 03
plan: all
status: complete
completed: 2026-04-23
plans: 3/3
tests_before: 1420
tests_after: 1438
coverage_voice: 96.43% (target >= 90%)
coverage_rancher_mcp: 82% (target >= 80%)
coverage_combined: 92.45%
twilio_status: deferred_awaiting_user
elevenlabs_status: configured + hash-QA
chrome_mcp_used: no
determinism: PASS (2/2)
---

# Phase 03 — Voice Hardening — SUMMARY

## Scope shipped

1. **`SKYHERD_VOICE=live|mock|silent` env flag** — wired into `_resolve_backend()`
   + `render_urgency_call()`. `mock|silent` forces `SilentBackend` and skips
   Twilio even when full creds are set; `live` keeps the priority chain
   ElevenLabs → piper → espeak → silent; unset defaults to chain; invalid
   values log a WARNING and fall through.
2. **Synthesize-failure fallback** — `render_urgency_call` wraps
   `backend.synthesize()` in try/except; any exception logs a WARNING and
   retries with `SilentBackend`, guaranteeing the demo never crashes.
3. **Pytest conftest default** — `tests/voice/conftest.py` autouse sets
   `SKYHERD_VOICE=mock`; tests that need live-chain behavior override via
   `monkeypatch.setenv("SKYHERD_VOICE", "live")` in their own body.
4. **Fallback-chain cascade coverage** — parametrized tests walk all 4
   resolution states (EL set → EL; EL unset + piper → Piper; EL unset + espeak
   only → Espeak; nothing → Silent).
5. **SMS + voice-call success paths** — new `tests/mcp/test_rancher_mcp_sms.py`
   covers urgency=text (SMS success + SMS failure → log fallback),
   urgency=call (voice channel), urgency=emergency (voice), page_vet text +
   emergency paths, with injected fake `twilio.rest` module.
6. **ElevenLabs voice-clone QA** — `tests/voice/test_voice_clone_qa.py`:
   - SHA-256 fixture pinning SilentBackend output (8044 bytes, 250ms @ 16kHz mono).
   - SHA-256 fixture pinning fake-ElevenLabs → WAV fallback path (512 bytes).
   - Chunked vs single-chunk invariant.
   - Non-bytes chunk filtering.
   - Opt-in live smoke via `ELEVENLABS_CLONE_QA=1` (skipped in CI).
7. **`skyherd-voice demo` CLI expanded to 5 urgency levels** — log, text,
   call, emergency, silent; graceful handling of `wav_path=None`.
8. **`make voice-demo` target** — defaults `SKYHERD_VOICE=mock`,
   video-B-roll-friendly.
9. **Twilio provisioning runbook** — `docs/TWILIO_PROVISIONING.md` — 7-step
   signup → number → env → tunnel → verify. Explains why automation stops at
   paid resource purchase.
10. **Deferred-features entry** — Twilio live-call HIGH priority, links runbook.

## Plans completed

| Plan | Focus | Status | Commit |
|------|-------|--------|--------|
| 03-01 | SKYHERD_VOICE flag + cascade tests + SMS coverage | PASS | `8171b65` |
| 03-02 | ElevenLabs voice-clone QA (hash-based) | PASS | `44ec0a2` |
| 03-03 | voice-demo target + 5-urgency CLI + Twilio runbook | PASS | `c8db47d` |

Plus `52f60c3 docs(03): auto-generated context + 3-plan breakdown`.

## Requirements (VOICE-01 .. VOICE-07)

| Req | Summary | Status |
|-----|---------|--------|
| VOICE-01 | Twilio credentials — documented provisioning runbook | PASS (runbook shipped) |
| VOICE-02 | Twilio number provision | DEFERRED (HIGH, needs user CONFIRM) |
| VOICE-03 | ElevenLabs voice-clone QA | PASS (hash-based, 2 fixtures) |
| VOICE-04 | Live-call path coverage | PASS (SMS + voice + fallback) |
| VOICE-05 | Fallback chain exhaustive test | PASS (4-state parametrized + synth-failure) |
| VOICE-06 | `SKYHERD_VOICE` flag | PASS (live/mock/silent) |
| VOICE-07 | `make voice-demo` + 5-urgency CLI demo | PASS |

## Files shipped

**New (Python tests + fixtures):**
- `tests/voice/test_voice_clone_qa.py` (~180 lines, 9 tests, 8 run + 1 opt-in skip)
- `tests/voice/fixtures/wes_reference_silent.sha256`
- `tests/voice/fixtures/fake_elevenlabs_wav.sha256`
- `tests/mcp/test_rancher_mcp_sms.py` (~205 lines, 7 tests)

**New (docs):**
- `docs/TWILIO_PROVISIONING.md` (~155 lines)

**Modified:**
- `src/skyherd/voice/tts.py` — `SKYHERD_VOICE` branch in `_resolve_backend` +
  `_VOICE_MODE_MOCK` / `_VOICE_MODE_LIVE` constants.
- `src/skyherd/voice/call.py` — `_voice_mode_is_mock`, `_should_attempt_twilio`,
  synthesize-failure fallback.
- `src/skyherd/voice/cli.py` — 5-urgency demo + log-only branch.
- `tests/voice/conftest.py` — autouse `default_voice_mock` fixture.
- `tests/voice/test_get_backend.py` — +11 tests (SKYHERD_VOICE flag + cascade).
- `tests/voice/test_call.py` — +7 tests (skip-twilio + synth-fallback).
- `tests/voice/test_cli.py` — 5-urgency assertions + log-only handling.
- `Makefile` — `voice-demo` target.
- `.planning/deferred-features.md` — Twilio HIGH row.

## Commits (4 atomic, including docs)

1. `52f60c3 docs(03): auto-generated context + 3-plan breakdown`
2. `8171b65 feat(03-01): SKYHERD_VOICE=live|mock|silent + fallback cascade + SMS coverage`
3. `44ec0a2 feat(03-02): ElevenLabs voice-clone QA (hash-based, zero new deps)`
4. `c8db47d feat(03-03): make voice-demo + 5-urgency CLI demo + Twilio provisioning runbook`

## Metrics

- Tests: 1420 → 1438 (+18 passing). 16 skipped (includes 1 new: opt-in
  ElevenLabs live smoke).
- New Python code: ~385 LOC tests + ~25 LOC src modifications.
- New docs: ~155 lines (Twilio runbook).
- Coverage: `skyherd.voice` 96% (target 90%), `rancher_mcp` 82% (target 80%),
  combined 92%.
- Determinism: `tests/test_determinism_e2e.py` 2/2 PASS (bytes-identical
  demo SEED=42 × 3).
- `make voice-demo`: 5 urgency lines + wav paths in <1s.
- No new runtime dependencies.
- Zero-attribution commits preserved.

## Chrome MCP usage

**Not used.** Scope rule: no paid-resource purchase without explicit user
CONFIRM. Without user presence + SMS verification code, a Twilio signup
flow cannot complete automatically. Documented provisioning via
`docs/TWILIO_PROVISIONING.md` instead — the code path is already fully
tested via mocked `twilio.rest.Client` injection.

## Deferred

| Item | Priority | Reason | Unblocker |
|------|----------|--------|-----------|
| Twilio account signup + paid US number (~$1.15/mo) | HIGH | SMS verification + paid resource → user CONFIRM required | Run `docs/TWILIO_PROVISIONING.md` steps 1-4 before live video shoot |
| `CLOUDFLARE_TUNNEL_URL` for TwiML `<Play>` WAV hosting | HIGH | Ephemeral; regenerate per session | Run `cloudflared tunnel --url http://127.0.0.1:8000` on demo day |
| Live ElevenLabs smoke (`ELEVENLABS_CLONE_QA=1`) | LOW | Costs API credits; hash-QA catches drift offline | Set env var in pre-demo dress rehearsal |

## Ready for Phase 4

Yes. All automated gates pass. Phase 3 is complete and the live voice-call
path is documented for the user to activate when ready for the video shoot.
No blocking changes; Phase 4 (Attestation Year-2) can proceed independently.
