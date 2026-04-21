---
name: heat-stress
description: Load when evaluating cattle behavior or physiology during high ambient temperatures, calculating Temperature-Humidity Index thresholds, or deciding whether to initiate cooling or shade interventions.
---

# Heat Stress

## When to load

- Ambient temperature exceeds 80°F (NM summer, May–September).
- Drone or camera shows cattle bunched in shade, standing in water, or panting.
- GrazingOptimizer is evaluating whether to delay a herd move.
- THI (Temperature-Humidity Index) data is available from a weather sensor.

## Summary

Heat stress is the leading production-loss event on NM beef operations from May through early September. The THI threshold where cattle begin experiencing measurable stress is 72 (equivalent to roughly 77°F at 50% RH). Above THI 84, health risk is severe. NM's low humidity makes shade and water access more effective interventions than in humid climates — a shaded cow in NM may have an effective THI 10 points lower than an exposed animal. The dangerous combination is THI >80 at night, which prevents recovery; cattle accumulate heat debt across multiple days.

## Key facts

- **THI formula**: THI = (1.8 × T_°C + 32) − (0.55 − 0.0055 × RH%) × (1.8 × T_°C − 26) where T is dry-bulb temp.
- **Thresholds**:
  - THI <72: No stress.
  - THI 72–79: Mild stress. Watch black-coated animals; pregnant/postpartum cows most vulnerable.
  - THI 80–84: Moderate stress. Panting rate 60–80 breaths/min; bunching in shade.
  - THI 85–89: Severe stress. Open-mouth panting, drooling, head weaving; feed intake drops 20–30%.
  - THI ≥90: Danger. Death risk in vulnerable animals without intervention.
- **Panting score** (0–4 scale):
  - 0: Normal respiration, no flank movement.
  - 1: Panting (>60 breaths/min); mouth closed; no drool.
  - 2: Open-mouth panting; tongue slightly visible; mild drool.
  - 3: Open-mouth panting; tongue hanging; excessive drool; head extended.
  - 4: Labored breathing; tongue far out; excessive saliva; animal may stagger.
- Shade-seeking: cattle move to shade when skin surface temp approaches 105–108°F. Visible on thermal drone as congregation in shaded areas.
- Watering frequency doubles above THI 80; a cow drinking 5+ times per day is a reliable heat-stress indicator.
- Black coat vs. red or white: black-hided cattle absorb ~30% more solar radiation; they reach stress thresholds 1–2 THI points earlier.
- NM-specific: monsoon (Jul–Aug) raises RH to 40–60%, elevating THI even when temps are lower than June peaks. The first monsoon rain often brings the highest combined THI of the year.
- Night THI recovery: if nighttime THI stays above 65, cattle carry over heat debt. Consecutive nights with THI >65 compound risk rapidly.
- Pregnant cows in third trimester are the highest-risk cohort; heat stress drops calf birth weight and cow conception rates for the next cycle.
- Feedlot-style cattle are more vulnerable than range cattle; range animals have more space to seek shade and water.

## Decision rules

```
IF THI <72:
  → no action; log

IF THI 72–79:
  → log; increase check frequency to 30-min intervals
  → ensure water tanks at >50% capacity (cross-reference water-tank-sops.md)

IF THI 80–84 AND panting score >1 visible on camera:
  → text rancher Tier 2: "heat index elevated, ensure shade access and full water tanks"
  → flag GrazingOptimizer to suspend herd moves until after 1800

IF THI >84 OR open-mouth panting observed (score 2+):
  → page rancher Tier 3; recommend supplemental water (portable tank or extra fill)
  → drone check for any recumbent animals

IF THI >88 OR panting score 3+ in any animal:
  → page rancher Tier 4; emergency cooling protocol
  → flag all pregnant cows and black-hided animals for priority check
  → suspend all drone operations except monitoring (drone itself adds heat stress noise)

IF nighttime THI >65 for 2+ consecutive nights:
  → append cumulative-heat-debt flag to morning rancher summary
  → watch for lag-day mortality (day 2–3 after peak is historically highest-risk)

IF animal recumbent on side in shade during peak heat:
  → page rancher Tier 4 immediately; possible heat stroke; vet contact
```

## Escalation / handoff

- **Tier 1 (log)**: THI <72 or mild panting, water adequate.
- **Tier 2 (text)**: THI 72–84, shade/water access uncertain.
- **Tier 3 (call)**: THI >84, open-mouth panting, water tank low.
- **Tier 4 (immediate)**: recumbent animal, score 3–4 panting, consecutive heat-debt nights.
- Vet escalation: heat stroke (recumbent with hyperthermia), any death.

## Sources

- Mader T.L., Davis M.S., Brown-Brandl T. (2006). "Environmental factors influencing heat stress in feedlot cattle." *Journal of Animal Science* 84:712–719.
- St-Pierre N.R., Cobanov B., Schnitkey G. (2003). "Economic losses from heat stress by US livestock industries." *Journal of Dairy Science* 86(E):E52–E77.
- Sanchez-Iborra R. et al. (2023). "IoT-based livestock heat stress monitoring." *Sensors* 23(4).
- USDA-ARS: Livestock Weather Safety Index (THI tables for beef cattle).
- NM State University Extension guide H-612: Managing Range Cattle in Hot, Dry Conditions.
