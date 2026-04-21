---
name: paddock-rotation
description: Load when GrazingOptimizer is evaluating when to rotate the herd to the next paddock, interpreting NDVI data, or calculating rest-period adequacy for forage recovery in NM rangeland conditions.
---

# Paddock Rotation

## When to load

- GrazingOptimizer is running a weekly rotation proposal.
- NDVI satellite data shows a paddock at or below the rotation threshold.
- A water tank failure or predator pressure requires an unscheduled herd move.
- Post-monsoon forage flush is prompting an earlier-than-planned rotation back to a rested paddock.

## Summary

Proper paddock rotation is the primary management tool for preventing overgrazing on NM rangeland. Blue grama (*Bouteloua gracilis*) — the dominant NM range grass — needs 60–90 days of rest after heavy grazing to recover root reserves. Rotating too early reduces long-term range health; rotating too late causes soil compaction and weed invasion. NDVI (Normalized Difference Vegetation Index) from Sentinel-2 satellite data provides a 10m-resolution proxy for forage mass that updates every 5 days. The combination of NDVI threshold + days since last use + weather forecast drives optimal rotation decisions.

## Key facts

- **NDVI trigger for rotation OUT** (move cattle out of paddock): NDVI drops to <0.25 on two consecutive measurements, OR residual forage height <2–3 inches (visual or ultrasonic sensor).
- **NDVI trigger for rotation IN** (cattle can return): NDVI >0.35 AND days-rested ≥ 60 (spring–fall) or ≥ 90 (drought conditions).
- **Minimum rest period**:
  - Spring/summer (adequate moisture): 45–60 days.
  - Dry year or drought: 75–90 days minimum; 120 days if range severely depleted.
  - Post-monsoon flush: paddock can recover faster; check NDVI before assuming standard rest period.
- **Stocking density**: NM NRCS recommended stocking on medium-quality rangeland 3–5 AUM/section (640 acres) per year. High variability by soil type and precipitation zone.
- **AUM (Animal Unit Month)**: 1 cow + calf pair = 1.25 AUM; dry cow = 1.0 AUM; yearling = 0.6 AUM.
- **Grazing days per paddock**: target 5–7 days maximum per entry before rotation (rotational system). Extended stays >10 days defeat the recovery benefit.
- **Water proximity**: cattle graze effectively within 1.0 mile of water on flat terrain; up to 1.5 miles on gentle slopes. Paddocks >1.5 miles from water result in undergrazing of distant areas and overgrazing near water.
- **Mesquite and cactus encroachment**: NM rangelands show increasing shrub encroachment. NDVI alone cannot distinguish grass from mesquite canopy; ground-truth with drone RGB pass every 3 months.
- **Cheatgrass invasion** (*Bromus tectorum*): NDVI peaks earlier in spring than native grasses; can mask overgrazing. If NDVI shows green in March but grass is <3 inches by May, suspect cheatgrass.
- **Post-monsoon window**: July–September monsoon often produces a forage flush. NDVI can jump 0.10–0.15 units in 2 weeks. GrazingOptimizer should flag this window for higher stocking density or accelerated rotation.

## Decision rules

```
IF NDVI >0.35 AND days-rested >60 AND weather forecast >0.5 inch rain in 14 days:
  → Paddock ready; recommend rotation IN

IF NDVI <0.25 on 2 consecutive readings (10-day window):
  → Paddock overused; recommend rotation OUT today

IF grazing days in current paddock ≥7:
  → Standard rotation trigger regardless of NDVI; Tier 2 text rancher with recommendation

IF days-rested <45 AND NDVI <0.30:
  → Do NOT rotate back; forage not recovered; Tier 2 note to rancher

IF paddock distance from water >1.5 miles:
  → Flag to rancher: uneven grazing likely; consider portable water deployment

IF monsoon event >0.75 inch in 48 hrs on rested paddock:
  → Re-evaluate NDVI in 7 days; early return may be appropriate if NDVI response confirmed

IF drought declared (USDA Drought Monitor D2+ for county):
  → Extend minimum rest period to 90 days; reduce stocking density recommendation 20%

IF drone RGB pass shows >30% mesquite or shrub cover in paddock:
  → Flag rancher for mechanical or chemical shrub control; do not count shrub cover as forage in NDVI
```

## Escalation / handoff

- **Tier 1 (log)**: NDVI normal, rotation schedule on track.
- **Tier 2 (text)**: rotation recommendation (in or out), monsoon adjustment, drought advisory.
- **Tier 3 (call)**: emergency unscheduled rotation needed (water failure, predator pressure, flood).
- GrazingOptimizer produces weekly proposal; rancher approves moves. Agent does not move cattle autonomously.

## Sources

- USDA NRCS NM: Grazing Management Technical Note NM-190.
- Holechek J.L., Pieper R.D., Herbel C.H. (2011). *Range Management: Principles and Practices*, 6th ed. Pearson.
- USDA Drought Monitor: droughtmonitor.unl.edu.
- Goward S.N. et al. (1991). NDVI remote sensing for rangeland monitoring. *Remote Sensing of Environment* 35(2–3).
- NM State University Extension Guide B-808: Rotational Grazing for New Mexico Rangelands.
