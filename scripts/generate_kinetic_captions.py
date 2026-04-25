"""Generate kinetic-caption JSON for the SkyHerd v2 demo video.

Phase E1 of the video-v2 plan. Two output modes:

  * **sparse** — variants A and B. Only the emphasis windows declared in the
    variant scripts (``docs/scripts/skyherd-script-{A,B}.md``) are written out.
    The Remotion ``KineticCaptions`` component renders these as punch-word
    lower-thirds at the second mentioned in the script.
  * **dense** — variant C. Runs faster-whisper over the concatenated VO bus
    for the variant and emits one entry per spoken word with start/end
    timestamps.

Output: ``remotion-video/public/captions/captions-{A,B,C}.json``

This script is **idempotent** — re-running with no source changes is a no-op.
We hash the input audio (or, in sparse mode, the parsed emphasis windows) and
embed the digest in the output. If the recomputed digest matches what's
already on disk, the run exits 0 without re-transcribing.

Usage::

    uv run python scripts/generate_kinetic_captions.py --variant A
    uv run python scripts/generate_kinetic_captions.py --variant C --force
    uv run python scripts/generate_kinetic_captions.py --variant all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Literal

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "docs" / "scripts"
VOICEOVER_DIR = ROOT / "remotion-video" / "public" / "voiceover"
CAPTIONS_DIR = ROOT / "remotion-video" / "public" / "captions"

LOG = logging.getLogger("kinetic-captions")

# --------------------------------------------------------------------------- #
# Variant configuration                                                       #
# --------------------------------------------------------------------------- #

Variant = Literal["A", "B", "C"]
Mode = Literal["sparse", "dense"]

VARIANT_SCRIPTS: dict[Variant, str] = {
    "A": "skyherd-script-A-winner-pattern.md",
    "B": "skyherd-script-B-hybrid.md",
    "C": "skyherd-script-C-differentiated.md",
}

# Variant C runs the full VO bus through faster-whisper. The cues below cover
# every spoken word in the 5-act layout (matching ``calculate-main-metadata``
# 's ``VO_FILES`` entries for variant C plus shared scenario cues).
VARIANT_C_VO_CUES: tuple[str, ...] = (
    "vo-hook-C.mp3",
    "vo-story-C.mp3",
    "vo-coyote.mp3",
    "vo-sick-cow.mp3",
    "vo-calving.mp3",
    "vo-storm.mp3",
    "vo-synthesis-C.mp3",
    "vo-opus-C.mp3",
    "vo-depth-C.mp3",
    "vo-close-C.mp3",
)


# --------------------------------------------------------------------------- #
# Sparse-mode emphasis-window parsing                                         #
# --------------------------------------------------------------------------- #


# Lines that look like::
#   - 0:01 — "**They don't.**"
#   - 0:24 — "Beef · record highs"
EMPHASIS_LINE_RE = re.compile(
    r"^- (?P<min>\d+):(?P<sec>\d{1,2})\s*[—-]\s*[\"“](?P<text>.+?)[\"”]"
)


def _strip_md(text: str) -> str:
    """Strip markdown emphasis (bold/italic) without losing the word."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text.strip()


def parse_emphasis_windows(variant: Variant) -> list[dict[str, Any]]:
    """Extract emphasis-window punch-word lines from the variant script.

    Returns ``[]`` for variant C (dense mode — emphasis windows aren't used).
    """
    if variant == "C":
        return []

    script_path = SCRIPTS_DIR / VARIANT_SCRIPTS[variant]
    if not script_path.is_file():
        raise FileNotFoundError(f"variant script missing: {script_path}")

    windows: list[dict[str, Any]] = []
    for line in script_path.read_text(encoding="utf-8").splitlines():
        m = EMPHASIS_LINE_RE.match(line.strip())
        if not m:
            continue
        minute = int(m.group("min"))
        second = int(m.group("sec"))
        total = minute * 60 + second
        text = _strip_md(m.group("text"))
        if not text:
            continue
        windows.append({"second": total, "text": text})
    return windows


# --------------------------------------------------------------------------- #
# Dense-mode transcription via faster-whisper                                 #
# --------------------------------------------------------------------------- #


@dataclass
class WordTiming:
    word: str
    start: float
    end: float


@dataclass
class SegmentTiming:
    start: float
    end: float
    text: str
    words: list[WordTiming]


def transcribe_cue(audio_path: pathlib.Path, model: Any) -> list[SegmentTiming]:
    """Transcribe one VO cue with word-level timestamps."""
    LOG.info("transcribing %s", audio_path.name)
    segments_iter, _info = model.transcribe(
        str(audio_path),
        language="en",
        word_timestamps=True,
        vad_filter=False,
        beam_size=5,
    )

    segments: list[SegmentTiming] = []
    for seg in segments_iter:
        words: list[WordTiming] = []
        for w in seg.words or []:
            words.append(
                WordTiming(
                    word=w.word.strip(),
                    start=float(w.start),
                    end=float(w.end),
                )
            )
        segments.append(
            SegmentTiming(
                start=float(seg.start),
                end=float(seg.end),
                text=seg.text.strip(),
                words=words,
            )
        )
    return segments


