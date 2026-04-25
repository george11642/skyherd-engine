# Elisa — Phase 7 Competitor Score

**Project:** Elisa | **Founder:** Jon McBee (dad/engineer)
**Method:** Scored from textual analysis in `.planning/research/winner-top3-analysis.md` via `mcp__gemini__gemini_chat` (Gemini 3.1 Pro, temp=0.2, thinking=medium).
**Note:** YouTube download failed (yt-dlp 2024.04.09 outdated, HTTP 400). Scored from textual analysis — see fallback note.
**Analyzed:** 2026-04-24

## Scores

| Dimension | Weight | Score | Weighted |
|---|---:|---:|---:|
| Impact | 30% | 6.5 | 1.95 |
| Demo | 25% | 9.5 | 2.375 |
| Opus 4.7 axis | 25% | 8.5 | 2.125 |
| Depth | 20% | 10.0 | 2.00 |
| **Weighted total** | — | — | **8.45 / 10** |

## Per-dimension highlights

## Impact (30%): 6.5/10
The video opens with a highly relatable, personal hook regarding the founder's 7th-grade daughter and her science fair project [0:00-0:15]. While this establishes a clear and credible framing for making software/hardware accessible to the next generation [2:26], it completely lacks the visceral economic pain or quantified stakes required for a top-tier score. The problem is understood and emotionally resonant, but not framed as a fundable, venture-scale pain point in the first 30 seconds.

## Demo (25%): 9.5/10
The demo is exceptionally strong, showcasing a true end-to-end live workflow [0:10-1:47]. The viewer gets to see the full lifecycle: defining specs in a visual IDE, watching agents build it in Mission Control, flashing the code to an actual ESP32 hardware board via USB, and finally seeing live gameplay of the generated product [2:37]. It is highly legible and proves the tool works in the real world.

## Opus 4.7 axis (25%): 8.5/10
The project explicitly names Claude Code early [0:12] and proves complex reasoning by showing a meta-planner and "Minion" agents executing tasks in real-time [1:08]. The founder makes a compelling claim that the entire application was built using Claude Code with zero manual lines written [1:50], heavily differentiating the model's capabilities.

## Depth (20%): 10.0/10
This entry perfectly hits the criteria for a 10 by delivering a massive "Stats Barrage" at [1:55]. The founder rapidly recites 30 hours, 76 commits, 39k+ lines of code, and 1500+ tests while scrolling through a dense GitHub README and file tree. Furthermore, the verbalized architecture includes MCP servers, CLI tools, real-time task graphs with dependency ordering, and hardware over serial/ethernet [0:49-1:10].

## Aggregate: 8.45/10
(6.5 × 0.30) + (9.5 × 0.25) + (8.5 × 0.25) + (10.0 × 0.20) = 1.95 + 2.375 + 2.125 + 2.00 = 8.45

## Critical issues:
- **Missing economic stakes:** The pitch relies entirely on a personal anecdote; there is no market sizing, educational sector data, or quantified pain point to make this a "fundable" pitch.
- **Pacing sag in the middle:** The meticulous explanation of the block taxonomy (Goals/Requirements/Minions) from [0:25-1:00] drags the energy down while the UI remains mostly static.
- **Basic production value:** The video relies exclusively on hard cuts (very slow cut rate of 0.45/10s) and lacks background music or polish, giving it a slightly dry, academic feel.

## Would change:
- **Quantify the hook:** Keep the story about Elisa, but immediately tie it to a massive, quantified problem (e.g., "90% of kids drop out of STEM because hardware integration is too hard — here is how we fix a $X billion education gap").
- **Condense the taxonomy explanation:** Speed through the block-snapping UI [0:25-1:00] to get to the high-energy agent execution and hardware flashing faster.
- **Elevate production:** Add subtle, driving background music to carry the viewer through the technical explanations and increase the cut rate during the UI walkthrough to maintain visual interest.
