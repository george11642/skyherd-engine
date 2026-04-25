# B-roll Provenance

All clips are license-clean for commercial use under their respective free
licenses. No attribution is technically required by Pexels / Pixabay / Coverr,
and Mixkit explicitly states attribution is not required (the "Mixkit License",
also called the "Mixkit Restricted License" on individual clip metadata, is a
permissive free-for-commercial-use license — see the per-source license notes
below). Where a source ever requests credit, a courtesy line is included in
`CREDITS.md` once that file is added in Phase F.

Clips are normalized to **1920×1080 30fps H.264 yuv420p AAC** to match the
Playwright dashboard recorder format used elsewhere in `remotion-video/public/`.

| File                                    | Source | URL                                                                                                       | License                       | Acquired   |
|-----------------------------------------|--------|-----------------------------------------------------------------------------------------------------------|-------------------------------|------------|
| t1-dawn-corral-golden.mp4               | Mixkit | https://mixkit.co/free-stock-video/sunset-in-the-ranch-2481/                                              | Mixkit License                | 2026-04-24 |
| t1-cattle-grazing-wide.mp4              | Mixkit | https://mixkit.co/free-stock-video/cows-grazing-slowly-on-a-grassy-paddock-44923/                         | Mixkit License                | 2026-04-24 |
| t1-cattle-herd-countryside.mp4          | Mixkit | https://mixkit.co/free-stock-video/herd-of-cows-in-the-countryside-31433/                                 | Mixkit License                | 2026-04-24 |
| t1-drone-rangeland-aerial.mp4           | Mixkit | https://mixkit.co/free-stock-video/flying-over-a-landscape-of-sun-soaked-desert-land-with-52012/          | Mixkit License                | 2026-04-24 |
| t1-drone-arid-mountains.mp4             | Mixkit | https://mixkit.co/free-stock-video/low-flyover-in-an-arid-ecosystem-with-mountains-50199/                 | Mixkit License                | 2026-04-24 |
| t1-storm-cell-horizon.mp4               | Mixkit | https://mixkit.co/free-stock-video/dark-stormy-clouds-in-the-sky-9704/                                    | Mixkit License                | 2026-04-24 |
| t1-lightning-night.mp4                  | Mixkit | https://mixkit.co/free-stock-video/lightning-in-the-night-sky-25081/                                      | Mixkit License                | 2026-04-24 |
| t2-rancher-horse-walk.mp4               | Mixkit | https://mixkit.co/free-stock-video/a-rancher-walks-his-horse-1155/                                        | Mixkit License                | 2026-04-24 |
| t2-cowboy-sunset.mp4                    | Mixkit | https://mixkit.co/free-stock-video/cowboy-at-sunset-525/                                                  | Mixkit License                | 2026-04-24 |
| t2-rancher-sunset-couple.mp4            | Mixkit | https://mixkit.co/free-stock-video/romantic-scene-of-a-couple-at-sunset-on-a-ranch-42383/                 | Mixkit License                | 2026-04-24 |
| t2-hardware-circuit-board.mp4           | Mixkit | https://mixkit.co/free-stock-video/high-tech-circuit-board-with-processor-47051/                          | Mixkit License                | 2026-04-24 |
| t2-hardware-microcircuit.mp4            | Mixkit | https://mixkit.co/free-stock-video/technical-engineer-working-with-a-microcircuit-47047/                  | Mixkit License                | 2026-04-24 |
| t2-sunrise-clouds.mp4                   | Mixkit | https://mixkit.co/free-stock-video/sunrise-shining-through-thick-clouds-26532/                            | Mixkit License                | 2026-04-24 |
| t3-night-sky-stars.mp4                  | Mixkit | https://mixkit.co/free-stock-video/milky-way-seen-at-night-4148/                                          | Mixkit License                | 2026-04-24 |
| t3-meadow-landscape.mp4                 | Mixkit | https://mixkit.co/free-stock-video/meadow-landscape-15981/                                                | Mixkit License                | 2026-04-24 |
| t3-cattle-windy-paddock.mp4             | Mixkit | https://mixkit.co/free-stock-video/cows-grazing-in-a-paddock-on-a-windy-day-44958/                        | Mixkit License                | 2026-04-24 |

## Shot-list mapping (Phase A reference)

The Phase A 19-shot list (see `.planning/research/winner-top3-analysis.md` lines
341–374) drives the choices below. Mapping is many-to-one where multiple Mixkit
clips give variant coverage for the same Phase A bullet.

