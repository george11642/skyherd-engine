#!/usr/bin/env python3
"""qc_compile_issues.py — aggregate per-second QC results into an issues report.

Reads analysis.jsonl produced by qc_video_per_second.py and writes issues.md
grouped by scene + contiguous time ranges. Also writes issues.json for downstream
verification (Phase 6).

Usage:
    python scripts/qc_compile_issues.py \\
        --analysis out/qc-frames-YYYYMMDD-HHMMSS/analysis.jsonl \\
        --output-md out/qc-frames-YYYYMMDD-HHMMSS/issues.md \\
        --output-json out/qc-frames-YYYYMMDD-HHMMSS/issues.json
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


# Scenes that DO have voice-over (used to filter "missing" noise from inter-scene gaps).
# Aligned with calculate-main-metadata.ts variant-C act durations (cumulative).
VO_ACTIVE_RANGES = [
    (6, 27),    # Act 1 hook VO 20.76s
    (27, 50),   # Act 2 traditional 22.10s
    (50, 66),   # Act 2 answer 15.50s
    (66, 96),   # Act 3 coyote (24.26s VO + breathing room)
    (96, 120),  # Act 3 grid 23.52s
    (120, 143), # Act 4 mvp 22.10s
    (143, 165), # Act 4 vision 21.55s
    (165, 178), # Act 5 aibody 13.27s
]


def in_vo_range(t: int) -> bool:
    return any(start <= t < end for start, end in VO_ACTIVE_RANGES)


def group_contiguous(seconds: list[int]) -> list[tuple[int, int]]:
    """[1,2,3,5,6,9] -> [(1,3), (5,6), (9,9)]"""
    if not seconds:
        return []
    seconds = sorted(set(seconds))
    ranges: list[tuple[int, int]] = []
    start = prev = seconds[0]
    for s in seconds[1:]:
        if s == prev + 1:
            prev = s
            continue
        ranges.append((start, prev))
        start = prev = s
    ranges.append((start, prev))
    return ranges


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args()

    rows: list[dict] = []
    for line in args.analysis.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))

    rows.sort(key=lambda r: r.get("t", -1))

    dupe_seconds: list[int] = []
    missing_seconds: list[int] = []
    parse_errors: list[int] = []
    api_errors: list[int] = []
    by_scene: dict[str, list[int]] = defaultdict(list)
    captions_at: dict[int, list[str]] = {}
    notes_at: dict[int, str] = {}

    for r in rows:
        t = int(r.get("t", -1))
        if t < 0:
            continue
        scene = (r.get("scene_label") or "").strip() or "?"
        by_scene[scene].append(t)
        captions_at[t] = list(r.get("captions_visible") or [])
        if r.get("notes"):
            notes_at[t] = r["notes"]
        if scene == "PARSE_ERROR":
            parse_errors.append(t)
        if scene == "API_ERROR":
            api_errors.append(t)
        if r.get("dupe_suspected"):
            dupe_seconds.append(t)
        # only count missing as a real bug if the second falls in an active VO range
        if r.get("missing_suspected") and in_vo_range(t):
            missing_seconds.append(t)

    dupe_ranges = group_contiguous(dupe_seconds)
    missing_ranges = group_contiguous(missing_seconds)

    # Per-scene dupe rollup
    dupe_by_scene: dict[str, list[int]] = defaultdict(list)
    for t in dupe_seconds:
        for r in rows:
            if int(r.get("t", -1)) == t:
                scene = (r.get("scene_label") or "?").strip() or "?"
                dupe_by_scene[scene].append(t)
                break

    # Per-scene missing rollup
    missing_by_scene: dict[str, list[int]] = defaultdict(list)
    for t in missing_seconds:
        for r in rows:
            if int(r.get("t", -1)) == t:
                scene = (r.get("scene_label") or "?").strip() or "?"
                missing_by_scene[scene].append(t)
                break

    md_lines: list[str] = []
    md_lines.append("# v5.6 Per-Second QC Issues Report")
    md_lines.append("")
    md_lines.append(f"- Total frames analyzed: **{len(rows)}**")
    md_lines.append(f"- Duplicate-caption seconds: **{len(dupe_seconds)}** in **{len(dupe_ranges)}** range(s)")
    md_lines.append(f"- Missing-caption seconds (inside VO ranges): **{len(missing_seconds)}** in **{len(missing_ranges)}** range(s)")
    md_lines.append(f"- Parse errors: **{len(parse_errors)}** | API errors: **{len(api_errors)}**")
    md_lines.append("")
    md_lines.append("## Duplicate captions")
    md_lines.append("")
    if not dupe_ranges:
        md_lines.append("_None detected._")
    else:
        for start, end in dupe_ranges:
            scenes = sorted({(next(r["scene_label"] for r in rows if int(r["t"]) == t) or "?") for t in range(start, end + 1) if t in captions_at})
            scene_str = ", ".join(scenes)
            md_lines.append(f"### Range {start}-{end}s  _(scene: {scene_str})_")
            for t in range(start, end + 1):
                if t not in captions_at:
                    continue
                caps = captions_at.get(t) or []
                note = notes_at.get(t, "")
                md_lines.append(f"- **t={t}s**: {caps}" + (f"  — _{note}_" if note else ""))
            md_lines.append("")

    md_lines.append("## Missing captions (in VO ranges)")
    md_lines.append("")
    if not missing_ranges:
        md_lines.append("_None detected._")
    else:
        for start, end in missing_ranges:
            scenes = sorted({(next(r["scene_label"] for r in rows if int(r["t"]) == t) or "?") for t in range(start, end + 1) if t in captions_at})
            scene_str = ", ".join(scenes)
            md_lines.append(f"### Range {start}-{end}s  _(scene: {scene_str})_")
            for t in range(start, end + 1):
                if t not in captions_at:
                    continue
                caps = captions_at.get(t) or []
                note = notes_at.get(t, "")
                md_lines.append(f"- **t={t}s**: visible={caps}" + (f"  — _{note}_" if note else ""))
            md_lines.append("")

    md_lines.append("## Per-scene dupe summary")
    md_lines.append("")
    if not dupe_by_scene:
        md_lines.append("_None._")
    else:
        for scene in sorted(dupe_by_scene.keys()):
            seconds = dupe_by_scene[scene]
            ranges = group_contiguous(seconds)
            md_lines.append(f"- **{scene}**: {len(seconds)}s across {len(ranges)} range(s) — {ranges}")

    md_lines.append("")
    md_lines.append("## Per-scene missing summary (VO ranges only)")
    md_lines.append("")
    if not missing_by_scene:
        md_lines.append("_None._")
    else:
        for scene in sorted(missing_by_scene.keys()):
            seconds = missing_by_scene[scene]
            ranges = group_contiguous(seconds)
            md_lines.append(f"- **{scene}**: {len(seconds)}s across {len(ranges)} range(s) — {ranges}")

    if parse_errors or api_errors:
        md_lines.append("")
        md_lines.append("## Errors")
        md_lines.append("")
        if parse_errors:
            md_lines.append(f"- Parse errors at: {parse_errors}")
        if api_errors:
            md_lines.append(f"- API errors at: {api_errors}")

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(md_lines))

    issues_doc = {
        "total_frames": len(rows),
        "dupe_seconds": dupe_seconds,
        "dupe_ranges": [list(r) for r in dupe_ranges],
        "missing_seconds": missing_seconds,
        "missing_ranges": [list(r) for r in missing_ranges],
        "dupe_by_scene": {k: v for k, v in dupe_by_scene.items()},
        "missing_by_scene": {k: v for k, v in missing_by_scene.items()},
        "parse_errors": parse_errors,
        "api_errors": api_errors,
        "verify_seconds": sorted(set(dupe_seconds) | set(missing_seconds)),
    }
    args.output_json.write_text(json.dumps(issues_doc, indent=2))

    print(f"wrote {args.output_md}")
    print(f"wrote {args.output_json}")
    print(f"dupe_ranges={dupe_ranges}")
    print(f"missing_ranges={missing_ranges}")


if __name__ == "__main__":
    main()
