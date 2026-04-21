---
name: nm-predator-ranges
description: Load when correlating a predator detection with its expected range in New Mexico, assessing whether a species is plausible at a given location, or briefing agents on the geographic distribution of major livestock predators.
---

# NM Predator Ranges

## When to load

- A thermal detection is ambiguous between two species and geographic plausibility helps resolve it.
- PredatorPatternLearner is building a threat-probability map for a specific ranch location.
- A new ranch is being onboarded and requires a baseline predator risk profile by county.

## Summary

New Mexico has three major livestock predators with distinct geographic ranges: coyotes (statewide, all terrain), mountain lions (concentrated in mountain ranges), and Mexican gray wolves (restricted to a defined federal recovery zone in western NM). Knowing which predators are plausible at a given GPS coordinate is the first filter before investing resources in full species-ID. A coyote-sized thermal contact in Lincoln County is almost certainly a coyote; the same contact in Catron County near the Gila has a non-trivial wolf probability.

## Key facts

**Coyote** (*Canis latrans*):
- Range: statewide, all 33 NM counties, all elevations (sea level to 12,000+ ft).
- Density highest: eastern NM plains (Roosevelt, Curry, Quay counties), agricultural edges, riparian corridors.
- No federal protection; managed by NMDGF; year-round take permitted.

**Mountain Lion** (*Puma concolor*):
- Core range: Gila Wilderness (Catron, Grant, Hidalgo counties), Sacramento Mountains (Otero county), Sangre de Cristo Mountains (Taos, Mora, Santa Fe, Colfax counties), Jemez Mountains (Sandoval, Rio Arriba), Guadalupe Mountains (Eddy/Otero border).
- Lower density in eastern plains, central desert basins.
- Estimated NM population: 3,000–4,500 animals (NMDGF 2023).
- Game animal; regulated hunting season; depredation permits available from NMDGF.
- Legal: NMDGF permit needed for lethal removal; call first.

**Mexican Gray Wolf** (*Canis lupus baileyi*):
- USFWS Mexican Wolf Experimental Population Area (MWEPA): encompasses the Apache, Gila, and Cibola National Forests in AZ and NM. In NM: roughly Catron, Grant, Hidalgo, and western Socorro counties; south of I-40, west of the Rio Grande.
- Active packs (as of Jan 2024): approximately 30 packs in the US side of the MWEPA; 241 individuals.
- High-probability counties for wolf contact: Catron (highest), Grant, Hidalgo, western Socorro.
- Near-zero probability: eastern NM plains, north-central NM away from designated recovery area.
- Legal: ESA-protected; any take without permit is a federal felony.

**Black Bear** (*Ursus americanus*):
- Range: forested mountain ranges statewide; Gila, Sacramento, Jemez, Sangre de Cristo, Manzano, San Mateo, Guadalupe mountains.
- Not a primary cattle predator; primarily opportunistic on grain/silage and rare calf predation.
- Estimated NM population: 5,000–6,000 (NMDGF).
- Active May–November; hibernates Dec–Feb at higher elevations.
- Mention here for completeness; thermal signature larger and blockier than any canid.

**Bobcat** (*Lynx rufus*):
- Statewide; primarily predates on sheep, goats, and young poultry. Rarely attacks beef calves >1 month old.
- Thermal signature: medium felid (15–35 lb); short tail distinguishes from lion at close range.

## Decision rules

```
IF predator detection in Catron or Grant county:
  → Wolf plausibility high; cross-reference wolf.md in addition to coyote.md for any canid

IF predator detection in eastern NM (Roosevelt, Curry, Quay, De Baca counties):
  → Wolf probability near zero; coyote is default canid assumption

IF large felid detected in Gila foothills or Sacramento Mountains:
  → Mountain lion expected; follow mountain-lion.md protocol

IF large bear-profile thermal in Gila or Sacramento (>200 lb, rounded body, no visible tail):
  → Log; black bear; not a direct cattle threat unless near feed storage; Tier 1

IF coyote-sized contact in MWEPA counties with pack behavior (3+ animals):
  → Upgrade to wolf protocol; wolf pack confirmation needed before downgrading
```

## Escalation / handoff

- County-level plausibility is a filter, not a confirmation. Species misidentification is still possible even where probability is low.
- PredatorPatternLearner maintains a per-ranch predator probability map updated weekly.

## Sources

- NM Dept of Game and Fish: Wildlife Management Plans for mountain lion, black bear, bobcat (2020–2023).
- USFWS Mexican Wolf Recovery Program: Annual Report 2024.
- USDA-APHIS Wildlife Services: Annual livestock loss report — NM (2022).
- NM Game and Fish species range maps: wildlife.state.nm.us.
- Logan K.A. & Sweanor L.L. (2001). *Desert Puma*. Island Press.
