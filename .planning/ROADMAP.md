# Roadmap: SkyHerd Engine

**Current milestone:** none (v1.0 shipped 2026-04-23). Standalone post-v1.0 phases run without a formal milestone until `/gsd-new-milestone` is invoked.

v1.0 MVP Completion milestone is complete — 32/32 requirements satisfied, 10/10 Sim Completeness Gate GREEN. Full details archived at `.planning/milestones/v1.0-ROADMAP.md` and `.planning/milestones/v1.0-REQUIREMENTS.md`; summary in `.planning/MILESTONES.md`.

Post-v1.0 autonomous track targeting the 2026-04-26 20:00 EST submission — Memory adoption, software-only hardware prep (H1–H4), cross-ranch promotion, voice hardening, attestation year-2, and demo-video scaffolding. Physical hardware assembly + field shoot + video edit remain manual.

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

**Requirements:** MEM-01, MEM-02, MEM-03, MEM-04, MEM-05, MEM-06, MEM-07, MEM-08, MEM-09, MEM-10, MEM-11, MEM-12 (defined in .planning/phases/01-memory-powered-agent-mesh/01-RESEARCH.md §Phase Requirements)

**Depends on:** v1.0 milestone (shipped 2026-04-23).

**Plans:** 7 plans

Plans:
- [ ] 01-01-PLAN.md — Wave 0 foundation: A1 live probe, HashChip extraction, memory_paths pure module, determinism sanitizer extension, Wave 0 test stubs
- [ ] 01-02-PLAN.md — MemoryStoreBase / MemoryStoreManager (REST wrapper) / LocalMemoryStore (deterministic JSONL shim) / factory + ≥90% coverage
- [ ] 01-03-PLAN.md — ManagedSessionManager wiring: memory_store_ids plumbing + extra_body resources attach + selective toolset disable for deterministic agents
- [ ] 01-04-PLAN.md — Post-cycle memory_hook + _handler_base integration + AgentMesh startup store creation + ledger + SSE pairing
- [ ] 01-05-PLAN.md — /api/memory/{agent} endpoints + events.py SSE event registration + app factory wiring
- [ ] 01-06-PLAN.md — MemoryPanel.tsx (5-agent tabs + HashChip rows + flash animation) + sse.ts eventTypes + App.tsx mount + human-verify checkpoint
- [ ] 01-07-PLAN.md — Determinism regression + end-to-end scenario + coverage + mesh-smoke + v1.0 scenario non-regression audit

**Evidence base:**
- Memory docs: https://platform.claude.com/docs/en/managed-agents/memory
- REST spike confirmed 2026-04-23 20:10 UTC (see `.planning/phases/01-memory-powered-agent-mesh/01-CONTEXT.md` `<spike_findings>` section)

---

### Phase 2: Cross-Ranch Mesh Promotion

**Goal:** Promote the existing cross-ranch coyote bonus scenario to a first-class feature — dedicated CrossRanchCoordinator agent, dashboard panel showing neighbor-mesh handoffs, and silent drone pre-positioning. Strengthens the "first predator nervous system" narrative.

**Scope:**

1. **CrossRanchCoordinator agent** — new 6th agent (parallel to 5 existing) that subscribes to `skyherd/neighbor/+/+/predator_confirmed`, correlates neighbor alerts with local thermal patterns, pre-positions drones silently (no rancher page unless threat cascades).
2. **Neighbor mesh API** — `/api/neighbors` endpoint returning connected-ranch handoff log (`mesh_neighbor.py` has the seed).
3. **Dashboard panel** — `CrossRanchPanel.tsx` showing inbound/outbound neighbor alerts with ranch names + timestamps; mount on main dashboard.
4. **Memory integration** — writes to `memstore_ranch_a_shared` under `/neighbors/{ranch_id}/` so Phase 1's shared-store topology extends naturally.
5. **Scenario upgrade** — the existing `cross_ranch_coyote` bonus scenario becomes a flagship showcase scenario with full agent dispatch (not just event-presence).

**Depends on:** Phase 1 (uses the memstore_ranch_a_shared topology).

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 2 to break down)

---

### Phase 3: Voice Hardening (Wes live Twilio + ElevenLabs)

**Goal:** Harden the Wes cowboy-persona voice chain so the live-call path is demo-ready — real Twilio number provisioning, ElevenLabs voice-clone QA tests, and failover coverage. Use Chrome MCP for account signups + number purchase if no credentials present.

**Scope:**

