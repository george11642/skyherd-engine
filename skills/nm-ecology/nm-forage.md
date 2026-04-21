---
name: nm-forage
description: Load when evaluating forage quality, interpreting NDVI data in the context of NM plant species, or advising GrazingOptimizer on forage availability by season and location.
---

# NM Forage Species and Range Conditions

## When to load

- GrazingOptimizer needs species-specific context when interpreting NDVI data.
- A paddock drone pass shows unusual vegetation that might affect stocking decisions.
- Seasonal forage calendar affects whether to move cattle into or out of a paddock.

## Summary

New Mexico rangeland is predominantly warm-season grass dominated, with blue grama (*Bouteloua gracilis*) as the keystone species across most of the state. Forage productivity is tightly coupled to precipitation — NM receives 50–60% of its annual precipitation during the July–August monsoon. Understanding which grasses are present, when they peak, and what weedy species threaten productivity is fundamental to sound rotation decisions. Misidentifying a cheatgrass flush as native grass recovery can lead to overgrazing the following year.

## Key facts

**Primary forage grasses** (NM rangeland):

- **Blue grama** (*Bouteloua gracilis*): dominant short-grass prairie and lower elevation grasslands (4,000–7,000 ft). Peak growth Jul–Sep. Highly drought-tolerant; recovers slowly from overgrazing. Recognizable "eyelash" seed head visible in Aug–Sep. NDVI signature: 0.25–0.45 at full growth.
- **Side-oats grama** (*Bouteloua curtipendula*): mid-elevation grasslands and oak savanna. Slightly taller than blue grama; oats hanging along one side of stem. High palatability; preferred by cattle over blue grama. Peak Aug–Sep.
- **Black grama** (*Bouteloua eriopoda*): lower elevation desert grassland (<5,000 ft). Chihuahuan Desert foothills. Slower recovery than blue grama; overgrazing can convert to shrubland. Southern Doña Ana/Luna/Hidalgo counties.
- **Tobosa grass** (*Pleuraphis mutica*): saline/alkaline flats, playas. Forms dense colonies. Moderately palatable when young in spring; coarse and low-value by summer.
- **Sacaton** (*Sporobolus wrightii*): riparian corridors, desert flats with seasonal water. Tall bunchgrass (3–6 ft); valuable summer forage; high biomass production. Common in Gila River drainages.
- **Alkali sacaton** (*Sporobolus airoides*): saline/alkaline sites, arroyos. Moderate palatability.

**Invasive/problematic species**:

- **Cheatgrass** (*Bromus tectorum*): winter annual; NDVI peaks February–April then dies; fire risk increases by June. Invades disturbed rangelands statewide. NDVI greens up earlier than native grasses — an NDVI spike in March on a semi-arid site may be cheatgrass, not native recovery.
- **Mesquite** (*Prosopis glandulosa*): brush encroachment; photosynthetically active and can inflate NDVI while reducing usable forage. Increases after soil disturbance or heavy grazing. NDVI from mesquite canopy can exceed 0.40 on bare soil — similar to healthy grass but provides no forage.
- **Snakeweed** (*Gutierrezia sarothrae*): increases with overgrazing; mildly toxic; cattle avoid it, leaving it to spread. Reduces usable forage density.
- **Prickly pear** (*Opuntia* spp.): increases with overgrazing and drought. Not forage (except emergency use when burned); can cause foot injuries that become infected.

**Forage production windows** (NM range):
- April–June: cool-season grasses and annuals (minor component); dry pre-monsoon; low productivity.
- July–September: monsoon flush; primary warm-season grass growth window; 60–70% of annual forage production.
- October–November: post-monsoon; curing on the stem; good quality hay-on-the-hoof for fall calves.
- December–March: dormant; protein content drops; supplemental feeding often needed.

## Decision rules

```
IF NDVI >0.35 in February or March on NM rangeland:
  → Suspect cheatgrass; confirm with drone RGB pass; do not credit as native forage recovery

IF NDVI shows 0.35–0.45 in August–September:
  → Likely blue grama or side-oats grama peak; paddock probably ready for grazing entry

IF drone pass shows >30% shrub cover (mesquite, snakeweed):
  → NDVI overstates usable forage; flag for rancher; brush management recommendation

IF paddock at <3,000 ft elevation in southern NM:
  → Black grama likely present; use 90-day minimum rest period (slower recovery than blue grama)

IF sacaton present (riparian paddock, 3–6 ft bunchgrass visible on drone):
  → Higher forage density than NDVI alone suggests; stocking density can be 20–30% higher

IF range dominated by tobosa or snakeweed:
  → Flag for paddock value assessment; lower productivity than grama-dominated range
```

## Escalation / handoff

- GrazingOptimizer uses this skill alongside paddock-rotation.md for data-driven rotation decisions.
- Forage species concern (invasive spread, brush encroachment): Tier 2 text to rancher; not an emergency but a long-term productivity concern.

## Sources

- Holechek J.L., Pieper R.D., Herbel C.H. (2011). *Range Management*, 6th ed. Pearson.
- USDA NRCS NM Plant Materials Center: species guides for grama grasses, sacaton, tobosa.
- NM State University Extension AG-471: Grasses of New Mexico Rangelands.
- Burgess T.L. & Northington D.K. (1985). Desert vegetation of the Chihuahuan Desert. *Journal of the Arizona-Nevada Academy of Science*.
- USDA NAIP / Sentinel-2: NDVI data interpretation for NM rangelands.
