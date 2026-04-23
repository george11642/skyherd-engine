# SkyHerd Autonomous Resume Sheet

**Last updated:** 2026-04-23 (Phase 1 in flight — pattern-mapper dispatched)
**Deadline:** 2026-04-26 20:00 EST (target 18:00 EST)
**Current invocation:** `/gsd-do research online claude … → /gsd-add-phase → /gsd-autonomous`

## How to resume in a fresh Claude Code session

```bash
cd /home/george/projects/active/skyherd-engine
git status         # see what's in flight
git log --oneline -20   # see what landed
cat .planning/STATE.md  # current phase + progress
cat .planning/RESUME.md # this file
```

Then, depending on where we are:

### If Phase 1 not yet planned

```
/gsd-plan-phase 1 --auto
```

### If Phase 1 planned but not executed

```
/gsd-execute-phase 1 --no-transition
```

### If Phase 1 executed, iterating 2-9

Read the Phase Board below; whichever phase has `status: ready_to_execute`, run:

```
/gsd-execute-phase <N> --no-transition
```

Or to chain all remaining:

```
/gsd-autonomous --from <next_incomplete>
```

## Phase Board

| # | Name | Status | Next command |
|---|---|---|---|
| 1 | Memory-Powered Agent Mesh | researching → planning | `/gsd-plan-phase 1 --auto` after pattern-mapper |
| 2 | Cross-Ranch Mesh Promotion | empty | `/gsd-plan-phase 2 --auto` |
| 3 | Voice Hardening | empty | `/gsd-plan-phase 3 --auto` |
| 4 | Attestation Year-2 | empty | `/gsd-plan-phase 4 --auto` |
| 5 | Hardware H1 software prep | empty | `/gsd-plan-phase 5 --auto` |
| 6 | Hardware H2 software prep | empty | `/gsd-plan-phase 6 --auto` |
| 7 | Hardware H3 software prep | empty | `/gsd-plan-phase 7 --auto` |
| 8 | Hardware H4 software prep | empty | `/gsd-plan-phase 8 --auto` |
| 9 | Demo Video Scaffolding | empty | `/gsd-plan-phase 9 --auto` |

## Key facts (don't re-research)

- **Memory API is REST-only in Python.** `anthropic==0.96.0` does NOT expose `client.beta.memory_stores`. Use `client.post()` / `client.get()` with `anthropic-beta: managed-agents-2026-04-01` header. REST spike verified 2026-04-23 20:10 UTC — see `.planning/phases/01-memory-powered-agent-mesh/01-CONTEXT.md` `<spike_findings>` section.
- **Endpoints:** `POST /v1/memory_stores` · `POST /v1/memory_stores/{id}/memories` · `GET /v1/memory_stores/{id}/memories` · `GET /v1/memory_stores/{id}/memory_versions` · `POST /v1/memory_stores/{id}/archive`
- **Determinism is sacred.** `make demo SEED=42 SCENARIO=all` must remain byte-identical. Memory calls stubbed in `LocalSessionManager`; real API gated on `SKYHERD_AGENTS=managed`.
- **Workspace-scoped stores** enable cross-agent coordination (1 shared read-only + 5 per-agent read_write).
- **Phase 3 (Voice) uses Chrome MCP** for Twilio signup/number provision. Load via `ToolSearch query="mcp__claude-in-chrome"` — do NOT shell `claude --chrome`.
- **Hardware phases 5-8 are SOFTWARE-ONLY prep.** Actual Pi flashing, Mavic pairing, collar soldering, and field testing remain manual. The goal is "one-command-to-live" when hardware arrives.
- **Phase 9 scaffolds the video** — script, shot list, submission form draft. User still shoots + edits.
- **workflow.skip_discuss=true** is set globally — discuss phase auto-generates CONTEXT.md from ROADMAP goals. This is intentional for autonomous mode.

## Environment

- `.env.local` has `ANTHROPIC_API_KEY` (108 chars, verified). Use it for Memory REST + any `anthropic` API work.
- No `TWILIO_*` creds yet — Phase 3 will provision via Chrome MCP (requires user presence for SMS verification step).
- `uv sync` + `(cd web && pnpm install)` are already done.
- Test command: `uv run pytest -x -q` (1262 passing as of last run).
- Coverage floor: 80%.
- Determinism test: `uv run pytest tests/test_determinism_e2e.py -v -m slow`.

## Context-preservation reminders

- Every planner / executor / checker / reviewer call goes through a subagent (Task / Skill). Never inline multi-file code edits unless <3 files.
- Agent skills are cached — pass `AGENT_SKILLS_*` via files, not inline strings (see `/tmp/agent-skills-*.txt` if still present).
- Commit after every logical unit so `git log` can replay.
- When main context crosses ~70%, checkpoint to this file and hand off.

## Open assumptions (from research)

- **A1 (Phase 1):** `sessions.create(resources=[{"type": "memory_store", ...}])` likely needs `extra_body=` because SDK 0.96 typed `Resource = Union[GitHubRepository, File]`. First 5 min of Phase 1 execution: probe this with a throwaway session. If A1 wrong → attach memstore via a different API path or per-agent `tools` configs instead.

## What NOT to do

- Do not rename `managed-agents-2026-04-01` to anything else — the SDK auto-applies it and Memory rides on the same header.
- Do not migrate skills/ to Memory. Skills stay packaged CrossBeam-style; Memory is for learned mutable facts.
- Do not `--no-verify` any commit. Pre-commit hooks surface real issues.
- Do not introduce AGPL deps (Ultralytics/YOLOv12). MegaDetector V6 only for vision.
- Do not attempt hardware phases H1-H4 with real hardware — that's post-hackathon. Phase 5-8 ship SOFTWARE ONLY, tested against mocks/SITL.
- Do not post LinkedIn or spend real money without explicit user CONFIRM (per global CLAUDE.md).
