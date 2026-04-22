# Managed Agents Migration Plan — Shim → Real Platform

*Written Apr 21 2026. Hackathon deadline: Apr 26 2026 8pm EST.*

---

## 1. Current State — The Shim

SkyHerd today ships a local "Managed-Agents-compat SHIM" built across five files:

| File | Role |
|------|------|
| `src/skyherd/agents/session.py` | `Session` dataclass + `SessionManager` (create/wake/sleep/checkpoint/restore/on_webhook) |
| `src/skyherd/agents/spec.py` | `AgentSpec` dataclass declaring name, system prompt, wake topics, MCP servers, skills, model |
| `src/skyherd/agents/mesh.py` | `AgentMesh` orchestrator — registers 5 sessions, routes MQTT events, runs cost tick loop |
| `src/skyherd/agents/cost.py` | `CostTicker` — 1 Hz async loop accumulating session-hour cost at $0.08/hr while `state == "active"` |
| `src/skyherd/agents/fenceline_dispatcher.py` | Handler template — calls `build_cached_messages()`, then `claude_agent_sdk.ClaudeSDKClient.query()` |

The shim emulates the platform behavior accurately: sessions transition `idle → active → idle`, costs are tracked, checkpoints are serialized to `runtime/sessions/{id}.json`, MQTT topics are wildcard-matched against `wake_topics`, and skills are loaded as prompt-cached system blocks via `build_cached_messages()`.

The critical distinction: **`claude_agent_sdk`** (the `.refs/` local package) wraps the Claude CLI via subprocess. It is NOT the `anthropic` Python package and does NOT speak to the Managed Agents platform API.

---

## 2. Target State — Real Platform

All five agents run as persistent `Agent` objects on the Anthropic platform, pinned to versioned configurations. Sessions are created via `client.beta.sessions.create(agent_id=...)`. Events stream bidirectionally over SSE. Idle sessions pause cost metering automatically; the platform enforces this without any local ticker loop. Custom tools (`page_rancher`, `launch_drone`, `play_deterrent`, `get_thermal_clip`) are handled host-side via `agent.custom_tool_use` events.

Target SDK: `anthropic` package, `client.beta.{agents,sessions,environments,vaults}.*` with beta header `managed-agents-2026-04-01`.

---

## 3. Platform Primitives Mapping

| Shim concept | Real MA primitive | Notes |
|---|---|---|
| `AgentSpec` | `agents.create(name, system_prompt, tools, skills, model)` | One-time; store returned `agent_id` |
| `Session` dataclass | `sessions.create(agent_id, ...)` | Platform manages lifecycle state |
| `SessionManager.create_session()` | `client.beta.sessions.create()` | Returns `session_id` |
| `SessionManager.wake()` | `client.beta.sessions.events.send(session_id, {"type": "user.text_input", ...})` | Called from MQTT bridge |
| `SessionManager.sleep()` | Implicit — session goes idle after response stream ends; explicit `sessions.archive()` to terminate |
| `SessionManager.checkpoint()` | Automatic — platform checkpoints internally; `runtime/sessions/*.json` not needed |
| `SessionManager.on_webhook()` | Your MQTT subscriber calls `events.send()` after topic-matching | Still your code; not a platform-native MQTT bridge |
| `CostTicker` / `run_tick_loop()` | Replaced by `span.model_request_end` events carrying `model_usage` dict + platform billing | Local ticker loop drops entirely |
| `build_cached_messages()` — manual `cache_control` blocks | Automatic — platform caches system prompt + skills prefix automatically | Remove `build_cached_messages()` |
| `claude_agent_sdk.ClaudeSDKClient.query()` | `client.beta.sessions.events.stream(session_id)` async generator | Core handler swap |
| `AgentSpec.skills` (file paths) | `skills=[{"type": "custom", "skill_id": "..."}]` on `agents.create()` | Upload skill content via Files API first |
| `AgentSpec.mcp_servers` (name list) | `tools=[{"type": "url", "name": "...", "url": "..."}]` on `agents.create()` | Servers must be publicly reachable HTTPS |
| Twilio/ElevenLabs credentials | NOT in Vaults (Vaults = MCP OAuth only); credentials stay in env or custom tool host | Vaults scope to MCP server URLs only |
| `agent_toolset_20260401` | Declare on agent; gives bash, read, write, edit, glob, grep, web_fetch, web_search | Free built-in set |

**NO PLATFORM PATH — requires workaround:**
- **MQTT as wake transport**: platform has no native MQTT listener; your `SensorBus` subscriber must call `events.send()` to bridge MQTT → MA session.
- **MCP servers (drone_mcp, sensor_mcp, rancher_mcp, galileo_mcp)**: need publicly reachable HTTPS URLs. Use Cloudflare Tunnel (`cloudflared tunnel`) from localhost during hackathon week.
- **`page_rancher` tool**: keep as a custom tool handled client-side — no public URL required, handled via `agent.custom_tool_use` SSE event.

