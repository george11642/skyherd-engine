# Best Use of Claude Managed Agents — SkyHerd

*This document is the $5k prize essay for the "Best Use of Claude Managed Agents" special award.*

---

Most demos that use Claude Managed Agents run a single agent for a few minutes. SkyHerd runs five agents across timescales ranging from 30 seconds to 30 days, billing nearly nothing between events, and producing a signed audit log that a livestock insurer can actually read. Here is how that works.

---

## Truth 1: Five agents, not one

A ranch does not have one kind of alert. Water tanks fail on random afternoons. Predators hunt at night. Calving season runs six weeks in spring and then goes quiet until next year. Grazing rotations take days to approve. A single long-running agent that watches all of this would be awake — and billing — constantly.

SkyHerd assigns each monitoring domain to its own Managed Agent session with its own wake pattern and its own skill set.

| Agent | Wake topics | Skills loaded at wake | Target wake latency | Runtime pattern |
|-------|-------------|----------------------|---------------------|-----------------|
| **FenceLineDispatcher** | `skyherd/+/fence/breach`, `skyherd/+/fence/motion` | coyote.md, thermal-signatures.md, deterrent-protocols.md, fence-line-protocols.md, urgency-tiers.md | &lt;30 s | Always-listening; wakes on MQTT webhook, decides, sleeps |
| **HerdHealthWatcher** | `skyherd/+/camera/motion`, daily schedule | lameness-indicators.md, all 7 disease skill files, herd-structure.md, feeding-patterns.md | &lt;2 min | Weekly session; mostly idle between camera events |
| **PredatorPatternLearner** | `skyherd/+/drone/thermal_clip`, nightly schedule | coyote.md, mountain-lion.md, wolf.md, thermal-signatures.md, nm-predator-ranges.md | &lt;5 min | 30-day session; wakes nightly on thermal clips, sleeps between |
| **GrazingOptimizer** | `skyherd/+/weather/alert`, weekly schedule | paddock-rotation.md, nm-forage.md, water-tank-sops.md, weather-patterns.md, seasonal-calendar.md | &lt;10 min | Weekly session; idles for days waiting on rancher approval |
| **CalvingWatch** | `skyherd/+/collar/activity_spike`, `skyherd/+/calving/prelabor` | calving-signs.md, lameness-indicators.md, urgency-tiers.md, human-in-loop-etiquette.md | &lt;1 min | Seasonal (Mar–Apr); 6-week session, nightly checkpoints |

The spec for each agent lives in `src/skyherd/agents/spec.py` as an `AgentSpec` dataclass. The `wake_topics` list is matched against incoming MQTT events by `SessionManager.on_webhook()`. When a topic matches, the session transitions from `idle` to `active` — the cost meter starts. When the agent finishes its tool-call sequence and calls `sleep()`, the meter stops.

---

## Truth 2: Idle-pause is the economics

Ranches are quiet 95% of the time. A water tank on a 50,000-acre New Mexico ranch might trigger a real alert twice a month. A predator breach event might happen once a week. Between events, these agents sit in `idle` state and cost nothing.

The Managed Agents platform charges `$0.08/session-hour` for active session time. Idle sessions are paused — the meter stops. Token costs are billed separately on each wake-cycle API call, but those are small compared to the session-hour rate at Opus 4.7 token prices.

The math for one ranch, one week:

```
FenceLineDispatcher:
  2 real alerts × 3 min active each = 6 min/week active
  Cost: 0.1 hr × $0.08 = $0.008/week

HerdHealthWatcher:
  7 daily checks × 5 min each = 35 min/week active
  Cost: 0.58 hr × $0.08 = $0.047/week

PredatorPatternLearner:
  7 nightly thermal-clip reviews × 8 min each = 56 min/week active
  Cost: 0.93 hr × $0.08 = $0.074/week

GrazingOptimizer:
  1 weekly rotation run × 15 min active = 15 min/week active
  Idle for 5 days waiting on rancher approval — $0 during the wait
  Cost: 0.25 hr × $0.08 = $0.020/week

CalvingWatch (in season):
  2 alerts × 4 min each = 8 min/week active
  Cost: 0.13 hr × $0.08 = $0.010/week

Total session-hour cost per ranch per week: ~$0.16
Add token costs for wake cycles: ~$3.50–$4.00
Total: ~$4/week to monitor a working ranch
```

That number holds because idle sessions contribute $0. If the platform billed a flat session-hour rate without idle-pause — the way most serverless compute works — the same five agents running "24/7" would cost roughly $67/week in session-hours alone. The idle-pause isn't a nice-to-have. It's what makes the unit economics work.

The `CostTicker` class in `src/skyherd/agents/cost.py` tracks this in real time. The pricing constants are in that file:

