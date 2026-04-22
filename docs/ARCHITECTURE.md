# SkyHerd Architecture

**Related docs**: [skills/README.md](../skills/README.md) · [docs/MANAGED_AGENTS.md](MANAGED_AGENTS.md) · [docs/REPLAY_LOG.md](REPLAY_LOG.md) · [docs/ONE_PAGER.md](ONE_PAGER.md) · [worlds/ranch_a.yaml](../worlds/ranch_a.yaml)

---

## The nervous-system pattern

SkyHerd maps a ranch's five alert categories to five software layers. Each layer has a dedicated Claude Managed Agent. Nothing is bolted onto a single giant model call.

| Layer | Name | Function |
|-------|------|----------|
| L1 | Sense | LoRaWAN water-tank sensors on 15-minute intervals report tank level, flow, and temperature before the rancher's truck rolls. |
| L2 | See | YOLOv12-Pose trough cameras run on-device (Jetson Orin NX) to count entries, flag gait drift, and surface 48-hour behavioral anomalies at each trough. |
| L3 | Respond | DJI Dock 3 auto-launches on any L1 or L2 alert, placing 4K+thermal over the flagged location in under 90 seconds without a human pilot. |
| L4 | Intervene | Conditioned ultrasonic emitters redirect cattle without cortisol elevation, replacing the helicopter call for routine herd movement. |
| L5 | Defend | Thermal-confirmed predator signatures trigger a graduated acoustic deterrence sequence; every Defend action requires rancher confirmation before executing. |

---

## Data flow: sensor to rancher

```
MQTT BUS  (topic: skyherd/ranch_a/#)
    │
    ├── water/tank_+    ← LoRaWAN ChirpStack → Mosquitto
    ├── camera/trough_+ ← Jetson edge inference → MJPEG frame events
    ├── fence/breach_+  ← LoRaWAN motion sensor → Mosquitto
    ├── drone/telemetry ← ArduPilot SITL (or real Dock 3)
    ├── collar/+        ← Simulated GPS+IMU collars (500 head)
    ├── weather/current ← NWS API poller
    └── cost/ticker     ← CostTicker.emit_tick() → SSE to dashboard

Webhook wake (HTTPS POST from MQTT bridge)
    │
    └── AgentMesh.on_webhook(event)
            │
            ├── topic matches FenceLineDispatcher.wake_topics?  → wake session
            ├── topic matches HerdHealthWatcher.wake_topics?    → wake session
            ├── topic matches PredatorPatternLearner.wake_topics? → wake session
            ├── topic matches GrazingOptimizer.wake_topics?     → wake session
            └── topic matches CalvingWatch.wake_topics?         → wake session

Agent wake cycle
    │
    ├── SessionManager.wake(session_id, event)
    │       └── CostTicker.set_state("active")  ← meter starts
    │
    ├── build_cached_messages(system_prompt, skills, event_payload)
    │       └── cache_control: ephemeral on prompt + each skill block
    │
    ├── Claude Opus 4.7 API call
    │       └── tool calls → MCP servers (drone_mcp / sensor_mcp / rancher_mcp)
    │
    ├── SessionManager.sleep(session_id)
    │       └── CostTicker.set_state("idle")   ← meter stops, $0/s
    │
    └── Ledger.append(source, kind, payload)   ← Ed25519 Merkle chain

Rancher surface
    └── page_rancher(urgency="call") → Twilio → ElevenLabs → "Wes" voice call
```

The cost ticker publishes to `skyherd/ranch_a/cost/ticker` once per second. The dashboard subscribes via SSE and shows a live dollar counter that visibly freezes between events — that freeze is the idle-pause.

---

## Why Skills, not one giant prompt

The first-place winner of the Built with Opus 4.6 hackathon was CrossBeam by Mike Brown. His ADU permit assistant won $50k by splitting domain knowledge across 28+ reference files loaded per task instead of cramming everything into one system prompt. SkyHerd uses the same pattern.

There are 33 skill files in `skills/` totaling roughly 3,000 lines of New Mexico ranch domain knowledge. They cover cattle behavior, disease signs, predator identification, drone regulations, acoustic deterrence protocols, and the laconic voice register of the "Wes" rancher interface. Each agent loads only the skills its current wake event needs.

```
# Example: FenceLineDispatcher wakes on fence.breach (coyote signal)
# Loads at wake time:
skills = [
    "skills/predator-ids/coyote.md",
    "skills/predator-ids/thermal-signatures.md",
    "skills/drone-ops/deterrent-protocols.md",
    "skills/ranch-ops/fence-line-protocols.md",
    "skills/voice-persona/urgency-tiers.md",
]
# Does NOT load: calving-signs.md, paddock-rotation.md, brd.md, etc.
```

Every skill file lands in a `cache_control: {"type": "ephemeral"}` block. After the first wake, subsequent wakes on the same session hit the cache. This drops per-wake cost by roughly 90% on the stable skill content, billing only the volatile event payload at full rate.

The per-agent skill mappings are in `src/skyherd/agents/*.py`. The full inventory is in `skills/README.md`.

---

## Determinism and attestation

Every scenario run uses `World(seed=42)` — the random number generator is seeded before any entity spawns, any sensor fires, or any predator moves. The same seed produces byte-identical event streams on any machine.

Every agent tool call and every world event writes to an Ed25519-signed Merkle chain backed by SQLite (`src/skyherd/attest/`). Each entry carries:
- SHA-256 hash of the previous entry
- Ed25519 signature over the concatenated payload + prev_hash
- Source, kind, timestamp, and JSON payload

The chain is verifiable with `skyherd-attest verify`. A tampered entry breaks the Merkle proof at that position. The dashboard attestation panel shows live chain growth during a demo run.

This matters past the hackathon. Year 2 of the SkyHerd business model is an LRP (Livestock Risk Protection) insurance rider underwritten on water-reliability data. The rider needs an auditable record. The Merkle chain is that record — built into the runtime, not bolted on later.

---

## Sim-first discipline

The entire submission is 100% simulated. No hardware is required to reproduce any result in this repo.

The `World` class in `src/skyherd/world/world.py` models terrain, 50–500 cattle with position and health scores, coyote/mountain-lion predators with pathfinding, LoRaWAN water-tank sensors, trough cameras with synthetic disease-detection frames, GPS+IMU cattle collars, and a weather ceiling model (27 kt sustained wind grounds the drone 15–20% of NM spring days — that number is in the sim too).

The Sim Completeness Gate required all five demo scenarios to run back-to-back without intervention, all five agents to cross-talk via MQTT, deterministic replay under a fixed seed, and a clean fresh-clone boot. Hardware tiers are sequentially gated behind the Gate, not wired in parallel.

```bash
make demo SEED=42 SCENARIO=all   # 5 scenarios, identical on every machine
make demo SEED=42 SCENARIO=coyote  # single scenario
```

The 63-second hero loop in the demo video is a single `make demo SEED=42 SCENARIO=all` run, no edits, no cuts.
