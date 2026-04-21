---
name: fence-line-protocols
description: Load when a perimeter sensor, GPS collar drift, or drone patrol detects a potential fence breach, and the agent needs to classify the cause and determine the correct response tier.
---

# Fence Line Protocols

## When to load

- FenceLineDispatcher received a LoRaWAN perimeter sensor alert or anomalous tag-drift event.
- Drone patrol identified a fence gap, broken wire, or downed post.
- An animal GPS collar shows a sudden location jump across a property boundary.

## Summary

Fence breaches on NM range operations have four primary causes: cattle drift through a gap (low urgency), coyote or predator crossing (medium urgency), wire cut by a trespasser or rustler (high urgency), and LGD roaming out (non-threat, log only). Misclassifying a trespass cut as a post knocked by a cow wastes the rancher's time and creates liability. The classification sequence — check tag drift pattern, check time of day, check perimeter camera, check for external evidence — resolves most cases without a rancher call.

## Key facts

- **NM fence law**: New Mexico is an open-range state. Landowners are responsible for fencing OUT (keeping neighbors' cattle off their property), not fencing IN. However, breach management is a shared operational responsibility in practice.
- **Common fence types on NM range**:
  - 3-strand barbed wire: most common. Posts typically cedar or steel T-posts at 8–12 ft spacing.
  - Net wire (woven): used near corrals and traps. Higher cost; more resistant to predator entry.
  - High-tensile electric: increasingly used in NM. Single or 3-strand; energizer-dependent.
- **Breach classification by cause**:
  - **Tag drift**: collar GPS shows gradual 50–200m drift through a fence line. Likely a slow graze-through at a broken wire. Low urgency.
  - **Coyote/predator crossing**: single thermal signature crossing a fence rapidly at night. No cattle movement. Note location for predator pattern log.
  - **Cattle escape**: multiple collar tags all moving together through a breach point. Fence gap confirmed by drone. Medium urgency (gather needed).
  - **Trespass or rustling**: no cattle movement but evidence of cut wire or recent vehicle tracks (visible on drone at low altitude in morning dew). High urgency.
  - **LGD crossing**: single large dog signature crossing at known patrol point. Log only.
- **Repair priority**: downed 3-strand barbed wire with cattle in the paddock = rancher action today. Broken top wire only, cattle in adjacent paddock = 24-hr window. Post-only damage (no wire break) = 48-hr window.
- **High-tensile electric**: energizer failure is common after lightning strikes (NM monsoon season). Energizer alarm triggers the same sensor as a breach. Distinguish by checking energizer output sensor.
- **Wire cut signs visible from drone**: clean wire ends with 6–12 inches of separation, both ends straight (tool cut vs. wire fatigue break which shows stretch). Visible in 4K camera at 30m AGL.
- **Rustling indicator**: vehicle track approach to fence line within 24 hrs of tag drift or missing animal. Page rancher and sheriff.

## Decision rules

```
IF LoRaWAN sensor trigger + single tag moving slowly through fence line at dawn or dusk:
  → Graze-through; Tier 1 log; drone confirm wire status on next scheduled patrol

IF multiple tags moving together through breach point:
  → Cattle escape; Tier 2 text rancher; drone to document breach GPS for repair

IF thermal detection of predator-sized animal crossing fence at night (no cattle following):
  → Predator crossing; log for PredatorPatternLearner; cross-reference coyote.md or wolf.md
  → No rancher page unless predator enters herd perimeter

IF drone visual shows cut wire (clean ends, no stretch):
  → Tier 3 call rancher immediately; possible trespass; document photos
  → If vehicle track or boot print visible: page rancher + log for sheriff report

IF energizer fault sensor active on electric fence:
  → Tier 2 text rancher; not a physical breach but herd is unprotected; repair same day

IF LGD tag crosses boundary at known patrol point:
  → Log only; no alert; LGD is doing its job

IF cattle outside boundary at peak heat (1100–1500):
  → Water access may be driving breach; check nearest water tank first
  → Tier 2 text rancher; cattle seeking water across boundary is a sign of tank failure
```

## Escalation / handoff

- **Tier 1 (log)**: single tag drift, LGD crossing, predator transit (no herd contact).
- **Tier 2 (text)**: cattle escape, energizer fault, water-driven breach.
- **Tier 3 (call)**: cut wire, vehicle tracks, missing animal.
- **Tier 4 (immediate)**: multiple missing animals + cut wire + tire tracks = possible rustling; call rancher and recommend sheriff contact.

## Sources

- NM Open Range statute: NMSA 1978 §77-16-1.
- USDA NRCS Fencing Practice Standard 382: New Mexico supplement.
- R-CALF USA: Cattle theft and rustling in the western US — situational report 2022.
- NM Dept of Agriculture Livestock Bureau: livestock inspection and theft reporting.
- University of Nebraska Extension EC826: Electric Fence Design and Operation.
