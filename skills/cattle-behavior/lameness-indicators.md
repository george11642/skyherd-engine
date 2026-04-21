---
name: lameness-indicators
description: Load when evaluating cattle gait, detecting weight-shifting or head-bobbing, scoring locomotion 1–5, or deciding whether a lame cow needs immediate vet escalation.
---

# Lameness Indicators

## When to load

- Camera or drone footage shows an animal with an abnormal gait.
- HerdHealthWatcher flags a cow isolating from the herd or standing apart at feeding time.
- Foot-rot or hardware disease is suspected following a wet season or muddy paddock rotation.

## Summary

Lameness is the third most costly health condition in beef cattle after respiratory disease and reproductive failure (USDA NAHMS 2017). It has two main causes on NM rangeland: foot rot (bacterial, *Fusobacterium necrophorum*) and foot/claw trauma (rocks, wire, cactus). A 5-point locomotion scoring system provides the fastest triage tool. A score of 3 or above requires same-day rancher notification; a score of 4–5 requires vet contact within 24 hours.

## Key facts

- **Gait score 1** — Sound. Flat back, long stride, full weight on all four feet.
- **Gait score 2** — Mildly lame. Slightly shortened stride in one limb; back stays level when standing, arches slightly when walking.
- **Gait score 3** — Moderately lame. Obvious asymmetry; back arched during walking; shortened stride; may shift weight when standing.
- **Gait score 4** — Lame. Will not bear weight on one limb when moving; travels with head down; visibly reluctant to walk.
- **Gait score 5** — Severely lame. Refuses to bear any weight; may be recumbent; does not keep pace with herd.
- Head-bob: the cow lifts its head as the sore leg strikes the ground (front leg) or drops it as the sore leg strikes (rear leg). Reliable indicator; visible from 30–50m on drone footage.
- Weight-shifting while standing: alternating partial weight relief between rear limbs is a subclinical lameness signal, often preceding detectable gait changes by 24–48 hrs.
- Social isolation: lame cows fall behind the herd during movement or stand apart at water/feed. Distance >50m from herd centroid for >2 consecutive observations is a useful proxy metric.
- Foot rot typically affects interdigital space; presents with swelling and foul odor. Onset 3–5 days post-exposure to wet/muddy conditions. Fever (>104°F) is common.
- Claw trauma from rocks, wire, or prickly pear spines presents without swelling; animal places foot cautiously.
- BRD-associated lameness (thrombosis) is rare but possible; cross-reference brd.md if respiratory signs co-occur.
- Rear-limb lameness is 3× more common than front-limb in range cattle (Merck Veterinary Manual).
- Chronic lameness (>14 days untreated) leads to BCS decline of 0.5–1.0 points per week.

## Decision rules

```
IF gait score 1–2 with no isolation or feed suppression:
  → log; re-evaluate in 48 hrs

IF gait score 3 OR weight-shifting for >4 hrs:
  → flag HerdHealthWatcher; page rancher Tier 2 message
  → drone close-pass to inspect interdigital space (look for swelling, discharge)
  → check foot-rot.md for confirmation criteria

IF gait score 4 OR animal not keeping pace with herd at movement:
  → page rancher Tier 3; vet contact recommended within 24 hrs
  → log GPS position for rancher locate-and-treat

IF gait score 5 OR recumbent animal detected:
  → page rancher Tier 4 (immediate); vet call now
  → flag GPS position; dispatch drone for continuous monitoring

IF score 3+ AND fever suspected (ear-tag temp sensor >104°F):
  → foot rot likely; rancher needs topical antibiotic spray + systemic oxytetracycline
  → page Tier 3

IF head-bob detected on drone without visible interdigital swelling:
  → suspect claw trauma or puncture; rancher visual inspection needed

IF >3 animals in same paddock show score 2+ within 5 days:
  → check paddock surface (wire, rocks, cactus encroachment); rotate paddock; page rancher Tier 2
```

## Escalation / handoff

- **Tier 1 (log)**: score 1–2, no feed/water disruption, no social isolation.
- **Tier 2 (text rancher)**: score 3, or 2+ animals in same paddock.
- **Tier 3 (call rancher)**: score 4, fever suspected, or any 14-day chronic case.
- **Tier 4 (call now)**: score 5, recumbent, or weight-loss trajectory >1 BCS point/week.
- Vet escalation: all score 4–5 cases; any suspected systemic infection with fever.

## Sources

- Sprecher D.J., Hostetler D.E., Kaneene J.B. (1997). "A lameness scoring system that uses posture and gait to predict dairy cattle reproductive performance." *Theriogenology* 47(6):1179–1187.
- Merck Veterinary Manual, 12th ed. — Lameness in Cattle.
- USDA NAHMS Beef 2017. "Lameness and foot disorders in U.S. beef operations."
- Apley M. (2015). "Beef cattle lameness management." *Veterinary Clinics of North America: Food Animal Practice* 31(1).
- Greenough P.R. (2007). *Bovine Laminitis and Lameness*. Saunders/Elsevier.
