---
name: herd-structure
description: Load when interpreting spatial distribution of a herd, identifying alpha-cow movement leadership, detecting separation stress, or evaluating whether herd cohesion is normal or disrupted.
---

# Herd Structure

## When to load

- Drone footage shows unusual herd fragmentation or a single animal excluded from the group.
- PredatorPatternLearner needs to understand baseline herd clustering before flagging a predator scatter event.
- GrazingOptimizer is evaluating whether a herd move will be followed by the full group or only part of it.
- An animal has been physically separated by fencing or handling and needs reintroduction assessment.

## Summary

Beef cattle are highly social; the herd is organized around a stable dominance hierarchy that emerges by 6–18 months of age and rarely changes. One to three alpha cows lead grazing movements; the rest follow within 15–30 minutes. An intact, unstressed herd maintains a consistent spatial spread of 10–40m per animal during grazing, compressing to tight clusters (<5m separation) when threatened or moving between paddocks. Disruption of this structure — fragmentation, persistent isolation, or failure to follow the leader — is a more reliable early signal of predator pressure or illness than any individual behavior alone.

## Key facts

- Herd size on NM range operations: 50–250 cows typical; 1 bull per 25–30 cows breeding season.
- Linear dominance hierarchy: older, larger cows dominate feed and water access. Rank is mostly stable; contested only by introduction of new animals or after injury.
- Lead cows: typically 1–3 high-ranking cows initiate grazing movements. 80% of the herd follows within 30 min (Uetake 2021). If the lead cow is sick or removed, herd movement becomes disorganized.
- Flight zone: 10–25m for range cattle unaccustomed to close human/drone contact; 3–5m for cattle habituated to daily handling. Drone operating inside flight zone triggers cohesion behaviors (bunching, flight).
- Inter-animal distance during grazing: 3–10m for bonded pairs (dam/calf, sisters), 10–30m for general herd spread. Distances >50m between individuals during rest = potential separation.
- Separation stress indicators: vocalizations (bawling), pacing fence lines, repeated approach to last-known herd location. Visible on audio sensors or camera.
- Calf-cow bonding: established within 4–6 hrs of birth; cows and calves maintain visual contact and reunite within 30 min after brief separations for at least 6 months.
- Introduction of new animals: dominant challenge behaviors peak in first 3–5 days; fighting is most intense. New animals are often displaced from water and feed during this period.
- Predator scatter event signature: herd centroid moves rapidly (>100m in <5 min), animals spread beyond normal 50m radius, vocalizations elevated. Compare against baseline spread using GPS collar data.
- Thermoregulation clustering: in cold (below 30°F) or rain, cattle cluster tight (1–3m separation) to share body heat. Not a stress event; normal behavior.
- NM range herds: typically single-breed or crossbred Angus/Hereford/Brangus. Brangus (3/8 Brahman) shows slightly wider individual spacing and higher heat tolerance than British breeds.

## Decision rules

```
IF herd centroid displacement >100m in <5 min AND time is 2000–0600:
  → predator scatter; cross-reference predator-ids skill; page rancher Tier 3

IF single animal >100m from nearest herd member for >2 consecutive drone passes:
  → flag for HerdHealthWatcher; check lameness, illness, calving signs

IF herd fails to follow lead cow during scheduled paddock move:
  → check lead cow health; may indicate lead cow illness or injury
  → re-attempt move; if second failure, page rancher Tier 2

IF >3 new animals introduced in same week:
  → increase observation frequency; monitor feed/water displacement of low-rank animals
  → if BCS decline in specific animals, flag HerdHealthWatcher

IF herd bunched tight (all animals <5m separation) during non-cold non-rain conditions:
  → predator nearby or recent; cross-reference predator-ids; drone sweep perimeter

IF dam and calf separated >2 hrs with audible bawling:
  → confirm physical barrier or handler separation; page rancher Tier 2 if unexplained

IF bull displaying mounting behavior out of season (Oct–Feb, outside breeding window):
  → log; possible bull management issue; text rancher non-urgent
```

## Escalation / handoff

- **Tier 1 (log)**: normal spread variation, brief separations (<30 min), thermoregulation clustering.
- **Tier 2 (text)**: persistent individual isolation (>2 hrs), new animal introduction conflicts, out-of-season bull behavior.
- **Tier 3 (call)**: herd scatter event (predator signature), lead cow illness suspected, dam-calf separation with vocalizations.
- Hand off to PredatorPatternLearner for any scatter event with confirmed or suspected predator.

## Sources

- Uetake K. (2021). "Cattle welfare and behavior." *Animal Science Journal* 92(1).
- Bouissou M.F. et al. (2001). "The social behaviour of cattle." In: Keeling L.J. & Gonyou H.W. (eds.), *Social Behaviour in Farm Animals*. CABI.
- Grandin T. (2014). *Livestock Handling and Transport*, 4th ed. CABI.
- USDA NAHMS Beef 2017 reference data on herd management practices.
- NM State University Extension: Range Cattle Management Bulletin.
