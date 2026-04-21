---
name: livestock-guardian-dogs
description: Load to prevent false-positive predator alerts on Livestock Guardian Dogs (LGDs). Covers thermal and behavioral signatures of Great Pyrenees, Anatolian Shepherd, and Maremma breeds working with cattle and sheep.
---

# Livestock Guardian Dogs (LGDs)

## When to load

- PredatorPatternLearner or FenceLineDispatcher detected a canid-sized thermal signature near the herd.
- A drone patrol identifies a large white or cream-colored dog lying near or among livestock.
- Any canid ID needs to be disambiguated before an alert is escalated or a deterrent activated.

## Summary

Livestock Guardian Dogs are working ranch dogs that live with and protect the herd 24/7. On NM ranches using LGDs, they are present at all hours, often within 10–50m of the herd, sometimes lying still for extended periods. Misidentifying an LGD as a coyote and activating an acoustic deterrent can distress the dog, disrupt herd bonding, and erode the rancher's trust in the system. A correct LGD non-flag is as important as a correct coyote flag. Key differentiators: size, behavior, thermal signature, and movement relative to herd.

## Key facts

- **Common breeds on NM ranches**:
  - Great Pyrenees: 85–120 lb; white/cream; heavy coat; thick thermal insulation.
  - Anatolian Shepherd: 80–150 lb; fawn/cream with black mask; shorter coat.
  - Maremma Sheepdog: 65–100 lb; white; dense double coat; less common in NM than Pyrenees.
- **Thermal signature**: dense double coat on Pyrenees and Maremma creates very low thermal emission compared to coyote. On a cold night, an LGD in thick coat appears nearly the same temperature as ambient ground — much cooler than a coyote of similar size. Anatolian with shorter coat shows warmer signature.
- **Behavior near herd**: LGDs move slowly among the herd, occasionally lie down within the group, or patrol the herd perimeter at a walk. They do NOT stalk, rush, or exhibit freeze-stalk-rush sequences typical of predatory species.
- **Response to drone**: habituated LGDs generally ignore drones overhead; may bark initially, then return to patrol. Coyotes typically flee from a drone at 60m AGL. A canid that holds position near the herd when a drone approaches is almost certainly an LGD.
- **Night pattern**: LGDs are most active at night — their alert and patrol frequency peaks 2100–0500. This overlaps with predator-detection windows. An active patrolling dog at night near the herd is expected and normal.
- **Barking**: LGDs bark extensively at perceived threats (coyotes, people, vehicles). Sustained barking + herd movement may indicate an LGD detecting a predator. This is a signal to increase monitoring, not to flag the LGD.
- **Size discrimination**: LGDs are consistently larger than coyotes (60 lb minimum vs. coyote max 50 lb). On thermal, head-to-body ratio for Pyrenees is blockier and more rounded than coyote's narrow tapered skull.
- **GPS collar**: many NM ranchers fit LGDs with GPS collars. If available, cross-reference LGD collar GPS with thermal detection coordinates before any predator escalation.
- **Multiple dogs**: ranches may run 1–4 LGDs per herd. Multiple large canids moving together near the herd are far more likely to be the LGD pack than a wolf pack.

## Decision rules

```
IF large white/cream-colored canid detected lying or walking slowly within herd:
  → LGD; DO NOT flag; log as expected patrol event; no alert

IF large canid at herd perimeter, slow walking, no stalk behavior, drone approach yields barking but not flight:
  → LGD behavioral signature; log; no alert

IF canid-sized thermal detected at night moving AWAY from herd at trot:
  → May be LGD patrolling or a coyote; check size (>60 lb = likely LGD)
  → If GPS collar data available, compare immediately

IF LGD barking sustained (>5 min) in direction away from herd:
  → LGD has detected external threat; increase drone sweep in that direction
  → Do NOT suppress bark; LGD is your first sensor

IF thermal signature is large canid APPROACHING herd from outside at stalk-freeze-rush pattern:
  → NOT LGD behavior; escalate as predator; cross-reference coyote.md or wolf.md

IF GPS shows 2 large canids at exact herd GPS centroid overnight:
  → LGDs present; downgrade all concurrent thermal canid detections to low-priority unless >3 additional signatures
```

## Escalation / handoff

- LGD detections: always **Tier 1 log only**. Never activate deterrents toward an LGD.
- If LGD appears injured (lame, stationary after herd movement, not responding to drone): page rancher Tier 2 — the protective layer is down.

## Sources

- Gehring T.M., VerCauteren K.C., Shivik J.A. (2004). "Livestock protection dogs in the 21st century." *Sheep & Goat Research Journal*.
- NM Dept of Agriculture: Use of Livestock Guardian Animals bulletin.
- Rigg R. (2001). "Livestock guarding dogs: their current use worldwide." *IUCN/SSC Canid Specialist Group Occasional Paper*.
- USDA-APHIS Wildlife Services: Nonlethal tools for predator management — LGDs.
