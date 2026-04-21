---
name: seasonal-calendar
description: Load to orient any agent to the NM ranch seasonal calendar — what is happening on the land and with the cattle in a given month, and which monitoring priorities shift with the season.
---

# NM Ranch Seasonal Calendar

## When to load

- An agent is initializing and needs context about what livestock management phase the operation is in.
- CalvingWatch, GrazingOptimizer, or HerdHealthWatcher is determining which disease/behavioral risks are elevated right now.
- A new weather event or calendar date triggers a seasonal protocol review.

## Summary

NM cow-calf operations run on a spring-calving, fall-weaning cycle. The year has five distinct management phases, each with different monitoring priorities, dominant risks, and drone tasking emphasis. CalvingWatch's active window (March–April), the monsoon's forage implications (July–August), and fall weaning stress (October–November) drive the biggest workload spikes in any given year. An agent that knows what month it is can pre-load the right skills and anticipate the rancher's concerns before being asked.

## Key facts

**January–February — Late gestation / Pre-calving prep**:
- Cows in last trimester; nutritional needs at peak.
- BCS monitoring critical; cows below 4.5 need supplemental feed now.
- Fence check before calving season (fix now, not during calving rush).
- Pasture rest from previous fall; no cattle movement; let grass recover.
- Drone weather holds common: winter dust storms Jan–Feb; check weather-patterns.md.
- Predator risk: mountain lion active in lower elevation desert margins as deer concentrate.

**March–April — Calving season**:
- CalvingWatch goes to full active monitoring.
- 80–90% of NM spring calves born these two months.
- Primary risks: dystocia, hypothermia (NM nights still 20–35°F), navel infection, coyote predation on newborns.
- Drone priority: visual monitoring of calving pen, dam-calf bonding confirmation.
- Personnel constraint: rancher is most time-pressed; minimize non-critical alerts.

**May–June — Pre-monsoon dry season**:
- Driest months of the year; native grasses dormant or slow.
- Water tank management critical; evaporation high; solar pump demand peaks.
- Heat stress begins building by late May in southern NM.
- Coyote pup season (May–June); pup-rearing adults are more aggressive toward livestock.
- Branding, castration, vaccination typically occur April–May; wound management (screwworm risk on open wounds in southern NM).
- THI begins to cross 72 threshold regularly by June.

**July–August — Monsoon season**:
- Monsoon arrives mid-July on average; widespread by late July.
- Primary forage production window; NDVI spikes within 7–14 days of first good rains.
- GrazingOptimizer active: adjust rotation schedule to take advantage of forage flush.
- Heat stress peak: RH rises with monsoon; THI can reach 84–90 even at 90°F ambient.
- Lightning risk to drone operations; afternoon thunderstorms nearly daily.
- Flash flood risk in arroyos; do not patrol drainage channels in storm conditions.
- Pinkeye season peak (face fly peak); HerdHealthWatcher ocular monitoring elevated.

**September–October — Post-monsoon / Fall transition**:
- Grasses curing; quality high protein content until December.
- Weaning of spring calves (October–November); BRD risk window opens immediately post-weaning.
- BRD monitoring goes to elevated priority for 45 days post-wean.
- Fall AI/natural breeding season may be active; bull management relevant.
- Screwworm risk begins dropping as temperatures cool.
- Mountain lion activity increases as elk rut draws deer/elk movement near ranches.

**November–December — Weaning completion / Pregnancy checking / Winter prep**:
- Preg-check herd; open cows are culled.
- Water pipe insulation before hard freeze.
- Fence repair before winter.
- Drone maintenance window: inspect batteries for cold-weather capacity loss.
- BCS assessment for the coming calving season; supplement marginal cows now.

## Decision rules

```
IF month is March–April:
  → CalvingWatch active; load calving-signs.md; dystocia and hypothermia protocols ready
  → Minimize non-critical Tier 2 alerts to rancher; calving is the priority

IF month is July–August:
  → Heat stress monitoring elevated; load heat-stress.md; THI check each morning
  → Pinkeye surveillance elevated; drone ocular detection priority
  → Afternoon drone grounding protocol (lightning); no flights 1400–1800 typical storm window

IF month is October–November:
  → BRD monitoring elevated for 45 days post-wean; load brd.md
  → Coyote pup dispersal: younger coyotes exploring new territory; increase fence-line patrol frequency

IF month is December–February:
  → Water freeze protection active; tank float valve check daily if temp <28°F
  → Drone cold-weather battery protocol (battery capacity drops ~30% below 32°F)
```

## Escalation / handoff

- Seasonal context modifies tier thresholds for all other agents; this skill is a context loader, not a primary escalation tool.
- When a new month begins, GrazingOptimizer and CalvingWatch should receive a season-change signal with updated priority list.

## Sources

- NMSU Extension AG-413: Calving Management for NM Beef Operations.
- USDA NAHMS Beef 2017: production calendar practices.
- NM Climate Center: historical temperature and precipitation normals (nmclimate.nmsu.edu).
- Holechek J.L. et al. (2011). *Range Management*, 6th ed. Pearson.
- NM Livestock Board: seasonal operation calendar guidance.
