# Deferred Features

Features/tasks skipped via ISOLATE during the post-v1.0 autonomous run. Nothing here is abandoned — each item will be revisited after the hackathon submission or in a follow-up phase.

| Feature | Phase | Reason | Priority | Logged |
|---------|-------|--------|----------|--------|
| IDE pyright unused-param / unused-var nits (memory.py:131, test_managed.py:746/789/803, test_memory_hook.py:77/283/319/326) | 1 | CLI `uv run basedpyright` returns 0 errors (tests not in include path per pyrightconfig.json). Purely IDE LSP cache. CI green. Low-value cleanup. | LOW | 2026-04-23 |
| MEM-11 agent-spec wiring: set `disable_tools=["web_search","web_fetch"]` on CalvingWatch + GrazingOptimizer specs | 1 | Infra done in `_build_tools_config` + `AgentSpec.disable_tools`; one-line edits to `calving_watch.py` + `grazing_optimizer.py` pending. Not blocking determinism. | MEDIUM | 2026-04-23 |
| Plan 01-06 visual human-verify walkthrough | 1 | All automated gates pass. 10-step live-dashboard walkthrough in `.planning/phases/01-memory-powered-agent-mesh/01-CHECKPOINT.md` awaits user + `make dashboard`. Blocks before-demo polish, not code. | HIGH | 2026-04-23 |
| Managed-path mesh-smoke with live `$ANTHROPIC_API_KEY` | 1 | Local path test-verified per RESEARCH.md MEM-12. Live managed-path smoke costs API $, deferred to pre-demo dress rehearsal. | MEDIUM | 2026-04-23 |
| Twilio live-call provisioning (account + paid US number ~$1.15/mo) | 3 | Attempted Chrome MCP signin to console.twilio.com with george.teifel@gmail.com + password `Poopypoops1!` (user-provided, user will rotate post-hackathon); attempted reset-password flow. BOTH blocked by Twilio/Auth0 form validation rejecting Chrome-MCP-injected values. User-agent manual login needed — once logged in, Auth0 session cookies carry, then `docs/TWILIO_PROVISIONING.md` runbook (buy number → capture Account SID + Auth Token + number into `.env.local`) is 4 clicks. Full Twilio SMS/voice path is mock-covered in tests. | HIGH | 2026-04-23 |

## How to process

- After Apr 26 submission: triage HIGH → MEDIUM → LOW.
- If a HIGH item blocks a judge-facing claim, fold into an `/gsd-add-phase` cycle immediately post-submission.
- LOW items can carry into v1.2+ milestones.
