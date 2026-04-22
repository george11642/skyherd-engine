---
phase: 3
slug: code-hygiene-sweep
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-22
updated: 2026-04-22 (post-planning)
---

# Phase 3 — Validation Strategy

> Per-phase validation contract. See "Validation Architecture" section of `03-RESEARCH.md` for full test specs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio (`asyncio_mode = "auto"`) + pytest-cov 7.1.0 + ruff + pyright |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/agents/test_cost.py tests/voice/ tests/sensors/ tests/edge/ tests/drone/ -x --no-cov` |
| **Full suite command** | `uv run pytest --cov=src/skyherd --cov-fail-under=80 && uv run pyright src/skyherd/drone/ src/skyherd/sensors/ src/skyherd/voice/ src/skyherd/edge/ src/skyherd/server/ src/skyherd/scenarios/ src/skyherd/agents/cost.py && uv run ruff check src/ tests/` |
| **Estimated runtime** | ~20-40s (quick) / ~3-5min (full with pyright) |

---

## Sampling Rate

- **After every task commit:** Quick run + category-specific test for the silent-except sweep category in flight (< 10s per test file).
- **After every plan wave:** Full suite + `rg 'except.*:\s*pass' src/skyherd/` must return only the 9 WONTFIX sites (Category 1 CancelledError + KeyboardInterrupt).
- **Before `/gsd-verify-work`:** Full suite + ruff clean + pyright clean (Phase-3-owned scope).
- **Max feedback latency:** ~30 seconds for single-task verification.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-T1 | 01 | 1 | HYG-02 | T-03-01 | Helper never logs token value; warning message is a static constant | unit + RED-first | `uv run pytest tests/voice/_twilio_env/test_twilio_env.py -x -v --no-cov` | ❌ Wave 0 (creates file) | planned |
| 01-T2 | 01 | 1 | HYG-02, HYG-01 (voice/call.py:200 Category-5 site) | T-03-02, T-03-03 | DEBUG log on OSError only — no token leak; `.env.example` placeholder-only | unit | `uv run pytest tests/voice/ tests/mcp/test_rancher_mcp.py -x --no-cov && ! grep -rn "TWILIO_TOKEN" src/skyherd/voice/call.py src/skyherd/demo/hardware_only.py src/skyherd/mcp/rancher_mcp.py .env.example docs/VOICE_ACCESS.md \| grep -v "TWILIO_AUTH_TOKEN" \| grep -v "legacy" \| grep -v "deprecated"` | ✅ `tests/voice/test_call.py` exists; RED new class added | planned |
| 02-T1 | 02 | 1 | HYG-01 | T-03-05, T-03-06 | `%s` format on exc; no raw payload bytes logged | unit caplog (RED-first) | `uv run pytest tests/sensors/test_bus.py::test_close_client_warns_on_exit_error tests/sensors/test_bus.py::test_parse_payload_debug_log_on_malformed_json tests/edge/test_watcher.py::test_mqtt_close_warns_on_exit_error tests/voice/test_tts.py::test_mp3_decode_debug_log_on_pydub_failure tests/sensors/test_trough_cam.py::test_frame_render_debug_log_on_import_error -x --no-cov` | ✅ test files exist; RED tests added | planned |
| 02-T2 | 02 | 1 | HYG-01 | T-03-05, T-03-06, T-03-08 | Category-2 WARNING sites get observable audit trail; WONTFIX CancelledError left as-is | static grep + unit regression | `uv run pytest tests/sensors/ tests/edge/ tests/voice/ tests/server/ tests/scenarios/ -x --no-cov && ! grep -rEn "except Exception:\s*pass\s*$" src/skyherd/sensors/ src/skyherd/server/ src/skyherd/edge/ src/skyherd/scenarios/` | ✅ source files exist | planned |
| 03-T1 | 03 | 1 | HYG-03, HYG-05 | T-03-09, T-03-10 | Tests assert BEHAVIOR (topic/payload content, property values, loop counts), not just "no raise" | unit coverage gate | `uv run pytest tests/agents/test_cost.py --cov=skyherd.agents.cost --cov-report=term-missing --cov-fail-under=90 --no-cov-on-fail` | ✅ `tests/agents/test_cost.py` exists; 4 new classes appended | planned |
| 04-T1 | 04 | 1 | HYG-01 | T-03-12, T-03-13 | DEBUG-level drone logs; no credentials in mavsdk error messages | unit caplog (RED-first) + static grep | `uv run pytest tests/drone/test_f3_inav.py::test_telemetry_debug_log_on_transient_failure tests/drone/ -x --no-cov && ! grep -rEn "except Exception:\s*pass\s*$" src/skyherd/drone/ && ! grep -rEn "except OSError:\s*pass\s*$" src/skyherd/drone/` | ✅ `tests/drone/test_f3_inav.py` exists; RED test added | planned |
| 04-T2 | 04 | 1 | HYG-04, HYG-05 | T-03-11, T-03-14 | Each `# type: ignore` carries rationale; agents/ errors deferred to Phase 1 with documented handoff | static analysis + coverage | `uv run ruff check src/ tests/ && uv run pyright src/skyherd/drone/ src/skyherd/sensors/ src/skyherd/voice/ src/skyherd/edge/ src/skyherd/server/ src/skyherd/scenarios/ src/skyherd/agents/cost.py && uv run pytest --cov=src/skyherd --cov-fail-under=80 -x --no-cov-on-fail` | ✅ source files exist | planned |

---

## Wave 0 Requirements

All Wave-0 gaps are handled as RED-first tests INSIDE the plan tasks (not separated into a standalone Wave-0 plan). This is intentional: each plan's Task 1 is the RED-first step, Task 2 is GREEN.

- [x] `tests/agents/test_cost.py` — extend with 4 new test classes (MqttPublishCallback, LedgerCallback, Properties, RunTickLoopBody) — **Plan 03 Task 1**
- [x] `tests/voice/_twilio_env/test_twilio_env.py` — new test for `_get_twilio_auth_token()` helper + deprecation warning — **Plan 01 Task 1**
- [x] `tests/voice/conftest.py` — autouse fixture to reset `_DEPRECATION_EMITTED` cache — **Plan 01 Task 1**
- [x] `tests/voice/test_call.py` — `TestTwilioAuthTokenMigration` class with 3 new tests — **Plan 01 Task 2**
- [x] `tests/sensors/test_bus.py` — `test_close_client_warns_on_exit_error` + `test_parse_payload_debug_log_on_malformed_json` — **Plan 02 Task 1**
- [x] `tests/sensors/test_trough_cam.py` — `test_frame_render_debug_log_on_import_error` — **Plan 02 Task 1**
- [x] `tests/voice/test_tts.py` — `test_mp3_decode_debug_log_on_pydub_failure` — **Plan 02 Task 1**
- [x] `tests/edge/test_watcher.py` — `test_mqtt_close_warns_on_exit_error` — **Plan 02 Task 1**
- [x] `tests/drone/test_f3_inav.py` — `test_telemetry_debug_log_on_transient_failure` — **Plan 04 Task 1**
- [x] Verify `pyright` already configured in `pyproject.toml` (it is per audit)

---

## Manual-Only Verifications

*None — all hygiene targets have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (Wave 0 handled inline as RED-first tests)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (9 new test files/classes enumerated above)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (quick run); full CI < 5min
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
