# clips/ — Asset Provenance

All clips in this directory are SkyHerd-internal screen recordings captured from
the live simulation dashboard (`make dashboard`) or from the Remotion-rendered
replay pipeline. No third-party footage. All recordings made 2026-04-22 to
2026-04-25.

| File | Provenance | Date |
|------|-----------|------|
| ambient_30x_synthesis.mp4 | SkyHerd-internal — 30x time-lapse synthesis of ranch sensor feed, Remotion render | 2026-04-24 |
| ambient_establish.mp4 | SkyHerd-internal — establishing shot of ranch dashboard ambient state, screen recording | 2026-04-23 |
| attest_verify.mp4 | SkyHerd-internal — `skyherd-attest verify` CLI output, screen recording | 2026-04-23 |
| calving.mp4 | SkyHerd-internal — CalvingWatch scenario replay, dashboard screen recording | 2026-04-22 |
| coyote.mp4 | SkyHerd-internal — FenceLineDispatcher coyote-alert scenario replay, dashboard screen recording | 2026-04-22 |
| fresh_clone.mp4 | SkyHerd-internal — `make demo SEED=42 SCENARIO=all` fresh clone run, screen recording | 2026-04-24 |
| sick_cow.mp4 | SkyHerd-internal — HerdHealthWatcher sick-cow scenario replay, dashboard screen recording | 2026-04-22 |
| storm.mp4 | SkyHerd-internal — GrazingOptimizer storm-incoming scenario replay, dashboard screen recording | 2026-04-22 |
| water.mp4 | SkyHerd-internal — water tank pressure drop scenario replay, dashboard screen recording | 2026-04-22 |

## B-roll sources

Pexels-sourced b-roll is managed separately via `scripts/fetch_broll.sh`. Those
assets live in `remotion-video/public/broll/` and carry their own Pexels free
license. This `clips/` directory contains only SkyHerd-internal recordings.

## License

SkyHerd-internal recordings are original work by the SkyHerd project team.
MIT License. See root `LICENSE` file.
