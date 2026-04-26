# SkyHerd

**The nervous system for working land.**

SkyHerd makes a ranch monitor itself — sensors and drones watch the water tanks, the cattle, and the predators around the clock, and the verified record they produce becomes underwriting data that insurance companies and ag-lenders pay for.

---

## The problem

- A rancher on a 50,000-acre New Mexico spread loses 2+ hours every day just checking water tanks and scanning for sick animals from a truck
- A cow can be dying for 72 hours before a rider happens to see symptoms
- Preventable losses run $40–80 per head per year on seedstock operations; feeder cattle are at ~$375/cwt as of April 2026 feeder futures
- The US beef cow herd is at 27.6 million head — the lowest since 1961 (USDA NASS Jan 2026) — so every head that dies unnecessarily stings more than it did a decade ago

---

## What we built

**5-layer closed loop, 100% simulated, reproducible in a fresh clone**

Sense (LoRaWAN water tanks) → See (trough-camera vision AI) → Respond (autonomous drone flyover) → Intervene (acoustic herd redirect) → Defend (predator deterrence with human-in-loop confirmation). Five named New Mexico pilot ranches on the roadmap: Singleton Ranches, CS Ranch, Bell Ranch, Jicarilla Apache Nation Livestock, and Roam Ranch.

**5 Claude Managed Agents, idle-paused between events**

FenceLineDispatcher, HerdHealthWatcher, PredatorPatternLearner, GrazingOptimizer, CalvingWatch. Each agent runs only while processing an alert. The session-hour meter stops the moment it goes idle. One ranch costs roughly $4/week to monitor — not $4K — because of idle-pause.

**33-file Skills library (CrossBeam pattern)**

Domain knowledge lives in `skills/*.md` — cattle disease signs, predator thermal signatures, NM ecology, drone regulations, acoustic deterrence protocols. Agents load only the skills their current task needs. System prompts stay short; cache hits stay high. This is the same architecture that won $50k at the Opus 4.6 hackathon.

**Ed25519 Merkle attestation chain**

Every sensor reading, agent tool call, and world event is signed and appended to a tamper-evident chain. `skyherd-attest verify` checks it from the command line. Year 2 of the business model is an LRP insurance rider underwritten on water-reliability data from this chain.

---

## The 5 scenarios (63-second hero loop)

| # | Scenario | Cascade |
|---|----------|---------|
| 1 | Coyote at SW fence | FenceLineDispatcher → drone launch → 8–18 kHz deterrent → Wes voice call |
| 2 | Sick cow flagged | HerdHealthWatcher → Doc escalation → vet-intake packet |
| 3 | Water tank pressure drop | LoRaWAN alert → drone flyover → attestation logged |
| 4 | Calving detected | CalvingWatch prelabor behavior → priority rancher page |
| 5 | Storm incoming | GrazingOptimizer herd-move proposal → acoustic nudge |

---

## What is measurable right now

| Item | Result |
|------|--------|
| Tests | 641 passing, 5 skipped |
| Coverage | ≥80% across `src/skyherd` |
| Deterministic replay | `make demo SEED=42 SCENARIO=all` |
| Dashboard | `make dashboard` → http://localhost:8000 |
| Fresh-clone boot | `uv sync && make demo SEED=42 SCENARIO=all` |
| Lint / types | `ruff check` clean, `pyright` clean |

---

## Repo and team

`github.com/george11642/skyherd-engine` — MIT license

```bash
git clone https://github.com/george11642/skyherd-engine && cd skyherd-engine
uv sync && (cd web && pnpm install && pnpm run build)
make demo SEED=42 SCENARIO=all
make dashboard
```

**George Teifel** (UNM, sole entrant, Part 107 licensed drone operator).

Prize targets: top-3 + Best Use of Claude Managed Agents ($5k) + Keep Thinking ($5k) + Most Creative Opus 4.7 Exploration ($5k).