1. **Twilio signup + number provision** — via `mcp__claude-in-chrome__*` on console.twilio.com: sign in (or sign up if no account), buy a local US number, capture account SID + auth token + number into `.env.local` (redacted in commits). Requires user approval for the paid number purchase (~$1.15/mo); if user absent, skip purchase and leave credential stubs + manual-step TODO.
2. **ElevenLabs voice-clone QA** — automated test that compares generated Wes audio waveforms against a reference clip (MSE threshold), ensuring voice clone doesn't regress on model updates.
3. **Live-call path coverage** — add integration test that exercises Twilio voice call via REST mock; cover `urgency=emergency` escalation chain.
4. **Fallback chain hardening** — test the ElevenLabs → piper → espeak → silent cascade exhaustively.
5. **Demo-mode toggle** — `SKYHERD_VOICE=live|mock|silent` env flag so the demo can mute voice for video B-roll vs go live on the hero shot.

**Depends on:** Phase 1 (Memory for voice-clone QA baseline storage).

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 3 to break down)

---

### Phase 4: Attestation Year-2 (public viewer + rotation)

**Goal:** Harden the Ed25519 + Merkle attestation ledger for year-2: public verification viewer page, signature rotation protocol, and a `verify-chain` CLI with polished output. Answers "can a judge audit what the AI did?" on camera.

**Scope:**

1. **Public attestation viewer** — new `/attest/{hash}` page in the SPA showing the full chain back to genesis with sig verification status.
2. **Signature rotation** — documented protocol + code path for rotating the signing key; old signatures remain verifiable; new root published to the Merkle forest.
3. **`skyherd-verify` CLI** — standalone click command that ingests an event JSON + sig and reports PASS/FAIL with human-readable trace. Target <200ms.
4. **Memory version pairing** — every ledger entry includes the paired `memver_…` ID (from Phase 1) so "two independent receipts agree" is verifiable on-chain.
5. **Docs** — `docs/ATTESTATION.md` end-to-end walkthrough, copy-pasteable verification commands.

**Depends on:** Phase 1 (memver pairing).

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 4 to break down)

---

### Phase 5: Hardware H1 Software Prep (Pi 4 + PiCamera + coyote harness)

**Goal:** Ship all Pi 4 + PiCamera *software* — boot script, sensor emulator, cardboard-coyote thermal-clip generator, MQTT bridge — so that when the physical Pi arrives the path to "sensor live on dashboard" is: flash SD card → plug power → work. Actual Pi flashing + field placement remains manual.

**Scope:**

1. **Pi boot image script** — `hardware/pi/bootstrap.sh` that takes a blank Raspberry Pi OS Lite and installs deps (Python 3.11, mosquitto-client, picamera2, our skyherd-edge package), configures systemd services, sets wifi from a provided `credentials.json`.
2. **PiCamera sensor emulator** — `src/skyherd/edge/picam_sensor.py` — captures frame, runs on-device classifier (MobileNetV3-Small from v1.0 pinkeye head), emits `skyherd/{ranch}/trough_cam/{cam_id}` MQTT events. Runs headless.
3. **Cardboard-coyote thermal-clip generator** — pre-recorded thermal MP4 playback that the dashboard consumes as if from a real FLIR; used to validate the full chain without needing nocturnal wildlife.
4. **MQTT bridge doc** — `docs/HARDWARE_H1_RUNBOOK.md` exact command sequence, expected SSE events, troubleshooting.
5. **Mock fabric** — a `pytest` fixture that stands up a local mosquitto broker, injects canned sensor events, asserts dashboard receives them.

**Depends on:** Phase 1.

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 5 to break down)

---

### Phase 6: Hardware H2 Software Prep (Pi → SITL drone integration)

**Goal:** Wire the Phase 5 Pi sensor events through to an ArduPilot SITL drone takeoff command so the "coyote detected → drone launches → deterrent plays" chain runs end-to-end against SITL. When physical hardware arrives, the same chain runs against a real Mavic.

**Scope:**

1. **Event → mission** — `src/skyherd/edge/pi_to_mission.py` — listens on the `fence.breach` MQTT topic, calls FenceLineDispatcher, which calls drone_mcp.launch_drone with a real mission upload to SITL.
2. **SITL fixture** — docker-compose target `hardware-demo` that boots ardupilot SITL + mosquitto + our live server + an edge Pi emulator, so the full chain runs on one laptop.
3. **Deterrent playback** — `hardware/speaker_bridge.py` — emits acoustic-deterrent MP3 to the OS audio device when SITL drone reaches overwatch waypoint.
4. **Failover** — if SITL connection drops mid-mission, drone returns-to-launch; tested with a chaos-monkey fixture.
5. **E2E test** — `tests/hardware/test_h2_e2e.py` — simulates cardboard-coyote → thermal-clip → fence breach → drone mission → RTL. Asserts attestation entries on every step.

