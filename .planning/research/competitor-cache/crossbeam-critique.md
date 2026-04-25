# CrossBeam — Phase 7 Competitor Score

**Project:** CrossBeam | **Founder:** Mike Brown (personal injury lawyer)
**Method:** Scored from textual analysis in `.planning/research/winner-top3-analysis.md` via `mcp__gemini__gemini_chat` (Gemini 3.1 Pro, temp=0.2, thinking=medium).
**Note:** YouTube download failed (yt-dlp 2024.04.09 outdated, HTTP 400). Scored from textual analysis — see fallback note.
**Analyzed:** 2026-04-24

## Scores (Run 1 — canonical)

| Dimension | Weight | Score | Weighted |
|---|---:|---:|---:|
| Impact | 30% | 9.5 | 2.85 |
| Demo | 25% | 9.0 | 2.25 |
| Opus 4.7 axis | 25% | 8.5 | 2.125 |
| Depth | 20% | 8.5 | 1.70 |
| **Weighted total** | — | — | **8.93 / 10** |

## Per-dimension highlights

## Impact (30%): 9.5/10
The video establishes a visceral, contrarian hook immediately at [0:00] by reframing the California housing crisis as a "permit crisis." The stakes are brilliantly quantified and grounded in reality by the Mayor's testimonial at [2:08] (needing 3,000 homes but building <100), and the drone shots at [2:46] perfectly connect the software to physical, real-world impact. This is a highly credible, fundable framing.

## Demo (25%): 9.0/10
The demo is highly convincing and shows a clear end-to-end workflow without relying on loading spinners. From the initial document upload at [1:08-1:22] to the split-screen accuracy proof at [1:52-2:03] and the dual-sided City Reviewer dashboard at [2:24-2:31], the viewer easily understands both sides of the marketplace product in a single watch.

## Opus 4.7 axis (25%): 8.5/10
This hits the maximum allowable score for a 4.6 entry. The video explicitly names and visualizes the model's role during the node diagram pan at [1:26-1:50], showing the "Opus Orchestrator" launching parallel sub-agents (Manifest Agent, Corrections Parser). It perfectly demonstrates how Claude's multi-agent capabilities are essential to solving the complex spatial reasoning problem outlined earlier.

## Depth (20%): 8.5/10
The technical framing is strong, clearly articulating the difficulty of spatial reasoning on massive blueprints combined with dense legal text [0:39-1:00]. The inclusion of the multi-agent architecture diagram [1:26-1:50] gives expert viewers confidence in the engineering design, though it misses a perfect score by lacking verifiable benchmarks, test counts, or latency stats on screen.

## Aggregate: 8.93/10
(9.5 × 0.30) + (9.0 × 0.25) + (8.5 × 0.25) + (8.5 × 0.20) = 2.85 + 2.25 + 2.125 + 1.70 = 8.925

## Critical issues:
- The founder's face is never shown on camera, which slightly diminishes the personal connection and founder-market fit narrative despite the strong VO.
- There is a noticeable drop in pacing and production quality during the first builder testimonial [0:24-0:38], creating a sag early in the video.
- While the architecture is visualized beautifully, the video lacks hard engineering metrics (e.g., accuracy benchmarks, processing time, or test coverage) to fully max out the Technical Depth category.

## Would change:
- Cut or heavily trim the low-quality builder testimonial at [0:24-0:38] to maintain the high energy and premium production value established in the hook.
- Overlay hard performance metrics (e.g., "98% accuracy vs human baseline" or "processing time reduced from 3 weeks to 4 minutes") during the split-screen demo [1:52-2:03].
- Add a brief 5-second on-camera introduction from the founder at the beginning to establish immediate personal credibility and trust.
- Briefly flash a snippet of the actual prompt structure or routing code alongside the "Opus Orchestrator" node diagram to further ground the technical claims for developer judges.

## Reproducibility check (Run 2)

| Dimension | Run 1 | Run 2 | Delta |
|---|---:|---:|---:|
| Impact | 9.5 | 9.0 | 0.5 |
| Demo | 9.0 | 9.5 | 0.5 |
| Opus | 8.5 | 8.5 | 0.0 |
| Depth | 8.5 | 9.0 | 0.5 |
| **Aggregate** | **8.93** | **9.00** | **0.075** |

**Reproducibility verdict: PASS (delta 0.075 < ±0.30 threshold)**
