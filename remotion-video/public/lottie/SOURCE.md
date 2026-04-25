# Lottie Animation Sources

Phase E2 of the SkyHerd video v2 plan. The 5 primitives below are rendered
with `@remotion/lottie` inside the Demo act for each variant.

**License**: All animations are CC0 — authored from scratch in this repo via
`scripts/generate_lottie_primitives.py`. They are NOT derived from any
LottieFiles asset. Re-run the generator to regenerate identical bytes.

| File | Purpose | Source | License | SHA256 |
|---|---|---|---|---|
| `stat-counter.json` | Cost ticker reveal — "$4.17/week" pop-up | `scripts/generate_lottie_primitives.py::stat_counter` | CC0 | `37f68711e5962e18540f0d60fb2bacbb297cf4b73f926ff1e89b8724f05454e1` |
| `map-pin-drop.json` | Scenario trigger pin drop | `scripts/generate_lottie_primitives.py::map_pin_drop` | CC0 | `f1dde22aa51ee9b9547b027cf94dea591bdd07c2963753d69deb64385741d3bd` |
| `hash-chip-slide.json` | Attestation hash-chip slide-in | `scripts/generate_lottie_primitives.py::hash_chip_slide` | CC0 | `bb114a6997a7aae25f20e22185a1460570462d738e8da5a5583642b9792527c0` |
| `pulse-wave.json` | Sensor activity indicator (concentric pulses) | `scripts/generate_lottie_primitives.py::pulse_wave` | CC0 | `45697194df322e05e0504abb68897fbc7617591fcdea627375c35e4cb84f03ca` |
| `check-complete.json` | Scenario resolution checkmark | `scripts/generate_lottie_primitives.py::check_complete` | CC0 | `b85485ce38b30e6f80587c109b16cc273efe781950b970cac642a62fb2805b4a` |

## Why authored, not sourced

LottieFiles' library has many CC0/MIT assets but vetting each one (and
recording stable SHAs after the site re-encodes JSON whitespace) creates
a license-audit hazard for a hackathon submission. By authoring our own
primitives we collapse the provenance story to: `git log` + this README.

## Acquisition date

2026-04-24 — generated via `uv run python scripts/generate_lottie_primitives.py`.

## Forbidden license tokens

The Phase E2 license-sweep test (`tests/test_lottie_layer_licensing.py`)
rejects any of: `GPL`, `AGPL`, `LGPL`, `proprietary`, `royalty`. Only
`CC0` and `MIT` are accepted; we ship the primitives under CC0.