**Depends on:** Phase 5.

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 6 to break down)

---

### Phase 7: Hardware H3 Software Prep (Mavic DJI SDK + MAVSDK failover)

**Goal:** Harden the iOS + Android companion app DJI SDK V5 wire-up and add an MAVSDK failover path so the Mavic Air 2 can run agent-commanded missions. Physical flight testing remains manual.

**Scope:**

1. **DJI SDK V5 integration review** — `ios/SkyHerdCompanion/` and `android/SkyHerdCompanion/` — audit the DJI mission upload path, ensure it handles GPS-denied, low-battery, and lost-signal gracefully.
2. **MAVSDK failover path** — if DJI SDK connection fails, fall back to MAVSDK via USB-C OTG; keep mission parity.
3. **Mission schema** — `docs/MAVIC_MISSION_SCHEMA.md` — exact JSON the agent produces, what the app consumes. Version it.
4. **Simulated mission E2E** — a test harness that replays a recorded DJI packet stream through the app to confirm the UI and mission logic work without a real drone.
5. **Companion app build** — Android APK build via CI, iOS build via Fastlane in CI (unsigned — real signing still needs Apple cert). Artifacts published to GitHub Releases.

**Depends on:** Phase 6.

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 7 to break down)

---

### Phase 8: Hardware H4 Software Prep (LoRa collar + ChirpStack bridge)

**Goal:** Finish the DIY LoRa GPS collar firmware and ChirpStack bridge so flashing the RAK3172 is one command and the dashboard sees collar GPS + IMU immediately. Soldering + burn-in remain manual.

**Scope:**

1. **Firmware polish** — `hardware/collar/src/main.cpp` — code review the existing 312 lines, add battery-save modes, tune GPS duty cycle, add OTA update placeholder.
2. **ChirpStack bridge** — `src/skyherd/edge/chirpstack_bridge.py` — ingests uplink frames from ChirpStack v4 REST API, republishes to `skyherd/{ranch}/collar/{id}/{topic}` MQTT. JSON codec for collar payload.
3. **Build + flash scripts** — `hardware/collar/flash.sh` that wraps PlatformIO upload with proper fuse settings. `hardware/collar/BOM.md` finalized.
4. **Collar simulator** — `src/skyherd/sensors/collar_sim.py` that emits fake collar events per cow entity; already partial, complete it.
5. **End-to-end docs** — `docs/HARDWARE_H4_RUNBOOK.md`: from a blank RAK3172 and new ChirpStack install to live collar events on dashboard.

**Depends on:** Phase 7.

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 8 to break down)

### Phase 10: Dashboard Polish 10/10 (livestock viz, layout fixes, ease-of-use, stitch-grade UI)

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 9
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 10 to break down)

---

### Phase 9: Demo Video Scaffolding + Submission

**Goal:** Everything upstream of the camera button: 3-min script timestamped to the sim, shot list, B-roll prompts, submission form draft, LinkedIn launch post, YouTube metadata. User still records + edits.

**Scope:**

1. **3-min script** — `docs/DEMO_VIDEO_SCRIPT.md` — shot-by-shot with timecodes, voiceover lines, scene descriptions. Aligned to `make demo SEED=42 SCENARIO=all` so the sim can be paused/scrubbed to match.
2. **Shot list + B-roll** — `docs/SHOT_LIST.md` — every screen capture, every physical shot (if hardware available), every product B-roll. Include image-gen prompts for any stylized overlays.
3. **Submission form draft** — `docs/SUBMISSION.md` — the 100–200 word summary, repo URL, YouTube URL placeholder, category selections for Managed Agents $5k + Keep Thinking $5k + Most Creative $5k.
4. **LinkedIn launch post** — `docs/LINKEDIN_LAUNCH.md` — draft post with hook, body, CTA; screenshot/thumbnail callouts.
5. **YouTube metadata** — `docs/YOUTUBE.md` — title, description with timestamps + links, tags, thumbnail brief.
6. **Dry-run rehearsal** — a `make rehearsal` target that plays the sim on loop so the user can practice voiceover before recording.

**Depends on:** Phases 1–8 (everything the video showcases).

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 9 to break down)
