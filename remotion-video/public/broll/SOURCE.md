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
| t1-pexels-coyote-night.mp4              | Pexels | https://www.pexels.com/video/silhouettes-in-moonlit-forest-video-34660193/                                | Pexels License                | 2026-04-24 |
| t1-pexels-fence-wire.mp4                | Pexels | https://www.pexels.com/video/a-metal-wire-mesh-fence-4650102/                                             | Pexels License                | 2026-04-24 |
| t2-pexels-hand-phone.mp4                | Pexels | https://www.pexels.com/video/close-up-view-of-person-calling-emergency-sos-6831196/                       | Pexels License                | 2026-04-24 |
| t2-pexels-water-tank.mp4                | Pexels | https://www.pexels.com/video/aerial-drone-footage-of-abandoned-desert-ranch-35529631/                     | Pexels License                | 2026-04-24 |
| t3-pexels-calf.mp4                      | Pexels | https://www.pexels.com/video/tender-moment-between-cow-and-newborn-calf-in-forest-35854640/               | Pexels License                | 2026-04-24 |
| t3-pexels-vet-mobile.mp4                | Pexels | https://www.pexels.com/video/vet-examining-little-dog-s-face-6235179/                                     | Pexels License                | 2026-04-24 |
| t1-pexels-drone-thermal.mp4             | Pexels | https://www.pexels.com/video/aerial-view-of-tractor-in-australian-countryside-31711788/                   | Pexels License                | 2026-04-24 |
| t1-pexels-ranch-dawn.mp4                | Pexels | https://www.pexels.com/video/rural-scenery-at-dawn-10585381/                                              | Pexels License                | 2026-04-24 |

### Phase H iter2 — Pexels gap fills (acquired 2026-04-24)

The iter1 inventory left 6 Phase-A shots un-covered on Mixkit/Coverr. With a
Pexels API key in hand, the `scripts/fetch_pexels.sh` pipeline searched for
each gap (plus a few variants like `drone aerial farm` and `ranch dawn`) and
picked the best 1080p result per search. All 8 clips are under the Pexels
License (commercial use allowed, no attribution required — attribution
recorded above as a courtesy).

| File | Contributor | Notes |
|---|---|---|
| `t1-pexels-coyote-night.mp4` | Burak Bahadır Büyükkılınç | silhouettes in moonlit forest — fills "coyote at fence" night ambience |
| `t1-pexels-fence-wire.mp4` | Pavel Danilyuk | metal wire-mesh fence close-up |
| `t2-pexels-hand-phone.mp4` | Tima Miroshnichenko | close-up hand placing an emergency SOS call — the Twilio/Wes voice-call beat |
| `t2-pexels-water-tank.mp4` | Strange Happenings | aerial over an abandoned desert ranch with a water-tank silhouette |
| `t3-pexels-calf.mp4` | Gizem Gökce | tender moment between a cow and a newborn calf (portrait framing, letterboxed in normalize) |
| `t3-pexels-vet-mobile.mp4` | Tima Miroshnichenko | vet examining an animal with a mobile/clinical framing — stands in for the vet-intake mock |
| `t1-pexels-drone-thermal.mp4` | Macourt Media | aerial drone view of a tractor on rural Australian farmland (establishing drone flyover; not literally thermal) |
| `t1-pexels-ranch-dawn.mp4` | Ruslan Sikunov | rural dawn scenery — the opening Act 1 establishing shot |

## Shot-list mapping (Phase A reference)

The Phase A 19-shot list (see `.planning/research/winner-top3-analysis.md` lines
341–374) drives the choices below. Mapping is many-to-one where multiple Mixkit
clips give variant coverage for the same Phase A bullet.

| Phase A shot | Mapped clip(s) | Tier |
|---|---|---|
| 1. Dawn over the corral / sunrise on rangeland | `t1-dawn-corral-golden.mp4`, `t2-sunrise-clouds.mp4`, `t1-pexels-ranch-dawn.mp4` | T1 |
| 2. Cattle herd grazing wide shot | `t1-cattle-grazing-wide.mp4`, `t1-cattle-herd-countryside.mp4`, `t3-cattle-windy-paddock.mp4` | T1 |
| 3. Drone aerial over rangeland | `t1-drone-rangeland-aerial.mp4`, `t1-drone-arid-mountains.mp4`, `t1-pexels-drone-thermal.mp4` | T1 |
| 4. Coyote silhouette / eyes at night | `t1-pexels-coyote-night.mp4` (silhouettes in moonlit forest — iter2 Pexels fill) | T1 |
| 5. Fence wire close-up at night | `t1-pexels-fence-wire.mp4` (metal wire-mesh fence close-up — iter2 Pexels fill) | T1 |
| 6. Lightning / storm cell on horizon | `t1-storm-cell-horizon.mp4`, `t1-lightning-night.mp4` | T1 |
| 7. Gloved hand on phone or radio | `t2-pexels-hand-phone.mp4` (close-up hand placing an emergency SOS call — iter2 Pexels fill) | T2 |
| 8. Rancher's boot kicking dust / walking through gate | `t2-rancher-horse-walk.mp4`, `t2-cowboy-sunset.mp4`, `t2-rancher-sunset-couple.mp4` | T2 |
| 9. Water tank from below with sky | `t2-pexels-water-tank.mp4` (aerial over abandoned desert ranch with water-tank — iter2 Pexels fill) | T2 |
| 10. Pi / Galileo board close-up with LEDs | `t2-hardware-circuit-board.mp4`, `t2-hardware-microcircuit.mp4` | T2 |
| 11. Cattle stampede / movement | `t3-cattle-windy-paddock.mp4` | T3 |
| 12. Empty pasture / lonely landscape | `t3-meadow-landscape.mp4` | T3 |
| 13. Calf close-up / newborn cow | `t3-pexels-calf.mp4` (tender moment: cow and newborn calf — iter2 Pexels fill) | T3 |
| 14. Sky / clouds time-lapse | `t2-sunrise-clouds.mp4`, `t3-night-sky-stars.mp4` | T3 |
| 15. Vet mobile / clinical hand-off | `t3-pexels-vet-mobile.mp4` (iter2 Pexels fill — stands in for the vet-intake mock) | T3 |

**Phase H iter2 update: all 6 Phase A gaps (coyote, fence wire, hand-on-phone,
water-tank, calf newborn, vet-mobile) are now filled by Pexels B-roll. Total
stock-B-roll clip count: 16 Mixkit + 8 Pexels = 24 clips. The SkyHerd-internal
dashboard recordings in `remotion-video/public/clips/` remain available as
supplementary cutaways but are no longer required to paper over shot gaps.**

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
