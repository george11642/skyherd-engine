"""OpenMontage EDL → Remotion props translator.

Reads OpenMontage's edit_decisions.json (schema v1.0) and emits a Remotion-compatible
JSON object describing <Sequence> props. The host Remotion composition imports this
and renders deterministically.

OpenMontage is an external AGPL-licensed tool. This adapter only consumes its OUTPUT
files; it never imports OpenMontage code. See docs/OPENMONTAGE_INTEGRATION.md.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_FPS = 60
SUPPORTED_RUNTIME = "remotion"


class EdlPathOutsideRepo(ValueError):
    """Raised when an EDL references an asset path outside the project tree."""


class EdlWrongRuntime(ValueError):
    """Raised when the EDL targets a render runtime other than Remotion."""


def load_edl(path: pathlib.Path) -> dict[str, Any]:
    """Permissive read — returns parsed JSON, no schema enforcement here."""
    return json.loads(path.read_text())


def validate_edl(edl: dict[str, Any]) -> list[str]:
    """Non-raising validator. Returns a list of error strings; empty == valid."""
    errors: list[str] = []
    if edl.get("version") != "1.0":
        errors.append(f"unsupported version: {edl.get('version')!r} (require '1.0')")
    cuts = edl.get("cuts")
    if not isinstance(cuts, list) or not cuts:
        errors.append("cuts must be a non-empty list")
    runtime = edl.get("render_runtime")
    if runtime != SUPPORTED_RUNTIME:
        errors.append(
            f"unsupported render_runtime: {runtime!r} (require {SUPPORTED_RUNTIME!r})"
        )
    return errors


def _seconds_to_frames(seconds: float, fps: int) -> int:
    return round(seconds * fps)


def _resolve_asset(source: str) -> dict[str, Any]:
    """Translate cuts[].source into a Remotion-friendly asset descriptor.

    Empty source → synthetic scene-component (drawn entirely in Remotion).
    Relative path → kept as-is.
    Absolute path inside REPO_ROOT → rewritten to repo-relative.
    Absolute path outside REPO_ROOT → raises EdlPathOutsideRepo.
    """
    if source == "":
        return {"kind": "scene-component"}
    p = pathlib.Path(source)
    if p.is_absolute():
        try:
            rel = p.resolve().relative_to(REPO_ROOT)
        except ValueError as exc:
            raise EdlPathOutsideRepo(f"asset path outside repo: {source}") from exc
        return {"kind": "asset", "path": rel.as_posix()}
    return {"kind": "asset", "path": source}


def to_remotion(
    edl: dict[str, Any],
    *,
    fps: int = DEFAULT_FPS,
) -> dict[str, Any]:
    """Translate an OpenMontage EDL to a Remotion props JSON object.

    Pure function — no I/O. Raises EdlWrongRuntime for non-remotion runtime,
    EdlPathOutsideRepo for asset paths outside the project tree, ValueError for
    other validation failures.
    """
    errors = validate_edl(edl)
    if errors:
        joined = "; ".join(errors)
        if any("render_runtime" in e for e in errors):
            raise EdlWrongRuntime(joined)
        raise ValueError(joined)

    cuts = sorted(edl["cuts"], key=lambda c: float(c.get("in_seconds", 0.0)))

    sequences: list[dict[str, Any]] = []
    for cut in cuts:
        in_s = float(cut.get("in_seconds", 0.0))
        out_s = float(cut.get("out_seconds", in_s))
        from_frame = _seconds_to_frames(in_s, fps)
        duration = max(0, _seconds_to_frames(out_s, fps) - from_frame)
        asset = _resolve_asset(cut.get("source", ""))
        seq: dict[str, Any] = {
            "id": cut.get("id"),
            "fromFrame": from_frame,
            "durationInFrames": duration,
            "asset": asset,
            "transition": cut.get("transition_in", "cut"),
            "transitionDurationFrames": _seconds_to_frames(
                float(cut.get("transition_in_duration", 0.0)), fps
            ),
            "metadata": {
                k: v
                for k, v in cut.items()
                if k
                not in {
                    "id",
                    "in_seconds",
                    "out_seconds",
                    "source",
                    "transition_in",
                    "transition_in_duration",
                }
            },
        }
        sequences.append(seq)

    last_cut = cuts[-1]
    duration_in_frames = _seconds_to_frames(
        float(last_cut.get("out_seconds", 0.0)), fps
    )

    audio_block = edl.get("audio") or {}

    return {
        "fps": fps,
        "durationInFrames": duration_in_frames,
        "sequences": sequences,
        "overlays": edl.get("overlays") or [],
        "transitions": edl.get("transitions") or [],
        "audio": {
            "narrationSegments": audio_block.get("narration") or [],
            "music": audio_block.get("music"),
            "sfx": audio_block.get("sfx") or [],
        },
        "captionEmphasis": edl.get("caption_emphasis"),
        "metadata": {
            "sourceTool": "openmontage",
            "sourceVersion": (edl.get("metadata") or {}).get("openmontage_version"),
            "rendererFamily": edl.get("renderer_family"),
            "ingestedAt": datetime.now(timezone.utc).isoformat(),
        },
    }


def main(
    input_path: str,
    output_path: str,
    fps: int = DEFAULT_FPS,
) -> int:
    """CLI entrypoint. Returns exit code: 0 ok, 2 validation error, 1 IO error."""
    src = pathlib.Path(input_path)
    try:
        edl = load_edl(src)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to load {src}: {exc}", file=sys.stderr)
        return 1
    try:
        remotion = to_remotion(edl, fps=fps)
    except (EdlWrongRuntime, EdlPathOutsideRepo, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    pathlib.Path(output_path).write_text(json.dumps(remotion, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Translate OpenMontage edit_decisions.json to Remotion props."
    )
    parser.add_argument("input", help="Path to OpenMontage edit_decisions.json")
    parser.add_argument("output", help="Path to write Remotion props JSON")
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    args = parser.parse_args()
    sys.exit(main(args.input, args.output, fps=args.fps))
