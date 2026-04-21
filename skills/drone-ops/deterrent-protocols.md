---
name: deterrent-protocols
description: Load when deciding whether to activate an acoustic deterrent, which frequency band to use for a specific predator, or how long to sustain a deterrent event. No autonomous lethal force under any circumstances.
---

# Deterrent Protocols

## When to load

- FenceLineDispatcher or PredatorPatternLearner has confirmed a predator contact and is deciding on a response.
- A deterrent has been activated and the agent needs to monitor effectiveness and determine when to stop.
- A rancher has asked about deterrent options for a specific predator type.

## Summary

SkyHerd's deterrent toolkit is strictly nonlethal. The primary active deterrent is a drone-mounted directional acoustic emitter capable of outputting species-targeted frequency profiles. Secondary deterrents available in the sim are strobe lighting and proximity overflight. No autonomous physical or lethal intervention is permitted under any circumstances — the platform escalates to the rancher for all situations where lethal force might be considered, which is a legal and regulatory decision for the human landowner. Deterrents are effective at reducing approach probability by 60–80% for coyotes and bears; they are less reliable for wolves and mountain lions.

## Key facts

**Acoustic deterrent frequency bands by predator**:
- **Coyote**: 10–18 kHz range. High-frequency aversive tones mimic distress and threat signals in canid hearing range. Field trials (Shivik et al. 2003) show 70% reduction in approach probability when combined with strobe.
- **Mountain lion**: low-frequency deterrents (200–800 Hz) simulating large predator vocalizations or human voice. High-frequency less effective for felids. Note: lion deterrence from drone is less reliable than coyote; physical deterrence (noise + proximity) more effective.
- **Mexican gray wolf**: 2–6 kHz range. Mid-frequency, similar to human voice range. USFWS nonlethal deterrent guidelines; acoustic + light combination recommended. Note: activating deterrents against a confirmed wolf should be logged with timestamp for USFWS records.
- **Bear**: broad spectrum 1–8 kHz; voice playback (human voice phrases) is most effective; combined with bright strobe.
- **LGDs**: NEVER activate deterrents toward an LGD. Always cross-reference livestock-guardian-dogs.md before activating.

**Duration and escalation**:
- Initial deterrent: 15–30 second burst.
- If predator does not retreat after first burst: repeat at 60-second intervals up to 3 cycles.
- If predator does not retreat after 3 cycles: escalate to Tier 3 rancher call; deterrent is not working.
- Maximum continuous deterrent activation: 5 minutes. Beyond that, the animal habituates and the tool loses effectiveness.

**Effectiveness limitations**:
- Coyotes habituate to repeated deterrents within 3–5 exposures. Rotate tone profiles; log each activation to PredatorPatternLearner to track habituation.
- Mountain lion: may not respond at all to acoustic alone; proximity overflight (<30m) combined with audio is more effective.
- Wolves: ESA protection means deterrence only; under no circumstances should deterrent be interpreted as provocation. USFWS recommends nonlethal deterrents; document all wolf deterrent uses.

**Strobe protocol**:
- Activate only during confirmed approach within 100m of herd.
- 1–4 Hz strobe at 10,000+ lux effective for nocturnal deterrence.
- Do NOT activate strobe toward cattle directly; can cause panic/stampede.
- Aim strobe at the predator's direction; away from herd.

**NO autonomous lethal force**:
- This platform does not and will not carry lethal payloads.
- Any situation where lethal removal is warranted goes to the rancher and appropriate authority.
- For wolves: USFWS depredation management team.
- For mountain lions: NM DGF depredation permit (505-476-8000).
- For coyotes: rancher or USDA-APHIS Wildlife Services.

## Decision rules

```
IF coyote confirmed within 200m of herd:
  → Activate 10–18 kHz burst (15 sec); maintain drone at 60m AGL
  → Monitor for retreat; if no retreat in 90 sec, repeat burst
  → After 3 cycles with no retreat: Tier 3 call rancher

IF mountain lion confirmed within 200m of herd:
  → Tier 3 call rancher immediately (do not wait for deterrent cycles)
  → Activate low-frequency deterrent while waiting for rancher; drone at 90m AGL
  → Proximity overflight at 30m AGL if rancher authorizes

IF wolf confirmed within 200m:
  → Tier 3 call rancher + log event for USFWS records
  → Activate 2–6 kHz deterrent; document activation in USFWS evidence log

IF LGD detected:
  → DO NOT activate any deterrent; cross-reference livestock-guardian-dogs.md

IF predator inside herd perimeter (30m or less):
  → All deterrents active; Tier 4 call rancher now; continuous monitoring
  → Do NOT risk cattle panic with misdirected strobe

IF predator retreats after deterrent:
  → Log success; maintain elevated monitoring for 30 min; predator may return
  → Reduce deterrent frequency to avoid habituation
```

## Escalation / handoff

- Any predator not deterred after 3 cycles: Tier 3 or Tier 4 rancher call.
- All wolf deterrent activations: log for USFWS with GPS, timestamp, species confidence.
- Lethal removal: always human decision, never autonomous.

## Sources

- Shivik J.A., Treves A., Callahan P. (2003). "Nonlethal techniques for managing predation." *Sheep & Goat Research Journal* 18:1–17.
- USFWS Mexican Wolf Recovery Program: nonlethal deterrent recommendations.
- Bomford M. & O'Brien P.H. (1990). "Sonic deterrents in animal damage control." *Wildlife Society Bulletin* 18(4).
- NM Dept of Game and Fish: mountain lion depredation permit process.
- USDA-APHIS Wildlife Services: Livestock Protection — nonlethal tools and practices.
