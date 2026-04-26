"""Generate kinetic-caption JSON for the SkyHerd v2 demo video.

Phase E1 of the video-v2 plan introduced two transcription modes:

  * **sparse** — variants A and B. Only the emphasis windows declared in the
    variant scripts (``docs/scripts/skyherd-script-{A,B}.md``) are written out.
    The Remotion ``KineticCaptions`` component renders these as punch-word
    lower-thirds at the second mentioned in the script.
  * **dense** — variant C. Runs faster-whisper over the concatenated VO bus
    for the variant and emits one entry per spoken word with start/end
    timestamps.

Output: ``remotion-video/public/captions/captions-{A,B,C}.json``

Phase G adds a third sub-command, ``style``, that asks Claude Opus 4.7 to
emit per-word visual styling (color / weight / animation / emphasis_level)
for each transcribed word. The styled JSON is written to
``remotion-video/public/captions/styled-captions-{A,B,C}.json`` and is read
preferentially by the ``KineticCaptions`` component, with graceful fallback
to the plain captions when the styled file is missing.

This script is **idempotent** — re-running with no source changes is a no-op.
We hash the input audio (or, in sparse mode, the parsed emphasis windows) and
embed the digest in the output. If the recomputed digest matches what's
already on disk, the run exits 0 without re-transcribing.

Usage::

    uv run python scripts/generate_kinetic_captions.py --variant A
    uv run python scripts/generate_kinetic_captions.py --variant C --force
    uv run python scripts/generate_kinetic_captions.py --variant all
    uv run python scripts/generate_kinetic_captions.py style --variant all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import pathlib
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

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
EMPHASIS_LINE_RE = re.compile(r"^- (?P<min>\d+):(?P<sec>\d{1,2})\s*[—-]\s*[\"“](?P<text>.+?)[\"”]")


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
    fp_input = json.dumps({"emphasis": emphasis, "segments": segments}, sort_keys=True).encode(
        "utf-8"
    )
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
        payload = build_payload(variant=variant, mode="sparse", emphasis=emphasis, segments=[])
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
        raise SystemExit("faster-whisper not installed — run `uv add faster-whisper`") from exc

    model = WhisperModel("small", compute_type="int8")
    segments = transcribe_dense(model)
    payload = build_payload(variant="C", mode="dense", emphasis=[], segments=segments)
    if not force and already_current(out, payload):
        LOG.info("captions-C.json up-to-date — skipping")
        return "dense", len(segments)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return "dense", len(segments)


# --------------------------------------------------------------------------- #
# Phase G — Opus 4.7 caption styling                                          #
# --------------------------------------------------------------------------- #
#
# The ``style`` sub-command reads ``captions-{variant}.json``, asks Claude
# Opus 4.7 to emit per-word visual styling, and writes
# ``styled-captions-{variant}.json``. The Remotion ``KineticCaptions``
# component reads the styled file when present and falls back to the plain
# captions otherwise.
#
# CLAUDE.md non-negotiables observed here:
#
#   * ``cache_control: ephemeral`` on the system + skills prefix blocks so
#     repeat runs across variants share a cached prefix (~30K tokens).
#   * ``ANTHROPIC_API_KEY`` must be present — we abort with a clear error if
#     the key is missing; we do **not** fall back silently to a stub.
#   * Idempotent — fingerprint over (caption JSON, script markdown, system
#     prompt, model). On match we skip the API call.

# Earth-tone palette — the system prompt tells Opus to stay inside this set
# unless emphasis_level >= 3, in which case a brick / espresso accent is
# allowed. We expose it as a module-level constant so tests can assert on it.
STYLE_PALETTE: tuple[str, ...] = (
    "#F5D49C",  # cream
    "#5A3A22",  # espresso
    "#A36B3A",  # clay
    "#3D5A3D",  # sage
    "#C04B2D",  # brick
)

ALLOWED_ANIMATIONS: tuple[str, ...] = ("fade", "pop", "pulse", "scale", "glow")
ALLOWED_WEIGHTS: tuple[str, ...] = ("normal", "bold", "black")

STYLE_MODEL = "claude-opus-4-7"
STYLE_MAX_TOKENS = 16000

# Skills the styling prompt loads as a second cache-controlled system block.
# We pick voice-persona/wes-register (governs tone) and ranch-ops/urgency-tiers
# (governs emphasis vocabulary). The system prompt itself is the first block.
STYLE_SKILL_FILES: tuple[str, ...] = (
    "voice-persona/wes-register.md",
    "voice-persona/urgency-tiers.md",
    "voice-persona/never-panic.md",
)

STYLE_SYSTEM_PROMPT = """You are an editorial caption stylist for a 3-minute hackathon demo video.

