---
name: feeding-patterns
description: Load when interpreting cattle trough activity, assessing whether a herd is feeding normally, or flagging anomalies in grazing/bunker congregation timing.
---

# Feeding Patterns

## When to load

- Drone or trough-cam footage shows unexpected congregation or absence at feed stations.
- HerdHealthWatcher is evaluating whether low trough activity is a health signal vs. behavioral norm.
- GrazingOptimizer needs baseline activity curves to compare against current movement data.

## Summary

Cattle are crepuscular grazers — most active at dawn and dusk, with a midday rest period that lengthens under heat load. An adult beef cow eats 8–12 times per day in bouts of 30–90 minutes, spending 6–8 hours total grazing. Trough congregation typically follows a bimodal curve: peak at 0600–0900, secondary peak at 1700–2000. Deviation from that pattern — especially a flat line through both peaks — is a reliable early indicator of illness, social disruption, or water failure.

## Key facts

- Average daily dry matter intake: 2–2.5% of body weight (a 1,000 lb cow eats ~22 lbs DM/day).
- Normal grazing bouts: 8–12 per day, each 10–45 min; total ~6–8 hrs.
- Resting/rumination: ~8 hrs/day, usually midday. Cows ruminate lying down; standing ruminators may be uncomfortable.
- Trough peak windows: 0600–0900 and 1700–2000 local time. These shift 30–60 min later in summer.
- Social hierarchy at the bunk: dominant cows eat first. Subordinates wait or eat during off-peak windows. A subordinate eating alone at midday is normal; a dominant cow absent from both peaks is not.
- Water intake: 1 gallon per 100 lbs body weight per day baseline; doubles above 80°F ambient.
- Feeding-to-water coupling: cattle drink 2–4 times per day, usually immediately after a major grazing bout. Camera detecting grazing but no trough visits within 2 hrs suggests water access failure.
- Herd-wide feeding suppression (>30% of animals absent from both peaks on the same day) correlates with a pathogen event, toxic forage, or significant weather disturbance (USDA NAHMS Beef 2017).
- Individual suppression lasting >24 hrs warrants health evaluation.
- NM-specific: summer monsoon (Jul–Aug) shifts peak grazing earlier; cows graze at dawn to avoid afternoon heat. Blue grama and side-oats grama are preferred species in NM; sacaton and alkali sacaton used near riparian draws.

## Decision rules

```
IF both morning and evening peaks absent for one animal over 24 hrs:
  → flag for HerdHealthWatcher; check lameness, BCS, vital signs

IF both peaks suppressed herd-wide (>30% absent) same day:
  → check water tank level first (most common cause in NM summer)
  → if water OK, check forage quality (new batch? toxic plant encroachment?)
  → if forage OK, flag pathogen concern; escalate to rancher

IF only morning peak absent, evening normal:
  → low priority; may reflect overnight grazing; re-check at 48 hrs

IF trough-cam shows feeding but animal in isolation from herd:
  → cross-reference lameness-indicators skill; social isolation + eating = early lameness

IF cow grazing at 1100–1400 on a 95°F+ day:
  → check heat-stress skill; normal cattle rest midday in heat; continued grazing = stress signal

IF feeding drops 48 hrs before calving window:
  → expected; cross-reference calving-signs skill
```

## Escalation / handoff

- **Page rancher** (Tier 2) if herd-wide suppression persists past 0900 with no water/forage explanation.
- **Page rancher** (Tier 3) if an individual animal misses 2 consecutive full days.
- **Log silently** (Tier 1) for single-peak absences or isolated subordinate skipping.
- Hand off to HerdHealthWatcher for any flag involving concurrent gait or posture anomaly.

## Sources

- USDA NAHMS Beef 2017 reference period study (beef cow health management practices).
- Uetake K. (2021). "Cattle welfare and behavior." *Animal Science Journal* 92(1).
- NRC (2016). *Nutrient Requirements of Beef Cattle*, 8th rev. ed. National Academies Press.
- Grandin T. & Deesing M. (2014). *Genetics and the Behavior of Domestic Animals*, 2nd ed. Academic Press.
- NM State University Extension AG-397: Grazing Management in New Mexico Rangelands.
