# Managed Agents — LIVE Evidence

**Status: GATE #1 TRULY-GREEN (live platform)**

Timestamp: `2026-04-22T15:49:39Z`
HEAD SHA: `c04ce2804a8a43cf166c486bb3ffa20cbcb3e396` (short `c04ce28`)
API Key prefix: `sk-ant-api...DQAA` (length 108, sanitized — never committed)
Runtime: `ManagedSessionManager` (SDK `anthropic` beta namespace)
Beta header: `managed-agents-2026-04-01` (set automatically by SDK on `client.beta.*`)

## 1. API Reachability

`GET /v1/models` — HTTP 200.
First model returned: `claude-opus-4-7` (1M context, 128K max output).

## 2. Beta Access Probe

`GET /v1/agents` with header `anthropic-beta: managed-agents-2026-04-01` — HTTP 200.
Response body shape: `{"data": [...]}` — **beta access is enrolled and active**.

`GET /v1/sessions` with same beta header — HTTP 200.

## 3. Runtime Resolution

```
AUTO_RUNTIME: ManagedSessionManager
MANAGED_RUNTIME: ManagedSessionManager
KEY_SET: True
FLAG_SET: managed
```

`get_session_manager("auto")` correctly returns `ManagedSessionManager` when
both `ANTHROPIC_API_KEY` and `SKYHERD_AGENTS=managed` are set. No factory
bug — no fix required.

## 4. Live Smoke Test — Session Creation

All 5 SkyHerd agents created as persisted platform agent objects (v=1),
with 5 matching live sessions attached to a shared `skyherd-ranch-env`
environment.

### Platform Agents (sanitized, first 12 chars)

| Agent name              | Agent ID prefix   | Version |
| ----------------------- | ----------------- | ------- |
| FenceLineDispatcher     | `agent_011CaK` | 1 |
| HerdHealthWatcher       | `agent_011CaK` | 1 |
| PredatorPatternLearner  | `agent_011CaK` | 1 |
| GrazingOptimizer        | `agent_011CaK` | 1 |
| CalvingWatch            | `agent_011CaK` | 1 |

### Platform Sessions (sanitized, first 8 chars)

| Session title                      | Session ID prefix | Status |
| ---------------------------------- | ----------------- | ------ |
| skyherd-FenceLineDispatcher        | `sesn_011` | idle |
| skyherd-HerdHealthWatcher          | `sesn_011` | idle |
| skyherd-PredatorPatternLearner     | `sesn_011` | idle |
| skyherd-GrazingOptimizer           | `sesn_011` | idle |
| skyherd-CalvingWatch               | `sesn_011` | idle |

### Environment

| Name | ID prefix |
| ---- | --------- |
| `skyherd-ranch-env` | `env_011c6NSU` |

IDs are persisted locally at (gitignored):
- `runtime/agent_ids.json` — name → platform agent ID map
- `runtime/ma_environment_id.txt` — cached environment ID

These are cached so `ensure_agent()` and `_ensure_environment()` are
idempotent on restart — no duplicate agents created.

## 5. End-to-End Round-Trip

Sent `user.message` to `skyherd-CalvingWatch` session with body
`"Respond with exactly: ACK SMOKE TEST"`, opened SSE stream first
(stream-first ordering per SDK guidance), read events until
`session.status_idle` with a terminal stop reason.

```
Using session sesn_011CaK5Af7k... (skyherd-CalvingWatch)
EVENTS_RECEIVED: 6
AGENT_REPLY: 'ACK SMOKE TEST'
```

Full bidirectional flow verified: user message in, agent reply out.

## 6. Cloudflared Tunnel (Webhooks)

Not started. `cloudflared` is not installed on the WSL host (`which cloudflared` → not found).

This is a George-side step; sudo install was not attempted. Webhook
endpoint (`POST /webhooks/managed-agents`, HMAC-SHA256 via
`SKYHERD_WEBHOOK_SECRET`) is wired in `src/skyherd/agents/webhook.py`
and ready to receive events once a public URL is bound.

To complete: install cloudflared, run
`bash scripts/cloudflared-setup.sh`, capture the `trycloudflare.com`
URL, and register it in the Anthropic console for the 5 managed agents.

## 7. What George Still Has to Do

1. **Install `cloudflared`** (apt/snap) and start the tunnel to publicly
   expose `/webhooks/managed-agents`.
2. **Register the webhook URL** in the Anthropic console against the 5
   agents so platform-side `agent.custom_tool_use` events route back into
   the mesh.
3. That's it — no pending charges, no console approvals required. Beta
   access is already enrolled.

## Verdict

**Gate #1 TRULY-GREEN (live platform).** Wiring correct; platform API
reachable; beta enrolled; 5 real agent objects and 5 real session objects
exist on the platform; full send+stream round-trip verified with live
token-generating agent response. Webhooks path is the only deferred piece
and it is a George-side install step, not a code gap.
