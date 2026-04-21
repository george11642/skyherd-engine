---
name: heat-stress-disease
description: Load when differentiating pathological heat stress from normal thermoregulation behavior, or when deciding whether observed panting and shade-seeking crosses into a disease/injury threshold requiring medical intervention.
---

# Heat Stress Disease (Pathological Heat Stress)

## When to load

- heat-stress.md has already been loaded and the agent needs to determine if clinical intervention — not just management — is required.
- An animal is showing neurological signs (stumbling, incoordination) during high-heat conditions.
- Panting score has reached 3–4 and the animal is not recovering after moving to shade.

## Summary

Normal heat stress is a physiological response — shade-seeking, reduced feed intake, increased water consumption, elevated respiratory rate — that reverses when ambient conditions improve. Pathological heat stress (heat exhaustion and heat stroke) occurs when core body temperature exceeds 106°F and the thermoregulatory system fails to compensate. Heat stroke is a medical emergency with a mortality rate of 50–80% without rapid intervention. The distinction matters because the agent response shifts from a management advisory (provide shade/water) to an urgent vet call.

## Key facts

- **Normal heat response** (not a disease event): panting score 1–2, shade-seeking, reduced midday grazing, increased water visits. Core temp 101.5–103.5°F.
- **Heat exhaustion**: core temp 104–106°F; animal standing but weak; not eating or drinking despite access; panting score 3; may be unsteady.
- **Heat stroke**: core temp >106°F; neurological signs — incoordination, stupor, recumbency; panting may be severe or paradoxically diminished in terminal phase.
- **Mortality**: heat stroke in cattle is 50–80% fatal without rapid cooling intervention (cold water hosing, shade, IV fluids).
- **Risk factors**: black coat (30% higher solar absorption), obesity/high BCS, pregnancy (3rd trimester), no shade access for 4+ hrs, prior day night THI >65.
- **Thermal camera signature**: hide surface temp >115°F in exposed animal; rectal probe if available (normal 101.5–103.5°F; fever plus heat = additive risk).
- **Distinguishing BRD from heat stroke**: BRD animals have mucopurulent nasal discharge and cough; heat-stroke animals do not. BRD animals are typically not seen in peak heat of day; heat-stroke animals are. Fever in BRD persists after cooling; heat-stroke fever resolves with cooling.
- **Action thresholds** at the disease boundary:
  - Panting score ≥3 AND not recovering after 30 min in shade → heat exhaustion.
  - Recumbency + panting + high ambient temp → heat stroke until proven otherwise.
- **First aid**: move to shade, cold water on neck/head/inner legs, oral electrolytes if animal can swallow, IV fluids for recumbent animals (vet-administered).

## Decision rules

```
IF panting score 1–2 AND shade/water accessible:
  → Normal heat response; cross-reference heat-stress.md management protocols; no vet call

IF panting score 3 AND no improvement after 30 min in shade:
  → Heat exhaustion; Tier 3 call rancher; wet animal down; watch for progression

IF panting score 4 OR recumbency during heat event:
  → Heat stroke; Tier 4 immediate; vet call now; start cold-water cooling while waiting

IF animal standing but incoordinate or head-weaving in heat:
  → Heat stroke prodrome; Tier 4; cool and call vet

IF core temp measured >106°F (ear sensor or rectal):
  → Tier 4; vet emergency; cold water cooling starting now

IF animal recovers in shade within 30 min, panting score drops:
  → Heat exhaustion avoided; Tier 1 log; increase shade/water checks
```

## Escalation / handoff

- **Tier 3**: exhaustion not resolving with shade/water.
- **Tier 4**: heat stroke (recumbency, score 4 panting, neurological signs, temp >106°F).
- Vet escalation: all heat stroke cases; IV fluid access needed for recumbent animals.

## Sources

- Mader T.L., Davis M.S., Brown-Brandl T. (2006). *Journal of Animal Science* 84:712–719.
- Merck Veterinary Manual — Heat Exhaustion and Heat Stroke in Cattle.
- USDA-ARS Livestock Weather Safety Index: thresholds for intervention.
- NM State University Extension H-612: Emergency management of heat-stressed cattle.
