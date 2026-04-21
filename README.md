# SkyHerd Engine

> The operating system for remote land assets — a 5-layer nervous system for American ranches.

**Hackathon submission** — [Built with Opus 4.7: a Claude Code hackathon](https://cerebralvalley.ai/e/built-with-4-7-hackathon), Apr 21–26 2026. All code in this repo is new, written during the hackathon, MIT licensed.

## What this is

A simulated ranch that monitors itself. Five Claude Managed Agents watch water tanks, cattle, fences, and weather 24/7. Drone auto-launches on predator or water-failure signals. Tamper-evident attestation log becomes insurance-grade underwriting data.

Built on:
- **Claude Agent SDK + Claude Managed Agents** — long-running, idle-paused monitoring
- **Anthropic Skills** — domain knowledge as first-class artifacts (CrossBeam pattern)
- **Claude Design** (Opus 4.7, launched Apr 17 2026) → Claude Code handoff for UI
- **MCP servers** — drone, sensors, rancher phone as Claude-callable tools

## Philosophy

**Simulation-first hardline.** The MVP is 100% simulated — zero hardware required for submission. Hardware integrates *after* the sim is flawless, one piece at a time. A sim that runs perfectly beats a hardware demo that glitches.

## Quickstart

```bash
# TBD by fresh Claude session — target:
# uv sync
# make sim
```

## Structure

```
src/skyherd/
├── world/       ranch simulation (clock, terrain, cattle)
├── sensors/     LoRaWAN water, trough cam, thermal, fence motion, collar GPS
├── agents/      5 Claude Managed Agents
├── mcp/         MCP servers (drone, sensor, rancher, galileo)
├── drone/       ArduPilot SITL + MAVSDK
├── vision/      MegaDetector + disease classifier heads
└── attest/      Merkle-chained attestation log

skills/          ~25 domain knowledge files (CrossBeam pattern)
tests/           pytest (TDD mandatory)
worlds/          YAML ranch world definitions
docs/            ARCHITECTURE.md + MANAGED_AGENTS.md
```

## The 5 demo scenarios

1. **Coyote at fence** — FenceLineDispatcher → SITL drone → deterrent → Wes voice call
2. **Sick cow flagged** — HerdHealthWatcher → Doc escalation → vet-intake packet
3. **Water tank pressure drop** — LoRaWAN alert → drone flyover → attestation logged
4. **Calving detected** — CalvingWatch labor behavior → priority rancher page
5. **Storm incoming** — Weather-Redirect → GrazingOptimizer herd-move proposal

## Vision

Detailed north-star vision lives in a sibling reference repo: `/home/george/projects/active/drone/VISION.md`. Reference only — not part of this submission.

## License

MIT. See [LICENSE](./LICENSE).

## Team

George Teifel (UNM, sole registered entrant, GitHub [@george11642](https://github.com/george11642)).
