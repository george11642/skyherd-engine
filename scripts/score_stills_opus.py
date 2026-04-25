#!/usr/bin/env python3
"""
score_stills_opus.py — Parallel Opus stills scorer for SkyHerd video iteration.

Splits ~360 stills (2fps × 180s) into 30 batches of 12 (6-second windows).
Spawns up to 8 concurrent Anthropic Messages API calls with claude-opus-4-7.
Uses prompt caching: cache_control on system+skills prefix (cacheable across all 30 batches).

Usage:
    python scripts/score_stills_opus.py \\
        --stills-dir out/iter-3/A-stills \\
        --variant A --iter 3 \\
        --output-dir out/iter-3/A-opus-stills \\
        --jsonl out/iter-3/A-opus-stills.jsonl

Token budget: ~600K tokens/variant/iter at Opus 4.7 rates (~$10/variant/iter).
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import os
import sys
import time
from pathlib import Path

import anthropic

# ── Constants ─────────────────────────────────────────────────────────────────

BATCH_SIZE = 12          # stills per batch (6s window at 2fps)
TOTAL_STILLS = 360       # 180s × 2fps
NUM_BATCHES = 30         # TOTAL_STILLS // BATCH_SIZE
SEMAPHORE_LIMIT = 8      # max concurrent API calls (rate limit safety)
MODEL = "claude-opus-4-7"
MAX_TOKENS = 2048

PROJECT_ROOT = Path(__file__).parent.parent
PROMPT_PATH = PROJECT_ROOT / "scripts" / "prompts" / "opus-stills-batch.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("score_stills_opus")


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_prompt_template() -> str:
    """Load the opus-stills-batch prompt template."""
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"Prompt not found: {PROMPT_PATH}")
    return PROMPT_PATH.read_text()


def list_stills(stills_dir: Path) -> list[Path]:
    """Return sorted list of JPEG stills from the directory."""
    stills = sorted(stills_dir.glob("f*.jpg"))
    if not stills:
        raise FileNotFoundError(f"No stills found in {stills_dir}")
    log.info("Found %d stills in %s", len(stills), stills_dir)
    return stills


def make_batches(stills: list[Path]) -> list[list[Path]]:
    """Split stills list into batches of BATCH_SIZE."""
    batches = []
    for i in range(0, len(stills), BATCH_SIZE):
        batches.append(stills[i : i + BATCH_SIZE])
    return batches


def frame_to_seconds(frame_path: Path, fps: float = 2.0) -> float:
    """Extract frame number from filename like f0042.jpg → seconds."""
    stem = frame_path.stem  # f0042
    try:
        frame_num = int(stem.lstrip("f"))
        return (frame_num - 1) / fps
    except ValueError:
        return 0.0


def encode_image(path: Path) -> str:
    """Base64-encode a JPEG file."""
    return base64.standard_b64encode(path.read_bytes()).decode("utf-8")


def build_system_content(prompt_template: str) -> list[dict]:
    """Build the cacheable system content block."""
    # Extract system portion (everything before "## User")
    parts = prompt_template.split("## User", 1)
    system_text = parts[0].strip()
    return [
        {
            "type": "text",
            "text": system_text,
            "cache_control": {"type": "ephemeral"},  # CLAUDE.md: prompt caching mandatory
        }
    ]


def build_user_content(
    batch: list[Path],
    variant: str,
    iter_num: int,
    prompt_template: str,
) -> list[dict]:
    """Build user message content: prompt text + image blocks."""
    # Extract user template portion
    parts = prompt_template.split("## User", 1)
    user_template = parts[1].strip() if len(parts) > 1 else ""

    start_sec = frame_to_seconds(batch[0])
    end_sec = frame_to_seconds(batch[-1]) + 0.5  # +0.5 for the last frame's duration
    start_frame = batch[0].stem
    end_frame = batch[-1].stem

    user_text = (
        user_template
        .replace("${VARIANT}", variant)
        .replace("${START_SEC}", f"{start_sec:.1f}")
        .replace("${END_SEC}", f"{end_sec:.1f}")
        .replace("${START_FRAME}", start_frame)
        .replace("${END_FRAME}", end_frame)
        .replace("${ITER}", str(iter_num))
        .replace("${NUM_FRAMES}", str(len(batch)))
        .replace("[FRAMES INSERTED HERE AS BASE64 JPEG IMAGE BLOCKS]", "")
    )

    content: list[dict] = [{"type": "text", "text": user_text.strip()}]

    # Add each frame as an image block
    for frame_path in batch:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": encode_image(frame_path),
                },
            }
        )

    return content


def parse_batch_response(response_text: str, batch: list[Path], variant: str, iter_num: int) -> dict:
    """Parse Opus JSON response, with graceful fallback on parse errors."""
    # Strip any markdown code fences
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        data = json.loads(text)
        # Validate required keys
        required = {"batch_start_seconds", "batch_end_seconds", "scores", "flags", "fix_suggestions"}
        if not required.issubset(data.keys()):
            raise ValueError(f"Missing keys: {required - set(data.keys())}")
        return data
    except (json.JSONDecodeError, ValueError) as e:
        log.warning("Batch parse error (batch starts at %s): %s", batch[0].stem, e)
        start_sec = frame_to_seconds(batch[0])
        end_sec = frame_to_seconds(batch[-1]) + 0.5
        return {
            "batch_start_seconds": start_sec,
            "batch_end_seconds": end_sec,
            "window_description": "Parse error — raw response stored in _raw_response",
            "scores": {"impact": 5.0, "demo": 5.0, "opus": 5.0, "depth": 5.0},
            "flags": [{"severity": "HIGH", "frame": batch[0].stem, "issue": f"Score parse error: {e}"}],
            "fix_suggestions": [],
            "_raw_response": response_text[:500],
            "_parse_error": str(e),
        }


# ── Async Opus caller ──────────────────────────────────────────────────────────

async def score_batch(
    client: anthropic.AsyncAnthropic,
    semaphore: asyncio.Semaphore,
    batch_idx: int,
    batch: list[Path],
    variant: str,
    iter_num: int,
    system_content: list[dict],
    prompt_template: str,
    output_dir: Path,
) -> dict:
    """Score a single batch of stills with Opus. Retries up to 3 times."""
    batch_label = f"batch-{batch_idx:02d}"
    output_path = output_dir / f"{batch_label}.json"

    # Check cache — skip if already scored
    if output_path.exists():
        log.info("[%s] Cache hit — skipping API call", batch_label)
        return json.loads(output_path.read_text())

    user_content = build_user_content(batch, variant, iter_num, prompt_template)

    for attempt in range(1, 4):  # up to 3 retries
        async with semaphore:
            try:
                log.info("[%s] Sending to Opus (attempt %d, %d frames)", batch_label, attempt, len(batch))
                t0 = time.monotonic()

                response = await client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=system_content,  # type: ignore[arg-type]
                    messages=[{"role": "user", "content": user_content}],
                )

                elapsed = time.monotonic() - t0
                usage = response.usage
                log.info(
                    "[%s] Done in %.1fs | cache_read=%d cache_write=%d uncached=%d",
                    batch_label,
                    elapsed,
                    usage.cache_read_input_tokens,
                    usage.cache_creation_input_tokens,
                    usage.input_tokens,
                )

                text = next(
                    (b.text for b in response.content if b.type == "text"),
                    ""
                )
                result = parse_batch_response(text, batch, variant, iter_num)
                result["_batch_idx"] = batch_idx
                result["_usage"] = {
                    "cache_read": usage.cache_read_input_tokens,
                    "cache_write": usage.cache_creation_input_tokens,
                    "uncached": usage.input_tokens,
                    "output": usage.output_tokens,
                }

                output_path.write_text(json.dumps(result, indent=2))
                return result

            except anthropic.RateLimitError as e:
                retry_after = int(getattr(e.response.headers, "retry-after", "30") if hasattr(e, "response") else "30")
                log.warning("[%s] Rate limit (attempt %d). Waiting %ds...", batch_label, attempt, retry_after)
                await asyncio.sleep(retry_after)

            except anthropic.APIStatusError as e:
                if e.status_code >= 500:
                    wait = 5 * attempt
                    log.warning("[%s] Server error %d (attempt %d). Waiting %ds...", batch_label, e.status_code, attempt, wait)
                    await asyncio.sleep(wait)
                else:
                    log.error("[%s] API error %d: %s", batch_label, e.status_code, e.message)
                    break

            except Exception as e:
                log.error("[%s] Unexpected error (attempt %d): %s", batch_label, attempt, e)
                await asyncio.sleep(5 * attempt)

    # All retries exhausted — return error result
    log.error("[%s] All retries exhausted", batch_label)
    start_sec = frame_to_seconds(batch[0])
    end_sec = frame_to_seconds(batch[-1]) + 0.5
    return {
        "batch_start_seconds": start_sec,
        "batch_end_seconds": end_sec,
        "window_description": "ERROR: all API retries exhausted",
        "scores": {"impact": 0.0, "demo": 0.0, "opus": 0.0, "depth": 0.0},
        "flags": [{"severity": "CRITICAL", "frame": batch[0].stem, "issue": "API call failed after 3 retries"}],
        "fix_suggestions": [],
        "_batch_idx": batch_idx,
        "_error": "all_retries_exhausted",
    }


async def run_all_batches(
    stills_dir: Path,
    variant: str,
    iter_num: int,
    output_dir: Path,
    jsonl_path: Path,
) -> list[dict]:
    """Fan out all batches in parallel with semaphore-limited concurrency."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Try .env.local
        env_local = PROJECT_ROOT / ".env.local"
        if env_local.exists():
            for line in env_local.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set. Export it or put it in .env.local")

    output_dir.mkdir(parents=True, exist_ok=True)

    stills = list_stills(stills_dir)
    batches = make_batches(stills)
    actual_num = len(batches)
    log.info("Scoring %d batches × %d frames (variant=%s iter=%d)", actual_num, BATCH_SIZE, variant, iter_num)

    prompt_template = load_prompt_template()
    system_content = build_system_content(prompt_template)

    client = anthropic.AsyncAnthropic(api_key=api_key)
    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)

    tasks = [
        score_batch(
            client=client,
            semaphore=semaphore,
            batch_idx=i,
            batch=batch,
            variant=variant,
            iter_num=iter_num,
            system_content=system_content,
            prompt_template=prompt_template,
            output_dir=output_dir,
        )
        for i, batch in enumerate(batches)
    ]

    t_start = time.monotonic()
    results = await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t_start

    # Sort by batch_start_seconds
    results_sorted = sorted(results, key=lambda r: r.get("batch_start_seconds", 0))

    # Write merged JSONL
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w") as f:
        for r in results_sorted:
            f.write(json.dumps(r) + "\n")

    # Token budget summary
    total_cache_read = sum(r.get("_usage", {}).get("cache_read", 0) for r in results_sorted)
    total_cache_write = sum(r.get("_usage", {}).get("cache_write", 0) for r in results_sorted)
    total_uncached = sum(r.get("_usage", {}).get("uncached", 0) for r in results_sorted)
    total_output = sum(r.get("_usage", {}).get("output", 0) for r in results_sorted)
    total_input = total_cache_read + total_cache_write + total_uncached

    opus_input_rate = 5.0 / 1_000_000   # $5/M input
    opus_output_rate = 25.0 / 1_000_000  # $25/M output
    # Cache reads cost 0.1×, cache writes 1.25×, uncached 1×
    cost = (
        total_cache_read * opus_input_rate * 0.1
        + total_cache_write * opus_input_rate * 1.25
        + total_uncached * opus_input_rate
        + total_output * opus_output_rate
    )

    log.info(
        "Completed %d batches in %.1fs | tokens: input=%d (cached_read=%d) output=%d | est_cost=$%.2f",
        actual_num, elapsed, total_input, total_cache_read, total_output, cost,
    )
    log.info("JSONL written to %s", jsonl_path)

    return results_sorted


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score SkyHerd video stills with Opus 4.7 (parallel batched vision).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--stills-dir", required=True, type=Path, help="Directory containing f*.jpg stills")
    parser.add_argument("--variant", required=True, choices=["A", "B", "C"], help="Video variant")
    parser.add_argument("--iter", required=True, type=int, help="Iteration number")
    parser.add_argument("--output-dir", required=True, type=Path, help="Per-batch JSON output directory")
    parser.add_argument("--jsonl", required=True, type=Path, help="Merged JSONL output path")
    parser.add_argument("--help-schema", action="store_true", help="Print expected output schema and exit")

    args = parser.parse_args()

    if args.help_schema:
        schema = {
            "batch_start_seconds": "float",
            "batch_end_seconds": "float",
            "window_description": "string",
            "scores": {"impact": "float 0-10", "demo": "float 0-10", "opus": "float 0-10", "depth": "float 0-10"},
            "flags": [{"severity": "CRITICAL|HIGH|MEDIUM|LOW", "frame": "string", "issue": "string"}],
            "fix_suggestions": [{"priority": "int", "frame": "string", "file_path": "string", "change": "string"}],
        }
        print(json.dumps(schema, indent=2))
        sys.exit(0)

    asyncio.run(
        run_all_batches(
            stills_dir=args.stills_dir,
            variant=args.variant,
            iter_num=args.iter,
            output_dir=args.output_dir,
            jsonl_path=args.jsonl,
        )
    )


if __name__ == "__main__":
    main()
