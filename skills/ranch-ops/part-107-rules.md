---
name: part-107-rules
description: Load when planning a drone flight, assessing legality of a proposed mission, or determining whether a specific operation requires a waiver. Covers FAA Part 107 rules applicable to ranch UAS operations in New Mexico.
---

# FAA Part 107 Rules for Ranch UAS Operations

## When to load

- Patrol-planning agent is composing a new mission and needs to confirm regulatory constraints.
- A proposed flight is near controlled airspace, a national park, or tribal land.
- The agent is deciding whether BVLOS (Beyond Visual Line of Sight) operations are permissible.

## Summary

FAA Part 107 governs small UAS (under 55 lbs) operations for commercial purposes in the US. Ranch surveillance and livestock management qualify as commercial operations. The Remote Pilot in Command (RPIC) must hold a Part 107 certificate. Key operational limits: 400 ft AGL, visual line of sight, daylight, yielding to manned aircraft. BVLOS operations require a specific FAA waiver (Form 7711-65). SkyHerd's sim-first architecture operates under Part 107 constraints as the legal baseline for all planned real-world flight.

## Key facts

- **Altitude limit**: 400 ft AGL (above ground level). Exception: within 400 ft of a structure, can fly up to 400 ft above the structure's highest point.
- **Typical ranch patrol altitude**: 60–100m AGL (200–330 ft). Well within 400 ft limit.
- **Airspeed**: max 100 mph (87 knots).
- **Visual line of sight (VLOS)**: RPIC must be able to see the drone at all times without visual aids (binoculars not permitted). This limits effective patrol range to ~1,500–3,000 ft in practice.
- **BVLOS**: prohibited without an FAA waiver. FAA BVLOS waivers under the Beyond Visual Line of Sight Aviation Rulemaking Committee (BVLOS ARC) framework require demonstrated system safety and risk mitigation. As of Apr 2026, waivers are being granted on a case-by-case basis; approval time is typically 90–180 days.
- **Nighttime operations**: legal under Part 107 with anti-collision lights visible from 3 statute miles. Critical for predator patrol.
- **Operations over people**: permitted if drone weighs <0.55 lbs (Category 1) or meets Category 2/3 safety standards. Mavic Air 2 is Category 3 capable with guard; most ranch drones require avoiding sustained flight over uninvolved people.
- **Controlled airspace**: operations in Class B/C/D/E surface airspace require LAANC authorization or FAA Drone Zone approval. NM ranch operations are typically Class G (uncontrolled) airspace.
- **National parks and monuments**: overflights prohibited without NPS permit. Chaco Culture NHP (San Juan County, NM) and Bandelier NM (Los Alamos/Sandoval County) are hard no-fly zones.
- **Tribal lands**: sovereign nations; FAA rules still apply to airspace but additional tribal permission may be required for takeoff/landing on tribal land. Contact tribe's range management office.
- **Aircraft registration**: any drone over 0.55 lbs must be registered with FAA. Registration mark (FAA-XXXXXXXX) must be visible on exterior.
- **Waivers applicable to ranch operations**:
  - BVLOS: for long-range paddock and fence patrol.
  - Night operations over people: rarely applicable on remote ranch.
  - Operations from moving vehicle: applicable to truck-mounted drone deployment.

## Decision rules

```
IF proposed flight is within Class G airspace AND below 400 ft AGL AND daytime AND VLOS:
  → Standard Part 107; legal; proceed

IF proposed flight is at night:
  → Legal under Part 107; confirm anti-collision lights on drone; log RPIC on duty

IF proposed flight requires BVLOS (patrol >1,500 ft from RPIC):
  → Requires active FAA BVLOS waiver; check waiver status before mission
  → If no waiver: constrain to VLOS range; RPIC must reposition as drone advances

IF proposed flight is over Chaco Culture NHP or Bandelier NM:
  → PROHIBITED; reroute mission; no exception

IF proposed flight is within 5 miles of an airport:
  → Check LAANC authorization via Kittyhawk, Aloft, or FAA DroneZone before launch

IF proposed flight altitude >400 ft AGL (non-structure):
  → PROHIBITED under standard Part 107; return to ≤400 ft or obtain waiver

IF wind >24 mph (Mavic Air 2 wind resistance spec):
  → Do not fly; aircraft handling compromised; see battery-economics.md and weather-patterns.md

IF drone is over tribal land (not airspace — actual land boundary for T/O and landing):
  → Confirm tribal permission; FAA airspace rules still govern flight above
```

## Escalation / handoff

- **Log only**: all flights in Class G <400 ft, VLOS confirmed.
- **Tier 2 text rancher**: BVLOS waiver needed, weather marginal, non-standard airspace.
- **Abort and log**: any flight over restricted zone (Chaco, Bandelier, Class B without LAANC).
- RPIC must be notified of any non-routine airspace situation.

## Sources

- FAA 14 CFR Part 107: Small Unmanned Aircraft Systems.
- FAA LAANC: Low Altitude Authorization and Notification Capability.
- FAA Drone Zone: faadronezone.faa.gov.
- NPS UAS Policy: nps.gov/subjects/aviation/uas.htm.
- FAA BVLOS ARC Final Report, 2022.
- DJI Mavic Air 2 specifications: max wind resistance 24 mph (10.7 m/s, Level 5).
