#!/usr/bin/env python3
"""
pick_winner.py — autonomous winner selection for SkyHerd Phase 8.

Reads .planning/research/final-{A,B,C}-score.md, picks the variant with
the highest aggregate score. Tiebreaker: highest Opus 4.7 axis.
Writes the winner letter to .planning/research/winner.txt.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
RESEARCH_DIR = PROJECT_ROOT / ".planning" / "research"
VARIANTS = ["A", "B", "C"]


def parse_scores(path: Path) -> dict[str, float]:
    """Extract Final row scores from a score .md file."""
    text = path.read_text()

    # Match the Final (avg) row in the aggregate table:
    # | **Final (avg)** | **8.00** | **7.25** | **8.15** | **8.50** | **7.9500** |
    final_row = re.search(
        r"\*\*Final \(avg\)\*\*\s*\|"
        r"\s*\*\*([0-9.]+)\*\*\s*\|"  # Impact
        r"\s*\*\*([0-9.]+)\*\*\s*\|"  # Demo
        r"\s*\*\*([0-9.]+)\*\*\s*\|"  # Opus 4.7
        r"\s*\*\*([0-9.]+)\*\*\s*\|"  # Depth
        r"\s*\*\*([0-9.]+)\*\*",  # Aggregate
        text,
    )
    if not final_row:
        raise ValueError(f"Could not parse Final row in {path}")

    impact, demo, opus, depth, aggregate = (float(g) for g in final_row.groups())
    return {
        "impact": impact,
        "demo": demo,
        "opus": opus,
        "depth": depth,
        "aggregate": aggregate,
    }


def pick_winner() -> str:
    scores: dict[str, dict[str, float]] = {}
    for variant in VARIANTS:
        score_path = RESEARCH_DIR / f"final-{variant}-score.md"
        if not score_path.exists():
            print(f"WARNING: {score_path} not found — skipping variant {variant}", file=sys.stderr)
            continue
        scores[variant] = parse_scores(score_path)
        print(
            f"  {variant}: aggregate={scores[variant]['aggregate']:.4f}  "
            f"opus={scores[variant]['opus']:.4f}"
        )

    if not scores:
        raise RuntimeError("No score files found. Cannot pick winner.")

    # Primary sort: aggregate descending. Tiebreaker: opus descending.
    winner = max(
        scores,
        key=lambda v: (scores[v]["aggregate"], scores[v]["opus"]),
    )
    return winner


def main() -> None:
    print("SkyHerd pick_winner.py — Phase 8")
    print("Scores:")
    winner = pick_winner()

    out_path = RESEARCH_DIR / "winner.txt"
    out_path.write_text(winner)
    print(f"\nWINNER: {winner}")
    print(f"Written to: {out_path}")


if __name__ == "__main__":
    main()
