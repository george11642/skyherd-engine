---
name: bcs
description: Load when assigning a Body Condition Score to cattle from camera or drone imagery, interpreting BCS trends over time, or deciding whether BCS change warrants a nutritional or health intervention.
---

# Body Condition Score (BCS 1–9)

## When to load

- HerdHealthWatcher needs to evaluate whether an animal has lost or gained significant condition since last scored.
- GrazingOptimizer is evaluating whether current forage quality is maintaining target BCS windows.
- Pre-calving or pre-breeding assessment is in progress.

## Summary

Body Condition Score is a 1–9 scale (1 = emaciated, 9 = obese) used to estimate the energy reserves of a beef cow from visual and tactile assessment of fat deposition over the ribs, spine, and tailhead. On camera or drone imagery, a trained observer can estimate BCS within ±0.5 points at 10–20m distance. Target BCS varies by production stage: thin cows at calving have higher dystocia rates, lower milk production, and are slower to return to estrus. Fat cows at calving have higher rates of difficult birth. The window 5–7 is operationally safe for most production stages.

## Key facts

- **BCS 1** — Emaciated. No fat detectable. Ribs, spine, tailhead, hips sharply protruding. Not survivable long-term without intervention.
- **BCS 2** — Very thin. Ribs individually visible and easily felt with no fat cover. Spine prominent.
- **BCS 3** — Thin. Ribs individually visible. Slight fat cover felt but not visible. Spine still prominent.
- **BCS 4** — Borderline. Ribs not individually visible but felt easily. Spine not prominent.
- **BCS 5** — Moderate (target for most operations). Ribs felt but with slight fat cover. Spine smooth.
- **BCS 6** — Good condition. Ribs covered; require firm pressure to feel. Brisket shows fat deposit.
- **BCS 7** — Good-to-fat. Ribs felt only with firm pressure. Tailhead fat visible.
- **BCS 8** — Fat. Ribs buried in fat; palpation difficult. Brisket very prominent.
- **BCS 9** — Obese. Bone structure barely detectable. Excessive fat over entire body.
- **Target windows by stage**:
  - Calving: 5.0–6.0 (cows below 4 have markedly higher calving difficulty and rebreeding failure).
  - Breeding: 5.5–6.5 (higher conception rates above BCS 5).
  - Mid-gestation: 4.0–5.5 acceptable.
  - Weaning: 4.5–6.0.
- **BCS change rate**: cows gain or lose approximately 0.5 BCS per 30–45 days on improved/reduced nutrition. Rapid change (>0.5 per 2 weeks) indicates unusual stress or illness.
- **Camera/drone scoring**: target dorsal-view pass at 20–30m altitude or lateral view at 15–20m. Ribs, spine, and tailhead fat visible at these distances. Machine vision models trained on labeled ranch imagery achieve ±0.5 BCS accuracy (Basarab et al. 2018 simulation).
- **Economic impact**: each BCS point below 5 at calving reduces calf crop percentage by approximately 6–8% on NM range operations (NMSU Extension AG-454).

## Decision rules

```
IF individual BCS drops >0.5 points in 2-week window:
  → Flag HerdHealthWatcher; check lameness, BRD, water access, social displacement

IF individual BCS <4 approaching calving window (within 30 days):
  → Tier 2 text rancher; supplemental feeding needed; dystocia and rebreeding risk

IF individual BCS <3:
  → Tier 3 call rancher; emergency nutritional support; vet evaluation for underlying disease

IF herd-wide mean BCS drops >0.3 in 3-week window:
  → Forage adequacy issue; cross-reference paddock-rotation.md; Tier 2 text rancher

IF BCS >7 in late-gestation cow:
  → Tier 2 note; fat cow calving risk; monitor closely in calving-signs
```

## Escalation / handoff

- **Tier 2**: individual <4 approaching calving; herd-wide trend decline.
- **Tier 3**: individual <3 at any stage.
- Vet: BCS <2 with concurrent illness; rapid decline despite adequate forage.

## Sources

- Herd, D.B. & Sprott L.R. (1986). "Body condition, nutrition and reproduction of beef cows." Texas A&M Extension B-1526.
- Basarab J.A. et al. (2018). "Automated body condition scoring in beef cattle using deep learning." *Canadian Journal of Animal Science* 98(4).
- NM State University Extension AG-454: Body Condition Scoring for Beef Cows.
- Merck Veterinary Manual — Body Condition Scoring of Beef Cattle.
- USDA NAHMS Beef 2017: nutritional management data.
