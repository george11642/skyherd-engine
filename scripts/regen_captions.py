#!/usr/bin/env python3
"""
regen_captions.py — Regenerate styled-captions-C.json using faster-whisper
word-level timestamps.

For each v4 C cue, loads the corresponding Inworld Nate MP3 and runs
faster-whisper transcription with word_timestamps=True and the cue text as
initial_prompt (ground-truth hint). This produces per-word start/end timestamps
that match the actual Inworld Nate audio, replacing the stale ElevenLabs-era
timestamps.

NOTE: whisperx (primary tool in plan) fails on this system due to a torchaudio
CUDA symbol mismatch (libtorchaudio.so: undefined symbol). faster-whisper is the
plan's first-listed fallback and provides the same [{word, start, end}] shape.

Per-word fields output (StyledWord schema from KineticCaptions.tsx):
  word, start, end, segment_id  — alignment-derived
  color, weight, animation, emphasis_level — defaults only
    color="#F5D49C", weight="normal", animation="fade", emphasis_level=1

The Opus-4.7 per-word styling (color/weight/animation/emphasis_level) is
intentionally stripped; the v4 rewrite removes the "Opus styled these captions"
meta-loop beat and goes with clean, uniform rendering. Default values are
supplied so KineticCaptions.tsx (which treats these as Required fields in
StyledWord) continues to render without changes.

Timeline offsets (absolute composition seconds, locked in plan v5.1
make-it-not-say-prancy-pudding.md):
  vo-c-hook         →   6s   (cold open extended to 6s)
  vo-c-traditional  →  28s
  vo-c-answer       →  48s
  vo-c-coyote       →  66s
  vo-c-grid         →  92s
  vo-c-mvp          → 114s
  vo-c-vision       → 134s
  vo-c-aibody       → 152s

Usage:
  uv run python scripts/regen_captions.py
  uv run python scripts/regen_captions.py --validate
  uv run python scripts/regen_captions.py --cue-keys vo-c-hook,vo-c-coyote
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
VO_DIR_DEFAULT = REPO_ROOT / "remotion-video/public/voiceover"
OUT_DEFAULT = REPO_ROOT / "remotion-video/public/captions/styled-captions-C.json"
CUES_FILE_DEFAULT = REPO_ROOT / "scripts/vo_cues.sh"

# Cue keys in playback order + their absolute composition start-time (seconds).
# Updated per plan v5.2 (make-it-not-say-prancy-pudding.md): 180s composition,
# 6s cold open, extended cue copy fills each scene window with ≤1.5s tail.
CUE_OFFSETS: dict[str, float] = {
    "vo-c-hook":         6.0,   # cold open is 6s
    "vo-c-traditional": 26.0,   # 6 + 20 hook
    "vo-c-answer":      50.0,   # 26 + 24 traditional
    "vo-c-coyote":      67.0,   # 50 + 17 answer
    "vo-c-grid":        97.0,   # 67 + 30 coyote
    "vo-c-mvp":        121.0,   # 97 + 24 grid
    "vo-c-vision":     144.0,   # 121 + 23 mvp
    "vo-c-aibody":     166.0,   # 144 + 22 vision
}

# Default StyledWord styling (uniform; no Opus-authored per-word color).
DEFAULT_COLOR = "#F5D49C"
DEFAULT_WEIGHT = "normal"
DEFAULT_ANIMATION = "fade"
DEFAULT_EMPHASIS_LEVEL = 1

# whisperx alignment language / model
ALIGN_LANGUAGE = "en"

# ---------------------------------------------------------------------------
# Text pre-processing helpers
# ---------------------------------------------------------------------------

# Patterns that whisperx's wav2vec2 aligner struggles with if left as-is.
# Maps display form → phonetic form for alignment. Post-process step
# re-collapses to display form in the output JSON word strings.
_PHONETIC_MAP: list[tuple[re.Pattern[str], str]] = [
    # "four-point-seven" → "four point seven"
    (re.compile(r"\bfour-point-seven\b", re.I), "four point seven"),
    # "M-V-P" → "M V P"
    (re.compile(r"\bM-V-P\b"), "M V P"),
    # "Voice-A-I" → "Voice A I"
    (re.compile(r"\bVoice-A-I\b", re.I), "Voice A I"),
    # "M-I-T-licensed" → "M I T licensed"
    (re.compile(r"\bM-I-T-licensed\b", re.I), "M I T licensed"),
    # "L-O-R-A" → "L O R A"
    (re.compile(r"\bL-O-R-A\b", re.I), "L O R A"),
    # "A-I" → "A I"
    (re.compile(r"\bA-I\b"), "A I"),
    # "three-fourteen" → "three fourteen"
    (re.compile(r"\bthree-fourteen\b", re.I), "three fourteen"),
    # "three A-M" → "three A M"
    (re.compile(r"\bA-M\b"), "A M"),
    # numbers with hyphens: "two-hundred" → "two hundred"
    (re.compile(r"\b(\w+)-(\w+)\b"), r"\1 \2"),
    # dollar amounts: "$4.17" → "four dollars seventeen cents"  (unlikely in cues but safe)
    (re.compile(r"\$(\d+)\.(\d+)"), lambda m: _dollars(m)),
]


def _dollars(m: re.Match[str]) -> str:
    dollars = int(m.group(1))
    cents = int(m.group(2))
    return f"{dollars} dollars {cents} cents"


def phonetic_text(text: str) -> str:
    """Convert display text to phonetic form for alignment."""
    result = text
    for pattern, replacement in _PHONETIC_MAP:
        if callable(replacement):
            result = pattern.sub(replacement, result)  # type: ignore[arg-type]
        else:
            result = pattern.sub(replacement, result)
    return result


# ---------------------------------------------------------------------------
# vo_cues.sh parser
# ---------------------------------------------------------------------------

def parse_cues(cues_file: Path) -> dict[str, str]:
    """
    Parse CUES["key"]="text" entries from vo_cues.sh.
    Returns {key: text} mapping.
    Does not execute the shell script — uses regex parsing only.
    """
    content = cues_file.read_text()
    pattern = re.compile(
        r'^CUES\["(vo-c-[^"]+)"\]\s*=\s*"((?:[^"\\]|\\.)*)"',
        re.MULTILINE,
    )
    cues: dict[str, str] = {}
    for m in pattern.finditer(content):
        key = m.group(1)
        # Unescape bash double-quote escapes
        text = m.group(2).replace('\\"', '"').replace("\\\\", "\\")
        cues[key] = text
    return cues


# ---------------------------------------------------------------------------
# faster-whisper word-level timestamp alignment
# (Plan fallback: whisperx fails due to torchaudio CUDA symbol mismatch)
# ---------------------------------------------------------------------------

# Module-level model cache — load once, reuse across all 8 cues.
_fw_model_cache: object | None = None
_fw_model_device: str = ""


def _get_fw_model(device: str) -> object:
    global _fw_model_cache, _fw_model_device
    if _fw_model_cache is None or _fw_model_device != device:
        from faster_whisper import WhisperModel
        print(
            f"[regen_captions] Loading faster-whisper model (base.en, device={device}) …"
        )
        # base.en: fast, English-only, ~145 MB, good word-level accuracy
        _fw_model_cache = WhisperModel("base.en", device=device, compute_type="int8")
        _fw_model_device = device
        print("[regen_captions] faster-whisper model loaded.")
    return _fw_model_cache


def align_cue(
    audio_path: Path,
    text: str,
    device: str = "cpu",
) -> list[dict[str, float | str]]:
    """
    Run faster-whisper transcription with word_timestamps=True on a single cue.

    Uses the cue text as initial_prompt so Whisper stays on-script for proper
    nouns and acronyms (MVP, LoRa, etc.). Returns list of
    {word, start, end} dicts with timestamps relative to the start of the audio
    file (cue-relative). The caller adds the composition offset.
    """
    model = _get_fw_model(device)

    # Use phonetic form as initial_prompt so the model recognises abbreviations
    phonetic = phonetic_text(text)

    # condition_on_previous_text=False prevents Whisper repeat-attractor loops
    # (e.g. vo-c-grid produced 277 words including 33x "A cow goes into labor
    # before dawn." with the default True setting — pure transcription
    # artifact, audio is fine).
    segments_iter, _info = model.transcribe(  # type: ignore[attr-defined]
        str(audio_path),
        language="en",
        word_timestamps=True,
        initial_prompt=phonetic,
        beam_size=5,
        vad_filter=False,
        condition_on_previous_text=False,
    )

    words: list[dict[str, float | str]] = []
    for seg in segments_iter:
        for w in (seg.words or []):
            word_text = str(w.word).strip()
            if not word_text:
                continue
            words.append({
                "word": word_text,
                "start": float(w.start),
                "end": float(w.end),
            })

    if not words:
        raise RuntimeError(
            f"faster-whisper returned no words for {audio_path.name}. "
            "Check that the audio file is not silent or corrupt."
        )

    return words


# ---------------------------------------------------------------------------
# Duration helper
# ---------------------------------------------------------------------------

def mp3_duration(path: Path) -> float:
    """Return duration of an MP3 in seconds via mutagen (fast, no subprocess)."""
    try:
        from mutagen.mp3 import MP3
        audio = MP3(str(path))
        return float(audio.info.length)
    except Exception:
        # Fallback: read duration via wave — won't work for mp3, so use subprocess
        import subprocess
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------

def generate(
    cue_keys: list[str],
    cues_file: Path,
    vo_dir: Path,
    out_path: Path,
    device: str = "cpu",
) -> None:
    print(f"[regen_captions] Parsing cues from {cues_file}")
    all_cues = parse_cues(cues_file)

    output_words: list[dict] = []
    segment_id = 0

    for cue_key in cue_keys:
        if cue_key not in all_cues:
            raise ValueError(
                f"Cue key '{cue_key}' not found in {cues_file}. "
                f"Available v4 C keys: {[k for k in all_cues if k.startswith('vo-c-')]}"
            )

        text = all_cues[cue_key]
        audio_path = vo_dir / f"{cue_key}.mp3"

        if not audio_path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio_path}. "
                "Run `bash scripts/render_vo.sh --provider inworld` first."
            )

        offset = CUE_OFFSETS[cue_key]
        print(f"[regen_captions] Aligning {cue_key} (offset={offset}s) …")

        words = align_cue(audio_path, text, device=device)

        for w in words:
            output_words.append({
                "word": str(w["word"]),
                "start": round(float(w["start"]) + offset, 4),
                "end": round(float(w["end"]) + offset, 4),
                "segment_id": segment_id,
                "color": DEFAULT_COLOR,
                "weight": DEFAULT_WEIGHT,
                "animation": DEFAULT_ANIMATION,
                "emphasis_level": DEFAULT_EMPHASIS_LEVEL,
            })

        word_count = len(words)
        print(f"[regen_captions]   → {word_count} words aligned for {cue_key}")
        segment_id += 1

    # Build fingerprint over the word data
    fingerprint = hashlib.sha256(
        json.dumps(output_words, sort_keys=True).encode()
    ).hexdigest()

    payload = {
        "variant": "C",
        "mode": "styled",
        "model": "whisperx-forced-alignment",
        "fingerprint": fingerprint,
        "words": output_words,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"[regen_captions] Wrote {len(output_words)} words → {out_path}")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(
    cue_keys: list[str],
    vo_dir: Path,
    out_path: Path,
) -> bool:
    if not out_path.exists():
        print(f"[validate] FAIL — output file does not exist: {out_path}")
        return False

    with out_path.open() as f:
        data = json.load(f)

    words: list[dict] = data.get("words", [])
    if not words:
        print("[validate] FAIL — no words in output JSON")
        return False

    # Group words by segment_id
    segments: dict[int, list[dict]] = {}
    for w in words:
        sid = w["segment_id"]
        segments.setdefault(sid, []).append(w)

    all_pass = True

    for idx, cue_key in enumerate(cue_keys):
        seg_words = segments.get(idx, [])
        if not seg_words:
            print(f"[validate] FAIL [{cue_key}] — no words for segment_id={idx}")
            all_pass = False
            continue

        audio_path = vo_dir / f"{cue_key}.mp3"
        dur = mp3_duration(audio_path)
        offset = CUE_OFFSETS[cue_key]
        lo = offset
        hi = offset + dur

        errors: list[str] = []
        for i, w in enumerate(seg_words):
            ws, we = w["start"], w["end"]
            if ws < lo - 0.05:
                errors.append(f"word[{i}] '{w['word']}' start={ws:.3f} < cue_offset={lo:.3f}")
            if we > hi + 0.5:  # 0.5s grace for boundary words
                errors.append(f"word[{i}] '{w['word']}' end={we:.3f} > cue_end={hi:.3f}")
            if i > 0:
                prev_end = seg_words[i - 1]["end"]
                if ws < prev_end - 0.02:
                    errors.append(
                        f"word[{i}] '{w['word']}' start={ws:.3f} overlaps prev end={prev_end:.3f}"
                    )

        if errors:
            print(f"[validate] FAIL [{cue_key}] ({len(seg_words)} words, dur={dur:.2f}s):")
            for e in errors[:5]:
                print(f"    {e}")
            all_pass = False
        else:
            print(f"[validate] PASS [{cue_key}] ({len(seg_words)} words, dur={dur:.2f}s, offset={offset}s)")

    return all_pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate styled-captions-C.json using whisperx forced alignment."
    )
    parser.add_argument(
        "--cues-file",
        type=Path,
        default=CUES_FILE_DEFAULT,
        help="Path to vo_cues.sh",
    )
    parser.add_argument(
        "--vo-dir",
        type=Path,
        default=VO_DIR_DEFAULT,
        help="Directory containing vo-*.mp3 files",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_DEFAULT,
        help="Output JSON path",
    )
    parser.add_argument(
        "--cue-keys",
        type=str,
        default=",".join(CUE_OFFSETS.keys()),
        help="Comma-separated cue keys to process (default: all 8 v4 C cues)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="torch device for alignment model (default: cpu)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing output JSON without regenerating",
    )
    args = parser.parse_args()

    cue_keys = [k.strip() for k in args.cue_keys.split(",") if k.strip()]

    if args.validate:
        ok = validate(cue_keys, args.vo_dir, args.out)
        sys.exit(0 if ok else 1)
    else:
        generate(
            cue_keys=cue_keys,
            cues_file=args.cues_file,
            vo_dir=args.vo_dir,
            out_path=args.out,
            device=args.device,
        )


if __name__ == "__main__":
    main()
