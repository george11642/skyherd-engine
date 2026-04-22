---
name: Scenario proposal
about: Propose a 6th (or later) demo scenario for the SkyHerd sim
title: 'scenario: '
labels: scenario, enhancement
assignees: george11642
---

## Scenario name

<!-- Short slug, e.g. `rustling_detection` or `wildfire_thermal`. -->

## One-sentence description

<!-- What happens, which agent responds, what the rancher sees. -->

## Trigger

<!-- What sensor event or scheduled condition fires this scenario? -->

## Agent(s) involved

- [ ] FenceLineDispatcher
- [ ] HerdHealthWatcher
- [ ] PredatorPatternLearner
- [ ] GrazingOptimizer
- [ ] CalvingWatch
- [ ] New agent (describe below)

## New agent description (if applicable)

<!-- Name, trigger, purpose. Must fit the Managed Agents pattern — see docs/MANAGED_AGENTS.md. -->

## Expected event sequence

<!-- Step-by-step: sensor event → agent action → tool call → rancher notification. -->

## Why it matters for working land

<!-- Concrete ranching problem this solves. No campus / consumer framing. -->

## Acceptance criteria

- [ ] Scenario runs cleanly via `make demo SCENARIO=<name>`
- [ ] Deterministic at `SEED=42`
- [ ] All 5 existing scenarios still pass (`make demo SCENARIO=all`)
- [ ] `make ci` green
- [ ] PROGRESS.md Sim Gate still 10/10
- [ ] Skills file(s) added or updated if new domain knowledge required

## Prior art / references

<!-- Ranching literature, USDA data, comparable tools. -->
