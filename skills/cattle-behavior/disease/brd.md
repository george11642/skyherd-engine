---
name: brd
description: Load when a drone thermal camera shows elevated head temperature, an animal is head-down with labored breathing, or HerdHealthWatcher detects respiratory abnormality. Covers Bovine Respiratory Disease complex.
---

# Bovine Respiratory Disease (BRD)

## When to load

- Thermal IR camera detects a nasal or ear region temperature spike (>2°F above herd mean).
- Animal shows head-down posture, shallow fast breathing, or is standing apart from herd at peak feeding time.
- HerdHealthWatcher is cross-referencing a multi-signal anomaly (thermal + gait + isolation).

## Summary

BRD is the number-one cause of morbidity and mortality in beef cattle in the US, accounting for 70–80% of all feedlot deaths and significant losses on cow-calf operations (USDA NAHMS 2017). It is a polymicrobial disease — viral infection (*BRSV*, *IBR*, *PI3*, *BVD*) weakens immune defenses, enabling secondary bacterial pneumonia (*Mannheimia haemolytica*, *Pasteurella multocida*, *Histophilus somni*). Stress is the universal precipitant: weaning, shipping, co-mingling, or weather events. Early detection (within 24 hrs of first signs) dramatically improves treatment success.

## Key facts

- **Primary viruses**: BRSV (bovine respiratory syncytial virus), IBR (*BoHV-1*), PI3 virus, BVD.
- **Primary bacteria**: *Mannheimia haemolytica*, *Pasteurella multocida*, *Histophilus somni*.
- **Risk window**: highest 2–45 days after transport, weaning, or co-mingling (the "high-risk period").
- **Clinical signs**:
  - Fever ≥104°F (normal cattle: 101.5–103.5°F).
  - Nasal discharge (clear early; mucopurulent later).
  - Labored or rapid breathing (>50 breaths/min; normal 20–30).
  - Droopy ears; head lowered; eyes partially closed.
  - Separation from herd; reduced feed intake.
  - Cough (most reliable early sign audible on microphone sensor).
- **Thermal IR detection**: nasal plume temperature elevated >2°F vs herd mean; ear temperature (tympanic proxy) elevated. Sanchez-Iborra 2023 reports 78% sensitivity for BRD screening via drone-mounted thermal at 30m altitude.
- **Scoring**: DART (Droopy ears, Abnormal breathing, Runny nose, Temperament change) — 2+ criteria = high suspicion.
- **Mortality without treatment**: 5–20% of untreated cases; drops to <1% with early intervention.
- **Treatment**: tulathromycin (2.5 mg/kg), enrofloxacin, florfenicol, or tilmicosin per label; single-injection options preferred for range cattle.
- **Withdrawal times**: florfenicol 28 days slaughter; tulathromycin 18 days; enrofloxacin 28 days.
- **NM seasonal risk**: fall weaning (Oct–Nov) is the highest-risk period on NM cow-calf operations.

## Decision rules

```
IF thermal ear/nose temp >2°F above herd mean + head-down posture:
  → Tier 2 text rancher; pull animal for temp check; DART score assessment

IF DART score ≥2 OR rectal temp ≥104°F:
  → Tier 3 call rancher; antibiotic treatment today

IF rapid shallow breathing >50/min + no improvement after 24 hrs:
  → Tier 3; second-line antibiotic; vet consultation

IF coughing detected on acoustic sensor + isolation + fever:
  → Confirm BRD; Tier 3; document for withdrawal time tracking

IF >5% of herd shows signs in 7-day window:
  → Outbreak protocol; Tier 3 call; vet herd health consultation; vaccination review

IF animal recumbent with labored breathing:
  → Tier 4 immediate; vet call; supportive care (NSAID, IV fluid)
```

## Escalation / handoff

- **Tier 2**: single animal, early signs only.
- **Tier 3**: DART ≥2, confirmed fever, or multiple animals.
- **Tier 4**: recumbent, septicemia signs, outbreak (>5% of herd).
- All treated animals must have ear tag or record update for withdrawal compliance.

## Sources

- USDA NAHMS Beef 2017. "Health and management practices on U.S. beef cow-calf operations."
- Merck Veterinary Manual — Bovine Respiratory Disease Complex.
- Sanchez-Iborra R. et al. (2023). "IoT-based livestock health monitoring with drone thermal imaging." *Sensors* 23(4).
- Duff G.C., Galyean M.L. (2007). "Recent advances in management of highly stressed beef cattle." *Journal of Animal Science* 85(3):823–840.
- APHIS-VS (2011). "Feedlot 2011 — Cattle health and management." USDA NAHMS.
