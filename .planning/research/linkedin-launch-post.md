# LinkedIn Launch Post Draft — SkyHerd

**STATUS: DRAFT ONLY. George approves before publish per CLAUDE.md hard rule. DO NOT POST.**

---

## Post copy

---

$4.17/week to watch 50,000 acres. That number on screen stopped me cold when I first saw it rendered.

I built SkyHerd — a 5-agent nervous system for working ranches — for the Anthropic "Built with Claude Opus 4.7" hackathon. Here's what it actually does:

- **Watches the land 24/7.** FenceLineDispatcher, HerdHealthWatcher, CalvingWatch, GrazingOptimizer, and PredatorPatternLearner share one platform session and go idle between events. No idle compute means the meter stops when nothing is happening. A US beef ranch running 500 head costs about $4 to monitor for a week — not $4K.

- **New in this build.** Inworld "Nate" voice on escalation calls, Opus 4.7 AI-directed caption styling, and OpenMontage agentic editorial that picked the b-roll cuts. The demo video itself was produced by a meta-loop where Opus 4.7 scored its own stills and dispatched fix agents until the score plateaued — the final render (variant C, 8.69/10) was never touched by hand.

- **Real code, not a slide deck.** `make demo SEED=42 SCENARIO=all` on a fresh clone: five field scenarios (coyote at the fence, sick cow, water tank drop, calving, incoming storm), deterministic replay, 1,106 tests, 87% coverage, Ed25519 Merkle attestation chain.

Demo video: [YOUTUBE_URL_PLACEHOLDER — fill in after upload]

Repo: github.com/george11642/skyherd-engine

Built with Claude Opus 4.7 | @Anthropic | #BuiltWithOpus47 | #AgTech | #ClaudeHackathon

---

## Screenshot moment to embed

Frame at **0:57** — the cost ticker reveal: "$4.17 / week" on a dark background. Thumbnail already extracted at `docs/demo-assets/video/skyherd-thumb-C.png`. This is the frame Gemini flagged as the strongest "pause and screenshot" moment in all three variants.

---

## Notes for George

- Replace `[YOUTUBE_URL_PLACEHOLDER]` with the real URL from `scripts/upload_youtube.sh` once creds are added.
- The #BuiltWithOpus47 tag is the hackathon official tag — keep it.
- The $4.17/week claim is sourced from the demo cost-ticker computation in the five-scenario run — it is defensible. If anyone asks: the breakdown is ~$0.10/agent-activation × ~40 activations/week + Twilio SMS overhead.
- Attach `skyherd-thumb-C.png` as the post image (LinkedIn native image, not link preview).
- LinkedIn character limit: 3,000. This draft is ~550 characters — room to expand if desired.
