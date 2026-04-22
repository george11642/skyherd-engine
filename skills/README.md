# Skills Library

SkyHerd's domain knowledge lives here as 33 Markdown files — not in agent system prompts. Each file is loaded at wake time as a `cache_control: {"type": "ephemeral"}` block, so the stable knowledge is cached and only the volatile event payload is billed at full token rate.

This is the same pattern Mike Brown used to win $50k at the Opus 4.6 hackathon (CrossBeam, 28+ reference files). We extended it to New Mexico ranch domain: cattle disease signs, predator thermal signatures, acoustic deterrence, drone regulations, and the "Wes" voice register.

---

## Inventory

| Subdir | File | Purpose |
|--------|------|---------|
| `cattle-behavior/` | [`feeding-patterns.md`](cattle-behavior/feeding-patterns.md) | Normal trough visit frequency, time-at-trough norms, signs that feeding behavior is off |
| `cattle-behavior/` | [`lameness-indicators.md`](cattle-behavior/lameness-indicators.md) | Gait asymmetry scoring, weight-shift patterns, toe-dragging flags for camera-based detection |
| `cattle-behavior/` | [`calving-signs.md`](cattle-behavior/calving-signs.md) | Pre-labor behavioral sequence, timing windows, dystocia escalation criteria |
| `cattle-behavior/` | [`heat-stress.md`](cattle-behavior/heat-stress.md) | Open-mouth breathing, bunching patterns, THI thresholds for NM summer conditions |
| `cattle-behavior/` | [`herd-structure.md`](cattle-behavior/herd-structure.md) | Dominance hierarchies, isolation as early-illness signal, normal vs. pathological separation |
| `cattle-behavior/disease/` | [`pinkeye.md`](cattle-behavior/disease/pinkeye.md) | IBK corneal opacity staging, ocular discharge, photophobia detection via head position |
| `cattle-behavior/disease/` | [`screwworm.md`](cattle-behavior/disease/screwworm.md) | New World Screwworm wound inspection, 2026-active USDA-APHIS northward-spread alert |
| `cattle-behavior/disease/` | [`foot-rot.md`](cattle-behavior/disease/foot-rot.md) | Interdigital swelling visual cues, gait scoring for early foot-rot vs. general lameness |
| `cattle-behavior/disease/` | [`brd.md`](cattle-behavior/disease/brd.md) | Bovine Respiratory Disease: head-down posture, abnormal respiration on thermal IR |
| `cattle-behavior/disease/` | [`lsd.md`](cattle-behavior/disease/lsd.md) | Lumpy Skin Disease nodule detection; emerging Western Hemisphere threat since 2023 |
| `cattle-behavior/disease/` | [`heat-stress-disease.md`](cattle-behavior/disease/heat-stress-disease.md) | Heat stress as a disease endpoint: panting score, drool, treatment thresholds |
| `cattle-behavior/disease/` | [`bcs.md`](cattle-behavior/disease/bcs.md) | Body Condition Score 1–9: visual and camera-based scoring criteria, intervention cutoffs |
| `predator-ids/` | [`coyote.md`](predator-ids/coyote.md) | Canid gait signature, thermal body mass, hunting patterns near NM ranch fence lines |
| `predator-ids/` | [`mountain-lion.md`](predator-ids/mountain-lion.md) | Felid thermal signature, ambush approach geometry, confirmed kill indicators |
| `predator-ids/` | [`wolf.md`](predator-ids/wolf.md) | Mexican Gray Wolf reintroduction range, pack behavior, reporting obligations under ESA |
| `predator-ids/` | [`livestock-guardian-dogs.md`](predator-ids/livestock-guardian-dogs.md) | LGD thermal signature to avoid false-positive deterrence on working ranch dogs |
| `predator-ids/` | [`thermal-signatures.md`](predator-ids/thermal-signatures.md) | Species-by-species thermal body-heat profiles for drone FLIR classification |
| `ranch-ops/` | [`fence-line-protocols.md`](ranch-ops/fence-line-protocols.md) | Breach response tiers, documentation requirements, escalation to law enforcement |
| `ranch-ops/` | [`water-tank-sops.md`](ranch-ops/water-tank-sops.md) | Tank-failure response checklist, sensor alert thresholds, manual override procedures |
| `ranch-ops/` | [`paddock-rotation.md`](ranch-ops/paddock-rotation.md) | Grazing pressure targets, rest-period minimums, soil-recovery logic for NM range conditions |
| `ranch-ops/` | [`part-107-rules.md`](ranch-ops/part-107-rules.md) | FAA Part 107 operating limits, waiver types, §44807 exemption criteria for BVLOS ops |
| `ranch-ops/` | [`human-in-loop-etiquette.md`](ranch-ops/human-in-loop-etiquette.md) | When to page vs. log, urgency tier definitions, rancher fatigue and false-positive tolerance |
| `nm-ecology/` | [`nm-predator-ranges.md`](nm-ecology/nm-predator-ranges.md) | Coyote, mountain lion, and Mexican Gray Wolf territory maps for NM ranch counties |
| `nm-ecology/` | [`nm-forage.md`](nm-ecology/nm-forage.md) | Blue grama, sacaton, and native grass productivity by range condition class in NM |
| `nm-ecology/` | [`seasonal-calendar.md`](nm-ecology/seasonal-calendar.md) | NM ranch calendar: calving window, branding, weaning, shipping, breeding, winterization |
| `nm-ecology/` | [`weather-patterns.md`](nm-ecology/weather-patterns.md) | NM monsoon onset, spring wind ceiling (27 kt sustained grounds Dock 3 15–20% of days), freeze risk |
| `drone-ops/` | [`patrol-planning.md`](drone-ops/patrol-planning.md) | Waypoint density, altitude trade-offs, battery economics for a ranch-scale patrol grid |
| `drone-ops/` | [`deterrent-protocols.md`](drone-ops/deterrent-protocols.md) | Acoustic deterrence frequency ranges (8–18 kHz), graduated response sequence, no-lethal-force rule |
| `drone-ops/` | [`battery-economics.md`](drone-ops/battery-economics.md) | Flight time vs. payload, charge cycle planning, Dock 3 turnaround time per patrol type |
| `drone-ops/` | [`no-fly-zones.md`](drone-ops/no-fly-zones.md) | Class G airspace confirmation, federal-land overflight restrictions, neighbor notification |
| `voice-persona/` | [`wes-register.md`](voice-persona/wes-register.md) | "Wes" voice persona: laconic cowboy register, sentence length, vocabulary constraints |
| `voice-persona/` | [`urgency-tiers.md`](voice-persona/urgency-tiers.md) | SMS vs. voice call decision rules; `urgency` parameter values for `page_rancher()` |
| `voice-persona/` | [`never-panic.md`](voice-persona/never-panic.md) | Calm-first communication rule: no alarm language until the rancher asks a follow-up |

---

Each agent loads only the skills its current task needs — see `src/skyherd/agents/*.py` for wake-to-skill mappings.
