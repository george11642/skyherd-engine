---
name: battery-economics
description: Load when managing drone battery state, calculating return-to-home triggers, estimating remaining flight time, or planning multi-battery swap logistics for extended ranch patrol.
---

# Battery Economics

## When to load

- A drone is mid-mission and an agent needs to decide whether to extend the mission or return home.
- A patrol is being planned and the agent needs to estimate how many batteries are required.
- Weather or workload has changed mid-flight and the agent needs to recalculate RTH trigger.

## Summary

Battery management is the binding constraint on drone patrol coverage. Run out of battery away from base and you lose the aircraft. Push too hard to maximize coverage and you return with 5% charge — fine on a calm day, fatal if a 15 mph headwind develops on the return leg. The 25% reserve rule is the operational floor, not a guideline. Extended ranch patrols require pre-staged battery swaps or a vehicle-based charging point. Understanding the math — distance, speed, altitude, wind, temperature — lets the agent plan missions that complete without incident.

## Key facts

- **Mavic Air 2 nominal flight time**: 34 minutes at sea level, no wind, 25°C.
- **Usable flight time at 25% reserve**: 34 min × 0.75 = **25.5 minutes operational window**.
- **Speed vs. consumption**:
  - 5 m/s cruise: ~30 min usable (ideal conditions).
  - 8 m/s cruise: ~25 min usable.
  - 10 m/s cruise: ~20 min usable (approaching max speed; not recommended for surveillance).
- **Altitude effect**: for every 1,000 ft increase in elevation above sea level, battery life decreases ~3–5%. NM ranches at 4,500–7,000 ft lose 15–25% of sea-level spec.
- **Temperature effect**:
  - 25°C: nominal.
  - 35°C: ~5% reduction.
  - 0°C: ~25–35% reduction. Warm battery to >60°F before cold-weather flight.
  - -10°C: do not fly; permanent cell damage risk.
- **Wind effect**: headwind at 15 mph adds ~20–30% to power consumption. Return leg with tailwind recovers ~15%. Net: plan as if average wind is 50% headwind.
- **RTH altitude**: set 20m above terrain max along return path. Add extra 20m buffer in hilly terrain.
- **RTH triggers** (hard limits):
  - 25% battery: automatic RTH initiated.
  - 15% battery: land immediately (emergency RTH override).
  - Never allow manual override below 20% in field operations.
- **Range calculation** (simple): max range = (usable flight time × speed) / 2. At 25 min usable and 6 m/s: max radius = (25 × 60 × 6) / 2 / 2 ≈ 2,250m = **1.4 miles** from home.
- **Charging time**: DJI Mavic Air 2 standard charger: 0% → 100% in ~80 min. With dual charger: ~60 min. Fast charging not recommended daily (degrades cells over time).
- **Battery cycle life**: rated 200 charge cycles to 80% original capacity. Track cycle count per battery ID.
- **Winter protocol**: store batteries at 50–60% charge if not flying for >1 week. Full charge stored degrades cells.
- **Multi-battery planning**: for a 2-hour ranch patrol with a 2-drone relay, you need 4 batteries minimum (2 flying, 2 charging). Charging point should be positioned centrally on the ranch.

## Decision rules

```
IF current battery < 25%:
  → Initiate RTH immediately; log current GPS before RTH; do not extend mission

IF current battery 25–40% AND mission >2,000m from home:
  → Begin RTH now; remaining mission segment incomplete; log for next patrol

IF current battery 40–60% AND strong headwind detected on return azimuth:
  → Apply 30% wind correction to RTH estimate; if adjusted RTH estimate <25%, return now

IF temperature <0°C and battery capacity seems low:
  → Apply cold-weather correction; assume 30% capacity loss; raise RTH trigger to 40%

IF mission requires >1.4 mile radius at standard params:
  → Multi-battery or vehicle staging needed; do not attempt single-battery long range

IF charging station is unavailable (e.g., power failure at ranch):
  → Reserve 2 batteries fully charged as emergency standby; do not use for routine patrol

IF battery shows >200 charge cycles:
  → Flag for replacement; capacity likely <80% of original; add 10% to all RTH thresholds

IF high-priority reactive dispatch but battery is at 60%:
  → Proceed; calculate RTH threshold before launch; shorten mission accordingly
  → Do NOT cancel a Tier 4 dispatch for battery reasons; launch with what you have
```

## Escalation / handoff

- Battery-related RTH during a Tier 4 event: log final GPS before RTH; page rancher immediately with last known predator/animal GPS; rancher must respond on ground.
- Battery swap coordination: log swap time, cycle count, post-charge level for each battery ID.

## Sources

- DJI Mavic Air 2 official specifications: dji.com/mavic-air-2/specs.
- Stolaroff J.K. et al. (2018). "Energy use and life cycle greenhouse gas emissions of drones." *Nature Communications* 9:409 — altitude and speed energy models.
- FAA Part 107: operational requirements.
- ArduCopter power management documentation: ardupilot.org/copter.
