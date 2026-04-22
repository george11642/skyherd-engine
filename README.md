# SkyHerd Engine

[![CI](https://github.com/george11642/skyherd-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/george11642/skyherd-engine/actions) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**The nervous system for working land.**

SkyHerd makes a ranch monitor itself — sensors and drones watch the water tanks, the cattle, and the predators around the clock, and the verified record they produce becomes underwriting data that insurance companies and ag-lenders pay for.

Hackathon submission — [Built with Opus 4.7: a Claude Code hackathon](https://cerebralvalley.ai/e/built-with-4-7-hackathon), Apr 21–26 2026. All code in this repo is new, written during the hackathon, MIT licensed.

## Quickstart

```bash
git clone https://github.com/george11642/skyherd-engine && cd skyherd-engine
uv sync && (cd web && pnpm install && pnpm run build)
make demo SEED=42 SCENARIO=all    # 5 scenarios, deterministic replay
make dashboard                     # http://localhost:8000
```

## What this is

A simulated ranch that monitors itself. Five Claude Managed Agents watch water tanks, cattle, fences, and weather 24/7. The drone auto-launches on predator or water-failure alerts. A tamper-evident Ed25519 Merkle chain logs every event for insurance-grade attestation.

## Documentation

- [docs/ONE_PAGER.md](docs/ONE_PAGER.md) — start here (2 min read)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — nervous-system pattern, data flow, attestation
- [docs/MANAGED_AGENTS.md](docs/MANAGED_AGENTS.md) — $5k prize essay: 5 agents, idle-pause economics, long-idle waits
- [skills/README.md](skills/README.md) — 33-file domain knowledge inventory (CrossBeam pattern)
- [docs/REPLAY_LOG.md](docs/REPLAY_LOG.md) — deterministic scenario replay log

## Prize targets

- Top-3 main prizes ($50k / $30k / $10k)
- Best Use of Claude Managed Agents ($5k)
- Keep Thinking ($5k)
- Most Creative Opus 4.7 Exploration ($5k)

## Team

George Teifel (UNM, sole registered entrant, [@george11642](https://github.com/george11642)).

## License

MIT. See [LICENSE](./LICENSE).
