"""Sanity test: v2 render paths must not reference wes-*.mp3 anymore.

Phase C of the demo-video v2 plan retires the Wes cowboy persona and
regenerates the entire VO bus as vo-*.mp3 with a neutral 19yo male voice
(Antoni — ElevenLabs ID ErXwobaYiN019PkySvjV).

This test sweeps `remotion-video/src/` for any `wes-*.mp3` literal and
fails if found. The v1 fallback render still references wes-*.mp3 but it
ships as a pre-rendered MP4 (docs/demo-assets/video/skyherd-demo-v1-sim-first.mp4),
not a re-render — the v1 act components were deleted as part of Phase C.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "remotion-video" / "src"

# Match string-literal references to wes-anything inside source files.
WES_REF_PATTERN = re.compile(r"wes-[a-z0-9_-]+\.mp3", re.IGNORECASE)


def test_no_wes_mp3_references_in_v2_remotion_sources() -> None:
    """No wes-*.mp3 string literals anywhere under remotion-video/src/."""
    if not SRC_DIR.is_dir():
        # If the Remotion tree is missing (e.g. partial clone), skip — this
        # test is a guardrail for the v2 render path, not a hard CI gate.
        return

    offenders: list[tuple[Path, int, str]] = []
    for path in sorted(SRC_DIR.rglob("*.tsx")) + sorted(SRC_DIR.rglob("*.ts")):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if WES_REF_PATTERN.search(line):
                offenders.append((path.relative_to(REPO_ROOT), lineno, line.strip()))

    assert not offenders, (
        "Found wes-*.mp3 references in v2 render path — Phase C requires "
        "all v2 sources to use vo-*.mp3 (neutral 19yo male voice).\n"
        + "\n".join(f"  {p}:{ln}: {src}" for p, ln, src in offenders)
    )


def test_v2_voiceover_dir_has_vo_prefix_mp3s() -> None:
    """Confirm the v2 VO bus (vo-*.mp3) is present in public/voiceover."""
    vo_dir = REPO_ROOT / "remotion-video" / "public" / "voiceover"
    if not vo_dir.is_dir():
        # Don't hard-fail if public/ isn't checked in / hydrated.
        return

    vo_files = sorted(vo_dir.glob("vo-*.mp3"))
    # Phase C target was ~14-18 cues across A/B/C variants. Allow ≥10 to
    # tolerate partial regen states.
    assert len(vo_files) >= 10, (
        f"Expected ≥10 vo-*.mp3 cues in {vo_dir}, found {len(vo_files)}: "
        f"{[f.name for f in vo_files]}"
    )

    # Spot-check the variant-shared scenario cues exist by name.
    required = {"vo-coyote.mp3", "vo-sick-cow.mp3", "vo-calving.mp3", "vo-storm.mp3"}
    present = {f.name for f in vo_files}
    missing = required - present
    assert not missing, f"Missing variant-shared scenario VO cues: {sorted(missing)}"