---

## 4. File-by-File Migration Diff Sketch

### `src/skyherd/agents/session.py`
**Delete**: `Session` dataclass, `SessionManager`, `build_cached_messages()`, `_load_text()`, all checkpoint I/O.  
**Replace with**: thin wrapper that calls `client.beta.sessions.create(agent_id=...)` and stores `session_id` → `agent_name` mapping. Keep `on_webhook()` as MQTT bridge calling `events.send()`.

### `src/skyherd/agents/spec.py`
**Delete**: `AgentSpec.skills` (file paths), `wake_topics` (stays in bridge, not on platform agent object), `checkpoint_interval_s`, `max_idle_s_before_checkpoint`.  
**Replace with**: a one-time `agents_create()` call that serializes spec fields into `agents.create(name, system_prompt, tools, skills, model)` and persists the returned `agent_id` to `runtime/agent_ids.json`.

### `src/skyherd/agents/mesh.py`
**Delete**: `SessionManager` instantiation, `run_tick_loop()`, `all_tickers()`.  
**Replace with**: MQTT → `events.send()` bridge. `AgentMesh.start()` loads `agent_ids.json`, subscribes to MQTT, and routes events. `smoke_test()` calls `sessions.create()` + `events.send()` + reads SSE stream.

### `src/skyherd/agents/cost.py`
**Delete**: `CostTicker`, `run_tick_loop()`, all local pricing constants.  
**Replace with**: `cost.py` now reads `span.model_request_end` events from the SSE stream and accumulates `model_usage.input_tokens` / `output_tokens` for the dashboard. Session-hour cost comes from platform billing; local tick loop is redundant.

### `src/skyherd/agents/fenceline_dispatcher.py` (and all 4 other handlers)
**Delete**: `from claude_agent_sdk import ...`, `build_cached_messages()` call, `_run_with_sdk()`, `_simulate_handler()` passthrough.  
**Replace `_run_with_sdk()` with**:
```python
async def _run_with_sdk(session_id: str, wake_event: dict, client: Anthropic) -> list[dict]:
    calls = []
    async with client.beta.sessions.events.stream(session_id) as stream:
        async for event in stream:
            if event.type == "agent.custom_tool_use":
                result = await _dispatch_tool(event.tool_use)
                calls.append({"tool": event.tool_use.name, "input": event.tool_use.input})
                await client.beta.sessions.events.send(session_id, {
                    "type": "user.custom_tool_result",
                    "tool_use_id": event.tool_use.id,
                    "content": result,
                })
            elif event.type == "span.model_request_end":
                session.cumulative_tokens_in += event.model_usage.get("input_tokens", 0)
    return calls
```

---

## 5. Prerequisites

1. `pip install anthropic` — confirmed includes `client.beta` MA surface.
2. `ANTHROPIC_API_KEY` in env — beta access enabled by default for all API accounts; no special enrollment needed for hackathon week.
3. Cloudflare Tunnel for each MCP server: `cloudflared tunnel --url http://localhost:{port}`. Required for `drone_mcp` (port 8001), `sensor_mcp` (8002), `rancher_mcp` (8003), `galileo_mcp` (8004). One tunnel per server; each must return a stable `*.trycloudflare.com` URL before `agents.create()` is called.
4. Run `agents.create()` once per agent and persist `agent_ids.json` to `runtime/`. Never call `agents.create()` in the request path.
5. Skills upload: convert skill `.md` files from `skills/` to Files API uploads; store returned `file_id` values for the `skill_id` references.

---

## 6. Rollout Plan

**Phase 0 — Parallel (today, Apr 21)**  
Tunnel all 4 MCP servers. Run `agents.create()` for all 5 agents. Write `runtime/agent_ids.json`. Keep shim running in parallel.

**Phase 1 — Handler swap (Apr 22–23)**  
Swap `_run_with_sdk()` in all 5 handlers to `events.stream()` loop. Shim `SessionManager` still manages state locally as fallback. Run `make mesh-smoke` — all 5 wake events must produce non-empty tool-call lists from real platform.

**Phase 2 — Shim teardown (Apr 24)**  
Delete `SessionManager`, `CostTicker`, `build_cached_messages()`. Wire `AgentMesh` directly to `client.beta.sessions.*`. Re-run full demo: `make demo SEED=42 SCENARIO=all`.

**Phase 3 — Cost dashboard (Apr 24–25)**  
Replace local tick loop with `span.model_request_end` event reader. Verify dashboard cost ticker still updates during active sessions and visibly pauses during idle stretches.

