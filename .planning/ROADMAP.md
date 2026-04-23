# Roadmap: SkyHerd Engine

**Current milestone:** none (v1.0 shipped 2026-04-23). Standalone post-v1.0 phases run without a formal milestone until `/gsd-new-milestone` is invoked.

v1.0 MVP Completion milestone is complete — 32/32 requirements satisfied, 10/10 Sim Completeness Gate GREEN. Full details archived at `.planning/milestones/v1.0-ROADMAP.md` and `.planning/milestones/v1.0-REQUIREMENTS.md`; summary in `.planning/MILESTONES.md`.

Next milestone candidates (deferred): hardware tier H1+H2, voice hardening, cross-ranch mesh, attestation year-2, or demo video + submission per PROJECT.md Out of Scope.

---

## Post-v1.0 Phases

### Phase 1: Memory-Powered Agent Mesh

**Goal:** Adopt the Claude Managed Agents **Memory** public beta (shipped 2026-04-23, existing `managed-agents-2026-04-01` header) across the 5-agent mesh so agents learn per-ranch patterns across sessions, with judge-visible Memory receipts on the dashboard — before the 2026-04-26 8pm EST submission. Numbered Phase 1 because post-v1.0 phases are archived under `.planning/milestones/v1.0-phases/`; numbering restarts post-milestone.

**Scope:**

1. **Memory store topology** — one `memstore_ranch_a_shared` read-only domain library + 5 per-agent `read_write` stores, attached via `resources[]` at `client.beta.sessions.create()` in `src/skyherd/agents/managed.py:240`. Workspace-scoped stores enable cross-agent coordination (PredatorPatternLearner writes → FenceLineDispatcher reads on breach).
2. **Memory write hooks in agents** — PredatorPatternLearner writes nightly crossing-pattern summaries; HerdHealthWatcher writes per-cow health baselines; FenceLineDispatcher reads patterns pre-dispatch; CalvingWatch writes labor-signal baselines.
3. **Memory Panel in dashboard** — new `/api/memory/{agent}` endpoint in `src/skyherd/server/app.py` backed by `client.beta.memory_stores.memories.list()` + `memory_versions.list()`; new `MemoryPanel.tsx` in `web/src/components/` with live `memver_…` attestation chain.
4. **Toolset determinism** — `agent_toolset_20260401` selective disable (no `web_search` / `web_fetch`) on CalvingWatch + GrazingOptimizer; preserves `make demo SEED=42 SCENARIO=all` byte-identical.
5. **Runtime guard** — Memory reads/writes stubbed in LocalSessionManager; real `client.beta.memory_stores.*` calls gated on `SKYHERD_AGENTS=managed`.

**Requirements:** (to be derived by `/gsd-plan-phase 1`)

**Depends on:** v1.0 milestone (shipped 2026-04-23) — specifically persistent sessions (one long-lived session per agent, from v1.0 Phase 1) and the `ManagedSessionManager` in `src/skyherd/agents/managed.py`.

**Constraints inherited from v1.0:**
- Determinism gate (`make demo SEED=42 SCENARIO=all`) byte-identical
- Coverage floor ≥ 80%
- MIT-only deps (zero AGPL); `cache_control: ephemeral` on every `messages.create` / `sessions.events.send`
- Zero attribution commits
- Submission hard deadline: 2026-04-26 20:00 EST (target 18:00 EST)

**Plans:** 0 plans (run `/gsd-plan-phase 1`)

Plans:
- [ ] TBD (run /gsd-plan-phase 1 to break down)

**Evidence base:**
- Memory docs: https://platform.claude.com/docs/en/managed-agents/memory
- Release notes (2026-04-23 entry): https://platform.claude.com/docs/en/release-notes/api
- Codebase integration points: `src/skyherd/agents/managed.py:185-404`, `session.py:110-152`, `mesh.py`
- Workspace-scoped memory stores = the cross-agent coordination win (memstore shared by all 5 sessions)
