#!/usr/bin/env python3
"""qc_video_per_second.py — per-frame Opus 4.7 vision QC for SkyHerd demo videos.

Sends one API call per frame with cache_control on the system prompt so the
shared instructions hit cache after the first call. Used to detect duplicate
captions, missing captions, and on-screen text quality issues at 1-second
granularity.

Usage:
    python scripts/qc_video_per_second.py \\
        --frames-dir out/qc-frames-YYYYMMDD-HHMMSS/v56 \\
        --output out/qc-frames-YYYYMMDD-HHMMSS/analysis.jsonl

    # restrict to specific seconds (Phase 6 verification mode)
    python scripts/qc_video_per_second.py \\
        --frames-dir out/qc-frames-YYYYMMDD-HHMMSS/v57 \\
        --output out/qc-frames-YYYYMMDD-HHMMSS/verify.jsonl \\
        --only-seconds 165,166,167,168,169,170
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import anthropic

MODEL = "claude-opus-4-7"
MAX_TOKENS = 1024
SEMAPHORE_LIMIT = 8
PROJECT_ROOT = Path(__file__).parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("qc_per_second")


SYSTEM_PROMPT = """You are a video QC reviewer for the SkyHerd demo (1920x1080, 30 fps, 180 seconds, MIT-licensed ranch-tech demo). The viewer sees a single still frame at a time. Your job is to report exactly what captions are visible on that frame.

Scene map by playback second (variant C):
- 0-3:    cold-open slam ("1 rancher | 10000 acres | 0 sleep")
- 3-6:    cold-open aerial stat card ("$1.8B/yr")
- 6-27:   Act 1 hook (Ken-Burns aerial)
- 27-50:  Act 2 traditional diagram
- 50-66:  Act 2 nervous-system stack diagram
- 66-96:  Act 3 coyote dashboard (live FenceLineDispatcher)
- 96-120: Act 3 scenario grid (4-card layout)
- 120-143: Act 4 software MVP blocks diagram
- 143-165: Act 4 vision timeline diagram
- 165-178: Act 5 AI Body close (mountain b-roll, hardcoded large outro lines)
- 178-180: wordmark tail ("SkyHerd")

For each frame return ONLY a single JSON object (no prose, no markdown fences) with:
- t: integer second of the frame (echo from input)
- captions_visible: array of strings, one per distinct caption / on-screen text element you can read clearly. Top to bottom, left to right. Each string is the literal visible text. Exclude small UI labels embedded in dashboards/diagrams (e.g. dashboard column headers, button labels) - only count narrative captions / lower thirds / large overlay text.
- caption_count: integer length of captions_visible
- dupe_suspected: true if the frame has two or more caption strings whose text is partially redundant or overlapping (e.g. one caption says "And the future of AI?" and another says "And the future of A I" or "the future of"). Word-by-word streams stacked on top of full-line captions count as duplicates.
- missing_suspected: true if the scene clearly has narration happening (mid-sentence diagram reveal, B-roll with someone speaking, mid-VO scene) but NO narrative caption is visible. Inter-scene blank holds are NOT missing.
- scene_label: short string naming the act/scene (use the map above)
- notes: optional one-sentence flag for anything weird (e.g. "caption text is cut off", "duplicate appears below main caption"). Empty string if nothing.

