# PostVisit.ai — Phase 7 Competitor Score

**Project:** PostVisit.ai | **Founder:** Michał Nedoszytko (cardiologist, 20yr software side-hustle)
**Method:** Scored from textual analysis in `.planning/research/winner-top3-analysis.md` via `mcp__gemini__gemini_chat` (Gemini 3.1 Pro, temp=0.2, thinking=medium).
**Note:** YouTube download failed (yt-dlp 2024.04.09 outdated, HTTP 400). Scored from textual analysis — see fallback note.
**Analyzed:** 2026-04-24

## Scores

| Dimension | Weight | Score | Weighted |
|---|---:|---:|---:|
| Impact | 30% | 6.0 | 1.80 |
| Demo | 25% | 9.0 | 2.25 |
| Opus 4.7 axis | 25% | 8.0 | 2.00 |
| Depth | 20% | 7.5 | 1.50 |
| **Weighted total** | — | — | **7.55 / 10** |

## Per-dimension highlights

## Impact (30%): 6.0/10
The founder establishes immense personal credibility as a cardiologist in the first 15 seconds, but fails to quantify the stakes of the problem. While the pain point is clearly stated at [0:38] ("The real struggle happens the moment that you leave the room"), the lack of hard numbers regarding readmission rates, time wasted, or financial loss keeps this from scoring higher. The problem is stated and credible, but not viscerally felt through data.

## Demo (25%): 9.0/10
The demo is exceptionally clear and demonstrates a highly practical, multi-sided workflow. The transition from the patient dashboard [1:10] to the physical-to-digital ambient recording [1:58] proves the software can survive real-world, non-EHR connected environments. The viewer easily understands the value proposition in a single watch.

## Opus 4.7 axis (25%): 8.0/10
The project explicitly names the model via a terminal title card at [0:50] and highlights a specific, high-value use case for the model's architecture at [1:36] by leveraging the 1-million token context window to process entire health files. It effectively demonstrates the model working on a complex medical task, though it falls just short of the 8.5 cap by not showing the step-by-step visual proof of the model's internal reasoning.

## Depth (20%): 7.5/10
The technical depth is solid, evidenced by the PubMed integration for evidence-based grounding [2:18] and the "API & Skills" slide [2:49] that proves the application is more than a simple wrapper. However, it lacks hard engineering evidence like test coverage, benchmarks, or live code execution on screen to push it into the top tier.

## Aggregate: 7.55/10
(6.0 × 0.30) + (9.0 × 0.25) + (8.0 × 0.25) + (7.5 × 0.20) = 1.80 + 2.25 + 2.00 + 1.50 = 7.55

## Critical issues:
- **Missing quantified impact:** The pitch relies entirely on qualitative statements; there are no metrics regarding the cost of poor post-visit care or time saved for the doctor.
- **Overlong setup:** Spending over a minute (33% of the video) on the travel montage and founder context delays the actual product demonstration.
- **Pacing sag during core tech:** The explanation of the 1M token context window [1:35-1:49] relies on a slow scroll through text-heavy UI, dropping the energy right when the core AI value is being explained.
- **Lack of engineering metrics:** No test counts, latency benchmarks, or accuracy stats are provided for the medical jargon translation or PubMed grounding.

## Would change:
- **Add a quantified hook:** Insert a hard statistic in the first 15 seconds (e.g., "Poor post-visit compliance costs hospitals $X billion and leads to Y% readmissions").
- **Condense the travel montage:** Cut the hackathon travel sequence [0:52-1:05] down to 5 seconds to get to the patient dashboard demo faster.
- **Visualize the context window:** Instead of a slow text scroll at [1:35], use a dynamic visual showing hundreds of medical documents being instantly ingested and synthesized by Opus.
- **Show an architecture diagram:** Replace the static "API & Skills" slide at the end with a clear architecture diagram showing how Opus, PubMed, and the mobile app interact.
- **Include accuracy benchmarks:** Briefly flash a metric on screen during the PubMed integration [2:18] proving the hallucination rate is mitigated for medical use.
