---
name: thermal-signatures
description: Load when classifying an unknown animal from IR thermal imagery alone — covers species discrimination by body temperature profile, size, gait, and posture at typical drone patrol altitudes (40–100m AGL).
---

# Thermal Signatures — Species ID from IR

## When to load

- Drone thermal camera has detected an animal and species is unknown.
- PredatorPatternLearner needs to cross-reference a thermal detection against known species signatures.
- FenceLineDispatcher is deciding whether to escalate before visual confirmation is available.

## Summary

A drone-mounted thermal camera (7.5–14 µm LWIR) at 40–100m AGL can identify species by combining apparent body temperature, size estimate, head-to-body ratio, gait pattern, tail characteristics, and behavioral posture. No single feature is reliable alone; classification uses a combination. This file covers the species most relevant to NM ranch operations: coyote, mountain lion, wolf, bear (black), cattle, LGD, mule deer, and human. False positives on wildlife cost resources; false negatives on predators cost livestock.

## Key facts

**Body temperature and coat insulation** (at ambient 50–70°F):

| Species | Apparent thermal brightness | Notes |
|---|---|---|
| Coyote (summer coat) | High | Thin coat; body heat bleeds well to sensor |
| Coyote (winter coat) | Medium-high | More insulation; face and legs remain hot |
| Mountain lion | Medium | Short coat; excellent thermal visibility; long tail always warm |
| Mexican gray wolf | Medium-high | Similar to coyote but larger heat blob |
| Black bear | Low-medium | Dense fur; feet and muzzle are hottest areas |
| Cattle (cow) | High | Large heat mass; highly visible; distinctive rectangular torso |
| LGD (Great Pyrenees) | Low | Dense double coat traps heat; appears cool at distance |
| LGD (Anatolian) | Medium | Shorter coat; warmer signature than Pyrenees |
| Mule deer | Medium | Slender profile; long narrow legs visible |
| Human | High | Upright posture; distinctive |

**Size estimates at altitude** (apparent pixel footprint at 60m AGL, 640×512 sensor, 13mm lens ≈ 0.7m/pixel):
- Coyote: 3–6 pixels wide at body.
- Mountain lion: 5–8 pixels wide; tail extends 4–7 pixels.
- Cattle: 8–15 pixels wide; 10–18 pixels long.
- LGD (Pyrenees): 5–9 pixels wide (smaller than cattle, larger than coyote).

**Gait signatures**:
- Coyote: diagonal trot; short bounding gallop when alarmed; rarely freezes for >15 sec.
- Mountain lion: fluid walk with freeze-stalk pattern; long tail visible dragging or lifted slightly.
- Wolf: purposeful loping trot; longer stride than coyote; covers ground steadily.
- LGD: slow deliberate walk; lies down among herd; does not flee drone.
- Cattle: walk in groups; synchronous movement; tail swishing visible as heat flicker.
- Deer: bounding gait when alarmed; thin long legs give characteristic "stick-legged" IR profile.

**Head-to-body ratio**:
- Felid (lion): round compact head; body length >> head size; long tail is definitive.
- Canid (coyote/wolf): narrow tapered muzzle; head in proportion to body; ears upright.
- LGD: blockier head than coyote; heavier shoulders visible even through insulating coat.
- Bear: round head on massive body; no visible tail in thermal.

**Behavioral posture cues**:
- Predator approaching herd: low body posture, freeze-advance pattern, wind-checking (facing upwind).
- LGD on patrol: upright posture, slow walk, occasional head-raise alert, remains near herd.
- Deer/elk: generally moving away from herd; not approaching.

## Decision rules

```
IF thermal blob is large (cattle-sized), rectangular, in group movement:
  → Cattle herd; no predator flag

IF thermal shows elongated body + tail length ≈ body length + freeze-stalk behavior:
  → Mountain lion; escalate per mountain-lion.md

IF thermal shows 3–6 px body width, coyote gait, <60 lb estimated, flees drone:
  → Coyote; escalate per coyote.md

IF thermal shows large canid body, pack formation (3+ animals):
  → Wolf pack; escalate per wolf.md regardless of confidence level

IF large canid, low thermal brightness, moves slowly among cattle, does not flee drone:
  → LGD; DO NOT escalate; log per livestock-guardian-dogs.md

IF upright warm signature, 5.5–6.5 ft height, bipedal:
  → Human; Tier 2 fence-line-protocols.md; trespass or rancher on property

IF animal is present but cannot be classified after 2 drone passes:
  → Log with thermal image; page rancher Tier 2 for human visual ID; do not assume predator or non-predator
```

## Escalation / handoff

- All unclassified animals >30 lb near the herd at night: Tier 2 at minimum.
- Classification confidence <70%: escalate one tier above the base species tier.
- Store all thermal clips for PredatorPatternLearner training data.

## Sources

- DJI Zenmuse XT2 / Mavic 3 Enterprise thermal camera specs (FLIR Lepton/BOSON sensor).
- Goodin D.G. et al. (2017). "Thermal infrared detection of large mammals." *Wildlife Biology in Practice* 13(2).
- NM Dept of Game and Fish: Wildlife species identification guides.
- Christiansen F. et al. (2020). "Thermal drone-based surveys for mammal detection." *Remote Sensing in Ecology and Conservation* 6(3).
- USDA-APHIS Wildlife Services: Wildlife identification field guide — western US.
