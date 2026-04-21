---
name: water-tank-sops
description: Load when a water level sensor shows low fill, a float valve failure is suspected, or cattle behavior suggests water access failure. Covers standard operating procedures for range water tank monitoring and response.
---

# Water Tank SOPs

## When to load

- A LoRaWAN water level sensor drops below a threshold.
- HerdHealthWatcher has flagged herd-wide suppression of trough visits (possible water failure).
- Drone patrol is performing a water infrastructure check pass.

## Summary

Water is the most critical single input for cattle survival on NM range. An adult cow needs 15–35 gallons per day in summer; that demand doubles above 90°F. On NM ranches, water typically arrives via one of three sources: solar-powered pump from a well, gravity-fed pipeline from a windmill/storage tank, or hauled water in portable tanks. Each failure mode is different. A tank that runs dry for 12 hours in July can trigger heat stress mortality in vulnerable animals; an undetected failure overnight is a Tier 3 event.

## Key facts

- **Daily water demand per 1,000 lb cow**:
  - Below 80°F: 15–20 gallons/day.
  - 80–90°F: 20–25 gallons/day.
  - Above 90°F: 25–35 gallons/day.
  - Lactating cows add 30–50% above baseline.
- **Tank types on NM operations**:
  - Earthen stock ponds (tanks): most common on large ranches; solar-powered pump backup or gravity. Algae, seepage, and evaporation are failure modes.
  - Metal/poly round tanks (300–1,500 gal): direct pump or gravity fill. Float valve failure is the most common issue.
  - Concrete water troughs: high durability; freeze cracking in winter.
- **Level thresholds** (operational triggers):
  - >60% full: normal; no action.
  - 40–60%: watch; refill expected within 24 hrs if normal fill rate holds.
  - 20–40%: low; check fill rate immediately; alert if fill rate below average.
  - <20%: critical; Tier 3; cattle may be rationing water already.
  - 0% (dry): Tier 4; emergency.
- **Flow rate monitoring**: normal fill rate for a 1,000 gal tank via solar pump is 1–3 gal/min depending on pump spec. If current level is declining despite pump active = leak or demand spike.
- **Float valve failure**: most common failure mode. Float stuck open = overflow and waste. Float stuck closed = tank not refilling. Either requires rancher manual check.
- **Solar pump failure**: most common July–August when demand is highest and dust coats panels. If solar irradiance sensor shows adequate sun but pump output is zero = panel cleaning or pump fault.
- **Algae bloom**: earthen tanks in summer can develop algae toxicity (cyanobacteria/blue-green algae). Cattle refuse to drink visibly green/blue-green water; apparent water refusal with full tank = check for algae.
- **Freeze risk**: NM winter nights below 20°F can freeze float valves and above-ground pipes. Wrap or drain above-ground sections before first hard freeze.
- **Distance to nearest backup**: ranch operations plan should list nearest backup water source (neighboring windmill, county road trough) for each paddock.

## Decision rules

```
IF tank level >40% AND fill rate normal:
  → Log; no action

IF tank level 20–40% AND fill rate below normal:
  → Tier 2 text rancher; check pump output; estimated time to dry = level / (demand - fill rate)

IF tank level <20%:
  → Tier 3 call rancher; pump check needed today; calculate hours to dry; move cattle if needed

IF tank level = 0% (dry sensor or drone visual shows empty):
  → Tier 4 immediate; cattle without water in summer = emergency
  → Dispatch drone to confirm; page rancher immediately with GPS of affected tank
  → Recommend moving herd to nearest backup water within 2 hrs

IF fill rate is positive but level still declining:
  → Leak suspected; drone low-pass to inspect base of tank and surrounding ground
  → Tier 3 call rancher

IF full tank but cattle trough visits near zero for 4+ hrs:
  → Check for algae bloom (drone visual — green/blue-green discoloration)
  → Check for float overflow (water overflowing tank edge)
  → Tier 2 text rancher

IF solar irradiance adequate but pump output zero:
  → Solar pump fault; Tier 2; panel cleaning or controller check

IF winter temp <20°F and tank level dropping abnormally fast:
  → Float valve freeze possible; Tier 2; insulation or heat tape needed
```

## Escalation / handoff

- **Tier 1 (log)**: level >40%, normal fill, no behavior anomaly.
- **Tier 2 (text)**: level 20–40%, pump fault, algae concern.
- **Tier 3 (call)**: level <20%, declining fill rate, confirmed pump failure.
- **Tier 4 (immediate)**: dry tank in summer; cattle health at risk within hours.

## Sources

- NM Office of the State Engineer: water rights and stock pond regulations.
- USDA NRCS NM: Range water development guide (Technical Note NM-181).
- NMSU Extension AG-616: Water Management for Range Livestock in New Mexico.
- Merck Veterinary Manual: Water requirements of beef cattle.
- USDA NAHMS Beef 2017: water source and management practices.
