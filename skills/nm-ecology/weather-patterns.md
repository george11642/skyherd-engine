---
name: weather-patterns
description: Load when evaluating current or forecast weather for its impact on cattle health, drone operability, or ranch operations in New Mexico. Covers monsoon cells, dry-line thunderstorms, dust events, and wind thresholds.
---

# NM Weather Patterns for Ranch and Drone Operations

## When to load

- A weather API alert or sensor data suggests conditions that could affect cattle health or drone flight.
- Drone patrol planning needs to account for wind, visibility, or lightning risk.
- GrazingOptimizer needs to factor a forecast rain event into a rotation decision.
- An unusual weather event (dust storm, flash flood, hard freeze) requires an operational protocol.

## Summary

New Mexico weather is highly variable and locally intense. The state has the highest number of thunderstorm days per year west of the Great Plains, and its summer monsoon produces dangerous afternoon convection with little warning. Understanding the weather patterns that affect ranch operations — monsoon timing, dry-line thunderstorms, haboobs, winter dust — is essential for both cattle management and safe drone operations. The Mavic Air 2's 24 mph (10.7 m/s) wind limit is the hard UAS ground rule; NM regularly exceeds this in afternoon convective outflow.

## Key facts

**Monsoon (July–August)**:
- NM North American Monsoon onset: average July 5–15 in southern NM; July 15–25 in northern NM.
- Mechanism: moisture flows north from Gulf of California and Gulf of Mexico; low-pressure trough over the desert Southwest.
- Precipitation pattern: typically afternoon convective showers, often 0.5–1.5 inch per event; localized; dry before noon.
- Lightning: NM averages 40–60 thunderstorm days/year; peak in July–August. Flash density 10–20 strikes/km²/year in southeast quadrant.
- Drone ground rule: no flights when towering cumulus visible within 20 miles. Typical safe morning window 0700–1300; abort by 1400 in monsoon season.
- Flash flood: arroyo flooding within 30–90 min of upstream rain, even in clear skies overhead. Do not patrol drainage channels during or after monsoon cells.
- Forage impact: each 0.5 inch monsoon rain on a rested paddock produces measurable NDVI increase within 5–7 days.

**Dry-line thunderstorms (May–June, pre-monsoon)**:
- Form along the dry line (boundary between moist Gulf air and dry desert air) typically in eastern NM.
- Less predictable than monsoon; can develop from clear to severe in 60–90 min.
- Hail risk higher in pre-monsoon storms than monsoon cells.
- Drone: watch afternoon sky; if anvil cloud visible, land within 15 min.

**Winter dust storms (January–March)**:
- Caused by high-pressure systems pushing dry, cold air through mountain passes.
- Visibility can drop to <1 mile in minutes; sustained winds 40–70 mph possible.
- Drone: ground all operations when dust storm watch/warning issued; winds exceed Mavic spec.
- Cattle: little direct health impact; but visibility loss means sensor data unreliable; pause active monitoring until dust clears.

**Wind thresholds for Mavic Air 2**:
- Rated max wind resistance: 24 mph (Level 5 Beaufort scale / 10.7 m/s).
- Operational caution at >15 mph sustained (battery drain 20–40% higher; flight time shortened).
- At >20 mph: constrain to low altitude (≤30m AGL) to reduce wind exposure; shorten patrol segments.
- At >24 mph: ground the aircraft.
- NM afternoon convective outflow: winds can jump from 5 mph to 35+ mph in 2–5 minutes; monitor nearest AWOS/ASOS.

**Freeze events**:
- Hard freeze (<28°F for 4+ hrs): November–February; less common in southern NM.
- Float valve freeze risk on above-ground water lines below 28°F.
- Drone battery: capacity drops ~30% at 32°F; ~50% at 14°F. Warm battery to >60°F before flight in winter.
- Calving risk: hypothermia for newborn calves if temps <35°F and wet; load calving-signs.md in advance.

**NM Climate zones relevant to ranch operations**:
- Eastern plains (>3,500 ft): highest thunderstorm frequency; coldest winters.
- Central highlands (5,000–8,000 ft): high monsoon reliability; coolest summers.
- Southern desert (<4,500 ft): hottest summers (THI highest); lowest winter severity; earliest screwworm risk.

## Decision rules

```
IF ASOS/AWOS wind sustained >24 mph:
  → Ground all drones; log; resume at next 15-min wind check

IF towering cumulus visible within 20 miles during monsoon season:
  → Land drone within 10 min; weather abort; resume after storm passes and cells >20 miles

IF flash flood watch in effect for ranch county:
  → Avoid arroyo patrol routes; restrict drone to open terrain; check cattle in low-ground paddocks

IF temperature <28°F at 0600:
  → Check water tank float valves; warm drone battery before pre-dawn patrol
  → If calving season: load calving-signs.md; hypothermia protocol active

IF dust storm warning issued:
  → Ground all drones; flag sensor data as unreliable until dust clears
  → Cattle health check deferred until visibility >3 miles

IF rain forecast >0.75 inch in 48 hrs on a rested paddock:
  → Flag to GrazingOptimizer: NDVI improvement expected in 5–7 days; early rotation may be possible

IF winter night temp <20°F with no pre-warm drone action:
  → Drone battery may be at 50% capacity; shorten patrol duration; RTH at 30% remaining
```

## Escalation / handoff

- Weather-driven groundings: **log + notify RPIC** (no rancher page unless livestock are at risk).
- Flash flood with cattle in arroyo paddock: **Tier 3** — confirm animal positions and recommend paddock move.
- Extreme heat (THI >88): hand off to heat-stress.md protocol.

## Sources

- NM Climate Center: nmclimate.nmsu.edu — historical normals, drought tracking.
- NWS Albuquerque: weather.gov/abq — ASOS/AWOS station data.
- NOAA: North American Monsoon System — tropical/extratropical interaction.
- DJI Mavic Air 2 specifications: max wind resistance 24 mph (10.7 m/s).
- Renard K.G. et al. (1997). *Predicting Soil Erosion by Water* (RUSLE), USDA ARS Handbook 703 — NM rainfall erosivity data.
