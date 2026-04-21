---
name: pinkeye
description: Load when a vision-agent flags ocular cloudiness, discharge, or squinting in cattle footage, or when evaluating whether an ocular finding requires vet attention. Covers Infectious Bovine Keratoconjunctivitis (IBK).
---

# Pinkeye (IBK — Infectious Bovine Keratoconjunctivitis)

## When to load

- Camera or drone footage shows a cow with one or both eyes partially closed, watery, or showing white corneal opacity.
- HerdHealthWatcher is cross-referencing an ocular detection with a disease head classifier result.

## Summary

Pinkeye is the most common ocular disease of cattle in the US, caused primarily by *Moraxella bovis* (gram-negative rod). It peaks June–August in NM — flies (*Musca autumnalis*, face fly) are the primary vector. Ultraviolet light intensity and tall grass seed contact are cofactors. If untreated, corneal ulceration can lead to permanent blindness. Early detection and isolation are the two most cost-effective interventions.

## Key facts

- **Causative agent**: *Moraxella bovis* (primary); *Moraxella bovoculi* increasingly implicated.
- **Vector**: face fly (*Musca autumnalis*) mechanical transmission; peaks in summer pasture, correlates with fly season.
- **Seasonal peak**: June–August in NM; incidence falls sharply after first frost.
- **Clinical progression**:
  - Day 1–2: excessive tearing (epiphora), blepharospasm (squinting), photophobia (seeks shade).
  - Day 3–5: central corneal ulcer visible; white/gray opacity developing.
  - Day 6–10: ulcer deepens; vascularization (pink ring) around ulcer edge.
  - Day 10+: without treatment, perforation risk; with treatment, healing usually within 14–21 days.
- **Bilateral cases**: 20–30% of affected animals develop bilateral involvement.
- **Transmission**: direct contact and fly-mediated; affects calves and yearlings more severely than mature cows.
- **Visual detection cues** (camera/drone): head tilted toward affected eye, reluctance to graze in bright sun, excessive ocular secretion visible as dark stain down face.
- **BCS impact**: blind or severely affected animals cannot graze efficiently; BCS may drop 0.5–1 point in 2–3 weeks without feed assistance.

## Decision rules

```
IF unilateral tearing without opacity:
  → Tier 1 log; recheck 48 hrs; early IBK or minor irritation

IF central corneal opacity visible:
  → Tier 2 text rancher; antibiotic treatment within 24 hrs improves outcome
  → Recommend isolation from direct sun; fly control

IF bilateral opacity OR deep ulcer visible:
  → Tier 3 call rancher; vet evaluation recommended; blindness risk
  → Flag for feed assistance if BCS concern

IF >3 animals in same pasture affected within 7 days:
  → Tier 3; herd-level outbreak; fly control intervention needed

IF perforation suspected (globe rupture, prolapsed iris):
  → Tier 4; vet emergency call
```

## Escalation / handoff

- Treatment: 200 mg oxytetracycline LA IM, or subconjunctival penicillin injection (vet-administered). Patch affected eye to reduce UV exposure.
- Vet escalation: bilateral cases, perforated globe, unresponsive after 5 days of treatment.

## Sources

- Merck Veterinary Manual, 12th ed. — Infectious Bovine Keratoconjunctivitis.
- USDA APHIS Veterinary Biologics: IBK fact sheet.
- Angelos J.A. (2015). "Infectious bovine keratoconjunctivitis." *Veterinary Clinics of North America: Food Animal Practice* 31(1).
- NM Livestock Board: reportable disease list (IBK not reportable; for reference only).