Return strict JSON only. No surrounding text, no code fences."""


def encode_image(path: Path) -> str:
    return base64.standard_b64encode(path.read_bytes()).decode("utf-8")


def load_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    env_local = PROJECT_ROOT / ".env.local"
    if env_local.exists():
        for line in env_local.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value
    raise EnvironmentError("ANTHROPIC_API_KEY not found in env or .env.local")


def frame_to_second(path: Path) -> int:
    """frame_001.jpg -> second 0, frame_180.jpg -> second 179."""
    m = re.match(r"frame_(\d+)", path.stem)
    if not m:
        raise ValueError(f"unexpected frame name: {path.name}")
    return int(m.group(1)) - 1


def build_user_content(frame_path: Path, second: int) -> list[dict]:
    return [
        {
            "type": "text",
            "text": f"Frame at playback second t={second}. Return strict JSON only.",
        },
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": encode_image(frame_path),
            },
        },
    ]


def parse_response(text: str, second: int) -> dict:
    raw = text.strip()
    if raw.startswith("```"):
        # strip first fence line
        lines = raw.split("\n")
        # drop opening fence
        lines = lines[1:]
        # drop trailing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning("parse error at t=%d: %s; raw=%s", second, e, text[:200])
        return {
            "t": second,
            "captions_visible": [],
            "caption_count": 0,
            "dupe_suspected": False,
            "missing_suspected": False,
            "scene_label": "PARSE_ERROR",
            "notes": f"parse error: {e}",
            "_raw": text[:300],
            "_parse_error": str(e),
        }
    # ensure t is set correctly
    data["t"] = second
    # backfill missing keys defensively
    data.setdefault("captions_visible", [])
    data.setdefault("caption_count", len(data["captions_visible"]))
    data.setdefault("dupe_suspected", False)
    data.setdefault("missing_suspected", False)
    data.setdefault("scene_label", "")
    data.setdefault("notes", "")
    return data


async def analyze_frame(
    client: anthropic.AsyncAnthropic,
    semaphore: asyncio.Semaphore,
    frame_path: Path,
    second: int,
    system_blocks: list[dict],
) -> dict:
    user_content = build_user_content(frame_path, second)
    for attempt in range(1, 4):
        try:
            async with semaphore:
                t0 = time.monotonic()
                response = await client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=system_blocks,  # type: ignore[arg-type]
                    messages=[{"role": "user", "content": user_content}],
                )
                elapsed = time.monotonic() - t0
                usage = response.usage
                text = next((b.text for b in response.content if b.type == "text"), "")
                result = parse_response(text, second)
                result["_usage"] = {
                    "cache_read": usage.cache_read_input_tokens,
                    "cache_write": usage.cache_creation_input_tokens,
                    "uncached": usage.input_tokens,
                    "output": usage.output_tokens,
                    "elapsed_s": round(elapsed, 2),
                }
                return result
        except anthropic.RateLimitError as e:
            wait = 30
            try:
                wait = int(e.response.headers.get("retry-after", "30"))
            except Exception:
                pass
            log.warning("[t=%d] rate-limited attempt %d, sleeping %ds", second, attempt, wait)
            await asyncio.sleep(wait)
        except anthropic.APIStatusError as e:
            wait = 5 * attempt
            log.warning("[t=%d] api error %d attempt %d, sleeping %ds", second, e.status_code, attempt, wait)
            await asyncio.sleep(wait)
        except Exception as e:
            log.warning("[t=%d] unexpected error attempt %d: %s", second, attempt, e)
            await asyncio.sleep(5 * attempt)
    log.error("[t=%d] all retries exhausted", second)
    return {
        "t": second,
        "captions_visible": [],
        "caption_count": 0,
        "dupe_suspected": False,
        "missing_suspected": False,
        "scene_label": "API_ERROR",
        "notes": "all retries exhausted",
        "_error": "retries_exhausted",
    }


async def run(frames_dir: Path, output_jsonl: Path, only_seconds: set[int] | None) -> None:
    api_key = load_api_key()
    frames = sorted(frames_dir.glob("frame_*.jpg"))
    if not frames:
        raise FileNotFoundError(f"no frames in {frames_dir}")

    pairs: list[tuple[Path, int]] = []
    for f in frames:
        sec = frame_to_second(f)
        if only_seconds is None or sec in only_seconds:
            pairs.append((f, sec))

    log.info("analyzing %d frames (filter=%s)", len(pairs), "all" if only_seconds is None else f"{len(only_seconds)} seconds")

    system_blocks = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    client = anthropic.AsyncAnthropic(api_key=api_key)
    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)

    tasks = [analyze_frame(client, semaphore, fp, sec, system_blocks) for fp, sec in pairs]

    results: list[dict] = []
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    t_start = time.monotonic()

    # write incrementally as each finishes
    with output_jsonl.open("w") as f:
        for coro in asyncio.as_completed(tasks):
            r = await coro
            results.append(r)
            f.write(json.dumps(r) + "\n")
            f.flush()
            if len(results) % 10 == 0:
                log.info("progress: %d/%d", len(results), len(pairs))

    elapsed = time.monotonic() - t_start
    cache_read = sum(r.get("_usage", {}).get("cache_read", 0) for r in results)
    cache_write = sum(r.get("_usage", {}).get("cache_write", 0) for r in results)
    uncached = sum(r.get("_usage", {}).get("uncached", 0) for r in results)
    output = sum(r.get("_usage", {}).get("output", 0) for r in results)

    # Opus 4.7 pricing (input $5/M, output $25/M, cache_read 0.1x, cache_write 1.25x)
    cost = (
        cache_read * 5.0 / 1_000_000 * 0.1
        + cache_write * 5.0 / 1_000_000 * 1.25
        + uncached * 5.0 / 1_000_000
        + output * 25.0 / 1_000_000
    )

    log.info(
        "done %d frames in %.1fs | cache_read=%d cache_write=%d uncached=%d output=%d | est=$%.2f",
        len(results), elapsed, cache_read, cache_write, uncached, output, cost,
    )
    log.info("written: %s", output_jsonl)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--only-seconds",
        type=str,
        default=None,
        help="comma-separated seconds (e.g. 165,166,170) - if set, only analyze these",
    )
    args = parser.parse_args()
    only = None
    if args.only_seconds:
        only = {int(s.strip()) for s in args.only_seconds.split(",") if s.strip()}
    asyncio.run(run(args.frames_dir, args.output, only))


if __name__ == "__main__":
    main()
