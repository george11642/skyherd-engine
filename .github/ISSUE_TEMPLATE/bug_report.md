---
name: Bug report
about: Something broke — sim, agent, hardware, or dashboard
title: 'bug: '
labels: bug
assignees: george11642
---

## What broke

<!-- One sentence: what failed and where. -->

## Steps to reproduce

```bash
# Exact commands
```

## Expected behavior

<!-- What should have happened. -->

## Actual behavior

<!-- What actually happened. Include error output. -->

## Environment

- OS / Python version:
- Branch / SHA:
- `make ci` output: pass / fail
- Relevant `make demo SEED=42 SCENARIO=` output (if sim):

## Which layer

- [ ] World simulator (`src/skyherd/world/`)
- [ ] Sensors / MQTT bus (`src/skyherd/sensors/`)
- [ ] Managed Agents (`src/skyherd/agents/`)
- [ ] MCP servers (`src/skyherd/mcp/`)
- [ ] Vision / disease heads (`src/skyherd/vision/`)
- [ ] Drone backend (`src/skyherd/drone/`)
- [ ] Edge / Pi runtime (`src/skyherd/edge/`)
- [ ] Attestation chain (`src/skyherd/attest/`)
- [ ] Voice / Wes (`src/skyherd/voice/`)
- [ ] Dashboard / server (`src/skyherd/server/`, `web/`)
- [ ] Hardware demo (`src/skyherd/demo/`)
- [ ] Android / iOS companion
- [ ] CI / tooling
