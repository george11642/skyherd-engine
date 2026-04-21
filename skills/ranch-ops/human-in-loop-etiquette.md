---
name: human-in-loop-etiquette
description: Load when deciding how urgently and through what channel to contact the rancher. Covers urgency tiers 1–4, time-of-day awareness, message format, and when the agent acts vs. when it must wait for human approval.
---

# Human-in-the-Loop Etiquette

## When to load

- Any agent is about to contact the rancher and needs to determine the correct channel and urgency.
- An event has occurred and the agent is deciding whether to page, text, log, or wait.
- Multiple events are queued and the agent needs to batch vs. escalate decisions.

## Summary

Ranchers run on ranch time, not tech time. A 3am phone call for a non-emergency burns trust faster than any missed alert. The goal is right information, right channel, right urgency — every time. Over-alerting is as harmful as under-alerting because it trains the rancher to ignore pages. Under-alerting means a dead calf. This skill defines the protocol that keeps SkyHerd's signal-to-noise ratio high enough that the rancher picks up on the first ring.

## Key facts

- **Four urgency tiers**:
  - **Tier 1 — Log silently**: event recorded in dashboard; no notification. Rancher sees it at next login.
  - **Tier 2 — Text (SMS)**: non-urgent advisory; rancher acts at their convenience within 2–8 hrs. Text delivered; no call.
  - **Tier 3 — Call**: important situation requiring same-day response (within 2–4 hrs). Wes voice call to rancher's primary number. If no answer, text fallback.
  - **Tier 4 — Call now**: animal life or property at immediate risk; call immediately regardless of time. Ring until answered; if voicemail, leave urgent message and try secondary contact.
- **Time-of-day gates** (applied before tier assignment):
  - 0000–0530: Only Tier 4 generates a live call. Tiers 1–3 queue until 0600.
  - 0530–0700: Tier 3–4 call; Tier 2 text acceptable.
  - 0700–2100: Normal operating hours; all tiers execute as specified.
  - 2100–2359: Tier 4 calls; Tier 3 degrades to text unless life risk confirmed.
- **Exception to time gate**: calving (Tier 3+), active predator inside herd perimeter (Tier 3+), and dry tank in peak summer heat (Tier 4) always override time gates.
- **Message format for Wes (voice)**:
  - Lead with the problem, not the preamble. "Three cows haven't come to the bunk since yesterday morning, boss."
  - State GPS or paddock name. "They're in the south pasture, near the windmill."
  - State what the system recommends (never commands). "Might be worth a drive by when you get a chance."
  - Tier 4 format: "We've got a problem that needs you now. [problem]. [location]. [what you need]."
- **Batching**: minor Tier 1 events accumulate in a daily summary delivered at 0700. No more than 3 separate texts in a 2-hour window for non-escalating events. Batch them.
- **Autonomous action boundary**: agents act autonomously on drone deployment, acoustic deterrents, logging, and camera repositioning. Agents do NOT act autonomously on: administering medication, physically moving cattle, making vet appointments, contacting authorities. Those require rancher confirmation.
- **Decision hand-off**: once the rancher acknowledges a Tier 3–4 event, agents shift to support mode — answering questions, providing GPS, pulling camera feeds — not generating new recommendations until rancher resolves the event.

## Decision rules

```
IF event has no livestock health, safety, or immediate financial consequence:
  → Tier 1; log only; next daily summary

IF event is a management advisory (rotation due, tank at 30%, fence wire loose):
  → Tier 2 text; queue during 0000–0530; send at 0600

IF event involves confirmed animal health issue (lameness ≥3, BRD suspected, off-feed 24 hrs):
  → Tier 3 call; respect time gate unless calving or summer tank failure

IF event involves immediate life risk (animal recumbent, confirmed predator inside herd, dry tank in 95°F heat):
  → Tier 4 call now; no time gate; ring until answered

IF rancher has not responded to Tier 3 after 20 min:
  → Upgrade to Tier 4; try secondary contact number

IF 3+ Tier 2 texts are queued within 2 hrs with no escalation:
  → Batch into a single Tier 2 text with summary

IF rancher is in acknowledged-active-event mode:
  → Hold all new Tier 2 notifications; only escalate if new Tier 4 event occurs
  → Summarize held events when rancher marks event resolved

IF agent is uncertain about urgency tier:
  → Default to the higher tier; over-notification is recoverable; missed emergency is not
  → Exception: 0000–0530 when a wrong Tier 4 wakes rancher needlessly; default to log and re-evaluate at 0600
```

## Escalation / handoff

- Wes persona delivers all voice messages per wes-register.md and never-panic.md.
- Agent records all contacts with timestamp, tier, acknowledgment status, and outcome in the attestation log.

## Sources

- Grandin T. (2014). *Livestock Handling and Transport*, 4th ed. CABI — on human-animal-technology interface principles.
- R-CALF USA producer survey data on technology adoption (2023): alert fatigue cited as #1 barrier.
- SkyHerd platform design specification v5.1 (internal).
- Twilio SMS/Voice API best practices: message format and delivery timing.
