# SkyHerd Design System

**Status**: Production — shipped in `web/src/`. Live at [skyherd-engine.vercel.app](https://skyherd-engine.vercel.app).
**Screenshots**: [dashboard.png](design/dashboard.png) · [rancher.png](design/rancher.png) · [cross-ranch.png](design/cross-ranch.png)

The visual language is a dense, dark ops console — Bloomberg Terminal meets topographic ranch map. Every choice is intentional: ranchers and judges should read it the same way they read a telemetry board, not a marketing site.

---

## Color tokens

Defined in `web/src/index.css` as Tailwind v4 `@theme` CSS custom properties. Never use raw hex outside this file.

| Token | Value | Role |
|---|---|---|
| `--color-bg-0` | `rgb(10 12 16)` | Page canvas |
| `--color-bg-1` | `rgb(16 19 25)` | Panel surface |
| `--color-bg-2` | `rgb(24 28 36)` | Raised card / hover state |
| `--color-line` | `rgb(38 45 58)` | Borders, dividers |
| `--color-text-0` | `rgb(236 239 244)` | Primary text |
| `--color-text-1` | `rgb(168 180 198)` | Secondary / label |
| `--color-text-2` | `rgb(110 122 140)` | Muted / disabled |
| `--color-accent-sage` | `rgb(148 176 136)` | Primary action, healthy state |
| `--color-accent-dust` | `rgb(210 178 138)` | Idle / warm secondary |
| `--color-accent-thermal` | `rgb(255 143 60)` | Thermal alert, active fence |
| `--color-accent-sky` | `rgb(120 180 220)` | Drone telemetry, data link |
| `--color-warn` | `rgb(240 195 80)` | Non-critical warning |
| `--color-danger` | `rgb(224 100 90)` | Critical alert, error state |
| `--color-ok` | `rgb(120 190 140)` | Confirmed healthy |

The four accents map to ranch semantics: sage (vegetation, life), dust (earth, idle), thermal (heat signature, threat), sky (airspace, connectivity).

---

## Typography scale

Three variable fonts loaded via `@fontsource-variable`. All weights are variable-axis — no separate weight files.

| Role | Family | Usage |
|---|---|---|
| Display | Fraunces Variable (serif) | Page headlines, scenario titles, hero numbers |
| Body | Inter Variable (sans) | All UI text, labels, descriptions, buttons |
| Mono | JetBrains Mono Variable | Cost ticker, attestation hashes, log lines, chip badges |

Base body: 14 px / 20 px line-height. Display headings track −0.02 em. Tabular numerals (`tnum`) applied via `.tabnum` utility and all `.chip` elements — cost and hash columns never shift width.

---

## Component inventory

| Component | File | Notes |
|---|---|---|
| AgentLane | `AgentLane.tsx` | Single Managed Agent row — status dot, event log, wake count |
| AgentLanes | `AgentLanes.tsx` | Five-lane grid, shared MQTT state |
| CostTicker | `CostTicker.tsx` | framer-motion animated dollar counter; freezes visibly when idle |
| AttestationPanel | `AttestationPanel.tsx` | Live Ed25519 Merkle chain table — hash prefix, signature, timestamp |
| RanchMap | `RanchMap.tsx` | SVG canvas topography + entity markers (cattle, predator, drone, trough) |
| CrossRanchView | `CrossRanchView.tsx` | Split-pane mesh handoff — ranch_a → ranch_b agent relay |
| RancherPhone | `RancherPhone.tsx` | PWA rancher UI — incoming "Wes" call screen, urgency tier display |
| Chip variants | `index.css` `.chip-*` | Mono-font status badges: sage, sky, dust, thermal, warn, danger, muted |
| Button variants | `index.css` `.btn-*` | Primary (sage fill), ghost (bordered), danger (red alpha) |

---

## Density rules

The dashboard is designed for a 1440 × 900 viewport minimum. Information density is intentionally high — this is a monitoring console, not a landing page.

- Panel padding: 12 px inner / 8 px between panels
- Row height: 28 px for log lines, 36 px for agent lanes
- Border radius: 2 px throughout — square corners signal precision; curves are only for status dots
- Scrollbars: 4 px track, hidden until hover

---

## Motion rules

All animations are declared in `index.css` `@keyframes`. Framer-motion is used only for the CostTicker value transitions (spring physics on number changes).

| Animation | Duration | Trigger |
|---|---|---|
| `pulse-dot` | 1.6 s ease-in-out loop | Active agent indicator |
| `threat-ring` | 1.8 s ease-out loop | Predator alert on ranch map |
| `phone-ring` | 1.2 s ease-in-out loop | Incoming Wes call |
| `log-enter` | 240 ms ease-out | New log line slide-in |
| `fence-pulse` | 1.6 s ease-in-out loop | Fence breach glow |

`prefers-reduced-motion: reduce` disables all five animations. No motion is load-bearing — every animated element remains visible and readable when animation is off.

---

## Accessibility

- Focus ring: 2 px solid `--color-accent-sage`, 2 px offset. Applies via `:focus-visible` only (no keyboard-vs-mouse ambiguity).
- Color contrast: text-0 on bg-0 exceeds 12:1. Text-1 on bg-1 exceeds 7:1. Accent-sage on bg-0 exceeds 4.5:1 (WCAG AA).
- `color-scheme: dark` declared on `html` — browser UI (scrollbars, form inputs) matches.
- Tabular numerals on all numeric columns prevent layout shift on live updates.
- Reduced-motion media query disables all CSS animations.
