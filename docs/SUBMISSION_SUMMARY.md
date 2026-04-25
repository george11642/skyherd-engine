# Submission Summary — paste-ready for Devpost / cerebralvalley

> 167 words. Aligned to judging weights: Impact 30 / Demo 25 / Opus 4.7 Use 25 / Depth & Execution 20. See `docs/HACKATHON.md` for the full brief.
>
> Drafted: 2026-04-24. Update this file (don't fork) if the wording changes — keep one canonical version.

---

## Summary (paste this block)

SkyHerd Engine is a 5-layer nervous system for American ranches: a reproducible ranch scenario harness and 5-agent Claude Managed Agents mesh that sees, decides, and pages a rancher in under a minute. The 3-minute demo runs five deterministic scenarios — coyote at fence, sick cow, water-tank pressure drop, calving labor, storm redirect — each ending in a Wes-voice phone call and an Ed25519-signed attestation row. `make demo SEED=42 SCENARIO=all` is byte-identical across replays, so any judge can clone the repo and get the same pixels.

Every agent runs on Opus 4.7 with the `managed-agents-2026-04-01` beta header, ephemeral prompt caching pinned to the system + skills prefix, and a 33-file Skills-first knowledge library (CrossBeam pattern). 1,106 tests / 87% coverage. Ranching is the work that takes weeks and should take hours — herd checks, predator response, calving watch, and vet hand-offs are still done by gut and binoculars. SkyHerd makes that work observable, accountable, and never panicked. MIT throughout. Pi + Galileo + Mavic runbooks shipped in-repo for Year-2 field deployment.

---

## Why this hits each criterion

| Weight | Criterion | How the summary scores |
|-------:|-----------|------------------------|
| **30%** | **Impact** | Mirrors "Build From What You Know" verbatim ("the work that takes weeks and should take hours"); concrete user (American ranchers); concrete benefit (observable, accountable, never panicked) |
| **25%** | **Demo** | Names all five scenarios + payoff (Wes call + attestation row); reproducibility hook (`make demo SEED=42` byte-identical) |
| **25%** | **Opus 4.7 Use** | Managed Agents mesh + `managed-agents-2026-04-01` beta header + ephemeral prompt caching + 33-file Skills-first library — four creative axes named |
| **20%** | **Depth & Execution** | 1,106 tests / 87% coverage; byte determinism; Ed25519 attestation chain; MIT discipline (no AGPL); Year-2 hardware-ready signal |

## Variants

If a judge asks for a tighter pitch, use this 50-word elevator:

> SkyHerd Engine is a 5-agent Claude Managed Agents mesh for American ranches: it watches the fence, the herd, the water tanks, and the weather, then makes the call to the rancher. Five deterministic scenarios; byte-identical replays; Ed25519-attested decisions. Built on Opus 4.7. MIT throughout.
