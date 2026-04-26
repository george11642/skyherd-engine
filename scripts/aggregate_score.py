#!/usr/bin/env python3
"""
aggregate_score.py — Aggregate Opus stills scores + Gemini critique into final score.

Usage (normal mode):
    python scripts/aggregate_score.py \\
        --variant A --iter 3 \\
        --opus-jsonl  out/iter-3/A-opus-stills.jsonl \\
        --gemini-md   .planning/research/gemini-cache/iter3-A-critique.md \\
        --output      .planning/research/iter-3-A-score.md

Usage (ship-gate check, exits 0 only if gate met):
    python scripts/aggregate_score.py --check-ship-gate --variant A

Usage (competitor mode — parse existing critique md):
    python scripts/aggregate_score.py \\
        --mode competitor --input .planning/research/competitor-cache/crossbeam-critique.md \\
        --variant crossbeam \\
        --output .planning/research/competitor-scores.md

Score formula:
    Opus aggregate  = 0.30×Impact + 0.25×Demo + 0.25×Opus + 0.20×Depth  (median per batch)
    Gemini aggregate = same weights applied to Gemini critique dimensions
    Final aggregate  = (Opus_aggregate + Gemini_aggregate) / 2

Plateau detection (stored in out/iter-history-{variant}.json):
    Plateau = variance of last 3 Final aggregates < 0.15 AND mean ≥ 9.5
    Any CRITICAL: or WOULD CHANGE: line in Gemini critique blocks plateau.

Ship gate (--check-ship-gate):
    Final aggregate ≥ 9.46
    Impact   ≥ 9.5
    Demo     ≥ 9.5
    Opus     ≥ 8.5
    Depth    ≥ 10.0
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import median, variance

# ── Constants ─────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent

WEIGHTS = {
    "impact": 0.30,
    "demo": 0.25,
    "opus": 0.25,
    "depth": 0.20,
}

# Ship gate thresholds (beats CrossBeam 8.93 by ≥0.5)
SHIP_GATE = {
    "aggregate": 9.46,
    "impact": 9.5,
    "demo": 9.5,
    "opus": 8.5,
    "depth": 10.0,
}

# Plateau detection
PLATEAU_VARIANCE_THRESHOLD = 0.15
PLATEAU_MEAN_THRESHOLD = 9.5
PLATEAU_WINDOW = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("aggregate_score")

# ── Dimension name normalisers ─────────────────────────────────────────────────

# Gemini uses "Opus 4.7 axis", Opus JSON uses "opus" — map all to canonical keys
_DIM_ALIASES: dict[str, str] = {
    "impact": "impact",
    "demo": "demo",
    "demo quality": "demo",
    "opus": "opus",
    "opus 4.7 axis": "opus",
    "opus 4.7 use": "opus",
    "opus use": "opus",
    "depth": "depth",
    "technical depth": "depth",
}


def _normalise_dim(raw: str) -> str | None:
    return _DIM_ALIASES.get(raw.lower().strip())


# ── Opus JSONL parsing ─────────────────────────────────────────────────────────


def parse_opus_jsonl(jsonl_path: Path) -> dict[str, float]:
    """
    Read Opus stills JSONL (one batch JSON per line).
    Return median score per dimension across all batches.
    """
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Opus JSONL not found: {jsonl_path}")

    per_dim: dict[str, list[float]] = {k: [] for k in WEIGHTS}

    with jsonl_path.open() as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                log.warning("Skipping malformed JSONL line %d: %s", line_no, exc)
                continue

            scores = rec.get("scores", {})
            for raw_key, value in scores.items():
                canonical = _normalise_dim(raw_key)
                if canonical and isinstance(value, (int, float)):
                    per_dim[canonical].append(float(value))

    result: dict[str, float] = {}
    for dim, values in per_dim.items():
        if not values:
            log.warning("No Opus scores found for dimension '%s'", dim)
            result[dim] = 0.0
        else:
            result[dim] = round(median(values), 3)

    log.info(
        "Opus medians — Impact:%.2f  Demo:%.2f  Opus:%.2f  Depth:%.2f",
        result.get("impact", 0),
        result.get("demo", 0),
        result.get("opus", 0),
        result.get("depth", 0),
    )
    return result


# ── Gemini critique md parsing ─────────────────────────────────────────────────

# Format 1 (gemini-rubric.md canonical output):
#   ## Impact (30%): 9.5/10
#   ## Demo (25%): 7.5/10
#   ## Opus 4.7 axis (25%): 6.0/10
#   ## Depth (20%): 10.0/10
#   ## Aggregate: 8.07/10

_GEMINI_DIM_RE = re.compile(
    r"^##\s+(Impact|Demo|Opus 4\.7 axis|Depth)\s+\(\d+%\)\s*:\s*([\d.]+)/10",
    re.IGNORECASE | re.MULTILINE,
)
_GEMINI_AGG_RE = re.compile(
    r"^##\s+Aggregate\s*:\s*([\d.]+)/10",
    re.MULTILINE,
)
_CRITICAL_RE = re.compile(
    r"^(CRITICAL|WOULD CHANGE)\s*[:\-]",
    re.IGNORECASE | re.MULTILINE,
)

# Format 2 (legacy table format used in iter1 critiques):
#   | Impact | 30% | 9.5 | 2.85 |
#   | Demo | 25% | 9.0 | 2.25 |
#   | Opus 4.7 use | 25% | 8.5 | 2.125 |
#   | Depth | 20% | 10.0 | 2.00 |

_GEMINI_TABLE_DIM_RE = re.compile(
    r"^\|\s*(Impact|Demo Quality|Demo|Opus 4\.7 use|Opus 4\.7 axis|Depth|Technical Depth)\s*\|\s*\d+%\s*\|\s*([\d.]+)\s*\|",
    re.IGNORECASE | re.MULTILINE,
)


def parse_gemini_md(md_path: Path) -> tuple[dict[str, float], bool, list[str]]:
    """
    Parse Gemini critique markdown.

    Returns:
        (dim_scores, has_blocking_flags, blocking_flag_lines)
        dim_scores keys: impact, demo, opus, depth
        has_blocking_flags: True if any CRITICAL: or WOULD CHANGE: line found
    """
    if not md_path.exists():
        raise FileNotFoundError(f"Gemini critique not found: {md_path}")

    content = md_path.read_text()

    # Dimension scores — try canonical heading format first, fall back to table format
    scores: dict[str, float] = {}

    raw_dims = _GEMINI_DIM_RE.findall(content)
    for raw_name, raw_val in raw_dims:
        canonical = _normalise_dim(raw_name)
        if canonical:
            scores[canonical] = float(raw_val)

    # If heading format found nothing, try legacy table format
    if not scores:
        table_dims = _GEMINI_TABLE_DIM_RE.findall(content)
        for raw_name, raw_val in table_dims:
            canonical = _normalise_dim(raw_name)
            if canonical:
                scores[canonical] = float(raw_val)

    # Gemini sometimes writes the aggregate; we recompute it ourselves but log it
    agg_match = _GEMINI_AGG_RE.search(content)
    if agg_match:
        log.info("Gemini stated aggregate: %s/10", agg_match.group(1))

    # Blocking flags
    blocking_lines = _CRITICAL_RE.findall(content)
    has_blocking = bool(blocking_lines)

    if has_blocking:
        log.warning(
            "Gemini critique has %d blocking flag(s): %s",
            len(blocking_lines),
            blocking_lines,
        )

    log.info(
        "Gemini scores — Impact:%.2f  Demo:%.2f  Opus:%.2f  Depth:%.2f",
        scores.get("impact", 0),
        scores.get("demo", 0),
        scores.get("opus", 0),
        scores.get("depth", 0),
    )
    return scores, has_blocking, blocking_lines


# ── Weighted aggregate ─────────────────────────────────────────────────────────


def weighted_aggregate(scores: dict[str, float]) -> float:
    total = sum(scores.get(dim, 0.0) * weight for dim, weight in WEIGHTS.items())
    return round(total, 4)


# ── Plateau detection ──────────────────────────────────────────────────────────


def iter_history_path(variant: str) -> Path:
    return PROJECT_ROOT / "out" / f"iter-history-{variant}.json"


def load_iter_history(variant: str) -> list[dict]:
    path = iter_history_path(variant)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Could not read iter history: %s", exc)
        return []


def save_iter_history(variant: str, history: list[dict]) -> None:
    path = iter_history_path(variant)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2))


def check_plateau(history: list[dict], has_blocking: bool) -> tuple[bool, str]:
    """
    Returns (is_plateau, reason_string).
    Plateau requires:
    - Last PLATEAU_WINDOW (3) iterations exist
    - Variance of their Final aggregates < PLATEAU_VARIANCE_THRESHOLD
    - Mean ≥ PLATEAU_MEAN_THRESHOLD
    - No blocking Gemini flags in current critique
    """
    if has_blocking:
        return False, "Blocked by CRITICAL/WOULD CHANGE flags in Gemini critique"

    if len(history) < PLATEAU_WINDOW:
        return False, f"Only {len(history)}/{PLATEAU_WINDOW} iterations available"

    recent = history[-PLATEAU_WINDOW:]
    finals = [r["final_aggregate"] for r in recent]
    var = variance(finals) if len(finals) > 1 else 0.0
    mean = sum(finals) / len(finals)

    if var >= PLATEAU_VARIANCE_THRESHOLD:
        return False, f"Variance {var:.4f} ≥ threshold {PLATEAU_VARIANCE_THRESHOLD}"
    if mean < PLATEAU_MEAN_THRESHOLD:
        return False, f"Mean {mean:.4f} < threshold {PLATEAU_MEAN_THRESHOLD}"

    return True, (f"PLATEAU: last {PLATEAU_WINDOW} iters mean={mean:.4f} variance={var:.4f}")


# ── Ship gate ──────────────────────────────────────────────────────────────────


def check_ship_gate(
    final_aggregate: float,
    final_dims: dict[str, float],
) -> tuple[bool, list[str]]:
    """
    Returns (passes, failure_reasons).
    """
    failures: list[str] = []

    if final_aggregate < SHIP_GATE["aggregate"]:
        failures.append(f"Aggregate {final_aggregate:.4f} < {SHIP_GATE['aggregate']}")
    for dim in ("impact", "demo", "opus", "depth"):
        val = final_dims.get(dim, 0.0)
        threshold = SHIP_GATE[dim]
        if val < threshold:
            failures.append(f"{dim.capitalize()} {val:.2f} < {threshold}")

    return not failures, failures


# ── Top fix suggestion dedup + ranking ────────────────────────────────────────


def extract_top_fixes(jsonl_path: Path | None, top_n: int = 3) -> list[dict]:
    """
    Read fix_suggestions from Opus batch JSONL.
    Deduplicate by (file_path, change summary), rank by frequency.
    Returns top_n unique suggestions.
    """
    if jsonl_path is None or not jsonl_path.exists():
        return []

    freq: dict[str, dict] = {}

    with jsonl_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            for fix in rec.get("fix_suggestions", []):
                fp = fix.get("file_path", "")
                change = fix.get("change", "")
                key = f"{fp}|{change[:80]}"
                if key not in freq:
                    freq[key] = {"count": 0, "fix": fix}
                freq[key]["count"] += 1

    ranked = sorted(freq.values(), key=lambda x: -x["count"])
    return [item["fix"] for item in ranked[:top_n]]


# ── Score markdown writer ──────────────────────────────────────────────────────


def write_score_md(
    output_path: Path,
    variant: str,
    iter_num: int,
    opus_dims: dict[str, float],
    gemini_dims: dict[str, float],
    final_dims: dict[str, float],
    opus_aggregate: float,
    gemini_aggregate: float,
    final_aggregate: float,
    plateau_status: tuple[bool, str],
    ship_gate_status: tuple[bool, list[str]],
    blocking_flags: list[str],
    top_fixes: list[dict],
    history: list[dict],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    is_plateau, plateau_reason = plateau_status
    gate_passes, gate_failures = ship_gate_status

    lines = [
        f"# SkyHerd iter-{iter_num}-{variant} Score Report",
        "",
        f"**Generated:** {datetime.now(UTC).isoformat()}",
        "",
        "---",
        "",
        "## Aggregate Scores",
        "",
        "| Source | Impact (30%) | Demo (25%) | Opus (25%) | Depth (20%) | **Aggregate** |",
        "|--------|-------------|------------|------------|-------------|---------------|",
        f"| Opus stills | {opus_dims.get('impact', 0):.2f} | {opus_dims.get('demo', 0):.2f} | {opus_dims.get('opus', 0):.2f} | {opus_dims.get('depth', 0):.2f} | **{opus_aggregate:.4f}** |",
        f"| Gemini critique | {gemini_dims.get('impact', 0):.2f} | {gemini_dims.get('demo', 0):.2f} | {gemini_dims.get('opus', 0):.2f} | {gemini_dims.get('depth', 0):.2f} | **{gemini_aggregate:.4f}** |",
        f"| **Final (avg)** | **{final_dims.get('impact', 0):.2f}** | **{final_dims.get('demo', 0):.2f}** | **{final_dims.get('opus', 0):.2f}** | **{final_dims.get('depth', 0):.2f}** | **{final_aggregate:.4f}** |",
        "",
        "---",
        "",
        "## Ship Gate",
        "",
        f"Status: {'✅ PASSES' if gate_passes else '❌ FAILS'}",
        "",
    ]

    if gate_failures:
        for reason in gate_failures:
            lines.append(f"- {reason}")
        lines.append("")

    # Plateau section
    lines += [
        "## Plateau Detection",
        "",
        f"Status: {'🏁 PLATEAU REACHED' if is_plateau else '🔄 CONTINUING'}",
        "",
        f"Reason: {plateau_reason}",
        "",
    ]

    # Iter history table
    if history:
        lines += [
            "### Iteration History",
            "",
            "| Iter | Opus | Gemini | Final |",
            "|------|------|--------|-------|",
        ]
        for h in history[-6:]:  # last 6 iters
            lines.append(
                f"| {h['iter']} | {h.get('opus_aggregate', 0):.4f} | {h.get('gemini_aggregate', 0):.4f} | {h['final_aggregate']:.4f} |"
            )
        lines.append("")

    # Blocking flags
    if blocking_flags:
        lines += [
            "## Blocking Flags",
            "",
        ]
        for flag in blocking_flags:
            lines.append(f"- **{flag}**")
        lines.append("")

    # Top fix suggestions
    if top_fixes:
        lines += [
            "## Top Fix Suggestions",
            "",
        ]
        for i, fix in enumerate(top_fixes, 1):
            frame = fix.get("frame", "N/A")
            fp = fix.get("file_path", "N/A")
            change = fix.get("change", "N/A")
            lines += [
                f"### Fix {i} (priority {i})",
                "",
                f"- **Frame:** `{frame}`",
                f"- **File:** `{fp}`",
                f"- **Change:** {change}",
                "",
            ]

    output_path.write_text("\n".join(lines))
    log.info("Score report written to %s", output_path)


# ── Competitor mode ────────────────────────────────────────────────────────────


def run_competitor_mode(args: argparse.Namespace) -> None:
    """
    Parse an existing critique md and emit a JSON envelope (+ optional score append).
    Compatible with score_competitor.sh integration.
    """
    input_path = Path(args.input)
    scores, has_blocking, blocking_lines = parse_gemini_md(input_path)

    agg = weighted_aggregate(scores)

    envelope = {
        "variant": args.variant,
        "mode": "competitor",
        "scores": {
            "impact": scores.get("impact", 0.0),
            "demo": scores.get("demo", 0.0),
            "opus": scores.get("opus", 0.0),
            "depth": scores.get("depth", 0.0),
            "aggregate": agg,
        },
        "critique_path": str(input_path.resolve()),
        "timestamp": datetime.now(UTC).isoformat(),
    }

    print(json.dumps(envelope, indent=2))

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Append (or create) competitor scores file
        mode = "a" if output_path.exists() else "w"
        with output_path.open(mode) as fh:
            fh.write(f"\n## {args.variant}\n\n")
            fh.write(f"- Impact: {scores.get('impact', 0):.2f}/10\n")
            fh.write(f"- Demo: {scores.get('demo', 0):.2f}/10\n")
            fh.write(f"- Opus 4.7: {scores.get('opus', 0):.2f}/10\n")
            fh.write(f"- Depth: {scores.get('depth', 0):.2f}/10\n")
            fh.write(f"- **Aggregate: {agg:.2f}/10**\n")
        log.info("Competitor scores appended to %s", output_path)


# ── Ship-gate-only check ───────────────────────────────────────────────────────


def run_check_ship_gate(args: argparse.Namespace) -> int:
    """
    Read latest iter history for variant and check ship gate.
    Returns 0 if gate passes, 1 otherwise.
    """
    history = load_iter_history(args.variant)
    if not history:
        log.error("No iter history found for variant %s", args.variant)
        print(f"SHIP GATE: FAILS — no history for variant {args.variant}")
        return 1

    latest = history[-1]
    final_aggregate = latest["final_aggregate"]
    final_dims = latest.get("final_dims", {})

    passes, failures = check_ship_gate(final_aggregate, final_dims)
    if passes:
        print(f"SHIP GATE: PASSES — aggregate={final_aggregate:.4f} iter={latest['iter']}")
        return 0
    else:
        print(f"SHIP GATE: FAILS — aggregate={final_aggregate:.4f}")
        for reason in failures:
            print(f"  - {reason}")
        return 1


# ── Main ───────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--variant",
        help="Variant (A, B, or C; any string in competitor mode)",
    )
    parser.add_argument("--iter", type=int, default=1, help="Iteration number")
    parser.add_argument("--opus-jsonl", help="Path to Opus stills JSONL output")
    parser.add_argument("--gemini-md", help="Path to Gemini critique markdown")
    parser.add_argument("--output", help="Path to write score markdown report")
    parser.add_argument(
        "--check-ship-gate",
        action="store_true",
        help="Check ship gate for variant (uses iter history). Exits 0 if gate passes.",
    )
    parser.add_argument(
        "--mode",
        choices=["normal", "competitor"],
        default="normal",
        help="Mode: normal (Opus+Gemini) or competitor (Gemini critique only).",
    )
    parser.add_argument("--input", help="(competitor mode) Input critique markdown path")
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Print expected competitor JSON envelope schema and exit.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # ── Schema help ──────────────────────────────────────────────────────────
    if args.schema:
        print(
            json.dumps(
                {
                    "variant": "<str>",
                    "mode": "competitor",
                    "scores": {
                        "impact": "<float>",
                        "demo": "<float>",
                        "opus": "<float>",
                        "depth": "<float>",
                        "aggregate": "<float>",
                    },
                    "critique_path": "<str>",
                    "timestamp": "<iso8601>",
                },
                indent=2,
            )
        )
        return 0

    # ── Competitor mode ───────────────────────────────────────────────────────
    if args.mode == "competitor":
        if not args.input:
            parser.error("--input is required in competitor mode")
        if not args.variant:
            parser.error("--variant is required in competitor mode")
        run_competitor_mode(args)
        return 0

    # ── Ship-gate-only check ──────────────────────────────────────────────────
    if args.check_ship_gate:
        if not args.variant:
            parser.error("--variant is required for --check-ship-gate")
        if args.variant not in ("A", "B", "C"):
            parser.error("--variant must be A, B, or C for --check-ship-gate")
        return run_check_ship_gate(args)

    # ── Normal mode: requires both inputs ────────────────────────────────────
    if not args.variant:
        parser.error("--variant is required")
    if args.variant not in ("A", "B", "C"):
        parser.error(
            "--variant must be A, B, or C in normal mode (use --mode competitor for other names)"
        )
    if not args.opus_jsonl:
        parser.error("--opus-jsonl is required in normal mode")
    if not args.gemini_md:
        parser.error("--gemini-md is required in normal mode")

    # Parse scores
    opus_dims = parse_opus_jsonl(Path(args.opus_jsonl))
    gemini_dims, has_blocking, blocking_lines = parse_gemini_md(Path(args.gemini_md))

    # Aggregate each source
    opus_aggregate = weighted_aggregate(opus_dims)
    gemini_aggregate = weighted_aggregate(gemini_dims)

    # Final = average of both sources per dimension, then aggregate
    final_dims = {
        dim: round((opus_dims.get(dim, 0.0) + gemini_dims.get(dim, 0.0)) / 2, 4) for dim in WEIGHTS
    }
    final_aggregate = round((opus_aggregate + gemini_aggregate) / 2, 4)

    log.info(
        "Final aggregate for %s iter-%d: %.4f (Opus=%.4f, Gemini=%.4f)",
        args.variant,
        args.iter,
        final_aggregate,
        opus_aggregate,
        gemini_aggregate,
    )

    # Load + update history
    history = load_iter_history(args.variant)
    history.append(
        {
            "iter": args.iter,
            "opus_aggregate": opus_aggregate,
            "gemini_aggregate": gemini_aggregate,
            "final_aggregate": final_aggregate,
            "final_dims": final_dims,
            "opus_dims": opus_dims,
            "gemini_dims": gemini_dims,
            "has_blocking": has_blocking,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )
    save_iter_history(args.variant, history)

    # Plateau + ship gate
    plateau_status = check_plateau(history, has_blocking)
    ship_gate_status = check_ship_gate(final_aggregate, final_dims)

    # Top fixes from Opus batches
    top_fixes = extract_top_fixes(Path(args.opus_jsonl))

    # Write report
    output_path = Path(
        args.output
        or PROJECT_ROOT / ".planning" / "research" / f"iter-{args.iter}-{args.variant}-score.md"
    )
    write_score_md(
        output_path=output_path,
        variant=args.variant,
        iter_num=args.iter,
        opus_dims=opus_dims,
        gemini_dims=gemini_dims,
        final_dims=final_dims,
        opus_aggregate=opus_aggregate,
        gemini_aggregate=gemini_aggregate,
        final_aggregate=final_aggregate,
        plateau_status=plateau_status,
        ship_gate_status=ship_gate_status,
        blocking_flags=blocking_lines,
        top_fixes=top_fixes,
        history=history,
    )

    # Print summary to stdout for shell orchestrator consumption
    is_plateau, plateau_reason = plateau_status
    gate_passes, gate_failures = ship_gate_status

    print(f"AGGREGATE: {final_aggregate:.4f}")
    print(f"SHIP_GATE: {'PASS' if gate_passes else 'FAIL'}")
    print(f"PLATEAU: {'YES' if is_plateau else 'NO'}")
    if not gate_passes:
        for f in gate_failures:
            print(f"  GAP: {f}")
    print(f"REPORT: {output_path}")

    # Exit codes: 0 = normal success, 2 = ship gate passed, 3 = plateau reached
    if is_plateau:
        return 3
    if gate_passes:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
