# Phase 03 Context — Voice Hardening (Wes live Twilio call + ElevenLabs voice-clone QA)

**Phase:** 03
**Goal:** Harden the Wes cowboy-persona voice chain so the live-call path is demo-ready — Twilio provisioning documented (creds-gated), ElevenLabs voice-clone QA test, failover coverage, and a `SKYHERD_VOICE=live|mock|silent` toggle.
**Depends on:** Phase 01 (determinism + Memory topology), Phase 02 (working pattern for atomic-plan + SUMMARY). No Phase 02 code is imported; this phase is voice-module-local.
**Deadline:** 2026-04-26 20:00 EST.

## User's vision (from phase mission)

> Video-ready Wes voice: when the judge watches a coyote scenario fire, they hear Wes page the boss in a cowboy tone. The fallback chain (ElevenLabs → piper → espeak → silent) never crashes the demo. Twilio provisioning is either done (free-tier if available) or *crystal-clearly documented* for manual completion; no surprise $1.15/mo charges.

## Existing voice chain (pre-Phase 3)

`src/skyherd/voice/`:
- `tts.py` — `ElevenLabsBackend` → `PiperBackend` → `EspeakBackend` → `SilentBackend`. `get_backend()` picks the highest-priority available. `_resolve_backend()` is the pure resolver.
- `wes.py` — `WesMessage` pydantic model + `wes_script()` template engine. Strong existing AI-telltale sanitizer.
- `call.py` — `render_urgency_call()` pipeline. Twilio path gated on `TWILIO_SID/AUTH_TOKEN/FROM/CLOUDFLARE_TUNNEL_URL` + `DEMO_PHONE_MODE != "dashboard"`. Emits `rancher.ringing` SSE.
- `_twilio_env.py` — TWILIO_AUTH_TOKEN canonical / TWILIO_TOKEN legacy.
- `cli.py` — `skyherd-voice say|demo` CLI.

`src/skyherd/mcp/rancher_mcp.py` — `page_rancher` MCP tool. SMS via `_try_send_sms` (Twilio messages API), voice via `_try_voice_call` (delegates to `render_urgency_call`).

**Existing tests:** `tests/voice/` — 7 files, test_call.py covers Twilio call mock + dashboard ring; test_get_backend.py covers chain selection; test_tts.py covers SilentBackend/ElevenLabs/piper/espeak error paths; test_wes.py covers script templating.

## Current state

- `.env.local`: `ELEVENLABS_API_KEY` set (free-tier). `TWILIO_*` **not** set.
- Baseline: **1422 tests collected**, coverage 88.96% (Phase 02 exit).
- `make` targets: no `voice-demo` yet. `hardware-demo` runs real combo but no voice-only B-roll target.
- `SKYHERD_VOICE` env flag: does **not exist** — backend chain only reads TTS-specific vars.

## Twilio status (decision)

**No Twilio credentials in `.env.local`, no account cookies visible, and scope hard-rule is "no paid purchase without user CONFIRM".**

Phase 03 will **not** attempt Chrome MCP signup under this run because:
1. Signup requires phone-number SMS verification — user presence required.
2. Free trial number allocation requires identity verification not automatable.
3. The hard rule is explicit: no number purchase without CONFIRM.

Instead: ship `docs/TWILIO_PROVISIONING.md` with exact copy-pasteable commands the user runs once, plus a `deferred-features.md` entry flagged HIGH for pre-demo. The Twilio *code path* is already fully tested via `twilio.rest.Client` mock in `test_call.py`; provisioning is an ops step, not a code step. This keeps the hackathon submission green: sim-perfect fallback + documented live path.

## ElevenLabs QA approach (lightweight, MIT, no heavy deps)

Rejected: librosa MSE (heavy), whisper transcription (heavy, AGPL risk on some models).

Chosen: **deterministic hash + size-band check**. The QA test uses `SilentBackend` to synthesize a known-phrase, asserts:
- File is valid RIFF/WAV (header + sample-rate + channels).
- Duration in expected band (e.g., 200–400 ms for silent reference).
- SHA-256 matches a committed hex string for the silent reference (catches regressions in `_write_wav` or silence-generator).