```python
_SESSION_HOUR_RATE_USD: float = 0.08   # per active session-hour only
_INPUT_TOKENS_PER_M_USD: float = 15.00
_OUTPUT_TOKENS_PER_M_USD: float = 75.00
_CACHE_HIT_PER_M_USD: float = 1.50
_CACHE_WRITE_PER_M_USD: float = 18.75
```

The ticker calls `emit_tick()` once per second. While `state == "active"`, the tick accumulates `$0.08 / 3600` per second. While `state == "idle"`, `delta = 0.0`. The dashboard subscribes to the `skyherd/ranch_a/cost/ticker` MQTT topic via SSE and shows the live dollar counter — which visibly freezes between events.

---

## Truth 3: Long-idle waits are real

Most Managed Agents demos show an agent that wakes, runs for two minutes, and exits. The waiting behavior — sessions that pause for hours or days — is what this platform is actually built for. SkyHerd has three agents where the wait is the point.

**GrazingOptimizer** runs a paddock rotation analysis once a week. The analysis takes 10–15 minutes of active Claude time and produces a rotation proposal. Then it sleeps and waits — sometimes for two to three days — for the rancher to approve the rotation via the phone PWA. When the rancher taps "Approve," the webhook fires, the session wakes, and the optimizer issues the acoustic nudge to move the herd. The session holds state across the entire wait. There is no polling, no re-prompting from scratch, no re-loading context. The agent remembers what it proposed.

**PredatorPatternLearner** runs a 30-day session. Every night, a new thermal clip arrives from the drone patrol. The agent wakes, processes the clip (new crossing points, species confirmation, time-of-night pattern), updates its internal crossing-pattern map, and checkpoints. Then it sleeps until the next night's clip. After 30 days it produces a crossing-density heatmap and a recommended patrol schedule. No other submission will demo a stateful session that accumulates evidence across 30 nightly wake events.

**CalvingWatch** runs a 6-week seasonal session from late February through mid-April — NM spring calving. It sits idle between events. When a collar reports an activity spike that matches pre-labor patterns from `skills/cattle-behavior/calving-signs.md`, it wakes, evaluates the cow, and either logs quietly or pages the rancher with urgency `"call"` if dystocia indicators are present. The session carries the week-over-week history of which cows are near term, which have already calved, and which are showing delayed-labor patterns. That history is not reconstructed from scratch on each wake. It is in the checkpoint.

All three sessions use `SessionManager.checkpoint()` to serialize state to `runtime/sessions/{session_id}.json` at nightly intervals (or sooner on explicit events). `restore_from_checkpoint()` rehydrates them after any outage.

```python
# From src/skyherd/agents/session.py
def sleep(self, session_id: str) -> Session:
    """Transition session to idle; halts token/cost meter."""
    session.state = "idle"
    session._ticker.set_state("idle")   # $0/s from this point

def wake(self, session_id: str, wake_event: dict) -> Session:
    """Transition session to active; resume cost meter."""
    session.state = "active"
    session._ticker.set_state("active") # $0.08/hr from this point
```

The `run_tick_loop()` async function logs `"cost ticker paused — all sessions idle, $0/s"` whenever every session is in idle state. In a working demo, that log line appears between every event. In a real ranch deployment, it appears most of the day.

---

## One ledger

Every session wake, every tool call, every world event writes to the same Ed25519-signed Merkle chain. The full audit trail for a 30-day deployment — which agent woke, when, on what event, which tools it called, what parameters it passed, what the sensor reading was — is in a single SQLite file with a verifiable hash chain.

That chain is not an artifact of the demo. It is the product. Year 2 of the SkyHerd business model is an LRP (Livestock Risk Protection) insurance rider underwritten on water-reliability attestation. The rider needs an auditable record of sensor readings over time. The Merkle chain is that record, produced automatically by the Managed Agent mesh as a side effect of normal operation.

The attestation panel in the dashboard shows the live chain during a demo run. `skyherd-attest verify` checks the chain integrity from the command line.

---

Cost-ticker is live in the dashboard at `/`. The attestation panel shows the live chain. `make mesh-smoke` replays five wake events end-to-end.

---

## Opus 4.7 outside the mesh — caption editorial

The 5-agent mesh above uses the Managed Agents API (`client.beta.sessions.*`,
beta header `managed-agents-2026-04-01`). Phase G adds a separate, one-shot
use of Opus 4.7 outside the mesh: the demo video's caption styling.

`scripts/generate_kinetic_captions.py style` calls
`client.messages.create(model="claude-opus-4-7", ...)` with a cached system
prompt and skills prefix, asking Opus to emit per-word visual styling
(color / weight / animation / emphasis level) for the transcribed voice-over.
Output lives at `remotion-video/public/captions/styled-captions-{A,B,C}.json`
and is rendered by `KineticCaptions.tsx`.

This is not a session and does not run inside the mesh — it's a single
batched generation, deliberately cached so re-runs across the three video
variants share a ~6.7K-token prefix. We mention it here so judges see that
Opus 4.7 makes editorial decisions across the full submission surface, not
only inside the agent loop.
