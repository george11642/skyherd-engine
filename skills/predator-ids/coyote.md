---
name: coyote
description: Load when thermal or visual drone footage shows a canid-shaped animal near the herd perimeter, or when PredatorPatternLearner is classifying a potential predator contact on the fence line.
---

# Coyote Identification

## When to load

- Thermal camera footage shows a medium-sized mammal with canid gait near livestock at night.
- FenceLineDispatcher received a fence breach or perimeter sensor trigger and dispatching drone to classify.
- PredatorPatternLearner is building a predator-activity dossier for a specific fence segment.

## Summary

The coyote (*Canis latrans*) is the most common livestock predator in New Mexico and across the western US. Coyotes kill primarily lambs, kid goats, and young calves (1–3 weeks of age); adult cattle are rarely attacked unless the coyote pack is unusually large or the cow is incapacitated. A lone coyote near a herd is a management concern; a pair near a calving pen is a Tier 3 event. Correct ID from thermal imagery prevents the agent from treating Livestock Guardian Dogs (LGDs) as threats — a critical false-positive risk.

## Key facts

- **Weight**: 20–50 lb (9–23 kg); males slightly larger than females. Compare to LGD breeds: Great Pyrenees 85–115 lb.
- **Size**: shoulder height 23–26 inches; body length 3.5–4.5 ft including tail.
- **Gait**: trot is fox-trot style with diagonal pairs (different from dog's bounding gallop). Coyotes rarely stop moving for more than 10–15 seconds at a distance.
- **Thermal signature**: compact oval body, narrow tapered muzzle visible in close passes, bushy tail held low or horizontal. Body temp similar to domestic dog.
- **Coat thermal**: summer coat (May–Sep) produces lower insulation; body heat bleeds more to thermal cam. Winter coat (Oct–Apr) insulates more; thermal signature slightly dimmer at core.
- **Activity pattern**: primarily crepuscular and nocturnal; peak activity 2100–0300 and 0500–0900. Daytime sightings increase when denning (pups present May–Jul).
- **Lone vs. pair vs. pack**: coyotes in NM primarily operate as mated pairs or family groups of 3–7. A pack approaching livestock warrants higher urgency than a lone animal.
- **Vocalization**: howl-yip sequences; distinctive from wolf (lower frequency, longer sustained howl) and domestic dog (bark-dominant). Audio sensor can support ID.
- **NM range**: statewide, all elevations. Most dense on farmland edges and riparian corridors. Higher density on eastern NM plains than in western mountain terrain where wolf and lion compete.
- **Kill sign**: calves killed by coyotes typically have throat bites and may be partially consumed. Dragging evidence. Compare to lion (clean kill, buried remains) and dog (messy bite, no caching).
- **Livestock losses NM**: coyotes account for ~60% of livestock predator kills in NM (USDA-APHIS Wildlife Services annual data).

## Decision rules

```
IF thermal signature matches coyote weight/gait at >200m from herd:
  → Log; no immediate action; PredatorPatternLearner records time/location

IF single coyote within 50–200m of herd at night:
  → Tier 2 log with alert; drone position at 60m AGL; activate acoustic deterrent
  → Cross-reference deterrent-protocols.md: coyote frequency band 10–18 kHz

IF coyote pair or group within 100m of herd:
  → Tier 2 text rancher + activate deterrent; increase monitoring frequency

IF coyote within 50m of calving pen or cow with very young calf (<3 weeks):
  → Tier 3 call rancher immediately; calf at real risk

IF coyote enters herd perimeter (30m or less):
  → Tier 3 call rancher; sustained acoustic deterrent; drone strobe if equipped

IF thermal signature is coyote-sized but stationary for >60 seconds in lying position near herd:
  → Do NOT assume threat yet; cross-reference livestock-guardian-dogs.md first

IF acoustic sensor detects yip-howl sequence approaching from multiple directions:
  → Pack approach; Tier 3 call rancher; all deterrents active
```

## Escalation / handoff

- **Tier 1**: single coyote >200m, no calf or calving activity nearby.
- **Tier 2**: single or pair within 200m, or any approach during calving season.
- **Tier 3**: pack, calf at risk, or animal inside herd perimeter.
- Hand off to PredatorPatternLearner: log all events with timestamp, GPS, thermal confidence score.
- Non-lethal deterrents only from drone. No autonomous physical intervention.

## Sources

- Bekoff M. (1978). *Coyotes: Biology, Behavior, and Management*. Academic Press.
- USDA-APHIS Wildlife Services. Annual livestock predator loss data — New Mexico.
- NM Dept of Game and Fish: Coyote management fact sheet.
- Sacks B.N. et al. (2011). "Coyote movements, diet, and social behavior in a rural landscape." *Journal of Wildlife Management*.
- Shivik J.A. et al. (2003). "Nonlethal techniques for managing predation." *Sheep & Goat Research Journal*.