For ElevenLabs specifically: the test is **mocked** (fake audio bytes via `monkeypatch.setitem(sys.modules, "elevenlabs", fake_module)`). A real-ElevenLabs smoke test is opt-in via `ELEVENLABS_CLONE_QA=1` so CI stays offline + deterministic.

A reference MP3 header pattern (committed to repo at `tests/voice/fixtures/wes_reference_silent.wav.sha256` — text file with hash only, not the audio blob) lets the QA test catch silent-backend drift.

## `SKYHERD_VOICE` env flag semantics

Wire in `src/skyherd/voice/tts.py::_resolve_backend()`:

| Value | Behavior |
|-------|----------|
| `live` (or unset in prod) | Current priority chain: ElevenLabs → piper → espeak → silent. |
| `mock` | Forces `SilentBackend` regardless of deps. Used in determinism tests + default in `pytest`. |
| `silent` | Alias of `mock` for readability; same effect. |

`render_urgency_call()` also reads `SKYHERD_VOICE=mock`: skips the Twilio attempt even if creds present (so tests that set TWILIO_* don't accidentally call out). Determinism preserved because `mock` routes through `SilentBackend` which already produces byte-identical silence.

Default in `conftest.py`: set `SKYHERD_VOICE=mock` at session scope so all 1422+ tests auto-use silent. Existing tests that explicitly test ElevenLabs / twilio paths override with `monkeypatch.setenv`.

## Fallback-chain coverage gap

Current tests cover individual backend errors (piper CalledProcessError, espeak timeout) but not the **cascade**: when ElevenLabs raises, does `_resolve_backend()` fall to piper, then espeak, then silent? Phase 03 adds a parametrized test that mocks each primary to fail and asserts the next is chosen.

## Demo target (`make voice-demo`)

- Plays 5 urgency lines back-to-back: `log`, `text`, `call`, `emergency`, `silent`.
- Uses `SilentBackend` by default (B-roll friendly — no audio output, just prints scripts).
- `SKYHERD_VOICE=live make voice-demo` exercises the real chain if creds + PATH tools present.
- Exits 0 always.

## Hard constraints

- **No real money spend** without user CONFIRM.
- **Determinism:** `make demo SEED=42 SCENARIO=all` must stay byte-identical. `SKYHERD_VOICE=mock` forces silent.
- **Coverage:** ≥80% overall, ≥90% on new voice code.
- **No new heavy deps.** No librosa, no whisper.
- **Prompt caching untouched** (voice is SDK-adjacent; no `messages.create` calls).
- **MIT-only.**
- **Zero-attribution commits** (global gitconfig).
- **Chrome MCP used:** NO (scoped out — see Twilio decision above).

## Execution pattern

3 plans, atomic commits. Each plan: write tests first (RED), implement (GREEN), refactor if needed (IMPROVE). Verify pytest + coverage + determinism between plans.

- **03-01** — `SKYHERD_VOICE=live|mock|silent` flag + fallback-chain cascade tests + SMS-path coverage expansion.
- **03-02** — ElevenLabs voice-clone QA (hash-based, mocked) + reference hash fixture.
- **03-03** — `make voice-demo` target + 5-line CLI demo + `docs/TWILIO_PROVISIONING.md` + deferred-features entry.

## Requirements

- **VOICE-01** Twilio credentials: documented provisioning runbook; `.env.local` keys standardized.
- **VOICE-02** Twilio number provision: deferred to manual step with exact commands.
- **VOICE-03** ElevenLabs voice-clone QA: hash-based determinism test on silent-backend reference + mocked EL output.
- **VOICE-04** Live-call path coverage: urgency=call+emergency exercises twilio mock; urgency=text exercises SMS mock.
- **VOICE-05** Fallback chain: parametrized cascade test ElevenLabs→piper→espeak→silent.
- **VOICE-06** `SKYHERD_VOICE` env flag: `live|mock|silent` in `_resolve_backend` + `render_urgency_call`.
- **VOICE-07** `make voice-demo` target + 5-urgency-line CLI demo.

## Non-goals

- Real Twilio number purchase (requires user CONFIRM + SMS verification).
- Real ElevenLabs voice-clone creation (free-tier works with premade "Adam" voice).
- LinkedIn / X / Discord posts announcing the voice feature (held for Phase 9 launch).
- Any change to `managed-agents-2026-04-01` beta header or prompt caching.
- Any change to `memstore_*` topology (Phase 01 owns that).