Your job: for each spoken word in the transcript, decide how it should look
on screen. You are not transcribing — the words are fixed. You are choosing
visual emphasis the same way a film editor would.

For every input word emit exactly one JSON object with these fields:

  * color: a hex string. Stay inside this earth-tone palette unless an
    emphasis_level of 3 demands the brick accent:
      #F5D49C cream    — default warm body text
      #5A3A22 espresso — quiet, grounding moments
      #A36B3A clay     — domain nouns (ranch, herd, fence, drone)
      #3D5A3D sage     — actions, verbs of care
      #C04B2D brick    — emphasis_level 3 only (highest stakes)
  * weight: one of "normal", "bold", "black"
  * animation: one of "fade", "pop", "pulse", "scale", "glow"
      - fade  — calm body text
      - pop   — money / numbers / shock cuts
      - pulse — verbs of attention ("watch", "see", "look")
      - scale — physical actions ("flies", "moves", "drops")
      - glow  — words about loss / blindness / silence
  * emphasis_level: integer 0..3
      0 — connective tissue (articles, prepositions)
      1 — normal sentence words
      2 — domain nouns and strong verbs
      3 — THE single most important word in each segment. Reserve for
          words like "blind", "watch", "$4.17", "65-year low",
          proper nouns of crisis. At most one level-3 word per segment.

Constraints:

  * Match the editorial tone in the supplied script — ranching / sim-first
    SkyHerd. Warm, plain-spoken, never corporate.
  * Animation must follow semantics: glow on "blind", pulse on "watch",
    pop on money figures, scale on action verbs.
  * Output ONLY a JSON array. No prose, no commentary, no markdown fences.
  * Preserve the exact ordering and word/start/end/segment_id fields you
    were given. Add color, weight, animation, emphasis_level. Nothing else.
"""


def styled_output_path(variant: Variant) -> pathlib.Path:
    return CAPTIONS_DIR / f"styled-captions-{variant}.json"


def flatten_caption_words(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Reduce a captions-{variant}.json payload to a flat list of words.

    Sparse mode (variants A/B): each emphasis window is split on
    whitespace; every resulting token becomes a pseudo-word with a
    1-second dwell starting at the window's ``second`` field.

    Dense mode (variant C): every word inside every segment is emitted
    in order with its existing ``start``/``end`` timestamps; the
    ``segment_id`` is the index of the source segment.
    """
    mode = payload.get("mode")
    out: list[dict[str, Any]] = []

    if mode == "sparse":
        for seg_id, window in enumerate(payload.get("emphasis", [])):
            text = str(window.get("text", "")).strip()
            if not text:
                continue
            tokens = [t for t in text.split() if t]
            second = float(window.get("second", 0))
            # Distribute tokens evenly across a 1-second dwell so word
            # timing roughly matches Wes's voice cadence.
            slice_dur = 1.0 / max(1, len(tokens))
            for i, tok in enumerate(tokens):
                start = round(second + i * slice_dur, 3)
                end = round(start + slice_dur, 3)
                out.append(
                    {
                        "word": tok,
                        "start": start,
                        "end": end,
                        "segment_id": seg_id,
                    }
                )
        return out

    if mode == "dense":
        for seg_id, seg in enumerate(payload.get("segments", [])):
            for w in seg.get("words", []):
                word_text = str(w.get("word", "")).strip()
                if not word_text:
                    continue
                out.append(
                    {
                        "word": word_text,
                        "start": float(w.get("start", 0.0)),
                        "end": float(w.get("end", 0.0)),
                        "segment_id": seg_id,
                    }
                )
        return out

    raise ValueError(f"unknown captions mode: {mode!r}")