**Phase 4 — Submission gate (Apr 25 noon)**  
`make ci` green. `make demo SEED=42 SCENARIO=all` byte-identical replay. Update `MANAGED_AGENTS.md` to remove any shim caveats. Record 3-min demo video showing real platform sessions.

---

## 7. Cost Model Comparison

| Metric | Shim (estimated) | Real Platform |
|---|---|---|
| Session-hour billing | Simulated locally at $0.08/hr | Actual platform billing at $0.08/hr active |
| Input token rate | $15.00/M (local estimate) | $15.00/M (platform actual, Opus 4.7) |
| Output token rate | $75.00/M (local estimate) | $75.00/M (platform actual) |
| Prompt cache hit | $1.50/M (local estimate) | $1.50/M (automatic — no manual `cache_control` needed) |
| Weekly ranch cost | ~$4/week projected | ~$4/week expected (same model + idle-pause) |
| Cold start penalty | None (local) | ~60s first session creation; use `prewarm: true` on create |

The $4/week figure in `MANAGED_AGENTS.md` is accurate assuming idle-pause is working correctly — the real platform enforces this automatically, which is stronger than the local shim's manual `state == "active"` gate.

---

## 8. Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Cloudflare Tunnel unstable during demo | HIGH | Pre-generate 4 stable named tunnels; add health check to `make demo` |
| Cold-start latency (60s) breaks <30s FenceLineDispatcher SLA | MEDIUM | `prewarm: true` on session create; keep sessions warm during demo |
| MQTT → `events.send()` bridge message ordering | MEDIUM | Single sequential MQTT handler per session; async queue with backpressure |
| Skills upload quota / file ID expiry | LOW | Upload once, persist IDs; re-upload only if API returns 404 |
| `agent_ids.json` missing on fresh clone | LOW | `make demo` prereq check; `agents.create()` is idempotent by name |
| Rate limits (60 create RPM / 600 read RPM) | LOW | 5 agents × 1 create each = well within limits |

---

## 9. Acceptance Criteria

- [ ] `make ci` passes (ruff + pyright + pytest, 80%+ coverage).
- [ ] `make demo SEED=42 SCENARIO=all` completes all 5 scenarios against real platform sessions (not shim).
- [ ] Dashboard cost ticker increments during active wake cycles and freezes between events.
- [ ] `runtime/agent_ids.json` present and all 5 `agent_id` values resolvable via `client.beta.agents.retrieve()`.
- [ ] `skyherd-attest verify` passes — attestation chain intact after real-platform tool calls.
- [ ] No references to `claude_agent_sdk` remain in non-test source after Phase 2.
- [ ] `docs/MANAGED_AGENTS.md` updated to state platform-native (not shim-emulated).

---

## 10. Fallback

If Cloudflare Tunnels fail on demo day or cold-start latency breaks the <30s SLA: fall back to custom-tool-only mode. Remove `tools=[{"type": "url", ...}]` MCP declarations from agents. Keep `drone_mcp`, `sensor_mcp`, `rancher_mcp`, `galileo_mcp` as custom tools handled host-side alongside `page_rancher`. All four are already implemented as simulation stubs in `_simulate_handler()` — the custom tool host just calls those stubs. Real platform sessions still run; only the MCP transport changes.

This fallback still qualifies for "Best Use of Claude Managed Agents" — 5 persistent agents, real platform, real idle-pause billing, real SSE event stream, real Vaults for any OAuth credentials.

---

## 11. Open Questions for George

1. **Cloudflare Tunnel naming**: Use named tunnels (require `cloudflared` login + Cloudflare account) or quick `trycloudflare.com` throwaway tunnels? Named = stable across restarts; throwaway = no account needed but URL changes on restart.
2. **Skills upload**: Should skill content be uploaded as plain-text files via the Files API, or declared inline as `{"type": "custom", "skill_id": "...", "content": "..."}` if the platform supports inline content? Need to verify against live docs.
3. **`page_rancher` in Vaults**: Twilio credentials currently in env. Vaults only hold MCP OAuth / static bearer tokens scoped to MCP server URLs — confirm Twilio REST API credentials cannot use Vaults and must stay in env or a separate secrets manager.
4. **Deterministic replay (`make demo SEED=42`)**: The shim's simulation path produces byte-identical output because it never calls the API. Real platform responses are non-deterministic. Is the replay requirement relaxed to "same tool-call sequence shape" for the judging criteria, or should the shim simulation path be preserved for the replay scenario only?
5. **`agent_ids.json` in git**: Commit `runtime/agent_ids.json` for portability (judge can clone and run without re-creating agents) or `.gitignore` it and document how to regenerate? Prefer committed given the hackathon one-clone judge quickstart requirement in `CLAUDE.md`.
