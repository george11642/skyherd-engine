---
name: urgency-tiers
description: Load when any agent must assign an urgency tier to an event before contacting the rancher. Provides the four-tier scale with concrete examples, time-of-day gates, and the logic for upgrading a tier if the rancher doesn't respond.
---

# Urgency Tiers

## When to load

- An event has occurred and the agent needs to decide whether and how urgently to page the rancher.
- Multiple queued events need to be prioritized before delivering a batch summary.
- A previous contact attempt received no response and the agent needs to escalate.

## Summary

Every event in SkyHerd resolves to one of four urgency tiers. Tier assignment is not a formality — it determines whether the rancher gets a text in the morning, a voice call during supper, or a ring at 2am. The most common error is upgrading everything to Tier 3 "to be safe," which trains the rancher to tune Wes out. The second most common error is leaving a Tier 4 event as Tier 2 because it seemed minor. This file gives concrete examples so the classification stays calibrated.

## Key facts

**Tier 1 — Log silently**:
- No rancher notification.
- Rancher sees it on dashboard at next login or in morning summary.
- Examples: minor NDVI decline, single cow absent from one trough visit, LGD detected on patrol, coyote >200m from herd with no approach, drone battery swap completed, standard fence patrol with no anomalies.

**Tier 2 — Text message (SMS)**:
- Non-urgent advisory; rancher acts within 2–8 hours at their discretion.
- Time gate: 0000–0530 texts are held until 0600.
- Examples: water tank at 30% but fill rate adequate, NDVI below rotation threshold, lameness score 2 in one animal, pinkeye early sign in one animal, fence top wire down (no cattle at risk), BCS 4.0 in one cow not near calving, paddock rotation recommendation.
- Format: single text, max 160 chars. Plain language. No alarm words. "Heads up, boss."

**Tier 3 — Voice call (Wes)**:
- Important; rancher should respond within 2–4 hours.
- Time gate: 2100–0530 degrades to text UNLESS it's a calving event, active predator, or dry tank in summer.
- Examples: lameness score 3–4, BRD suspected (fever + lethargy), water tank <20%, confirmed predator within 200m of herd, calving Stage 2 active, BCS <3.5 in animal approaching calving, wolf detected on property, fence cut wire suspected, multiple animals off feed >24 hrs.
- Format: Wes voice call; 20–30 words; per wes-register.md.
- If no answer after 2 rings: leave voicemail; send follow-up text; retry in 20 min.

**Tier 4 — Call now (immediate)**:
- Life or significant property at immediate risk.
- No time gate. Ring until answered.
- If no answer after 3 attempts: secondary contact; then 911 if animal welfare situation is critical (rancher may be incapacitated).
- Examples: coyote or predator inside herd perimeter with young calves, mountain lion kill confirmed on property, water tank dry in July–August heat, calving Stage 2 >90 min with no progress (dystocia), animal recumbent with active predator nearby, cut wire + vehicle tracks (rustling), screwworm larvae confirmed in wound, heat stroke (recumbent animal during peak heat), any LSD or FAD suspect.

**No-answer escalation protocol**:
- Tier 3, no answer after 2 min: leave voicemail; text; try in 20 min; if still no answer, upgrade to Tier 4 attempt.
- Tier 4, no answer after first ring: call again immediately (twice); then secondary contact within 2 min; document attempts in attestation log.

**Time-of-day adjustments**:
- 0000–0530: Tier 3 → hold as text at 0600 (except calving, predator/herd, dry tank in heat).
- 0530–0700: Tier 3 call acceptable; Tier 2 text ok.
- 0700–2100: all tiers as specified.
- 2100–2359: Tier 4 calls; Tier 3 degrades to text unless immediate life risk confirmed.

## Decision rules

```
IF event involves confirmed livestock death or injury in progress:
  → Tier 4 regardless of other factors

IF event involves confirmed foreign animal disease (LSD, screwworm):
  → Tier 4 + mandatory government report; do not hold for time gate

IF event is a sensor anomaly with no confirmed livestock impact:
  → Tier 1 (log); re-evaluate at next data point

IF multiple Tier 2 events accumulate in 2-hour window:
  → Batch into single Tier 2 text; list in order of severity

IF rancher acknowledged a Tier 3 event but it has worsened:
  → Upgrade to Tier 4; notify immediately with "it's gotten worse, boss"

IF it is 0200 and an event is borderline Tier 3 / Tier 4:
  → Apply the "would I be forgiven for waking them?" test:
    → Coyote 500m from herd: hold until 0600
    → Predator inside herd perimeter: call now
```

## Escalation / handoff

- All tier assignments are logged in the attestation chain with the justification for the assigned tier.
- Tier mis-assignments (over or under) noted by rancher feedback should trigger a review of this skill's calibration.

## Sources

- human-in-loop-etiquette.md (cross-reference for channel mechanics).
- wes-register.md (cross-reference for message format per tier).
- R-CALF USA producer survey 2023: alert fatigue findings.
- SkyHerd platform design specification v5.1 (internal).