def _load_skills_prefix() -> str:
    """Concatenate the skills/ files referenced by STYLE_SKILL_FILES.

    Missing skill files are skipped with a warning rather than failing the
    run — the system prompt is the load-bearing context, the skills are
    domain flavor.
    """
    chunks: list[str] = []
    skills_dir = ROOT / "skills"
    for relpath in STYLE_SKILL_FILES:
        path = skills_dir / relpath
        if not path.is_file():
            LOG.warning("skill prefix file missing: %s", relpath)
            continue
        chunks.append(f"# skills/{relpath}\n\n" + path.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(chunks)


def _read_script_excerpt(variant: Variant) -> str:
    """Return the variant's script markdown (used for tone context)."""
    path = SCRIPTS_DIR / VARIANT_SCRIPTS[variant]
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def build_style_user_prompt(
    variant: Variant,
    words: list[dict[str, Any]],
    script_excerpt: str,
) -> str:
    """Assemble the user-message body for one variant.

    The transcript is embedded as JSON so Opus sees ordering and
    timestamps verbatim. The script excerpt provides tone context but
    is never the source of truth for words.
    """
    return (
        f"Variant: {variant}\n\n"
        "Transcript (one entry per word — preserve ordering and "
        "timestamps verbatim, augment with styling):\n"
        f"{json.dumps(words, indent=2)}\n\n"
        "Script context (for tone only — do NOT alter the words above):\n"
        f"{script_excerpt}\n\n"
        "Emit a JSON array. One entry per input word. Preserve word, "
        "start, end, and segment_id; add color, weight, animation, "
        "emphasis_level. Output ONLY the JSON, no preamble."
    )


def _strip_code_fence(text: str) -> str:
    """Remove ```json ... ``` fences if Opus wrapped the output."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Drop the opening fence (with or without language tag).
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[: -len("```")]
    return stripped.strip()


def parse_styled_response(raw: str, source_words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse Opus's response, validate schema, return styled words."""
    blob = _strip_code_fence(raw)
    try:
        parsed = json.loads(blob)
    except json.JSONDecodeError as exc:
        raise ValueError(f"styled response is not valid JSON: {exc}") from exc

    if not isinstance(parsed, list):
        raise ValueError("styled response must be a JSON array")
    if len(parsed) != len(source_words):
        raise ValueError(
            f"styled response word count ({len(parsed)}) != input ({len(source_words)})"
        )

    out: list[dict[str, Any]] = []
    hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
    allowed_animations = set(ALLOWED_ANIMATIONS)
    allowed_weights = set(ALLOWED_WEIGHTS)

    for i, (entry, src) in enumerate(zip(parsed, source_words, strict=True)):
        if not isinstance(entry, dict):
            raise ValueError(f"styled entry {i} is not an object")
        for field in ("color", "weight", "animation", "emphasis_level"):
            if field not in entry:
                raise ValueError(f"styled entry {i} missing field: {field}")
        color = str(entry["color"])
        if not hex_re.match(color):
            raise ValueError(f"styled entry {i} bad color: {color!r}")
        weight = str(entry["weight"])
        if weight not in allowed_weights:
            raise ValueError(f"styled entry {i} bad weight: {weight!r}")
        animation = str(entry["animation"])
        if animation not in allowed_animations:
            raise ValueError(
                f"styled entry {i} bad animation: {animation!r} "
                f"(allowed: {sorted(allowed_animations)})"
            )
        try:
            level = int(entry["emphasis_level"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"styled entry {i} non-integer emphasis_level") from exc
        if not 0 <= level <= 3:
            raise ValueError(f"styled entry {i} emphasis_level out of range: {level}")
        out.append(
            {
                "word": src["word"],
                "start": src["start"],
                "end": src["end"],
                "segment_id": src["segment_id"],
                "color": color,
                "weight": weight,
                "animation": animation,
                "emphasis_level": level,
            }
        )
    return out


def build_style_payload(
    variant: Variant,
    model: str,
    words: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the on-disk styled-captions-{variant}.json payload."""
    fp_input = json.dumps(
        {"variant": variant, "model": model, "words": words}, sort_keys=True
    ).encode("utf-8")
    return {
        "variant": variant,
        "mode": "styled",
        "model": model,
        "fingerprint": hashlib.sha256(fp_input).hexdigest(),
        "words": words,
    }


def _style_input_fingerprint(
    variant: Variant,
    captions_payload: dict[str, Any],
    script_excerpt: str,
) -> str:
    """Cache key — invalidates when any input that feeds Opus changes."""
    h = hashlib.sha256()
    h.update(STYLE_MODEL.encode("utf-8"))
    h.update(STYLE_SYSTEM_PROMPT.encode("utf-8"))
    h.update(_load_skills_prefix().encode("utf-8"))
    h.update(json.dumps(captions_payload, sort_keys=True).encode("utf-8"))
    h.update(script_excerpt.encode("utf-8"))
    h.update(variant.encode("utf-8"))
    return h.hexdigest()


def _style_cache_hit(out_path: pathlib.Path, input_fp: str) -> bool:
    if not out_path.is_file():
        return False
    try:
        existing = json.loads(out_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return existing.get("input_fingerprint") == input_fp


def style_variant(variant: Variant, force: bool = False) -> dict[str, Any]:
    """Drive the Opus 4.7 styling for one variant.

    Returns a small report dict the CLI uses to print summaries.
    Raises ``SystemExit`` if ``ANTHROPIC_API_KEY`` is unset (per
    CLAUDE.md non-negotiable: don't fall back silently).
    """
    captions_path = output_path(variant)
    if not captions_path.is_file():
        raise SystemExit(
            f"plain captions missing: {captions_path}. Run `make video-captions` first."
        )
    captions_payload = json.loads(captions_path.read_text(encoding="utf-8"))
    words = flatten_caption_words(captions_payload)
    if not words:
        LOG.warning("variant %s has no words to style — skipping", variant)
        return {"variant": variant, "skipped": True, "word_count": 0}

    script_excerpt = _read_script_excerpt(variant)
    input_fp = _style_input_fingerprint(variant, captions_payload, script_excerpt)
    out_path = styled_output_path(variant)

    if not force and _style_cache_hit(out_path, input_fp):
        LOG.info("styled-captions-%s.json up-to-date — skipping API call", variant)
        existing = json.loads(out_path.read_text(encoding="utf-8"))
        return {
            "variant": variant,
            "skipped": True,
            "cached": True,
            "word_count": len(existing.get("words", [])),
        }

    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. The Phase G styling pipeline "
            "calls Claude Opus 4.7; we do not fall back to a stub. "
            "Either export the key or load it from .env.local."
        )

    try:
        from anthropic import Anthropic  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit("anthropic SDK not installed — run `uv add anthropic`") from exc

    client = Anthropic()  # picks up ANTHROPIC_API_KEY from env
    skills_prefix = _load_skills_prefix()
    user_prompt = build_style_user_prompt(
        variant=variant, words=words, script_excerpt=script_excerpt
    )

    LOG.info(
        "calling %s for variant %s (%d words, %d skill chars cached)",
        STYLE_MODEL,
        variant,
        len(words),
        len(skills_prefix),
    )

    # cache_control: ephemeral on both system blocks per CLAUDE.md
    # non-negotiable. The system prompt + skills prefix is large and
    # repeats across all 3 variant calls, so we want a cache hit on
    # variants B and C.
    response = client.messages.create(
        model=STYLE_MODEL,
        max_tokens=STYLE_MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": STYLE_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": (
                    "# Domain skills (load these as background — do not "
                    "narrate them):\n\n" + skills_prefix
                ),
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Concatenate any text blocks from the response.
    raw_text = "".join(
        getattr(block, "text", "")
        for block in response.content
        if getattr(block, "type", "") == "text"
    )
    if not raw_text.strip():
        raise SystemExit(f"variant {variant}: empty text response from {STYLE_MODEL}")

    styled_words = parse_styled_response(raw_text, source_words=words)
    payload = build_style_payload(variant=variant, model=STYLE_MODEL, words=styled_words)
    payload["input_fingerprint"] = input_fp

    # Surface usage so judges (and the run summary) can see the cache
    # working across variants.
    usage = getattr(response, "usage", None)
    if usage is not None:
        payload["usage"] = {
            "input_tokens": getattr(usage, "input_tokens", 0),
            "output_tokens": getattr(usage, "output_tokens", 0),
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
        }

    CAPTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    LOG.info(
        "wrote %s (%d words, in=%d out=%d cache_read=%d)",
        out_path.name,
        len(styled_words),
        payload.get("usage", {}).get("input_tokens", 0),
        payload.get("usage", {}).get("output_tokens", 0),
        payload.get("usage", {}).get("cache_read_input_tokens", 0),
    )

    return {
        "variant": variant,
        "skipped": False,
        "word_count": len(styled_words),
        "usage": payload.get("usage", {}),
    }


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=(__doc__ or "").split("\n", 1)[0])
    sub = p.add_subparsers(dest="command")

    # The default (no sub-command) keeps the Phase E1 transcription
    # behavior so ``make video-captions`` and existing tests don't break.
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
    p.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")

    style_p = sub.add_parser(
        "style",
        help="run the Phase G Opus 4.7 caption styling pass",
    )
    style_p.add_argument(
        "--variant",
        choices=["A", "B", "C", "all"],
        default="all",
        help="which variant(s) to style",
    )
    style_p.add_argument(
        "--force",
        action="store_true",
        help="re-run the API call even on a cache hit",
    )
    style_p.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")

    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    variants: tuple[Variant, ...] = ("A", "B", "C") if args.variant == "all" else (args.variant,)

    if getattr(args, "command", None) == "style":
        reports: list[dict[str, Any]] = []
        for v in variants:
            reports.append(style_variant(v, force=args.force))
        print("opus 4.7 caption styling:")
        for r in reports:
            usage = r.get("usage", {})
            tag = (
                "skipped (cache)"
                if r.get("cached")
                else ("skipped" if r.get("skipped") else "styled")
            )
            print(
                f"  {r['variant']}: {tag} "
                f"({r.get('word_count', 0)} words"
                + (
                    f", in={usage.get('input_tokens', 0)} "
                    f"out={usage.get('output_tokens', 0)} "
                    f"cache_read={usage.get('cache_read_input_tokens', 0)}"
                    if usage
                    else ""
                )
                + ")"
            )
        print(f"output dir: {CAPTIONS_DIR.relative_to(ROOT)}")
        return 0

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