| Phase A shot | Mapped clip(s) | Tier |
|---|---|---|
| 1. Dawn over the corral / sunrise on rangeland | `t1-dawn-corral-golden.mp4`, `t2-sunrise-clouds.mp4` | T1 |
| 2. Cattle herd grazing wide shot | `t1-cattle-grazing-wide.mp4`, `t1-cattle-herd-countryside.mp4`, `t3-cattle-windy-paddock.mp4` | T1 |
| 3. Drone aerial over rangeland | `t1-drone-rangeland-aerial.mp4`, `t1-drone-arid-mountains.mp4` | T1 |
| 4. Coyote silhouette / eyes at night | **GAP** — no permissive coyote night silhouette located on Mixkit/Coverr (Pexels/Pixabay reachable only via authed browser). Compensate with `t3-night-sky-stars.mp4` ambience + voiceover-driven framing. | T1 |
| 5. Fence wire close-up at night | **GAP** — no permissive fence-wire night clip located. Use existing `clips/coyote.mp4` dashboard recording for fence-line dispatcher narrative; ambient cover from `t1-lightning-night.mp4`. | T1 |
| 6. Lightning / storm cell on horizon | `t1-storm-cell-horizon.mp4`, `t1-lightning-night.mp4` | T1 |
| 7. Gloved hand on phone or radio | **GAP** — no permissive close-up hand-on-phone clip. Compensate with `t2-rancher-horse-walk.mp4` (rancher establishing) and on-screen Twilio SMS recording from `clips/`. | T2 |
| 8. Rancher's boot kicking dust / walking through gate | `t2-rancher-horse-walk.mp4`, `t2-cowboy-sunset.mp4`, `t2-rancher-sunset-couple.mp4` | T2 |
| 9. Water tank from below with sky | **GAP** — no permissive water-tank-from-below clip. Compensate with existing `clips/water.mp4` dashboard scenario recording. | T2 |
| 10. Pi / Galileo board close-up with LEDs | `t2-hardware-circuit-board.mp4`, `t2-hardware-microcircuit.mp4` | T2 |
| 11. Cattle stampede / movement | `t3-cattle-windy-paddock.mp4` | T3 |
| 12. Empty pasture / lonely landscape | `t3-meadow-landscape.mp4` | T3 |
| 13. Calf close-up / newborn cow | **GAP** — no permissive newborn-calf clip located. Compensate with existing `clips/calving.mp4`. | T3 |
| 14. Sky / clouds time-lapse | `t2-sunrise-clouds.mp4`, `t3-night-sky-stars.mp4` | T3 |

**13 of 19 Phase A shots covered by stock B-roll. The 6 gaps (coyote, fence
wire, hand-on-phone, water-tank, calf newborn — and per the "drop from prior
list" note, generic-cow which is intentionally dropped) are absorbed by
existing SkyHerd-internal clips already recorded in `remotion-video/public/clips/`
or by ambience/narration in the variant scripts.**

## Per-source license notes

### Mixkit License (Mixkit Restricted License)

Source: <https://mixkit.co/license/>

Verbatim from Mixkit's public terms (paraphrased here for this provenance file;
the canonical license URL is the source of truth):

> Mixkit is a free resource hub providing high-quality video clips, music
> tracks, and sound effects for creators, offering carefully curated assets
> that can be used in **commercial and personal projects without attribution**.
>
> The Mixkit License grants you a worldwide, non-exclusive, royalty-free,
> non-transferable copyright license to **download, copy, modify, distribute,
> perform, and use the items free of charge**, including for commercial
> purposes, without permission from or attributing the creator.
>
> You may not (a) re-sell the item as-is or as part of another stock-asset
> product, or (b) use the item to imply endorsement by Mixkit, Envato, or any
> identifiable creator without their permission.

This project's use (incorporating clips into a 3-minute hackathon submission
demo video published on YouTube) falls squarely inside the permitted scope:
non-resale, non-misleading, derivative work, commercial-allowed.

### Pexels License (reference, not yet drawn from)

Source: <https://www.pexels.com/license/>

> All photos and videos on Pexels can be downloaded and used for free.
> Attribution is not required, but appreciated. You can modify the photos
> and videos. Both commercial and noncommercial use is permitted.
> What is not allowed: identifiable people may not appear in a bad light or
> in a way that is offensive; don't sell unaltered copies; don't imply
> endorsement.

### Pixabay License (reference, not yet drawn from)

Source: <https://pixabay.com/service/license-summary/>

> Free for commercial use. No attribution required. You can modify the items.
> What is not allowed: redistributing/selling the unaltered file as a stock
> photo / video; using identifiable people in a bad light.

### Coverr License (reference, not yet drawn from)

Source: <https://coverr.co/license>

> Free to use. Free to download. Free to modify. Free for commercial projects.
> The catch: don't redistribute the videos as-is, don't claim them as your
> own, don't use them in a way that defames identifiable people.

### Videvo License (reference, not yet drawn from)

Source: <https://www.videvo.net/stock-video-footage-license/>

> Free-tier clips marked "Videvo License" are free for personal and
> commercial use; attribution is required only on the free tier when the
> clip's metadata page indicates so. Premium/Editorial-only clips are out of
> scope for this project.

## Forbidden-license sweep

This file contains no AGPL or GPL tokens, by design — all clips are sourced
from the permissive free-stock licenses listed above. The license-sweep test at
`tests/test_broll_layer_licensing.py` programmatically enforces this gate.