def _segment_to_dict(seg: SegmentTiming, offset: float = 0.0) -> dict[str, Any]:
    return {
        "start": round(seg.start + offset, 3),
        "end": round(seg.end + offset, 3),
        "text": seg.text,
        "words": [
            {
                "word": w.word,
                "start": round(w.start + offset, 3),
                "end": round(w.end + offset, 3),
            }
            for w in seg.words
        ],
    }


def _ffprobe_duration(path: pathlib.Path) -> float:
    """Read MP3 duration in seconds via ffprobe."""
    import subprocess

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return float(result.stdout.strip())
    except (subprocess.SubprocessError, ValueError) as exc:
        LOG.warning("ffprobe failed on %s: %s", path.name, exc)
        return 0.0


def transcribe_dense(model: Any) -> list[dict[str, Any]]:
    """Concatenate variant C cues, transcribing each with their wall-clock offsets.

    The offset for each cue is the cumulative duration of preceding cues so the
    output uses an absolute timeline matching the rendered video.
    """
    out: list[dict[str, Any]] = []
    cursor = 0.0
    for filename in VARIANT_C_VO_CUES:
        path = VOICEOVER_DIR / filename
        if not path.is_file():
            LOG.warning("missing C cue %s — skipping", filename)
            continue
        duration = _ffprobe_duration(path)
        segments = transcribe_cue(path, model)
        for seg in segments:
            out.append(_segment_to_dict(seg, offset=cursor))
        cursor += duration
    return out


# --------------------------------------------------------------------------- #
# Payload assembly + idempotence                                              #
# --------------------------------------------------------------------------- #


def build_payload(
    variant: Variant,
    mode: Mode,
    emphasis: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the JSON payload that the KineticCaptions component reads.

    Schema:

    .. code-block:: json

        {
          "variant": "A" | "B" | "C",
          "mode": "sparse" | "dense",
          "emphasis": [{"second": 4, "text": "They don't."}, ...],
          "segments": [{"start": 0.0, "end": 1.4, "text": "...",
                        "words": [{"word": "...", "start": 0.0, "end": 0.4}, ...]}],
          "fingerprint": "<sha256 hex of inputs>"
        }
    """
    fp_input = json.dumps(
        {"emphasis": emphasis, "segments": segments}, sort_keys=True
    ).encode("utf-8")
    fingerprint = hashlib.sha256(fp_input).hexdigest()

    return {
        "variant": variant,
        "mode": mode,
        "emphasis": emphasis,
        "segments": segments,
        "fingerprint": fingerprint,
    }


def output_path(variant: Variant) -> pathlib.Path:
    return CAPTIONS_DIR / f"captions-{variant}.json"


def already_current(out_path: pathlib.Path, payload: dict[str, Any]) -> bool:
    """Return True if the on-disk file already matches this payload's fingerprint."""
    if not out_path.is_file():
        return False
    try:
        existing = json.loads(out_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return existing.get("fingerprint") == payload["fingerprint"]


# --------------------------------------------------------------------------- #
# Per-variant orchestration                                                   #
# --------------------------------------------------------------------------- #


def run_variant(variant: Variant, force: bool = False) -> tuple[Mode, int]:
    """Generate the captions JSON for a single variant.

    Returns (mode, emphasis_count_or_segment_count) for the report.
    """
    CAPTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out = output_path(variant)

    if variant in ("A", "B"):
        emphasis = parse_emphasis_windows(variant)
        payload = build_payload(
            variant=variant, mode="sparse", emphasis=emphasis, segments=[]
        )
        if not force and already_current(out, payload):
            LOG.info("captions-%s.json up-to-date — skipping", variant)
            return "sparse", len(emphasis)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return "sparse", len(emphasis)

    # Dense — variant C requires faster-whisper.
    LOG.info("loading faster-whisper (small) for variant C…")
    try:
        from faster_whisper import WhisperModel  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            "faster-whisper not installed — run `uv add faster-whisper`"
        ) from exc

    model = WhisperModel("small", compute_type="int8")
    segments = transcribe_dense(model)
    payload = build_payload(
        variant="C", mode="dense", emphasis=[], segments=segments
    )
    if not force and already_current(out, payload):
        LOG.info("captions-C.json up-to-date — skipping")
        return "dense", len(segments)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return "dense", len(segments)


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument(
        "--variant",
        choices=["A", "B", "C", "all"],
        default="all",
        help="which variant(s) to (re)generate",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="re-run even if the on-disk fingerprint matches",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true", help="enable debug logging"
    )
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    variants: tuple[Variant, ...] = (
        ("A", "B", "C") if args.variant == "all" else (args.variant,)
    )

    summary: list[str] = []
    for v in variants:
        mode, count = run_variant(v, force=args.force)
        summary.append(f"  {v}: {mode} ({count} entries)")

    print("kinetic captions:")
    print("\n".join(summary))
    print(f"output dir: {CAPTIONS_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
